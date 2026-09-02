# Bot IA (Módulo 09) — Funcionamiento, reglas e integración

> Documento de referencia. El estado vivo (pendientes, etapas) está en `CHECKLIST.md`;
> la bitácora en `docs/checkpoints.md`. Plan maestro de etapas:
> `~/.claude/plans/empezamos-a-evaluar-la-generic-squirrel.md`.

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
  `getUpdates`. Por eso el bot de producción y el de desarrollo son **bots distintos con
  tokens distintos**.
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
- **Desarrollo**: `.venv\Scripts\python.exe fin_sys_core\bot_telegram.py` con el token del
  bot dev (`@COLFinsysbot`) en `.env`.
- **Migraciones**: `python scripts/migrate_bot_tables.py` ANTES del deploy (idempotente,
  desde local — la BD es compartida).
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
- ⏳ C — Bandeja web de borradores (`BotApp.jsx` en el slot del registry)
- ⏳ B.5 — RAG semántico (pgvector instalado; requiere aprobación para tocar `get_rag_context`)
- ⏳ D — WhatsApp (Meta Cloud API; necesita dominio+TLS)
- ⏳ E — Fotos de facturas y ubicación
- ⏳ F — Consultas/comandos de lectura ("¿cuánto gasté este mes?")
