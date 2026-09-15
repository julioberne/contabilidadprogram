# -*- coding: utf-8 -*-
"""Esquemas Pydantic del módulo Contadores (B2)."""
from typing import List, Optional

from pydantic import BaseModel, Field


class LineaInput(BaseModel):
    cuenta_codigo: str = Field(min_length=1, max_length=50)
    cuenta_nombre: Optional[str] = ""
    debito: float = 0
    credito: float = 0


class LineasEditInput(BaseModel):
    lineas: List[LineaInput] = Field(min_length=2)
    fecha: Optional[str] = None
    descripcion: Optional[str] = None
    portfolio_id: Optional[int] = None


class MotivoInput(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)


class AnularInput(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)
    fecha: Optional[str] = None


class LoteInput(BaseModel):
    ids: List[str] = Field(min_length=1, max_length=200)
    accion: str = Field(pattern="^(contabilizar|rechazar)$")
    motivo: Optional[str] = None


class AsientoManualInput(BaseModel):
    portfolio_id: Optional[int] = None
    fecha: str = Field(min_length=10, max_length=10)
    descripcion: Optional[str] = ""
    lineas: List[LineaInput] = Field(min_length=2)
    contabilizar: bool = False


class CuentaInput(BaseModel):
    portfolio_id: int
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    account_type: str = Field(min_length=1, max_length=20)
    is_group: bool = False
    parent_code: Optional[str] = None
    description: Optional[str] = None


class CuentaUpdateInput(BaseModel):
    name: Optional[str] = None
    account_type: Optional[str] = None
    is_group: Optional[bool] = None
    parent_code: Optional[str] = None      # "" = sin padre
    description: Optional[str] = None


class CopiarCoaInput(BaseModel):
    from_portfolio_id: int
    to_portfolio_id: int


class ReglaInput(BaseModel):
    rule_name: Optional[str] = None
    category: str = Field(min_length=1, max_length=150)
    transaction_type: str = Field(min_length=1, max_length=15)
    debit_account_code: str = Field(min_length=1, max_length=50)
    credit_account_code: str = Field(min_length=1, max_length=50)
    description: Optional[str] = None
    portfolio_id: Optional[int] = None
    is_active: bool = True


class ReglaUpdateInput(BaseModel):
    rule_name: Optional[str] = None
    category: Optional[str] = None
    transaction_type: Optional[str] = None
    debit_account_code: Optional[str] = None
    credit_account_code: Optional[str] = None
    description: Optional[str] = None
    portfolio_id: Optional[int] = None
    is_active: Optional[bool] = None


class PeriodoInput(BaseModel):
    portfolio_id: int
    anio: int = Field(ge=1990, le=2100)
    mes: int = Field(ge=1, le=12)
    nota: Optional[str] = None
    motivo: Optional[str] = None
