# -*- coding: utf-8 -*-
"""Migración 2026-09-09 — Bot Etapa E (fotos + botones).

Columna ADITIVA en transaction_drafts:

    bot_summary_message_id TEXT  — message_id del mensaje-resumen que el bot
    envió al chat. Permite (a) adjuntar una foto respondiendo a ese mensaje
    (reply-to → borrador exacto) y (b) editar el mensaje al confirmar por
    botón. Nullable: los borradores viejos y los de la web no lo tienen.

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
        cur.execute("""
            ALTER TABLE transaction_drafts
            ADD COLUMN IF NOT EXISTS bot_summary_message_id TEXT;
        """)
        conn.commit()
        cur.execute("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_name = 'transaction_drafts'
              AND column_name = 'bot_summary_message_id';
        """)
        print("✅ Columna:", cur.fetchone())
    finally:
        put_conn(conn)


if __name__ == "__main__":
    main()
