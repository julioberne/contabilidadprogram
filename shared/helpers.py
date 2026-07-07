# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Shared Helpers
---------------------------------
Funciones y constantes compartidas entre múltiples routers.
"""

import logging

logger = logging.getLogger("zero_coa")


# ══════════════════════════════════════════════════════════════════
#  Constantes
# ══════════════════════════════════════════════════════════════════

BANK_ACCOUNT_MAP = {
    "Efectivo": "110505",
    "Caja Menor": "110510",
}


# ══════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════

def resolve_bank_code(account_id: int = None) -> str:
    """Resuelve un account_id a su código PUC. Default: 111005 (Bancos)."""
    if not account_id:
        return "111005"
    try:
        from fin_sys_core.database_driver import get_db_connection, release_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM user_accounts WHERE id = %s;", (account_id,))
        row = cur.fetchone()
        cur.close()
        release_db_connection(conn)
        if row:
            return BANK_ACCOUNT_MAP.get(row[0], "111005")
        return "111005"
    except:
        return "111005"


def emit_journal_entry(category, tx_type, amount, account_id=None, referencia="", descripcion="", fecha=None):
    """
    Busca la posting_rule por (category, tx_type), resuelve __BANK__,
    y emite el evento al kernel para generar el asiento de partida doble.
    Nunca bloquea la operación original si falla.
    """
    try:
        from kernel.kernel_event_bus import emit
        from fin_sys_core.database_driver import get_db_connection, release_db_connection
        from datetime import date
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT debit_account_code, credit_account_code, rule_name
            FROM posting_rules
            WHERE category = %s AND transaction_type = %s AND is_active = TRUE
            ORDER BY portfolio_id NULLS LAST LIMIT 1;
        """, (category, tx_type))
        rule = cur.fetchone()
        # Fallback: si no hay match exacto, usar regla genérica
        if not rule:
            cur.execute("""
                SELECT debit_account_code, credit_account_code, rule_name
                FROM posting_rules
                WHERE category = '__FALLBACK__' AND transaction_type = %s AND is_active = TRUE
                LIMIT 1;
            """, (tx_type,))
            rule = cur.fetchone()
        cur.close()
        release_db_connection(conn)
        if not rule:
            return None
        debit_code, credit_code, rule_name = rule
        bank_code = resolve_bank_code(account_id)
        if debit_code == "__BANK__":
            debit_code = bank_code
        if credit_code == "__BANK__":
            credit_code = bank_code
        result = emit('fin.transaccion.registrada', {
            'fecha': fecha or str(date.today()),
            'modulo_origen': 'zero_coa',
            'referencia': referencia,
            'descripcion': f"[{rule_name}] {descripcion}",
            'asientos': [
                {'cuenta_codigo': debit_code, 'debito': amount, 'credito': 0,
                 'cuenta_nombre': rule_name, 'cuenta_tipo': ''},
                {'cuenta_codigo': credit_code, 'debito': 0, 'credito': amount,
                 'cuenta_nombre': rule_name, 'cuenta_tipo': ''},
            ]
        })
        logger.info(f"✅ Zero-COA: {rule_name} | ${amount:,.0f} | Db={debit_code} Cr={credit_code}")
        return result
    except Exception as e:
        logger.warning(f"⚠️ Zero-COA emit failed: {e}")
        return None
