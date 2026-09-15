# -*- coding: utf-8 -*-
"""Snapshot del dashboard (plan cimientos A2).

- caja_viva_desde_agregados debe dar EXACTAMENTE lo mismo que
  calculate_caja_viva sobre la lista completa de transacciones (sin BD).
- obtener_transaccion(id) debe tener las mismas claves que una fila de
  obtener_transacciones (requiere BD: se salta si no hay DB_HOST).
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# .env ANTES de importar fin_sys_core: db_pool lee DB_HOST/DB_PORT al importar.
_ENV = os.path.join(_ROOT, ".env")
if os.path.exists(_ENV):
    with open(_ENV, encoding="utf-8") as _f:
        for _line in _f:
            _ls = _line.strip()
            if _ls and not _ls.startswith("#") and "=" in _ls:
                _k, _v = _ls.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

import fin_sys_core  # noqa: E402,F401


class TestCajaVivaDesdeAgregados(unittest.TestCase):
    def test_equivale_a_la_lista_completa(self):
        from fin_sys_core.ledger_math import calculate_caja_viva
        from fin_sys_core.dashboard_query import caja_viva_desde_agregados

        txs = [
            {"type": "INGRESO", "transaction_currency": "COP", "net_value": 1000.55},
            {"type": "INGRESO", "transaction_currency": None, "net_value": 200},      # None → COP
            {"type": "GASTO", "transaction_currency": "COP", "net_value": "300.10"},  # str → float
            {"type": "GASTO", "transaction_currency": "USD", "net_value": 40},
            {"type": "INGRESO", "transaction_currency": "USD", "net_value": 15.5},
            {"type": "TRANSFERENCIA", "transaction_currency": "COP", "net_value": 999},  # se ignora
            {"type": "gasto", "transaction_currency": "COP", "net_value": None},      # None → 0
        ]
        accounts = [
            {"id": 1, "name": "Banco", "type": "Ahorros", "currency": "COP", "current_balance": 5000},
            {"id": 2, "name": "Tarjeta", "type": "Crédito", "currency": "COP", "current_balance": -2500000},
            {"id": 3, "name": "USD", "type": "Ahorros", "currency": "USD", "current_balance": -10},
        ]
        kpi = {"ingresos_cop": 1000.55 + 200, "gastos_cop": 300.10 + 0,
               "ingresos_usd": 15.5, "gastos_usd": 40}
        self.assertEqual(calculate_caja_viva(txs, accounts),
                         caja_viva_desde_agregados(kpi, accounts))

    def test_sin_cuentas_usa_capital_inicial(self):
        from fin_sys_core.ledger_math import calculate_caja_viva
        from fin_sys_core.dashboard_query import caja_viva_desde_agregados
        kpi = {"ingresos_cop": 10, "gastos_cop": 4, "ingresos_usd": 0, "gastos_usd": 0}
        txs = [{"type": "INGRESO", "transaction_currency": "COP", "net_value": 10},
               {"type": "GASTO", "transaction_currency": "COP", "net_value": 4}]
        self.assertEqual(calculate_caja_viva(txs, []), caja_viva_desde_agregados(kpi, []))


@unittest.skipUnless(os.getenv("DB_HOST") or os.path.exists(os.path.join(_ROOT, ".env")),
                     "requiere BD")
class TestFormaDeTransaccion(unittest.TestCase):
    def test_mismas_claves_que_obtener_transacciones(self):
        from fin_sys_core.database_driver import obtener_transacciones
        from fin_sys_core.dashboard_query import obtener_transaccion
        filas = obtener_transacciones(None, limit=1)["items"]
        if not filas:
            self.skipTest("sin transacciones en la BD")
        una = obtener_transaccion(filas[0]["id"])
        self.assertIsNotNone(una)
        self.assertEqual(set(una.keys()), set(filas[0].keys()))
        self.assertEqual(una["id"], filas[0]["id"])


if __name__ == "__main__":
    unittest.main()
