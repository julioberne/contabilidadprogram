# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: COA & Terceros & Health (5 endpoints)
Extracted from contabilidad.py — PURE refactor, zero logic changes."""
from fastapi import APIRouter, HTTPException

from routers.schemas import CoaTemplateInput, CoaAccountInput

router = APIRouter(tags=["COA & Terceros"])


# ==============================================================================
# 🔌 Endpoints — COA (Catálogo de Cuentas)
# ==============================================================================

@router.get("/api/coa")
def get_coa_tree(portfolio: str):
    """Obtiene el árbol del catálogo de cuentas"""
    try:
        from database_driver import obtener_coa_tree
        tree = obtener_coa_tree(portfolio)
        return {"status": "OK", "data": tree}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/coa/template")
def load_coa_template(payload: CoaTemplateInput):
    """Carga una plantilla COA para un portafolio"""
    try:
        from database_driver import cargar_plantilla_coa
        success = cargar_plantilla_coa(payload.portfolio_name, payload.template_name)
        if not success:
            raise HTTPException(status_code=500, detail="No se pudo cargar la plantilla COA. Verifica la base de datos.")
        return {"status": "CARGADO", "message": f"Plantilla {payload.template_name} cargada con éxito."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/coa/account")
def add_coa_account(payload: CoaAccountInput):
    """Agrega una cuenta personalizada al COA"""
    from database_driver import agregar_cuenta_coa
    try:
        acc_data = {
            "code": payload.code,
            "name": payload.name,
            "type": payload.type,
            "is_group": payload.is_group,
            "parent_code": payload.parent_code
        }
        success = agregar_cuenta_coa(payload.portfolio_name, acc_data)
        if not success:
            raise HTTPException(status_code=500, detail="Error guardando cuenta.")
        return {"status": "CREADO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# 🔌 Endpoints — Terceros
# ==============================================================================

@router.get("/api/third-parties")
def get_third_parties():
    try:
        from database_driver import obtener_terceros
        return obtener_terceros()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# 📊 Health
# ==============================================================================

@router.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0"}
