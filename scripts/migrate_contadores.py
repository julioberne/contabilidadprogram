# -*- coding: utf-8 -*-
"""
migrate_contadores.py — Módulo Contadores (B1, 2026-09-15): esquema + backfill.
=================================================================================
En UNA transacción, idempotente:
  1. Columnas nuevas en kernel_journal_entries (estado, portfolio_id, tx_id,
     created_by, posted_by, posted_at, revisado_por, revisado_en, motivo,
     reversa_de, anulado_por) + índices + CHECK del estado. (Las mismas que
     el server crea al arrancar; aquí además se hace el backfill.)
  2. Tabla accounting_periods.
  3. Backfill tx_id desde referencia 'TX-<n>'.
  4. Backfill portfolio_id: TX- desde transactions; PAY- vía
     cartera_payments→cxp_cxc_ledger→transactions; CXC-/CXP- vía cxp_cxc_ledger.
  5. Espejos REV-<ref> previos (plan A4): reversa_de = grupo original y el
     original queda ANULADO/anulado_por.
  6. Históricos (created_by NULL) → CONTABILIZADO (posted_by='migracion',
     posted_at=created_at). Decisión: ya alimentaban los reportes; ponerlos en
     borrador vaciaría todo y crearía una cola sin valor. Lo dudoso se corrige
     con anulación + asiento manual, que deja rastro.
     --borrador-desde YYYY-MM-DD deja en BORRADOR los históricos desde esa fecha.
  7. Verificación: conteo por estado, sin portafolio, grupos con estados mixtos.

Uso:  python scripts/migrate_contadores.py [--dry-run] [--borrador-desde 2026-09-01]
Correr ANTES de desplegar el backend de B1 (el server se auto-cura con las
columnas, pero el backfill solo lo hace este script).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
DRY_RUN = "--dry-run" in sys.argv
BORRADOR_DESDE = None
if "--borrador-desde" in sys.argv:
    BORRADOR_DESDE = sys.argv[sys.argv.index("--borrador-desde") + 1]


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
    from kernel.kernel_accounting import _DDL_CONTADORES

    print("=" * 70)
    print("  MIGRACIÓN CONTADORES (B1)" + ("  — DRY-RUN" if DRY_RUN else ""))
    print("=" * 70)
    conn = get_conn()
    try:
        cur = conn.cursor()

        # 1. Columnas + índices + CHECK
        for sql in _DDL_CONTADORES:
            cur.execute(sql)
        print("1. columnas/índices/CHECK de kernel_journal_entries: OK")

        # 2. accounting_periods
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounting_periods (
                id SERIAL PRIMARY KEY,
                portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                anio SMALLINT NOT NULL,
                mes  SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
                estado VARCHAR(10) NOT NULL DEFAULT 'CERRADO',
                cerrado_por VARCHAR(64), cerrado_en TIMESTAMPTZ,
                reabierto_por VARCHAR(64), reabierto_en TIMESTAMPTZ,
                nota TEXT,
                UNIQUE (portfolio_id, anio, mes)
            );
        """)
        print("2. accounting_periods: OK")

        # 3. tx_id desde la referencia
        cur.execute("""
            UPDATE kernel_journal_entries
               SET tx_id = CAST(substring(referencia from 4) AS INTEGER)
             WHERE referencia ~ '^TX-[0-9]+$' AND tx_id IS NULL
        """)
        print(f"3. tx_id backfill: {cur.rowcount} líneas")

        # 4. portfolio_id
        cur.execute("""
            UPDATE kernel_journal_entries j
               SET portfolio_id = t.portfolio_id
              FROM transactions t
             WHERE j.tx_id = t.id AND j.portfolio_id IS NULL
        """)
        n_tx = cur.rowcount
        cur.execute("""
            UPDATE kernel_journal_entries j
               SET portfolio_id = t.portfolio_id, tx_id = COALESCE(j.tx_id, t.id)
              FROM cartera_payments p
              JOIN cxp_cxc_ledger l ON l.id = p.ledger_id
              JOIN transactions t ON t.id = l.transaction_id
             WHERE j.referencia = 'PAY-' || p.id AND j.portfolio_id IS NULL
        """)
        n_pay = cur.rowcount
        cur.execute("""
            UPDATE kernel_journal_entries j
               SET portfolio_id = t.portfolio_id, tx_id = COALESCE(j.tx_id, t.id)
              FROM cxp_cxc_ledger l
              JOIN transactions t ON t.id = l.transaction_id
             WHERE (j.referencia = 'CXC-' || l.id OR j.referencia = 'CXP-' || l.id)
               AND j.portfolio_id IS NULL
        """)
        n_led = cur.rowcount
        print(f"4. portfolio_id backfill: TX {n_tx} | PAY {n_pay} | CXC/CXP {n_led} líneas")

        # 5. Espejos REV- previos (A4): enlazar y marcar el original ANULADO
        cur.execute("""
            UPDATE kernel_journal_entries rev
               SET reversa_de = o.entry_group_id
              FROM (SELECT DISTINCT modulo_origen, referencia, entry_group_id
                      FROM kernel_journal_entries WHERE referencia NOT LIKE 'REV-%%') o
             WHERE rev.referencia = 'REV-' || o.referencia
               AND rev.modulo_origen = o.modulo_origen
               AND rev.reversa_de IS NULL
        """)
        n_rev = cur.rowcount
        cur.execute("""
            UPDATE kernel_journal_entries o
               SET estado = 'ANULADO', anulado_por = rev.entry_group_id,
                   motivo = COALESCE(o.motivo, 'Anulado antes de la migración Contadores')
              FROM (SELECT DISTINCT reversa_de, entry_group_id FROM kernel_journal_entries
                     WHERE reversa_de IS NOT NULL) rev
             WHERE o.entry_group_id = rev.reversa_de AND o.estado <> 'ANULADO'
        """)
        n_anul = cur.rowcount
        print(f"5. espejos enlazados: {n_rev} líneas | originales ANULADOS: {n_anul} líneas")

        # 6. Históricos → CONTABILIZADO
        filtro_fecha = ""
        params = []
        if BORRADOR_DESDE:
            filtro_fecha = " AND fecha < %s"
            params.append(BORRADOR_DESDE)
        cur.execute(f"""
            UPDATE kernel_journal_entries
               SET estado = 'CONTABILIZADO', posted_by = 'migracion', posted_at = created_at,
                   created_by = 'migracion'
             WHERE created_by IS NULL AND estado = 'BORRADOR'{filtro_fecha}
        """, params)
        n_hist = cur.rowcount
        cur.execute("""
            UPDATE kernel_journal_entries SET created_by = 'migracion' WHERE created_by IS NULL
        """)
        print(f"6. históricos CONTABILIZADOS: {n_hist} líneas"
              + (f" (BORRADOR desde {BORRADOR_DESDE})" if BORRADOR_DESDE else ""))

        # 7. Verificación
        cur.execute("SELECT estado, COUNT(*) FROM kernel_journal_entries GROUP BY estado ORDER BY estado")
        print("7. por estado:", {r[0]: r[1] for r in cur.fetchall()})
        cur.execute("SELECT COUNT(*) FROM kernel_journal_entries WHERE portfolio_id IS NULL")
        print("   líneas sin portafolio:", cur.fetchone()[0])
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT entry_group_id FROM kernel_journal_entries
                GROUP BY entry_group_id HAVING COUNT(DISTINCT estado) > 1) x
        """)
        mixtos = cur.fetchone()[0]
        print("   grupos con estados mixtos (esperado 0):", mixtos)

        if DRY_RUN:
            conn.rollback()
            print("\nDRY-RUN: nada aplicado (rollback).")
        else:
            conn.commit()
            print("\n✅ Migración aplicada.")
        cur.close()
        return 0 if mixtos == 0 else 1
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e} — rollback")
        return 1
    finally:
        put_conn(conn)


if __name__ == "__main__":
    sys.exit(run())
