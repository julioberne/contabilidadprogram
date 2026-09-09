# -*- coding: utf-8 -*-
"""Migración 2026-09-09 — Nota breve del comprobante (pedido de Andrés).

transactions.note TEXT (nullable, opcional): descripción/observación libre
que se escribe y se ve en el Visualizador de Evidencia. Límite de 280
caracteres aplicado en el contrato (pydantic) y en la UI. Idempotente.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from fin_sys_core.db_pool import get_conn, put_conn  # noqa: E402


def main():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS note TEXT;")
        conn.commit()
        cur.execute("""SELECT column_name FROM information_schema.columns
                       WHERE table_name='transactions' AND column_name='note';""")
        print("✅ transactions.note:", cur.fetchone())
    finally:
        put_conn(conn)


if __name__ == "__main__":
    main()
