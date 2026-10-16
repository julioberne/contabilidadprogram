# Laboratorio de carga local (estándar de consultas, hito H1)

La BD de Supabase es **la misma** en local y en producción: las pruebas de carga
se hacen **solo** aquí, contra un Postgres 17 local con PgBouncer en modo
transacción (imita el pooler `:6543`). Los scripts se niegan a correr contra un
host que no sea `localhost` (`_seguro.py`).

Requiere Docker Desktop. Comandos para PowerShell, desde la raíz del repo:

```powershell
docker compose -f scripts/carga/docker-compose.carga.yml up -d
.venv\Scripts\python.exe scripts\carga\escenarios.py --solo-esquema
.venv\Scripts\python.exe scripts\carga\generar_holding.py --escala chica
.venv\Scripts\python.exe scripts\carga\escenarios.py --escalones 5,20,60,120 --segundos 20
docker compose -f scripts/carga/docker-compose.carga.yml down -v
```

- `--escala chica | media | grande`: ~60 mil, ~1 millón o ~3 millones de
  transacciones; la empresa 000 es la "ballena".
- `--admision activo` prueba los 429 del control de admisión; por defecto
  `registrar` (solo deja `[admision] habría rechazado …` en el log).
- El resultado queda en `scripts/carga/resultado_carga.json` (no se versiona).

Qué mirar: por escalón, el goodput (OK/s) debe crecer y luego quedarse **plano**,
no caer a cero; los p95 de `diario_busqueda` y `panel` por debajo de 300 ms; y
cero `-1` (timeouts) o 500 en las escrituras. `terceros_catalogo` y
`analisis_dataset` descargan todo: son los que más se espera que se degraden
(hitos H3 y H6 del plan).
