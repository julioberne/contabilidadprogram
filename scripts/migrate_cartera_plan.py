# -*- coding: utf-8 -*-
"""Migración: Plan de pagos en cartera (Fase 1 — modo préstamo).

Aditiva e idempotente (ADD COLUMN IF NOT EXISTS). Ejecutar ANTES del deploy:
    .venv\\Scripts\\python.exe scripts\\migrate_cartera_plan.py

- cxp_cxc_ledger.min_payment       cuota mínima exigida por corte (NULL = sin plan)
- cxp_cxc_ledger.interest_rate     tasa % (NULL/0 = sin interés)
- cxp_cxc_ledger.interest_period   'MENSUAL' | 'ANUAL' (base 30/365 días)
- cartera_payments.interest_part   parte del abono aplicada a interés
- cartera_payments.principal_part  parte del abono aplicada a capital
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "fin_sys_core"))

with open(".env", encoding="utf-8-sig") as f:
    for line in f:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from db_pool import get_conn, put_conn  # noqa: E402

DDL = [
    "ALTER TABLE cxp_cxc_ledger ADD COLUMN IF NOT EXISTS min_payment NUMERIC(15,2)",
    "ALTER TABLE cxp_cxc_ledger ADD COLUMN IF NOT EXISTS interest_rate NUMERIC(8,4)",
    "ALTER TABLE cxp_cxc_ledger ADD COLUMN IF NOT EXISTS interest_period VARCHAR(10) DEFAULT 'MENSUAL'",
    "ALTER TABLE cartera_payments ADD COLUMN IF NOT EXISTS interest_part NUMERIC(15,2)",
    "ALTER TABLE cartera_payments ADD COLUMN IF NOT EXISTS principal_part NUMERIC(15,2)",
]

conn = get_conn()
try:
    cur = conn.cursor()
    for ddl in DDL:
        cur.execute(ddl)
        print("OK:", ddl)
    conn.commit()
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'cxp_cxc_ledger'
          AND column_name IN ('min_payment', 'interest_rate', 'interest_period')
    """)
    print("Verificado cxp_cxc_ledger:", sorted(r[0] for r in cur.fetchall()))
    cur.close()
finally:
    put_conn(conn)
print("✅ Migración cartera_plan aplicada.")
