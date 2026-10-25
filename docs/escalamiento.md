# Runbook de escalamiento de FIN-SYS

Cuándo y cómo crecer sin adivinar. Complementa el estándar de consultas
(`docs/estandar-consultas-escalables.md`) y el laboratorio (`scripts/laboratorio/`).
Valores medidos el 16-oct-2026 con `scripts/probar_set_local.py` y el laboratorio.

## 1. Cómo está hoy

| Pieza | Valor | Fuente |
|---|---|---|
| Supabase | Postgres 17.6, **Micro** (CPU compartida), `max_connections` 60, ~200 clientes del pooler | `SHOW max_connections`; docs de Supabase |
| Canal | Pooler en modo transacción `:6543` (`SET LOCAL statement_timeout` funciona; `SET` de sesión no) | `probar_set_local.py` |
| API | gunicorn, `GUNICORN_WORKERS=2`, pool **10 caliente** por worker (`DB_POOL_MIN = DB_POOL_MAX`) | `Dockerfile`, `docker-compose.yml` |
| Bot | proceso aparte, pool 2-10 (procesa en serie) | `docker-compose.yml` |
| Worker (H5) | proceso aparte, pool 3, `FINSYS_WORKER_HILOS=2`: la cola pgmq `trabajos` (hoy, la exportación .xlsx) | `docker-compose.yml`, `fin_sys_core/worker.py` |
| Desarrollo local | **la misma BD**, pool 10 | `.env` |

**Clientes del pooler** (lo que pone `docker-compose.yml`): 2 workers × 10 + bot ≤ 10 + worker 3 + dev 10 = **≤ 43 de ~200**.
**Conexiones del servidor**: en modo transacción, una conexión ociosa del pool NO ocupa una conexión
de Postgres; el techo real lo da el *pool size* de Supavisor del proyecto (verlo en el panel de
Supabase → Database → Connection pooling) y las 60 de `max_connections` (menos ~15 de servicios de Supabase).

## 2. Cómo se comporta el pool (hito H2)

- Cada préstamo toma un **turno** (tantos como `DB_POOL_MAX`). Sin turno, espera hasta
  `DB_POOL_ESPERA_S` (1 s). Si no llega, o ya hay `DB_POOL_MAX_ESPERA` (2×pool) peticiones en fila,
  la petición responde **503 + `Retry-After: 2`** al instante.
- **Nunca** abre conexiones directas extra cuando el pool está lleno (antes: sonda de 4 s + TLS
  directas en pleno pico). El failover de canal `:6543 → :5432` sigue igual.
- Si una petición sufrió saturación, el middleware devuelve 503 **aunque el endpoint dijera 200**:
  varios drivers se tragan el error y devuelven `[]` o datos de ejemplo (deuda registrada en la
  auditoría, regla `error-tragado-vacio`).
- **Pool caliente**: psycopg2 cierra al devolver toda conexión por encima de `minconn` y abre las
  nuevas dentro de su candado. Con `min=2`, 10 consultas simultáneas tardaban **4,5 s**; con
  `min=max`, **0,34 s**. 40 simultáneas: de 14,8 s con 30 respuestas falsas → 0,84 s (30 OK + 10 × 503).
- Métricas en `GET /api/health/profundo` → `pool.espera`: `prestamos`, `esperas`, `rechazos`,
  `esperando`, `p95_ms`, `max_ms`, `turnos_libres`.

## 3. Disparadores → acción

| Señal (sostenida 15 min) | Dónde se ve | Acción |
|---|---|---|
| `espera.p95_ms` > 100 ms y CPU de la BD < 50 % | `/api/health/profundo`, panel de Supabase | Subir `DB_POOL_MAX` o `GUNICORN_WORKERS` **dentro del presupuesto** (§4) |
| `rechazos` > 1 % de `prestamos`, o 503 frecuentes | `/api/health/profundo`, logs `[admision]` | Primero el laboratorio, criterio 4: una consulta lenta retiene conexiones. Luego el punto anterior |
| CPU de la BD > 70 % o presupuesto de IO agotado | Panel de Supabase → Reports | **Subir cómputo** (§4). En Micro/Small/Medium la CPU es compartida |
| Conexiones abiertas > 70 % de `max_connections` | Laboratorio, criterio 3 | Bajar pools ociosos (bot, dev) o subir cómputo |
| Pausa global en el laboratorio (varias peticiones lentas a la vez) | Laboratorio, criterio 2 | Repetir; si se repite: red, pooler o región. Considerar región São Paulo para Colombia |
| Análisis/reportes > 20 % del tiempo de la BD | `pg_stat_statements` (observatorio) | H6 (dataset acotado) y después **réplica de lectura** (cuesta como el primario) |
| Una empresa > 5 M de transacciones | Observatorio, tablas | Particionar `transactions` por año (migración) + resúmenes de meses cerrados (H7) |
| Muchos holdings grandes o > 50 M de filas | — | Celdas: un despliegue y una BD por grupo de clientes |

## 4. Presupuesto por escalón de Supabase

Regla: `workers × DB_POOL_MAX + bot + dev ≤ 80 % de los clientes del pooler`, y el *pool size* de
Supavisor ≤ 80 % de (`max_connections` − ~15 de servicios). `DB_POOL_MIN = DB_POOL_MAX`.

| Cómputo | max_connections / clientes | Precio aprox. (USD/mes) | `GUNICORN_WORKERS` | `DB_POOL_MAX` | Bot |
|---|---|---|---|---|---|
| Micro (hoy) | 60 / 200 | ~10 | 2 | 10 | 2-10 |
| Small | 90 / 400 | ~15 | 2-3 | 10 | 2-10 |
| Medium | 120 / 600 | ~60 | 3 | 12 | 2-10 |
| **Large** (2 vCPU dedicadas) | 160 / 800 | ~110 | 4 | 15 | 2-10 |
| XL y más | ver tabla de Supabase | 210+ | según vCPU del VPS | 15-20 | 2-10 |

Los workers también dependen del VPS: `workers ≈ min(2×vCPU+1, presupuesto)`. Precios y límites:
página *Compute and Disk* de Supabase (revisarla al subir; cambian).

## 5. Variables (Dokploy → Environment)

| Variable | Defecto | Para qué |
|---|---|---|
| `DB_POOL_MAX` / `DB_POOL_MIN` | 10 / 10 | Tamaño del pool por proceso (mantener iguales) |
| `DB_POOL_ESPERA_S` | 1.0 | Cuánto espera una petición su turno |
| `DB_POOL_MAX_ESPERA` | 2 × pool | Tope de la fila de espera |
| `DB_FALLBACK_SI_AGOTADO` | 0 | `1` = comportamiento anterior (conexiones directas al agotarse). Solo como reversa |
| `FINSYS_ADMISION` | registrar | `activo` → 429 por cuotas por usuario; `apagado` |
| `FINSYS_HILOS` | (40 de Starlette) | No bajar hasta que lo lento sin BD vaya a la cola (H5); luego 16-20 |
| `FINSYS_DDL_ARRANQUE` | 1 | `0` cuando las migraciones cubran el esquema (evita `ALTER` en cada reciclaje) |
| `GUNICORN_WORKERS` | 2 | Procesos de la API |
| `FINSYS_COLA` | trabajos_prueba | Cola pgmq que usan la API y el worker; `trabajos` solo en docker-compose |
| `FINSYS_EN_COLA` | (vacía) | Qué va por la cola: `exportacion,entrega,diario_csv,bot` (`bot` = voz, IA y /analisis del bot, H5.4; solo con el worker healthy) → 202 y lo arma el worker (encender tras `migrate_operaciones.py`). `FINSYS_EXPORT_EN_COLA=1` sigue valiendo como `exportacion` |
| `FINSYS_WORKER_HILOS` | 2 | Trabajos a la vez en el worker. Subir si la edad del más viejo (`/api/health/profundo` → `cola`) pasa de 60 s |
| `FINSYS_WORKER_PRODUCCION` | — | `1` solo en el worker de Dokploy: sin ella un worker se niega a tomar la cola de producción |
| `TG_POR_CHAT_S` / `TG_GLOBAL_POR_S` | 1.25 / 15 | Ritmo de envíos a Telegram por proceso (bot y worker: entre los dos < 30/s); 429 y 5xx se reintentan |
| `DIARIO_SIMULTANEAS` | 3 | Consultas del Diario a la vez por worker de la API (H4); la siguiente espera 2 s → 503 |

**Puente de emergencia `:5432`** (modo sesión, límite ~15 clientes compartido): `DB_PORT=5432`,
`FINSYS_ALLOW_5432=1`, `DB_POOL_MAX=3`, `DB_POOL_MIN=2`, `GUNICORN_WORKERS=2`, y apagar el dev local.
Con el pool caliente de 10 el puente se saturaría al instante.

## 6. Cómo medir antes y después de cada cambio

```powershell
.venv\Scripts\python.exe scripts\laboratorio\laboratorio.py                 # auditoría + BD + proyección
$env:LAB_TOKEN = "<token>"; .venv\Scripts\python.exe scripts\laboratorio\laboratorio.py --carga --url https://finsys-andres.duckdns.org
curl.exe -s https://finsys-andres.duckdns.org/api/health/profundo
```
Comparar el informe nuevo con el anterior (`docs/laboratorio/historial.jsonl`). Un cambio de escalón
se da por bueno si el p95 interactivo neto baja y no aparecen rechazos ni pausas globales.
