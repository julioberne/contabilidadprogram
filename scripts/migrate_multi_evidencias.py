# -*- coding: utf-8 -*-
"""Migración 2026-09-08 — Múltiples evidencias por transacción (Etapa E.3).

Pedido de Andrés: "a veces necesito 2 o 3 fotos, o foto + PDF".

Cambios ADITIVOS (idempotentes):
1. transaction_drafts.media_paths JSONB — lista de URLs de evidencia del
   borrador. media_path (singular) se conserva = la primera, por compat
   con la bandeja y el flujo viejo.
2. Tabla transaction_evidences — N evidencias por transacción confirmada.
   transactions.evidence_file_path se conserva = la primera (el Libro, el
   comprobante y el kernel siguen leyendo ese campo sin cambios).
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
        cur.execute("""
            ALTER TABLE transaction_drafts
            ADD COLUMN IF NOT EXISTS media_paths JSONB;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transaction_evidences (
                id SERIAL PRIMARY KEY,
                transaction_id INTEGER NOT NULL
                    REFERENCES transactions(id) ON DELETE CASCADE,
                file_path TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tx_evidences_tx
            ON transaction_evidences (transaction_id);
        """)
        conn.commit()
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'transaction_drafts' AND column_name = 'media_paths';
        """)
        print("✅ transaction_drafts.media_paths:", cur.fetchone())
        cur.execute("SELECT COUNT(*) FROM transaction_evidences")
        print("✅ transaction_evidences filas:", cur.fetchone()[0])
    finally:
        put_conn(conn)


if __name__ == "__main__":
    main()
