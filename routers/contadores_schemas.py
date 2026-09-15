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


class PeriodoInput(BaseModel):
    portfolio_id: int
    anio: int = Field(ge=1990, le=2100)
    mes: int = Field(ge=1, le=12)
    nota: Optional[str] = None
    motivo: Optional[str] = None
