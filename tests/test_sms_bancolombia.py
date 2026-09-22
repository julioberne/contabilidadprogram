# -*- coding: utf-8 -*-
"""Tests del parser puro de SMS de Bancolombia (etapa 09.F, CA-09F-01/02).

Sin BD ni red. Las muestras son SMS reales del 21-sep-2026 (remitente 85540)
con montos y cuentas tal como llegaron al teléfono de Andrés.
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import sms_bancolombia as sms  # noqa: E402

MUESTRA_1 = ("Bancolombia: Transferiste $11,900.00 desde tu cuenta *3037 a la cuenta "
             "*3193301184 el 21/09/26 a las 20:00. ¿Dudas? Llamanos al 018000931987. "
             "Estamos cerca.")
MUESTRA_2 = ("Bancolombia: Transferiste $2,500.00 desde tu cuenta *3037 a la cuenta "
             "*3114452993 el 21/09/26 a las 21:44. ¿Dudas? Llamanos al 018000931987. "
             "Estamos cerca.")
MUESTRA_3 = ("Bancolombia: Transferiste $4,530,000 desde tu cuenta *3037 a la cuenta "
             "*91232656625 el 21/09/2026 a las 17:24. ¿Dudas? Llamanos al 018000931987. "
             "Estamos cerca.")


class TestTransferiste(unittest.TestCase):

    def test_transferiste_muestra_1_con_decimales(self):          # CA-09F-01
        r = sms.parsear(MUESTRA_1)
        self.assertIsNotNone(r)
        self.assertEqual(r["familia"], "transferencia_enviada")
        self.assertEqual(r["amount"], 11900.0)
        self.assertEqual(r["currency"], "COP")
        self.assertEqual(r["origen_last4"], "3037")
        self.assertEqual(r["destino"], "3193301184")
        self.assertEqual(r["destino_last4"], "1184")
        self.assertTrue(r["destino_es_celular"])
        self.assertEqual(r["fecha"], "2026-09-21")
        self.assertEqual(r["hora"], "20:00")
        self.assertEqual(r["tipo_sugerido"], "GASTO")
        self.assertEqual(r["raw"], MUESTRA_1)

    def test_transferiste_muestra_2(self):
        r = sms.parsear(MUESTRA_2)
        self.assertEqual(r["amount"], 2500.0)
        self.assertEqual(r["destino"], "3114452993")
        self.assertEqual(r["hora"], "21:44")

    def test_transferiste_muestra_3_sin_decimales_anio_4_digitos(self):
        r = sms.parsear(MUESTRA_3)
        self.assertEqual(r["amount"], 4530000.0)
        self.assertEqual(r["fecha"], "2026-09-21")
        self.assertEqual(r["destino"], "91232656625")
        self.assertEqual(r["destino_last4"], "6625")
        self.assertFalse(r["destino_es_celular"])

    def test_sin_prefijo_bancolombia_ni_hora(self):
        r = sms.parsear("Transferiste $10,000.00 desde tu cuenta *3037 a la cuenta *1234 el 1/2/26.")
        self.assertIsNotNone(r)
        self.assertEqual(r["amount"], 10000.0)
        self.assertEqual(r["fecha"], "2026-02-01")
        self.assertIsNone(r["hora"])

    def test_moneda_usd(self):
        r = sms.parsear("Bancolombia: Transferiste USD 25.50 desde tu cuenta *3037 a la cuenta *9999 el 21/09/26 a las 10:00.")
        self.assertEqual(r["currency"], "USD")
        self.assertEqual(r["amount"], 25.5)


class TestNoReconocido(unittest.TestCase):

    def test_no_reconocido_devuelve_none(self):                    # CA-09F-02
        self.assertIsNone(sms.parsear("Bancolombia: Compraste $45,000.00 en EXITO con tu T.Deb *1234 el 21/09/26."))
        self.assertIsNone(sms.parsear("Tu código de verificación es 123456"))
        self.assertIsNone(sms.parsear(""))
        self.assertIsNone(sms.parsear(None))

    def test_familias_es_tabla_extensible(self):
        for nombre, rx, builder in sms.FAMILIAS:
            self.assertIsInstance(nombre, str)
            self.assertTrue(hasattr(rx, "search"))
            self.assertTrue(callable(builder))


class TestNormalizadores(unittest.TestCase):

    def test_monto_formatos(self):
        self.assertEqual(sms.normalizar_monto("11,900.00"), 11900.0)
        self.assertEqual(sms.normalizar_monto("4,530,000"), 4530000.0)
        self.assertEqual(sms.normalizar_monto("1.234,56"), 1234.56)
        self.assertEqual(sms.normalizar_monto("11,900"), 11900.0)
        self.assertEqual(sms.normalizar_monto("1.500"), 1500.0)
        self.assertEqual(sms.normalizar_monto("2,50"), 2.5)
        self.assertEqual(sms.normalizar_monto("12345.67"), 12345.67)
        self.assertEqual(sms.normalizar_monto("500"), 500.0)
        self.assertIsNone(sms.normalizar_monto(""))
        self.assertIsNone(sms.normalizar_monto("abc"))

    def test_fecha_dos_y_cuatro_digitos(self):
        self.assertEqual(sms.normalizar_fecha("21/09/26"), "2026-09-21")
        self.assertEqual(sms.normalizar_fecha("21/09/2026"), "2026-09-21")
        self.assertEqual(sms.normalizar_fecha("1/2/26"), "2026-02-01")

    def test_fecha_invalida_devuelve_none(self):
        self.assertIsNone(sms.normalizar_fecha("31/02/26"))
        self.assertIsNone(sms.normalizar_fecha("2026-09-21"))
        self.assertIsNone(sms.normalizar_fecha(""))

    def test_es_celular(self):
        self.assertTrue(sms.es_celular("3193301184"))
        self.assertFalse(sms.es_celular("91232656625"))
        self.assertFalse(sms.es_celular("1184"))
        self.assertFalse(sms.es_celular("4193301184"))


if __name__ == "__main__":
    unittest.main()
