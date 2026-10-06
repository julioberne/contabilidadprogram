# -*- coding: utf-8 -*-
"""
migrate_compendios.py — Exportación 13.6: 🤝 Compendio para el cliente.
=========================================================================
En UNA transacción, idempotente (se puede correr las veces que sea):
  1. Tabla NUEVA accounting_compendios (+ índice). Ninguna tabla existente cambia.
     El folio usa la secuencia accounting_files_folio_seq de 13.5 (debe existir:
     scripts/migrate_exports.py ya corrió el 05-oct).
  2. Verificación: tabla presente y secuencia presente.

El DDL vive en fin_sys_core/compendio_driver.py (una sola fuente).
La BD es la MISMA en local y en producción: correrla ANTES del deploy.

Uso:  python scripts/migrate_compendios.py [--dry-run]
Rollback: DROP TABLE accounting_compendios; (los links dejan de existir).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
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
    from fin_sys_core.compendio_driver import DDL

    print("=" * 70)
    print("  MIGRACIÓN 13.6 — COMPENDIO PARA EL CLIENTE" + ("  — DRY-RUN" if DRY_RUN else ""))
    print("=" * 70)
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('accounting_compendios') IS NOT NULL, "
                    "to_regclass('accounting_files_folio_seq') IS NOT NULL")
        tabla, secuencia = cur.fetchone()
        print("0. ya existía la tabla:", tabla, "| secuencia de folios 13.5:", secuencia)
        if not secuencia:
            print("\n❌ Falta la secuencia de folios: corre primero scripts/migrate_exports.py")
            conn.rollback()
            return 1

        for sql in DDL:
            cur.execute(sql)
        print("1. tabla e índice: OK")

        cur.execute("SELECT to_regclass('accounting_compendios') IS NOT NULL")
        ok = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM accounting_compendios")
        print("2. presente:", ok, "| compendios:", cur.fetchone()[0])

        if DRY_RUN:
            conn.rollback()
            print("\nDRY-RUN: nada aplicado (rollback).")
        else:
            conn.commit()
            print("\n✅ Migración aplicada." if ok else "\n⚠ Aplicada, pero la verificación no cuadra.")
        cur.close()
        return 0 if ok else 1
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e} — rollback")
        return 1
    finally:
        put_conn(conn)


if __name__ == "__main__":
    sys.exit(run())
