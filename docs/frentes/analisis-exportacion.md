# Frente: analisis-exportacion
Estado: ACTIVO · Actualizado: 2026-10-05 · Rama/commit: claude/project-status-review-5e1694 (sobre origin/master 01c5a36; SIN push)

## Objetivo
Cerrar el último escalón del plan "Mejor que Excel" (B5): submódulo desplegable 📦 EXPORTACIÓN dentro de ∑ Análisis
(spec `docs/specs/13-analisis/13.5-submodulo-exportacion.md`, APROBADO 05-oct con las 5 decisiones de §10). Termina con
13.5 HECHO, desplegado y visto en el navegador.

## Estado actual
- 13.4 motor EN PRODUCCIÓN (`bf03177`). Falta que Andrés abra un libro en Excel (CA-134-01).
- 13.5-a backend HECHO (`066d6bc` + `426e95f`): migración `scripts/migrate_exports.py` APLICADA en la BD compartida el
  05-oct (OK de Andrés; 4 tablas + 7 tipos default + secuencia de folios). 47 tests puros (CI) + 2 de integración opt-in
  (`FINSYS_TEST_BD_ESCRIBE=1`) verdes. Huella verificada en solo lectura = motor en 5 alcances.
- 13.5-b organizador web HECHO (`8a082eb`): `frontend/src/analisis/exportacion/` (ExportacionPanel, Organizador,
  FolderCard, FileCard, PreviewModal, UploadModal, TiposModal, Dialogos, api.js, organizador.js + 22 vitest), montado con
  1 import + 1 línea en `AnalisisApp.jsx`. Chunk propio `Organizador-*.js` 46 KB; carga inicial 298 KB. Verificado en el
  navegador (:8003) por verificador-visual: LISTO (A–K). Datos de prueba BORRADOS; la secuencia de folios quedó en 0001.
- "📥 NUEVA EXPORTACIÓN" y la vista 🗓 están DESHABILITADOS (llegan en 13.5-c y 13.5-d).
- Pendiente de push: todo lo de esta rama (Andrés: `git push origin claude/project-status-review-5e1694:master`).

## Próximo paso (concreto) — 13.5-c nueva exportación
1. `analisis/exportacion/{paquetes,periodos}.js` (+ vitest): paquetes predefinidos desde `GET /api/analytics/export/paquetes`,
   períodos relativos (este mes, mes anterior —ojo 1 de enero—, trimestre, año corrido, rango).
2. `NuevaExportacion.jsx`: modo período (empresa, período, paquete u hojas, filtros finos) con pre-vuelo
   (`POST /api/analytics/export/preflight`) → `POST /api/analytics/export` → `api.descargar(id)`; modo transacciones con
   `SelectorTransacciones.jsx`. Habilitar el botón en `Organizador.jsx`.
3. `contabilidad-v2/components/SeleccionExportarBar.jsx` + casillas en `LibroDiario.jsx:105-110` (la casilla no expande
   ni edita la fila: CA-135-09).
4. 13.5-d: `CalendarioCierres.jsx` (`GET /api/accounting-files/cierres`) y habilitar 🗓.

## Decisiones tomadas (y por qué)
- Archivos en Postgres bytea: el bucket `hr-docs` es PÚBLICO. Retención 90 días para lo generado no fijado.
- Folio `EXP-AAAA-NNNN` por SECUENCIA global (no por año): una purga nunca reutiliza un número. Puede tener huecos si
  una generación falla tras pedirlo.
- La huella se toma ANTES de leer los datos (falsa alarma ⚠ antes que falsa tranquilidad ✅).
- Carpetas automáticas = filtros que bajan (empresa → año → mes muestran TODO lo de debajo); propias = directas.
- `ExportacionPanel` va estático en AnalisisApp (dentro de su barrera de errores); lo perezoso es `Organizador.jsx`.
- Tipos documentales con `clave` estable para los default (el nombre se puede cambiar).

## Archivos clave
- Backend: `fin_sys_core/accounting_files_driver.py` · `routers/accounting_files.py` · `scripts/migrate_exports.py`
- Web: `frontend/src/analisis/exportacion/` · `AnalisisApp.jsx` (al final, `<ExportacionPanel/>`)
- Docs: `docs/database_schema.md` (tablas V–Y) · `docs/api_spec.md` §10

## Cómo verificar
- `python -m unittest tests.test_accounting_files` (47) · `npx vitest run src/analisis` (22) · `npm run build`
- Servidor del WORKTREE: config `finsys-13-5` en `.claude/launch.json` (local, no commitear) → :8003 con lanzador del
  scratchpad que carga el `.env` del principal. Sesión de prueba local "Verificador 13.5" (rol owner, 2 h) sembrada por
  script; lo creado por "Verificador 13.5" se borra con el script de limpieza y la secuencia vuelve a 0001 si queda vacía.

## Bloqueos y riesgos
- BD compartida: lo que se genere en local aparece en producción cuando se despliegue (los folios también).
- `launch.json` del worktree tiene arreglos solo locales: no commitear.
