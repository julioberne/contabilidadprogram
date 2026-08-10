"""Genera un código de vinculación del Bot IA desde la línea de comandos.

Atajo de desarrollo mientras la UI no tiene el botón (el camino oficial es
POST /api/bot/link-code con sesión autenticada). Mismo hash y misma tabla.

Uso:  .venv\\Scripts\\python.exe scripts\\bot_link_code.py [email]
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

from fin_sys_core.db_pool import get_conn, put_conn

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def main():
    email = sys.argv[1] if len(sys.argv) > 1 else "andres@finsys.os"
    code = "".join(secrets.choice(ALPHABET) for _ in range(6))
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
            INSERT INTO bot_link_codes (code_hash, hub_user_id, expires_at)
            VALUES (%s, %s, NOW() + INTERVAL '30 minutes')
        """, (hashlib.sha256(code.encode()).hexdigest(), uid))
        conn.commit()
        cur.close()
        print(f"Usuario: {nombre} <{email}>")
        print(f"CODIGO:  {code}   (valido 30 minutos, un solo uso)")
        print(f"Envia al bot de Telegram:  /vincular {code}")
        return 0
    finally:
        put_conn(conn)


if __name__ == "__main__":
    sys.exit(main())
