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


def send_message(chat_id: str, text: str) -> bool:
    """Envía texto plano (sin parse_mode: cero problemas de escapado)."""
    try:
        r = _client.post(f"{API}/sendMessage",
                         json={"chat_id": chat_id, "text": text[:4096]})
        return r.status_code == 200
    except Exception as e:
        print(f"⚠️ [TG] sendMessage falló: {e}")
        return False


def _descargar_voz(file_id: str):
    """Descarga una nota de voz a uploads/. → ruta FS relativa o None."""
    try:
        r = _client.get(f"{API}/getFile", params={"file_id": file_id})
        r.raise_for_status()
        remote_path = r.json()["result"]["file_path"]
        ext = remote_path.rsplit(".", 1)[-1].lower() if "." in remote_path else "ogg"
        if ext not in _AUDIO_EXTS:
            ext = "ogg"
        data = _client.get(f"{FILES}/{remote_path}")
        data.raise_for_status()
        os.makedirs("uploads", exist_ok=True)
        nombre = f"{uuid.uuid4().hex[:8]}_tg_voice.{ext}"
        destino = os.path.join("uploads", nombre)
        with open(destino, "wb") as fh:
            fh.write(data.content)
        return f"uploads/{nombre}"
    except Exception as e:
        print(f"⚠️ [TG] descarga de voz falló: {e}")
        return None


def normalize(update: dict):
    """Update de Telegram → InboundMessage canal-agnóstico (o None si se ignora)."""
    m = update.get("message")
    if not m or not m.get("chat"):
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
        path = _descargar_voz(voz["file_id"])
        if path is None:
            base["kind"] = "unsupported"
            return base
        base["kind"] = "audio"
        base["media_path"] = path
        return base
    # Fotos, ubicación, stickers, documentos… → Etapa E
    base["kind"] = "unsupported"
    return base


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
    while True:
        try:
            params = {"timeout": POLL_TIMEOUT}
            if offset is not None:
                params["offset"] = offset
            r = _client.get(f"{API}/getUpdates", params=params)
            r.raise_for_status()
            for update in r.json().get("result", []):
                offset = update["update_id"] + 1
                msg = normalize(update)
                if not msg:
                    continue
                try:
                    reply = bot_driver.handle_message(msg)
                except Exception as e:
                    reply = f"⚠ Error interno del bot: {e}"
                if reply:
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
