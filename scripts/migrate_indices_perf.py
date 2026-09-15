# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Índices de rendimiento (2026-09-15, plan cimientos A1)
========================================================================
El dashboard y el libro diario ordenan/filtran `transactions` por
(portfolio_id, transaction_date) y NO existía ningún índice sobre esas
columnas; _asegurar_tercero busca por lower(btrim(name)) sin índice
funcional; la subconsulta de evidencias por fila no tenía índice por
transaction_id. Con 25 filas no se nota; con miles, sí.

Idempotente (CREATE INDEX IF NOT EXISTS). Uso:
    python scripts/migrate_indices_perf.py               # aplica
    python scripts/migrate_indices_perf.py --dry-run     # solo muestra
    python scripts/migrate_indices_perf.py --explain     # EXPLAIN antes/después
    python scripts/migrate_indices_perf.py --concurrently
        CONCURRENTLY no puede correr dentro de una transacción: este script
        abre una conexión DIRECTA con autocommit=True (cada sentencia es su
        propia transacción, válido también por el pooler :6543). Si un
        CREATE ... CONCURRENTLY falla a medias deja un índice INVALID; el
        paso final los detecta para hacer DROP INDEX y reintentar.
"""
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_ROOT)
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            ls = line.strip()
            if ls and not ls.startswith("#") and "=" in ls:
                k, v = ls.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

import psycopg2  # noqa: E402

INDICES = [
    ("idx_tx_portfolio_date",
     "ON transactions (portfolio_id, transaction_date DESC, id DESC)",
     "página del diario filtrada por portafolio"),
    ("idx_tx_date_id",
     "ON transactions (transaction_date DESC, id DESC)",
     "página global (dashboard sin portafolio)"),
    ("idx_third_parties_name_norm",
     "ON third_parties (lower(btrim(name)))",
     "_asegurar_tercero: búsqueda por nombre normalizado"),
    ("idx_tx_evidences_tx",
     "ON transaction_evidences (transaction_id)",
     "subconsulta json_agg de evidencias por transacción"),
    ("idx_ael_account",
     "ON account_entity_links (account_id)",
     "vínculos cuenta↔empresa del dashboard"),
]

EXPLAIN_QUERIES = [
    ("página filtrada",
     "SELECT t.id FROM transactions t JOIN portfolios p ON p.id = t.portfolio_id "
     "WHERE p.name = (SELECT name FROM portfolios ORDER BY id LIMIT 1) "
     "ORDER BY t.transaction_date DESC, t.id DESC LIMIT 50"),
    ("tercero por nombre",
     "SELECT id FROM third_parties WHERE lower(btrim(name)) = lower(btrim('x'))"),
]


def connect():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        port=os.getenv("DB_PORT", "6543"),
        connect_timeout=15,
        application_name="finsys-migrate-indices",
    )
    conn.autocommit = True   # imprescindible para CONCURRENTLY
    return conn


def explain(cur, etiqueta):
    for nombre, sql in EXPLAIN_QUERIES:
        try:
            cur.execute("EXPLAIN (ANALYZE, FORMAT TEXT) " + sql)
            plan = cur.fetchall()
            primera = plan[0][0] if plan else "?"
            tiempo = next((r[0] for r in plan if "Execution Time" in r[0]), "")
            print(f"    [{etiqueta}] {nombre}: {primera.strip()[:90]} | {tiempo.strip()}")
        except Exception as e:
            print(f"    [{etiqueta}] {nombre}: EXPLAIN falló: {e}")


def main():
    dry = "--dry-run" in sys.argv
    conc = "--concurrently" in sys.argv
    do_explain = "--explain" in sys.argv
    print("=" * 70)
    print("  ÍNDICES DE RENDIMIENTO" + ("  (DRY-RUN)" if dry else ""))
    print("=" * 70)
    conn = connect()
    cur = conn.cursor()
    print(f"✅ Conectado a {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")

    if do_explain:
        explain(cur, "antes")

    for nombre, definicion, motivo in INDICES:
        cur.execute("SELECT 1 FROM pg_indexes WHERE indexname = %s", (nombre,))
        if cur.fetchone():
            print(f"  ⏭  {nombre} ya existe")
            continue
        sql = f"CREATE INDEX {'CONCURRENTLY ' if conc else ''}IF NOT EXISTS {nombre} {definicion}"
        if dry:
            print(f"  🔍 {nombre}: {sql}")
            continue
        t0 = time.perf_counter()
        try:
            cur.execute(sql)
            print(f"  ✅ {nombre} ({motivo}) en {time.perf_counter() - t0:.2f}s")
        except Exception as e:
            print(f"  ❌ {nombre}: {e}")

    if not dry:
        cur.execute("SELECT indexrelid::regclass::text FROM pg_index WHERE NOT indisvalid")
        invalidos = [r[0] for r in cur.fetchall()]
        if invalidos:
            print(f"  ⚠️ Índices INVALID (CONCURRENTLY a medias): {invalidos} — "
                  f"DROP INDEX y reintentar")
        else:
            print("  ✅ Sin índices inválidos")

    if do_explain:
        explain(cur, "después")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
