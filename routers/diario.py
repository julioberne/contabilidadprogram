# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Libro Diario (Módulo 02) con filtros en servidor.

GET /api/diario/movimientos  → página + totales (+ grupos) de lo filtrado
GET /api/diario/opciones     → valores existentes para llenar los selectores

Solo lectura. La lógica vive en fin_sys_core/diario_query.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from psycopg2 import errors as pg_errors

from routers.auth_guard import require_auth

router = APIRouter(tags=["Diario"])

_LENTA = ("La consulta tardó demasiado. Acota los filtros (fechas, empresa o "
          "búsqueda) e intenta de nuevo.")


def _demasiado_lenta():
    # 503 + Retry-After (estándar P6/P7): el cliente reintenta con calma o acota.
    return HTTPException(status_code=503, detail=_LENTA, headers={"Retry-After": "5"})


def _ocupado(e):
    # Sin cupo del Diario en este worker (estándar H4, P4): reintentar en 2 s.
    return HTTPException(status_code=503, detail=str(e), headers={"Retry-After": "2"})


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
    totales: bool = True,
    despues_fecha: Optional[str] = None,
    despues_id: Optional[str] = None,
    _u: dict = Depends(require_auth),
):
    from fin_sys_core.diario_query import DiarioOcupado, buscar_movimientos

    filtros = {
        "empresas": _empresas(portfolio, empresas), "q": q, "tipos": tipos,
        "desde": desde, "hasta": hasta, "terceros": terceros, "cuentas": cuentas,
        "categorias": categorias, "etiquetas": etiquetas, "monto_min": monto_min,
        "monto_max": monto_max, "moneda": moneda, "cartera": cartera,
        "cartera_estado": cartera_estado, "banderas": banderas,
    }
    despues = (despues_fecha, despues_id) if (despues_fecha or despues_id) else None
    try:
        return buscar_movimientos(filtros, orden=orden, agrupar=agrupar or None,
                                  limit=limit, offset=offset, totales=totales, despues=despues)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DiarioOcupado as e:
        raise _ocupado(e)
    except pg_errors.QueryCanceled:
        raise _demasiado_lenta()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/diario/opciones")
def diario_opciones(portfolio: Optional[str] = None, empresas: Optional[str] = None,
                    campo: Optional[str] = None, q: Optional[str] = None,
                    sel_terceros: Optional[str] = None, sel_cuentas: Optional[str] = None,
                    sel_categorias: Optional[str] = None, sel_etiquetas: Optional[str] = None,
                    _u: dict = Depends(require_auth)):
    """Top-50 por lista (+ lo ya elegido) y `mas`; con `campo` y `q`, solo esa
    lista filtrada en el servidor (el buscador del selector)."""
    from fin_sys_core.diario_query import DiarioOcupado, opciones_filtros
    sel = {"terceros": sel_terceros, "cuentas": sel_cuentas,
           "categorias": sel_categorias, "etiquetas": sel_etiquetas}
    try:
        return opciones_filtros(_empresas(portfolio, empresas), campo=campo or None, q=q, sel=sel)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DiarioOcupado as e:
        raise _ocupado(e)
    except pg_errors.QueryCanceled:
        raise _demasiado_lenta()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
