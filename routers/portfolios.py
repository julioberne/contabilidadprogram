# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Portafolios (3 endpoints)
Extracted from contabilidad.py — PURE refactor, zero logic changes."""
from fastapi import APIRouter, HTTPException
from typing import Optional

from routers.schemas import PortfolioInput

router = APIRouter(tags=["Portafolios"])


# ==============================================================================
# 🔌 Endpoints de la API — Portafolios
# ==============================================================================

@router.get("/api/portfolios")
def get_portfolios():
    try:
        from database_driver import obtener_portafolios
        ports = obtener_portafolios()
        if not ports:
            # Fallback a iniciales por defecto si está vacío
            ports = [
                {"id": 1, "name": "Negocio A", "industry_type": "ESTANDAR"},
                {"id": 2, "name": "Negocio B", "industry_type": "ESTANDAR"},
                {"id": 3, "name": "Finanzas Personales", "industry_type": "ESTANDAR"}
            ]
        return ports
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/portfolios", status_code=201)
def create_portfolio_endpoint(port_input: PortfolioInput):
    try:
        from database_driver import crear_portafolio
        new_id = crear_portafolio(port_input.name, port_input.industry_type, port_input.sub_industry_type)
        if not new_id:
             raise HTTPException(status_code=500, detail="Error al crear el portafolio")
        return {"status": "CREADO", "portfolio_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/portfolios/balance")
def get_caja_viva_balance(portfolio: Optional[str] = None):
    """
    Obtiene los agregados acumulados de la Caja Viva en tiempo real.
    Suma el total de ingresos, gastos, balance neto y patrimonio con alertas.
    """
    try:
        from database_driver import obtener_transacciones, obtener_cuentas
        from ledger_math import calculate_caja_viva
        txs = obtener_transacciones(portfolio)
        accounts = obtener_cuentas()
        totals = calculate_caja_viva(txs, accounts)
        return {
            "status": totals["status"],
            "total_ingresos": totals["total_ingresos"],
            "total_gastos": totals["total_gastos"],
            "balance_neto": totals["balance_neto"],
            "capital_inicial": totals.get("capital_inicial", 5000000.0),
            "patrimonio": totals.get("patrimonio", 5000000.0),
            
            # Nuevos agregados separados
            "total_ingresos_cop": totals["total_ingresos_cop"],
            "total_gastos_cop": totals["total_gastos_cop"],
            "balance_neto_cop": totals["balance_neto_cop"],
            "patrimonio_cop": totals["patrimonio_cop"],
            
            "total_ingresos_usd": totals["total_ingresos_usd"],
            "total_gastos_usd": totals["total_gastos_usd"],
            "balance_neto_usd": totals["balance_neto_usd"],
            "patrimonio_usd": totals["patrimonio_usd"],
            
            "alerts": totals.get("alerts", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
