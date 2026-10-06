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
4. Motor 13.4 (06-oct): comparativo (`periodo_anterior|anio_anterior`), certificación Ley 222 art. 37 y folio inicial
   HECHOS (receta + UI en 📥: chips junto a los libros; folio en Avanzado) + hojas CAMBIOS EN EL PATRIMONIO y FLUJOS
   DE EFECTIVO (método indirecto por grupos PUC; cuadran con datos reales). En Completo; ¿Grupo 2 o 3? solo decide
   si se suman por defecto a Cierre de mes (Grupo 2 los exige).
- Andrés: generar el 1.er libro .xlsx real (CA-134-01, CA-135-08).

5. **Escalabilidad HECHA (06-oct, aprobada)**: gunicorn `--max-requests 1000 ±100 --graceful-timeout 30`; proxy de
   comprobantes ASÍNCRONO en streaming (`_flujo`, httpx.AsyncClient por worker; caché 1 h immutable); PDF/HTML con
   `compendio_cache.py` (disco compartido, TTL 1 h, 300 MB, semáforo 2/worker → 503 "intenta en un minuto");
   nginx `limit_req` (/c/ 60/min burst 20 · /api/publico/ 10/s burst 60) + `set_real_ip_from` (Traefik) y el
   backend usa X-Real-IP; purga de eventos de compendios vencidos > 180 días al crear uno; CI: `nginx -t` (bloquea),
   `pip-audit` y `npm audit` (informativos) y test_compendios/test_entrega en la lista. Probado en :8003 con datos
   reales: foto 317 KB en streaming; PDF 5,5 s → 2,4 s con caché. PENDIENTE (Andrés): límites del bucket en Supabase.
   Lo que sigue del plan original:
   - Workers: gunicorn YA es el administrador (supervisa/reinicia). Sumar `--max-requests 1000 --max-requests-jitter 100
     --timeout 60 --graceful-timeout 30`; proxy de comprobantes ASÍNCRONO en streaming (httpx ya instalado) + caché del
     navegador; PDF/HTML con caché por compendio (foto inmutable; clave = lista de comprobantes) y semáforo de 2 por worker;
     `limit_req` en nginx para `/c/` y `/api/publico/`; purga de eventos de compendios vencidos > 180 días. Cola futura,
     si hiciera falta: tabla Postgres `FOR UPDATE SKIP LOCKED` en un servicio con la misma imagen (como el bot), sin Redis.
   - Guardián `fin_sys_core/guardian.py` en las 3 puertas donde un archivo toca el servidor (subida del organizador, bot
     antes de subir a Supabase, y donde se parsea: PDF/HTML del compendio y vista previa): tipo real por firma (lista
     blanca), imágenes RE-CODIFICADAS con Pillow (mata polyglots y metadatos; tope de píxeles anti-bomba), PDF sin contenido
     activo (/JavaScript, /OpenAction, /Launch, /EmbeddedFile, /XFA → rechazo, con pypdf), xlsx sin macros ni zip-bomb
     (defusedxml explícito), texto seguro para Excel/CSV. Subidas directas navegador→Supabase (EvidenceModal): límites de
     MIME y tamaño en la configuración del bucket (sin código). CI: `pip-audit` + `npm audit`. ClamAV solo si sobra RAM.
   - Mediano plazo (evaluar aparte): bucket privado + URLs firmadas de vida corta (toca RRHH, bot y Excel).
- 06-oct: el aviso de Telegram no salía → `f097d2e` pasa TELEGRAM_BOT_TOKEN y COMPENDIO_AVISO_TELEGRAM al backend en el
  compose. Probar con un compendio NUEVO (EXP-0003 y 0005 ya tienen su 1.ª apertura).

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
