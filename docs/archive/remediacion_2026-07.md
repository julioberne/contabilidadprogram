# Remediación de Auditoría — Julio 2026

**Fecha**: 2026-07-26 · **Rama**: `fix/audit-remediation` (mergeada a `master`) ·
**Estado**: F0–F4 + residuales al 100%, desplegado en producción. F5 (deuda menor) agendada como DT-11.

## Commits

| Commit | Fase | Contenido |
|---|---|---|
| `26438ad` | pre | Trabajo de features previo (router, cuentas, RRHH, inventario) |
| `47efd51` | F1 | Seguridad: backdoor, path traversal, auth con token, MD5 |
| `feb414e` | F2 | Estabilidad: fugas de conexión al pool |
| `7cf9905` | F3 | Contabilidad: emisión única, idempotencia, Decimal, validación COA |
| `187adb6` | F4 | Frontend: 7 hallazgos verificados |
| `818d9cc` | res. | 5 pendientes residuales (EntityTree, MembersList, 4120, AGENTS, ANSI) |

## Origen

Un informe de auditoría externo reportó ~75 hallazgos. Antes de ejecutar su plan se
**verificaron 28 hallazgos contra el código real**: 22 confirmados, 3 parciales y
3 falsos (los falsos estaban en frontend; uno de ellos —EntityTree— resultó luego
verdadero pero en OTRO archivo homónimo: `project-hub/settings/EntityTree.jsx`,
no `control-tower/CTEntityTree.jsx`). Lección: verificar por síntoma en todo el
repo, no por nombre de archivo.

## Qué se cambió

### F1 — Seguridad (`47efd51`)

| Cambio | Archivos |
|---|---|
| Backdoor eliminado: `andres@finsys.os/admin123` autenticaba como ADMIN incluso con el backend caído; el mensaje de error revelaba las credenciales | `shell/hooks/useGlobalSession.js` |
| Botón "CONTINUAR COMO ANDRÉS (DEMO)" eliminado | `control-tower/components/CTLoginRegister.jsx` |
| Auth por token HMAC firmado (12 h TTL, `SESSION_SECRET` o derivado): el login del hub emite `token`; `require_auth`/`require_admin` como `Depends()` | `routers/auth_guard.py` (nuevo), `routers/hub.py` |
| Endpoints destructivos protegidos: `POST /transactions/reset`, `/seed_synthetic`, `PUT`/`DELETE /module-flags` (403 sin rol owner/admin) | `routers/transactions.py`, `routers/module_flags.py` |
| Frontend adjunta `Authorization: Bearer` en esos 3 flujos + errores visibles | `shell/authHeaders.js` (nuevo), `useAdminActions.js`, `ModuleSettingsPanel.jsx` |
| Path traversal cerrado: filename saneado (basename + whitelist de extensión + prefijo aleatorio) en evidence/voice/transcribe | `routers/transactions.py` |
| MD5 eliminado del CT (sin fallback mock de login: BD caída = login falla); SHA-256 muerto eliminado del hub. Cierra **DT-04/DT-05** | `control_tower_driver.py`, `hub_driver.py` |

### F2 — Estabilidad BD (`feb414e`)

Las conexiones del pool (max 10) se fugaban en cada error: tras ~10 fallos el
backend se degradaba hasta reiniciar. Corregido con `finally` + patrón
`conn = None` en: `registrar_transaccion`/`actualizar_transaccion`
(`database_driver.py`), `cartera.py` (404 con conexión viva), **todo**
`module_flags.py` (no liberaba ni en éxito), `zero_coa.py` (bare `except`).
DDL de `cartera_payments` movido de cada GET a `init_db()`.

### F3 — Integridad contable (`7cf9905`)

El problema compuesto: cada `POST /api/transactions` generaba **dos grupos de
asientos** (una vía hardcodeada en `database_driver` con cuentas inventadas —
la 4120 no está en el seed— y otra vía posting_rules), sin ninguna llave que
impidiera duplicados, con errores tragados (`except: pass`) y la mitad de los
asientos invisibles en el resumen financiero (`cuenta_tipo: ''`).

- **Emisión única**: vía hardcodeada eliminada; todo pasa por
  `shared/helpers.emit_journal_entry` → posting_rules.
- **Idempotencia**: columna `linea` + índice único parcial
  `uq_journal_modulo_ref_linea (modulo_origen, referencia, linea)`. Re-emitir la
  misma referencia devuelve `skipped_duplicate`, jamás duplica. `entry_group_id`
  ya no usa `COUNT(*)+1` (condición de carrera) sino sufijo aleatorio.
- **Decimal, tolerancia 0**: partida doble validada con `Decimal` centavo a
  centavo; `0.1+0.2=0.3` cuadra, `100 vs 99.99` se rechaza.
- **Cuentas validadas**: `CuentaNoExisteError` real contra COA ∪ posting_rules.
- **Errores visibles**: el resultado del asiento viaja en la respuesta del POST
  (`journal: ok|skipped_duplicate|no_rule|error`) y se loguea si falla.
- **Datos históricos saneados**: `scripts/migrate_kernel_integrity.py` (aplicada)
  — backfill de `cuenta_tipo`, dedup de 9 referencias (21 líneas), huérfanos.
- **Tests honestos**: `python -m kernel.test_kernel` — 5 tests con asserts
  reales, refs `TEST-KRN-*` y cleanup en `finally` (antes: prints sin asserts
  que contaminaban la BD).

### F4 — Frontend (`187adb6`) y residuales (`818d9cc`)

Ver la sección siguiente: son los cambios que se ven directamente.

## Cómo se refleja en el FRONTEND (guía de usuario)

1. **Login** (`/`): ya no existe el acceso demo. Entrar con `andres@finsys.io`.
   El rol ADMIN se conserva (el shell reconoce owner/admin del hub). En Control
   Tower desapareció el botón demo. *Sesiones guardadas antes del cambio no
   tienen token: cerrar sesión y volver a entrar una vez.*
2. **Contabilidad → botones REINICIAR / SEMILLAR**: ahora piden sesión de
   administrador. Sin token muestran "Autenticación requerida" (antes cualquiera
   en internet podía borrar la BD llamando el endpoint a mano).
3. **Módulos (feature flags)**: ahora **funcionan de verdad**. Los IDs del panel
   apuntaban a módulos inexistentes (`control-tower` vs `tower`), así que ninguna
   regla hacía nada; se corrigieron y se borraron los 7 flags muertos de la BD.
   Activar/desactivar Contabilidad, Control Tower o RRHH tiene efecto inmediato.
   Los errores del panel ahora se muestran (antes fallaban en silencio).
4. **Libro Diario**: cada transacción aparece **una sola vez** (antes: asientos
   duplicados con códigos PUC distintos). El resumen financiero ahora incluye
   los asientos Zero-COA (ingresos/gastos que antes eran invisibles). Editar
   una celda numérica con texto inválido se rechaza con aviso (antes guardaba
   0.0 en silencio).
5. **RRHH → AJUSTES → Estructura Organizacional**: el árbol ahora se **indenta
   por nivel** (antes se veía plano aunque hubiera jerarquía).
6. **RRHH → EQUIPO**: el deep-link `?member=<id>` sobrevive recargas para
   cualquier tipo de id.
7. **RRHH → CALENDARIO**: el toggle "◈ TAREAS" ahora carga tareas reales por
   proyecto y las pinta por fecha de vencimiento (antes era un botón muerto).
8. **RRHH → perfil → SALARIO**: nuevo toggle "HISTORIAL" en el header que
   muestra el historial de pagos (el panel existía pero era inalcanzable).
9. **Control Tower**: pulsar home deja el breadcrumb limpio (antes un glitch
   `···`); un colaborador con permisos corruptos ya no rompe la lista.
10. **Adjuntar evidencia**: solo imágenes/PDF; el archivo se guarda con nombre
    saneado (`a1b2c3d4_nombre.png`). Un `.py` o un nombre con `../` se rechaza
    con mensaje claro.
11. **Estabilidad general**: el backend ya no se degrada con el uso (fugas de
    pool eliminadas) — menos "se puso lento, toca reiniciar".

## Migraciones aplicadas a la BD (idempotentes, re-correr es seguro)

`migrate_hub_optional_login` · `migrate_hr_profile_fields(+v2)` ·
`migrate_ct_bcrypt` (no-op: ya estaba en bcrypt) · `migrate_kernel_integrity`.

## Operación

- **Deploy**: Dokploy (`finsys-app`). El webhook GitHub→Dokploy NO existe
  (DT-10): tras `git push origin master` hay que disparar deploy a mano
  (panel :3000 o `POST /api/compose.deploy`).
- **Producción verificada** (2026-07-26): build nuevo sirviendo, `/reset` sin
  token → 401, login real → 200 + token, upload `.py` → 400.
- **Recomendado en Dokploy → Environment**: `SESSION_SECRET` (firma de tokens)
  y `CORS_ORIGINS=http://159.223.156.50:8080`.

## Verificación reproducible

```bash
python -m kernel.test_kernel        # 5/5 — kernel contable
cd frontend && npx vitest run       # 45/45 — frontend
npx vite build                      # build limpio
```
