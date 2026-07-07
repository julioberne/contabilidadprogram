"""
migrate_company_id.py — Migración: Agregar company_id a tablas core

Agrega columna company_id (FK → entities.id) a:
  - transactions
  - pockets
  - assets
  - chart_of_accounts

Pobla company_id usando el mapeo entities.portfolio_id → portfolio_id existente.
NO elimina portfolio_id — coexistencia temporal.

Uso:
    python scripts/migrate_company_id.py --dry-run   # Solo muestra el plan
    python scripts/migrate_company_id.py             # Ejecuta la migración
"""

import os
import sys
import argparse

# ── Conexión a Supabase ──────────────────────────────────────
def get_connection():
    """Conectar a PostgreSQL usando las mismas variables de entorno que db_pool.py."""
    try:
        import psycopg2

        # Usar las mismas env vars que db_pool.py
        host = os.getenv("DB_HOST", "localhost")
        dbname = os.getenv("DB_NAME", "fin_sys_db")
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "postgres")
        port = os.getenv("DB_PORT", "5432")

        return psycopg2.connect(
            host=host, port=port, dbname=dbname,
            user=user, password=password,
            connect_timeout=10,
        )
    except ImportError:
        print("❌ psycopg2 no instalado. Ejecuta: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print(f"   Variables: DB_HOST={os.getenv('DB_HOST','?')} DB_PORT={os.getenv('DB_PORT','?')} DB_NAME={os.getenv('DB_NAME','?')}")
        print(f"   Asegúrate de que el backend (server.py) pueda conectar a la misma BD.")
        sys.exit(1)


# ── Tablas a migrar ──────────────────────────────────────────
TABLES = [
    "transactions",
    "pockets",
    "assets",
    "chart_of_accounts",
]


def check_column_exists(cur, table, column):
    """Verificar si una columna ya existe en una tabla."""
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        )
    """, (table, column))
    return cur.fetchone()[0]


def check_table_exists(cur, table):
    """Verificar si una tabla existe."""
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = %s
        )
    """, (table,))
    return cur.fetchone()[0]


def run_migration(dry_run=False):
    """Ejecutar la migración."""
    conn = get_connection()
    cur = conn.cursor()

    print("=" * 66)
    print("  MIGRACIÓN: portfolio_id → company_id (coexistencia)")
    print(f"  Modo: {'DRY-RUN (no se ejecuta nada)' if dry_run else '⚡ EJECUCIÓN REAL'}")
    print("=" * 66)
    print()

    # ── Paso 0: Verificar que entities existe ────────────────
    if not check_table_exists(cur, "entities"):
        print("❌ La tabla 'entities' no existe. Ejecuta primero el módulo Control Tower.")
        cur.close()
        conn.close()
        return

    # Contar entities
    cur.execute("SELECT COUNT(*) FROM entities")
    entity_count = cur.fetchone()[0]
    print(f"✅ Tabla 'entities' encontrada ({entity_count} registros)")

    # Mostrar mapeo entities.portfolio_id
    cur.execute("SELECT id, name, type, portfolio_id, industry FROM entities ORDER BY id")
    entities = cur.fetchall()
    print("\n  MAPEO entities → portfolio_id:")
    for ent in entities:
        pid = ent[3] if ent[3] else "—"
        ind = ent[4] if ent[4] else "—"
        print(f"    Entity #{ent[0]:3d} | {ent[1]:30s} | {ent[2]:12s} | portfolio={pid} | industry={ind}")
    print()

    # ── Paso 1: ADD COLUMN company_id ────────────────────────
    for table in TABLES:
        if not check_table_exists(cur, table):
            print(f"⚠️  Tabla '{table}' no existe — omitida")
            continue

        if check_column_exists(cur, table, "company_id"):
            print(f"✅ {table}.company_id ya existe — omitida")
        else:
            sql_add = f"""
                ALTER TABLE {table}
                ADD COLUMN company_id INTEGER REFERENCES entities(id);
            """
            print(f"{'🔍' if dry_run else '⚡'} ALTER TABLE {table} ADD COLUMN company_id INTEGER REFERENCES entities(id)")
            if not dry_run:
                cur.execute(sql_add)

    print()

    # ── Paso 2: Poblar company_id desde entities.portfolio_id ─
    has_portfolio_id_col = {}
    for table in TABLES:
        if not check_table_exists(cur, table):
            continue
        has_portfolio_id_col[table] = check_column_exists(cur, table, "portfolio_id")

    # Obtener mapeo portfolio_id → entity_id
    cur.execute("SELECT id, portfolio_id FROM entities WHERE portfolio_id IS NOT NULL")
    portfolio_to_entity = {row[1]: row[0] for row in cur.fetchall()}

    if portfolio_to_entity:
        print("  MAPEO portfolio_id → entity_id:")
        for pid, eid in portfolio_to_entity.items():
            print(f"    portfolio_id={pid} → entity_id={eid}")
        print()

    for table in TABLES:
        if not check_table_exists(cur, table):
            continue

        if not has_portfolio_id_col.get(table):
            # Tabla no tiene portfolio_id — usar portfolio_name si existe
            if check_column_exists(cur, table, "portfolio_name"):
                sql_update = f"""
                    UPDATE {table} t
                    SET company_id = e.id
                    FROM entities e
                    JOIN portfolios p ON e.portfolio_id = p.id
                    WHERE p.name = t.portfolio_name
                    AND t.company_id IS NULL;
                """
                print(f"{'🔍' if dry_run else '⚡'} UPDATE {table} SET company_id FROM entities (via portfolio_name)")
                if not dry_run:
                    cur.execute(sql_update)
                    print(f"    → {cur.rowcount} filas actualizadas")
            else:
                print(f"⚠️  {table} no tiene portfolio_id ni portfolio_name — no se puede mapear automáticamente")
            continue

        sql_update = f"""
            UPDATE {table} t
            SET company_id = e.id
            FROM entities e
            WHERE e.portfolio_id = t.portfolio_id
            AND t.company_id IS NULL;
        """
        print(f"{'🔍' if dry_run else '⚡'} UPDATE {table} SET company_id FROM entities (via portfolio_id)")
        if not dry_run:
            cur.execute(sql_update)
            print(f"    → {cur.rowcount} filas actualizadas")

    print()

    # ── Paso 3: Crear índices ────────────────────────────────
    for table in TABLES:
        if not check_table_exists(cur, table):
            continue
        idx_name = f"idx_{table}_company_id"
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = %s
            )
        """, (idx_name,))
        if cur.fetchone()[0]:
            print(f"✅ Índice {idx_name} ya existe — omitido")
        else:
            sql_idx = f"CREATE INDEX {idx_name} ON {table}(company_id);"
            print(f"{'🔍' if dry_run else '⚡'} CREATE INDEX {idx_name} ON {table}(company_id)")
            if not dry_run:
                cur.execute(sql_idx)

    print()

    # ── Paso 4: Resumen ──────────────────────────────────────
    if not dry_run:
        conn.commit()
        print("=" * 66)
        print("  ✅ MIGRACIÓN COMPLETADA")
        print("  portfolio_id se mantiene intacto (coexistencia)")
        print("  company_id poblado desde entities.portfolio_id")
        print("=" * 66)
    else:
        print("=" * 66)
        print("  🔍 DRY-RUN completado — NO se ejecutó ningún cambio")
        print("  Ejecuta sin --dry-run para aplicar la migración")
        print("=" * 66)

    cur.close()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migración company_id")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar plan sin ejecutar")
    args = parser.parse_args()
    run_migration(dry_run=args.dry_run)
