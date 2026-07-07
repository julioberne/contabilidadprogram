# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Driver de Organizaciones (org_driver.py)
═══════════════════════════════════════════════════════════
Driver independiente de CRUD para la tabla `entities` de Supabase.
Usado por el selector de empresa del módulo Contabilidad.

NO importa de database_driver ni control_tower_driver — conexión
directa al pool centralizado de db_pool.py.
"""

import os
import sys
from typing import List, Dict, Any, Optional
from psycopg2.extras import RealDictCursor

# Conexión directa al pool centralizado (mismo patrón que database_driver.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_pool import get_conn, put_conn


# ═══════════════════════════════════════════════════════════
# MODO SIMULACIÓN — Datos en memoria si Postgres no responde
# ═══════════════════════════════════════════════════════════

MOCK_ENTITIES = [
    {
        "id": 1, "name": "Mi Holding Principal", "type": "HOLDING",
        "parent_id": None, "portfolio_id": None,
        "industry": "MULTI-SECTOR", "status": "AL DIA", "level": 0
    },
    {
        "id": 2, "name": "Jardín Infantil Pegasus", "type": "EMPRESA",
        "parent_id": 1, "portfolio_id": 2,
        "industry": "EDUCACION", "status": "AL DIA", "level": 1
    },
    {
        "id": 3, "name": "Consultora Digital SAS", "type": "EMPRESA",
        "parent_id": 1, "portfolio_id": 1,
        "industry": "SERVICIOS", "status": "ALERTA", "level": 1
    },
    {
        "id": 4, "name": "Proyecto E-Commerce", "type": "PROYECTO",
        "parent_id": 3, "portfolio_id": None,
        "industry": "COMERCIO", "status": "AL DIA", "level": 2
    },
]


# ═══════════════════════════════════════════════════════════
# UTILIDADES INTERNAS
# ═══════════════════════════════════════════════════════════

def _calcular_niveles(flat: List[Dict]) -> List[Dict]:
    """Asigna el campo `level` a cada entidad según su profundidad en el árbol.
    Nivel 0 = raíz (sin parent_id)."""
    lookup = {e["id"]: e for e in flat}
    for entity in flat:
        # Calcular profundidad recorriendo hacia la raíz
        nivel = 0
        pid = entity.get("parent_id")
        while pid and pid in lookup:
            nivel += 1
            pid = lookup[pid].get("parent_id")
        entity["level"] = nivel
    return flat


def _ordenar_jerarquico(flat: List[Dict]) -> List[Dict]:
    """Ordena la lista plana jerárquicamente: padres antes que hijos,
    y hermanos ordenados por nombre."""
    # Construir mapa de hijos
    hijos: Dict[Optional[int], List[Dict]] = {}
    for e in flat:
        pid = e.get("parent_id")
        if pid not in hijos:
            hijos[pid] = []
        hijos[pid].append(e)

    # Ordenar hermanos por nombre
    for key in hijos:
        hijos[key].sort(key=lambda x: x.get("name", ""))

    # Recorrido DFS pre-order
    resultado = []

    def _dfs(parent_id: Optional[int]):
        for child in hijos.get(parent_id, []):
            resultado.append(child)
            _dfs(child["id"])

    _dfs(None)
    return resultado


def _build_tree(flat: List[Dict]) -> List[Dict]:
    """Construye árbol anidado con campo `children[]` desde lista plana."""
    lookup = {e["id"]: {**e, "children": []} for e in flat}
    roots = []
    for item in lookup.values():
        pid = item.get("parent_id")
        if pid and pid in lookup:
            lookup[pid]["children"].append(item)
        else:
            roots.append(item)
    return roots


# ═══════════════════════════════════════════════════════════
# 1. SELECTOR DE EMPRESA — Lista plana ordenada jerárquicamente
# ═══════════════════════════════════════════════════════════

def get_entities_for_selector() -> List[Dict[str, Any]]:
    """Retorna todas las entidades formateadas para el dropdown del selector.
    Cada elemento: {id, name, type, parent_id, industry, portfolio_id, status, level}
    Ordenado jerárquicamente (padre antes que hijos)."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, name, type, parent_id, portfolio_id,
                   industry, status
            FROM entities
            ORDER BY parent_id NULLS FIRST, id ASC;
        """)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        put_conn(conn)

        # Calcular niveles y ordenar jerárquicamente
        rows = _calcular_niveles(rows)
        rows = _ordenar_jerarquico(rows)
        return rows
    except Exception as e:
        print(f"⚠️ [ORG_DRIVER] Fallback mock en get_entities_for_selector: {e}")
        return _ordenar_jerarquico(list(MOCK_ENTITIES))


# ═══════════════════════════════════════════════════════════
# 2. CREAR ENTIDAD BÁSICA
# ═══════════════════════════════════════════════════════════

def create_entity_basic(data: dict) -> Dict[str, Any]:
    """Crea una nueva entidad con campos: name, type, parent_id, industry, portfolio_id.
    Retorna la entidad creada con todos sus campos."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO entities (name, type, parent_id, industry, portfolio_id, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, type, parent_id, portfolio_id, industry, status, created_at;
        """, (
            data["name"],
            data.get("type", "EMPRESA"),
            data.get("parent_id"),
            data.get("industry", ""),
            data.get("portfolio_id"),
            "AL DIA"
        ))
        created = dict(cur.fetchone())
        conn.commit()
        cur.close()
        put_conn(conn)
        return created
    except Exception as e:
        print(f"⚠️ [ORG_DRIVER] Fallback mock en create_entity_basic: {e}")
        # Simulación en memoria
        new_id = max(e["id"] for e in MOCK_ENTITIES) + 1 if MOCK_ENTITIES else 1
        nueva = {
            "id": new_id,
            "name": data["name"],
            "type": data.get("type", "EMPRESA"),
            "parent_id": data.get("parent_id"),
            "portfolio_id": data.get("portfolio_id"),
            "industry": data.get("industry", ""),
            "status": "AL DIA",
            "level": 0
        }
        MOCK_ENTITIES.append(nueva)
        return nueva


# ═══════════════════════════════════════════════════════════
# 3. ACTUALIZAR ENTIDAD BÁSICA
# ═══════════════════════════════════════════════════════════

def update_entity_basic(entity_id: int, data: dict) -> Dict[str, Any]:
    """Actualiza name, type, industry, status, parent_id de una entidad.
    Retorna la entidad actualizada."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Construir SET dinámico solo con campos presentes
        campos_permitidos = ["name", "type", "industry", "status", "parent_id"]
        sets = []
        valores = []
        for campo in campos_permitidos:
            if campo in data:
                sets.append(f"{campo} = %s")
                valores.append(data[campo])

        if not sets:
            raise ValueError("No se proporcionaron campos para actualizar.")

        valores.append(entity_id)
        query = f"""
            UPDATE entities SET {', '.join(sets)}
            WHERE id = %s
            RETURNING id, name, type, parent_id, portfolio_id, industry, status;
        """
        cur.execute(query, valores)
        updated = cur.fetchone()
        if not updated:
            raise ValueError(f"Entidad con ID {entity_id} no encontrada.")
        updated = dict(updated)
        conn.commit()
        cur.close()
        put_conn(conn)
        return updated
    except Exception as e:
        print(f"⚠️ [ORG_DRIVER] Fallback mock en update_entity_basic: {e}")
        for ent in MOCK_ENTITIES:
            if ent["id"] == entity_id:
                for campo in ["name", "type", "industry", "status", "parent_id"]:
                    if campo in data:
                        ent[campo] = data[campo]
                return ent
        raise ValueError(f"Entidad con ID {entity_id} no encontrada en mock.")


# ═══════════════════════════════════════════════════════════
# 4. ACTUALIZAR INDUSTRIA DE ENTIDAD
# ═══════════════════════════════════════════════════════════

def update_entity_industry(entity_id: int, industry: str) -> Dict[str, Any]:
    """Actualiza SOLAMENTE el campo industry de una entidad.
    Retorna la entidad actualizada."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            UPDATE entities SET industry = %s
            WHERE id = %s
            RETURNING id, name, type, parent_id, portfolio_id, industry, status;
        """, (industry, entity_id))
        updated = cur.fetchone()
        if not updated:
            raise ValueError(f"Entidad con ID {entity_id} no encontrada.")
        updated = dict(updated)
        conn.commit()
        cur.close()
        put_conn(conn)
        return updated
    except Exception as e:
        print(f"⚠️ [ORG_DRIVER] Fallback mock en update_entity_industry: {e}")
        for ent in MOCK_ENTITIES:
            if ent["id"] == entity_id:
                ent["industry"] = industry
                return ent
        raise ValueError(f"Entidad con ID {entity_id} no encontrada en mock.")


# ═══════════════════════════════════════════════════════════
# 5. ÁRBOL COMPLETO DE ENTIDADES
# ═══════════════════════════════════════════════════════════

def get_entity_tree() -> List[Dict[str, Any]]:
    """Retorna el árbol completo de entidades con hijos anidados.
    Cada nodo: {id, name, type, industry, status, children[]}."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, name, type, parent_id, industry, status
            FROM entities
            ORDER BY parent_id NULLS FIRST, id ASC;
        """)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        put_conn(conn)
        return _build_tree(rows)
    except Exception as e:
        print(f"⚠️ [ORG_DRIVER] Fallback mock en get_entity_tree: {e}")
        return _build_tree(list(MOCK_ENTITIES))
