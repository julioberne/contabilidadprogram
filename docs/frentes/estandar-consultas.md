# Frente: estándar de consultas escalables (todo FIN-SYS)

**Estado:** ACTIVO — H1, **laboratorio** y **H2** HECHOS y commiteados (16-oct-2026), **sin push ni deploy**.
**Rama:** `claude/servidores-libro-mayor-9e4614` (worktree `affectionate-mestorf-f204bc`), junto con
el Diario (frente `libro-diario-filtros` = H0).

## Objetivo
Que ninguna pantalla cueste según el tamaño del holding sino según lo que pide el usuario, y que
nada espere sin tope. Plan y 41 reglas (B, F, P): `docs/estandar-consultas-escalables.md`.

## Hecho
- **H1:** `SET LOCAL statement_timeout` SÍ funciona por :6543 (no hacen falta roles para timeouts).
  BD real: Postgres 17.6, `max_connections` 60 (= **Micro**, CPU compartida), la app entra como
  `postgres`. Admisión `FINSYS_ADMISION=registrar`; `/api/health/vida` (Docker) y `/profundo`;
  `FINSYS_DDL_ARRANQUE=0` opcional; timeouts del Diario; sesión obligatoria en GET abiertos
  (RRHH salario/pagos, Hub, inventario, tags, tasas, portafolios).
- **Laboratorio** `scripts/laboratorio/` (README ahí) + agente `.claude/agents/laboratorio-rendimiento.md`:
  6 criterios + proyección, informe en `docs/laboratorio/`, trinquete de la auditoría en el CI
  (`linea_base.json`). Carga: solo GET, ≤20 usuarios, ≤60 s, freno p95/errores/pool, 21–07 h.
  Volumen grande: proyecto Supabase aparte con `--lab-env` (la guarda rechaza el usuario de prod).

- **H2 (21d9757):** el pool espera su turno (1 s, fila 2×pool) y si no, 503 + Retry-After; sin
  conexiones directas en el pico; **pool caliente** (`DB_POOL_MIN = DB_POOL_MAX`, también en
  docker-compose): psycopg2 cerraba lo que pasaba de min=2 y reconectaba en fila (10 simultáneas
  4,5 s → 0,34 s; 40 simultáneas 14,8 s → 0,84 s). Con saturación, 503 aunque el endpoint diga 200
  (`/api/portfolios` inventaba "Negocio A/B" ante un error). Runbook: `docs/escalamiento.md`.

## Primer informe (`docs/laboratorio/informe-2026-10-16-1351.md`, backend LOCAL)
- 🟡 `bot_messages`: ~95.700 recorridos completos vs 1.445 por índice → a una consulta del bot le
  falta índice y la tabla crece sin tope (revisar retención y el índice).
- 🟡 Auditoría: 19 patrones de gravedad alta (7 descargas de todas las TX, 10 catálogos de terceros
  completos, 2 dataset de Análisis) y 145 medios → deuda conocida; el trinquete impide que crezca.
- 🔴 Proyección a 500.000 TX/empresa: ~11 usuarios; cuello = Diario con grupos (recorre
  `transactions` 5 veces) → plan A del Diario.
- 🟡 Carga útil: dataset de Análisis pasa 200 KB desde ~50.000 TX; terceros desde ~5.000.
- Una **pausa global de ~10 s** (todas las peticiones a la vez, sonda de BD con timeout) en una
  corrida; no se repitió aislando el endpoint. Si reaparece: red, Supavisor o el vigía de `db_pool.py`.
- Latencias locales infladas (1 worker con recarga, ~180 ms de red): no representan producción.

## Próximo paso
1. Andrés: `scripts\publicar.cmd` (Diario + H1 + laboratorio). Sondas: `/api/health/vida` 200,
   `/api/portfolios` sin token 401.
2. Andrés, de noche: laboratorio contra producción con `LAB_TOKEN` (comando en el README) → cifras reales.
3. Andrés: revisar el diff de `fin_sys_core/db_pool.py` (infraestructura común) antes de publicar;
   tras publicar, mirar `/api/health/profundo` → `pool.minconn` 10 y `pool.espera`.
4. **H3**: búsqueda remota única (terceros, cuentas, etiquetas; Mini App primero).
5. Deuda con permiso: drivers que tragan errores y devuelven `[]` (9 casos, `database_driver.py`
   y `control_tower_driver.py`); índice/retención de `bot_messages`.

## Cómo verificar
`python -m unittest tests.test_laboratorio tests.test_estandar_h1` (sin BD) ·
`python scripts/laboratorio/auditoria_codigo.py` (trinquete) · error preexistente sin BD:
`tests/test_coa_fix.py`.
