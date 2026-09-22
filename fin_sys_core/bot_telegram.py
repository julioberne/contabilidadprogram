# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Módulo 09: adaptador + poller de Telegram (long-polling).

PROCESO ÚNICO por token: Telegram devuelve 409 Conflict si dos consumidores
hacen getUpdates a la vez. Por eso:
  - En producción corre como servicio `bot` del docker-compose (misma imagen
    del backend, command distinto) con SU PROPIO token de producción.
  - En desarrollo se usa OTRO bot (token de dev en .env local):
        .venv\\Scripts\\python.exe fin_sys_core\\bot_telegram.py

El adaptador es deliberadamente delgado: normaliza el update entrante,
descarga la nota de voz si la hay, delega TODO en bot_driver.handle_message()
y envía la respuesta. Sin estado propio — la verdad vive en Postgres.
"""
import os
import sys
import time
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))
os.chdir(_ROOT)  # uploads/ y .env relativos al repo, igual que server.py
import fin_sys_core  # noqa: E402,F401  — un solo pool por proceso (ver su __init__)

# --- Cargador de Variables de Entorno (mismo patrón de server.py) ---
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line_strip = line.strip()
            if line_strip and not line_strip.startswith("#") and "=" in line_strip:
                key, val = line_strip.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

import httpx

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}"
FILES = f"https://api.telegram.org/file/bot{TOKEN}"
POLL_TIMEOUT = 45  # long-poll del lado de Telegram (el cliente espera un poco más)

_client = httpx.Client(timeout=httpx.Timeout(POLL_TIMEOUT + 15, connect=10.0))

_AUDIO_EXTS = {"ogg", "opus", "mp3", "m4a", "wav", "webm", "flac"}


def _markup(buttons):
    """Botonera canal-agnóstica [(label, data)…] → InlineKeyboardMarkup."""
    if buttons is None:
        return None
    return {"inline_keyboard": [
        [{"text": lbl, "callback_data": data[:64]} for lbl, data in fila]
        for fila in buttons
    ]}


def send_message(chat_id: str, text: str, buttons=None):
    """Envía texto plano (sin parse_mode: cero problemas de escapado).
    → message_id del mensaje enviado, o None si falló."""
    try:
        body = {"chat_id": chat_id, "text": text[:4096]}
        mk = _markup(buttons)
        if mk:
            body["reply_markup"] = mk
        r = _client.post(f"{API}/sendMessage", json=body)
        if r.status_code == 200:
            return r.json().get("result", {}).get("message_id")
        print(f"⚠️ [TG] sendMessage {r.status_code}: {r.text[:120]}")
        return None
    except Exception as e:
        print(f"⚠️ [TG] sendMessage falló: {e}")
        return None


def answer_callback(callback_id: str, texto=None):
    """Obligatorio tras cada callback_query — sin esto el botón queda girando."""
    try:
        body = {"callback_query_id": callback_id}
        if texto:
            body["text"] = str(texto)[:190]
        _client.post(f"{API}/answerCallbackQuery", json=body)
    except Exception as e:
        print(f"⚠️ [TG] answerCallbackQuery falló: {e}")


def edit_message(chat_id: str, message_id, text=None, buttons=None):
    """Edita el mensaje del borrador: texto y/o botonera ([] = quitarla)."""
    try:
        if text is not None:
            body = {"chat_id": chat_id, "message_id": message_id,
                    "text": str(text)[:4096]}
            mk = _markup(buttons)
            if mk is not None:
                body["reply_markup"] = mk
            _client.post(f"{API}/editMessageText", json=body)
        elif buttons is not None:
            _client.post(f"{API}/editMessageReplyMarkup",
                         json={"chat_id": chat_id, "message_id": message_id,
                               "reply_markup": _markup(buttons)})
    except Exception as e:
        print(f"⚠️ [TG] editMessage falló: {e}")


def _bajar_de_telegram(file_id: str):
    """getFile + descarga. → (bytes, extensión) o (None, None)."""
    try:
        r = _client.get(f"{API}/getFile", params={"file_id": file_id})
        r.raise_for_status()
        remote_path = r.json()["result"]["file_path"]
        ext = remote_path.rsplit(".", 1)[-1].lower() if "." in remote_path else ""
        data = _client.get(f"{FILES}/{remote_path}")
        data.raise_for_status()
        return data.content, ext
    except Exception as e:
        print(f"⚠️ [TG] descarga de archivo falló: {e}")
        return None, None


def _descargar_voz(file_id: str):
    """Nota de voz → (media_path, transcribe_path):
      · transcribe_path: archivo LOCAL (Whisper necesita filesystem)
      · media_path: URL del bucket (evidencia compartida local↔prod, DT-29);
        si la subida falla, la ruta local hace de evidencia como antes."""
    contenido, ext = _bajar_de_telegram(file_id)
    if contenido is None:
        return None, None
    if ext not in _AUDIO_EXTS:
        ext = "ogg"
    os.makedirs("uploads", exist_ok=True)
    nombre = f"{uuid.uuid4().hex[:8]}_tg_voice.{ext}"
    destino = os.path.join("uploads", nombre)
    with open(destino, "wb") as fh:
        fh.write(contenido)

    from storage_media import subir_evidencia
    mime = "audio/ogg" if ext in ("ogg", "opus") else f"audio/{ext}"
    url = subir_evidencia(nombre, contenido, mime)
    return (url or f"uploads/{nombre}"), f"uploads/{nombre}"


_FOTO_MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
              "webp": "image/webp", "gif": "image/gif"}


def _descargar_foto(m: dict):
    """📸 message.photo → la resolución MÁS GRANDE → bucket. → URL o None.
    La foto no toca el disco: pasa por memoria directo a Supabase Storage."""
    fotos = m.get("photo") or []
    if not fotos:
        return None
    file_id = fotos[-1].get("file_id")      # Telegram las ordena de menor a mayor
    contenido, ext = _bajar_de_telegram(file_id)
    if contenido is None:
        return None
    from storage_media import subir_evidencia
    mime = _FOTO_MIME.get(ext, "image/jpeg")
    nombre = f"tg_foto.{ext or 'jpg'}"
    return subir_evidencia(nombre, contenido, mime)


def normalize(update: dict):
    """Update de Telegram → InboundMessage canal-agnóstico (o None si se ignora)."""
    m = update.get("message")
    if not m or not m.get("chat"):
        return None
    # Solo chat PRIVADO: en un grupo cualquiera podría dictarle gastos al bot
    # (y con privacy mode ni vemos los mensajes completos). Silencio deliberado.
    if m["chat"].get("type", "private") != "private":
        print(f"🔇 [TG] mensaje de chat no privado ignorado ({m['chat'].get('type')})")
        return None
    base = {
        "channel": "telegram",
        "chat_id": str(m["chat"]["id"]),
        "external_message_id": str(update["update_id"]),
        "text": None,
        "media_path": None,
    }
    if m.get("text") is not None:
        base["kind"] = "text"
        base["text"] = m["text"]
        return base
    voz = m.get("voice") or m.get("audio")
    if voz and voz.get("file_id"):
        media, transcribe = _descargar_voz(voz["file_id"])
        if media is None:
            base["kind"] = "unsupported"
            return base
        base["kind"] = "audio"
        base["media_path"] = media           # URL del bucket (o local si falló)
        base["transcribe_path"] = transcribe  # archivo local para Whisper
        return base
    # 📸 Fotos (Etapa E): al bucket; caption = texto; reply → borrador exacto
    if m.get("photo"):
        base["kind"] = "photo"
        base["media_path"] = _descargar_foto(m)   # None si falló (driver avisa)
        base["text"] = m.get("caption")
        reply = m.get("reply_to_message") or {}
        if reply.get("message_id"):
            base["reply_to_message_id"] = str(reply["message_id"])
        return base
    # 📍 Ubicación (Etapa E.2): geolocalización explícita para el borrador
    loc = m.get("location")
    if loc and loc.get("latitude") is not None:
        base["kind"] = "location"
        base["latitude"] = loc["latitude"]
        base["longitude"] = loc["longitude"]
        reply = m.get("reply_to_message") or {}
        if reply.get("message_id"):
            base["reply_to_message_id"] = str(reply["message_id"])
        return base
    # Stickers, documentos… → próxima etapa
    base["kind"] = "unsupported"
    return base


def _procesar_callback(bot_driver, cb: dict):
    """callback_query → bot_driver.handle_callback → acciones en Telegram.
    answerCallbackQuery SIEMPRE se responde (aunque falle lo demás)."""
    cb_id = cb.get("id")
    try:
        m = cb.get("message") or {}
        chat = (m.get("chat") or {})
        if chat.get("type", "private") != "private":
            answer_callback(cb_id)
            return
        chat_id = str(chat.get("id", ""))
        out = bot_driver.handle_callback("telegram", chat_id, cb.get("data") or "")
        answer_callback(cb_id, out.get("alert"))
        if out.get("edit_text") is not None or out.get("edit_buttons") is not None:
            edit_message(chat_id, m.get("message_id"),
                         text=out.get("edit_text"), buttons=out.get("edit_buttons"))
        if out.get("text"):
            send_message(chat_id, out["text"])
    except Exception as e:
        print(f"⚠️ [TG] callback falló: {e}")
        answer_callback(cb_id, "Error procesando el botón.")


def main():
    if not TOKEN:
        print("❌ Falta TELEGRAM_BOT_TOKEN en el entorno/.env — no puedo arrancar.")
        sys.exit(1)

    try:
        me = _client.get(f"{API}/getMe").json()
        username = me.get("result", {}).get("username", "?")
        print(f"🤖 [TG] Poller iniciado como @{username} (long-polling {POLL_TIMEOUT}s)")
    except Exception as e:
        print(f"❌ [TG] No se pudo contactar a api.telegram.org: {e}")
        sys.exit(1)

    import bot_driver

    offset = None
    backoff = 1
    proximo_tick = 0.0   # monotonic: throttle local del tick (la verdad vive en BD)
    proximo_purga = 0.0  # retención de borradores/mensajes (etapa 09.F): una vez por hora
    while True:
        try:
            # ── Resumen analítico periódico (hito 2, B1) ─────────────────
            # Cada 15 min se consulta a la BD si ya tocan las
            # ANALYTICS_RESUMEN_HORAS (default 24; 0 = apagado) desde el
            # último envío — el tick es el "scheduler" del sistema y queda
            # listo para los recordatorios de cartera de la Fase 2.
            if time.monotonic() >= proximo_tick:
                proximo_tick = time.monotonic() + 900
                try:
                    from insight_engine import tick_resumen_telegram
                    if tick_resumen_telegram(send_message):
                        print("📊 [TG] Resumen analítico enviado a los chats vinculados.")
                except Exception as e:
                    print(f"⚠️ [TG] tick del resumen falló (se reintenta): {e}")

            # ── SMS de Bancolombia → borradores (etapa 09.F) ──────────────
            # Cada vuelta (≤ POLL_TIMEOUT s de latencia): los SMS que encoló
            # el webhook en bot_messages se convierten en borradores y se
            # envían con botones. Un SMS malo marca SU fila; el tick nunca
            # tumba el poller (D-09F-01: el único que habla con Telegram).
            try:
                from bot_sms import procesar_pendientes
                n_sms = procesar_pendientes(send_message)
                if n_sms:
                    print(f"📲 [TG] {n_sms} SMS convertido(s) en borrador.")
            except Exception as e:
                print(f"⚠️ [TG] tick SMS falló (se reintenta): {e}")

            # ── Retención 30/60/90 (Regla 6b): una vez por hora ───────────
            if time.monotonic() >= proximo_purga:
                proximo_purga = time.monotonic() + 3600
                try:
                    from bot_retencion import purgar
                    res = purgar(send_message)
                    if any(res.values()):
                        print(f"🧹 [TG] retención: {res}")
                except Exception as e:
                    print(f"⚠️ [TG] purga de retención falló (se reintenta): {e}")

            params = {"timeout": POLL_TIMEOUT}
            if offset is not None:
                params["offset"] = offset
            r = _client.get(f"{API}/getUpdates", params=params)
            r.raise_for_status()
            for update in r.json().get("result", []):
                offset = update["update_id"] + 1

                # ── Botones inline (Etapa E) ──
                cb = update.get("callback_query")
                if cb:
                    _procesar_callback(bot_driver, cb)
                    continue

                msg = normalize(update)
                if not msg:
                    continue
                try:
                    reply = bot_driver.handle_message(msg)
                except Exception as e:
                    reply = f"⚠ Error interno del bot: {e}"
                if not reply:
                    continue
                if isinstance(reply, dict):
                    mid = send_message(msg["chat_id"], reply["text"],
                                       buttons=reply.get("buttons"))
                    if mid and reply.get("draft_id"):
                        bot_driver.guardar_summary_message_id(reply["draft_id"], mid)
                    bot_driver.log_outbound("telegram", msg["chat_id"], reply["text"],
                                            draft_id=reply.get("draft_id"))
                else:
                    send_message(msg["chat_id"], reply)
                    bot_driver.log_outbound("telegram", msg["chat_id"], reply)
            backoff = 1
        except KeyboardInterrupt:
            print("👋 [TG] Poller detenido.")
            break
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 409:
                print("⚠️ [TG] 409: otro proceso usa este token (¿dev y prod con el "
                      "mismo bot?). Reintento en 30s…")
                time.sleep(30)
            else:
                print(f"⚠️ [TG] HTTP {e}. Reintento en {backoff}s…")
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
        except Exception as e:
            print(f"⚠️ [TG] {e}. Reintento en {backoff}s…")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)


if __name__ == "__main__":
    main()
