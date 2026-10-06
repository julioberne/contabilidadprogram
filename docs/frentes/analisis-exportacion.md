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
- 13.6-a/b + nginx `/c/` EN PRODUCCIÓN y funcionando (Andrés lo confirmó el 06-oct; origin/master = `86c66b5`).
1. 13.6-c 📈 seguimiento (`b49e15f`), 13.6-d ⬇ PDF (`92983f1`, fpdf2+pypdf en requirements) y 13.6-e 💾 HTML
   offline (`a7ede78`) HECHOS, sin push. Andrés: publicar + `migrate_compendios.py` (tabla de eventos) + en Dokploy
   `COMPENDIO_AVISO_TELEGRAM=1`. Pendiente E2E: modal de seguimiento con datos, HTML en modo avión en un celular.
2. 13.5-d 🗓 cierres HECHO (`CalendarioCierres.jsx` + `cierres.js`; botón 🗓 del organizador habilitado).
3. 📦 Compendio de entrega en ZIP HECHO (`entrega_driver.py`, ☑ ELEGIR en el organizador).
4. Luego: motor 13.4 (comparativo, patrimonio, flujos, certificación; ¿Grupo 2 o 3?); 13.5-d 🗓.
- Andrés: generar el 1.er libro .xlsx real (CA-134-01, CA-135-08).

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
- Producción tiene nginx delante (`frontend/nginx.conf`): solo `/api/`, `/uploads/` y `/c/` (desde `90a6a73`) van al
  backend. Toda ruta nueva del backend fuera de `/api/` necesita su `location` ahí; :8003 no lo detecta.
