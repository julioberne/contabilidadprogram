# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Dashboard Data (3 endpoints)
Dashboard aggregator, reconcile-balances, cache invalidate.
Extracted from contabilidad.py — PURE refactor, zero logic changes."""
from fastapi import APIRouter, HTTPException
from typing import Optional

from routers.schemas import _build_coa_tree

router = APIRouter(tags=["Dashboard"])


# ==============================================================================
# 📊 Dashboard, Reconciliación, Cache
# ==============================================================================

@router.post("/api/reconcile-balances")
def reconcile_balances():
    try:
        from fin_sys_core.database_driver import get_db_connection, release_db_connection, recalcular_saldos_cuentas
        conn = get_db_connection()
        recalcular_saldos_cuentas(conn)
        conn.commit()
        release_db_connection(conn)
        return {"status": "OK", "message": "Saldos reconciliados"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/dashboard-data")
def get_dashboard_data(portfolio: Optional[str] = None, limit: int = 50, offset: int = 0):
    try:
        from fin_sys_core.database_driver import obtener_transacciones, obtener_cuentas, obtener_portafolios, obtener_perfil_usuario
        from fin_sys_core.ledger_math import calculate_caja_viva
        txs = obtener_transacciones(portfolio)
        accounts = obtener_cuentas()
        totals = calculate_caja_viva(txs, accounts)
        
        # Paginación de transacciones
        paginated_txs = txs[offset:offset + limit] if txs else []
        
        result = {
            # KPIs (balance)
            "status": totals["status"],
            "total_ingresos": totals["total_ingresos"],
            "total_gastos": totals["total_gastos"],
            "balance_neto": totals["balance_neto"],
            "capital_inicial": totals.get("capital_inicial", 5000000.0),
            "patrimonio": totals.get("patrimonio", 5000000.0),
            "total_ingresos_cop": totals["total_ingresos_cop"],
            "total_gastos_cop": totals["total_gastos_cop"],
            "balance_neto_cop": totals["balance_neto_cop"],
            "patrimonio_cop": totals["patrimonio_cop"],
            "total_ingresos_usd": totals["total_ingresos_usd"],
            "total_gastos_usd": totals["total_gastos_usd"],
            "balance_neto_usd": totals["balance_neto_usd"],
            "patrimonio_usd": totals["patrimonio_usd"],
            "alerts": totals.get("alerts", []),
            # SOL-04A: datos consolidados para el frontend
            "transactions": paginated_txs,
            "total_tx_count": len(txs),
            "accounts": accounts,
            "portfolios": obtener_portafolios(),
            "balance": totals,
        }
        
        # Perfil
        try:
            result["profile"] = obtener_perfil_usuario()
        except:
            result["profile"] = None
        
        # COA
        try:
            from fin_sys_core.database_driver import get_db_connection, release_db_connection
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, code, name, parent_id, is_group, naturaleza, nivel
                FROM coa_accounts
                WHERE portfolio_name = %s
                ORDER BY code;
            """, (portfolio or "Negocio A",))
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            cur.close()
            release_db_connection(conn)
            if rows:
                result["coa"] = {"status": "OK", "data": _build_coa_tree(rows)}
            else:
                result["coa"] = {"status": "EMPTY", "data": []}
        except Exception:
            result["coa"] = None
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/cache/invalidate")
def invalidate_cache():
    return {"status": "OK", "message": "Cache invalidado"}
