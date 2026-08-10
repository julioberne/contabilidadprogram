"""Repara transacciones que quedaron SIN asiento contable.

Causa tipica: la transaccion se creo en un proceso que no tenia registrado el
listener de partida doble (p.ej. el poller del bot antes del fix de
transaction_service.ensure_journal_listener). El resultado es una TX en el
libro auxiliar sin su contrapartida en kernel_journal_entries.

Uso:
    python scripts/repair_missing_journal.py            # solo LISTA los huerfanos
    python scripts/repair_missing_journal.py --repair   # emite los asientos faltantes

Idempotente: el kernel deduplica por (modulo_origen, referencia, linea), asi que
volver a correrlo no duplica asientos.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../fin_sys_core")

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _, _val = _line.partition('=')
                os.environ.setdefault(_key.strip(), _val.strip().strip('"').strip("'"))

from fin_sys_core.db_pool import get_conn, put_conn

SQL_HUERFANAS = """
    SELECT t.id, t.type, t.category, t.net_value, t.amount, t.account_id,
           t.concept, t.transaction_date
    FROM transactions t
    WHERE NOT EXISTS (
        SELECT 1 FROM kernel_journal_entries k
        WHERE k.referencia = 'TX-' || t.id
    )
    ORDER BY t.id
"""


def main():
    reparar = "--repair" in sys.argv
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(SQL_HUERFANAS)
        huerfanas = cur.fetchall()
        cur.close()
    finally:
        put_conn(conn)

    if not huerfanas:
        print("✓ No hay transacciones sin asiento contable.")
        return 0

    print(f"{len(huerfanas)} transaccion(es) SIN asiento contable:")
    for tx in huerfanas:
        tx_id, tipo, categoria, net, amount, account_id, concepto, fecha = tx
        print(f"  TX-{tx_id} | {tipo} | {categoria} | ${float(net or amount):,.0f} | {concepto}")

    if not reparar:
        print("\nEjecuta con --repair para emitir los asientos faltantes.")
        return 0

    from fin_sys_core.transaction_service import ensure_journal_listener
    from shared.helpers import emit_journal_entry
    ensure_journal_listener()

    print("\nReparando…")
    ok = 0
    for tx in huerfanas:
        tx_id, tipo, categoria, net, amount, account_id, concepto, fecha = tx
        res = emit_journal_entry(
            category=categoria or "",
            tx_type=tipo,
            amount=float(net if net is not None else amount),
            account_id=account_id,
            referencia=f"TX-{tx_id}",
            descripcion=concepto or "",
            fecha=str(fecha),
        )
        estado = (res or {}).get("status")
        print(f"  TX-{tx_id}: {estado}")
        if estado in ("ok", "skipped_duplicate"):
            ok += 1

    # Los borradores del bot que quedaron en ERROR solo por el asiento faltante
    # pasan a CONFIRMADO: su transaccion existe y ahora si tiene contrapartida.
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE transaction_drafts d
               SET status = 'CONFIRMADO', error = NULL, confirmed_at = COALESCE(confirmed_at, NOW())
             WHERE d.status = 'ERROR'
               AND d.confirmed_transaction_id IS NOT NULL
               AND d.error LIKE 'Asiento contable:%%'
               AND EXISTS (SELECT 1 FROM kernel_journal_entries k
                           WHERE k.referencia = 'TX-' || d.confirmed_transaction_id)
            RETURNING d.id, d.confirmed_transaction_id
        """)
        arreglados = cur.fetchall()
        conn.commit()
        cur.close()
    finally:
        put_conn(conn)
    for did, txid in arreglados:
        print(f"  Borrador #{did} → CONFIRMADO (TX-{txid})")

    print(f"\n{ok}/{len(huerfanas)} asientos emitidos.")
    return 0 if ok == len(huerfanas) else 1


if __name__ == "__main__":
    sys.exit(main())
