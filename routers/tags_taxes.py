# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Tags & Impuestos Personalizados
Extracted from contabilidad.py — PURE refactor, zero logic changes.

1-oct-2026: PUT/DELETE de etiquetas y de plantillas de impuesto. Hasta ese día
el ✎/🗑 del panel llamaba a rutas inexistentes (405) y el error se tragaba.
La lógica de etiquetas vive en fin_sys_core/etiquetas.py (renombrar no toca
las transacciones; borrar en uso exige ?forzar=1 — segunda confirmación en la
web). Las plantillas de impuesto no tienen historia: usan el driver directo."""
from fastapi import APIRouter, Depends, HTTPException, Query

from routers.auth_guard import require_admin

router = APIRouter(tags=["Tags & Impuestos"])

TIPOS_IMPUESTO = ("ADDITIVE", "DEDUCTIVE")
_HTTP_ETIQUETAS = {"no_existe": 404, "nombre_duplicado": 409, "en_uso": 409,
                   "invalido": 422, "sin_cambios": 400}


def _con_transaccion(fn):
    """Ejecuta fn(cur) en una conexión del pool: commit si termina, rollback si
    lanza o si devuelve un resultado con ok=False (mapeado a HTTPException)."""
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        r = fn(cur)
        if not r["ok"]:
            raise HTTPException(status_code=_HTTP_ETIQUETAS.get(r["codigo"], 409), detail=r["error"])
        conn.commit()
        cur.close()
        return r
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn is not None:
            try:
                conn.rollback()      # sin commit (4xx/500) suelta el FOR UPDATE
            except Exception:
                pass
            try:
                release_db_connection(conn)
            except Exception:
                pass


# ==============================================================================
# 🏷️ Tags & Impuestos Personalizados
# ==============================================================================

@router.get("/api/tags")
def list_tags():
    try:
        from fin_sys_core.database_driver import listar_tags
        return listar_tags()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/tags", status_code=201)
def create_tag(body: dict, _admin: dict = Depends(require_admin)):
    try:
        from fin_sys_core.database_driver import crear_tag
        return crear_tag(body.get("name", ""), body.get("color", "#000000"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/tags/{tag_id}")
def update_tag(tag_id: int, body: dict, _admin: dict = Depends(require_admin)):
    """Nombre y/o color de la etiqueta. Solo la definición: las transacciones
    que ya la llevan conservan el nombre anterior (decisión de Andrés).
    404 no existe · 409 ya hay otra con ese nombre · 422 inválido · 400 nada que editar."""
    from fin_sys_core.etiquetas import actualizar
    body = body or {}
    r = _con_transaccion(lambda cur: actualizar(cur, tag_id, name=body.get("name"), color=body.get("color")))
    return {"status": "OK", "tag": r["tag"]}


@router.delete("/api/tags/{tag_id}")
def delete_tag(tag_id: int, forzar: bool = Query(False), _admin: dict = Depends(require_admin)):
    """Borra la etiqueta. Si está en transacciones o en borradores abiertos del
    bot → 409 con el conteo; con ?forzar=1 (segunda confirmación de la web) se
    quita de ahí y se borra. 404 no existe."""
    from fin_sys_core.etiquetas import eliminar
    r = _con_transaccion(lambda cur: eliminar(cur, tag_id, forzar=forzar))
    if r["transacciones_actualizadas"] or r["borradores_actualizados"]:
        print(f"🏷️ [TAGS] «{r['name']}» (#{tag_id}) borrada y quitada de "
              f"{r['transacciones_actualizadas']} transacciones y {r['borradores_actualizados']} "
              f"borradores por {_admin.get('name') or _admin.get('uid')}")
    return {"status": "ELIMINADO", "id": tag_id, "name": r["name"],
            "transacciones_actualizadas": r["transacciones_actualizadas"],
            "borradores_actualizados": r["borradores_actualizados"]}


@router.get("/api/custom-taxes")
def list_custom_taxes():
    try:
        from fin_sys_core.database_driver import listar_custom_taxes
        return listar_custom_taxes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/custom-taxes", status_code=201)
def create_custom_tax(body: dict, _admin: dict = Depends(require_admin)):
    try:
        from fin_sys_core.database_driver import crear_custom_tax
        return crear_custom_tax(body.get("name", ""), float(body.get("rate", 0)), body.get("tax_type", "ADDITIVE"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _validar_impuesto(body: dict) -> dict:
    """Campos presentes del body → kwargs de actualizar_custom_tax. 422 si alguno es inválido."""
    cambios = {}
    if "name" in body:
        nombre = str(body.get("name") or "").strip()
        if not nombre:
            raise HTTPException(status_code=422, detail="El nombre de la tasa no puede estar vacío.")
        cambios["name"] = nombre
    if "rate" in body:
        try:
            tasa = float(body.get("rate"))
        except (TypeError, ValueError):
            tasa = float("nan")
        if tasa != tasa or tasa < 0 or tasa == float("inf"):
            raise HTTPException(status_code=422, detail="La tasa debe ser un número mayor o igual a 0.")
        cambios["rate"] = tasa
    # La web manda `type`; el POST histórico lee `tax_type`: aquí valen los dos.
    tipo = body.get("type", body.get("tax_type"))
    if tipo is not None:
        tipo = str(tipo).strip().upper()
        if tipo not in TIPOS_IMPUESTO:
            raise HTTPException(status_code=422, detail=f"Tipo inválido. Válidos: {', '.join(TIPOS_IMPUESTO)}.")
        cambios["tax_type"] = tipo
    if not cambios:
        raise HTTPException(status_code=400, detail="Nada que editar.")
    return cambios


@router.put("/api/custom-taxes/{tax_id}")
def update_custom_tax(tax_id: int, body: dict, _admin: dict = Depends(require_admin)):
    """Edita una plantilla de impuesto (nombre, tasa, tipo). Sin historia que
    cuidar: la plantilla solo precarga el formulario. 404 si no existe."""
    cambios = _validar_impuesto(body or {})
    from fin_sys_core.database_driver import actualizar_custom_tax
    try:
        actualizado = actualizar_custom_tax(tax_id, **cambios)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not actualizado:
        raise HTTPException(status_code=404, detail="Esa tasa no existe.")
    return {"status": "OK", "id": tax_id, **cambios}


@router.delete("/api/custom-taxes/{tax_id}")
def delete_custom_tax(tax_id: int, _admin: dict = Depends(require_admin)):
    """Borra una plantilla de impuesto. 404 si no existe."""
    from fin_sys_core.database_driver import eliminar_custom_tax
    try:
        eliminado = eliminar_custom_tax(tax_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not eliminado:
        raise HTTPException(status_code=404, detail="Esa tasa no existe.")
    return {"status": "ELIMINADO", "id": tax_id}
