# -*- coding: utf-8 -*-
"""Tests de los resolvedores deterministas del bot (portafolio y método de pago).

Cubren el bug real detectado en la primera prueba end-to-end: "pagué desde
Bancolombia" quedaba como Efectivo porque el prompt de ai_engine lista métodos
genéricos ("Banco M", "Tarjeta C") ajenos a las cuentas de esta instalación.
Lo que el usuario DIJO manda sobre lo que el LLM propuso.
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import bot_driver  # noqa: E402


class _FakeCursor:
    """Cursor mínimo: devuelve filas fijas según la tabla consultada."""

    def __init__(self, portfolios=(), accounts=()):
        self._portfolios = [(p,) for p in portfolios]
        self._accounts = [(a,) for a in accounts]
        self._rows = []

    def execute(self, sql, params=None):
        self._rows = self._portfolios if "portfolios" in sql else self._accounts

    def fetchall(self):
        return self._rows


CUENTAS_REALES = ("Efectivo", "Bancolombia Ahorros", "Nequi",
                  "Davivienda Crédito", "Binance USDT")
PORTAFOLIOS_REALES = ("Negocio A", "EMPRESA INFANTIL PEGASUS", "MI EMPRESA",
                      "Negocio Principal")


class TestResolverMetodoPago(unittest.TestCase):

    def _cur(self):
        return _FakeCursor(accounts=CUENTAS_REALES)

    def test_lo_dicho_por_el_usuario_gana_sobre_el_llm(self):
        # El caso real: el LLM propuso "Efectivo" pero el usuario dijo Bancolombia
        metodo, explicito = bot_driver._resolver_metodo_pago(
            self._cur(), "Gasté 50.000 en almuerzo con Juan, pagué desde Bancolombia", "Efectivo")
        self.assertEqual(metodo, "Bancolombia Ahorros")
        self.assertTrue(explicito)

    def test_palabra_distintiva_sin_tildes(self):
        metodo, explicito = bot_driver._resolver_metodo_pago(
            self._cur(), "pagué con la davivienda", "Efectivo")
        self.assertEqual(metodo, "Davivienda Crédito")
        self.assertTrue(explicito)

    def test_nequi(self):
        metodo, explicito = bot_driver._resolver_metodo_pago(
            self._cur(), "mandé 30 mil por Nequi", "Banco M")
        self.assertEqual(metodo, "Nequi")
        self.assertTrue(explicito)

    def test_sin_mencion_usa_sugerencia_del_llm_si_es_cuenta_real(self):
        metodo, explicito = bot_driver._resolver_metodo_pago(
            self._cur(), "almuerzo 20.000", "Efectivo")
        self.assertEqual(metodo, "Efectivo")
        self.assertFalse(explicito)   # inferido, no dicho

    def test_sugerencia_generica_del_prompt_no_inventa_cuenta(self):
        metodo, explicito = bot_driver._resolver_metodo_pago(
            self._cur(), "almuerzo 20.000", "Tarjeta C")
        self.assertFalse(explicito)
        self.assertIn(metodo, list(CUENTAS_REALES) + ["Tarjeta C"])

    def test_sin_cuentas_devuelve_la_sugerencia(self):
        metodo, explicito = bot_driver._resolver_metodo_pago(
            _FakeCursor(accounts=()), "pagué con Bancolombia", "Efectivo")
        self.assertEqual(metodo, "Efectivo")
        self.assertFalse(explicito)


class TestResolverPortafolio(unittest.TestCase):

    def _cur(self):
        return _FakeCursor(portfolios=PORTAFOLIOS_REALES)

    def test_portafolio_existente_se_respeta(self):
        nombre, corregido = bot_driver._resolver_portafolio(self._cur(), "MI EMPRESA")
        self.assertEqual(nombre, "MI EMPRESA")
        self.assertFalse(corregido)

    def test_inexistente_cae_al_principal_y_se_marca(self):
        # El bug real: default 'Personal' no existía y bloqueaba la confirmación
        nombre, corregido = bot_driver._resolver_portafolio(self._cur(), "Personal")
        self.assertEqual(nombre, "Negocio A")
        self.assertTrue(corregido)

    def test_match_sin_distinguir_mayusculas_ni_tildes(self):
        nombre, corregido = bot_driver._resolver_portafolio(self._cur(), "mi empresa")
        self.assertEqual(nombre, "MI EMPRESA")
        self.assertFalse(corregido)

    def test_sin_portafolios(self):
        nombre, _ = bot_driver._resolver_portafolio(_FakeCursor(portfolios=()), "X")
        self.assertIsNone(nombre)


if __name__ == "__main__":
    unittest.main()
