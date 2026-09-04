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
    conn = None
    try:
        from fin_sys_core.database_driver import get_db_connection, release_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM user_accounts WHERE id = %s;", (account_id,))
        row = cur.fetchone()
        cur.close()
        if row:
            return BANK_ACCOUNT_MAP.get(row[0], "111005")
        return "111005"
    except Exception:
        return "111005"
    finally:
        # Se invoca en CADA asiento contable: el except desnudo fugaba la
        # conexión ante cualquier error (auditoría 2026-09-04)
        if conn is not None:
            try:
                release_db_connection(conn)
            except Exception:
                pass


def puc_tipo(cuenta_codigo: str) -> str:
    """Tipo contable según el primer dígito del PUC colombiano.
    1=ACTIVO 2=PASIVO 3=PATRIMONIO 4=INGRESO 5/6/7=GASTO."""
    return {
        "1": "ACTIVO", "2": "PASIVO", "3": "PATRIMONIO",
        "4": "INGRESO", "5": "GASTO", "6": "GASTO", "7": "GASTO",
    }.get(str(cuenta_codigo or "")[:1], "")


def emit_journal_entry(category, tx_type, amount, account_id=None, referencia="", descripcion="", fecha=None):
    """
    Busca la posting_rule por (category, tx_type), resuelve __BANK__,
    y emite el evento al kernel para generar el asiento de partida doble.

    No bloquea la operación original, pero SÍ reporta el resultado:
      {'status': 'ok'|'skipped_duplicate', 'entry_group_id': ...}
      {'status': 'no_rule'}   — sin posting rule aplicable
      {'status': 'error', 'error': ...} — el asiento falló (queda en logs)
    """
    conn = None
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
        conn = None
        if not rule:
            logger.warning(f"⚠️ Zero-COA: sin posting rule para ({category}, {tx_type}) — asiento NO generado ({referencia})")
            return {"status": "no_rule"}
        debit_code, credit_code, rule_name = rule
        bank_code = resolve_bank_code(account_id)
        if debit_code == "__BANK__":
            debit_code = bank_code
        if credit_code == "__BANK__":
            credit_code = bank_code
        results = emit('fin.transaccion.registrada', {
            'fecha': fecha or str(date.today()),
            'modulo_origen': 'zero_coa',
            'referencia': referencia,
            'descripcion': f"[{rule_name}] {descripcion}",
            'asientos': [
                # cuenta_tipo derivado del PUC: sin esto el resumen financiero
                # ignoraba estos asientos (tipo '' no matchea ninguna categoría)
                {'cuenta_codigo': debit_code, 'debito': amount, 'credito': 0,
                 'cuenta_nombre': rule_name, 'cuenta_tipo': puc_tipo(debit_code)},
                {'cuenta_codigo': credit_code, 'debito': 0, 'credito': amount,
                 'cuenta_nombre': rule_name, 'cuenta_tipo': puc_tipo(credit_code)},
            ]
        })
        # Inspeccionar el resultado de los handlers en vez de descartarlo
        if not results:
            # Sin listeners no se registró NADA — jamás reportar "ok"
            logger.error(f"❌ Zero-COA: evento sin listeners — asiento NO registrado ({referencia})")
            return {"status": "no_listener"}
        for r in results:
            if r.get("status") == "error":
                logger.error(f"❌ Zero-COA: asiento FALLÓ para {referencia}: {r.get('error')}")
                return {"status": "error", "error": r.get("error")}
            inner = r.get("result") or {}
            if inner.get("status") == "skipped_duplicate":
                return {"status": "skipped_duplicate", "entry_group_id": inner.get("entry_group_id")}
        logger.info(f"✅ Zero-COA: {rule_name} | ${amount:,.0f} | Db={debit_code} Cr={credit_code}")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"❌ Zero-COA emit failed ({referencia}): {e}")
        return {"status": "error", "error": str(e)}
    finally:
        if conn is not None:
            try:
                from fin_sys_core.database_driver import release_db_connection
                release_db_connection(conn)
            except Exception:
                pass
