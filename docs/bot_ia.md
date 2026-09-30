# Bot IA (Módulo 09) — Funcionamiento, reglas e integración

> Documento de referencia. El estado vivo (pendientes, etapas) está en `CHECKLIST.md`;
> la bitácora en `docs/checkpoints.md`. Specs del módulo (requisitos, decisiones,
> criterios de aceptación por etapa): `docs/specs/09-bot-ia/SPEC.md`.

## 1. Qué hace

Registra **ingresos y gastos por chat** (Telegram hoy; WhatsApp en Etapa D), por texto
o nota de voz, en lenguaje natural:

> "Gasté 45.000 en almuerzo con Juan, pagué desde Bancolombia"

El bot lo convierte en un **BORRADOR** contable. Nada toca la contabilidad hasta que el
usuario responda `Confirmar #N` — entonces se crea la transacción real con su asiento de
partida doble vía el pipeline oficial (`transaction_service.create_transaction`).

## 2. Arquitectura (archivos)

| Pieza | Archivo | Rol |
|---|---|---|
| Adaptador Telegram | `fin_sys_core/bot_telegram.py` | Poller long-polling. Normaliza el update, descarga la nota de voz a `uploads/`, delega TODO en el driver y responde. Sin estado propio |
| Núcleo canal-agnóstico | `fin_sys_core/bot_driver.py` | `handle_message()`: comandos, vinculación, borradores, confirmación. No conoce las APIs de los canales |
| Inferencia compartida | `fin_sys_core/draft_builder.py` | Construye el borrador desde el JSON del LLM (misma lógica que la Ingestión por Voz de la web) |
| Motor IA | `fin_sys_core/ai_engine.py` | Whisper (voz→texto) + LLM (texto→JSON estructurado) + contexto RAG de transacciones pasadas |
| API web | `routers/bot.py` | Endpoints para la bandeja web de borradores (Etapa C) y vinculación |
| Tablas | `scripts/migrate_bot_tables.py` | `transaction_drafts`, vinculación chat↔usuario, códigos. Idempotente |
| Ingesta de SMS (09.F) | `fin_sys_core/sms_bancolombia.py`, `fin_sys_core/bot_sms.py`, `routers/webhooks_sms.py` | Lector por plantillas (sin LLM) → cola en `bot_messages` → borrador en el tick del poller |
| Medios de pago del tercero (09.G) | `fin_sys_core/terceros_cuentas.py`, `routers/third_party_accounts.py` | Cuentas, celulares, llaves y nombre del banco de cada tercero (`third_party_accounts`): el SMS siguiente al mismo destino llega con el tercero puesto |

## 3. Flujo de un mensaje

1. **Update llega** por long-polling (`getUpdates`, dedupe por `update_id`).
2. **¿Chat vinculado?** Si no → responde instrucciones de `/vincular` (el bot es privado).
3. **Voz** → se descarga el `.ogg` a `uploads/` → **Whisper** (`whisper-large-v3`, es) lo transcribe.
4. **Texto** → si es comando determinista (regex) se ejecuta directo — `Confirmar`/`Descartar`
   **JAMÁS pasan por el LLM**. Si no, va al LLM.
5. **LLM (Groq, modelo `GROQ_MODEL`)** estructura el texto a JSON estricto: tipo
   (INGRESO/GASTO/TRANSFERENCIA), monto (resuelve cálculos compuestos: "5 aptos a 1.000.000 y
   2 a 300.000"), concepto, método de pago, tercero (NIT si el RAG lo conoce), fecha (default hoy),
   etiquetas. Lo que no está explícito queda `null` — no inventa. Fallback: Gemini 2.5 Flash.
6. **Borrador** → fila en `transaction_drafts`, estado `BORRADOR`. El bot responde el resumen
   con lo inferido y lo faltante.
7. **`Confirmar #N`** → transición condicional `BORRADOR→PROCESANDO` (solo una petición gana:
   chat y web no pueden doble-confirmar) → pipeline oficial → transacción + asiento kernel →
   `CONFIRMADO`. Un `PROCESANDO` atascado >5 min se puede retomar.

Máquina de estados: `BORRADOR → PROCESANDO → CONFIRMADO | ERROR`, `BORRADOR → DESCARTADO`.

## 4. Reglas de negocio (no negociables)

- **Regla 6**: el LLM solo PROPONE. Toda escritura contable exige confirmación humana explícita.
- **Privacidad**: solo chats vinculados a un usuario del sistema pueden operar
  (`/vincular CODIGO`; el código se genera en la web o con `scripts/bot_link_code.py [email]`).
- **Un solo poller por token**: Telegram devuelve `409 Conflict` con dos consumidores de
  `getUpdates`. El diseño original preveía un bot de producción y otro de desarrollo con
  tokens distintos. **Hoy (sep-2026) local y producción comparten el MISMO token** (decisión
  de Andrés: no crear más bots): **no lanzar el poller local** mientras el contenedor `bot`
  de producción esté arriba — los cambios del bot se ven en el chat solo después del deploy;
  en local se prueban con los tests (`handle_message` / `handle_callback` directos).
- **Portafolio**: se valida ANTES de llamar al LLM (default del chat; corregible).
- La nota de voz de Telegram queda adjunta como evidencia de la transacción (mismo volumen
  `uploads` que sirve la web).

## 5. Comandos

| Comando | Efecto |
|---|---|
| texto o nota de voz libre | crea un borrador |
| `Confirmar #N` | oficializa (transacción + asiento) |
| `Descartar #N` | elimina el borrador |
| `/borradores` | lista borradores pendientes |
| `/vincular CODIGO` | vincula el chat al usuario |
| `/ayuda`, `/start` | ayuda |
| **reply** al borrador con texto libre, o `Concepto: …` | pone el concepto literal (etapa 09.G) |
| **reply** al borrador: `Tercero: nombre` (o un número: documento o celular) | asigna un tercero existente (varios → botones; ninguno → explica cómo crearlo) |
| **reply** al borrador: `Tercero: Nombre cc 123456` (o `nit …`, opcional `cel …` y correo) | el documento manda: si existe lo asigna, si no existe lo crea; con nombres parecidos pregunta con botones (nunca duplica) |
| **reply** con varias líneas (`abono cuota 1` + `Tercero: Leidy Molina cc 1007…`) | concepto y tercero en un solo mensaje |
| **reply** al borrador: `Tercero nuevo: Nombre` | crea el tercero sin documento (provisional `SN-…`) y lo asigna |
| SMS de Bancolombia pegado o reenviado al chat | lo convierte con el mismo lector del webhook (plan B si el teléfono no pudo enviarlo) |
| botón 👤 Tercero / 📝 Concepto | terceros recientes con un toque / instrucciones |
| botón **💾 Guardar … en (tercero)** (borradores de SMS) | registra en la ficha del tercero la cuenta, celular, llave o nombre del banco que trae el SMS; el siguiente SMS con ese dato llega con el tercero ya puesto. Aparece al asignar el tercero y junto a la confirmación; **nada se guarda solo** (etapa 09.G §10) |
| botón **🔁 Mover … a (tercero)** | el dato ya estaba en la ficha de otro tercero: lo pasa al correcto (solo con el toque) |

## 6. Modelos IA y configuración

| Función | Modelo | Config |
|---|---|---|
| Voz → texto | `whisper-large-v3` (Groq, idioma es) | fijo en `ai_engine.py` |
| Texto → JSON | **`GROQ_MODEL`** (env), default `openai/gpt-oss-120b` | `.env` local / Dokploy → Environment |
| Fallback | Gemini 2.5 Flash | `GEMINI_API_KEY` |

**Incidente 2026-09-02**: Groq retiró TODOS los Llama del catálogo (`llama-3.3-70b-versatile`
→ `model_not_found`) y el bot dejó de registrar. Fix: modelo configurable por env con default
`openai/gpt-oss-120b` (verificado con la key real). Si vuelve a pasar: consultar el catálogo
(`GET https://api.groq.com/openai/v1/models` con la key vía httpx — urllib lo bloquea Cloudflare)
y poner el nuevo modelo en `GROQ_MODEL` **sin tocar código**.

## 7. Despliegue y operación

- **Producción**: servicio `bot` del `docker-compose.yml` (misma imagen del backend,
  `command: python fin_sys_core/bot_telegram.py`). Env: `TELEGRAM_BOT_TOKEN` (bot de PROD),
  `GROQ_API_KEY`, `GEMINI_API_KEY`, `DB_*` — en Dokploy → Environment. `GROQ_MODEL` opcional.
- **Desarrollo**: `.venv\Scripts\python.exe fin_sys_core\bot_telegram.py` **solo** si el
  `.env` local tiene un token distinto al de producción. Con el token compartido actual (§4)
  no se lanza: chocaría con el poller de producción (409).
- **Migraciones**: `python scripts/migrate_bot_tables.py` ANTES del deploy (idempotente,
  desde local — la BD es compartida). Etapas nuevas: `scripts/migrate_sms_bancolombia.py`
  (09.F) y `scripts/migrate_third_party_accounts.py` (09.G), ambas ya aplicadas.
- **Tests**: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_bot_*.py"`.

## 8. Diagnóstico rápido

| Síntoma | Causa probable | Acción |
|---|---|---|
| "Error en Groq … model_not_found" | Groq rotó el catálogo | actualizar `GROQ_MODEL` (§6) |
| Bot no responde nada | contenedor `bot` caído o token vacío | Dokploy → logs del servicio `bot` |
| `409 Conflict` en logs | dos pollers con el mismo token | matar el poller local o usar el bot dev |
| "Este bot es privado" | chat sin vincular | `/vincular` con código de la web |
| Responde pero no registra al confirmar | error en pipeline (ver estado `ERROR` del draft) | revisar logs backend + `transaction_drafts` |

## 9. Etapas

- ✅ A/B — MVP Telegram (texto+voz, borradores, confirmación) — **en producción**
- ✅ C — Bandeja web de borradores (`BotApp.jsx` en el slot del registry)
- ⏳ B.5 — RAG semántico (pgvector instalado; requiere aprobación para tocar `get_rag_context`)
- ⏳ D — WhatsApp (Meta Cloud API; necesita dominio+TLS)
- ✅ E / E.2 / E.3 — Fotos de facturas (cero inferencia), ubicación, múltiples evidencias, botones (09-sep-2026)
- ✅ F — SMS de Bancolombia → borradores automáticos (30-sep-2026, probado con SMS real) — `docs/specs/09-bot-ia/09.F-sms-bancolombia.md`
- 🔵 G — Completar tercero y concepto desde Telegram + medios de pago del tercero (💾) — **en producción desde el 30-sep-2026**; falta solo la prueba con SMS real — `docs/specs/09-bot-ia/09.G-completar-borrador.md`
- ⏳ H — OCR de comprobantes con botón dedicado — `docs/specs/09-bot-ia/09.H-ocr-comprobantes.md`

> Las consultas de lectura ("¿cuánto gasté este mes?") las cubre el módulo 13 (Análisis Inteligente), no una etapa del bot.

## 10. Flujo típico: del SMS del banco a la transacción (09.F + 09.G)

1. **Pagas o transfieres.** Bancolombia manda el SMS (remitente 85540). MacroDroid lo reenvía al
   webhook y en menos de un minuto llega a Telegram un borrador con monto, fecha y tu cuenta.
2. **Si el bot ya conoce el destino**, el borrador llega con el tercero puesto y la nota
   "Tercero por medio de pago registrado". Respondes con el concepto y tocas ✅.
3. **Si no lo conoce** (primera vez), respondes (reply) al borrador:
   ```
   abono cuota 1
   Tercero: Leidy Molina cc 1007289007
   ```
   La primera línea es el concepto. La segunda asigna el tercero: si el documento existe lo usa,
   si no existe lo crea; con nombres parecidos te muestra botones para que elijas.
4. **Aparece el botón 💾 Guardar … en (tercero).** Un toque registra en su ficha el celular, la
   cuenta o la llave que traía el SMS. Desde ahí, los SMS con ese dato llegan con el tercero.
   Si no lo tocas, el botón vuelve a salir junto a la confirmación.
5. **Otra cuenta de la misma persona**: llega sin tercero; respondes `Tercero: leidy`, la
   encuentra sin duplicarla y tocas 💾. Queda una ficha con dos medios de pago.
6. **Si el bot trajo un tercero que no era**, lo cambias (reply o botón 👤) y el botón pasa a ser
   🔁 Mover: el dato sale de la ficha equivocada y entra en la correcta.
7. **En la web** (Contabilidad → 👤 Terceros → ✎) ves y editas la ficha completa y su sección
   "Cuentas, celulares y llaves": lo que guardas con 💾 aparece ahí y lo que registres ahí lo usa
   el bot.

Qué dato se guarda según el SMS: transferencia a celular → el celular; transferencia a cuenta → el
número completo de la cuenta; pago con QR → la llave; transferencia recibida o compra con tarjeta →
el nombre tal como lo escribe el banco. Siempre por igualdad exacta; nada se guarda ni se mueve sin
tu toque (Regla 6b).
