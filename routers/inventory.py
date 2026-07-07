# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Router: Inventario
--------------------------------------
CRUD de artículos + movimientos de inventario.
Endpoints: /api/inventory/*
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["Inventario"])


# ── Modelos Pydantic ──

class InventoryItemCreateInput(BaseModel):
    """Datos para crear un artículo de inventario."""
    portfolio_name: str
    name: str
    company_id: Optional[int] = None
    sku: Optional[str] = ""
    category: Optional[str] = "General"
    unit: Optional[str] = "unidad"
    cost_price: Optional[float] = 0
    sell_price: Optional[float] = 0
    current_stock: Optional[int] = 0
    min_stock: Optional[int] = 0


class InventoryItemUpdateInput(BaseModel):
    """Datos para actualizar un artículo de inventario."""
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    cost_price: Optional[float] = None
    sell_price: Optional[float] = None
    current_stock: Optional[int] = None
    min_stock: Optional[int] = None
    status: Optional[str] = None


class InventoryMovementInput(BaseModel):
    """Datos para registrar un movimiento de inventario."""
    item_id: int
    type: str  # ENTRADA, SALIDA, AJUSTE
    quantity: int
    unit_price: Optional[float] = 0
    reference: Optional[str] = None
    transaction_id: Optional[int] = None
    third_party_id: Optional[int] = None
    notes: Optional[str] = None


# ── Endpoints ──

@router.get("/api/inventory/items")
def inventory_list_items(portfolio: str = "Principal", company_id: Optional[int] = None):
    """Retorna todos los artículos de inventario de un portafolio."""
    try:
        from fin_sys_core.inventory_driver import get_items
        return get_items(portfolio, company_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/inventory/items", status_code=201)
def inventory_create_item(body: InventoryItemCreateInput):
    """Crea un nuevo artículo en el catálogo de inventario."""
    try:
        from fin_sys_core.inventory_driver import create_item
        return create_item(body.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/inventory/items/{item_id}")
def inventory_update_item(item_id: int, body: InventoryItemUpdateInput):
    """Actualiza campos de un artículo existente."""
    try:
        from fin_sys_core.inventory_driver import update_item
        # Solo enviar campos que no sean None
        data = {k: v for k, v in body.dict().items() if v is not None}
        return update_item(item_id, data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/inventory/items/{item_id}")
def inventory_delete_item(item_id: int):
    """Marca un artículo como ELIMINADO (soft delete)."""
    try:
        from fin_sys_core.inventory_driver import delete_item
        return delete_item(item_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/inventory/movements", status_code=201)
def inventory_register_movement(body: InventoryMovementInput):
    """Registra un movimiento de inventario (entrada/salida/ajuste)
    y actualiza el stock automáticamente."""
    try:
        from fin_sys_core.inventory_driver import register_movement
        return register_movement(body.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/inventory/movements")
def inventory_list_movements(
    item_id: Optional[int] = None,
    portfolio: Optional[str] = None,
    limit: int = 50
):
    """Retorna los movimientos de inventario filtrados."""
    try:
        from fin_sys_core.inventory_driver import get_movements
        return get_movements(item_id, portfolio, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/inventory/summary")
def inventory_stock_summary(portfolio: str = "Principal"):
    """Retorna resumen de inventario: totales, valor, alertas de stock bajo."""
    try:
        from fin_sys_core.inventory_driver import get_stock_summary
        return get_stock_summary(portfolio)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
