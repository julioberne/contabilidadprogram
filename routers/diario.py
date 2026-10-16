# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Libro Diario (Módulo 02) con filtros en servidor.

GET /api/diario/movimientos  → página + totales (+ grupos) de lo filtrado
GET /api/diario/opciones     → valores existentes para llenar los selectores

Solo lectura. La lógica vive en fin_sys_core/diario_query.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from routers.auth_guard import require_auth

router = APIRouter(tags=["Diario"])


def _empresas(portfolio: Optional[str], empresas: Optional[str]):
    """`empresas=*` → todas; `empresas=A,B` → esas; nada → el portafolio activo."""
    if empresas == "*":
        return []
    if empresas:
        return [e.strip() for e in empresas.split(",") if e.strip()]
    return [portfolio] if portfolio else []


@router.get("/api/diario/movimientos")
def diario_movimientos(
    portfolio: Optional[str] = None,
    empresas: Optional[str] = None,
    q: Optional[str] = None,
    tipos: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    terceros: Optional[str] = None,
    cuentas: Optional[str] = None,
    categorias: Optional[str] = None,
    etiquetas: Optional[str] = None,
    monto_min: Optional[str] = None,
    monto_max: Optional[str] = None,
    moneda: Optional[str] = None,
    cartera: Optional[str] = None,
    cartera_estado: Optional[str] = None,
    banderas: Optional[str] = None,
    orden: str = "fecha_desc",
    agrupar: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    _u: dict = Depends(require_auth),
):
    from fin_sys_core.diario_query import buscar_movimientos

    filtros = {
        "empresas": _empresas(portfolio, empresas), "q": q, "tipos": tipos,
        "desde": desde, "hasta": hasta, "terceros": terceros, "cuentas": cuentas,
        "categorias": categorias, "etiquetas": etiquetas, "monto_min": monto_min,
        "monto_max": monto_max, "moneda": moneda, "cartera": cartera,
        "cartera_estado": cartera_estado, "banderas": banderas,
    }
    try:
        return buscar_movimientos(filtros, orden=orden, agrupar=agrupar or None,
                                  limit=limit, offset=offset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/diario/opciones")
def diario_opciones(portfolio: Optional[str] = None, empresas: Optional[str] = None,
                    _u: dict = Depends(require_auth)):
    from fin_sys_core.diario_query import opciones_filtros
    try:
        return opciones_filtros(_empresas(portfolio, empresas))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
