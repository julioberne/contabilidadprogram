# Frente: analisis-exportacion (hoy módulo 14 ⇩ Exportación)
Estado: ACTIVO · Actualizado: 2026-10-06 · Rama/commit: claude/project-status-review-5e1694 = origin/master 0e2dda2 (+ este frente)

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
- Docs al día: spec 13.5 v1.2, SPEC 13, índice de specs, CHECKLIST (fila 14), AGENTS.md, api_spec §10, reglas_proyecto (Regla 2).
- "📥 NUEVA EXPORTACIÓN" y la vista 🗓 están DESHABILITADOS (llegan en 13.5-c y 13.5-d).
- **EN PRODUCCIÓN** desde el 06-oct 01:04 (deploy de `df1047f` con las funciones de `publicar`): rutas del organizador y
  `PUT /api/tags/0` 404→401, `/exportacion` sirve `ExportacionApp-Cf7bNf5p.js` (= :8000). `:8000` al día (sync de Andrés).
  Sin push: `bb04826` (`scripts/publicar`) + frentes. La 1.ª vez `publicar.cmd` se corre en el worktree (la principal aún no lo tiene).

## Próximo paso (concreto)
- 13.5-c web EN PRODUCCIÓN (06-oct 01:42, `0e2dda2`, con `publicar` de punta a punta; :8000 al día): franja 📥 en `ExportacionApp`, `NuevaExportacion.jsx` (📚 período: paquete →
  empresa → período con atajos → libros en 3 grupos → avanzado plegado + ★ guardar paquete; 🧾 transacciones con
  `SelectorTransacciones.jsx`), `periodos.js` + `paquetes.js` (+10 vitest), paquetes `revisor_fiscal` e `iva_bimestral`
  en el driver. Verificado en :8003 hasta el pre-vuelo (A–J LISTO); GENERAR no se probó en E2E para no gastar folio:
  la PRIMERA generación real la hace Andrés (será EXP-2026-0001).
1. Andrés: generar un libro real y abrirlo en Excel (CA-134-01 + E2E de GENERAR).
2. Casillas en `LibroDiario.jsx:105-110` + `SeleccionExportarBar.jsx` que abre NuevaExportacion en modo transacciones
   con la selección (CA-135-08/09).
3. Compendio de entrega: elegir varios archivos del organizador → ZIP con índice y folio propio (backend nuevo).
4. Motor 13.4 (imprescindible según la investigación): comparativo, cambios en el patrimonio, flujos de efectivo,
   bloque de certificación (Ley 222 art. 37) y folio inicial. Preguntar a Andrés: ¿Grupo 2 o Grupo 3?
5. 13.5-d: `CalendarioCierres.jsx` (`GET /api/accounting-files/cierres`) y habilitar 🗓.

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
