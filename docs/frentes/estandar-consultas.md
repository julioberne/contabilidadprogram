# Frente: estándar de consultas escalables (todo FIN-SYS)

**Estado:** ACTIVO — H0-H8 en producción y migrados (master `0f41849`, 3-nov-2026). H8 verificado contra la BD y en
pantalla. Sin publicar: `91ef4ef`, `20a298f` y el commit de este frente (solo tests y docs: `publicar.cmd --sin-deploy`).
Rama `claude/servidores-libro-mayor-9e4614`. **Sigue H9.**

## Objetivo
Que ninguna pantalla cueste según el tamaño del holding sino según lo que pide el usuario, y que nada espere sin
tope. Plan H0–H9 y 41 reglas (B/F/P): `docs/estandar-consultas-escalables.md` (§6 hitos). Runbook:
`docs/escalamiento.md`. Laboratorio: `scripts/laboratorio/README.md` (trinquete en el CI).

## Hecho (en producción)
- H0-H7: Diario con filtros en servidor, timeouts y admisión, pool caliente con turno, búsqueda top-N y trigram,
  cola pgmq + worker (`FINSYS_EN_COLA`), bot sin carril único, tareas al worker, Mayor por páginas, panel por versión
  y fotos de saldo.
- H8.0 `7dee08f`: demora del aviso Mini App → chat en `payload.aviso_demora_s`; la lee `observatorio_bd.py`.
- H8.1 `97126aa`: `fin_sys_core/incremental_balance.py` (Decimal al centavo, cuentas en orden de id,
  `reemplazar_delta_incremental`); saldo lo último antes del commit (`database_driver.py`, `registrar_transaccion`
  y `eliminar_transaccion`); genérico solo se lee; triggers del panel al commit (`scripts/migrate_h8.py`).
- H8.2 `1cf22c5`: `fin_sys_core/idempotencia.py`; `Idempotency-Key` opcional en `POST /api/transactions`
  (otra huella → 422); `confirmar_draft` (`bot_driver.py`) suelta la conexión antes de registrar y usa `draft:<id>`.
- H8.3 `9042041`: «Marcar todo» por filtro (`modules/diario/seleccion.js`, `LibroDiario.jsx`); filas al actuar con
  `GET /api/diario/seleccion` (7 columnas, tope 20.000).

## Próximo paso
1. **H9** (roles, alcance por empresa, cuotas activas), con plan previo para aprobación de Andrés. Leer: doc §6 fila H9
   y fila S1 de la tabla de riesgos; `routers/auth_guard.py` (≈49-102), `shared/admision.py`, `fin_sys_core/db_pool.py`.
   Toca BD (roles Postgres + tabla nueva de membresía usuario↔empresa): migración la corre Andrés. Criterio del doc:
   `pg_stat_activity` por rol y 403 entre empresas. Va antes de dar acceso a un segundo usuario del holding.
2. **Andrés:** agregar `tareas` a `FINSYS_EN_COLA` con el worker healthy (apagado al 3-nov). Luego revisar
   `saldos_foto_meta.tomada` (primer `tomar_foto` real) y el p95 del aviso en el observatorio (meta ≤ 10 s).
3. **Revisar:** la primera TX real tras H8 debe dejar su fila en `idempotency_keys` con `transaction_id` lleno.
4. **Andrés (opcional):** borrar los 7 `envio_perdido` falsos (ids 62, 64, 66, 72, 75, 94, 96, detalle
   «sendPhoto: RuntimeError: sin red»): los dejaba `tests/test_bot_analisis`, corregido en `91ef4ef`.

## Decisiones (y porqué)
- Pruebas contra la BD compartida solo lectura; escrituras solo en filas `test-` que se limpian. La suite carga el
  `.env` (`tests/__init__.py`): todo fallo simulado debe parchear `bot_anomalias.registrar`/`_anotar_perdido`.
- B11 (montos como texto) descartado: numeric(15,2) cabe exacto en un número JSON; basta sumar en BD o Decimal.
- Triggers del panel `DEFERRABLE INITIALLY DEFERRED`: H7 bloqueaba empresa y fila 0 durante el asiento.
  `panel_hija_cambio` salta si la madre ya no existe (orden empresa → 0). `migrate_h8.py --deshacer` vuelve atrás.
- `Idempotency-Key` opcional para no romper pestañas abiertas; puede volverse obligatoria.
- Editar en lote sigue siendo un PUT por fila (`AccionesLote.jsx`): `category` reemite asientos; llevarlo al servidor
  pide la cola. Deuda, no hecho.
- Cuentas 2, 11 y 12 no cuadran con sus movimientos: son los saldos reales que ingresa Andrés. No tocar.
- Deuda con permiso: drivers que tragan errores (9 casos), índice/retención de `bot_messages` (~96k recorridos).

## Cómo verificar
Python del checkout principal. Con BD: `wt.py` del scratchpad anterior (carga el `.env` principal):
`python -m unittest tests.test_escritura_h8 tests.test_idempotencia tests.test_diario_filtros` (incluye los 200 pares
A→B/B→A y la carrera de claves; escriben solo `test-h8-*`). Sin BD: la lista de `.github/workflows/ci.yml` y
`python scripts/laboratorio/auditoria_codigo.py`. En `frontend/`: `npx vitest run --pool=threads`.
Backend del worktree: `preview_start finsys-wt` (:8003, origen nuevo: pide login).
