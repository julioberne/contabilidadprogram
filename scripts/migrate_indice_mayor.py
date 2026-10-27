# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Estándar de consultas H6.3: índice del Libro Mayor (27-oct-2026)
==================================================================================
El Libro Mayor pagina por cursor (empresa, cuenta, fecha, id). Hoy existen
índices por cuenta y por (empresa, fecha), pero ninguno con los tres: con
cientos de miles de asientos cada página recorrería la cuenta entera. Este
índice deja cada página en "cuesta lo mismo que la primera".

Idempotente. Lo corre Andrés (el clasificador no deja a Claude correr migrate_*.py):
    python scripts/migrate_indice_mayor.py --dry-run
    python scripts/migrate_indice_mayor.py --concurrently --explain
"""
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_ROOT)


def _cargar_env():
    """El .env del proyecto: el de esta carpeta o, desde un worktree, el de la principal."""
    import pathlib
    raiz = pathlib.Path(_ROOT)
    for base in (raiz, *raiz.parents):
        env = base / ".env"
        if env.is_file():
            with open(env, "r", encoding="utf-8") as f:
                for line in f:
                    ls = line.strip()
                    if ls and not ls.startswith("#") and "=" in ls:
                        k, v = ls.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
            return env
    return None


if not _cargar_env() or not os.getenv("DB_HOST"):
    sys.exit("❌ No encontré el .env con DB_HOST (ni aquí ni en la carpeta principal): no me conecto a ciegas.")

import psycopg2  # noqa: E402

NOMBRE = "idx_journal_pf_cuenta_fecha"
DEFINICION = "ON kernel_journal_entries (portfolio_id, cuenta_codigo, fecha, id)"
EXPLAIN = ("SELECT id FROM kernel_journal_entries WHERE portfolio_id = "
           "(SELECT portfolio_id FROM kernel_journal_entries LIMIT 1) AND cuenta_codigo = "
           "(SELECT cuenta_codigo FROM kernel_journal_entries LIMIT 1) ORDER BY fecha, id LIMIT 501")


def main():
    dry, conc, expl = "--dry-run" in sys.argv, "--concurrently" in sys.argv, "--explain" in sys.argv
    conn = psycopg2.connect(host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME", "postgres"),
                            user=os.getenv("DB_USER", "postgres"), password=os.getenv("DB_PASSWORD", ""),
                            port=os.getenv("DB_PORT", "6543"), connect_timeout=15,
                            application_name="finsys-migrate-indice-mayor")
    conn.autocommit = True
    cur = conn.cursor()
    print(f"✅ Conectado a {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")

    def explicar(etiqueta):
        cur.execute("EXPLAIN (ANALYZE, FORMAT TEXT) " + EXPLAIN)
        plan = [r[0] for r in cur.fetchall()]
        usa = next((ln.strip() for ln in plan if NOMBRE in ln), "sin el índice nuevo")
        tiempo = next((ln.strip() for ln in plan if "Execution Time" in ln), "")
        print(f"    [{etiqueta}] {usa[:90]} | {tiempo}")

    if expl:
        explicar("antes")
    cur.execute("SELECT 1 FROM pg_indexes WHERE indexname = %s", (NOMBRE,))
    if cur.fetchone():
        print(f"  ⏭  {NOMBRE} ya existe")
    else:
        sql = f"CREATE INDEX {'CONCURRENTLY ' if conc else ''}IF NOT EXISTS {NOMBRE} {DEFINICION}"
        if dry:
            print(f"  🔍 {sql}")
        else:
            t0 = time.perf_counter()
            cur.execute(sql)
            print(f"  ✅ {NOMBRE} en {time.perf_counter() - t0:.2f}s")
    if not dry:
        cur.execute("SELECT indexrelid::regclass::text FROM pg_index WHERE NOT indisvalid")
        invalidos = [r[0] for r in cur.fetchall()]
        print(f"  ⚠️ Índices INVALID: {invalidos} — DROP INDEX y reintentar" if invalidos else "  ✅ Sin índices inválidos")
    if expl:
        explicar("después")
        print("  ℹ️ Con pocos asientos Postgres puede preferir recorrer la tabla: el índice entra cuando conviene.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
