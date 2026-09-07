# -*- coding: utf-8 -*-
"""DT-28 (incidente 2026-09-07): durante un corte de red los drivers servían
datos MOCK como si fueran reales — el selector mostró empresas inventadas.
Regla: fallo de BD ⇒ error visible; mock SOLO con FINSYS_ALLOW_MOCK=1."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fin_sys_core"))

import org_driver          # noqa: E402
import inventory_driver    # noqa: E402
from mock_policy import mock_permitido  # noqa: E402


class TestPoliticaMock(unittest.TestCase):
    def test_flag_apagado_por_defecto(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("FINSYS_ALLOW_MOCK", None)
            self.assertFalse(mock_permitido())
        with mock.patch.dict(os.environ, {"FINSYS_ALLOW_MOCK": "1"}):
            self.assertTrue(mock_permitido())

    def test_selector_sin_flag_propaga_el_error(self):
        """El caso exacto del incidente: BD caída ⇒ NUNCA empresas inventadas."""
        with mock.patch.object(org_driver, "get_conn", side_effect=OSError("sin red")):
            with mock.patch.dict(os.environ):
                os.environ.pop("FINSYS_ALLOW_MOCK", None)
                with self.assertRaises(OSError):
                    org_driver.get_entities_for_selector()

    def test_selector_con_flag_sirve_mock(self):
        with mock.patch.object(org_driver, "get_conn", side_effect=OSError("sin red")):
            with mock.patch.dict(os.environ, {"FINSYS_ALLOW_MOCK": "1"}):
                out = org_driver.get_entities_for_selector()
        self.assertTrue(len(out) > 0)   # modo dev deliberado: mock permitido

    def test_inventario_sin_flag_propaga_el_error(self):
        with mock.patch.object(inventory_driver, "get_conn", side_effect=OSError("sin red")):
            with mock.patch.dict(os.environ):
                os.environ.pop("FINSYS_ALLOW_MOCK", None)
                with self.assertRaises(OSError):
                    inventory_driver.get_items("Negocio A")


if __name__ == "__main__":
    unittest.main()
