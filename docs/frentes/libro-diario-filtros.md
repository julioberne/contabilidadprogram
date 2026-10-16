# Frente: búsqueda y filtros del Libro Diario (Módulo 02)

**Estado:** ACTIVO — hito 1 **EN PRODUCCIÓN** (`e0f6925`, 16-oct-2026; `/api/diario/opciones` sin token → 401).
Commits: `1fa64a7` fix Mayor, `a2ffccb` backend, `9bb1ec5` frontend. Falta la prueba a mano en la web.
**Rama:** `claude/servidores-libro-mayor-9e4614` (worktree `affectionate-mestorf-f204bc`).

## Objetivo
Pedido de Andrés (16-oct): barra de búsqueda + filtros completos en la tabla
"Módulo 02: Libro Diario Inteligente" (él la llamó "libro mayor"), filtros en el
SERVIDOR (la tabla carga de 50 en 50) y los extras propuestos.

## Hecho (commits)
- `bd11bb5` fix: Libro Mayor (Contadores) sin `desde` sumaba todo dos veces
  (saldo inicial = todos los movimientos). Ahora sin `desde` no hay saldo anterior.
- `3c5d66d` backend: `GET /api/diario/movimientos` y `GET /api/diario/opciones`
  (`fin_sys_core/diario_query.py`, `routers/diario.py`, `include_router` en server.py).
- `b58ad65` frontend: barra, panel, chips, URL, subtotales clicables, vistas
  guardadas (localStorage `finsys_diario_vistas`), CSV de todo lo filtrado,
  "Marcar N", edición en lote (etiqueta / cuenta COA vía PUT admin),
  avisos ⚠ DUP y ⚠ sin NIT, enlace 📘 al Libro Mayor (`/contadores?tab=reportes&rep=mayor&cuenta=&empresa=`).

## Próximo paso
1. Andrés: probar en la web la barra, los filtros y el enlace 📘 al Libro Mayor (Negocio A).
2. Hecho: sonda `/api/diario/opciones` sin token → 401 (16-oct).
3. Ideas en espera (no pedidas aún): editar en lote más campos (tercero, cuenta),
   duplicados con criterio más fino, vistas guardadas compartidas (en BD).

## Decisiones
- Endpoint propio (zero-impact): `/api/dashboard-data` no se tocó; el Diario ya
  no usa sus `transactions`, solo los KPIs (sin filtros el encabezado sigue
  mostrando la caja viva).
- La tabla se recarga sola cuando cambia `cajaViva`/`totalTxCount` (alta, edición, borrado).
- "Proyecto" = etiqueta (las TX no tienen campo de proyecto).
- Posible duplicado = misma empresa + fecha + tipo + valor neto + cuenta; solo aviso.
- Búsqueda sin tildes con `translate()` (no depende de la extensión unaccent); `%`/`_` literales.
- El enlace al Mayor solo aparece si la categoría empieza por un código PUC
  (hoy las de Negocio A son texto: "Alimentación"… → no sale).

## Archivos clave
`fin_sys_core/diario_query.py` · `routers/diario.py` ·
`frontend/src/contabilidad-v2/modules/diario/` (`DiarioModule`, `DiarioFiltrosBar`,
`DiarioGrupos`, `AccionesLote`, `useDiarioFiltrado`, `diarioFiltros.js`) ·
`frontend/src/contadores/ContadoresApp.jsx`, `tabs/ReportesTab.jsx` · `kernel/kernel_reports.py`

## Cómo verificar
- `python -m unittest tests.test_diario_filtros` (20 con BD, solo lectura) y
  `npx vitest run src/contabilidad-v2/modules/diario --pool=threads` (18; sin `--pool=threads` el worker se cuelga en este worktree).
- Local: backend del worktree en **:8003** (lanzador en el scratchpad que carga el
  `.env` principal; :8000 es el build congelado de main). Los datos están en
  **Negocio A** = `/contabilidad/20-finanzas-personales-julian`; Constructora Blu (22) tiene 0 TX.
- Ej.: `?q=café&tipos=GASTO&orden=monto_desc&agrupar=tercero` → 4 resultados, $119.500.
