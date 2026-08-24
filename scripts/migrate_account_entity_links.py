"""Migración: las cuentas se vinculan a EMPRESAS (entities), no a portafolios.

Corrección conceptual del usuario (2026-08-24): los portafolios son
PRESUPUESTOS dentro de las empresas/proyectos (una empresa podrá tener
varios); "Negocio A" no es una empresa. La cuenta bancaria pertenece a la
EMPRESA (entidad del árbol de Control Tower):

    EMPRESA/proyecto (entities) ── account_entity_links ── user_accounts
        └── portafolios (presupuestos, entities.portfolio_id)
              └── pockets (siguiente capa)

Visibilidad contable derivada: una cuenta se ve en el portafolio P si está
vinculada a una empresa cuyo presupuesto es P, o si no tiene vínculos
(compartida global).

Migra los vínculos cuenta↔portafolio existentes a cuenta↔empresa usando el
vínculo empresa↔portafolio (entities.portfolio_id). Los vínculos a
portafolios sin empresa se reportan y descartan (no hay empresa dueña).

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
            CREATE TABLE IF NOT EXISTS account_entity_links (
                account_id INTEGER NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
                entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (account_id, entity_id)
            )
        """)
        # Migrar: cuenta→portafolio  ⇒  cuenta→empresa(s) cuyo presupuesto es ese portafolio
        cur.execute("""
            INSERT INTO account_entity_links (account_id, entity_id)
            SELECT DISTINCT l.account_id, e.id
            FROM account_portfolio_links l
            JOIN entities e ON e.portfolio_id = l.portfolio_id
            ON CONFLICT DO NOTHING
        """)
        migrados = cur.rowcount
        # Vínculos no resolubles (portafolio sin empresa dueña)
        cur.execute("""
            SELECT a.name, p.name
            FROM account_portfolio_links l
            JOIN user_accounts a ON a.id = l.account_id
            JOIN portfolios p ON p.id = l.portfolio_id
            WHERE NOT EXISTS (SELECT 1 FROM entities e WHERE e.portfolio_id = l.portfolio_id)
        """)
        huerfanos = cur.fetchall()
        conn.commit()

        for cuenta, port in huerfanos:
            print(f"  ⚠ {cuenta} → portafolio '{port}' sin empresa dueña — vínculo no migrado")

        cur.execute("""
            SELECT a.name, COALESCE(string_agg(e.name, ', ' ORDER BY e.name), '(compartida global)')
            FROM user_accounts a
            LEFT JOIN account_entity_links l ON l.account_id = a.id
            LEFT JOIN entities e ON e.id = l.entity_id
            GROUP BY a.id, a.name ORDER BY a.id
        """)
        for nombre, links in cur.fetchall():
            print(f"  ✓ {nombre} → {links}")
        cur.close()
        print(f"RESULTADO: OK — {migrados} vínculo(s) migrados a empresas")
        return 0
    finally:
        put_conn(conn)


if __name__ == "__main__":
    sys.exit(main())
