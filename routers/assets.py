# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Recursos/Activos (assets).

Historia: la pestaña RECURSOS llamaba GET/PUT/DELETE /api/assets desde su
nacimiento, pero el endpoint NUNCA existió — el catch-all del SPA devolvía
index.html, el catch del frontend lo tragaba y el panel decía "SIN RECURSOS"
para siempre (bug encontrado 2026-09-06). Este router lo hace real, con el
recurso vinculado a la EMPRESA activa (entities) — pedido de Andrés: "cuando
establezco un recurso tiene que ir vinculado a la entidad donde trabajo".

Los assets nacidos del registro contable (establish_as_asset) traen
portfolio_id y entity_id NULL: se muestran como legado del portafolio.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from routers.auth_guard import require_admin

router = APIRouter(tags=["Recursos"])


def _conn():
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    return get_db_connection, release_db_connection


@router.get("/api/assets")
def list_assets(entity_id: Optional[int] = None, portfolio: Optional[str] = None):
    """Con entity_id: los recursos de esa empresa + los legado del portafolio
    (entity NULL). Solo portfolio: por portafolio. Sin filtros: todos."""
    get_db, release_db = _conn()
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        base = """
            SELECT a.id, a.name, a.purchase_value, a.purchase_date, a.custom_tag,
                   a.is_passive_income_generator, a.entity_id, e.name AS entity_name,
                   a.portfolio_id, p.name AS portfolio_name
            FROM assets a
            LEFT JOIN entities e ON e.id = a.entity_id
            LEFT JOIN portfolios p ON p.id = a.portfolio_id
        """
        if entity_id is not None:
            cur.execute(base + """
                WHERE a.entity_id = %s
                   OR (a.entity_id IS NULL AND p.name = %s)
                ORDER BY a.id DESC;
            """, (entity_id, portfolio or ""))
        elif portfolio:
            cur.execute(base + " WHERE p.name = %s ORDER BY a.id DESC;", (portfolio,))
        else:
            cur.execute(base + " ORDER BY a.id DESC;")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        for r in rows:
            if r.get("purchase_value") is not None:
                r["purchase_value"] = float(r["purchase_value"])
            if r.get("purchase_date"):
                r["purchase_date"] = str(r["purchase_date"])
        cur.close()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn is not None:
            try: release_db(conn)
            except Exception: pass


@router.post("/api/assets", status_code=201)
def create_asset(body: dict, _admin: dict = Depends(require_admin)):
    """Crea un recurso directo, vinculado a la empresa activa (entity_id)."""
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    get_db, release_db = _conn()
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        portfolio_id = None
        if body.get("portfolio"):
            cur.execute("SELECT id FROM portfolios WHERE name = %s", (body["portfolio"],))
            row = cur.fetchone()
            portfolio_id = row[0] if row else None
        cur.execute("""
            INSERT INTO assets (name, purchase_value, purchase_date, custom_tag,
                                is_passive_income_generator, entity_id, portfolio_id)
            VALUES (%s, %s, CURRENT_DATE, %s, %s, %s, %s) RETURNING id;
        """, (name, float(body.get("purchase_value") or 0),
              (body.get("custom_tag") or "").strip() or None,
              bool(body.get("is_passive_income_generator")),
              body.get("entity_id"), portfolio_id))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return {"status": "CREADO", "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn is not None:
            try: release_db(conn)
            except Exception: pass


@router.put("/api/assets/{asset_id}")
def update_asset(asset_id: int, body: dict, _admin: dict = Depends(require_admin)):
    CAMPOS = {"name": str, "purchase_value": float, "custom_tag": str,
              "entity_id": int, "is_passive_income_generator": bool}
    sets, params = [], []
    for k, cast in CAMPOS.items():
        if k in body and body[k] is not None:
            sets.append(f"{k} = %s")
            params.append(cast(body[k]) if body[k] != "" else None)
    if not sets:
        raise HTTPException(status_code=400, detail="Nada que editar.")
    get_db, release_db = _conn()
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        params.append(asset_id)
        cur.execute(f"UPDATE assets SET {', '.join(sets)} WHERE id = %s RETURNING id;", params)
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Recurso no encontrado")
        conn.commit()
        cur.close()
        return {"status": "ACTUALIZADO"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn is not None:
            try: release_db(conn)
            except Exception: pass


@router.delete("/api/assets/{asset_id}")
def delete_asset(asset_id: int, _admin: dict = Depends(require_admin)):
    get_db, release_db = _conn()
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM assets WHERE id = %s RETURNING id;", (asset_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Recurso no encontrado")
        conn.commit()
        cur.close()
        return {"status": "ELIMINADO"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn is not None:
            try: release_db(conn)
            except Exception: pass
