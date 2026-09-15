# -*- coding: utf-8 -*-
"""Un solo objeto por módulo de fin_sys_core (regresión del doble pool).

Antes del alias de fin_sys_core/__init__.py, `import db_pool` y
`import fin_sys_core.db_pool` eran DOS módulos → dos pools por proceso.
Estos tests fallan si vuelve a pasar, en cualquier orden de importación.
Sin BD: solo importan módulos.
"""
import importlib
import os
import subprocess
import sys
import textwrap
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
# Simula lo que hacían server.py y varios drivers: la forma corta en sys.path
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

# Módulos sin dependencias externas pesadas (ai_engine/bot_* necesitan httpx
# y credenciales; se cubren indirectamente por el finder genérico).
MODULOS = [
    "db_pool", "database_driver", "tax_motor", "ledger_math",
    "transaction_service", "org_driver", "inventory_driver", "mock_policy",
    "cartera_plan", "incremental_balance", "draft_builder",
]


class TestIdentidadDeModulos(unittest.TestCase):
    def test_forma_corta_y_paquete_son_el_mismo_objeto(self):
        import fin_sys_core  # noqa: F401  (instala el alias)
        for nombre in MODULOS:
            with self.subTest(modulo=nombre):
                corto = importlib.import_module(nombre)
                paquete = importlib.import_module(f"fin_sys_core.{nombre}")
                self.assertIs(corto, paquete, f"{nombre} cargado dos veces")

    def test_estado_compartido(self):
        import fin_sys_core  # noqa: F401
        import db_pool
        import fin_sys_core.db_pool as paquete
        self.assertIs(db_pool._init_lock, paquete._init_lock)
        self.assertIs(db_pool._fallback_sem, paquete._fallback_sem)

    def test_orden_inverso_en_proceso_nuevo(self):
        """`import db_pool` ANTES de que exista `fin_sys_core` en sys.modules."""
        codigo = textwrap.dedent(f"""
            import os, sys
            root = {_ROOT!r}
            sys.path.insert(0, root)
            sys.path.insert(0, os.path.join(root, "fin_sys_core"))
            import db_pool                         # forma corta primero
            import fin_sys_core.db_pool as paquete  # dispara el __init__
            assert db_pool is paquete, "orden inverso: dos objetos"
            import tax_motor
            import fin_sys_core.tax_motor as tm
            assert tax_motor is tm
            print("OK")
        """)
        r = subprocess.run([sys.executable, "-c", codigo],
                           capture_output=True, text=True, cwd=_ROOT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)


if __name__ == "__main__":
    unittest.main()
