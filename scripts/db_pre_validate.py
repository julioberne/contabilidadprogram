# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Pre-validación antes de aplicar mejoras
============================================================
Verifica que los datos existentes no violen los constraints
que vamos a agregar. EJECUTAR ANTES de aplicar el SQL.
"""
import sys, os

if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            ls = line.strip()
            if ls and not ls.startswith("#") and "=" in ls:
                key, val = ls.split("=", 1)
                os.environ[key.strip()] = val.strip()

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fin_sys_core"))
import psycopg2

def connect():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        port=os.getenv("DB_PORT", "5432"),
        connect_timeout=15,
    )

def validate():
    print("=" * 70)
    print("  PRE-VALIDACIÓN — ¿Los datos actuales cumplen los constraints?")
    print("=" * 70)

    try:
        conn = connect()
        print(f"\n✅ Conectado a: {os.getenv('DB_HOST')}")
    except Exception as e:
        print(f"\n❌ No se pudo conectar: {e}")
        return False

    cur = conn.cursor()
    all_ok = True

    checks = [
        # (descripción, query que debe retornar 0 filas para pasar)
        (
            "transactions.type IN ('INGRESO','GASTO','TRANSFERENCIA')",
            "SELECT id, type FROM transactions WHERE type NOT IN ('INGRESO','GASTO','TRANSFERENCIA')"
        ),
        (
            "transactions.amount > 0",
            "SELECT id, amount FROM transactions WHERE amount <= 0"
        ),
        (
            "cxp_cxc_ledger.type IN ('CXC','CXP')",
            "SELECT id, type FROM cxp_cxc_ledger WHERE type NOT IN ('CXC','CXP')"
        ),
        (
            "cxp_cxc_ledger.status válido",
            "SELECT id, status FROM cxp_cxc_ledger WHERE status NOT IN ('PENDIENTE','PARCIAL','PAGADO','VENCIDO')"
        ),
        (
            "cxp_cxc_ledger.original_amount > 0",
            "SELECT id, original_amount FROM cxp_cxc_ledger WHERE original_amount <= 0"
        ),
        (
            "cxp_cxc_ledger.remaining_balance >= 0",
            "SELECT id, remaining_balance FROM cxp_cxc_ledger WHERE remaining_balance < 0"
        ),
        (
            "entities.type válido",
            "SELECT id, type FROM entities WHERE type NOT IN ('HOLDING','EMPRESA','SUB_EMPRESA','PROYECTO','TAREA')"
        ),
        (
            "entities.status válido",
            "SELECT id, status FROM entities WHERE status NOT IN ('AL DIA','ALERTA','MOROSO')"
        ),
        (
            "user_accounts.currency IN ('COP','USD')",
            "SELECT id, currency FROM user_accounts WHERE currency NOT IN ('COP','USD')"
        ),
    ]

    print(f"\n  Verificando {len(checks)} reglas...\n")

    for desc, query in checks:
        try:
            cur.execute(query)
            violations = cur.fetchall()
            if violations:
                all_ok = False
                print(f"  ❌ FALLA: {desc}")
                print(f"     → {len(violations)} filas violan la regla:")
                for v in violations[:5]:
                    print(f"       ID={v[0]}, valor='{v[1]}'")
                if len(violations) > 5:
                    print(f"       ... y {len(violations)-5} más")
            else:
                print(f"  ✅ OK: {desc}")
        except Exception as e:
            print(f"  ⚠️ ERROR verificando '{desc}': {e}")
            conn.rollback()

    # Verificar que los índices no existan ya
    print(f"\n{'─'*70}")
    print("  Verificando índices existentes que NO necesitan crearse...")
    print(f"{'─'*70}\n")

    idx_to_create = [
        ("idx_assets_portfolio", "assets", "portfolio_id"),
        ("idx_pockets_portfolio", "pockets", "portfolio_id"),
        ("idx_tx_third_party", "transactions", "third_party_id"),
        ("idx_tx_account", "transactions", "account_id"),
        ("idx_cxp_third_party", "cxp_cxc_ledger", "third_party_id"),
        ("idx_cxp_transaction", "cxp_cxc_ledger", "transaction_id"),
        ("idx_approvals_entity_id", "approvals_queue", "entity_id"),
        ("idx_entities_created_by", "entities", "created_by"),
        ("idx_entities_portfolio", "entities", "portfolio_id"),
        ("idx_members_entity", "entity_members", "entity_id"),
        ("idx_members_user", "entity_members", "user_id"),
        ("idx_resources_entity", "resource_ids", "entity_id"),
    ]

    existing = 0
    needed = 0
    for idx_name, table, col in idx_to_create:
        cur.execute("""
            SELECT 1 FROM pg_indexes
            WHERE tablename = %s AND indexdef LIKE %s
        """, (table, f"%({col})%"))
        if cur.fetchone():
            existing += 1
            print(f"  ⏭️ YA EXISTE índice en {table}.{col}")
        else:
            needed += 1
            print(f"  📝 NECESITA índice: {table}.{col}")

    print(f"\n  Resumen: {existing} ya existen, {needed} necesitan crearse")

    # Verificar CHECK constraints existentes
    print(f"\n{'─'*70}")
    print("  Verificando CHECK constraints existentes...")
    print(f"{'─'*70}\n")

    cur.execute("""
        SELECT conrelid::regclass, conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE contype = 'c' AND connamespace = 'public'::regnamespace
    """)
    existing_checks = cur.fetchall()
    if existing_checks:
        for c in existing_checks:
            print(f"  ✓ {c[0]}: {c[1]}")
    else:
        print("  ℹ️ 0 CHECK constraints existentes — todos son nuevos")

    print(f"\n{'='*70}")
    if all_ok:
        print("  ✅ VALIDACIÓN COMPLETA — Los datos actuales cumplen TODAS las reglas")
        print("  → Es SEGURO aplicar los CHECK constraints")
    else:
        print("  ⚠️ HAY VIOLACIONES — Corregir los datos ANTES de agregar constraints")
    print(f"{'='*70}")

    cur.close()
    conn.close()
    return all_ok

if __name__ == "__main__":
    validate()
