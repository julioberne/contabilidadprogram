# Frente: estándar de consultas escalables (todo FIN-SYS)

**Estado:** ACTIVO — H0-H3 HECHOS y verificados (16-oct-2026). **Nada publicado.**
**Rama:** `claude/servidores-libro-mayor-9e4614` (worktree `affectionate-mestorf-f204bc`), **19 commits sin push**
desde `d87c1fe` (incluye el Diario, frente `libro-diario-filtros` = H0).

## Objetivo
Que ninguna pantalla cueste según el tamaño del holding sino según lo que pide el usuario, y que
nada espere sin tope. Plan H0–H9 y 41 reglas (B/F/P): `docs/estandar-consultas-escalables.md`.
Runbook de escalamiento: `docs/escalamiento.md`. Laboratorio: `scripts/laboratorio/README.md`.

## Hecho (sin push)
- **H0** Diario con filtros en servidor (`/api/diario/*`) + fix del Libro Mayor (sin `desde` duplicaba saldo).
- **H1** `SET LOCAL statement_timeout` SÍ funciona por :6543; admisión por usuario en `registrar`
  (`shared/admision.py`); `/api/health/vida` (Docker) y `/profundo`; sesión obligatoria en GET
  abiertos (RRHH salario/pagos, Hub, tags, portafolios…); `FINSYS_DDL_ARRANQUE=0` opcional.
- **Laboratorio** `scripts/laboratorio/` + agente `.claude/agents/laboratorio-rendimiento.md`: 6 criterios,
  informe en `docs/laboratorio/`, trinquete en el CI (`scripts/laboratorio/linea_base.json`).
- **H2** pool que espera su turno (1 s, fila 2×pool → 503 + Retry-After) y **caliente**
  (`DB_POOL_MIN = DB_POOL_MAX`): psycopg2 cerraba lo que pasaba de min=2 y reconectaba en fila
  (10 simultáneas 4,5 s → 0,34 s). Con saturación responde 503 aunque el endpoint diga 200.
- **H3** `GET /api/buscar/terceros|cuentas|etiquetas` (top-N + `mas`; `ids`/`ident`/`nombre` exacto;
  listado por cursor `orden=nombre&despues_nombre&despues_id`). Web y Mini App ya **no descargan**
  `/third-parties` (registro, TercerosTab paginada, CarteraTab, EvidenceModal, ThirdPartyModal, Mini App,
  refresco de 60 s). Hooks en `frontend/src/shared/busqueda/useBusqueda.js`.

## Próximo paso
1. **Andrés:** revisar el diff de `fin_sys_core/db_pool.py` y publicar con `scripts\publicar.cmd`.
   Sondas: `/api/health/vida` 200; `/api/portfolios` sin token 401; `/api/health/profundo` →
   `pool.minconn` 10 y `pool.espera`; probar la Mini App en el celular y TercerosTab en la web.
2. **Siguiente sesión (cierre de H3):** el bot con `buscar_terceros` — "terceros recientes" hace
   GROUP BY sobre todas las TX (`fin_sys_core/bot_driver.py:943-952`) y los botones de cuentas/empresas/
   etiquetas cortan en LIMIT 14/12/10. Hito propio, con `tests/test_bot_*.py`.
3. **Decisión pendiente de Andrés:** los widgets de colegio
   (`frontend/src/contabilidad-v2/modules/registro/widgets/{Pensiones,Recaudos,Uniformes}Widget.jsx`)
   tratan a TODO tercero como estudiante → ¿etiqueta o tipo para marcar estudiantes? Son los 3
   catálogos completos que quedan en la auditoría.
4. Después: Diario plan A (duplicados solo para la página, montos Decimal), H5 cola+worker, H6 fin de
   las descargas de todas las TX (7 casos), plan B (índice trigram, migración de Andrés).

## Decisiones (y porqué)
- Pruebas contra la BD compartida SOLO LECTURA y acotadas (Andrés lo autorizó); volumen grande en un
  proyecto Supabase aparte (`scripts/carga --lab-env`): la BD es la de producción.
- `FINSYS_HILOS` no se baja hasta H5 (IA, voz y PDF necesitan hilos sin BD).
- Deuda registrada que necesita permiso: drivers que tragan errores y devuelven `[]` (9 casos en
  `database_driver.py`/`control_tower_driver.py`); índice/retención de `bot_messages`
  (~95.700 recorridos completos con 1.081 filas).

## Datos medidos (16-oct)
Supabase **Micro**: Postgres 17.6, `max_connections` 60, CPU compartida; la app entra como `postgres`.
Desde el PC local cada viaje a la BD cuesta ~180 ms y abrir el pool caliente ~16 s: no es producción.

## Cómo verificar
`python -m unittest tests.test_busqueda tests.test_pool_espera tests.test_estandar_h1 tests.test_laboratorio
tests.test_diario_filtros` · `python scripts/laboratorio/auditoria_codigo.py` · en `frontend/`:
`npx vitest run --pool=threads` (sin esa opción el worker se cuelga en el worktree) ·
`python scripts/laboratorio/laboratorio.py` (informe). Error preexistente sin BD: `tests/test_coa_fix.py`.
