# Frente: estándar de consultas escalables (todo FIN-SYS)

**Estado:** ACTIVO — H0-H8 en producción (master `fb5d0ce`). **H9.1 backend hecho, sin publicar ni migrar**
(3-nov-2026). Rama `claude/servidores-libro-mayor-9e4614`. Incidente del trigger H7 (30-oct → 3-nov, TX caídas):
`docs/checkpoints.md` → «Checkpoint 2026-11-03».

## Objetivo
Que ninguna pantalla cueste según el tamaño del holding sino según lo que pide el usuario, y que nada espere sin
tope. Plan H0–H9 y 41 reglas: `docs/estandar-consultas-escalables.md` (§6). Runbook: `docs/escalamiento.md`.

## H9 aprobado por Andrés (3-nov) — orden H9.1 → H9.2 → H9.3; H9.4 pospuesto
- **H9.1 alcance por empresa.** Backend HECHO: `shared/alcance.py` (dependencia de la app en `server.py`),
  `routers/alcance.py` (`GET /api/alcance/yo`, `GET|PUT /api/alcance/usuarios[/{id}]`, solo dueño),
  `scripts/migrate_h9_alcance.py` (tabla nueva `usuario_empresas`), `GET /api/portfolios` filtrado,
  `tests/test_alcance_h9.py` (en el CI). Tokens de `health_check.py`/`session_maintenance.py`/`test_e2e` → su.
- **Falta de H9.1:** pantalla para asignar empresas (gestión de usuarios del Hub, casillas por empresa); la web de
  un no-dueño debe elegir empresa (sin consolidado); bot y Mini App: empresa del chat y «Empresa:» solo suyas
  (`bot_driver.py`, `bot_chat_links.default_portfolio`); probar con un usuario de prueba en el navegador.
- **H9.2:** reintento de GET ante 429/503 con `Retry-After` en `frontend/src/shell/installAuthFetch.js` (hoy solo
  `shared/operaciones.js` reintenta); luego Andrés pone `FINSYS_ADMISION=activo`.
- **H9.3:** quitar/proteger `hr.py:136,141` (públicos, NOT_IMPLEMENTED); revisar `/uploads` sin sesión
  (`server.py:84`) y proponer enlaces firmados aparte; Andrés desactiva las 3 cuentas de prueba con login.
- **H9.4 roles de BD: pospuesto.** `SET LOCAL` ya da topes por consulta; Supavisor abre un pool por usuario de BD
  (3 roles ≈ triple de conexiones en una BD de 60). Retomar al necesitar atribución por proceso o al subir de plan.

## Próximo paso
1. **Andrés:** `python scripts/migrate_h9_alcance.py --dry-run` y luego sin `--dry-run`; publicar con
   `scripts\publicar.cmd` (con deploy: cambia el backend). Para el dueño nada cambia; sin la tabla, los demás no ven
   ninguna empresa (falla cerrado).
2. Seguir con lo que falta de H9.1 (arriba). Luego H9.2 y H9.3.
3. **Andrés:** ✅ a los 17 borradores (ya en BORRADOR) y `tareas` en `FINSYS_EN_COLA`; después revisar
   `saldos_foto_meta.tomada` y la primera fila de `idempotency_keys` con `transaction_id`.

## Decisiones (y porqué)
- H9.1: dueño y su ven todo; admin, contador y miembro solo lo asignado (Andrés, 3-nov). Terceros, etiquetas e
  impuestos siguen compartidos. **Negado por defecto** para no-dueños: ruta sin clasificar en `alcance.RUTAS` → 403,
  así una ruta nueva no filtra empresas por olvido. La membresía va en BD con caché de 60 s, no en el token (dura 7
  días). Para un no-dueño «todas» no existe: elige empresa. Registro por id → resolvedor (`alcance.RESOLVERES`).
- Escalar workers solo según el observatorio: idea para cuando haya tráfico (el techo son las 60 conexiones de la
  BD, no el worker); primero, que el observatorio avise en el tablero al cruzar un disparador de `escalamiento.md`.
- Pruebas contra la BD compartida solo lectura; escrituras solo en filas `test-` que se limpian. La suite carga el
  `.env` (`tests/__init__.py`): todo fallo simulado debe parchear `bot_anomalias.registrar`/`_anotar_perdido`.
- Triggers en `transactions`: su test debe escribir en `transactions` (INSERT/DELETE + `SET CONSTRAINTS ALL
  IMMEDIATE` + ROLLBACK). Antes de una función o trigger, leer los tipos reales en `information_schema`.
- `Idempotency-Key` opcional para no romper pestañas abiertas. Editar en lote sigue siendo un PUT por fila (deuda).
- Cuentas 2, 11 y 12 no cuadran con sus movimientos: son los saldos reales que ingresa Andrés. No tocar.
- Deuda con permiso: drivers que tragan errores (9 casos), índice/retención de `bot_messages` (~96k recorridos).

## Cómo verificar
Python del checkout principal. Con BD: `wt.py` en el scratchpad de la sesión (carga el `.env` principal):
`python -m unittest tests.test_alcance_h9 tests.test_escritura_h8` (solo lectura / filas `test-h8-*`). Sin BD: la
lista de `.github/workflows/ci.yml` (776 OK) y `python scripts/laboratorio/auditoria_codigo.py`. Humo de H9.1:
TestClient sobre `server.app` con token owner (ve 8 empresas) y contador sin empresas (403 / lista vacía).
