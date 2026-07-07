"""
routers/module_flags.py — Feature Flags CRUD.
Permite activar/desactivar módulos por empresa y/o rol.

Endpoints:
  GET  /api/module-flags          → flags filtrados para el usuario actual
  GET  /api/module-flags/admin    → todos los flags (panel admin)
  PUT  /api/module-flags          → crear/actualizar un flag
  DELETE /api/module-flags/{id}   → eliminar un flag específico
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["Module Flags"])

# ── Helpers ──────────────────────────────────────────────────

def _get_conn():
    from database_driver import get_db_connection
    return get_db_connection()

# ── Modelos ──────────────────────────────────────────────────

class ModuleFlagUpdate(BaseModel):
    module_id: str
    enabled: bool
    company_id: Optional[int] = None
    role_filter: Optional[str] = None

# ── GET /api/module-flags ────────────────────────────────────
# Devuelve los flags resueltos para una empresa/rol específicos.
# Prioridad: company+role > company > role > global

@router.get("/api/module-flags")
async def get_module_flags(company_id: Optional[int] = None, role: Optional[str] = None):
    conn = _get_conn()
    if not conn:
        return {"flags": [], "source": "unavailable"}
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, module_id, enabled, company_id, role_filter FROM module_flags ORDER BY module_id")
        rows = cur.fetchall()
        cur.close()

        all_flags = [
            {"id": r[0], "module_id": r[1], "enabled": r[2], "company_id": r[3], "role_filter": r[4]}
            for r in rows
        ]

        # Resolver flags por prioridad
        resolved = {}
        for f in all_flags:
            mid = f["module_id"]
            priority = 0

            # Calcular prioridad del flag
            if f["company_id"] is None and f["role_filter"] is None:
                priority = 1  # Global
            elif f["company_id"] is None and f["role_filter"] == role:
                priority = 2  # Por rol
            elif f["company_id"] == company_id and f["role_filter"] is None:
                priority = 3  # Por empresa
            elif f["company_id"] == company_id and f["role_filter"] == role:
                priority = 4  # Más específico
            else:
                continue  # No aplica a este usuario

            if mid not in resolved or priority > resolved[mid]["_priority"]:
                resolved[mid] = {**f, "_priority": priority}

        # Limpiar campo interno
        result = []
        for mid, f in resolved.items():
            del f["_priority"]
            result.append(f)

        return {"flags": result, "company_id": company_id, "role": role}
    except Exception as e:
        return {"flags": [], "error": str(e)}

# ── GET /api/module-flags/admin ──────────────────────────────
# Devuelve TODOS los flags sin filtrar (para panel admin)

@router.get("/api/module-flags/admin")
async def get_all_module_flags():
    conn = _get_conn()
    if not conn:
        return {"flags": []}
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT mf.id, mf.module_id, mf.enabled, mf.company_id, mf.role_filter,
                   mf.updated_at, mf.updated_by, e.name as company_name
            FROM module_flags mf
            LEFT JOIN entities e ON e.id = mf.company_id
            ORDER BY mf.module_id, mf.company_id NULLS FIRST, mf.role_filter NULLS FIRST
        """)
        rows = cur.fetchall()
        cur.close()
        return {"flags": [
            {
                "id": r[0], "module_id": r[1], "enabled": r[2],
                "company_id": r[3], "role_filter": r[4],
                "updated_at": str(r[5]) if r[5] else None,
                "updated_by": r[6],
                "company_name": r[7]
            }
            for r in rows
        ]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── PUT /api/module-flags ────────────────────────────────────
# Crea o actualiza un flag (upsert)

@router.put("/api/module-flags")
async def upsert_module_flag(flag: ModuleFlagUpdate):
    conn = _get_conn()
    if not conn:
        raise HTTPException(status_code=503, detail="BD no disponible")
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO module_flags (module_id, enabled, company_id, role_filter, updated_at, updated_by)
            VALUES (%s, %s, %s, %s, now(), 'admin')
            ON CONFLICT (module_id, company_id, role_filter)
            DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = now(), updated_by = 'admin'
            RETURNING id
        """, (flag.module_id, flag.enabled, flag.company_id, flag.role_filter))
        result = cur.fetchone()
        conn.commit()
        cur.close()
        return {"status": "OK", "id": result[0], "module_id": flag.module_id, "enabled": flag.enabled}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ── DELETE /api/module-flags/{flag_id} ───────────────────────
# Elimina un flag específico (vuelve al default del registry)

@router.delete("/api/module-flags/{flag_id}")
async def delete_module_flag(flag_id: int):
    conn = _get_conn()
    if not conn:
        raise HTTPException(status_code=503, detail="BD no disponible")
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM module_flags WHERE id = %s RETURNING module_id", (flag_id,))
        result = cur.fetchone()
        conn.commit()
        cur.close()
        if not result:
            raise HTTPException(status_code=404, detail="Flag no encontrado")
        return {"status": "DELETED", "module_id": result[0]}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
