# -*- coding: utf-8 -*-
"""
migrate_ct_bcrypt.py — Cierra DT-04: migra el hash MD5 del seed de
workspace_users (Control Tower) a bcrypt vía pgcrypto.

Contexto: el seed original insertó a andres@finsys.os con MD5. El login real
usa crypt(), que nunca matchea un hex MD5, así que ese usuario solo entraba
por el fallback mock (eliminado). Este script re-hashea ÚNICAMENTE la cuenta
seed cuya contraseña es conocida ('admin123'); no puede tocar otras cuentas
porque sus contraseñas no se conocen (y las registradas por la app ya usan
crypt()/bcrypt desde el inicio).

Idempotente: solo actúa si el hash actual es un hex de 32 chars (MD5).

Uso:  python scripts/migrate_ct_bcrypt.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SEED_EMAIL = "andres@finsys.os"
SEED_PASSWORD = "admin123"


def _load_env():
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def run():
    _load_env()
    from fin_sys_core.db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, password_hash FROM workspace_users WHERE email = %s",
                (SEED_EMAIL,),
            )
            row = cur.fetchone()
            if not row:
                print(f"No existe {SEED_EMAIL} en workspace_users — nada que migrar.")
                return
            user_id, current_hash = row[0], row[1] or ""
            if not re.fullmatch(r"[0-9a-f]{32}", current_hash):
                print("El hash ya no es MD5 (parece bcrypt) — nada que migrar.")
                return
            cur.execute(
                "UPDATE workspace_users SET password_hash = crypt(%s, gen_salt('bf')) WHERE id = %s",
                (SEED_PASSWORD, user_id),
            )
        conn.commit()
        print(f"OK — {SEED_EMAIL} migrado de MD5 a bcrypt (pgcrypto).")
        print("Recomendado: cambia esa contraseña desde la app cuanto antes.")
    finally:
        put_conn(conn)


if __name__ == "__main__":
    run()
