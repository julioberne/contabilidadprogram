"""Crea un token de ingesta de SMS (Bot IA, etapa 09.F) desde la línea de comandos.

Atajo de desarrollo; el camino oficial es POST /api/webhooks/sms/token con
sesión autenticada. Mismo hash y misma tabla (sms_ingest_tokens).

Uso:  .venv\\Scripts\\python.exe scripts\\sms_token.py [email] [etiqueta] [remitente ...]
      (default: andres@finsys.os, "Teléfono", 85540)
El token plano se imprime UNA sola vez: pégalo en MacroDroid (header X-SMS-Token).
"""
import hashlib
import os
import secrets
import sys

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


def main():
    email = sys.argv[1] if len(sys.argv) > 1 else "andres@finsys.os"
    label = sys.argv[2] if len(sys.argv) > 2 else "Teléfono"
    remitentes = ["".join(ch for ch in r if ch.isdigit()) for r in sys.argv[3:]] or ["85540"]
    token = secrets.token_urlsafe(32)
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM hub_users WHERE email = %s", (email,))
        row = cur.fetchone()
        if not row:
            print(f"No existe el usuario {email}")
            return 1
        uid, nombre = row
        cur.execute("""
            INSERT INTO sms_ingest_tokens (hub_user_id, token_hash, label, sender_allowlist)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (uid, hashlib.sha256(token.encode()).hexdigest(), label, remitentes))
        token_id = cur.fetchone()[0]
        cur.execute("""
            SELECT chat_id FROM bot_chat_links
             WHERE hub_user_id = %s AND channel = 'telegram' AND status = 'ACTIVO'
        """, (uid,))
        chats = [r[0] for r in cur.fetchall()]
        conn.commit()
        cur.close()
        print(f"Usuario:    {nombre} <{email}>")
        print(f"Token #{token_id} ({label}) — remitentes permitidos: {', '.join(remitentes)}")
        print(f"TOKEN:      {token}")
        print("            (se muestra UNA sola vez; va en el header X-SMS-Token)")
        if chats:
            print(f"Chat(s) Telegram vinculados: {', '.join(chats)}")
        else:
            print("⚠ Sin chat de Telegram vinculado: los SMS se aceptan (sms_sin_chat) y se "
                  "convierten cuando hagas /vincular.")
        return 0
    finally:
        put_conn(conn)


if __name__ == "__main__":
    sys.exit(main())
