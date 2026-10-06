# Frente: analisis-exportacion (hoy módulo 14 ⇩ Exportación)
Estado: ACTIVO · Actualizado: 2026-10-06 · Rama/commit: claude/project-status-review-5e1694 (sobre origin/master df1047f; 1 commit SIN push)

## Objetivo
B5 de "Mejor que Excel": ⇩ EXPORTACIÓN, organizador contable (spec `docs/specs/13-analisis/13.5-submodulo-exportacion.md`,
APROBADO 05-oct, decisiones §10). Termina con 13.5 HECHO, desplegado y visto en el navegador.

## Estado actual
- 13.4 motor EN PRODUCCIÓN (`bf03177`). Falta que Andrés abra un libro en Excel (CA-134-01).
- 13.5-a backend HECHO (`066d6bc` + `426e95f`): migración `scripts/migrate_exports.py` APLICADA en la BD el 05-oct
  (4 tablas + 7 tipos + secuencia de folios). 47 tests puros + 2 opt-in (`FINSYS_TEST_BD_ESCRIBE=1`).
- 13.5-b organizador web HECHO (`8a082eb`): Organizador, FolderCard, FileCard, PreviewModal, UploadModal, TiposModal,
  Dialogos, api.js, organizador.js + 22 vitest. Verificado en :8003 (A–K LISTO); datos de prueba borrados, folios en 0001.
- 06-oct, pedido de Andrés: **módulo 14 propio** (no debajo de Análisis). Carpeta `frontend/src/exportacion/` (movida de
  `analisis/exportacion/`), página `ExportacionApp.jsx` (cabecera con resumen + organizador; reemplaza al desplegable
  `ExportacionPanel.jsx`), 1 entrada en el registry (⇩, FINANCIERO tras Análisis, ruta `/exportacion`, roles
  owner/admin/contador, lazy) + etiqueta en `ModuleSettingsPanel`. `AnalisisApp.jsx` y el shell (Sidebar, useRoute,
  main.jsx, shell.css) quedan como antes de 13.5-b: el sub-ítem del menú (`51e5702` + `d59eaa7`, ya en origin) se retiró.
  113 vitest + build OK; chunk `ExportacionApp-*.js` 56 KB; carga inicial 298 KB.
- Docs revisados: spec 13.5 v1.2 (D-135-05 = módulo 14), SPEC 13, `docs/specs/README.md`, CHECKLIST (fila 14), AGENTS.md
  (Estado de Módulos + permisos), `docs/api_spec.md` §10, `docs/reglas_proyecto.md` (Regla 2: navegación por el registry).
- "📥 NUEVA EXPORTACIÓN" y la vista 🗓 están DESHABILITADOS (llegan en 13.5-c y 13.5-d).
- origin/master = `df1047f` (push de Andrés 06-oct; CI verde): 13.5-a/b, módulo 14, etiquetas/tasas y auditoría PUC.
  Sin push: `bb04826` (`scripts/publicar`).
  Producción SIN deploy: `/api/accounting-files/cierres` y `/api/analytics/export/paquetes` daban 404.

## Próximo paso (concreto)
0. Andrés: `scripts\publicar.cmd` en la terminal de esta sesión (push + CI + deploy con sonda + `:8000`); primero
   `--sin-deploy` si prefiere ver `:8000` antes de producción. Sonda extra: `/exportacion` y `PUT /api/tags/0` sin token → 401.
1. 13.5-c: `exportacion/{paquetes,periodos}.js` (+ vitest): paquetes de `GET …/export/paquetes`; períodos relativos (ojo 1-ene).
2. `exportacion/NuevaExportacion.jsx`: modo período con pre-vuelo (`POST …/export/preflight`) → `POST /api/analytics/export`
   → `api.descargar(id)`; modo transacciones con `SelectorTransacciones.jsx`. Habilitar el botón en `Organizador.jsx`.
3. `contabilidad-v2/components/SeleccionExportarBar.jsx` + casillas en `LibroDiario.jsx:105-110` (CA-135-09).
4. 13.5-d: `CalendarioCierres.jsx` (`GET /api/accounting-files/cierres`) y habilitar 🗓.

## Decisiones tomadas (y por qué)
- Módulo 14 propio (06-oct): vista independiente como los demás; arquitectura modular = carpeta + 1 entrada en el
  registry, sin tocar Análisis ni el shell. Icono ⇩ (glifo monocromo, estilo brutalista de la barra). Solo `.jsx`/`.js`.
- Archivos en Postgres bytea: el bucket `hr-docs` es PÚBLICO. Retención 90 días para lo generado no fijado.
- Folio `EXP-AAAA-NNNN` por SECUENCIA global: una purga nunca reutiliza un número (puede tener huecos).
- La huella se toma ANTES de leer los datos (falsa alarma ⚠ antes que falsa tranquilidad ✅).
- Carpetas automáticas = filtros que bajan (empresa → año → mes); propias = directas. Tipos default con `clave` estable.

## Archivos clave
- Backend: `fin_sys_core/accounting_files_driver.py` · `routers/accounting_files.py` · `scripts/migrate_exports.py`
- Web: `frontend/src/exportacion/` (`ExportacionApp.jsx` entra por `registry/moduleRegistry.js`)
- Docs: `docs/database_schema.md` (tablas V–Y) · `docs/api_spec.md` §10

## Cómo verificar
- `python -m unittest tests.test_accounting_files` (47) · `npx vitest run src/exportacion` (22) · `npm run build`
- Worktree en :8003 (config `finsys-13-5`, lanzador del scratchpad con el `.env` del principal). Sesión de prueba
  "Verificador 13.5" (owner, 2 h): `sembrar_13_5.py --solo-sesion` no escribe en la BD; lo que cree se borra con `limpiar_13_5.py`.

## Bloqueos y riesgos
- BD compartida: lo que se genere en local aparece en producción cuando se despliegue (los folios también).
- `launch.json` del worktree tiene arreglos solo locales: no commitear.
