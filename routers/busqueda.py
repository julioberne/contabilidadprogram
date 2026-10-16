# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: búsqueda remota única (estándar de consultas, H3).

GET /api/buscar/terceros?q=&limite=&ids=&ident=   → top-N + `mas`
GET /api/buscar/cuentas?q=&limite=&ids=
GET /api/buscar/etiquetas?q=&limite=

Contrato para todos los selectores (web, Mini App, bot): nunca el catálogo
completo. La lógica vive en fin_sys_core/consultas/busqueda.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from psycopg2 import errors as pg_errors

from routers.auth_guard import require_auth

router = APIRouter(tags=["Búsqueda"])


def _envolver(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except pg_errors.QueryCanceled:
        raise HTTPException(status_code=503, detail="La búsqueda tardó demasiado. Escribe algo más específico.",
                            headers={"Retry-After": "2"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/buscar/terceros")
def buscar_terceros(q: str = "", limite: int = 8, ids: Optional[str] = None, ident: Optional[str] = None,
                    _u: dict = Depends(require_auth)):
    from fin_sys_core.consultas.busqueda import buscar_terceros as _buscar
    if len(q) > 120:
        raise HTTPException(status_code=400, detail="La búsqueda es demasiado larga (máximo 120 caracteres).")
    return _envolver(_buscar, q, limite, ids, ident)


@router.get("/api/buscar/cuentas")
def buscar_cuentas(q: str = "", limite: int = 8, ids: Optional[str] = None, _u: dict = Depends(require_auth)):
    from fin_sys_core.consultas.busqueda import buscar_cuentas as _buscar
    return _envolver(_buscar, q[:120], limite, ids)


@router.get("/api/buscar/etiquetas")
def buscar_etiquetas(q: str = "", limite: int = 8, _u: dict = Depends(require_auth)):
    from fin_sys_core.consultas.busqueda import buscar_etiquetas as _buscar
    return _envolver(_buscar, q[:120], limite)
