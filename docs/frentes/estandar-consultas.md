# Frente: estándar de consultas escalables (todo FIN-SYS)

**Estado:** ACTIVO — H1 HECHO y commiteado (16-oct-2026), **sin push ni deploy**.
**Rama:** `claude/servidores-libro-mayor-9e4614` (worktree `affectionate-mestorf-f204bc`),
junto con los commits del Diario (frente `libro-diario-filtros`, que es H0).

## Objetivo
Que ninguna pantalla cueste según el tamaño del holding sino según lo que pide
el usuario, y que nada espere sin tope. Plan completo y las 41 reglas (B1–B14,
F1–F12, P1–P15): `docs/estandar-consultas-escalables.md`. Investigación previa:
`docs/filtros-contables-gran-escala.md`.

## H1 hecho (medir y blindar sin tocar drivers)
- `scripts/probar_set_local.py`: **SET LOCAL statement_timeout SÍ funciona por :6543**
  y no se filtra a la transacción siguiente → los timeouts no necesitan roles nuevos.
- Valores reales (16-oct): Postgres **17.6**, `max_connections` **60** (= cómputo
  **Micro**, CPU compartida), la app entra como `postgres` (timeout 2 min),
  `anon` 3 s, `authenticated` 8 s; el pooler NO deja pasar `application_name`.
- `shared/admision.py`: cuotas por usuario (10 lect/s, ráfaga 30) y tope de pesadas
  (2 por usuario, 4 por worker). `FINSYS_ADMISION=registrar` por defecto (solo
  log `[admision] habría rechazado`); `activo` → 429 + Retry-After; falla abierto.
- `routers/salud.py`: `/api/health/vida` (sin BD; Docker ahora mira esta) y
  `/api/health/profundo`; `/api/health` igual que antes pero con caché de 10 s.
- `FINSYS_DDL_ARRANQUE=0` salta el DDL de arranque (por defecto sigue activo).
- Diario: `SET LOCAL statement_timeout` 5 s / 3 s → 503 + Retry-After.
- **Sesión obligatoria** en GET que respondían sin ella: RRHH (¡salario y pagos!),
  Hub, `inventory/movements`, `tags`, `custom-taxes`, `portfolios`;
  `module-flags/admin` → admin. `/api/module-flags` sigue público (main.jsx antes del login).
- Laboratorio de carga `scripts/carga/` (Postgres 17 + PgBouncer en Docker, holding
  sintético, escenarios con escalones). **No corrido: no hay Docker en este PC.**

## Próximo paso
1. Andrés: `scripts\publicar.cmd` (Diario + H1). Sondas: `/api/health/vida` 200,
   `/api/portfolios` sin token 401, `/api/health` con `db: connected`.
2. Andrés: instalar Docker Desktop y correr el laboratorio (`scripts/carga/README.md`).
3. Tras ~1 semana en `registrar`: revisar logs `[admision]` y decidir `activo`.
4. Siguiente hito: **H2** (pool que espera: semáforo con timeout en `db_pool.py`,
   sin conexiones directas de respaldo, threadpool 16). Requiere revisión de Andrés.

## Decisiones
- Con 60 conexiones (Micro), el presupuesto P1 es ajustado: 2 workers × (10 + 5
  de respaldo) + bot ya puede llegar a ~45. Subir de cómputo antes que de pool.
- `FINSYS_DDL_ARRANQUE` queda en 1 hasta confirmar que las migraciones cubren el esquema.

## Cómo verificar
- `python -m unittest tests.test_estandar_h1` (14, sin BD) y
  `tests.test_diario_filtros` (con BD, solo lectura).
- Error preexistente sin BD: `tests/test_coa_fix.py` (conecta al importar).
