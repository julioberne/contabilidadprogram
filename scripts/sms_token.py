"""Crea un token de ingesta de SMS (Bot IA, etapa 09.F) desde la línea de comandos.

Atajo de desarrollo; el camino oficial es POST /api/webhooks/sms/token con
sesión autenticada. Mismo hash y misma tabla (sms_ingest_tokens).

Uso:
  .venv\\Scripts\\python.exe scripts\\sms_token.py [email] [etiqueta]
        [--remitente 85540 ...] [--telegram] [--url https://xxxx.trycloudflare.com]
        [--revocar-otros]
  .venv\Scripts\python.exe scripts\sms_token.py --solo-url --url https://yyyy.trycloudflare.com

  --solo-url       NO crea ni revoca tokens: solo manda al chat la URL nueva del
                   webhook (el túnel cloudflared cambia de URL cada vez que se
                   reinicia; el token de MacroDroid sigue siendo el mismo).
  --telegram       envía el token (y la URL del webhook si se da --url) a TU chat
                   de Telegram vinculado, cada dato en un mensaje aparte: en el
                   celular se copia con un toque largo y se pega en MacroDroid.
  --url            base HTTPS del backend (la que imprime cloudflared, o el dominio).
  --revocar-otros  revoca los demás tokens vigentes del usuario (deja solo el nuevo).

Sin --telegram el token plano se imprime UNA sola vez en esta terminal.
"""
import argparse
import hashlib
import json
import os
import secrets
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _, _val = _line.partition('=')
                os.environ.setdefault(_key.strip(), _val.strip().strip('"').strip("'"))

from fin_sys_core.db_pool import get_conn, put_conn  # noqa: E402


def _enviar_telegram(chat_id, texto):
    """sendMessage directo (no usa getUpdates: no choca con el poller)."""
    bot = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot:
        print("⚠ Falta TELEGRAM_BOT_TOKEN en .env: no pude enviar por Telegram.")
        return False
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": texto}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception as e:
        print(f"⚠ Telegram no aceptó el mensaje: {e}")
        return False


def _chats_de(email):
    """→ (nombre, [chat_id...]) del usuario; ([], None) si no existe."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM hub_users WHERE email = %s", (email,))
        row = cur.fetchone()
        if not row:
            return None, []
        cur.execute("""
            SELECT chat_id FROM bot_chat_links
             WHERE hub_user_id = %s AND channel = 'telegram' AND status = 'ACTIVO'
        """, (row[0],))
        chats = [r[0] for r in cur.fetchall()]
        cur.close()
        return row[1], chats
    finally:
        put_conn(conn)


def _solo_url(a):
    """--solo-url: manda la URL nueva del webhook al chat sin tocar los tokens."""
    if not a.url:
        print("--solo-url necesita --url https://xxxx.trycloudflare.com")
        return 1
    webhook = a.url.rstrip("/") + "/api/webhooks/sms"
    nombre, chats = _chats_de(a.email)
    if nombre is None:
        print(f"No existe el usuario {a.email}")
        return 1
    print(f"Usuario:    {nombre} <{a.email}>")
    print(f"URL:        {webhook}")
    if not chats:
        print("⚠ Sin chat de Telegram vinculado: cópiala de aquí.")
        return 0
    ok = True
    for chat in chats:
        ok &= _enviar_telegram(chat, (
            "🔁 El túnel cambió de dirección. En MacroDroid → acción Solicitud HTTP, "
            "reemplaza solo la URL por la del siguiente mensaje (toque largo → Copiar). "
            "El token y los encabezados siguen igual."))
        ok &= _enviar_telegram(chat, webhook)
    print("Enviada a tu chat de Telegram." if ok else "⚠ No se pudo enviar por Telegram.")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="Token de ingesta de SMS")
    ap.add_argument("email", nargs="?", default="andres@finsys.os")
    ap.add_argument("label", nargs="?", default="Teléfono")
    ap.add_argument("--remitente", action="append", default=[])
    ap.add_argument("--telegram", action="store_true")
    ap.add_argument("--url", default="")
    ap.add_argument("--revocar-otros", action="store_true")
    ap.add_argument("--solo-url", action="store_true")
    a = ap.parse_args()

    if a.solo_url:
        return _solo_url(a)

    remitentes = ["".join(ch for ch in r if ch.isdigit()) for r in a.remitente] or ["85540"]
    token = secrets.token_urlsafe(32)
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM hub_users WHERE email = %s", (a.email,))
        row = cur.fetchone()
        if not row:
            print(f"No existe el usuario {a.email}")
            return 1
        uid, nombre = row
        revocados = 0
        if a.revocar_otros:
            cur.execute("""
                UPDATE sms_ingest_tokens SET revoked_at = NOW()
                 WHERE hub_user_id = %s AND revoked_at IS NULL
            """, (uid,))
            revocados = cur.rowcount
        cur.execute("""
            INSERT INTO sms_ingest_tokens (hub_user_id, token_hash, label, sender_allowlist)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (uid, hashlib.sha256(token.encode()).hexdigest(), a.label, remitentes))
        token_id = cur.fetchone()[0]
        cur.execute("""
            SELECT chat_id FROM bot_chat_links
             WHERE hub_user_id = %s AND channel = 'telegram' AND status = 'ACTIVO'
        """, (uid,))
        chats = [r[0] for r in cur.fetchall()]
        conn.commit()
        cur.close()
    finally:
        put_conn(conn)

    print(f"Usuario:    {nombre} <{a.email}>")
    print(f"Token #{token_id} ({a.label}) — remitentes permitidos: {', '.join(remitentes)}")
    if revocados:
        print(f"Revocados:  {revocados} token(s) anteriores")

    webhook = (a.url.rstrip("/") + "/api/webhooks/sms") if a.url else ""
    if a.telegram and chats:
        ok = True
        for chat in chats:
            ok &= _enviar_telegram(chat, (
                f"📲 Configuración de MacroDroid (token #{token_id} · {a.label})\n\n"
                "Te mando cada dato en un mensaje aparte: toque largo → Copiar, y pégalo "
                "en MacroDroid.\n\n"
                "1) URL de la Solicitud HTTP (método POST)\n"
                "2) Encabezado X-SMS-Token → su valor es el token\n"
                f"3) Encabezado X-SMS-From → valor: {remitentes[0]}\n"
                "4) Cuerpo: tipo text/plain y, como contenido, el texto mágico del "
                "mensaje SMS (botón …)"))
            if webhook:
                ok &= _enviar_telegram(chat, webhook)
            ok &= _enviar_telegram(chat, "X-SMS-Token")
            ok &= _enviar_telegram(chat, token)
            ok &= _enviar_telegram(chat, "X-SMS-From")
            ok &= _enviar_telegram(chat, remitentes[0])
        if ok:
            print("TOKEN:      enviado a tu chat de Telegram (no se imprime aquí).")
            if webhook:
                print(f"URL:        {webhook} (también enviada)")
            return 0
        print("⚠ No se pudo enviar todo por Telegram; lo imprimo aquí:")
    elif a.telegram:
        print("⚠ Sin chat de Telegram vinculado: imprimo el token aquí.")

    print(f"TOKEN:      {token}")
    print("            (se muestra UNA sola vez; va en el encabezado X-SMS-Token)")
    if webhook:
        print(f"URL:        {webhook}")
    if chats:
        print(f"Chat(s) Telegram vinculados: {', '.join(chats)}")
    else:
        print("⚠ Sin chat de Telegram vinculado: los SMS se aceptan (sms_sin_chat) y se "
              "convierten cuando hagas /vincular.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
