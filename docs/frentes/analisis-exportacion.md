# Frente: analisis-exportacion (hoy módulo 14 ⇩ Exportación)
Estado: ACTIVO · Actualizado: 2026-10-06 · Rama: claude/project-status-review-5e1694 = origin/master 0e2dda2 + 7 commits sin push

## Objetivo
B5 de "Mejor que Excel": ⇩ EXPORTACIÓN (spec `docs/specs/13-analisis/13.5-submodulo-exportacion.md`) y su extensión
13.6 🤝 Compendio para el cliente (`13.6-compendio-cliente.md`, APROBADA 06-oct, EN CONSTRUCCIÓN).

## Estado actual
- 13.4 motor, 13.5-a/b/c y módulo 14 EN PRODUCCIÓN (`0e2dda2`). GENERAR sin E2E: 1.ª generación real = Andrés.
- Casillas del Libro Diario HECHAS (`50617b5`): `LibroDiario.jsx` + `SeleccionExportarBar.jsx` → `ExportarSeleccion.jsx`
  (lazy + portal) → NuevaExportacion 🧾 con los ids. CA-135-09 ✅, CA-135-08 🟡 (falta GENERAR).
- 13.6-a HECHO (`2809389`): `compendio_driver.py` (snapshot sin asientos, totales por moneda, NIT/ubicación opcionales,
  maps solo https Google; código = HMAC(clave, nonce), BD solo SHA-256; vigencia 7/15/30/90; ampliar/revocar; comprobantes
  EN VIVO como el botón [Ver], solo por índice y solo del bucket), `compendio_visor.py` + `templates/compendio_visor.{html,js}`
  (visor único, CSP con nonce), `routers/compendios.py` (privados contador; públicos `/c/{token}` y
  `/api/publico/compendio/{token}/soporte/{i}/{j}`; ritmo 120/min), `scripts/migrate_compendios.py`, 25 tests.
- 13.6-b HECHO (`7420b31`): ¿Para quién? 📊/🤝 en NuevaExportacion, `CompendioCliente.jsx`, `CompendiosPanel.jsx` (botón
  🔗 Compendios en la franja), `compendios.js` (+4 vitest). 134 vitest, build OK. Navegador :8003 A–G LISTO hasta la revisión.
- **La migración la bloqueó el clasificador ([Production Deploy]) → la corre Andrés.** Dry-run OK (tabla nueva, secuencia ok).

## Próximo paso (concreto)
1. Andrés: `.venv\Scripts\python.exe scripts\migrate_compendios.py` en el checkout principal o el worktree (1 tabla nueva) y
   luego `scripts\publicar.cmd` (sube 622025d…7420b31 + docs).
2. Andrés: crear el primer compendio real (marcar en el Libro Diario → 📥 → 🤝 Cliente) y abrir el link en el celular
   (CA-136-01/02). Ojo: gasta un folio EXP de la secuencia compartida (si es el primero, EXP-2026-0001).
3. 13.6-c PDF: `requirements.txt` + fpdf2 + pypdf, `fin_sys_core/compendio_pdf.py`, `GET …/pdf` privado y público,
   botón ⬇ PDF en el visor y en el panel (CA-136-05/07).
4. 13.6-d HTML offline: `compendio_offline.py` (mismo visor; `soporte.data` = data URI, fotos Pillow 1280 px q65) (CA-136-06).
5. Después, en este orden: compendio ZIP del organizador; motor 13.4 (comparativo, patrimonio, flujos, certificación;
   preguntar ¿Grupo 2 o 3?); 13.5-d `CalendarioCierres.jsx` 🗓.

## Decisiones tomadas (y por qué)
- Módulo 14 propio; exportar desde el Libro Diario abre el modal AHÍ MISMO; se exporta lo marcado que está cargado.
- 13.6 (Andrés 06-oct): link temporal + PDF + HTML offline; vigencia elegida cada vez; comprobantes en vivo; NIT visible con
  opción de ocultar; sin asientos; orden link → PDF → offline. Panel 🔗 en la franja (un compendio es un link, no un archivo).
- Archivos en Postgres bytea (bucket `hr-docs` PÚBLICO); folio `EXP-AAAA-NNNN` por secuencia global (libros y compendios).

## Archivos clave
- Web: `frontend/src/exportacion/` · `contabilidad-v2/modules/diario/{LibroDiario.jsx,seleccion.js}` · `contabilidad-v2/components/SeleccionExportarBar.jsx`
- Backend: `fin_sys_core/{accounting_files_driver,export_xlsx,compendio_driver,compendio_visor}.py` · `routers/{accounting_files,compendios}.py`
- Evidencias: `transactions.evidence_file_path` + `transaction_evidences.file_path` (URLs públicas, `storage_media.py`).

## Cómo verificar
- `python -m unittest tests.test_compendios tests.test_accounting_files` · `npx vitest run src/exportacion src/contabilidad-v2/modules/diario` · `npm run build`
- :8003 (config `finsys-13-5`; lanzador y `sembrar_13_5.py --solo-sesion` en el scratchpad 7a9ac386 → `sesion_13_5.json` →
  localStorage `finsys_session`). `/c/<43 letras>` sin tabla → 404 "ya no está disponible" con cabeceras.

## Bloqueos y riesgos
- BD compartida: crear un compendio o generar un libro gasta folio real. No pulsar CREAR/GENERAR en pruebas.
- `launch.json` del worktree tiene arreglos solo locales: no commitear.
