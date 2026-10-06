# Frente: analisis-exportacion (hoy módulo 14 ⇩ Exportación)
Estado: ACTIVO · Actualizado: 2026-10-06 · Rama: claude/project-status-review-5e1694 = origin/master 0e2dda2 + 622025d (frente) + 50617b5 (casillas) + docs 13.6

## Objetivo
B5 de "Mejor que Excel": ⇩ EXPORTACIÓN, organizador contable (spec `docs/specs/13-analisis/13.5-submodulo-exportacion.md`)
y su extensión 13.6 🤝 Compendio para el cliente (`13.6-compendio-cliente.md`, PROPUESTA).

## Estado actual
- 13.4 motor, 13.5-a/b (organizador) y módulo 14 propio EN PRODUCCIÓN. 13.5-c 📥 Nueva exportación EN PRODUCCIÓN
  (06-oct 01:42, `0e2dda2`). GENERAR no se ha probado en E2E: la 1.ª generación real la hace Andrés (EXP-2026-0001).
- **Casillas del Libro Diario HECHAS (`50617b5`, sin push):** columna de casillas + "todas las visibles" (indeterminada)
  en `LibroDiario.jsx`, solo para roles del módulo 14 (`getRenderableModules`); `SeleccionExportarBar.jsx` (sticky abajo,
  fuera de la tarjeta por su overflow-hidden; ING/GAS por moneda con valor neto como la carátula) → 📥 abre ahí mismo
  `exportacion/ExportarSeleccion.jsx` (puerta del módulo 14: lazy + portal; carga paquetes, carpetas, empresas) →
  `NuevaExportacion` en 🧾 con `inicial.txIds` y "solo marcadas". +7 vitest (130 total), build OK.
  Navegador :8003 A–J LISTO (#57, #56, #45 → modal con esas 3; pre-vuelo n_txs=3 cuadra; 375 px sin scroll horizontal).
  CA-135-09 ✅; CA-135-08 🟡 (falta GENERAR).
- 13.6 spec escrita (06-oct): link temporal `/c/<token>` + ⬇ PDF (fpdf2 + pypdf) + 💾 HTML offline; vigencia elegida
  cada vez (7/15/30/90, 15 preseleccionado). Espera las 4 decisiones de §10.

## Próximo paso (concreto)
1. Andrés: `scripts\publicar.cmd` (sube 622025d + 50617b5 + docs) y generar un libro real (CA-134-01 + E2E de GENERAR).
2. Andrés: responder §10 de la spec 13.6 (comprobantes en vivo, NIT/CC visible, sin asientos, orden) → aprobar.
3. 13.6-a backend + visor (migración `accounting_compendios`, `compendio_driver.py`, `routers/compendios.py`,
   plantilla `/c/{token}` antes del catch-all de `server.py`, proxy de comprobantes por índice, tests) → 13.6-b web
   → 13.6-c PDF → 13.6-d HTML offline.
4. Pendientes que siguen en cola (orden por decidir con 13.6): compendio ZIP del organizador; motor 13.4 (comparativo,
   patrimonio, flujos, certificación Ley 222 art. 37; preguntar ¿Grupo 2 o 3?); 13.5-d `CalendarioCierres.jsx` 🗓.

## Decisiones tomadas (y por qué)
- Módulo 14 propio (06-oct): carpeta + 1 entrada en el registry, sin tocar Análisis ni el shell. Icono ⇩. Solo .jsx/.js.
- Exportar desde el Libro Diario abre el modal AHÍ MISMO (Andrés 06-oct); Contabilidad importa solo la puerta
  `ExportarSeleccion.jsx` en diferido (chunk de 0,9 KB + el de Exportación).
- Se exporta lo marcado que está CARGADO (un id de otra empresa no cuenta): lo que se ve es lo que se exporta.
- Para el cliente final (Andrés 06-oct): link temporal + PDF, y probar HTML offline; vigencia elegida cada vez.
- Archivos en Postgres bytea (bucket `hr-docs` PÚBLICO); folio `EXP-AAAA-NNNN` por secuencia global; huella antes de leer.

## Archivos clave
- Web: `frontend/src/exportacion/` · `contabilidad-v2/modules/diario/{LibroDiario.jsx,seleccion.js}` ·
  `contabilidad-v2/components/SeleccionExportarBar.jsx`
- Backend: `fin_sys_core/{accounting_files_driver,export_xlsx}.py` · `routers/accounting_files.py`
- Evidencias: `transactions.evidence_file_path` + `transaction_evidences.file_path` (URLs públicas del bucket,
  `fin_sys_core/storage_media.py`); ubicación `geo_maps_link` + lat/lng.

## Cómo verificar
- `npx vitest run src/exportacion src/contabilidad-v2/modules/diario` · `npm run build` · `python -m unittest tests.test_accounting_files`
- :8003 (config `finsys-13-5`, lanzador en el scratchpad 7a9ac386 con el `.env` del principal). Sesión de prueba:
  `sembrar_13_5.py --solo-sesion` (no escribe en la BD) → `sesion_13_5.json` → localStorage `finsys_session`.

## Bloqueos y riesgos
- BD compartida: lo generado en local aparece en producción (folios incluidos). No pulsar GENERAR en pruebas.
- `launch.json` del worktree tiene arreglos solo locales: no commitear.
