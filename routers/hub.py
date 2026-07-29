# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Router: Project Hub (Módulo 08)
---------------------------------------------------
Workspaces, usuarios, entidades, proyectos, tareas, notas, eventos, métricas.
Endpoints: /api/hub/*
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from routers.auth_guard import require_auth, require_admin

router = APIRouter(tags=["Project Hub"])


# ══════════════════════════════════════════════════════════════════════════════
# Modelos Pydantic del Hub
# ══════════════════════════════════════════════════════════════════════════════

class HubWorkspaceCreate(BaseModel):
    name: str
    nit: Optional[str] = None
    logo_url: Optional[str] = None
    owner_id: Optional[str] = None

class HubUserRegister(BaseModel):
    email: str
    password: str
    name: str
    cedula: Optional[str] = None
    description: Optional[str] = None
    workspace_id: Optional[str] = None
    role: str = "member"

class HubUserLogin(BaseModel):
    email: str
    password: str

class HubMemberCreate(BaseModel):
    workspace_id: str
    name: str
    email: Optional[str] = None
    cedula: Optional[str] = None
    description: Optional[str] = None
    role: str = "member"
    password: Optional[str] = None

class HubUserUpdate(BaseModel):
    workspace_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    cedula: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None

class HubPasswordChange(BaseModel):
    old_password: str
    new_password: str

class HubRoleChange(BaseModel):
    role: str

class HubEntityCreate(BaseModel):
    workspace_id: str
    name: str
    entity_type: str = "CUSTOM"
    parent_id: Optional[str] = None
    description: Optional[str] = None
    color: str = "#0EA5E9"

class HubProjectCreate(BaseModel):
    workspace_id: str
    name: str
    entity_id: Optional[str] = None
    description: Optional[str] = None
    color: str = "#0EA5E9"
    created_by: Optional[str] = None

class HubTaskCreate(BaseModel):
    workspace_id: str
    project_id: str
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[str] = None
    created_by: Optional[str] = None
    assignee_ids: List[str] = []

class HubTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    position: Optional[int] = None
    assignee_ids: Optional[List[str]] = None

class HubNoteCreate(BaseModel):
    workspace_id: str
    user_id: str
    title: str = "Sin titulo"
    project_id: Optional[str] = None

class HubNoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[list] = None
    is_private: Optional[bool] = None

class HubEventCreate(BaseModel):
    workspace_id: str
    title: str
    start_time: str
    end_time: str
    description: Optional[str] = None
    all_day: bool = False
    color: Optional[str] = None
    created_by: Optional[str] = None
    project_id: Optional[str] = None
    attendee_ids: List[str] = []

class HubEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    all_day: Optional[bool] = None
    color: Optional[str] = None
    attendee_ids: Optional[List[str]] = None

class HubMemberAdd(BaseModel):
    workspace_id: str
    user_id: str
    role: str = "member"


# ── WORKSPACES ────────────────────────────────────────────────────────────────

@router.post("/api/hub/workspaces")
def hub_create_workspace(data: HubWorkspaceCreate):
    try:
        from fin_sys_core.hub_driver import create_workspace
        ws = create_workspace(name=data.name, nit=data.nit,
                              logo_url=data.logo_url, owner_id=data.owner_id)
        return {"status": "ok", "workspace": ws}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/hub/workspaces/{workspace_id}")
def hub_delete_workspace(workspace_id: str):
    """Elimina un workspace y todo su contenido (cascade). Irreversible."""
    try:
        from fin_sys_core.hub_driver import delete_workspace
        ok = delete_workspace(workspace_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Workspace no encontrado")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/hub/workspaces")
def hub_get_workspaces(user_id: str = None, all: bool = False):
    try:
        from fin_sys_core.hub_driver import get_workspaces_for_user, get_all_workspaces
        if all:
            return get_all_workspaces()
        if user_id:
            return get_workspaces_for_user(user_id)
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── USERS ─────────────────────────────────────────────────────────────────────

@router.post("/api/hub/users/register")
def hub_register(data: HubUserRegister):
    try:
        from fin_sys_core.hub_driver import register_user
        user = register_user(
            email=data.email, password=data.password, name=data.name,
            cedula=data.cedula, description=data.description,
            workspace_id=data.workspace_id, role=data.role
        )
        return {"status": "ok", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hub/users/login")
def hub_login(data: HubUserLogin):
    try:
        from fin_sys_core.hub_driver import login_user
        from routers.auth_guard import create_session_token
        user = login_user(email=data.email, password=data.password)
        if not user:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        return {"status": "ok", "user": user, "token": create_session_token(user)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/hub/users")
def hub_get_members(workspace_id: str):
    try:
        from fin_sys_core.hub_driver import get_workspace_members
        return get_workspace_members(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/hub/users/me/password")
def hub_change_own_password(data: HubPasswordChange, auth: dict = Depends(require_auth)):
    """Cambio de contraseña del PROPIO usuario (MI CUENTA), verificando la actual."""
    try:
        from fin_sys_core.hub_driver import change_password
        result = change_password(auth["uid"], data.old_password, data.new_password)
        if result == "ok":
            return {"status": "ok"}
        detail = {
            "wrong_old": "La contraseña actual es incorrecta.",
            "not_found": "Usuario no encontrado.",
            "no_login":  "Esta cuenta no tiene acceso con contraseña.",
        }.get(result, "No se pudo cambiar la contraseña.")
        raise HTTPException(status_code=400, detail=detail)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/hub/users/all")
def hub_get_all_users(_admin: dict = Depends(require_admin)):
    """Todos los usuarios del sistema (panel USUARIOS Y ROLES — solo owner/admin)."""
    try:
        from fin_sys_core.hub_driver import get_all_users
        return get_all_users()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/hub/users/{user_id}/role")
def hub_set_user_role(user_id: str, data: HubRoleChange, _admin: dict = Depends(require_admin)):
    """Cambia el rol global de un usuario (solo owner/admin)."""
    try:
        from fin_sys_core.hub_driver import set_user_role
        updated = set_user_role(user_id, data.role)
        if not updated:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        return {"status": "ok", "user": updated}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hub/users/add-member")
def hub_add_member(data: HubMemberAdd):
    try:
        from fin_sys_core.hub_driver import add_member_to_workspace
        result = add_member_to_workspace(data.workspace_id, data.user_id, data.role)
        return {"status": "ok", "member": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hub/users", status_code=201)
def hub_create_member(data: HubMemberCreate):
    """Crea una persona (ficha de roster) y la vincula al workspace."""
    try:
        from fin_sys_core.hub_driver import create_member
        member = create_member(
            workspace_id=data.workspace_id, name=data.name, email=data.email,
            cedula=data.cedula, description=data.description,
            role=data.role, password=data.password,
        )
        return {"status": "ok", "member": member}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/hub/users/{user_id}")
def hub_update_member(user_id: str, data: HubUserUpdate):
    """Edita nombre, email, cédula, descripción y rol de una persona."""
    try:
        from fin_sys_core.hub_driver import update_member
        member = update_member(
            user_id=user_id, workspace_id=data.workspace_id, name=data.name,
            email=data.email, cedula=data.cedula,
            description=data.description, role=data.role,
        )
        if not member:
            raise HTTPException(status_code=404, detail="Miembro no encontrado en este workspace")
        return {"status": "ok", "member": member}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/hub/users/{user_id}")
def hub_remove_member(user_id: str, workspace_id: str):
    """Desvincula a la persona del workspace (conserva su ficha de usuario)."""
    try:
        from fin_sys_core.hub_driver import remove_member_from_workspace
        ok = remove_member_from_workspace(workspace_id, user_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Miembro no encontrado en este workspace")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/hub/users/{user_id}/tasks")
def hub_get_user_tasks(user_id: str, workspace_id: str):
    """Tareas asignadas a una persona, con proyecto y empresa (para RENDIMIENTO)."""
    try:
        from fin_sys_core.hub_driver import get_user_tasks
        return get_user_tasks(workspace_id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── ENTITIES ──────────────────────────────────────────────────────────────────

@router.get("/api/hub/entities")
def hub_get_entities(workspace_id: str):
    try:
        from fin_sys_core.hub_driver import get_entity_tree
        return get_entity_tree(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hub/entities")
def hub_create_entity(data: HubEntityCreate):
    try:
        from fin_sys_core.hub_driver import create_entity
        entity = create_entity(
            workspace_id=data.workspace_id, name=data.name,
            entity_type=data.entity_type, parent_id=data.parent_id,
            description=data.description, color=data.color
        )
        return {"status": "ok", "entity": entity}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/hub/entities/{entity_id}")
def hub_delete_entity(entity_id: str):
    try:
        from fin_sys_core.hub_driver import delete_entity
        ok = delete_entity(entity_id)
        return {"status": "ok" if ok else "not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── PROJECTS ──────────────────────────────────────────────────────────────────

@router.get("/api/hub/projects")
def hub_get_projects(workspace_id: str, entity_id: str = None):
    try:
        from fin_sys_core.hub_driver import get_projects
        return get_projects(workspace_id, entity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hub/projects")
def hub_create_project(data: HubProjectCreate):
    try:
        from fin_sys_core.hub_driver import create_project
        project = create_project(
            workspace_id=data.workspace_id, name=data.name,
            entity_id=data.entity_id, description=data.description,
            color=data.color, created_by=data.created_by
        )
        return {"status": "ok", "project": project}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── TASKS ─────────────────────────────────────────────────────────────────────

@router.get("/api/hub/tasks/overview")
def hub_get_tasks_overview(workspace_id: str):
    """COMPENDIO: todas las tareas del workspace con asignados, empresa y estado."""
    try:
        from fin_sys_core.hub_driver import get_workspace_tasks_overview
        return get_workspace_tasks_overview(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/hub/tasks")
def hub_get_tasks(project_id: str, status: str = None):
    try:
        from fin_sys_core.hub_driver import get_tasks
        return get_tasks(project_id, status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hub/tasks")
def hub_create_task(data: HubTaskCreate):
    try:
        from fin_sys_core.hub_driver import create_task
        task = create_task(
            workspace_id=data.workspace_id, project_id=data.project_id,
            title=data.title, description=data.description,
            priority=data.priority, due_date=data.due_date,
            created_by=data.created_by, assignee_ids=data.assignee_ids
        )
        return {"status": "ok", "task": task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/hub/tasks/{task_id}")
def hub_update_task(task_id: str, data: HubTaskUpdate):
    try:
        from fin_sys_core.hub_driver import update_task
        task = update_task(
            task_id,
            **{k: v for k, v in data.dict().items() if v is not None}
        )
        return {"status": "ok", "task": task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/hub/tasks/{task_id}")
def hub_delete_task(task_id: str):
    try:
        from fin_sys_core.hub_driver import delete_task
        ok = delete_task(task_id)
        return {"status": "ok" if ok else "not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── NOTES ─────────────────────────────────────────────────────────────────────

@router.get("/api/hub/notes")
def hub_get_notes(workspace_id: str, user_id: str):
    try:
        from fin_sys_core.hub_driver import get_notes
        return get_notes(workspace_id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hub/notes")
def hub_create_note(data: HubNoteCreate):
    try:
        from fin_sys_core.hub_driver import create_note
        note = create_note(
            workspace_id=data.workspace_id, user_id=data.user_id,
            title=data.title, project_id=data.project_id
        )
        return {"status": "ok", "note": note}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/hub/notes/{note_id}")
def hub_update_note(note_id: str, data: HubNoteUpdate):
    try:
        from fin_sys_core.hub_driver import update_note
        note = update_note(
            note_id, title=data.title,
            content=data.content, is_private=data.is_private
        )
        return {"status": "ok", "note": note}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── EVENTS / CALENDAR ─────────────────────────────────────────────────────────

@router.get("/api/hub/events")
def hub_get_events(workspace_id: str):
    try:
        from fin_sys_core.hub_driver import get_events
        return get_events(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/hub/events")
def hub_create_event(data: HubEventCreate):
    try:
        from fin_sys_core.hub_driver import create_event
        event = create_event(
            workspace_id=data.workspace_id, title=data.title,
            start_time=data.start_time, end_time=data.end_time,
            description=data.description, all_day=data.all_day,
            color=data.color, created_by=data.created_by,
            project_id=data.project_id, attendee_ids=data.attendee_ids
        )
        return {"status": "ok", "event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/api/hub/events/{event_id}")
def hub_update_event(event_id: str, data: HubEventUpdate):
    try:
        from fin_sys_core.hub_driver import update_event
        event = update_event(
            event_id,
            **{k: v for k, v in data.dict().items() if v is not None}
        )
        return {"status": "ok", "event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── METRICS ───────────────────────────────────────────────────────────────────

@router.get("/api/hub/metrics")
def hub_get_metrics(workspace_id: str):
    try:
        from fin_sys_core.hub_driver import get_user_metrics
        return get_user_metrics(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
