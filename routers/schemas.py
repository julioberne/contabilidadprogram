# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Schemas: Pydantic models for Contabilidad routers.
Extracted from contabilidad.py — PURE refactor, zero logic changes."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ==============================================================================
# 📋 Esquemas de Validación de Datos (Pydantic Models)
# ==============================================================================

class PortfolioInput(BaseModel):
    name: str
    industry_type: str = "ESTANDAR"
    sub_industry_type: str = ""

class ThirdPartyInput(BaseModel):
    identification_type: str = Field(..., pattern="^(NIT|CC)$")
    identification_number: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None


class ProfileInput(BaseModel):
    name: str
    email: str
    role: str
    avatar_style: str


class AccountInput(BaseModel):
    name: str
    type: str
    currency: str = "COP"
    initial_balance: float = 0.0


class CxcCxpInput(BaseModel):
    type: str = Field(..., pattern="^(CXC|CXP)$")
    due_date: str
    term: str = Field("Corto", pattern="^(Corto|Mediano|Largo)$")


class AssetInput(BaseModel):
    name: str
    purchase_value: float
    custom_tag: Optional[str] = None
    establish_as_asset: bool = False
    is_passive_income_generator: bool = False
    recurrence_interval_days: Optional[int] = 30
    recurrence_amount: Optional[float] = 0.0


class TransactionInput(BaseModel):
    portfolio_name: str
    type: str = Field(..., pattern="^(INGRESO|GASTO|TRANSFERENCIA)$")
    amount: float = Field(..., gt=0.0)
    concept: str
    payment_method: str
    category: str
    third_party: ThirdPartyInput
    transaction_date: str
    apply_iva: bool = False
    apply_gmf: bool = False
    custom_taxes: Optional[List[Dict[str, Any]]] = None
    
    # Georreferenciación opcional
    geo_latitude: Optional[float] = None
    geo_longitude: Optional[float] = None
    geo_maps_link: Optional[str] = None
    
    # Módulo de Cuentas
    account_id: Optional[int] = None
    dest_account_id: Optional[int] = None
    trm: Optional[float] = 1.0
    transaction_currency: Optional[str] = "COP"
    
    # [NEW] Campos por cobrar/pagar y activos
    cxc_cxp: Optional[CxcCxpInput] = None
    asset: Optional[AssetInput] = None
    evidence_file_path: Optional[str] = None
    is_recurring: Optional[bool] = False
    recurrence_interval: Optional[str] = "MENSUAL"
    recurrence_days: Optional[int] = 30
    recurrence_max_reps: Optional[int] = None
    recurrence_start_date: Optional[str] = None
    recurrence_end_date: Optional[str] = None


class StructureRequest(BaseModel):
    transcript: str
    portfolio_name: str = "Negocio A"


class TransactionUpdateInput(BaseModel):
    type: Optional[str] = None
    amount: Optional[float] = None
    concept: Optional[str] = None
    transaction_date: Optional[str] = None
    payment_method: Optional[str] = None
    category: Optional[str] = None
    net_value: Optional[float] = None
    third_party_name: Optional[str] = None
    identification_number: Optional[str] = None
    
    # Módulo de Cuentas
    account_id: Optional[int] = None
    dest_account_id: Optional[int] = None
    trm: Optional[float] = None
    transaction_currency: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_interval: Optional[str] = None
    recurrence_days: Optional[int] = None
    recurrence_max_reps: Optional[int] = None
    recurrence_start_date: Optional[str] = None
    recurrence_end_date: Optional[str] = None


class CoaTemplateInput(BaseModel):
    portfolio_name: str
    template_name: str


class CoaAccountInput(BaseModel):
    portfolio_name: str
    code: str
    name: str
    type: str
    is_group: bool
    parent_code: Optional[str] = None


# ==============================================================================
# 🔧 Helpers compartidos
# ==============================================================================

def _build_coa_tree(flat_rows):
    """Construye árbol COA a partir de filas planas."""
    by_id = {r["id"]: {**r, "children": []} for r in flat_rows}
    tree = []
    for r in flat_rows:
        node = by_id[r["id"]]
        if r.get("parent_id") and r["parent_id"] in by_id:
            by_id[r["parent_id"]]["children"].append(node)
        else:
            tree.append(node)
    return tree
