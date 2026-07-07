# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Aplicar mejoras progresivas a la BD
========================================================
Ejecuta: corrección de datos + índices FK + CHECK constraints
directamente contra Supabase via psycopg2.
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

# ══════════════════════════════════════════════════════════════════
# Definición de todos los cambios a aplicar
# ══════════════════════════════════════════════════════════════════

PASO_0_FIX_DATA = [
    ("FIX entities 'SUBSIDIARIA' → 'SUB_EMPRESA'",
     "UPDATE entities SET type = 'SUB_EMPRESA' WHERE type = 'SUBSIDIARIA'"),
]

PASO_1_INDICES = [
    # Core
    ("idx_assets_portfolio", "CREATE INDEX IF NOT EXISTS idx_assets_portfolio ON assets(portfolio_id)"),
    ("idx_pockets_portfolio", "CREATE INDEX IF NOT EXISTS idx_pockets_portfolio ON pockets(portfolio_id)"),
    ("idx_tx_third_party", "CREATE INDEX IF NOT EXISTS idx_tx_third_party ON transactions(third_party_id)"),
    ("idx_tx_pocket", "CREATE INDEX IF NOT EXISTS idx_tx_pocket ON transactions(pocket_id)"),
    ("idx_tx_account", "CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id)"),
    ("idx_tx_dest_account", "CREATE INDEX IF NOT EXISTS idx_tx_dest_account ON transactions(dest_account_id)"),
    ("idx_cxp_third_party", "CREATE INDEX IF NOT EXISTS idx_cxp_third_party ON cxp_cxc_ledger(third_party_id)"),
    ("idx_cxp_transaction", "CREATE INDEX IF NOT EXISTS idx_cxp_transaction ON cxp_cxc_ledger(transaction_id)"),
    ("idx_cartera_payments_ledger", "CREATE INDEX IF NOT EXISTS idx_cartera_payments_ledger ON cartera_payments(ledger_id)"),
    ("idx_coa_parent", "CREATE INDEX IF NOT EXISTS idx_coa_parent ON chart_of_accounts(parent_id)"),
    ("idx_posting_rules_portfolio", "CREATE INDEX IF NOT EXISTS idx_posting_rules_portfolio ON posting_rules(portfolio_id)"),
    # Control Tower
    ("idx_approvals_entity_id", "CREATE INDEX IF NOT EXISTS idx_approvals_entity_id ON approvals_queue(entity_id)"),
    ("idx_approvals_tx_id", "CREATE INDEX IF NOT EXISTS idx_approvals_tx_id ON approvals_queue(transaction_id)"),
    ("idx_approvals_requested", "CREATE INDEX IF NOT EXISTS idx_approvals_requested ON approvals_queue(requested_by)"),
    ("idx_approvals_reviewed", "CREATE INDEX IF NOT EXISTS idx_approvals_reviewed ON approvals_queue(reviewed_by)"),
    ("idx_entities_created_by", "CREATE INDEX IF NOT EXISTS idx_entities_created_by ON entities(created_by)"),
    ("idx_entities_portfolio", "CREATE INDEX IF NOT EXISTS idx_entities_portfolio ON entities(portfolio_id)"),
    ("idx_members_entity", "CREATE INDEX IF NOT EXISTS idx_members_entity ON entity_members(entity_id)"),
    ("idx_members_user", "CREATE INDEX IF NOT EXISTS idx_members_user ON entity_members(user_id)"),
    ("idx_resources_entity", "CREATE INDEX IF NOT EXISTS idx_resources_entity ON resource_ids(entity_id)"),
    ("idx_wu_parent", "CREATE INDEX IF NOT EXISTS idx_wu_parent ON workspace_users(parent_user_id)"),
    # RRHH
    ("idx_hr_docs_folder", "CREATE INDEX IF NOT EXISTS idx_hr_docs_folder ON hr_documents(folder_id)"),
    ("idx_hr_folders_parent", "CREATE INDEX IF NOT EXISTS idx_hr_folders_parent ON hr_folders(parent_id)"),
    ("idx_hr_pay_voucher", "CREATE INDEX IF NOT EXISTS idx_hr_pay_voucher ON hr_payment_records(voucher_document_id)"),
    # Hub
    ("idx_hub_entities_ws", "CREATE INDEX IF NOT EXISTS idx_hub_entities_ws ON hub_entities(workspace_id)"),
    ("idx_hub_entities_parent", "CREATE INDEX IF NOT EXISTS idx_hub_entities_parent ON hub_entities(parent_id)"),
    ("idx_hub_events_ws", "CREATE INDEX IF NOT EXISTS idx_hub_events_ws ON hub_events(workspace_id)"),
    ("idx_hub_events_created", "CREATE INDEX IF NOT EXISTS idx_hub_events_created ON hub_events(created_by)"),
    ("idx_hub_events_project", "CREATE INDEX IF NOT EXISTS idx_hub_events_project ON hub_events(project_id)"),
    ("idx_hub_notes_ws", "CREATE INDEX IF NOT EXISTS idx_hub_notes_ws ON hub_notes(workspace_id)"),
    ("idx_hub_notes_user", "CREATE INDEX IF NOT EXISTS idx_hub_notes_user ON hub_notes(user_id)"),
    ("idx_hub_notes_project", "CREATE INDEX IF NOT EXISTS idx_hub_notes_project ON hub_notes(project_id)"),
    ("idx_hub_projects_ws", "CREATE INDEX IF NOT EXISTS idx_hub_projects_ws ON hub_projects(workspace_id)"),
    ("idx_hub_projects_entity", "CREATE INDEX IF NOT EXISTS idx_hub_projects_entity ON hub_projects(entity_id)"),
    ("idx_hub_projects_created", "CREATE INDEX IF NOT EXISTS idx_hub_projects_created ON hub_projects(created_by)"),
    ("idx_hub_tasks_ws", "CREATE INDEX IF NOT EXISTS idx_hub_tasks_ws ON hub_tasks(workspace_id)"),
    ("idx_hub_tasks_project", "CREATE INDEX IF NOT EXISTS idx_hub_tasks_project ON hub_tasks(project_id)"),
    ("idx_hub_tasks_created", "CREATE INDEX IF NOT EXISTS idx_hub_tasks_created ON hub_tasks(created_by)"),
    ("idx_hub_task_assign_task", "CREATE INDEX IF NOT EXISTS idx_hub_task_assign_task ON hub_task_assignees(task_id)"),
    ("idx_hub_task_assign_user", "CREATE INDEX IF NOT EXISTS idx_hub_task_assign_user ON hub_task_assignees(user_id)"),
    ("idx_hub_event_att_event", "CREATE INDEX IF NOT EXISTS idx_hub_event_att_event ON hub_event_attendees(event_id)"),
    ("idx_hub_event_att_user", "CREATE INDEX IF NOT EXISTS idx_hub_event_att_user ON hub_event_attendees(user_id)"),
    ("idx_hub_ws_members_ws", "CREATE INDEX IF NOT EXISTS idx_hub_ws_members_ws ON hub_workspace_members(workspace_id)"),
    ("idx_hub_ws_members_user", "CREATE INDEX IF NOT EXISTS idx_hub_ws_members_user ON hub_workspace_members(user_id)"),
]

PASO_2_CHECKS = [
    ("chk_tx_type",
     "ALTER TABLE transactions ADD CONSTRAINT chk_tx_type CHECK (type IN ('INGRESO', 'GASTO', 'TRANSFERENCIA'))"),
    ("chk_tx_positive_amount",
     "ALTER TABLE transactions ADD CONSTRAINT chk_tx_positive_amount CHECK (amount > 0)"),
    ("chk_ledger_type",
     "ALTER TABLE cxp_cxc_ledger ADD CONSTRAINT chk_ledger_type CHECK (type IN ('CXC', 'CXP'))"),
    ("chk_ledger_status",
     "ALTER TABLE cxp_cxc_ledger ADD CONSTRAINT chk_ledger_status CHECK (status IN ('PENDIENTE', 'PARCIAL', 'PAGADO', 'VENCIDO'))"),
    ("chk_cxp_positive",
     "ALTER TABLE cxp_cxc_ledger ADD CONSTRAINT chk_cxp_positive CHECK (original_amount > 0 AND remaining_balance >= 0)"),
    ("chk_entity_type",
     "ALTER TABLE entities ADD CONSTRAINT chk_entity_type CHECK (type IN ('HOLDING', 'EMPRESA', 'SUB_EMPRESA', 'PROYECTO', 'TAREA'))"),
    ("chk_entity_status",
     "ALTER TABLE entities ADD CONSTRAINT chk_entity_status CHECK (status IN ('AL DIA', 'ALERTA', 'MOROSO'))"),
    ("chk_currency",
     "ALTER TABLE user_accounts ADD CONSTRAINT chk_currency CHECK (currency IN ('COP', 'USD'))"),
]


def apply():
    print("=" * 70)
    print("  FIN-SYS OS v2.0 — APLICAR MEJORAS A LA BD")
    print("=" * 70)

    try:
        conn = connect()
        conn.autocommit = False
        print(f"\n✅ Conectado a: {os.getenv('DB_HOST')}")
    except Exception as e:
        print(f"\n❌ No se pudo conectar: {e}")
        return

    cur = conn.cursor()
    errors = []

    # ── PASO 0: FIX DATA ──
    print(f"\n{'─'*70}")
    print("  PASO 0: Corrección de datos")
    print(f"{'─'*70}")
    for name, sql in PASO_0_FIX_DATA:
        try:
            cur.execute(sql)
            print(f"  ✅ {name} → {cur.rowcount} filas actualizadas")
        except Exception as e:
            errors.append((name, str(e)))
            print(f"  ❌ {name}: {e}")
            conn.rollback()

    if not errors:
        conn.commit()
        print("  💾 Commit OK")

    # ── PASO 1: ÍNDICES ──
    print(f"\n{'─'*70}")
    print(f"  PASO 1: Crear {len(PASO_1_INDICES)} índices en FK")
    print(f"{'─'*70}")
    created = 0
    skipped = 0
    for name, sql in PASO_1_INDICES:
        try:
            # Check if exists first
            cur.execute("SELECT 1 FROM pg_indexes WHERE indexname = %s", (name,))
            if cur.fetchone():
                skipped += 1
                continue
            cur.execute(sql)
            conn.commit()
            created += 1
            print(f"  ✅ {name}")
        except Exception as e:
            errors.append((name, str(e)))
            print(f"  ❌ {name}: {e}")
            conn.rollback()

    print(f"\n  📊 Índices: {created} creados, {skipped} ya existían, {len([e for e in errors if 'idx_' in e[0]])} errores")

    # ── PASO 2: CHECK CONSTRAINTS ──
    print(f"\n{'─'*70}")
    print(f"  PASO 2: Agregar {len(PASO_2_CHECKS)} CHECK constraints")
    print(f"{'─'*70}")
    created_chk = 0
    for name, sql in PASO_2_CHECKS:
        try:
            # Check if exists
            cur.execute("""
                SELECT 1 FROM pg_constraint
                WHERE conname = %s AND connamespace = 'public'::regnamespace
            """, (name,))
            if cur.fetchone():
                print(f"  ⏭️ {name} (ya existe)")
                continue
            cur.execute(sql)
            conn.commit()
            created_chk += 1
            print(f"  ✅ {name}")
        except Exception as e:
            errors.append((name, str(e)))
            print(f"  ❌ {name}: {e}")
            conn.rollback()

    # ── VERIFICACIÓN ──
    print(f"\n{'─'*70}")
    print("  VERIFICACIÓN FINAL")
    print(f"{'─'*70}")

    cur.execute("""
        SELECT count(*) FROM pg_indexes
        WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
    """)
    total_idx = cur.fetchone()[0]

    cur.execute("""
        SELECT count(*) FROM pg_constraint
        WHERE contype = 'c' AND connamespace = 'public'::regnamespace
    """)
    total_chk = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM entities WHERE type = 'SUBSIDIARIA'")
    subsidiaria_count = cur.fetchone()[0]

    # FK sin índice (solo tablas del usuario, no auth.* ni storage.*)
    cur.execute("""
        SELECT count(*)
        FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
        WHERE c.contype = 'f'
          AND c.conrelid::regclass::text NOT LIKE 'auth.%'
          AND c.conrelid::regclass::text NOT LIKE 'storage.%'
          AND NOT EXISTS (
            SELECT 1 FROM pg_index i
            WHERE i.indrelid = c.conrelid AND a.attnum = ANY(i.indkey)
          )
    """)
    fk_sin_idx = cur.fetchone()[0]

    print(f"\n  Índices personalizados (idx_*):  {total_idx}")
    print(f"  CHECK constraints:              {total_chk}")
    print(f"  Entities con 'SUBSIDIARIA':     {subsidiaria_count}")
    print(f"  FK sin índice (tus tablas):     {fk_sin_idx}")

    # ── RESUMEN ──
    print(f"\n{'='*70}")
    if not errors:
        print("  ✅ TODAS LAS MEJORAS APLICADAS EXITOSAMENTE")
    else:
        print(f"  ⚠️ {len(errors)} errores encontrados:")
        for name, err in errors:
            print(f"     ❌ {name}: {err}")
    print(f"{'='*70}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    apply()
