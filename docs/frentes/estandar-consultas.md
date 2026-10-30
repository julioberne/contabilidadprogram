# Frente: estándar de consultas escalables (todo FIN-SYS)

**Estado:** ACTIVO — H0-H3 (con el cierre del bot) **EN PRODUCCIÓN** (`191b340`, 16-oct-2026).
**En producción** (20-oct): H4, Plan B, webhook SMS, H5.1-H5.3 (`341cbfe`). H5.4 y H5.5 en producción (master al 27-oct). **Migrado** (20-oct): pg_trgm + 3
índices trigram; pgmq 1.5.1, colas `trabajos`/`trabajos_prueba`, tabla `operaciones`. Ciclo de la cola verificado
contra la BD (`tests.test_cola`, 3/3) y `/api/health/profundo` → `cola.activa: true`. Rama
`claude/servidores-libro-mayor-9e4614`. Orden acordado: **H5.4** (bot) → H5.5 → H6 → H7 → H8 (H8 con permiso
para `database_driver.py`, plan previo).

## Objetivo
Que ninguna pantalla cueste según el tamaño del holding sino según lo que pide el usuario, y que
nada espere sin tope. Plan H0–H9 y 41 reglas (B/F/P): `docs/estandar-consultas-escalables.md` (§6 hitos).
Runbook de escalamiento: `docs/escalamiento.md`. Laboratorio: `scripts/laboratorio/README.md`.

## En producción
- **H0** Diario con filtros en servidor (`/api/diario/*`) + fix del Libro Mayor.
- **H1** `SET LOCAL statement_timeout` por :6543; admisión en `registrar`; `/api/health/vida` y `/profundo`;
  sesión obligatoria en los GET abiertos; `FINSYS_DDL_ARRANQUE=0` opcional.
- **H2** pool que espera su turno (1 s, fila 2×pool → 503) y caliente (`DB_POOL_MIN = DB_POOL_MAX` = 10).
- **H3** `/api/buscar/*` top-N; web y Mini App sin catálogo de terceros; uso de terceros acotado a las
  últimas 2.000 TX (`VENTANA_USO`); bot con «Cuenta:»/«Empresa:», recientes acotados, listas que avisan.
- **Laboratorio** (`scripts/laboratorio/`, trinquete en el CI). Informe 15:50 (local): p95 a 5 usuarios
  1,2-1,9 s → 0,3-0,55 s; 0 % errores; proyección 500k TX/empresa ~11 usuarios (cuello: Diario por tercero).

## Hecho, sin publicar
- **H4 `43bf674`** Diario: duplicado fila por fila solo para la página (antes ventana sobre TODAS las TX);
  `filtradas MATERIALIZED` (una lectura para página+totales+grupos); `totales=false` + cursor
  `despues_fecha/despues_id` en orden por fecha (`siguiente`); OFFSET ≤ 2.000; búsqueda 1/2/3+ letras
  con `aviso`; opciones top-50 + `mas` + `campo&q`; cupo `DIARIO_SIMULTANEAS`=3 → 503. El índice
  `idx_tx_portfolio_date` ya existía en la BD. Verificado: 26 tests con BD, vitest, build, navegador.
- **Plan B `586fb51`** `scripts/migrate_trgm_busqueda.py` (pg_trgm + 3 GIN en third_parties con las
  expresiones de `busqueda.py`); en `busqueda.py`, 2 letras = inicio de palabra, «contiene» desde 3.
- Fuera de H4 a propósito: «Marcar todo» y el CSV (tope 5.000) → H5.3 (CSV a la cola) y H8 (lote en el
  servidor); montos como string → H6/H8.
- **H5.1-H5.2 `ab44f49`** (Andrés eligió pgmq para la cola; `operaciones` solo estado):
  `fin_sys_core/cola.py`, `worker.py` (+`worker_jobs.py`), `routers/operaciones.py`, servicio `worker`
  en compose, `cola` en `/api/health/profundo`; exportación .xlsx en la cola con `FINSYS_EXPORT_EN_COLA=1`
  (sin bandera o sin migración, síncrona). Seguridad: cola por defecto `trabajos_prueba`; un worker sin
  `FINSYS_WORKER_PRODUCCION=1` se niega a tomar `trabajos`. **`215ea23`** webhook SMS ya no frena la API.
- Hallazgos del relevamiento (19-oct) para H5.3-H5.5: el bot procesa todo en serie (`bot_telegram.py:325`;
  una voz o la IA frena a todos los chats), sin manejo de 429/retry_after (la respuesta se pierde), SMS
  con hasta 45 s de espera; la voz web deja el audio en `./uploads` sin borrarlo (`transactions.py:313`);
  la entrega ZIP retiene una conexión mientras arma (`entrega_driver.py:141-156`).

## Próximo paso
0. **H6 y H7 en producción y migrados** (30-oct: `idx_journal_pf_cuenta_fecha` y tablas H7 existen).
   `saldos_foto_meta` sigue sin foto y `operaciones` vacía: `tareas` no está activa en el worker.
1. **Andrés:** agregar `tareas` a `FINSYS_EN_COLA` con el worker healthy. Baja el aviso de la Mini App de hasta
   45 s a ≤ 5 s (hoy es tick del poller, detrás del long-poll). Verificar: `saldos_foto_meta.tomada` se llena
   (primer `tomar_foto` real). Medido: 44 avisos, 3 medibles, mediana 8,8 s, máx. 28,8 s. No va en H9.
2. **H8** plan propuesto el 30-oct, esperando aprobación de líneas de `database_driver.py`, migración y prueba con BD:
   H8.0 sello y demora del aviso + lectura en el laboratorio; H8.1 saldos al final en orden de id, `Decimal`
   a 2 decimales, genérico sin UPDATE, triggers del panel diferidos; H8.2 `idempotency_keys` y bot con una
   conexión; H8.3 «Marcar todo» por filtro. B11 (montos como texto) se descarta: numeric(15,2) cabe exacto.
3. **Deuda de H7 que arregla H8.1:** `panel_subir` bloquea la empresa desde el INSERT y la fila 0 desde el
   saldo hasta el commit; crear (empresa→0) y borrar (0→empresa) pueden interbloquearse. Leído en el código,
   no medido; hoy 120 TX y 0 deadlocks. 53 de 120 TX usan el tercero genérico.

## Decisiones (y porqué)
- Pruebas contra la BD compartida SOLO LECTURA y acotadas; carga de día solo con OK explícito de Andrés.
- `FINSYS_HILOS` no se baja hasta H5 (IA, voz y PDF necesitan hilos sin BD).
- Deuda con permiso: drivers que tragan errores (9 casos), índice/retención de `bot_messages` (~96k recorridos).

## Cómo verificar
Python del checkout principal; con BD (solo lectura) vía el `wt.py` del scratchpad anterior, que carga el
`.env` principal. `python -m unittest tests.test_diario_filtros tests.test_busqueda tests.test_bot_listas
tests.test_laboratorio tests.test_pool_espera tests.test_estandar_h1` · `python scripts/laboratorio/auditoria_codigo.py`
· en `frontend/`: `npx vitest run --pool=threads` · backend del worktree en :8003 (`localhost:8003` tiene la sesión).
