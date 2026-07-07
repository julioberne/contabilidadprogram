# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Zero-COA (Kernel Contable)"""
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(tags=["Zero-COA"])


# ── GET /api/journal-entries ──
@router.get("/api/journal-entries")
def get_journal_entries(
    fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None,
    modulo_origen: Optional[str] = None, limit: int = 100, offset: int = 0
):
    try:
        from kernel.kernel_accounting import obtener_asientos
        entries = obtener_asientos(
            fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
            modulo_origen=modulo_origen, limit=limit, offset=offset
        )
        for e in entries:
            for k in ['fecha', 'created_at']:
                if k in e and e[k]: e[k] = str(e[k])
            for k in ['debito', 'credito']:
                if k in e and e[k] is not None: e[k] = float(e[k])
        return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/financial-summary ──
@router.get("/api/financial-summary")
def get_financial_summary(fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None):
    try:
        from kernel.kernel_accounting import obtener_resumen_financiero
        return obtener_resumen_financiero(fecha_desde, fecha_hasta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/posting-rules ──
@router.get("/api/posting-rules")
def list_posting_rules():
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, rule_name, category, transaction_type,
                   debit_account_code, credit_account_code, description, is_active
            FROM posting_rules ORDER BY transaction_type, category;
        """)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
        release_db_connection(conn)
        return rows
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except: pass
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/posting-rules/preview ──
@router.get("/api/posting-rules/preview")
def preview_posting_rule(category: str, tx_type: str, amount: float = 0, account_id: int = None):
    """Retorna el preview del asiento contable sin emitirlo."""
    try:
        from fin_sys_core.database_driver import get_db_connection, release_db_connection
        from shared.helpers import resolve_bank_code
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT debit_account_code, credit_account_code, rule_name, description
            FROM posting_rules
            WHERE category = %s AND transaction_type = %s AND is_active = TRUE
            ORDER BY portfolio_id NULLS LAST LIMIT 1;
        """, (category, tx_type))
        rule = cur.fetchone()
        # Fallback genérico
        if not rule:
            cur.execute("""
                SELECT debit_account_code, credit_account_code, rule_name, description
                FROM posting_rules
                WHERE category = '__FALLBACK__' AND transaction_type = %s AND is_active = TRUE
                LIMIT 1;
            """, (tx_type,))
            rule = cur.fetchone()
        cur.close()
        release_db_connection(conn)
        if not rule:
            return {"found": False}
        debit_code, credit_code, rule_name, desc = rule
        bank_code = resolve_bank_code(account_id)
        if debit_code == "__BANK__":
            debit_code = bank_code
        if credit_code == "__BANK__":
            credit_code = bank_code
        return {
            "found": True, "rule_name": rule_name, "description": desc,
            "debit": {"cuenta_codigo": debit_code, "monto": amount},
            "credit": {"cuenta_codigo": credit_code, "monto": amount},
            "balanced": True
        }
    except:
        return {"found": False}
