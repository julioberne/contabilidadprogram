# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: estado de los trabajos en segundo plano (H5).

GET /api/operaciones/{id} → estado, resultado o error de un trabajo que la
API encoló (respuesta 202 de, p. ej., POST /api/analytics/export). Solo lo
ve quien lo pidió, o un admin. Solo lectura.
"""
from fastapi import APIRouter, Depends, HTTPException

from routers.auth_guard import require_auth

router = APIRouter(tags=["Operaciones"])


def _es_admin(user: dict) -> bool:
    return bool(user.get("su")) or user.get("role") in ("owner", "admin")


@router.get("/api/operaciones/{op_id}")
def ver_operacion(op_id: int, user: dict = Depends(require_auth)):
    from fin_sys_core.cola import ColaNoDisponible, estado
    try:
        op = estado(op_id)
    except ColaNoDisponible as e:
        raise HTTPException(status_code=503, detail=str(e))
    # 404 también si es de otro usuario: no se revela que existe.
    if not op or (str(op.get("usuario") or "") != str(user.get("uid") or "") and not _es_admin(user)):
        raise HTTPException(status_code=404, detail="Esa operación no existe.")
    terminada = op["estado"] in ("HECHA", "FALLIDA")
    return {
        "id": op["id"], "tipo": op["tipo"], "estado": op["estado"], "terminada": terminada,
        "resultado": op.get("resultado") if op["estado"] == "HECHA" else None,
        "error": op.get("error") if op["estado"] in ("FALLIDA", "PENDIENTE") else None,
        "intentos": op["intentos"], "creada": op["creada"], "iniciada": op["iniciada"],
        "terminada_en": op["terminada"],
    }
