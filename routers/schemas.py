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
    # 2026-09-08 (bot Etapa E.3): el usuario dicta la dirección por voz y la
    # columna third_parties.address ya existía (migración cartera) — solo
    # faltaba el campo en el contrato.
    address: Optional[str] = None


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
    # Nombre del portafolio dueño de la cuenta. None = compartida (global).
    portfolio: Optional[str] = None
    # EMPRESA del árbol a la que nace vinculada (account_entity_links). Tiene
    # prioridad sobre portfolio: la mayoría de empresas no tienen portafolio
    # propio y la resolución por nombre dejaba la cuenta compartida.
    entity_id: Optional[int] = None
    # Etapa 09.F (cuentas POR ID): últimos 4 dígitos del número de cuenta y de
    # la tarjeta asociada. Es lo que cruza el bot con los SMS del banco; el
    # nombre de la cuenta queda libre. None = sin dato.
    last4_cuenta: Optional[str] = None
    last4_tarjeta: Optional[str] = None


class AccountUpdateInput(BaseModel):
    name: str
    type: str
    # None = no tocar el saldo (lo mantiene el motor incremental)
    current_balance: Optional[float] = None
    # None = no tocar el saldo inicial (editable desde 💳 Cuentas)
    initial_balance: Optional[float] = None
    # None = no tocar; "" = volver COMPARTIDA; nombre = asignar a ese portafolio
    portfolio_name: Optional[str] = None
    # None = no tocar; "" = borrar; "3037" = fijar (etapa 09.F)
    last4_cuenta: Optional[str] = None
    last4_tarjeta: Optional[str] = None


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
    # Etiquetas libres (2026-09-08): el form y la bandeja del bot ya las
    # enviaban — sin este campo pydantic las descartaba en silencio.
    tags: Optional[List[str]] = None
    # Múltiples evidencias (Etapa E.3): lista completa de URLs/rutas.
    # evidence_file_path (singular) sigue siendo la principal, por compat.
    evidence_files: Optional[List[str]] = None


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
    # Edición desde el comprobante (2026-09-09): revincular la TX a un
    # tercero YA registrado, completar la geolocalización faltante y
    # modificar las etiquetas.
    third_party_id: Optional[int] = None
    geo_maps_link: Optional[str] = None
    tags: Optional[List[str]] = None
    # Nota breve del comprobante (opcional, solo texto)
    note: Optional[str] = Field(None, max_length=280)
    
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


class TransactionDeleteInput(BaseModel):
    """Eliminar exige la clave del administrador en CADA intento (2026-09-11)."""
    password: str = Field(min_length=1)


class EvidenceAttachInput(BaseModel):
    """Adjuntar evidencias (URLs del bucket) a una TX ya registrada."""
    files: List[str] = Field(min_length=1)


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
