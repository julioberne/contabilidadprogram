# Frente: bot-mini-app-terceros
Estado: ACTIVO · Actualizado: 2026-10-02 09:55 · Rama/commit: master @ b44deb8 (producción: b6c0e42)

## Objetivo
Que cada borrador del bot de Telegram se pueda completar con la ficha del tercero sin salir del chat (Mini App 09.I),
y que esa ficha sea la fuente de verdad: una por tercero, con sus cuentas/celulares/llaves, sin duplicados ni renombres
en silencio. Termina cuando Andrés hace la prueba real (CA-09I-01) y las siguientes mejoras pequeñas quedan en producción.

## Estado actual
- Hecho: v1 de la Mini App en producción (2-oct 09:39): botón `📝 Completar tercero` bajo cada borrador nuevo →
  `https://finsys-andres.duckdns.org/tg.html?draft=N` (misma web, misma sesión usuario/clave); buscar/asignar/crear/
  editar/eliminar tercero y sus medios; al asignar, el poller reenvía el resumen al chat (`avisar_chat`, ≤45 s).
  Revisión adversarial (16 hallazgos) corregida. DELETE de terceros integrado. Kit de sesión de la otra sesión integrado.
- En producción: b6c0e42 (Dokploy `done`, 3 contenedores, `/tg.html` 200 con `frame-ancestors`, `/api/bot/drafts/1` → 401).
- Pendiente de push/deploy: commit de docs b44deb8 (sin deploy). Rama `claude/eager-mcnulty-92ede8` tiene 1 commit
  más (PUT/DELETE de tags y tasas) sin integrar → `git apply --3way` como se hizo con el DELETE de terceros.

## Próximo paso (concreto, ejecutable sin releer todo)
1. Andrés: generar un borrador nuevo (los anteriores al deploy conservan la botonera vieja), tocar `📝 Completar tercero`,
   asignar/crear, ver el resumen reenviado → marcar CA-09I-01 en la spec §10.1 y `Estado` de 09.I; CHECKLIST.
2. Si falla: leer el log del backend de prod con `scratchpad/dokploy_logs_ws.py` (WebSocket de Dokploy, x-api-key) y
   `GET /api/bot/drafts/{id}`; el token vence (`TOKEN_TTL_SECONDS` en `routers/auth_guard.py`) → la pantalla vuelve al login.
3. Siguientes mejoras, una por hito: catálogo de entidades (select en `TerceroMediosPago`, clave en `banco`, sin ALTER);
   motor de identidad `fin_sys_core/terceros_identidad.py` (avisos por celular/cuenta, spec §3-§4); entrar sin clave (initData).

## Decisiones tomadas (y por qué)
- Mini App = la misma web recortada, no un tercer frontend: reutiliza sesión, endpoints y componentes (`TerceroForm`,
  `TerceroFicha` + `TerceroMediosPago`). Sin token del bot en el backend ni cambios de compose: no hacían falta en v1.
- El backend NO habla con Telegram: el poller sigue siendo el único emisor (tick `avisar_chat_pendientes`, atómico).
- Nunca renombrar ni duplicar en silencio (D-09I-08): `POST/PUT /api/third-parties` → 409 «existe» con la ficha dueña,
  400 vacío/genérico, 404, 422 tipo/longitud; sin documento nace `SN-…`. Al confirmar, `_tercero_vigente` relee la ficha
  por id (formalizar un provisional ya asignado creaba otra ficha). `database_driver.py` (🔴) sin tocar.
- `ThirdPartyInput` admite CE/PP (la web los ofrecía y el borrador caía en ERROR). Tests con BD usan links `whatsapp`.
- `git rebase origin/master` pasa el clasificador (merge no): úsalo cuando el push de Andrés sea non-fast-forward.

## Archivos clave (ruta:línea cuando aplique)
- `fin_sys_core/bot_driver.py`: `WEBAPP_BASE`, `_botones_borrador` (fila `webapp:`), `marcar_aviso_chat`,
  `avisar_chat_pendientes`, `_tercero_vigente` · `fin_sys_core/bot_telegram.py`: `_markup` (web_app) y el tick en `main`.
- `routers/bot.py`: `GET /api/bot/drafts/{id}`, `PUT` con `avisar_chat` · `routers/cartera.py`: `_normalizar_tercero`,
  `_ficha_por_documento`, `_respuesta_existe`, POST/PUT/DELETE de terceros · `routers/schemas.py:18`.
- `frontend/tg.html`, `frontend/src/tg/{main.jsx,telegram.js,TelegramTerceroApp.jsx}`,
  `frontend/src/contabilidad-v2/components/{TerceroForm,TerceroFicha,TerceroMediosPago}.jsx`, `frontend/nginx.conf` (`/tg.html`),
  `frontend/vite.config.js` (input `tg`). Spec: `docs/specs/09-bot-ia/09.I-ficha-tercero-anclas.md` (§10 = lo construido).

## Cómo verificar
- `.venv\Scripts\python.exe -m unittest tests.test_bot_webapp tests.test_bot_webapp_db tests.test_terceros_borrado_db`
  (los `_db` escriben filas de prueba y las borran; chat `test-tg-…`, canal `whatsapp`).
- `frontend/`: `npx vitest run` (90) · `npm run build` → `dist/tg.html`. Local: `.claude/launch.json` → `finsys-backend-tg`
  (:8002; :8000/:8001 suelen estar ocupados por otra sesión) y abrir `http://localhost:8002/tg.html?draft=<id>` con la
  sesión de la web en `localStorage.finsys_session`.
- Prod: `curl -I https://finsys-andres.duckdns.org/tg.html` (200 + CSP) y `GET /api/bot/drafts/1` → 401.

## Bloqueos y riesgos
- Falta la prueba real de Andrés (CA-09I-01). MacroDroid gratis se desactiva solo (anuncio/Pro): decidir Pro o
  SMS to URL Forwarder. El panel Terceros de la web aún no usa los componentes compartidos (acoplado al estado de la TX).
