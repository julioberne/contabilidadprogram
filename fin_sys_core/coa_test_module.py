# -*- coding: utf-8 -*-
"""
Módulo de prueba independiente para el Catálogo de Cuentas (COA) Flexible.
Este archivo contiene la lógica para manejar jerarquías y plantillas predefinidas.
"""

from typing import List, Dict, Any

# ==========================================
# 1. Esquema SQL (Propuesta para PostgreSQL)
# ==========================================
COA_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS test_chart_of_accounts (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER, -- Simulación de FK a portfolios
    code VARCHAR(50) NOT NULL,
    name VARCHAR(150) NOT NULL,
    account_type VARCHAR(20) NOT NULL, -- 'ACTIVO', 'PASIVO', 'PATRIMONIO', 'INGRESO', 'GASTO'
    parent_id INTEGER REFERENCES test_chart_of_accounts(id) ON DELETE CASCADE,
    is_group BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (portfolio_id, code)
);
"""

# ==========================================
# 2. Definición de Plantillas COA
# ==========================================
COA_TEMPLATES = {
    "ESTANDAR": [
        {"code": "1", "name": "Activos", "account_type": "ACTIVO", "is_group": True, "parent_code": None},
        {"code": "11", "name": "Efectivo y Equivalentes", "account_type": "ACTIVO", "is_group": True, "parent_code": "1"},
        {"code": "1105", "name": "Caja", "account_type": "ACTIVO", "is_group": False, "parent_code": "11"},
        {"code": "1110", "name": "Bancos", "account_type": "ACTIVO", "is_group": False, "parent_code": "11"},
        
        {"code": "2", "name": "Pasivos", "account_type": "PASIVO", "is_group": True, "parent_code": None},
        {"code": "21", "name": "Cuentas por Pagar", "account_type": "PASIVO", "is_group": True, "parent_code": "2"},
        
        {"code": "3", "name": "Patrimonio", "account_type": "PATRIMONIO", "is_group": True, "parent_code": None},
        
        {"code": "4", "name": "Ingresos", "account_type": "INGRESO", "is_group": True, "parent_code": None},
        {"code": "41", "name": "Ingresos Operacionales", "account_type": "INGRESO", "is_group": True, "parent_code": "4"},
        
        {"code": "5", "name": "Gastos", "account_type": "GASTO", "is_group": True, "parent_code": None},
    ],
    "INMOBILIARIA": [
        {"code": "15", "name": "Propiedades, Planta y Equipo", "account_type": "ACTIVO", "is_group": True, "parent_code": "1"},
        {"code": "1516", "name": "Bienes Raíces para Alquiler", "account_type": "ACTIVO", "is_group": False, "parent_code": "15"},
        {"code": "4120", "name": "Ingresos por Alquiler", "account_type": "INGRESO", "is_group": False, "parent_code": "41"},
    ],
    "RETAIL": [
        {"code": "14", "name": "Inventarios", "account_type": "ACTIVO", "is_group": True, "parent_code": "1"},
        {"code": "1435", "name": "Mercancía no fabricada por la empresa", "account_type": "ACTIVO", "is_group": False, "parent_code": "14"},
        {"code": "6135", "name": "Costo de Ventas Retail", "account_type": "GASTO", "is_group": False, "parent_code": "5"},
    ],
    "CONSTRUCTORA": [
        {"code": "14", "name": "Inventarios de Construcción", "account_type": "ACTIVO", "is_group": True, "parent_code": "1"},
        {"code": "1410", "name": "Trabajo en Progreso (WIP)", "account_type": "ACTIVO", "is_group": False, "parent_code": "14"},
        {"code": "4150", "name": "Ingresos por Avance de Obra", "account_type": "INGRESO", "is_group": False, "parent_code": "41"},
    ]
}

# ==========================================
# 3. Lógica de Simulación
# ==========================================
class MockCOADatabase:
    def __init__(self):
        self.accounts = []
        self._id_counter = 1

    def _get_account_by_code(self, portfolio_id: int, code: str) -> Any:
        for acc in self.accounts:
            if acc["portfolio_id"] == portfolio_id and acc["code"] == code:
                return acc
        return None

    def add_account(self, portfolio_id: int, code: str, name: str, account_type: str, is_group: bool, parent_code: str = None) -> int:
        # Prevenir duplicados de código en el mismo portafolio
        if self._get_account_by_code(portfolio_id, code):
            raise ValueError(f"La cuenta con el código {code} ya existe en este portafolio.")

        parent_id = None
        if parent_code:
            parent_acc = self._get_account_by_code(portfolio_id, parent_code)
            if parent_acc:
                parent_id = parent_acc["id"]
            else:
                # El usuario puede agregar cuentas personalizadas colgando de padres existentes
                # Si el padre no existe, hay un error en la jerarquía.
                pass

        account = {
            "id": self._id_counter,
            "portfolio_id": portfolio_id,
            "code": code,
            "name": name,
            "account_type": account_type,
            "is_group": is_group,
            "parent_id": parent_id
        }
        self.accounts.append(account)
        self._id_counter += 1
        return account["id"]

    def load_template(self, portfolio_id: int, template_name: str = "ESTANDAR"):
        """
        Carga la plantilla estándar (siempre como base) y luego superpone
        las cuentas específicas de la industria si es requerida.
        """
        print(f"[*] Cargando plantilla ESTANDAR para portafolio {portfolio_id}")
        base_template = COA_TEMPLATES["ESTANDAR"]
        
        # Cargar base
        for acc in base_template:
            try:
                self.add_account(portfolio_id, acc["code"], acc["name"], acc["account_type"], acc["is_group"], acc["parent_code"])
            except ValueError:
                pass

        # Cargar industria si aplica
        if template_name != "ESTANDAR" and template_name in COA_TEMPLATES:
            print(f"[*] Superponiendo cuentas de la plantilla {template_name}")
            industry_template = COA_TEMPLATES[template_name]
            for acc in industry_template:
                try:
                    self.add_account(portfolio_id, acc["code"], acc["name"], acc["account_type"], acc["is_group"], acc["parent_code"])
                except ValueError:
                    pass

    def get_tree(self, portfolio_id: int):
        """Retorna el árbol jerárquico de cuentas para un portafolio."""
        portfolio_accs = [a for a in self.accounts if a["portfolio_id"] == portfolio_id]
        
        # Diccionario para acceso rápido
        acc_dict = {a["id"]: {**a, "children": []} for a in portfolio_accs}
        
        tree = []
        for acc_id, node in acc_dict.items():
            parent_id = node.get("parent_id")
            if parent_id and parent_id in acc_dict:
                acc_dict[parent_id]["children"].append(node)
            else:
                tree.append(node)
                
        return tree

    def print_tree(self, nodes, level=0):
        """Imprime el árbol de forma amigable"""
        for node in nodes:
            indent = "  " * level
            group_indicator = "[+]" if node["is_group"] else "   "
            print(f"{indent}{group_indicator} {node['code']} - {node['name']} ({node['account_type']})")
            if node["children"]:
                self.print_tree(node["children"], level + 1)
