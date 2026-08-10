# -*- coding: utf-8 -*-
"""Tests unitarios del núcleo del Bot IA (funciones puras, sin BD).

Ejecutar:  .venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_bot_*.py" -v
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import bot_driver  # noqa: E402


class TestParseCommand(unittest.TestCase):
    """Confirmar/descartar JAMÁS deben depender del LLM — regex estricta."""

    def test_confirmar_variantes(self):
        for texto in ("Confirmar #42", "confirmar 42", "  CONFIRMAR #42  ", "/confirmar 42"):
            self.assertEqual(bot_driver.parse_command(texto), ("confirmar", 42), texto)

    def test_confirmar_sin_numero(self):
        self.assertEqual(bot_driver.parse_command("confirmar"), ("confirmar", None))

    def test_descartar(self):
        self.assertEqual(bot_driver.parse_command("Descartar #7"), ("descartar", 7))

    def test_vincular_normaliza_mayusculas(self):
        self.assertEqual(bot_driver.parse_command("/vincular abc123"), ("vincular", "ABC123"))

    def test_ayuda_y_borradores(self):
        self.assertEqual(bot_driver.parse_command("/start")[0], "ayuda")
        self.assertEqual(bot_driver.parse_command("/ayuda")[0], "ayuda")
        self.assertEqual(bot_driver.parse_command("/borradores")[0], "borradores")
        self.assertEqual(bot_driver.parse_command("borradores")[0], "borradores")

    def test_texto_libre_no_es_comando(self):
        for texto in ("gasté 20.000 en taxi", "confirmar el gasto de ayer",
                      "vincular", "", None):
            self.assertEqual(bot_driver.parse_command(texto), (None, None), repr(texto))


class TestBuildPayload(unittest.TestCase):

    def test_defaults_quedan_marcados_como_inferidos(self):
        parsed = {"type": "GASTO", "amount": "45000", "concept": "Almuerzo"}
        payload, inferred = bot_driver.build_payload(parsed, "Personal")
        self.assertEqual(payload["amount"], 45000.0)
        self.assertEqual(payload["payment_method"], "Efectivo")
        self.assertEqual(payload["category"], "Otros Gastos")
        self.assertEqual(payload["third_party"]["identification_number"], "999999999")
        for campo in ("payment_method", "category", "third_party"):
            self.assertIn(campo, inferred)

    def test_tipo_invalido_cae_a_gasto(self):
        payload, _ = bot_driver.build_payload({"type": "EGRESO", "amount": 1}, "P")
        self.assertEqual(payload["type"], "GASTO")

    def test_monto_invalido_queda_none(self):
        payload, _ = bot_driver.build_payload({"amount": "cuarenta"}, "P")
        self.assertIsNone(payload["amount"])

    def test_impuestos_jamas_se_autoaplican(self):
        # Una categoría inferida por el LLM no es autorización humana para
        # gravar: el neto debe ser igual al monto dicho por el usuario.
        for categoria in ("Servicios", "Infraestructura", "Alimentación"):
            p, _ = bot_driver.build_payload({"category": categoria, "amount": 1}, "P")
            self.assertFalse(p["apply_iva"], categoria)
            self.assertFalse(p["apply_gmf"], categoria)

    def test_tercero_explicito_se_conserva(self):
        parsed = {"third_party": {"identification_type": "CC",
                                  "identification_number": "123", "name": "Juan"}}
        payload, inferred = bot_driver.build_payload(parsed, "P")
        self.assertEqual(payload["third_party"]["name"], "Juan")
        self.assertEqual(payload["third_party"]["identification_type"], "CC")
        self.assertNotIn("third_party", inferred)


class TestComputeMissing(unittest.TestCase):

    def test_faltantes(self):
        self.assertEqual(bot_driver.compute_missing({"amount": None, "concept": ""}),
                         ["monto", "concepto"])
        self.assertEqual(bot_driver.compute_missing({"amount": 0, "concept": "x"}), ["monto"])
        self.assertEqual(bot_driver.compute_missing({"amount": 10, "concept": "x"}), [])


class TestRenderSummary(unittest.TestCase):

    def _payload(self):
        return {
            "type": "GASTO", "amount": 45000, "concept": "ALMUERZO CON JUAN",
            "category": "Alimentación", "payment_method": "Efectivo",
            "third_party": {"identification_type": "NIT",
                            "identification_number": "999999999", "name": "Sin especificar"},
            "transaction_date": "2026-08-09", "portfolio_name": "Personal",
        }

    def test_resumen_contiene_id_y_acciones(self):
        texto = bot_driver.render_summary(42, self._payload(), ["payment_method"], [])
        self.assertIn("BORRADOR #42", texto)
        self.assertIn("Confirmar #42", texto)
        self.assertIn("Descartar #42", texto)
        self.assertIn("$45.000", texto)
        self.assertIn("Pago: Efectivo (inferido)", texto)
        self.assertNotIn("⚠ Falta", texto)

    def test_resumen_muestra_faltantes(self):
        texto = bot_driver.render_summary(7, self._payload(), [], ["monto"])
        self.assertIn("⚠ Falta: monto", texto)


class TestFmtMoney(unittest.TestCase):

    def test_formato_cop(self):
        self.assertEqual(bot_driver._fmt_money(45000), "$45.000")
        self.assertEqual(bot_driver._fmt_money(1234567.89), "$1.234.568")
        self.assertEqual(bot_driver._fmt_money(None), "$?")


if __name__ == "__main__":
    unittest.main()
