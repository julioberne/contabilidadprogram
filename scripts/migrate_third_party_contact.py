# -*- coding: utf-8 -*-
"""Migración: dirección y link de Maps en terceros (aditiva, idempotente).
    .venv\Scripts\python.exe scripts\migrate_third_party_contact.py
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "fin_sys_core"))
with open(".env", encoding="utf-8-sig") as f:
    for line in f:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
from db_pool import get_conn, put_conn
DDL = [
    "ALTER TABLE third_parties ADD COLUMN IF NOT EXISTS address TEXT",
    "ALTER TABLE third_parties ADD COLUMN IF NOT EXISTS maps_link TEXT",
]
conn = get_conn()
try:
    cur = conn.cursor()
    for d in DDL:
        cur.execute(d); print("OK:", d)
    conn.commit(); cur.close()
finally:
    put_conn(conn)
print("✅ Migración third_party_contact aplicada.")
