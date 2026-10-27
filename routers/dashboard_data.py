# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Dashboard Data (3 endpoints)
Dashboard aggregator, reconcile-balances, cache invalidate.
Extracted from contabilidad.py — PURE refactor, zero logic changes."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from routers.auth_guard import require_admin, require_auth
from routers.schemas import _build_coa_tree

router = APIRouter(tags=["Dashboard"])


# ==============================================================================
# 📊 Dashboard, Reconciliación, Cache
# ==============================================================================

def _agregar_tx_delta(accounts, txs):
    """Anota en cada cuenta el movimiento neto REAL según sus transacciones.

    Réplica exacta de la matemática de recalcular_saldos_cuentas (INGRESO
    +neto, GASTO -neto, TRANSFERENCIA origen -monto / destino +monto, con
    conversión TRM entre monedas). Agrega a cada dict de cuenta:
      tx_delta          → suma de movimientos por transacciones
      expected_balance  → initial_balance + tx_delta
    Así el frontend puede evidenciar cuánto sube/baja cada cuenta y detectar
    descuadres cuando current_balance fue editado a mano.
    """
    por_id = {a["id"]: a for a in accounts if a.get("id") is not None}
    deltas = {aid: 0.0 for aid in por_id}

    def _conv(valor, desde, hacia, trm):
        if desde == hacia:
            return valor
        if desde == "USD" and hacia == "COP":
            return valor * trm
        if desde == "COP" and hacia == "USD":
            return valor / trm if trm > 0 else 0.0
        return valor

    for tx in txs or []:
        tx_type = (tx.get("type") or "").upper()
        acc = por_id.get(tx.get("account_id"))
        dest = por_id.get(tx.get("dest_account_id"))
        trm = float(tx.get("trm") or 1.0)
        tx_curr = tx.get("transaction_currency") or "COP"
        net_val = float(tx.get("net_value") or 0.0)
        amount = float(tx.get("amount") or 0.0)

        if tx_type == "INGRESO" and acc:
            deltas[acc["id"]] += _conv(net_val, tx_curr, acc["currency"], trm)
        elif tx_type == "GASTO" and acc:
            deltas[acc["id"]] -= _conv(net_val, tx_curr, acc["currency"], trm)
        elif tx_type == "TRANSFERENCIA" and acc:
            deltas[acc["id"]] -= amount
            if dest:
                deltas[dest["id"]] += _conv(amount, acc["currency"], dest["currency"], trm)

    for aid, a in por_id.items():
        a["tx_delta"] = round(deltas[aid], 2)
        a["expected_balance"] = round(float(a.get("initial_balance") or 0.0) + deltas[aid], 2)

@router.post("/api/reconcile-balances")
def reconcile_balances(_admin: dict = Depends(require_admin)):
    conn = None
    try:
        from fin_sys_core.database_driver import get_db_connection, release_db_connection, recalcular_saldos_cuentas
        conn = get_db_connection()
        recalcular_saldos_cuentas(conn)
        conn.commit()
        return {"status": "OK", "message": "Saldos reconciliados"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn is not None:
            try:
                release_db_connection(conn)
            except Exception:
                pass


def _armar_respuesta(totals, paginated_txs, total_tx_count, accounts, portfolios):
    """Las MISMAS claves que siempre devolvió /api/dashboard-data (contrato
    que consume frontend/src/contabilidad-v2/hooks/useDashboardData.js)."""
    return {
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
        "total_tx_count": total_tx_count,
        "accounts": accounts,
        "portfolios": portfolios,
        "balance": totals,
    }


def _dashboard_fast(portfolio: Optional[str], limit: int, offset: int):
    """Ruta rápida (plan cimientos A2, 2026-09-15): UN viaje a la BD vía
    fin_sys_core/dashboard_query.py. Desde H6.3 es la única (la legacy se
    retiró); scripts/verify_dashboard_parity.py --http compara dos servidores."""
    from fin_sys_core.dashboard_query import obtener_dashboard_snapshot, caja_viva_desde_agregados
    from fin_sys_core.database_driver import MOCK_USER_PROFILE

    snap = obtener_dashboard_snapshot(portfolio, limit=limit, offset=offset)
    portfolios = snap["portfolios"]
    if portfolio and not any(p.get("name") == portfolio for p in portfolios):
        raise HTTPException(status_code=404, detail=f"Portafolio no encontrado: '{portfolio}'")

    totals = caja_viva_desde_agregados(snap["kpi"], snap["accounts"])
    result = _armar_respuesta(totals, snap["transactions"], snap["total_tx_count"],
                              snap["accounts"], portfolios)
    # obtener_perfil_usuario devuelve el default útil cuando no hay perfil
    result["profile"] = snap["profile"] or dict(MOCK_USER_PROFILE)
    result["coa"] = ({"status": "OK", "data": snap["coa"]} if snap["coa"]
                     else {"status": "EMPTY", "data": []})
    return result


@router.get("/api/dashboard-data/balance")
def get_dashboard_balance(portfolio: Optional[str] = None, _u: dict = Depends(require_auth)):
    """Refresco liviano tras una mutación (plan A5): KPIs + cuentas sin la
    página de transacciones. Un viaje a la BD."""
    try:
        from fin_sys_core.dashboard_query import obtener_dashboard_snapshot, caja_viva_desde_agregados
        snap = obtener_dashboard_snapshot(portfolio, limit=0, incluir_txs=False)
        if portfolio and not any(p.get("name") == portfolio for p in snap["portfolios"]):
            raise HTTPException(status_code=404, detail=f"Portafolio no encontrado: '{portfolio}'")
        totals = caja_viva_desde_agregados(snap["kpi"], snap["accounts"])
        return {"balance": totals, "accounts": snap["accounts"],
                "total_tx_count": snap["total_tx_count"], "portfolios": snap["portfolios"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/dashboard-data")
def get_dashboard_data(portfolio: Optional[str] = None, limit: int = 50, offset: int = 0, _u: dict = Depends(require_auth)):
    # Estándar H6.3 (27-oct-2026, decisión de Andrés): solo la ruta rápida. La
    # legacy (DASHBOARD_FAST=0: TODAS las transacciones y el filtro en Python)
    # llevaba apagada desde el 15-sep; un respaldo que nunca corre no está
    # probado justo cuando haría falta (regla 7 del estándar).
    try:
        return _dashboard_fast(portfolio, limit, offset)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/cache/invalidate")
def invalidate_cache(_admin: dict = Depends(require_admin)):
    return {"status": "OK", "message": "Cache invalidado"}
