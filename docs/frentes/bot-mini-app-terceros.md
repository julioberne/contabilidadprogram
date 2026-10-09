# Frente: bot-mini-app-terceros
Estado: ACTIVO · Actualizado: 2026-10-09 · Rama: claude/telegram-bot-evaluation-56c2d8 (worktree intelligent-ellis-6061d5)

## Objetivo
Evaluación del bot de Telegram pedida por Andrés el 9-oct (7 puntos): que responder a un mensaje complete
ESE borrador, plantillas SMS que faltaban, Mini App con mensaje original + concepto/monto + anclar el dato
del SMS en la ficha, etiquetas nuevas desde el bot y una bitácora de anomalías visible en la web.

## Estado actual: A-E HECHOS, sin push (listo para publicar)
- A 68058eb: registro message_id→borrador (bot_messages OUT con external_message_id) + respaldo «#N» del
  texto respondido; reply nunca crea borrador; monto por reply; «Tercero Nombre 1007289007»; aviso de
  faltantes informativo; botonera sin 👤/📝; solo el último mensaje del borrador lleva botones.
- B 5d9922d: familias transferencia_llave, pago_boton, retiro_cajero (GASTO), ahorro_bolsillo (TRANSFERENCIA);
  «plantilla nueva» solo si dice Bancolombia (publicidad fuera); 💳 Cuenta; traslado sin destino no confirma.
- C 1076c3d: Mini App con 📩 mensaje original, concepto y monto editables, casilla «recordar dato del SMS»
  al asignar + bloque 📲 (💾 / 🔁 mover). Verificación visual PENDIENTE (en :8002 no hay sesión; la clave no
  se teclea): verla en Telegram tras publicar.
- D 28a3e0a: 🏷️ ➕ Nueva etiqueta (force_reply, kind pedir_etiqueta) y «Etiqueta: x» en replies.
- E 41b55e1: tabla `bot_anomalias` (la crea server._startup al desplegar), `/anomalias`, pestaña
  Bot IA → 📓 Bitácora, GET/PUT /api/bot/anomalias. Antes del deploy, registrar() avisa y no rompe.

## Próximo paso
1. Andrés: `scripts\publicar.cmd` (push a master + CI + deploy). Sonda: `GET /api/bot/anomalias` → 401.
2. Prueba real: SMS nuevo → reply «parqueadero» + «12100» al mensaje viejo; 📝 Completar (mensaje original,
   casilla recordar); 🏷️ ➕ Nueva; 💳 Cuenta en un SMS de bolsillo; `/anomalias`; pestaña 📓 en la web.
3. Sugerencias en espera de OK: categoría/empresa habitual en la ficha del tercero; categoría y ✅ en la Mini
   App; recordatorio diario de borradores (43 pendientes al 9-oct); fotos en la Mini App; filtro de remitente
   en MacroDroid. CA-09I-01 sigue pendiente.

## Decisiones de Andrés (9-oct)
- Retiro en cajero = GASTO. Quitar 👤 Tercero y 📝 Concepto. Texto suelto SÍ crea borrador (aviso informativo).
  Bolsillo = traslado + botón de cuentas. Bitácora informativa, no restrictiva, con pestaña en Bot IA.

## Archivos clave
- `fin_sys_core/bot_driver.py` (`_draft_por_reply`, `_flujo_respuesta`, `_parse_reply`, callbacks acc*/tagnew,
  `editar_draft` cuentas, `_faltantes`), `bot_telegram.py` (`_botonera_en`), `sms_bancolombia.py`, `bot_sms.py`,
  `bot_anomalias.py`, `etiquetas.crear_o_usar`, `routers/bot_anomalias.py`, `frontend/src/tg/BorradorEditable.jsx`,
  `frontend/src/bot/{BotApp,BotBitacoraPanel}.jsx`.

## Cómo verificar
- Puros (en CI): `tests.test_bot_reply tests.test_sms_plantillas_oct tests.test_bot_anomalias` + los de siempre.
- BD (worktree sin .env): scratchpad `correr_tests.py` → `test_bot_cuentas_db test_bot_etiquetas_db` + `_db` del bot (57 OK).
- `frontend`: vitest 156 OK, build OK. 4 errores de `test_compendios` en local = DLL bloqueada por Windows.
