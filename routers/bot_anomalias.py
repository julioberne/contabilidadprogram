# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: bitácora de anomalías del bot (📓 Bot IA → Bitácora).

  GET /api/bot/anomalias?dias=30&tipo=&estado=abiertas|todas  ← lista + resumen (sesión)
  PUT /api/bot/anomalias/{id}  {revisada, nota?}               ← marcar revisada (admin)

Registro literal de lo que el bot no pudo resolver (fin_sys_core/bot_anomalias.py).
Router nuevo (Zero-Impact). Si la tabla aún no existe (antes del primer
arranque con este código), responde vacío con `disponible: false`.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from routers.auth_guard import require_admin, require_auth

router = APIRouter(tags=["Bot IA · Bitácora"])


class MarcaInput(BaseModel):
    revisada: bool = True
    nota: Optional[str] = None


def _uid(user: dict) -> str:
    uid = (user.get("uid") or "").strip()
    if not uid:
        raise HTTPException(status_code=401, detail="Sesión sin uid válido.")
    return uid


@router.get("/api/bot/anomalias")
def listar_anomalias(dias: int = 30, tipo: str = "", estado: str = "abiertas",
                     user: dict = Depends(require_auth)):
    if estado not in ("abiertas", "todas"):
        raise HTTPException(status_code=422, detail="estado: abiertas | todas")
    from bot_anomalias import DIAS_RETENCION, TIPOS, listar, resumen
    dias = max(1, min(int(dias), DIAS_RETENCION))
    if tipo and tipo not in TIPOS:
        raise HTTPException(status_code=422, detail="tipo desconocido")
    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        try:
            items = listar(cur, dias=dias, tipo=tipo or None, solo_abiertas=(estado == "abiertas"),
                           hub_user_id=_uid(user))
            cuenta = resumen(cur, dias=dias, hub_user_id=_uid(user))
            disponible = True
        except HTTPException:
            raise
        except Exception:
            conn.rollback()             # la tabla aún no existe: nada que mostrar
            items, cuenta, disponible = [], {}, False
        cur.close()
    finally:
        put_conn(conn)
    return {"disponible": disponible, "dias": dias, "tipos": TIPOS, "resumen": cuenta, "items": items}


@router.put("/api/bot/anomalias/{anomalia_id}")
def marcar_anomalia(anomalia_id: int, body: MarcaInput, _admin: dict = Depends(require_admin)):
    from bot_anomalias import marcar
    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        fila = marcar(cur, anomalia_id, revisada=body.revisada, nota=body.nota)
        if not fila:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Esa anomalía no existe.")
        conn.commit()
        cur.close()
        return fila
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        put_conn(conn)
