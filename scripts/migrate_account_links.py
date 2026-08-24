"""Migración: vínculos N:M cuenta ↔ portafolio (account_portfolio_links).

Evolución del modelo (pedido del usuario 2026-08-24): una misma cuenta puede
estar COMPARTIDA por varias empresas/proyectos, y cada empresa puede crear y
vincular sus propias cuentas. El portfolio_id 1:1 de user_accounts se queda
corto — se reemplaza por una tabla de vínculos:

    sin filas para una cuenta  = compartida GLOBAL (visible en todos)
    con filas                  = visible SOLO en esos portafolios

Los vínculos existentes en user_accounts.portfolio_id se migran a la tabla
(la columna vieja queda sin uso; se conserva por compatibilidad).

Jerarquía contable completa (siguientes capas): empresa → proyecto →
portafolio → pockets (bolsillos internos, transactions.pocket_id ya existe).

Idempotente.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _, _val = _line.partition('=')
                os.environ.setdefault(_key.strip(), _val.strip().strip('"').strip("'"))

from fin_sys_core.db_pool import get_conn, put_conn


def main():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS account_portfolio_links (
                account_id INTEGER NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
                portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (account_id, portfolio_id)
            )
        """)
        # Migrar los vínculos 1:1 existentes
        cur.execute("""
            INSERT INTO account_portfolio_links (account_id, portfolio_id)
            SELECT id, portfolio_id FROM user_accounts WHERE portfolio_id IS NOT NULL
            ON CONFLICT DO NOTHING
        """)
        migrados = cur.rowcount
        conn.commit()

        cur.execute("""
            SELECT a.name, COALESCE(string_agg(p.name, ', ' ORDER BY p.name), '(compartida global)')
            FROM user_accounts a
            LEFT JOIN account_portfolio_links l ON l.account_id = a.id
            LEFT JOIN portfolios p ON p.id = l.portfolio_id
            GROUP BY a.id, a.name ORDER BY a.id
        """)
        for nombre, links in cur.fetchall():
            print(f"  ✓ {nombre} → {links}")
        cur.close()
        print(f"RESULTADO: OK — tabla de vínculos lista ({migrados} vínculo(s) migrados)")
        return 0
    finally:
        put_conn(conn)


if __name__ == "__main__":
    sys.exit(main())
