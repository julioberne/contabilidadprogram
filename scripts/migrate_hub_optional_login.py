# -*- coding: utf-8 -*-
"""
migrate_hub_optional_login.py — Hace opcionales email y password en hub_users.

Modelo "roster RRHH, login opcional": una persona puede existir solo con nombre
(ficha de personal para RRHH/nómina) sin ser una cuenta con login. Si más tarde
se le da acceso al sistema, se le asignan email + contraseña.

Idempotente: se puede correr las veces que sea. Postgres permite múltiples NULL
bajo un UNIQUE, así que varios trabajadores sin email conviven sin chocar.

Uso:  python scripts/migrate_hub_optional_login.py
"""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_env():
    """Carga .env a os.environ sin depender de python-dotenv."""
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
            cur.execute("ALTER TABLE hub_users ALTER COLUMN email DROP NOT NULL;")
            cur.execute("ALTER TABLE hub_users ALTER COLUMN password_hash DROP NOT NULL;")
        conn.commit()
        print("OK — hub_users.email y hub_users.password_hash ahora son opcionales.")
    finally:
        put_conn(conn)


if __name__ == "__main__":
    run()
