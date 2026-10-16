# Frente: estándar de consultas escalables (todo FIN-SYS)

**Estado:** ACTIVO — H0-H3 (con el cierre del bot) **EN PRODUCCIÓN** (`191b340`, 16-oct-2026).
**H4 y Plan B hechos, sin publicar** (`43bf674`, `586fb51`). Rama `claude/servidores-libro-mayor-9e4614`
(worktree `affectionate-mestorf-f204bc`). Orden acordado con Andrés (16-oct): **uno por uno en esta
rama**: H4 → Plan B → **H5** → H6 → H7 → H8 (H8 con permiso para `database_driver.py`, plan previo).

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
- Fuera de H4 a propósito: «Marcar todo» y el CSV (tope 5.000) → H5 (CSV a la cola) y H8 (lote en el
  servidor); montos como string → H6/H8.

## Próximo paso
1. **Andrés:** `scripts\publicar.cmd` en la terminal de esta sesión (H4 + Plan B). Después, la migración:
   `.venv\Scripts\python.exe scripts\migrate_trgm_busqueda.py --dry-run` y luego `--concurrently --explain`.
2. **H5 cola y worker** (siguiente hito): plan antes de código → aprobación. Alcance en §6 del doc:
   pgmq (Supabase Queues; activar la extensión = Andrés) o PGQueuer; servicio `worker` en
   `docker-compose.yml`; 202 + `/api/operaciones`; pasar al worker .xlsx, compendio, PDF, voz, foto, IA,
   envíos de Telegram y tareas periódicas; el CSV del Diario como exportación en la cola.
   Ojo: `bot_telegram.py` nunca se lanza en local; colas de prueba `*_prueba`.
3. **Decisión pendiente de Andrés:** widgets de colegio (`registro/widgets/{Pensiones,Recaudos,Uniformes}Widget.jsx`)
   tratan a todo tercero como estudiante → ¿etiqueta o tipo? Son los 3 catálogos completos que quedan.
4. Medición real: laboratorio contra producción de noche con `LAB_TOKEN`; prueba de volumen en BD aparte.

## Decisiones (y porqué)
- Pruebas contra la BD compartida SOLO LECTURA y acotadas; carga de día solo con OK explícito de Andrés.
- `FINSYS_HILOS` no se baja hasta H5 (IA, voz y PDF necesitan hilos sin BD).
- Deuda con permiso: drivers que tragan errores (9 casos), índice/retención de `bot_messages` (~96k recorridos).

## Cómo verificar
Python del checkout principal; con BD (solo lectura) vía el `wt.py` del scratchpad anterior, que carga el
`.env` principal. `python -m unittest tests.test_diario_filtros tests.test_busqueda tests.test_bot_listas
tests.test_laboratorio tests.test_pool_espera tests.test_estandar_h1` · `python scripts/laboratorio/auditoria_codigo.py`
· en `frontend/`: `npx vitest run --pool=threads` · backend del worktree en :8003 (`localhost:8003` tiene la sesión).
