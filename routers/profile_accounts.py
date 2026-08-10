# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Perfil & Cuentas (4 endpoints)
Extracted from contabilidad.py — PURE refactor, zero logic changes."""
from fastapi import APIRouter, HTTPException

from routers.schemas import ProfileInput, AccountInput, AccountUpdateInput

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


@router.put("/api/accounts/{account_id}")
def update_account(account_id: int, acc: AccountUpdateInput):
    try:
        from database_driver import actualizar_cuenta
        if not actualizar_cuenta(account_id, acc.dict()):
            raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
        # Saldo inicial: actualizar_cuenta (driver estable) no lo cubre — se
        # maneja aquí. Editarlo NO recalcula current_balance automáticamente:
        # para eso está ⟳ Reconciliar (inicial + transacciones reales).
        if acc.initial_balance is not None:
            from db_pool import get_conn, put_conn
            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute("UPDATE user_accounts SET initial_balance = %s WHERE id = %s",
                            (float(acc.initial_balance), account_id))
                conn.commit()
                cur.close()
            finally:
                put_conn(conn)
        return {"status": "ACTUALIZADO"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/accounts/{account_id}")
def delete_account(account_id: int):
    try:
        from database_driver import eliminar_cuenta
        if not eliminar_cuenta(account_id):
            raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
        return {"status": "ELIMINADO"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
