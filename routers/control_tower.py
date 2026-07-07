# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Router: Control Tower (Módulo 07)
-----------------------------------------------------
Entidades, usuarios workspace, resource IDs, aprobaciones, miembros, quick-TX.
Endpoints: /api/ct/*
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter(tags=["Control Tower"])


# ── Modelos Pydantic ──

class EntityInput(BaseModel):
    name: str
    type: str = "EMPRESA"
    parent_id: Optional[int] = None
    portfolio_id: Optional[int] = None
    industry: Optional[str] = ""
    sub_industry: Optional[str] = ""
    status: Optional[str] = "AL DIA"

class CTUserRegisterInput(BaseModel):
    name: str
    email: str
    password: str
    role_label: str = "Colaborador"
    permissions: Optional[Dict[str, Any]] = None
    parent_user_id: Optional[int] = None

class CTLoginInput(BaseModel):
    email: str
    password: str

class ResourceIdInput(BaseModel):
    entity_id: int
    label: str
    value: str
    category: str = "FISCAL"
    expires_at: Optional[str] = None
    notes: Optional[str] = None

class ApprovalInput(BaseModel):
    entity_id: int
    transaction_id: Optional[int] = None
    requested_by: Optional[int] = None
    description: Optional[str] = None
    amount: Optional[float] = None

class ResolveApprovalInput(BaseModel):
    status: str  # APROBADO | RECHAZADO
    reviewer_id: int
    notes: Optional[str] = ""

class MemberInviteInput(BaseModel):
    user_id: int
    role_label: str = "Colaborador"
    permissions: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None

class CTQuickTransactionInput(BaseModel):
    entity_id: int
    portfolio_name: str
    type: str  # INGRESO | GASTO
    amount: float
    concept: str
    category: str
    payment_method: str
    third_party_name: str
    third_party_id_number: str
    third_party_id_type: str = "NIT"


# ── Endpoints: Entidades ──

@router.get("/api/ct/entities")
def ct_get_entities():
    try:
        from control_tower_driver import obtener_entidades_arbol
        return obtener_entidades_arbol()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/ct/entities", status_code=201)
def ct_create_entity(data: EntityInput):
    try:
        from control_tower_driver import crear_entidad
        new_id = crear_entidad(data.dict())
        return {"status": "CREADO", "entity_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/api/ct/entities/{entity_id}/status")
def ct_update_entity_status(entity_id: int, status: str):
    try:
        from control_tower_driver import actualizar_estado_entidad
        actualizar_estado_entidad(entity_id, status)
        return {"status": "ACTUALIZADO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/ct/entities/{entity_id}")
def ct_delete_entity(entity_id: int):
    try:
        from control_tower_driver import eliminar_entidad
        eliminar_entidad(entity_id)
        return {"status": "ELIMINADO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/ct/entities/{entity_id}/kpis")
def ct_get_entity_kpis(entity_id: int):
    try:
        from control_tower_driver import obtener_kpis_entidad
        return obtener_kpis_entidad(entity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoints: Usuarios del Workspace ──

@router.get("/api/ct/users")
def ct_get_users():
    try:
        from control_tower_driver import obtener_workspace_users
        return obtener_workspace_users()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/ct/users/register", status_code=201)
def ct_register_user(data: CTUserRegisterInput):
    try:
        from control_tower_driver import registrar_workspace_user
        user = registrar_workspace_user(data.dict())
        return {"status": "REGISTRADO", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/ct/users/login")
def ct_login_user(data: CTLoginInput):
    try:
        from control_tower_driver import login_workspace_user
        user = login_workspace_user(data.email, data.password)
        if not user:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        return {"status": "OK", "user": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoints: Resource IDs ──

@router.get("/api/ct/entities/{entity_id}/resources")
def ct_get_resources(entity_id: int):
    try:
        from control_tower_driver import obtener_resource_ids
        return obtener_resource_ids(entity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/ct/resources", status_code=201)
def ct_create_resource(data: ResourceIdInput):
    try:
        from control_tower_driver import crear_resource_id
        new_id = crear_resource_id(data.dict())
        return {"status": "CREADO", "resource_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/ct/resources/{rid}")
def ct_delete_resource(rid: int):
    try:
        from control_tower_driver import eliminar_resource_id
        eliminar_resource_id(rid)
        return {"status": "ELIMINADO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoints: Aprobaciones ──

@router.get("/api/ct/approvals")
def ct_get_approvals(entity_id: Optional[int] = None):
    try:
        from control_tower_driver import obtener_aprobaciones
        return obtener_aprobaciones(entity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/ct/approvals", status_code=201)
def ct_create_approval(data: ApprovalInput):
    try:
        from control_tower_driver import crear_aprobacion
        new_id = crear_aprobacion(data.dict())
        return {"status": "CREADO", "approval_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/api/ct/approvals/{approval_id}/resolve")
def ct_resolve_approval(approval_id: int, data: ResolveApprovalInput):
    try:
        from control_tower_driver import resolver_aprobacion
        resolver_aprobacion(approval_id, data.status, data.reviewer_id, data.notes)
        return {"status": "RESUELTO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Endpoints: Miembros por entidad ──

@router.get("/api/ct/entities/{entity_id}/members")
def ct_get_members(entity_id: int):
    try:
        from control_tower_driver import obtener_miembros_entidad
        return obtener_miembros_entidad(entity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/ct/entities/{entity_id}/members", status_code=201)
def ct_invite_member(entity_id: int, data: MemberInviteInput):
    try:
        from control_tower_driver import invitar_miembro
        perms = data.permissions or {"ledger": True, "reports": True}
        new_id = invitar_miembro(entity_id, data.user_id, data.role_label, perms, data.expires_at)
        return {"status": "INVITADO", "member_id": new_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Transacción Rápida desde Control Tower ──

@router.post("/api/ct/quick-transaction", status_code=201)
def ct_quick_transaction(data: CTQuickTransactionInput):
    """Registra una transacción rápida desde el panel lateral del Control Tower."""
    try:
        from tax_motor import process_transaction_taxes
        tax_results = process_transaction_taxes(
            base_amount=data.amount, apply_iva=False, apply_gmf=False
        )
        tx_data = {
            "portfolio_name": data.portfolio_name,
            "type": data.type,
            "amount": data.amount,
            "concept": data.concept,
            "payment_method": data.payment_method,
            "category": data.category,
            "transaction_date": __import__('datetime').date.today().isoformat(),
            "third_party": {
                "identification_type": data.third_party_id_type,
                "identification_number": data.third_party_id_number,
                "name": data.third_party_name,
            },
            "tax_iva_percentage": 0.0, "tax_iva_amount": 0.0,
            "tax_gmf_percentage": 0.0, "tax_gmf_amount": 0.0,
            "custom_tax_amount": 0.0,
            "net_value": tax_results["net_value"],
        }
        from database_driver import registrar_transaccion
        tx_id = registrar_transaccion(tx_data)
        return {"status": "EXITOSO", "transaction_id": tx_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
