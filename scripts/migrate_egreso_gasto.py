"""Migración Etapa A (Módulo 09): reparar posting_rules en la BD viva.

1. transaction_type 'EGRESO' → 'GASTO': el contrato de la API (TransactionInput)
   solo acepta INGRESO|GASTO|TRANSFERENCIA, y emit_journal_entry filtra por
   transaction_type exacto — las 10 reglas seeded como EGRESO jamás matchean,
   así que todo gasto caía al fallback genérico 5105.
2. Fallbacks de INGRESO con cuenta '4120' → '417505': la 4120 no existe en el
   PUC estándar y el kernel rechaza asientos contra cuentas inexistentes
   (CuentaNoExisteError). El seed ya fue corregido; la BD seguía con el valor viejo.

Idempotente: una segunda ejecución reporta 0 cambios.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

# Load .env
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _, _val = _line.partition('=')
                os.environ.setdefault(_key.strip(), _val.strip().strip('"').strip("'"))

from fin_sys_core.db_pool import get_conn, put_conn


def _counts(cur):
    cur.execute("SELECT transaction_type, COUNT(*) FROM posting_rules GROUP BY 1 ORDER BY 1")
    return dict(cur.fetchall())


def main():
    conn = get_conn()
    try:
        cur = conn.cursor()

        print("── ANTES ──")
        print(f"  Reglas por tipo: {_counts(cur)}")

        # 1. EGRESO → GASTO
        cur.execute("""
            UPDATE posting_rules SET transaction_type = 'GASTO'
            WHERE transaction_type = 'EGRESO'
            RETURNING rule_name, category, debit_account_code;
        """)
        cambiadas = cur.fetchall()
        for r in cambiadas:
            print(f"  ✓ GASTO: {r[0]} (categoría '{r[1]}' → débito {r[2]})")

        # 2. Fallback INGRESO 4120 → 417505 (cuenta inexistente en PUC estándar)
        cur.execute("""
            UPDATE posting_rules SET credit_account_code = '417505'
            WHERE credit_account_code = '4120'
            RETURNING rule_name, category;
        """)
        reparadas = cur.fetchall()
        for r in reparadas:
            print(f"  ✓ 417505: {r[0]} (categoría '{r[1]}')")

        conn.commit()

        print("── DESPUÉS ──")
        despues = _counts(cur)
        print(f"  Reglas por tipo: {despues}")
        cur.execute("SELECT COUNT(*) FROM posting_rules WHERE credit_account_code = '4120'")
        restantes_4120 = cur.fetchone()[0]

        ok = despues.get('EGRESO', 0) == 0 and restantes_4120 == 0
        print(f"\n{len(cambiadas)} reglas EGRESO→GASTO, {len(reparadas)} reglas 4120→417505")
        print("RESULTADO: OK — sin EGRESO ni 4120 residuales" if ok
              else "RESULTADO: REVISAR — quedan reglas sin migrar")
        cur.close()
        return 0 if ok else 1
    finally:
        put_conn(conn)


if __name__ == "__main__":
    sys.exit(main())
