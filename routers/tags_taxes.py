# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Tags & Impuestos Personalizados (4 endpoints)
Extracted from contabilidad.py — PURE refactor, zero logic changes."""
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Tags & Impuestos"])


# ==============================================================================
# 🏷️ Tags & Impuestos Personalizados
# ==============================================================================

@router.get("/api/tags")
def list_tags():
    try:
        from fin_sys_core.database_driver import listar_tags
        return listar_tags()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/tags", status_code=201)
def create_tag(body: dict):
    try:
        from fin_sys_core.database_driver import crear_tag
        return crear_tag(body.get("name", ""), body.get("color", "#000000"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/custom-taxes")
def list_custom_taxes():
    try:
        from fin_sys_core.database_driver import listar_custom_taxes
        return listar_custom_taxes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/custom-taxes", status_code=201)
def create_custom_tax(body: dict):
    try:
        from fin_sys_core.database_driver import crear_custom_tax
        return crear_custom_tax(body.get("name", ""), float(body.get("rate", 0)), body.get("tax_type", "ADDITIVE"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
