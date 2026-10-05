# -*- coding: utf-8 -*-
"""
migrate_exports.py — Análisis 13.5: organizador contable 📦 EXPORTACIÓN.
=========================================================================
En UNA transacción, idempotente (se puede correr las veces que sea):
  1. Tablas NUEVAS (ninguna tabla existente cambia):
       accounting_doc_types · accounting_folders · accounting_files
       (+ secuencia accounting_files_folio_seq e índices) · analytics_export_paquetes
  2. Tipos documentales por defecto (Libros, Estados financieros, Impuestos,
     Cartera, Bancos, Relaciones de TXs, Soportes). ON CONFLICT: si alguien
     renombró uno, se respeta.
  3. Verificación: tablas presentes y conteo de tipos.

El DDL vive en fin_sys_core/accounting_files_driver.py (una sola fuente).
La BD es la MISMA en local y en producción: correrla ANTES del deploy.

Uso:  python scripts/migrate_exports.py [--dry-run]
Rollback: las tablas pueden quedarse (nadie más las lee); para quitarlas,
DROP TABLE accounting_files, accounting_folders, accounting_doc_types,
analytics_export_paquetes; DROP SEQUENCE accounting_files_folio_seq.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
DRY_RUN = "--dry-run" in sys.argv
TABLAS = ("accounting_doc_types", "accounting_folders", "accounting_files", "analytics_export_paquetes")


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
    from fin_sys_core.accounting_files_driver import DDL, SQL_TIPOS_DEFAULT, TIPOS_DEFAULT

    print("=" * 70)
    print("  MIGRACIÓN 13.5 — ORGANIZADOR CONTABLE" + ("  — DRY-RUN" if DRY_RUN else ""))
    print("=" * 70)
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass(t) IS NOT NULL FROM unnest(%s::text[]) AS t", (list(TABLAS),))
        antes = [r[0] for r in cur.fetchall()]
        print("0. ya existían:", {t: e for t, e in zip(TABLAS, antes)})

        for sql in DDL:
            cur.execute(sql)
        print("1. tablas, secuencia e índices: OK")

        for fila in TIPOS_DEFAULT:
            cur.execute(SQL_TIPOS_DEFAULT, fila)
        cur.execute("SELECT clave, nombre FROM accounting_doc_types WHERE es_default ORDER BY orden")
        tipos = cur.fetchall()
        print(f"2. tipos documentales por defecto: {len(tipos)} → " + ", ".join(n for _, n in tipos))

        cur.execute("SELECT to_regclass(t) IS NOT NULL FROM unnest(%s::text[]) AS t", (list(TABLAS),))
        despues = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM accounting_files")
        n_archivos = cur.fetchone()[0]
        print("3. presentes:", {t: e for t, e in zip(TABLAS, despues)}, f"| archivos: {n_archivos}")
        ok = all(despues) and len(tipos) == len(TIPOS_DEFAULT)

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
