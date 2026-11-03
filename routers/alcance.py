# -*- coding: utf-8 -*-
"""alcance.py — Qué empresas ve cada usuario (estándar de consultas, H9.1).

    GET  /api/alcance/yo                    mis empresas (la web decide qué mostrar)
    GET  /api/alcance/usuarios              usuarios y sus empresas (solo el dueño)
    PUT  /api/alcance/usuarios/{user_id}    reemplaza sus empresas (solo el dueño)

El dueño y el superusuario ven todas sin asignar nada. La regla en sí vive en
shared/alcance.py; la tabla la crea scripts/migrate_h9_alcance.py (Andrés).
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from psycopg2 import errors as pg_errors
from pydantic import BaseModel

from routers.auth_guard import require_auth
from shared import alcance

router = APIRouter(tags=["Alcance por empresa"])

SIN_TABLA = "Falta crear la tabla de empresas por usuario: corre scripts/migrate_h9_alcance.py."


class EmpresasIn(BaseModel):
    portfolio_ids: List[int]


@router.get("/api/alcance/yo")
def mis_empresas(user: dict = Depends(require_auth)):
    nombres = alcance.portafolios()
    permitidas = alcance.empresas_permitidas(user)
    ids = sorted(nombres) if permitidas is None else sorted(i for i in permitidas if i in nombres)
    return {"todas": permitidas is None, "empresas": [{"id": i, "name": nombres[i]} for i in ids]}


@router.get("/api/alcance/usuarios")
def usuarios_y_empresas(user: dict = Depends(require_auth)):
    alcance.solo_dueno(user)
    from fin_sys_core.db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id::text, name, email, role, coalesce(is_superuser, false) FROM hub_users ORDER BY name")
        usuarios = [{"id": i, "name": n, "email": e, "role": r, "todas": bool(su) or r == "owner",
                     "portfolio_ids": []} for i, n, e, r, su in cur.fetchall()]
        try:
            cur.execute("SELECT hub_user_id::text, portfolio_id FROM usuario_empresas ORDER BY portfolio_id")
        except pg_errors.UndefinedTable:
            raise HTTPException(status_code=409, detail=SIN_TABLA)
        por_usuario = {}
        for uid, pid in cur.fetchall():
            por_usuario.setdefault(uid, []).append(int(pid))
        for u in usuarios:
            u["portfolio_ids"] = por_usuario.get(u["id"], [])
        return usuarios
    finally:
        conn.rollback()
        put_conn(conn)


@router.put("/api/alcance/usuarios/{user_id}")
def asignar_empresas(user_id: str, body: EmpresasIn, user: dict = Depends(require_auth)):
    alcance.solo_dueno(user)
    try:
        uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Ese usuario no existe.")
    ids = sorted(alcance.ids_validos(body.portfolio_ids))
    faltan = sorted(set(body.portfolio_ids) - set(ids))
    if faltan:
        raise HTTPException(status_code=422, detail=f"Empresas que no existen: {', '.join(map(str, faltan))}.")
    from fin_sys_core.db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM hub_users WHERE id = %s", (user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Ese usuario no existe.")
        try:
            cur.execute("DELETE FROM usuario_empresas WHERE hub_user_id = %s", (user_id,))
        except pg_errors.UndefinedTable:
            raise HTTPException(status_code=409, detail=SIN_TABLA)
        if ids:
            cur.execute("INSERT INTO usuario_empresas (hub_user_id, portfolio_id) SELECT %s, unnest(%s::bigint[])",
                        (user_id, ids))
        conn.commit()
    finally:
        conn.rollback()
        put_conn(conn)
    alcance.limpiar_cache(user_id)
    return {"user_id": user_id, "portfolio_ids": ids}
