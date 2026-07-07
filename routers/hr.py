# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Router: RRHH (Módulo 08c)
----------------------------------------------
Perfil, salario, empresas, documentos, categorías, pagos.
Endpoints: /api/hr/*
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(tags=["RRHH"])


# ── Endpoints ──

@router.get("/api/hr/profile/{user_id}")
def hr_get_profile(user_id: str, workspace_id: str = "default"):
    try:
        from fin_sys_core.hr_driver import get_hr_profile
        return get_hr_profile(user_id, workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/hr/profile/{user_id}")
def hr_update_profile(user_id: str, body: dict):
    try:
        from fin_sys_core.hr_driver import update_hr_profile
        ws = body.pop("workspace_id", "default")
        return update_hr_profile(user_id, ws, body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/hr/salary/{user_id}")
def hr_get_salary(user_id: str, workspace_id: str = "default"):
    try:
        from fin_sys_core.hr_driver import get_hr_salary
        return get_hr_salary(user_id, workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/hr/salary/{user_id}")
def hr_update_salary(user_id: str, body: dict):
    try:
        from fin_sys_core.hr_driver import update_hr_salary
        ws = body.pop("workspace_id", "default")
        return update_hr_salary(user_id, ws, body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/hr/companies/{user_id}")
def hr_get_companies(user_id: str):
    try:
        from fin_sys_core.hr_driver import get_employee_companies
        return get_employee_companies(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hr/companies/{user_id}")
def hr_add_company(user_id: str, body: dict):
    try:
        from fin_sys_core.hr_driver import add_employee_company
        return add_employee_company(
            user_id, body.get("entity_id"), body.get("entity_name", ""),
            body.get("workspace_id", "default"), body.get("role", "Empleado"),
            body.get("start_date")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/hr/folders/{workspace_id}")
def hr_get_folders(workspace_id: str):
    try:
        from fin_sys_core.hr_documents_driver import get_folders
        return get_folders(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hr/folders/{workspace_id}")
def hr_create_folder(workspace_id: str, body: dict):
    try:
        from fin_sys_core.hr_documents_driver import create_folder
        return create_folder(workspace_id, body.get("name", ""), body.get("parent_id"), body.get("color"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/hr/documents/{user_id}")
def hr_get_documents(user_id: str, workspace_id: str = "default", folder_id: Optional[str] = None):
    try:
        from fin_sys_core.hr_documents_driver import get_documents
        return get_documents(user_id, workspace_id, folder_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hr/documents/{user_id}")
def hr_save_document(user_id: str, body: dict):
    try:
        from fin_sys_core.hr_documents_driver import save_document_metadata
        ws = body.get("workspace_id", "default")
        return save_document_metadata(
            user_id, ws, body.get("name", ""), body.get("doc_type", ""),
            body.get("file_data"), body.get("file_name"), body.get("mime_type"),
            body.get("folder_id"), body.get("notes"), body.get("category_id")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hr/salary/calculate")
def hr_calculate_salary(body: dict):
    """Endpoint huérfano — mantener hasta limpieza técnica."""
    return {"status": "NOT_IMPLEMENTED", "message": "Cálculo ocurre localmente en SalaryTab.jsx"}

@router.post("/api/hr/storage/sign-upload")
def hr_sign_upload(body: dict):
    """Endpoint huérfano — sustituido por data URL base64."""
    return {"status": "NOT_IMPLEMENTED", "message": "Bucket bloquea MIME, usando base64"}

@router.get("/api/hr/categories/{workspace_id}")
def hr_get_categories(workspace_id: str):
    try:
        from fin_sys_core.hr_driver import get_doc_categories
        return get_doc_categories(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hr/categories/{workspace_id}")
def hr_add_category(workspace_id: str, body: dict):
    try:
        from fin_sys_core.hr_driver import add_doc_category
        return add_doc_category(workspace_id, body.get("name", ""), body.get("color", "#666"), body.get("sort_order", 0))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/hr/payments/{user_id}")
def hr_get_payments(user_id: str, workspace_id: str = "default"):
    try:
        from fin_sys_core.hr_driver import get_payment_records
        return get_payment_records(user_id, workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hr/payments/{user_id}")
def hr_add_payment(user_id: str, body: dict):
    try:
        from fin_sys_core.hr_driver import add_payment_record
        ws = body.pop("workspace_id", "default")
        return add_payment_record(user_id, ws, body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
