# -*- coding: utf-8 -*-
"""
routers/analytics.py — Análisis Inteligente (B0+B2+B3).
Archivo NUEVO (Zero-Impact). Registrado en server.py ANTES del catch-all SPA.

Endpoints (todos exigen Bearer — son datos de dinero):
  GET  /api/analytics/catalog  → catálogo whitelisted de métricas (para UI/depuración)
  POST /api/analytics/metric   → ejecuta UNA métrica del catálogo
  GET  /api/analytics/dataset  → tabla plana consolidada para Perspective (B2)
  POST /api/analytics/ask      → pregunta en español → texto + datos + gráfica (B3)

Criterios inmutables: ninguna cifra nace de la IA (solo del catálogo); la
empresa va amarrada por código (el LLM jamás la decide); toda respuesta
lleva sello de origen; errores honestos.
"""
import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from routers.auth_guard import require_auth

router = APIRouter(tags=["Analytics"])


# ── Modelos ──────────────────────────────────────────────────

class MetricRequest(BaseModel):
    metrica: str
    params: Optional[Dict[str, Any]] = None
    portfolio_id: Optional[int] = None   # lo elige el USUARIO en la UI, no el LLM


class AskRequest(BaseModel):
    pregunta: str
    portfolio_id: Optional[int] = None   # ídem: selector de la UI / sesión


# ── GET /api/analytics/catalog ───────────────────────────────

@router.get("/api/analytics/catalog")
def get_catalog(_user: dict = Depends(require_auth)):
    from metrics_catalog import catalogo_publico
    return {"metricas": catalogo_publico()}


# ── POST /api/analytics/metric ───────────────────────────────

@router.post("/api/analytics/metric")
def run_metric(req: MetricRequest, _user: dict = Depends(require_auth)):
    from metrics_catalog import ejecutar_metrica
    try:
        return ejecutar_metrica(req.metrica, req.params, portfolio_id=req.portfolio_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"La métrica falló: {e}")


# ── GET /api/analytics/dataset ───────────────────────────────
# Tabla plana consolidada multi-empresa para el visor Perspective (B2).
# Reusa obtener_transacciones(None) — la MISMA verdad que contabilidad.

_ESQUEMA_DATASET = {
    "empresa": "string", "portafolio": "string", "fecha": "date", "tipo": "string",
    "categoria": "string", "tercero": "string", "cuenta": "string", "metodo_pago": "string",
    "concepto": "string", "etiquetas": "string", "moneda": "string",
    "monto": "float", "neto": "float", "iva": "float", "gmf": "float",
}


def _nombres_de_empresa() -> Dict[str, str]:
    """portafolio contable → nombre de empresa del Control Tower.

    El caso real (18-sep): las TXs viven en el portafolio interno "Negocio A"
    (default histórico, no renombrable), pero Andrés lo conoce como
    "Finanzas Personales Julian". El módulo debe hablar SU idioma; el nombre
    interno queda visible en la columna `portafolio` (nada se esconde)."""
    conn = None
    try:
        from database_driver import get_db_connection, release_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT p.name, e.name
              FROM entities e
              JOIN portfolios p ON p.id = e.portfolio_id
             WHERE e.portfolio_id IS NOT NULL;
        """)
        alias = {r[0]: (r[1] or "").strip() for r in cur.fetchall() if (r[1] or "").strip()}
        cur.close()
        return alias
    except Exception:
        return {}   # sin vínculo CT no se cae el dataset: queda el nombre interno
    finally:
        if conn is not None:
            try:
                from database_driver import release_db_connection
                release_db_connection(conn)
            except Exception:
                pass


def _num(x) -> float:
    try:
        return float(x) if x is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _texto(x) -> str:
    if x is None:
        return ""
    if isinstance(x, (list, tuple)):
        return ", ".join(str(i) for i in x)
    return str(x)


@router.get("/api/analytics/dataset")
def get_dataset(_user: dict = Depends(require_auth)):
    from database_driver import obtener_transacciones
    try:
        txs = obtener_transacciones(None)   # consolidado multi-empresa (lista plana)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"No pude leer las transacciones: {e}")

    alias = _nombres_de_empresa()
    filas = []
    for t in txs:
        fecha = t.get("transaction_date")
        portafolio = _texto(t.get("portfolio_name")) or "(sin portafolio)"
        filas.append({
            "empresa": alias.get(portafolio, portafolio),
            "portafolio": portafolio,
            "fecha": fecha.isoformat() if hasattr(fecha, "isoformat") else _texto(fecha),
            "tipo": _texto(t.get("type")),
            "categoria": _texto(t.get("category")).strip() or "(sin categoría)",
            "tercero": _texto(t.get("third_party_name")) or "(sin tercero)",
            "cuenta": _texto(t.get("account_name")) or "(sin cuenta)",
            "metodo_pago": _texto(t.get("payment_method")),
            "concepto": _texto(t.get("concept")),
            "etiquetas": _texto(t.get("tags")),
            "moneda": _texto(t.get("transaction_currency")) or "COP",
            "monto": _num(t.get("amount")),
            "neto": _num(t.get("net_value")),
            "iva": _num(t.get("tax_iva_amount")),
            "gmf": _num(t.get("tax_gmf_amount")),
        })

    return {
        "esquema": _ESQUEMA_DATASET,
        "filas": filas,
        "n": len(filas),
        "generado": datetime.datetime.now().isoformat(timespec="seconds"),
    }


# ── GET /api/analytics/insights ──────────────────────────────
# Hito 2 (B1): tarjetas automáticas para el HomeDashboard. Las cifras salen
# SOLO del catálogo (insight_engine no calcula nada por su cuenta).

@router.get("/api/analytics/insights")
def get_insights(portfolio_id: Optional[int] = None, _user: dict = Depends(require_auth)):
    from insight_engine import generar_insights
    try:
        return generar_insights(portfolio_id=portfolio_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Los insights fallaron: {e}")


# ── GET /api/analytics/preguntas-log ─────────────────────────
# Bitácora de preguntas sin responder (retención 30 días): el insumo para
# decidir qué métricas nuevas amerita el catálogo.

@router.get("/api/analytics/preguntas-log")
def get_preguntas_log(_user: dict = Depends(require_auth)):
    from analytics_log import RETENCION_DIAS, preguntas_recientes
    try:
        return {"preguntas": preguntas_recientes(), "retencion_dias": RETENCION_DIAS}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No pude leer la bitácora: {e}")


# ── POST /api/analytics/ask ──────────────────────────────────

@router.post("/api/analytics/ask")
def ask(req: AskRequest, _user: dict = Depends(require_auth)):
    if not (req.pregunta or "").strip():
        raise HTTPException(status_code=400, detail="Escribe una pregunta.")
    from analytics_qa import responder_pregunta
    try:
        return responder_pregunta(req.pregunta.strip(), portfolio_id=req.portfolio_id)
    except Exception as e:
        # Error honesto (criterio 4): jamás una respuesta rellenada.
        raise HTTPException(status_code=502, detail=f"El traductor de preguntas falló: {e}")
