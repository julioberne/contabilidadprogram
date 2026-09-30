# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: medios de pago de un tercero (Bot IA, etapa 09.G §10).

Archivo NUEVO (Zero-Impact). Registrado en server.py ANTES del catch-all SPA.

  GET    /api/third-parties/{tp_id}/accounts             ← lista (sesión)
  POST   /api/third-parties/{tp_id}/accounts             ← agrega (admin) · 409 si ya es de otro tercero
  POST   /api/third-parties/{tp_id}/accounts/mover       ← trae a esta ficha un medio que hoy es de otro (admin)
  DELETE /api/third-parties/{tp_id}/accounts/{medio_id}  ← quita (admin)

"Medio de pago" = cuenta, celular, llave o nombre con que el banco llama al
tercero en sus SMS. Es el dato estructurado que usa el bot para traer el
tercero ya puesto (Regla 6b: lo registra una persona — aquí o con el botón 💾
del bot —, nunca se memoriza solo). Toda la lógica vive en
fin_sys_core/terceros_cuentas.py; este archivo solo enruta.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from routers.auth_guard import require_admin, require_auth

router = APIRouter(tags=["Terceros · Medios de pago"])

_HTTP_POR_CODIGO = {"de_otro": 409, "tercero_no_existe": 404}


class MedioInput(BaseModel):
    tipo: str                       # celular | cuenta | llave | nombre_banco
    valor: str
    banco: Optional[str] = None
    etiqueta: Optional[str] = None


class MoverInput(BaseModel):
    tipo: str
    valor: str


def _con_cursor(fn):
    """Ejecuta fn(cur) en una conexión del pool: commit si termina, rollback si lanza."""
    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        resultado = fn(cur)
        conn.commit()
        cur.close()
        return resultado
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        put_conn(conn)


@router.get("/api/third-parties/{tp_id}/accounts")
def listar_medios(tp_id: int, _u: dict = Depends(require_auth)):
    from terceros_cuentas import listar
    return _con_cursor(lambda cur: listar(cur, tp_id))


@router.post("/api/third-parties/{tp_id}/accounts", status_code=201)
def agregar_medio(tp_id: int, body: MedioInput, _admin: dict = Depends(require_admin)):
    from terceros_cuentas import agregar

    def _hacer(cur):
        r = agregar(cur, tp_id, body.tipo, body.valor, banco=body.banco,
                    etiqueta=body.etiqueta, origen="web")
        if not r["ok"]:
            raise HTTPException(status_code=_HTTP_POR_CODIGO.get(r.get("codigo"), 422),
                                detail=r["error"])
        return {"status": "YA_EXISTIA" if r.get("ya_existia") else "CREADO", "medio": r["medio"]}
    return _con_cursor(_hacer)


@router.post("/api/third-parties/{tp_id}/accounts/mover")
def mover_medio(tp_id: int, body: MoverInput, _admin: dict = Depends(require_admin)):
    """Decisión explícita: este medio deja la ficha donde estaba y pasa a esta."""
    from terceros_cuentas import listar, mover, normalizar

    def _hacer(cur):
        cur.execute("SELECT identification_number FROM third_parties WHERE id = %s", (tp_id,))
        fila = cur.fetchone()
        if not fila:
            raise HTTPException(status_code=404, detail="Ese tercero no existe.")
        if str(fila[0]) == "999999999":
            raise HTTPException(status_code=422, detail="El tercero genérico no puede tener medios de pago.")
        if not normalizar(body.tipo, body.valor):
            raise HTTPException(status_code=422, detail="Tipo o valor inválido.")
        if not mover(cur, body.tipo, body.valor, tp_id, origen="web"):
            raise HTTPException(status_code=404, detail="Ese medio de pago no está registrado.")
        return {"status": "MOVIDO", "medios": listar(cur, tp_id)}
    return _con_cursor(_hacer)


@router.delete("/api/third-parties/{tp_id}/accounts/{medio_id}")
def eliminar_medio(tp_id: int, medio_id: int, _admin: dict = Depends(require_admin)):
    from terceros_cuentas import eliminar

    def _hacer(cur):
        if not eliminar(cur, medio_id, tp_id):
            raise HTTPException(status_code=404, detail="Medio de pago no encontrado en esta ficha.")
        return {"status": "ELIMINADO", "id": medio_id}
    return _con_cursor(_hacer)
