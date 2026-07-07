# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Perfil & Cuentas (4 endpoints)
Extracted from contabilidad.py — PURE refactor, zero logic changes."""
from fastapi import APIRouter, HTTPException

from routers.schemas import ProfileInput, AccountInput

router = APIRouter(tags=["Perfil & Cuentas"])


# ==============================================================================
# 🔌 Endpoints — Perfil & Cuentas
# ==============================================================================

@router.get("/api/profile")
def get_profile():
    try:
        from database_driver import obtener_perfil_usuario
        return obtener_perfil_usuario()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/profile")
def update_profile(profile: ProfileInput):
    try:
        from database_driver import actualizar_perfil_usuario
        success = actualizar_perfil_usuario(profile.dict())
        if not success:
            raise HTTPException(status_code=500, detail="No se pudo actualizar el perfil.")
        return {"status": "ACTUALIZADO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/accounts")
def list_accounts():
    try:
        from database_driver import obtener_cuentas
        return obtener_cuentas()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/accounts", status_code=201)
def add_account(acc: AccountInput):
    try:
        from database_driver import crear_cuenta
        new_id = crear_cuenta(acc.dict())
        return {"status": "CREADO", "account_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
