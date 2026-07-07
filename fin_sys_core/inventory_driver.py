# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Driver de Inventario (inventory_driver.py)
═══════════════════════════════════════════════════════════════
Driver independiente de CRUD para las tablas `inventory_items`
e `inventory_movements` de Supabase.

NO importa de database_driver — conexión directa al pool
centralizado de db_pool.py (mismo patrón que org_driver.py).
"""

import os
import sys
from typing import List, Dict, Any, Optional
from psycopg2.extras import RealDictCursor

# Conexión directa al pool centralizado (mismo patrón que org_driver.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_pool import get_conn, put_conn


# ═══════════════════════════════════════════════════════════
# MODO SIMULACIÓN — Datos en memoria si Postgres no responde
# ═══════════════════════════════════════════════════════════

MOCK_ITEMS = [
    {
        "id": 1, "portfolio_name": "Principal", "company_id": None,
        "name": "Resma Papel A4", "sku": "PAP-001",
        "category": "Papelería", "unit": "unidad",
        "cost_price": 12000, "sell_price": 15000,
        "current_stock": 50, "min_stock": 10,
        "status": "ACTIVO", "created_at": "2026-01-01", "updated_at": "2026-01-01"
    },
    {
        "id": 2, "portfolio_name": "Principal", "company_id": None,
        "name": "Tóner Impresora HP", "sku": "TON-002",
        "category": "Tecnología", "unit": "unidad",
        "cost_price": 85000, "sell_price": 120000,
        "current_stock": 5, "min_stock": 3,
        "status": "ACTIVO", "created_at": "2026-01-01", "updated_at": "2026-01-01"
    },
    {
        "id": 3, "portfolio_name": "Principal", "company_id": None,
        "name": "Caja Grapas x5000", "sku": "GRP-003",
        "category": "Papelería", "unit": "caja",
        "cost_price": 5000, "sell_price": 8000,
        "current_stock": 2, "min_stock": 5,
        "status": "ACTIVO", "created_at": "2026-01-01", "updated_at": "2026-01-01"
    },
    # ── Datos sintéticos para Jardín Infantil ──
    {
        "id": 4, "portfolio_name": "Pegasus", "company_id": 2,
        "name": "Uniforme Camiseta Talla 6", "sku": "UNI-T06",
        "category": "Uniformes", "unit": "unidad",
        "cost_price": 22000, "sell_price": 45000,
        "current_stock": 18, "min_stock": 5,
        "status": "ACTIVO", "created_at": "2026-03-01", "updated_at": "2026-06-01"
    },
    {
        "id": 5, "portfolio_name": "Pegasus", "company_id": 2,
        "name": "Uniforme Sudadera Talla 8", "sku": "UNI-S08",
        "category": "Uniformes", "unit": "unidad",
        "cost_price": 35000, "sell_price": 65000,
        "current_stock": 3, "min_stock": 5,
        "status": "ACTIVO", "created_at": "2026-03-01", "updated_at": "2026-06-10"
    },
    {
        "id": 6, "portfolio_name": "Pegasus", "company_id": 2,
        "name": "Kit Útiles Escolares Básico", "sku": "UTL-BAS",
        "category": "Útiles", "unit": "unidad",
        "cost_price": 18000, "sell_price": 32000,
        "current_stock": 25, "min_stock": 10,
        "status": "ACTIVO", "created_at": "2026-02-01", "updated_at": "2026-05-15"
    },
    {
        "id": 7, "portfolio_name": "Pegasus", "company_id": 2,
        "name": "Lonchera Térmica Institucional", "sku": "LON-TRM",
        "category": "Uniformes", "unit": "unidad",
        "cost_price": 28000, "sell_price": 48000,
        "current_stock": 0, "min_stock": 3,
        "status": "ACTIVO", "created_at": "2026-02-15", "updated_at": "2026-06-20"
    },
    {
        "id": 8, "portfolio_name": "Pegasus", "company_id": 2,
        "name": "Material Didáctico Montessori", "sku": "MAT-MNT",
        "category": "Material Didáctico", "unit": "caja",
        "cost_price": 95000, "sell_price": 0,
        "current_stock": 4, "min_stock": 2,
        "status": "ACTIVO", "created_at": "2026-01-20", "updated_at": "2026-04-01"
    },
    # ── Datos sintéticos para Consultora Digital ──
    {
        "id": 9, "portfolio_name": "Negocio A", "company_id": 1,
        "name": "Licencia Adobe CC Anual", "sku": "LIC-ADO",
        "category": "Tecnología", "unit": "unidad",
        "cost_price": 890000, "sell_price": 0,
        "current_stock": 3, "min_stock": 1,
        "status": "ACTIVO", "created_at": "2026-01-01", "updated_at": "2026-06-01"
    },
    {
        "id": 10, "portfolio_name": "Negocio A", "company_id": 1,
        "name": "Mouse Ergonómico Logitech", "sku": "PER-MOU",
        "category": "Tecnología", "unit": "unidad",
        "cost_price": 185000, "sell_price": 0,
        "current_stock": 2, "min_stock": 2,
        "status": "ACTIVO", "created_at": "2026-02-01", "updated_at": "2026-06-15"
    },
]

MOCK_MOVEMENTS = [
    {
        "id": 1, "item_id": 1, "type": "ENTRADA", "quantity": 100,
        "unit_price": 12000, "total": 1200000,
        "reference": "OC-001", "transaction_id": None,
        "third_party_id": None, "notes": "Compra inicial",
        "created_at": "2026-01-01"
    },
    {
        "id": 2, "item_id": 1, "type": "SALIDA", "quantity": 50,
        "unit_price": 12000, "total": 600000,
        "reference": "VTA-001", "transaction_id": None,
        "third_party_id": None, "notes": "Venta al detal",
        "created_at": "2026-01-15"
    },
    {
        "id": 3, "item_id": 4, "type": "ENTRADA", "quantity": 30,
        "unit_price": 22000, "total": 660000,
        "reference": "OC-JRD-001", "transaction_id": None,
        "third_party_id": None, "notes": "Compra uniformes temporada 2026",
        "created_at": "2026-03-01"
    },
    {
        "id": 4, "item_id": 4, "type": "SALIDA", "quantity": 12,
        "unit_price": 45000, "total": 540000,
        "reference": "VTA-JRD-002", "transaction_id": None,
        "third_party_id": None, "notes": "Ventas febrero-mayo",
        "created_at": "2026-05-30"
    },
    {
        "id": 5, "item_id": 5, "type": "ENTRADA", "quantity": 15,
        "unit_price": 35000, "total": 525000,
        "reference": "OC-JRD-003", "transaction_id": None,
        "third_party_id": None, "notes": "Compra sudaderas Talla 8",
        "created_at": "2026-03-15"
    },
    {
        "id": 6, "item_id": 5, "type": "SALIDA", "quantity": 12,
        "unit_price": 65000, "total": 780000,
        "reference": "VTA-JRD-004", "transaction_id": None,
        "third_party_id": None, "notes": "Ventas sudaderas semestre",
        "created_at": "2026-06-10"
    },
    {
        "id": 7, "item_id": 7, "type": "SALIDA", "quantity": 5,
        "unit_price": 48000, "total": 240000,
        "reference": "VTA-JRD-005", "transaction_id": None,
        "third_party_id": None, "notes": "Agotadas — reabastecer",
        "created_at": "2026-06-20"
    },
]

_mock_item_counter = 100
_mock_mov_counter = 100


# ═══════════════════════════════════════════════════════════
# 1. LISTAR ITEMS — Por portafolio y/o empresa
# ═══════════════════════════════════════════════════════════

def get_items(portfolio_name: str, company_id: int = None) -> List[Dict[str, Any]]:
    """Retorna todos los artículos de un portafolio.
    Opcionalmente filtra por company_id."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = "SELECT * FROM inventory_items WHERE portfolio_name = %s"
        params = [portfolio_name]

        if company_id is not None:
            query += " AND company_id = %s"
            params.append(company_id)

        query += " ORDER BY name ASC;"
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        put_conn(conn)

        # Serializar campos especiales
        for r in rows:
            for k in ['cost_price', 'sell_price']:
                if k in r and r[k] is not None:
                    r[k] = float(r[k])
            for k in ['created_at', 'updated_at']:
                if k in r and r[k]:
                    r[k] = str(r[k])
        return rows
    except Exception as e:
        print(f"⚠️ [INVENTORY_DRIVER] Fallback mock en get_items: {e}")
        return [
            i for i in MOCK_ITEMS
            if i["portfolio_name"] == portfolio_name
            and (company_id is None or i.get("company_id") == company_id)
        ]


# ═══════════════════════════════════════════════════════════
# 2. CREAR ITEM — Nuevo artículo en el catálogo
# ═══════════════════════════════════════════════════════════

def create_item(data: dict) -> Dict[str, Any]:
    """Crea un nuevo artículo de inventario.
    Requerido: portfolio_name, name.
    Opcional: sku, category, unit, cost_price, sell_price,
              current_stock, min_stock, company_id."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO inventory_items
                (portfolio_name, company_id, name, sku, category, unit,
                 cost_price, sell_price, current_stock, min_stock)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *;
        """, (
            data["portfolio_name"],
            data.get("company_id"),
            data["name"],
            data.get("sku", ""),
            data.get("category", "General"),
            data.get("unit", "unidad"),
            float(data.get("cost_price", 0)),
            float(data.get("sell_price", 0)),
            int(data.get("current_stock", 0)),
            int(data.get("min_stock", 0)),
        ))
        created = dict(cur.fetchone())
        conn.commit()
        cur.close()
        put_conn(conn)

        # Serializar
        for k in ['cost_price', 'sell_price']:
            if k in created and created[k] is not None:
                created[k] = float(created[k])
        for k in ['created_at', 'updated_at']:
            if k in created and created[k]:
                created[k] = str(created[k])
        return created
    except Exception as e:
        print(f"⚠️ [INVENTORY_DRIVER] Fallback mock en create_item: {e}")
        global _mock_item_counter
        _mock_item_counter += 1
        nuevo = {
            "id": _mock_item_counter,
            "portfolio_name": data.get("portfolio_name", "Principal"),
            "company_id": data.get("company_id"),
            "name": data["name"],
            "sku": data.get("sku", ""),
            "category": data.get("category", "General"),
            "unit": data.get("unit", "unidad"),
            "cost_price": float(data.get("cost_price", 0)),
            "sell_price": float(data.get("sell_price", 0)),
            "current_stock": int(data.get("current_stock", 0)),
            "min_stock": int(data.get("min_stock", 0)),
            "status": "ACTIVO",
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
        MOCK_ITEMS.append(nuevo)
        return nuevo


# ═══════════════════════════════════════════════════════════
# 3. ACTUALIZAR ITEM — Modificar campos de un artículo
# ═══════════════════════════════════════════════════════════

def update_item(item_id: int, data: dict) -> Dict[str, Any]:
    """Actualiza campos de un artículo existente.
    Campos permitidos: name, sku, category, unit, cost_price,
    sell_price, current_stock, min_stock, status."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Construir SET dinámico solo con campos presentes
        campos_permitidos = [
            "name", "sku", "category", "unit",
            "cost_price", "sell_price", "current_stock",
            "min_stock", "status"
        ]
        sets = []
        valores = []
        for campo in campos_permitidos:
            if campo in data:
                sets.append(f"{campo} = %s")
                valores.append(data[campo])

        if not sets:
            raise ValueError("No se proporcionaron campos para actualizar.")

        # Siempre actualizar updated_at
        sets.append("updated_at = NOW()")
        valores.append(item_id)

        query = f"""
            UPDATE inventory_items SET {', '.join(sets)}
            WHERE id = %s
            RETURNING *;
        """
        cur.execute(query, valores)
        updated = cur.fetchone()
        if not updated:
            raise ValueError(f"Artículo con ID {item_id} no encontrado.")
        updated = dict(updated)
        conn.commit()
        cur.close()
        put_conn(conn)

        # Serializar
        for k in ['cost_price', 'sell_price']:
            if k in updated and updated[k] is not None:
                updated[k] = float(updated[k])
        for k in ['created_at', 'updated_at']:
            if k in updated and updated[k]:
                updated[k] = str(updated[k])
        return updated
    except Exception as e:
        print(f"⚠️ [INVENTORY_DRIVER] Fallback mock en update_item: {e}")
        for item in MOCK_ITEMS:
            if item["id"] == item_id:
                for campo in ["name", "sku", "category", "unit",
                               "cost_price", "sell_price", "current_stock",
                               "min_stock", "status"]:
                    if campo in data:
                        item[campo] = data[campo]
                return item
        raise ValueError(f"Artículo con ID {item_id} no encontrado en mock.")


# ═══════════════════════════════════════════════════════════
# 4. ELIMINAR ITEM — Soft delete (status = ELIMINADO)
# ═══════════════════════════════════════════════════════════

def delete_item(item_id: int) -> Dict[str, Any]:
    """Marca un artículo como ELIMINADO (soft delete).
    No borra el registro de la base de datos."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            UPDATE inventory_items
            SET status = 'ELIMINADO', updated_at = NOW()
            WHERE id = %s
            RETURNING id, name, status;
        """, (item_id,))
        deleted = cur.fetchone()
        if not deleted:
            raise ValueError(f"Artículo con ID {item_id} no encontrado.")
        deleted = dict(deleted)
        conn.commit()
        cur.close()
        put_conn(conn)
        return deleted
    except Exception as e:
        print(f"⚠️ [INVENTORY_DRIVER] Fallback mock en delete_item: {e}")
        for item in MOCK_ITEMS:
            if item["id"] == item_id:
                item["status"] = "ELIMINADO"
                return {"id": item["id"], "name": item["name"], "status": "ELIMINADO"}
        raise ValueError(f"Artículo con ID {item_id} no encontrado en mock.")


# ═══════════════════════════════════════════════════════════
# 5. REGISTRAR MOVIMIENTO — Entrada / Salida / Ajuste
# ═══════════════════════════════════════════════════════════

def register_movement(data: dict) -> Dict[str, Any]:
    """Registra un movimiento de inventario y actualiza el stock.
    Requerido: item_id, type (ENTRADA|SALIDA|AJUSTE), quantity.
    Opcional: unit_price, reference, transaction_id,
              third_party_id, notes.

    Lógica de stock:
      - ENTRADA: current_stock += quantity
      - SALIDA:  current_stock -= quantity
      - AJUSTE:  current_stock = quantity (set absoluto)
    """
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        item_id = data["item_id"]
        mov_type = data["type"]  # ENTRADA, SALIDA, AJUSTE
        quantity = int(data["quantity"])
        unit_price = float(data.get("unit_price", 0))
        total = unit_price * quantity if unit_price else None

        # 1. Insertar movimiento
        cur.execute("""
            INSERT INTO inventory_movements
                (item_id, type, quantity, unit_price, total,
                 reference, transaction_id, third_party_id, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *;
        """, (
            item_id, mov_type, quantity, unit_price, total,
            data.get("reference"),
            data.get("transaction_id"),
            data.get("third_party_id"),
            data.get("notes"),
        ))
        movement = dict(cur.fetchone())

        # 2. Actualizar stock del artículo
        if mov_type == "ENTRADA":
            cur.execute("""
                UPDATE inventory_items
                SET current_stock = current_stock + %s, updated_at = NOW()
                WHERE id = %s
                RETURNING current_stock;
            """, (quantity, item_id))
        elif mov_type == "SALIDA":
            cur.execute("""
                UPDATE inventory_items
                SET current_stock = current_stock - %s, updated_at = NOW()
                WHERE id = %s
                RETURNING current_stock;
            """, (quantity, item_id))
        elif mov_type == "AJUSTE":
            cur.execute("""
                UPDATE inventory_items
                SET current_stock = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING current_stock;
            """, (quantity, item_id))

        stock_row = cur.fetchone()
        new_stock = dict(stock_row)["current_stock"] if stock_row else None

        conn.commit()
        cur.close()
        put_conn(conn)

        # Serializar
        for k in ['unit_price', 'total']:
            if k in movement and movement[k] is not None:
                movement[k] = float(movement[k])
        if movement.get('created_at'):
            movement['created_at'] = str(movement['created_at'])

        movement["new_stock"] = new_stock
        return movement
    except Exception as e:
        print(f"⚠️ [INVENTORY_DRIVER] Fallback mock en register_movement: {e}")
        global _mock_mov_counter
        _mock_mov_counter += 1

        quantity = int(data["quantity"])
        unit_price = float(data.get("unit_price", 0))

        nuevo_mov = {
            "id": _mock_mov_counter,
            "item_id": data["item_id"],
            "type": data["type"],
            "quantity": quantity,
            "unit_price": unit_price,
            "total": unit_price * quantity,
            "reference": data.get("reference"),
            "transaction_id": data.get("transaction_id"),
            "third_party_id": data.get("third_party_id"),
            "notes": data.get("notes"),
            "created_at": "2026-01-01",
            "new_stock": None,
        }

        # Actualizar stock en mock
        for item in MOCK_ITEMS:
            if item["id"] == data["item_id"]:
                if data["type"] == "ENTRADA":
                    item["current_stock"] += quantity
                elif data["type"] == "SALIDA":
                    item["current_stock"] -= quantity
                elif data["type"] == "AJUSTE":
                    item["current_stock"] = quantity
                nuevo_mov["new_stock"] = item["current_stock"]
                break

        MOCK_MOVEMENTS.append(nuevo_mov)
        return nuevo_mov


# ═══════════════════════════════════════════════════════════
# 6. LISTAR MOVIMIENTOS — Por item y/o portafolio
# ═══════════════════════════════════════════════════════════

def get_movements(item_id: int = None, portfolio_name: str = None,
                  limit: int = 50) -> List[Dict[str, Any]]:
    """Retorna movimientos de inventario.
    Filtra por item_id y/o portfolio_name. Máximo `limit` registros."""
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT m.*, i.name AS item_name, i.sku AS item_sku
            FROM inventory_movements m
            JOIN inventory_items i ON i.id = m.item_id
            WHERE 1=1
        """
        params = []

        if item_id is not None:
            query += " AND m.item_id = %s"
            params.append(item_id)

        if portfolio_name is not None:
            query += " AND i.portfolio_name = %s"
            params.append(portfolio_name)

        query += " ORDER BY m.created_at DESC LIMIT %s;"
        params.append(limit)

        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        put_conn(conn)

        # Serializar campos especiales
        for r in rows:
            for k in ['unit_price', 'total']:
                if k in r and r[k] is not None:
                    r[k] = float(r[k])
            if r.get('created_at'):
                r['created_at'] = str(r['created_at'])
        return rows
    except Exception as e:
        print(f"⚠️ [INVENTORY_DRIVER] Fallback mock en get_movements: {e}")
        result = MOCK_MOVEMENTS[:]
        if item_id is not None:
            result = [m for m in result if m["item_id"] == item_id]
        return result[:limit]


# ═══════════════════════════════════════════════════════════
# 7. RESUMEN DE STOCK — Totales y alertas de stock bajo
# ═══════════════════════════════════════════════════════════

def get_stock_summary(portfolio_name: str) -> Dict[str, Any]:
    """Retorna resumen de inventario para un portafolio:
    - total_items: cantidad de artículos activos
    - total_value: valor total (cost_price * current_stock)
    - low_stock_alerts: artículos con stock <= min_stock
    """
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Totales generales
        cur.execute("""
            SELECT
                COUNT(*) AS total_items,
                COALESCE(SUM(cost_price * current_stock), 0) AS total_value,
                COALESCE(SUM(current_stock), 0) AS total_units
            FROM inventory_items
            WHERE portfolio_name = %s AND status = 'ACTIVO';
        """, (portfolio_name,))
        summary = dict(cur.fetchone())
        summary["total_value"] = float(summary["total_value"])
        summary["total_units"] = int(summary["total_units"])

        # Alertas de stock bajo
        cur.execute("""
            SELECT id, name, sku, current_stock, min_stock
            FROM inventory_items
            WHERE portfolio_name = %s
              AND status = 'ACTIVO'
              AND current_stock <= min_stock
              AND min_stock > 0
            ORDER BY (current_stock - min_stock) ASC;
        """, (portfolio_name,))
        alerts = [dict(r) for r in cur.fetchall()]

        cur.close()
        put_conn(conn)

        summary["low_stock_alerts"] = alerts
        return summary
    except Exception as e:
        print(f"⚠️ [INVENTORY_DRIVER] Fallback mock en get_stock_summary: {e}")
        activos = [
            i for i in MOCK_ITEMS
            if i["portfolio_name"] == portfolio_name and i["status"] == "ACTIVO"
        ]
        total_value = sum(i["cost_price"] * i["current_stock"] for i in activos)
        total_units = sum(i["current_stock"] for i in activos)
        low_stock = [
            {"id": i["id"], "name": i["name"], "sku": i["sku"],
             "current_stock": i["current_stock"], "min_stock": i["min_stock"]}
            for i in activos
            if i["current_stock"] <= i["min_stock"] and i["min_stock"] > 0
        ]
        return {
            "total_items": len(activos),
            "total_value": total_value,
            "total_units": total_units,
            "low_stock_alerts": low_stock,
        }
