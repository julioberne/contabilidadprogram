# Frente: estándar de consultas escalables (todo FIN-SYS)

**Estado:** ACTIVO — H0-H8 en producción y migrados (master `0f41849`, 3-nov-2026; `migrate_h8.py` aplicado).
Sin publicar: `91ef4ef` (solo tests). Rama `claude/servidores-libro-mayor-9e4614`. Sigue H9.

## Objetivo
Que ninguna pantalla cueste según el tamaño del holding sino según lo que pide el usuario, y que
nada espere sin tope. Plan H0–H9 y 41 reglas (B/F/P): `docs/estandar-consultas-escalables.md` (§6 hitos).
Runbook de escalamiento: `docs/escalamiento.md`. Laboratorio: `scripts/laboratorio/README.md`.

## H8 (en producción)
- **H8.0 `7dee08f`** La marca de la Mini App guarda la hora y queda `aviso_demora_s` en el borrador;
  `observatorio_bd.py` reporta n, p50, p95 y máximo (meta p95 ≤ 10 s). Sin datos hasta publicar.
- **H8.1 `97126aa`** `incremental_balance`: `Decimal` al centavo, cuentas en orden de id,
  `reemplazar_delta_incremental` para editar. Saldo lo último antes del commit, al crear y al borrar.
  Genérico solo se lee (53 de 120 TX lo usan). `SN-` con uuid. `scripts/migrate_h8.py`.
- **H8.2 `1cf22c5`** `fin_sys_core/idempotencia.py`: la clave entra en la misma transacción de BD.
  `Idempotency-Key` opcional en `POST /api/transactions` (otra huella → 422). `confirmar_draft` suelta su
  conexión antes de registrar y usa `draft:<id>`. La limpieza horaria borra claves de más de 7 días.
- **H8.3 `9042041`** «Marcar todo» por filtro: marcar no baja filas; `GET /api/diario/seleccion` (7 columnas,
  tope 20.000) se pide al exportar o editar en lote. Más de 20.000: avisa y no marca a medias.

## Próximo paso
1. **Ver «Marcar todo» en pantalla** (único pendiente de H8): Andrés inicia sesión en el navegador integrado (en prod
   ya está desplegado). Flujo: marcar sin petición de filas, desmarcar una, Exportar (solo abrir el modal), Limpiar,
   cambiar filtro. Solo lectura.
2. **Hecho 3-nov tras migrar:** `TestCarreraReal`, `TestTriggersAlCommit` y los 200 pares pasan contra la BD; huella
   igual. La primera TX real con clave debe dejar `idempotency_keys.transaction_id` lleno: revisar.
3. **Andrés:** agregar `tareas` a `FINSYS_EN_COLA` con el worker healthy (sigue apagado al 3-nov: foto nunca tomada,
   0 avisos medidos). Luego: `saldos_foto_meta.tomada` y el p95 del observatorio.
4. **Bitácora:** 7 `envio_perdido` falsos (ids 62-96, «sendPhoto: RuntimeError: sin red») venían de
   `tests/test_bot_analisis` (corregido en `91ef4ef`). Los borra Andrés con SQL; siguen saliendo hasta publicar.
5. **H9** roles, alcance por empresa y cuotas: arrancar con plan previo en sesión limpia (doc §6, fila H9).

## Decisiones (y porqué)
- Pruebas contra la BD compartida SOLO LECTURA y acotadas; escrituras solo en filas `test-` que se limpian.
- B11 (montos como texto) se descarta: numeric(15,2) cabe exacto en un número JSON; lo que importa es sumar en BD
  o `Decimal`. Cambiarlo obligaría a tocar todo el frontend.
- La demora de la Mini App no va en H9: era el tick detrás del long-poll de 45 s.
- Los triggers del panel pasan a commit (`DEFERRABLE INITIALLY DEFERRED`): H7 bloqueaba empresa y fila 0 durante el
  asiento. `panel_hija_cambio` salta si la madre ya no existe, para conservar el orden empresa → 0.
- `Idempotency-Key` opcional para no romper pestañas abiertas; se puede volver obligatoria luego.
- Editar en lote sigue siendo un PUT por fila desde el navegador (porque `category` reemite asientos): llevarlo al
  servidor pide la cola. Queda como deuda; no se hizo en H8.3.
- Deuda con permiso: drivers que tragan errores (9 casos), índice/retención de `bot_messages` (~96k recorridos).

## Evidencia de H8 (30-oct, solo lectura salvo cuentas `test-h8-*`)
Fórmula vieja vs nueva en las 107 TX con cuenta: 0 diferencias (todas COP: la conversión USD solo está en tests). 200 pares
A→B/B→A: 0 interbloqueos y saldos exactos, dos corridas; la fórmula vieja dio 14 interbloqueos en 10 pares (de ahí que
`pg_stat_database.deadlocks` marque 14). Huella de cuentas, TX, asientos y terceros idéntica antes y después.
Cuentas 2, 11 y 12 no cuadran con sus movimientos: ya venía así, son los saldos reales que ingresa Andrés.

## Cómo verificar
Python del checkout principal; con BD (solo lectura) vía el `wt.py` del scratchpad anterior, que carga el
`.env` principal. `python -m unittest tests.test_escritura_h8 tests.test_idempotencia tests.test_diario_filtros
tests.test_bot_confirmation` · `python scripts/laboratorio/auditoria_codigo.py` · en `frontend/`:
`npx vitest run --pool=threads` · backend del worktree en :8003 (`finsys-wt`).
