# -*- coding: utf-8 -*-
"""Migración: recursos/activos vinculados a la EMPRESA (entities) — aditiva.
    .venv\Scripts\python.exe scripts\migrate_assets_entity.py
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
conn = get_conn()
try:
    cur = conn.cursor()
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS entity_id BIGINT REFERENCES entities(id) ON DELETE SET NULL")
    conn.commit(); cur.close()
finally:
    put_conn(conn)
print("✅ assets.entity_id lista.")
