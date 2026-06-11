# -*- coding: utf-8 -*-
"""
FIN-SYS CONTROL TOWER — Driver de Base de Datos
------------------------------------------------
Gestiona las 5 tablas nuevas del módulo Control Tower:
  - workspace_users: Colaboradores con roles dinámicos
  - entities: Árbol jerárquico de 5 niveles
  - entity_members: Asignación de usuarios a entidades
  - resource_ids: Inventario de IDs/documentos clasificados
  - approvals_queue: Cola de gastos pendientes de aprobación
"""

import os
import sys
import json
import hashlib
from typing import List, Dict, Any, Optional

# Importar el driver de BD existente para reutilizar la conexión
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database_driver import get_db_connection, IS_POSTGRES_ACTIVE

# ──────────────────────────────────────────────
# MODO SIMULACIÓN (cuando Postgres no está activo)
# ──────────────────────────────────────────────
MOCK_ENTITIES = [
    {
        "id": 1, "name": "Mi Holding Principal", "type": "HOLDING",
        "parent_id": None, "portfolio_id": None,
        "industry": "MULTI-SECTOR", "sub_industry": "Holding",
        "status": "AL DIA", "created_by": 1,
        "children": []
    },
    {
        "id": 2, "name": "Jardín Infantil Pegasus", "type": "EMPRESA",
        "parent_id": 1, "portfolio_id": 2,
        "industry": "EDUCACION", "sub_industry": "Jardín Infantil",
        "status": "AL DIA", "created_by": 1,
        "children": []
    },
    {
        "id": 3, "name": "Consultora Digital SAS", "type": "EMPRESA",
        "parent_id": 1, "portfolio_id": 1,
        "industry": "SERVICIOS", "sub_industry": "Consultoría",
        "status": "ALERTA", "created_by": 1,
        "children": []
    },
    {
        "id": 4, "name": "Proyecto E-Commerce", "type": "PROYECTO",
        "parent_id": 3, "portfolio_id": None,
        "industry": "COMERCIO", "sub_industry": "Retail Digital",
        "status": "AL DIA", "created_by": 1,
        "children": []
    },
]

MOCK_WORKSPACE_USERS = [
    {
        "id": 1, "name": "Andrés (Super-Contador)", "email": "andres@finsys.os",
        "password_hash": hashlib.md5("admin123".encode()).hexdigest(),
        "role_label": "Super-Contador",
        "permissions": {"ledger": True, "reports": True, "users": True, "approvals": True},
        "parent_user_id": None
    }
]

MOCK_RESOURCE_IDS = []
MOCK_APPROVALS = []
MOCK_MEMBERS = []


def _hash_password(password: str) -> str:
    """Hash simple MD5 para simulación local."""
    return hashlib.md5(password.encode()).hexdigest()


def init_control_tower_db():
    """Crea las 5 tablas del Control Tower si no existen."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. workspace_users
        cur.execute("""
        CREATE TABLE IF NOT EXISTS workspace_users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role_label VARCHAR(100) NOT NULL DEFAULT 'Colaborador',
            permissions JSONB DEFAULT '{"ledger": true, "reports": true, "users": false, "approvals": false}'::jsonb,
            parent_user_id INTEGER REFERENCES workspace_users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Seed del Super-Contador inicial
        cur.execute("SELECT COUNT(*) FROM workspace_users;")
        if cur.fetchone()[0] == 0:
            cur.execute("""
            INSERT INTO workspace_users (name, email, password_hash, role_label, permissions)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING;
            """, (
                "Andrés (Super-Contador)",
                "andres@finsys.os",
                _hash_password("admin123"),
                "Super-Contador",
                json.dumps({"ledger": True, "reports": True, "users": True, "approvals": True})
            ))

        # 2. entities (árbol recursivo con self-reference)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id SERIAL PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            type VARCHAR(20) NOT NULL DEFAULT 'EMPRESA',
            parent_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
            portfolio_id INTEGER REFERENCES portfolios(id) ON DELETE SET NULL,
            industry VARCHAR(100),
            sub_industry VARCHAR(100),
            status VARCHAR(20) NOT NULL DEFAULT 'AL DIA',
            created_by INTEGER REFERENCES workspace_users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Seed de entidades demo
        cur.execute("SELECT COUNT(*) FROM entities;")
        if cur.fetchone()[0] == 0:
            cur.execute("""
            INSERT INTO entities (name, type, parent_id, industry, sub_industry, status)
            VALUES ('Mi Holding Principal', 'HOLDING', NULL, 'MULTI-SECTOR', 'Holding', 'AL DIA')
            RETURNING id;
            """)
            holding_id = cur.fetchone()[0]
            cur.execute("""
            INSERT INTO entities (name, type, parent_id, industry, sub_industry, status)
            VALUES
                ('Jardín Infantil Pegasus', 'EMPRESA', %s, 'EDUCACION', 'Jardín Infantil', 'AL DIA'),
                ('Consultora Digital SAS', 'EMPRESA', %s, 'SERVICIOS', 'Consultoría', 'ALERTA');
            """, (holding_id, holding_id))

        # 3. entity_members
        cur.execute("""
        CREATE TABLE IF NOT EXISTS entity_members (
            id SERIAL PRIMARY KEY,
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES workspace_users(id) ON DELETE CASCADE,
            role_label VARCHAR(100) NOT NULL DEFAULT 'Colaborador',
            permissions JSONB DEFAULT '{"ledger": true, "reports": true}'::jsonb,
            invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            UNIQUE(entity_id, user_id)
        );
        """)

        # 4. resource_ids
        cur.execute("""
        CREATE TABLE IF NOT EXISTS resource_ids (
            id SERIAL PRIMARY KEY,
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            label VARCHAR(100) NOT NULL,
            value VARCHAR(255) NOT NULL,
            category VARCHAR(50) NOT NULL DEFAULT 'FISCAL',
            expires_at DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 5. approvals_queue
        cur.execute("""
        CREATE TABLE IF NOT EXISTS approvals_queue (
            id SERIAL PRIMARY KEY,
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
            requested_by INTEGER REFERENCES workspace_users(id) ON DELETE SET NULL,
            description VARCHAR(255),
            amount DECIMAL(15,2),
            status VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
            reviewed_by INTEGER REFERENCES workspace_users(id) ON DELETE SET NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("✅ Control Tower DB inicializado correctamente.")
        return True
    except Exception as e:
        print(f"⚠️ Control Tower DB error: {e}")
        return False


# ──────────────────────────────────────────────
# FUNCIONES DE ENTIDADES
# ──────────────────────────────────────────────

def obtener_entidades_arbol() -> List[Dict[str, Any]]:
    """Retorna todas las entidades como árbol jerárquico anidado."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, type, parent_id, portfolio_id, industry,
                   sub_industry, status, created_at
            FROM entities
            ORDER BY parent_id NULLS FIRST, id ASC;
        """)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        flat = [dict(zip(cols, r)) for r in rows]
        cur.close()
        conn.close()
        return _build_tree(flat)
    except Exception:
        return _build_tree(MOCK_ENTITIES)


def _build_tree(flat: List[Dict]) -> List[Dict]:
    """Construye árbol anidado desde lista plana con parent_id."""
    lookup = {e["id"]: {**e, "children": []} for e in flat}
    roots = []
    for item in lookup.values():
        pid = item.get("parent_id")
        if pid and pid in lookup:
            lookup[pid]["children"].append(item)
        else:
            roots.append(item)
    return roots


def crear_entidad(data: Dict[str, Any]) -> int:
    """Crea una nueva entidad en el árbol."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO entities (name, type, parent_id, portfolio_id, industry, sub_industry, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """, (
            data["name"],
            data.get("type", "EMPRESA"),
            data.get("parent_id"),
            data.get("portfolio_id"),
            data.get("industry", ""),
            data.get("sub_industry", ""),
            data.get("status", "AL DIA")
        ))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return new_id
    except Exception as e:
        print(f"Error creando entidad: {e}")
        new_id = max(e["id"] for e in MOCK_ENTITIES) + 1
        MOCK_ENTITIES.append({"id": new_id, **data, "children": []})
        return new_id


def actualizar_estado_entidad(entity_id: int, status: str) -> bool:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE entities SET status = %s WHERE id = %s;", (status, entity_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception:
        for e in MOCK_ENTITIES:
            if e["id"] == entity_id:
                e["status"] = status
        return True


def eliminar_entidad(entity_id: int) -> bool:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM entities WHERE id = %s;", (entity_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception:
        return False


# ──────────────────────────────────────────────
# FUNCIONES DE USUARIOS / COLABORADORES
# ──────────────────────────────────────────────

def obtener_workspace_users() -> List[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, email, role_label, permissions, created_at
            FROM workspace_users ORDER BY id ASC;
        """)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        result = []
        for r in rows:
            d = dict(zip(cols, r))
            if isinstance(d["permissions"], str):
                d["permissions"] = json.loads(d["permissions"])
            result.append(d)
        cur.close()
        conn.close()
        return result
    except Exception:
        return [{k: v for k, v in u.items() if k != "password_hash"}
                for u in MOCK_WORKSPACE_USERS]


def registrar_workspace_user(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        perms = data.get("permissions", {"ledger": True, "reports": True, "users": False, "approvals": False})
        cur.execute("""
        INSERT INTO workspace_users (name, email, password_hash, role_label, permissions, parent_user_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, name, email, role_label;
        """, (
            data["name"],
            data["email"],
            _hash_password(data["password"]),
            data.get("role_label", "Colaborador"),
            json.dumps(perms),
            data.get("parent_user_id")
        ))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return {"id": row[0], "name": row[1], "email": row[2], "role_label": row[3]}
    except Exception as e:
        raise ValueError(f"Error registrando usuario: {e}")


def login_workspace_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    password_hash = _hash_password(password)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT id, name, email, role_label, permissions
        FROM workspace_users
        WHERE email = %s AND password_hash = %s;
        """, (email, password_hash))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            perms = row[4]
            if isinstance(perms, str):
                perms = json.loads(perms)
            return {"id": row[0], "name": row[1], "email": row[2],
                    "role_label": row[3], "permissions": perms}
        return None
    except Exception:
        for u in MOCK_WORKSPACE_USERS:
            if u["email"] == email and u["password_hash"] == password_hash:
                return {k: v for k, v in u.items() if k != "password_hash"}
        return None


# ──────────────────────────────────────────────
# FUNCIONES DE RESOURCE IDs
# ──────────────────────────────────────────────

def obtener_resource_ids(entity_id: int) -> List[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT id, entity_id, label, value, category, expires_at, notes, created_at
        FROM resource_ids WHERE entity_id = %s ORDER BY category, label;
        """, (entity_id,))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        cur.close()
        conn.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return [r for r in MOCK_RESOURCE_IDS if r.get("entity_id") == entity_id]


def crear_resource_id(data: Dict[str, Any]) -> int:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO resource_ids (entity_id, label, value, category, expires_at, notes)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        """, (
            data["entity_id"], data["label"], data["value"],
            data.get("category", "FISCAL"), data.get("expires_at"),
            data.get("notes")
        ))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return new_id
    except Exception as e:
        new_id = len(MOCK_RESOURCE_IDS) + 1
        MOCK_RESOURCE_IDS.append({"id": new_id, **data})
        return new_id


def eliminar_resource_id(rid: int) -> bool:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM resource_ids WHERE id = %s;", (rid,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception:
        return False


# ──────────────────────────────────────────────
# FUNCIONES DE APROBACIONES
# ──────────────────────────────────────────────

def obtener_aprobaciones(entity_id: Optional[int] = None) -> List[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if entity_id:
            cur.execute("""
            SELECT a.id, a.entity_id, e.name as entity_name,
                   a.description, a.amount, a.status, a.created_at,
                   wu.name as requested_by_name
            FROM approvals_queue a
            JOIN entities e ON a.entity_id = e.id
            LEFT JOIN workspace_users wu ON a.requested_by = wu.id
            WHERE a.entity_id = %s
            ORDER BY a.created_at DESC;
            """, (entity_id,))
        else:
            cur.execute("""
            SELECT a.id, a.entity_id, e.name as entity_name,
                   a.description, a.amount, a.status, a.created_at,
                   wu.name as requested_by_name
            FROM approvals_queue a
            JOIN entities e ON a.entity_id = e.id
            LEFT JOIN workspace_users wu ON a.requested_by = wu.id
            ORDER BY a.created_at DESC;
            """)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        cur.close()
        conn.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return MOCK_APPROVALS


def crear_aprobacion(data: Dict[str, Any]) -> int:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO approvals_queue (entity_id, transaction_id, requested_by, description, amount, status)
        VALUES (%s, %s, %s, %s, %s, 'PENDIENTE') RETURNING id;
        """, (
            data["entity_id"], data.get("transaction_id"),
            data.get("requested_by"), data.get("description"), data.get("amount")
        ))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return new_id
    except Exception as e:
        new_id = len(MOCK_APPROVALS) + 1
        MOCK_APPROVALS.append({"id": new_id, "status": "PENDIENTE", **data})
        return new_id


def resolver_aprobacion(approval_id: int, status: str, reviewer_id: int, notes: str = "") -> bool:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        UPDATE approvals_queue
        SET status = %s, reviewed_by = %s, notes = %s
        WHERE id = %s;
        """, (status, reviewer_id, notes, approval_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception:
        for a in MOCK_APPROVALS:
            if a["id"] == approval_id:
                a["status"] = status
        return True


# ──────────────────────────────────────────────
# FUNCIONES DE MIEMBROS POR ENTIDAD
# ──────────────────────────────────────────────

def obtener_miembros_entidad(entity_id: int) -> List[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT em.id, em.entity_id, em.role_label, em.permissions,
               em.invited_at, em.expires_at,
               wu.name, wu.email
        FROM entity_members em
        JOIN workspace_users wu ON em.user_id = wu.id
        WHERE em.entity_id = %s;
        """, (entity_id,))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        cur.close()
        conn.close()
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []


def invitar_miembro(entity_id: int, user_id: int, role_label: str,
                    permissions: dict, expires_at=None) -> int:
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO entity_members (entity_id, user_id, role_label, permissions, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (entity_id, user_id) DO UPDATE
            SET role_label = EXCLUDED.role_label,
                permissions = EXCLUDED.permissions
        RETURNING id;
        """, (entity_id, user_id, role_label, json.dumps(permissions), expires_at))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return new_id
    except Exception as e:
        raise ValueError(f"Error invitando miembro: {e}")


# ──────────────────────────────────────────────
# FUNCIÓN DE KPIs CONSOLIDADOS
# ──────────────────────────────────────────────

def obtener_kpis_entidad(entity_id: int) -> Dict[str, Any]:
    """Calcula KPIs consolidados de una entidad y todos sus hijos."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Obtener todos los IDs de la jerarquía descendiente
        cur.execute("""
        WITH RECURSIVE entity_tree AS (
            SELECT id FROM entities WHERE id = %s
            UNION ALL
            SELECT e.id FROM entities e
            JOIN entity_tree et ON e.parent_id = et.id
        )
        SELECT id FROM entity_tree;
        """, (entity_id,))
        entity_ids = [r[0] for r in cur.fetchall()]

        # Obtener portfolios vinculados
        cur.execute("""
        SELECT DISTINCT portfolio_id FROM entities
        WHERE id = ANY(%s) AND portfolio_id IS NOT NULL;
        """, (entity_ids,))
        portfolio_ids = [r[0] for r in cur.fetchall()]

        total_ingresos = 0.0
        total_gastos = 0.0
        total_cxc = 0.0
        pending_approvals = 0

        if portfolio_ids:
            cur.execute("""
            SELECT
                SUM(CASE WHEN type = 'INGRESO' THEN net_value ELSE 0 END) as ingresos,
                SUM(CASE WHEN type = 'GASTO' THEN net_value ELSE 0 END) as gastos
            FROM transactions
            WHERE portfolio_id = ANY(%s);
            """, (portfolio_ids,))
            row = cur.fetchone()
            total_ingresos = float(row[0] or 0)
            total_gastos = float(row[1] or 0)

            try:
                cur.execute("""
                SELECT COALESCE(SUM(remaining_balance), 0)
                FROM cxp_cxc_ledger cxc
                JOIN transactions t ON cxc.transaction_id = t.id
                WHERE t.portfolio_id = ANY(%s) AND cxc.type = 'CXC' AND cxc.status = 'PENDIENTE';
                """, (portfolio_ids,))
                total_cxc = float(cur.fetchone()[0] or 0)
            except Exception:
                total_cxc = 0.0  # tabla no existe aún

        # Aprobaciones pendientes
        cur.execute("""
        SELECT COUNT(*) FROM approvals_queue
        WHERE entity_id = ANY(%s) AND status = 'PENDIENTE';
        """, (entity_ids,))
        pending_approvals = cur.fetchone()[0]

        # Número de entidades hijas
        cur.execute("""
        SELECT COUNT(*) FROM entities WHERE parent_id = %s;
        """, (entity_id,))
        child_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        return {
            "total_ingresos": total_ingresos,
            "total_gastos": total_gastos,
            "balance_neto": total_ingresos - total_gastos,
            "total_cxc": total_cxc,
            "pending_approvals": pending_approvals,
            "child_entities": child_count,
            "entity_ids_in_scope": len(entity_ids)
        }
    except Exception as e:
        print(f"Error calculando KPIs: {e}")
        return {
            "total_ingresos": 68575000.0,
            "total_gastos": 26352500.0,
            "balance_neto": 42222500.0,
            "total_cxc": 0.0,
            "pending_approvals": 4,
            "child_entities": 4,
            "entity_ids_in_scope": 7
        }
