# -*- coding: utf-8 -*-
"""
migrate_third_party_accounts.py — Etapa 09.G §10 (30-sep-2026): medios de pago del tercero.
==========================================================================================
Idempotente, en UNA transacción:
  1. Tabla third_party_accounts (celular / cuenta / llave / nombre_banco → tercero),
     con UNIQUE (tipo, valor): un medio de pago pertenece a una sola ficha.
  2. Verificación: prerrequisito third_parties, conteos.

NO hay backfill: ningún medio se registra solo (Regla 6b). Los registra una
persona con el botón 💾 del bot o en el módulo Terceros de la web.

Uso:  .venv\\Scripts\\python.exe scripts\\migrate_third_party_accounts.py [--dry-run]
Correr ANTES del deploy (el server también se auto-cura con init_table()).
Spec: docs/specs/09-bot-ia/09.G-completar-borrador.md §10
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "fin_sys_core"))
os.chdir(ROOT)
DRY_RUN = "--dry-run" in sys.argv


def _load_env():
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def run():
    _load_env()
    import fin_sys_core  # noqa: F401
    from fin_sys_core.db_pool import get_conn, put_conn
    from terceros_cuentas import DDL

    print("=" * 70)
    print("  MIGRACIÓN MEDIOS DE PAGO DEL TERCERO (09.G)" + ("  — DRY-RUN" if DRY_RUN else ""))
    print("=" * 70)
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'public' AND table_name = 'third_parties'
        """)
        if not cur.fetchone():
            print("❌ Falta la tabla third_parties.")
            conn.rollback()
            return 1
        print("0. prerrequisito third_parties: OK")

        cur.execute(DDL)
        print("1. third_party_accounts + índice: OK")

        cur.execute("SELECT tipo, COUNT(*) FROM third_party_accounts GROUP BY tipo ORDER BY tipo")
        por_tipo = dict(cur.fetchall())
        cur.execute("SELECT COUNT(*) FROM third_parties WHERE identification_number <> '999999999'")
        print(f"2. medios registrados: {por_tipo or 'ninguno todavía'} · terceros: {cur.fetchone()[0]}")

        if DRY_RUN:
            conn.rollback()
            print("\nDRY-RUN: nada aplicado (rollback).")
        else:
            conn.commit()
            print("\n✅ Migración aplicada.")
        cur.close()
        return 0
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e} — rollback")
        return 1
    finally:
        put_conn(conn)


if __name__ == "__main__":
    sys.exit(run())
