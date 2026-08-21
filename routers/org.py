# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Router: Organización (Empresas)
---------------------------------------------------
CRUD de entidades organizacionales para el selector de empresa.
Endpoints: /api/org/*
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["Organización"])


# ── Modelos Pydantic ──

class OrgEntityCreateInput(BaseModel):
    """Datos para crear una entidad organizacional."""
    name: str
    type: str = "EMPRESA"
    parent_id: Optional[int] = None
    industry: Optional[str] = "ESTANDAR"
    portfolio_id: Optional[int] = None


class OrgEntityUpdateInput(BaseModel):
    """Datos para actualizar una entidad organizacional."""
    name: Optional[str] = None
    type: Optional[str] = None
    industry: Optional[str] = None
    status: Optional[str] = None
    parent_id: Optional[int] = None
    portfolio_id: Optional[int] = None


class OrgEntityIndustryInput(BaseModel):
    """Datos para actualizar solo la industria de una entidad."""
    industry: str


# ── Endpoints ──

@router.get("/api/org/entities/selector")
def org_get_entities_selector():
    """Retorna entidades formateadas para el dropdown de selección de empresa."""
    try:
        from fin_sys_core.org_driver import get_entities_for_selector
        return get_entities_for_selector()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/org/consolidated")
def org_get_consolidated():
    """Consolidado real por entidad (cifras del portafolio vinculado).

    Reemplaza el patrón anterior del frontend, que pedía N veces
    /api/dashboard-data?portfolio=<nombre-de-la-entidad>: el nombre de una
    entidad no es el nombre de un portafolio, así que todas las filas recibían
    el mismo payload vacío y el total lo multiplicaba por N.
    """
    try:
        from fin_sys_core.org_driver import get_consolidated_by_entity
        return get_consolidated_by_entity()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/org/entities/tree")
def org_get_entity_tree():
    """Retorna el árbol completo de entidades con hijos anidados."""
    try:
        from fin_sys_core.org_driver import get_entity_tree
        return get_entity_tree()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/org/entities", status_code=201)
def org_create_entity(body: OrgEntityCreateInput):
    """Crea una nueva entidad organizacional."""
    try:
        from fin_sys_core.org_driver import create_entity_basic
        return create_entity_basic(
            name=body.name,
            type=body.type,
            parent_id=body.parent_id,
            industry=body.industry,
            portfolio_id=body.portfolio_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/org/entities/{entity_id}")
def org_update_entity(entity_id: int, body: OrgEntityUpdateInput):
    """Actualiza campos de una entidad existente."""
    try:
        from fin_sys_core.org_driver import update_entity_basic
        # Solo los campos que el cliente envió de verdad. Antes se filtraba por
        # `is not None`, lo que hacía imposible poner un campo en NULL: mandar
        # {"portfolio_id": null} para desvincular una empresa se descartaba en
        # silencio y la API respondía 200 como si hubiera funcionado.
        data = body.dict(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar.")
        return update_entity_basic(entity_id=entity_id, data=data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/org/entities/{entity_id}/industry")
def org_update_entity_industry(entity_id: int, body: OrgEntityIndustryInput):
    """Actualiza únicamente la industria de una entidad."""
    try:
        from fin_sys_core.org_driver import update_entity_industry
        return update_entity_industry(
            entity_id=entity_id,
            industry=body.industry,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
