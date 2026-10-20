# Frente: estándar de consultas escalables (todo FIN-SYS)

**Estado:** ACTIVO — H0-H3 (con el cierre del bot) **EN PRODUCCIÓN** (`191b340`, 16-oct-2026).
**En producción** (20-oct): H4, Plan B (código), webhook SMS y H5.1-H5.2 (`5a94172`). **Sin publicar:**
`7835511` (las migraciones encuentran el `.env` desde el worktree) y **H5.3 `c7d8d72`**. **Sin migrar:** Plan B y H5
(los dos scripts fallaron el 19-oct por el `.env`; ya corregido). Rama `claude/servidores-libro-mayor-9e4614`.
Orden acordado: uno por uno en esta rama → **H5.4** (bot) → H5.5 → H6 → H7 → H8 (H8 con permiso para
`database_driver.py`, plan previo).

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
1. **Andrés:** correr `..\..\..\.venv\Scripts\python.exe scripts\migrate_trgm_busqueda.py --concurrently --explain` y
   `...\migrate_operaciones.py` (deben decir "✅ Conectado a …supabase.com:6543"; Supabase → Queues sin PostgREST);
   publicar `c7d8d72` con `scripts\publicar.cmd`.
2. **Claude:** con la migración, `tests.test_cola` con BD (ciclo en `trabajos_prueba`) y revisar `/api/health/profundo` → `cola`.
3. **Andrés:** `FINSYS_EN_COLA=exportacion,entrega,diario_csv` en Dokploy → probar exportación, 📦 entrega y CSV
   grande del Diario (más de 2.000 filas; con orden que no es por fecha sale por fecha y se avisa).
4. **H5.4 bot**: voz/IA/foto al worker y envíos a Telegram con límite y retry_after (plan previo; `bot_telegram.py`
   nunca se lanza en local). **H5.5**: tareas periódicas al worker + purga de `operaciones` (>30 días).

## Decisiones (y porqué)
- Pruebas contra la BD compartida SOLO LECTURA y acotadas; carga de día solo con OK explícito de Andrés.
- `FINSYS_HILOS` no se baja hasta H5 (IA, voz y PDF necesitan hilos sin BD).
- Deuda con permiso: drivers que tragan errores (9 casos), índice/retención de `bot_messages` (~96k recorridos).

## Cómo verificar
Python del checkout principal; con BD (solo lectura) vía el `wt.py` del scratchpad anterior, que carga el
`.env` principal. `python -m unittest tests.test_diario_filtros tests.test_busqueda tests.test_bot_listas
tests.test_laboratorio tests.test_pool_espera tests.test_estandar_h1` · `python scripts/laboratorio/auditoria_codigo.py`
· en `frontend/`: `npx vitest run --pool=threads` · backend del worktree en :8003 (`localhost:8003` tiene la sesión).
