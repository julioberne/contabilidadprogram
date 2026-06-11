# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 - Suite de Pruebas Unitarias (test_core.py)
---------------------------------------------------------
Pruebas para verificar matemáticamente la integridad contable del tax_motor 
y la lógica de saldos del ledger_math.
"""

import os
import sys
import unittest

# Registrar el directorio actual en sys.path para importaciones locales
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tax_motor import calculate_iva, calculate_gmf, process_transaction_taxes
from ledger_math import calculate_caja_viva, validate_pocket_budget, ExcedeLimitePocketError


class TestAccountingMathCore(unittest.TestCase):

    def test_iva_calculation(self):
        """Verifica que el IVA del 19% se calcule correctamente."""
        self.assertEqual(calculate_iva(100.0), 19.0)
        self.assertEqual(calculate_iva(50000.0), 9500.0)
        self.assertEqual(calculate_iva(0.0), 0.0)
        self.assertEqual(calculate_iva(-50.0), 0.0)

    def test_gmf_calculation(self):
        """Verifica que el GMF del 4x1000 se calcule correctamente."""
        self.assertEqual(calculate_gmf(1000.0), 4.0)
        self.assertEqual(calculate_gmf(50000.0), 200.0)
        self.assertEqual(calculate_gmf(0.0), 0.0)
        self.assertEqual(calculate_gmf(-50.0), 0.0)

    def test_transaction_taxes_and_net_value(self):
        """Verifica la liquidación neta de transacciones con combinación de IVA, GMF y tasas."""
        # Caso 1: Transacción simple sin impuestos
        result1 = process_transaction_taxes(10000.0)
        self.assertEqual(result1["iva_amount"], 0.0)
        self.assertEqual(result1["gmf_amount"], 0.0)
        self.assertEqual(result1["net_value"], 10000.0)

        # Caso 2: Transacción con IVA 19% aditivo
        result2 = process_transaction_taxes(50000.0, apply_iva=True)
        self.assertEqual(result2["iva_amount"], 9500.0)
        self.assertEqual(result2["net_value"], 59500.0) # 50,000 + 9,500

        # Caso 3: Transacción con IVA 19% aditivo y GMF 4x1000 deductivo
        result3 = process_transaction_taxes(50000.0, apply_iva=True, apply_gmf=True)
        self.assertEqual(result3["iva_amount"], 9500.0)
        self.assertEqual(result3["gmf_amount"], 200.0)
        self.assertEqual(result3["net_value"], 59300.0) # 50,000 + 9,500 - 200

        # Caso 4: Impuestos y retenciones personalizados
        customs = [
            {"name": "Retención en la Fuente", "rate": 0.04, "type": "DEDUCTIVE"}, # 4%
            {"name": "Estampilla Municipal", "amount": 150.0, "type": "ADDITIVE"} # Fijo
        ]
        result4 = process_transaction_taxes(10000.0, apply_iva=True, custom_taxes=customs)
        # Base: 10,000.00
        # IVA (19%): +1,900.00
        # Estampilla (Aditiva): +150.00
        # Retencion (4% Deduc.): -400.00
        # Neto propuesto: 10,000 + 1,900 + 150 - 400 = 11,650.00
        self.assertEqual(result4["iva_amount"], 1900.0)
        self.assertEqual(result4["custom_taxes_total"], -250.0) # +150 - 400
        self.assertEqual(result4["net_value"], 11650.0)

    def test_caja_viva_aggregation(self):
        """Verifica que la sumatoria consolidada de la Caja Viva sea exacta."""
        txs = [
            {"type": "INGRESO", "net_value": 50000.0},
            {"type": "GASTO", "net_value": 15000.0},
            {"type": "TRANSFERENCIA", "net_value": 10000.0}, # Las transferencias no restan al neto global
            {"type": "INGRESO", "net_value": 70000.0},
            {"type": "GASTO", "net_value": 4500.0}
        ]
        totals = calculate_caja_viva(txs)
        # Ingresos: 50,000 + 70,000 = 120,000.0
        # Gastos: 15,000 + 4,500 = 19,500.0
        # Neto: 120,000 - 19,500 = 100,500.0
        self.assertEqual(totals["total_ingresos"], 120000.0)
        self.assertEqual(totals["total_gastos"], 19500.0)
        self.assertEqual(totals["balance_neto"], 100500.0)

    def test_pocket_limits(self):
        """Verifica la regla de aislamiento de capital y control de presupuestos (Pockets)."""
        # Presupuesto suficiente
        self.assertTrue(validate_pocket_budget(1000.0, 300.0, "Caja Menor"))
        
        # Presupuesto insuficiente: debe lanzar ExcedeLimitePocketError
        with self.assertRaises(ExcedeLimitePocketError):
            validate_pocket_budget(200.0, 250.0, "Fondo de Inversiones")


if __name__ == "__main__":
    unittest.main()
