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

        portfolios = obtener_portafolios()

        # Un portafolio inexistente ya NO responde 200 con ceros. Antes cualquier
        # nombre devolvía un payload con pinta de válido (ingresos 0 + patrimonio
        # global), así que el consolidado por empresa mostraba el mismo número
        # fantasma en cada fila y lo sumaba N veces.
        if portfolio and not any(p.get("name") == portfolio for p in portfolios):
            raise HTTPException(
                status_code=404,
                detail=f"Portafolio no encontrado: '{portfolio}'"
            )

        txs = obtener_transacciones(portfolio)
        accounts = obtener_cuentas()
        totals = calculate_caja_viva(txs, accounts)

        # Δ real por cuenta desde las TRANSACCIONES (todas, sin filtro de
        # portafolio: las cuentas son globales). Misma matemática que
        # recalcular_saldos_cuentas. Permite al frontend mostrar
        # inicial → movimientos → esperado, y detectar descuadres cuando el
        # saldo actual fue editado a mano.
        all_txs = txs if not portfolio else obtener_transacciones(None)
        _agregar_tx_delta(accounts, all_txs)
        
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
            "portfolios": portfolios,
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
            # Sin portafolio explícito se usa el primero de la BD (antes estaba
            # hardcodeado "Negocio A", que dejaba de existir si lo renombraban).
            coa_portfolio = portfolio or (portfolios[0]["name"] if portfolios else None)
            cur.execute("""
                SELECT id, code, name, parent_id, is_group, naturaleza, nivel
                FROM coa_accounts
                WHERE portfolio_name = %s
                ORDER BY code;
            """, (coa_portfolio,))
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
    except HTTPException:
        # El 404 de arriba es intencional: sin esto el `except Exception`
        # lo re-envolvía como 500 y el cliente no podía distinguir
        # "no existe" de "se cayó el servidor".
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/cache/invalidate")
def invalidate_cache():
    return {"status": "OK", "message": "Cache invalidado"}
