# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Database Audit Script
=========================================
Ejecuta queries de diagnóstico contra la BD para encontrar mejoras.
"""
import sys, os

# Cargar .env
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

def run_audit():
    print("=" * 70)
    print("  FIN-SYS OS v2.0 — AUDITORÍA DE BASE DE DATOS")
    print("=" * 70)

    try:
        conn = connect()
        print(f"\n✅ Conectado a: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")
    except Exception as e:
        print(f"\n❌ No se pudo conectar a PostgreSQL: {e}")
        print("   Verifica que Supabase esté activo (no pausado)")
        return

    cur = conn.cursor()

    # ── 1. INVENTARIO DE TABLAS ──────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  1. INVENTARIO DE TABLAS (schema public)")
    print("─" * 70)
    cur.execute("""
        SELECT tablename,
               pg_size_pretty(pg_total_relation_size(quote_ident(tablename))) as size,
               (SELECT count(*) FROM information_schema.columns
                WHERE table_name = t.tablename AND table_schema = 'public') as cols
        FROM pg_tables t
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(quote_ident(tablename)) DESC
    """)
    tables = cur.fetchall()
    print(f"\n  Total tablas: {len(tables)}\n")
    print(f"  {'Tabla':<35} {'Tamaño':<12} {'Columnas':<8}")
    print(f"  {'─'*35} {'─'*12} {'─'*8}")
    for t in tables:
        print(f"  {t[0]:<35} {t[1]:<12} {t[2]:<8}")

    # ── 2. CONTEO DE FILAS ────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  2. CONTEO DE FILAS POR TABLA")
    print("─" * 70)
    for t in tables:
        try:
            cur.execute(f'SELECT count(*) FROM "{t[0]}"')
            count = cur.fetchone()[0]
            if count > 0:
                print(f"  {t[0]:<35} {count:>8} filas")
        except Exception:
            conn.rollback()

    # ── 3. FK SIN ÍNDICE ─────────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  3. FOREIGN KEYS SIN ÍNDICE (❌ Performance)")
    print("─" * 70)
    cur.execute("""
        SELECT
            conrelid::regclass AS tabla,
            a.attname AS columna_fk,
            confrelid::regclass AS tabla_referenciada
        FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
        WHERE c.contype = 'f'
          AND NOT EXISTS (
            SELECT 1 FROM pg_index i
            WHERE i.indrelid = c.conrelid AND a.attnum = ANY(i.indkey)
          )
        ORDER BY conrelid::regclass::text
    """)
    missing_fk_idx = cur.fetchall()
    if missing_fk_idx:
        print(f"\n  ⚠️ {len(missing_fk_idx)} FK sin índice:\n")
        for row in missing_fk_idx:
            idx_name = f"idx_{row[0]}_{row[1]}"
            print(f"  ❌ {row[0]}.{row[1]} → {row[2]}")
            print(f"     FIX: CREATE INDEX {idx_name} ON {row[0]}({row[1]});")
    else:
        print("\n  ✅ Todas las FK tienen índice")

    # ── 4. TABLAS SIN PRIMARY KEY ────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  4. TABLAS SIN PRIMARY KEY")
    print("─" * 70)
    cur.execute("""
        SELECT t.tablename
        FROM pg_tables t
        LEFT JOIN pg_constraint c
            ON c.conrelid = (quote_ident(t.tablename))::regclass
            AND c.contype = 'p'
        WHERE t.schemaname = 'public' AND c.conname IS NULL
    """)
    no_pk = cur.fetchall()
    if no_pk:
        print(f"\n  ⚠️ {len(no_pk)} tablas sin PK:")
        for t in no_pk:
            print(f"  ❌ {t[0]}")
    else:
        print("\n  ✅ Todas las tablas tienen Primary Key")

    # ── 5. COLUMNAS TIMESTAMP SIN TIMEZONE ───────────────────────────────
    print("\n" + "─" * 70)
    print("  5. COLUMNAS timestamp SIN timezone")
    print("─" * 70)
    cur.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND data_type = 'timestamp without time zone'
        ORDER BY table_name, column_name
    """)
    no_tz = cur.fetchall()
    if no_tz:
        print(f"\n  ⚠️ {len(no_tz)} columnas sin timezone:\n")
        for row in no_tz:
            print(f"  🟡 {row[0]}.{row[1]}")
    else:
        print("\n  ✅ Todas las timestamps tienen timezone")

    # ── 6. COLUMNAS SERIAL vs IDENTITY ───────────────────────────────────
    print("\n" + "─" * 70)
    print("  6. SERIAL vs IDENTITY (Primary Keys)")
    print("─" * 70)
    cur.execute("""
        SELECT table_name, column_name, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND column_default LIKE 'nextval%%'
        ORDER BY table_name
    """)
    serials = cur.fetchall()
    if serials:
        print(f"\n  ℹ️ {len(serials)} columnas usan SERIAL (nextval):\n")
        for row in serials:
            print(f"  🟡 {row[0]}.{row[1]}")
    else:
        print("\n  ✅ No se encontraron SERIAL (usan identity)")

    # ── 7. CHECK CONSTRAINTS EXISTENTES ──────────────────────────────────
    print("\n" + "─" * 70)
    print("  7. CHECK CONSTRAINTS EXISTENTES")
    print("─" * 70)
    cur.execute("""
        SELECT conrelid::regclass AS tabla, conname, pg_get_constraintdef(oid) AS definicion
        FROM pg_constraint
        WHERE contype = 'c' AND connamespace = 'public'::regnamespace
        ORDER BY conrelid::regclass::text
    """)
    checks = cur.fetchall()
    if checks:
        print(f"\n  ✅ {len(checks)} CHECK constraints:\n")
        for row in checks:
            print(f"  ✓ {row[0]}: {row[1]} → {row[2]}")
    else:
        print("\n  ⚠️ 0 CHECK constraints en toda la BD")
        print("     La BD acepta cualquier valor — solo el backend valida")

    # ── 8. COLUMNAS NULLABLE QUE PROBABLEMENTE NO DEBERÍAN SERLO ────────
    print("\n" + "─" * 70)
    print("  8. COLUMNAS POSIBLEMENTE MAL COMO NULLABLE")
    print("─" * 70)
    cur.execute("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND is_nullable = 'YES'
          AND column_name IN ('type', 'status', 'name', 'email', 'amount',
                              'portfolio_id', 'entity_id', 'member_id',
                              'transaction_date', 'due_date')
        ORDER BY table_name, column_name
    """)
    nullable_suspects = cur.fetchall()
    if nullable_suspects:
        print(f"\n  ⚠️ {len(nullable_suspects)} columnas que PODRÍAN necesitar NOT NULL:\n")
        for row in nullable_suspects:
            print(f"  🟡 {row[0]}.{row[1]} (nullable)")
    else:
        print("\n  ✅ Columnas críticas tienen NOT NULL")

    # ── 9. ÍNDICES EXISTENTES ────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  9. ÍNDICES EXISTENTES")
    print("─" * 70)
    cur.execute("""
        SELECT
            tablename,
            indexname,
            pg_size_pretty(pg_relation_size(quote_ident(indexname))) as size
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
    """)
    indexes = cur.fetchall()
    print(f"\n  Total índices: {len(indexes)}\n")
    current_table = ""
    for idx in indexes:
        if idx[0] != current_table:
            current_table = idx[0]
            print(f"\n  📋 {current_table}:")
        marker = "🔑" if "_pkey" in idx[1] else "📇"
        print(f"     {marker} {idx[1]} ({idx[2]})")

    # ── 10. TABLAS CON RLS ───────────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  10. ROW LEVEL SECURITY (RLS)")
    print("─" * 70)
    cur.execute("""
        SELECT relname, relrowsecurity
        FROM pg_class
        WHERE relnamespace = 'public'::regnamespace
          AND relkind = 'r'
        ORDER BY relname
    """)
    rls_status = cur.fetchall()
    rls_on = [r for r in rls_status if r[1]]
    rls_off = [r for r in rls_status if not r[1]]
    print(f"\n  RLS habilitado: {len(rls_on)} tablas")
    print(f"  RLS deshabilitado: {len(rls_off)} tablas")
    if rls_off:
        print(f"\n  Tablas SIN RLS:")
        for r in rls_off:
            print(f"  ❌ {r[0]}")

    # ── 11. FOREIGN KEYS TOTALES ─────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  11. RESUMEN DE FOREIGN KEYS")
    print("─" * 70)
    cur.execute("""
        SELECT
            conrelid::regclass AS from_table,
            a.attname AS from_column,
            confrelid::regclass AS to_table,
            af.attname AS to_column,
            CASE
                WHEN confdeltype = 'a' THEN 'NO ACTION'
                WHEN confdeltype = 'r' THEN 'RESTRICT'
                WHEN confdeltype = 'c' THEN 'CASCADE'
                WHEN confdeltype = 'n' THEN 'SET NULL'
                WHEN confdeltype = 'd' THEN 'SET DEFAULT'
            END AS on_delete
        FROM pg_constraint c
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
        JOIN pg_attribute af ON af.attrelid = c.confrelid AND af.attnum = ANY(c.confkey)
        WHERE c.contype = 'f'
        ORDER BY conrelid::regclass::text
    """)
    fks = cur.fetchall()
    print(f"\n  Total FK: {len(fks)}\n")
    for fk in fks:
        print(f"  {fk[0]}.{fk[1]} → {fk[2]}.{fk[3]}  (ON DELETE {fk[4]})")

    # ── RESUMEN FINAL ────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  RESUMEN AUDITORÍA")
    print("=" * 70)
    print(f"  Tablas:                {len(tables)}")
    print(f"  Índices:               {len(indexes)}")
    print(f"  Foreign Keys:          {len(fks)}")
    print(f"  FK sin índice:         {len(missing_fk_idx)} ⚠️" if missing_fk_idx else f"  FK sin índice:         0 ✅")
    print(f"  CHECK constraints:     {len(checks)}" if checks else f"  CHECK constraints:     0 ⚠️")
    print(f"  Timestamps sin TZ:     {len(no_tz)} 🟡" if no_tz else f"  Timestamps sin TZ:     0 ✅")
    print(f"  Serials (no identity): {len(serials)} 🟡" if serials else f"  Serials (no identity): 0 ✅")
    print(f"  RLS habilitado:        {len(rls_on)}/{len(rls_status)} tablas")
    print(f"  Nullable sospechosos:  {len(nullable_suspects)}" if nullable_suspects else f"  Nullable sospechosos:  0 ✅")
    print("=" * 70)

    cur.close()
    conn.close()

if __name__ == "__main__":
    run_audit()
