# -*- coding: utf-8 -*-
"""Migración 2026-09-09 — Tablas del módulo Inventario (Fase 4).

El driver (inventory_driver.py) llevaba meses operando contra
inventory_items / inventory_movements… que NUNCA se crearon en la BD.
Nadie lo notó porque el fallback MOCK silencioso fingía guardar; al
cerrarse DT-28 (error visible, jamás datos falsos) el fantasma quedó al
descubierto: 'relation "inventory_items" does not exist' (reporte de
Andrés al agregar un ítem).

Esquema derivado 1:1 de las queries reales del driver. Idempotente.
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
            CREATE TABLE IF NOT EXISTS inventory_items (
                id SERIAL PRIMARY KEY,
                portfolio_name TEXT NOT NULL,
                company_id INTEGER REFERENCES entities(id) ON DELETE SET NULL,
                name TEXT NOT NULL,
                sku TEXT DEFAULT '',
                category TEXT DEFAULT 'General',
                unit TEXT DEFAULT 'unidad',
                cost_price NUMERIC(14,2) DEFAULT 0,
                sell_price NUMERIC(14,2) DEFAULT 0,
                current_stock NUMERIC(14,2) DEFAULT 0,
                min_stock NUMERIC(14,2) DEFAULT 0,
                status TEXT DEFAULT 'ACTIVO',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_movements (
                id SERIAL PRIMARY KEY,
                item_id INTEGER NOT NULL
                    REFERENCES inventory_items(id) ON DELETE CASCADE,
                type TEXT NOT NULL,
                quantity NUMERIC(14,2) NOT NULL,
                unit_price NUMERIC(14,2) DEFAULT 0,
                total NUMERIC(14,2) DEFAULT 0,
                reference TEXT,
                transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
                third_party_id INTEGER REFERENCES third_parties(id) ON DELETE SET NULL,
                notes TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_inv_items_portfolio
            ON inventory_items (portfolio_name, company_id);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_inv_movs_item
            ON inventory_movements (item_id);
        """)
        conn.commit()
        for t in ("inventory_items", "inventory_movements"):
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            print(f"✅ {t}: lista ({cur.fetchone()[0]} filas)")
    finally:
        put_conn(conn)


if __name__ == "__main__":
    main()
