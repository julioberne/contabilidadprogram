# -*- coding: utf-8 -*-
"""Tests del plan de pagos de cartera (Fase 1) — funciones puras, sin BD."""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fin_sys_core"))

from cartera_plan import dividir_abono, interes_devengado, plan_info  # noqa: E402

HOY = date(2026, 9, 3)


class TestPlanInfo(unittest.TestCase):
    def test_sin_plan_devuelve_none(self):
        row = {"min_payment": None, "interest_rate": None,
               "remaining_balance": 100, "start_date": HOY, "payment_frequency": 30}
        self.assertIsNone(plan_info(row, 0, None, HOY))

    def test_en_mora_por_cuota_incumplida(self):
        # 65 días desde el inicio a cortes de 30d = 2 cortes cumplidos → exige 2M
        row = {"min_payment": 1_000_000, "interest_rate": None,
               "remaining_balance": 5_000_000,
               "start_date": date(2026, 6, 30), "payment_frequency": 30}
        info = plan_info(row, 1_500_000, None, HOY)
        self.assertEqual(info["cortes_cumplidos"], 2)
        self.assertEqual(info["cuota_exigida"], 2_000_000)
        self.assertTrue(info["en_mora"])
        # Con 2M abonados queda al día
        self.assertFalse(plan_info(row, 2_000_000, None, HOY)["en_mora"])

    def test_al_dia_sin_cortes_cumplidos(self):
        row = {"min_payment": 1_000_000, "interest_rate": None,
               "remaining_balance": 5_000_000, "start_date": date(2026, 8, 20),
               "payment_frequency": 30}
        info = plan_info(row, 0, None, HOY)
        self.assertEqual(info["cuota_exigida"], 0)
        self.assertFalse(info["en_mora"])
        self.assertEqual(info["proximo_corte"], "2026-09-19")

    def test_saldada_no_esta_en_mora(self):
        row = {"min_payment": 1_000_000, "interest_rate": None,
               "remaining_balance": 0, "start_date": date(2026, 1, 1),
               "payment_frequency": 30}
        self.assertFalse(plan_info(row, 0, None, HOY)["en_mora"])


class TestInteres(unittest.TestCase):
    def test_prorrateo_mensual(self):
        # 2% mensual sobre 3M durante 15 días = 3M * 0.02/30 * 15 = 30.000
        monto, dias = interes_devengado(3_000_000, 2, "MENSUAL", date(2026, 8, 19), HOY)
        self.assertEqual(dias, 15)
        self.assertAlmostEqual(monto, 30_000, places=2)

    def test_dividir_abono_sin_tasa_todo_capital(self):
        i, p, saldo = dividir_abono(400_000, 1_000_000, None, None, None, HOY)
        self.assertEqual((i, p, saldo), (0.0, 400_000, 600_000))

    def test_dividir_abono_interes_primero(self):
        # Interés devengado 30.000 → abono de 100.000: 30k interés + 70k capital
        i, p, saldo = dividir_abono(100_000, 3_000_000, 2, "MENSUAL", date(2026, 8, 19), HOY)
        self.assertAlmostEqual(i, 30_000, places=2)
        self.assertAlmostEqual(p, 70_000, places=2)
        self.assertAlmostEqual(saldo, 2_930_000, places=2)

    def test_abono_menor_que_interes_no_amortiza(self):
        i, p, saldo = dividir_abono(10_000, 3_000_000, 2, "MENSUAL", date(2026, 8, 19), HOY)
        self.assertEqual(i, 10_000)
        self.assertEqual(p, 0)
        self.assertEqual(saldo, 3_000_000)


if __name__ == "__main__":
    unittest.main()
