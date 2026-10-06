# Frente: analisis-exportacion
Estado: ACTIVO · Actualizado: 2026-10-06 · Rama/commit: claude/project-status-review-5e1694 (7 commits sobre origin/master a18613b; SIN push)

## Objetivo
B5 de "Mejor que Excel": 📦 EXPORTACIÓN dentro de ∑ Análisis (spec `docs/specs/13-analisis/13.5-submodulo-exportacion.md`,
APROBADO 05-oct, decisiones §10). Termina con 13.5 HECHO, desplegado y visto en el navegador.

## Estado actual
- 13.4 motor EN PRODUCCIÓN (`bf03177`). Falta que Andrés abra un libro en Excel (CA-134-01).
- 13.5-a backend HECHO (`066d6bc` + `426e95f`): migración `scripts/migrate_exports.py` APLICADA en la BD el 05-oct
  (4 tablas + 7 tipos + secuencia de folios). 47 tests puros + 2 opt-in (`FINSYS_TEST_BD_ESCRIBE=1`).
- 13.5-b organizador web HECHO (`8a082eb`): `frontend/src/analisis/exportacion/` (ExportacionPanel, Organizador,
  FolderCard, FileCard, PreviewModal, UploadModal, TiposModal, Dialogos, api.js, organizador.js + 22 vitest), montado con
  1 import + 1 línea en `AnalisisApp.jsx`. Chunk propio `Organizador-*.js` 46 KB; carga inicial 298 KB. Verificado en el
  navegador (:8003) por verificador-visual: LISTO (A–K). Datos de prueba BORRADOS; la secuencia de folios quedó en 0001.
- Menú lateral HECHO (`51e5702`, pedido de Andrés 06-oct): ∑ Análisis desplegable (▾/▸ recordado en localStorage)
  con el sub-ítem 📦 Exportación (roles owner/admin/contador) → `/analisis/exportacion` (antes `/analisis/archivo`,
  nunca desplegada). `navigate(view, {path})` + `EVENTO_RUTA`/`usePathname` en `shell/useRoute.js`. 4 vitest nuevos;
  verificado en :8003 por verificador-visual (A–J LISTO) + ajuste del resaltado con el sub-ítem plegado.
- "📥 NUEVA EXPORTACIÓN" y la vista 🗓 están DESHABILITADOS (llegan en 13.5-c y 13.5-d).
- 13.5-a/b ya están en origin/master (a18613b, push de Andrés) pero NO en producción: el 06-oct
  `/api/accounting-files/cierres` y `/api/analytics/export/paquetes` daban 404.
- Integrado en esta rama el 06-oct (pendientes de otras sesiones): PUT/DELETE de etiquetas y tasas (`e83314e` +
  frente `8a81a56` + nota CHECKLIST `bbab872`) y la auditoría posting_rules vs PUC (`7a764cb`, solo docs; SQL sin
  ejecutar). CI 365/365 + 113 vitest + build OK tras integrar.
- Pendiente (Andrés): push `git push origin claude/project-status-review-5e1694:master` → deploy (`scratch\deploy_prod.py`;
  sonda: las 2 rutas de arriba y `PUT /api/tags/0` sin token pasan a 401) → en el checkout principal
  `.venv\Scripts\python.exe scripts\sync_local.py` (el fast-forward del principal lo bloquea el clasificador).

## Próximo paso (concreto) — 13.5-c nueva exportación
1. `analisis/exportacion/{paquetes,periodos}.js` (+ vitest): paquetes de `GET …/export/paquetes`; períodos relativos (ojo 1-ene).
2. `NuevaExportacion.jsx`: modo período (empresa, período, paquete u hojas, filtros finos) con pre-vuelo
   (`POST /api/analytics/export/preflight`) → `POST /api/analytics/export` → `api.descargar(id)`; modo transacciones con
   `SelectorTransacciones.jsx`. Habilitar el botón en `Organizador.jsx`.
3. `contabilidad-v2/components/SeleccionExportarBar.jsx` + casillas en `LibroDiario.jsx:105-110` (CA-135-09).
4. 13.5-d: `CalendarioCierres.jsx` (`GET /api/accounting-files/cierres`) y habilitar 🗓.

## Decisiones tomadas (y por qué)
- Archivos en Postgres bytea: el bucket `hr-docs` es PÚBLICO. Retención 90 días para lo generado no fijado.
- Folio `EXP-AAAA-NNNN` por SECUENCIA global (no por año): una purga nunca reutiliza un número. Puede tener huecos si
  una generación falla tras pedirlo.
- La huella se toma ANTES de leer los datos (falsa alarma ⚠ antes que falsa tranquilidad ✅).
- Ruta `/analisis/exportacion` (decisión de Andrés 06-oct). El sub-ítem es sub-ruta del módulo, no módulo 14.
- Carpetas automáticas = filtros que bajan (empresa → año → mes muestran TODO lo de debajo); propias = directas.
- `ExportacionPanel` va estático en AnalisisApp (dentro de su barrera de errores); lo perezoso es `Organizador.jsx`.
- Tipos documentales con `clave` estable para los default (el nombre se puede cambiar).

## Archivos clave
- Backend: `fin_sys_core/accounting_files_driver.py` · `routers/accounting_files.py` · `scripts/migrate_exports.py`
- Web: `frontend/src/analisis/exportacion/` · `AnalisisApp.jsx` (al final, `<ExportacionPanel/>`) · menú:
  `registry/moduleRegistry.js` (`sub`), `shell/Sidebar.jsx`, `shell/useRoute.js`
- Docs: `docs/database_schema.md` (tablas V–Y) · `docs/api_spec.md` §10

## Cómo verificar
- `python -m unittest tests.test_accounting_files` (47) · `npx vitest run src/analisis` (22) · `npm run build`
- Worktree en :8003 (config `finsys-13-5`, lanzador del scratchpad con el `.env` del principal). Sesión de prueba
  "Verificador 13.5" (owner, 2 h): `sembrar_13_5.py --solo-sesion` no escribe en la BD; lo que cree se borra con `limpiar_13_5.py`.

## Bloqueos y riesgos
- BD compartida: lo que se genere en local aparece en producción cuando se despliegue (los folios también).
- `launch.json` del worktree tiene arreglos solo locales: no commitear.
