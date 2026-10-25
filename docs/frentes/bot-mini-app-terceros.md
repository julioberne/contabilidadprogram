# Frente: bot-mini-app-terceros
Estado: ACTIVO · Actualizado: 2026-10-25 · Rama: claude/telegram-bot-evaluation-56c2d8 (worktree intelligent-ellis-6061d5)

## Objetivo
Bot de Telegram cómodo para registrar desde el chat: responder a un mensaje completa ESE borrador, plantillas
SMS reales, Mini App (📝 Completar) como puente a la web, etiquetas manejables y bitácora de anomalías.

## Estado actual
- EN PRODUCCIÓN (publicado ~13-oct, d87c1fe): evaluación del 9-oct, hitos A-E — replies asociados al borrador
  (registro message_id + «#N»), monto/tercero/etiqueta por reply, aviso informativo, botonera corta + 💳 Cuenta,
  plantillas Bre-B llave/Botón/retiro/bolsillo, filtro de publicidad, Mini App con mensaje original + concepto/
  monto + recordar dato del SMS, ➕ Nueva etiqueta, bitácora `bot_anomalias` (/anomalias + Bot IA → 📓 Bitácora).
  La bitácora ya registra en prod (1.ª anomalía 13-oct, borrador #821).
- HECHO 25-oct, SIN PUSH — etiquetas (con 19, el botón mostraba 10 y nunca salían Oficina/Operativo/Recurrente):
  - 37f18e2 chat: orden estable por uso (VENTANA_USO) + nombre, 12 por página en 2 columnas, ◀ n/N ▶,
    🔎 Buscar (force_reply kind buscar_etiqueta, armar_contiene B6 ≥3 letras), ➕ Crear «texto» desde la
    búsqueda; tocar en resultados se queda en resultados (handle_callback recibe texto_mensaje).
  - 36e2ba5 Mini App: `EtiquetasBorrador.jsx` — fichas, búsqueda en servidor (/api/buscar/etiquetas top 30),
    crear (POST /api/tags), Guardar con PUT + avisar_chat.

## Próximo paso
1. Andrés: `scripts\publicar.cmd` (2 commits). Probar: 🏷️ Etiquetas → ▶ página 2, 🔎 Buscar «obra», ➕ Crear;
   📝 Completar → sección 🏷️ Etiquetas.
2. Etiquetas basura sin uso («dfghj», «nm», «bnm,»): las borra Andrés en 🏷️ Tags de la web.
3. Sugerencias en espera de OK: categoría/empresa habitual en la ficha del tercero; categoría y ✅ en la Mini
   App; recordatorio diario de borradores; fotos en la Mini App; filtro de remitente en MacroDroid.

## Decisiones de Andrés
- 9-oct: retiro = GASTO; sin 👤/📝 en la botonera; texto suelto crea borrador con aviso informativo; bolsillo =
  traslado + 💳 Cuenta; bitácora informativa con pestaña en Bot IA.
- 24-oct: etiquetas en chat (páginas + buscar) Y en la Mini App.

## Archivos clave
- `fin_sys_core/bot_driver.py`: `_tags_reales`, `_botones_tags`, `_resultado_busqueda_etiquetas`, callbacks
  tags/tagpg/tagset/tagbus/tagcrea/tagnew, `_flujo_respuesta` (pedir_etiqueta, buscar_etiqueta).
- `frontend/src/tg/{TelegramTerceroApp,BorradorEditable,EtiquetasBorrador}.jsx`; `fin_sys_core/bot_anomalias.py`.

## Cómo verificar
- `tests.test_bot_listas tests.test_bot_reply` (puros, en CI); `frontend`: vitest (177) + build.
- Local: Smart App Control quedó APAGADO (13-oct) → `:8000` arranca con `launch.json` local (no commiteado:
  python del checkout principal + scratchpad `lanzar_backend_wt.py <puerto>`). Sin sesión en el panel.
- Vitest bajo carga (build+lint a la vez) dio 2 fallas intermitentes en BorradorEditable; solo pasa 7/7.
