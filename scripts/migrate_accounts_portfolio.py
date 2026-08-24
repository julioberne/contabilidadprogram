"""Migración: cuentas financieras por portafolio (separación multi-empresa).

Problema real (2026-08-10): user_accounts era GLOBAL — todas las empresas
"veían" las mismas cuentas y el mismo patrimonio, pero no todas las empresas
tienen las mismas cuentas ni los mismos valores.

Orden correcto de separación por portafolio (cada portafolio = un libro):
  1. user_accounts.portfolio_id (esta migración)  → cuentas y su patrimonio
  2. transactions ya tienen portfolio_id           → libro diario/mayor
  3. cxp_cxc_ledger deriva de transactions         → cartera hereda el vínculo
  4. assets/inventario                             → siguiente iteración

portfolio_id NULL = cuenta COMPARTIDA (visible en todos los portafolios).
Las cuentas existentes quedan compartidas; se asignan desde 💳 Cuentas → ✎.

Idempotente: ADD COLUMN IF NOT EXISTS.
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
            ALTER TABLE user_accounts
            ADD COLUMN IF NOT EXISTS portfolio_id INTEGER
                REFERENCES portfolios(id) ON DELETE SET NULL
        """)
        conn.commit()
        cur.execute("""
            SELECT a.name, COALESCE(p.name, '(compartida)')
            FROM user_accounts a LEFT JOIN portfolios p ON p.id = a.portfolio_id
            ORDER BY a.id
        """)
        for nombre, port in cur.fetchall():
            print(f"  ✓ {nombre} → {port}")
        cur.close()
        print("RESULTADO: OK — user_accounts.portfolio_id disponible")
        return 0
    finally:
        put_conn(conn)


if __name__ == "__main__":
    sys.exit(main())
