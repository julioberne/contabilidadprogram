# -*- coding: utf-8 -*-
"""Migración 2026-09-08 — Etiquetas por transacción (pedido de Andrés).

El formulario web ya enviaba `tags` y la bandeja del bot ya las editaba,
pero el backend las descartaba (TransactionInput sin campo, INSERT sin
columna). Columna nueva ADITIVA:

    transactions.tags TEXT[]  (nullable — las TXs viejas quedan sin tags)

Idempotente: IF NOT EXISTS.
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
        cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS tags TEXT[];")
        conn.commit()
        cur.execute("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_name = 'transactions' AND column_name = 'tags';
        """)
        print("✅ Columna:", cur.fetchone())
    finally:
        put_conn(conn)


if __name__ == "__main__":
    main()
