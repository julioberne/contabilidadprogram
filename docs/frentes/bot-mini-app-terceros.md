# Frente: bot-mini-app-terceros
Estado: ACTIVO · Actualizado: 2026-10-09 · Rama: claude/telegram-bot-evaluation-56c2d8 (worktree intelligent-ellis-6061d5)

## Objetivo
Evaluación del bot de Telegram pedida por Andrés el 9-oct (7 puntos): que responder a un mensaje complete
ESE borrador, plantillas SMS que faltaban, Mini App con mensaje original + concepto/monto + anclar el dato
del SMS en la ficha, etiquetas nuevas desde el bot y una bitácora de anomalías visible en la web.

## Estado actual (plan aprobado: A → B → C → D → E)
- A HECHO 68058eb: registro message_id→borrador en bot_messages (OUT con external_message_id, sin esquema
  nuevo) + respaldo «#N» del texto del mensaje del bot; reply nunca crea borrador; monto por reply; tercero
  «Nombre 1007289007»; aviso de faltantes informativo; botonera sin 👤/📝; solo el último mensaje con botones.
- B HECHO 5d9922d: familias transferencia_llave, pago_boton, retiro_cajero (GASTO), ahorro_bolsillo
  (TRANSFERENCIA, destino por 💳 Cuenta); «plantilla nueva» solo si el texto dice Bancolombia; botón
  💳 Cuenta (acc/accsel/accset/accno); traslado sin destino no confirma; `_faltantes` en editar_draft.
- Falta: C (Mini App), D (etiquetas ➕ Nueva), E (tabla `bot_anomalias` + `/anomalias` + pestaña en Bot IA web).
- Sin push: 68058eb, 5d9922d (+ los que siguen). CA-09I-01 (prueba real de la Mini App) sigue pendiente.

## Próximo paso
C: `frontend/src/tg/TelegramTerceroApp.jsx` → bloque «📩 Mensaje original» (draft.raw_text), campos
Concepto y Monto (PUT /api/bot/drafts/{id} con avisar_chat), casilla «Recordar «X» en esta ficha»
(POST /api/third-parties/{id}/accounts con payload.sms.medio; 409 → ofrecer /mover). Luego D y E.

## Decisiones de Andrés (9-oct)
- Retiro en cajero = GASTO. Quitar 👤 Tercero y 📝 Concepto. Texto suelto SÍ crea borrador (con aviso
  informativo de lo que falta). Bolsillo = traslado + botón de cuentas. Bitácora informativa, no restrictiva,
  con pestaña en el módulo Bot IA de la web (registro tal cual, sin inferencias).

## Archivos clave
- `fin_sys_core/bot_driver.py`: `_draft_por_reply`, `_flujo_respuesta`, `_parse_reply`/`_monto_de`,
  `_botones_borrador`, callbacks acc*, `editar_draft` (cuentas), `_faltantes`, `log_outbound`/`vincular_mensaje`.
- `fin_sys_core/bot_telegram.py`: `_datos_respuesta`, `_botonera_en`. `fin_sys_core/sms_bancolombia.py`, `bot_sms.py`.
- Tests: `tests/test_bot_reply.py`, `tests/test_sms_plantillas_oct.py` (en CI), `tests/test_bot_cuentas_db.py` (BD).

## Cómo verificar
- Puros: `.venv\Scripts\python.exe -m unittest tests.test_bot_reply tests.test_sms_plantillas_oct tests.test_bot_sms`.
- BD (worktree sin .env): scratchpad `correr_tests.py` carga el .env principal → tests `_db` (chat test-tg-…).
- 4 errores de `test_compendios` en local = DLL bloqueada por Windows (no es del bot).

## Riesgos
- `vincular_mensaje` deja filas OUT sin chat_link_id (las limpia la retención). Mensajes del bot anteriores
  al deploy se resuelven por el «#N» de su texto.
