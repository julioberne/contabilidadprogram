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


COMPRA_1 = ("Bancolombia: Compraste $7.000,00 en Didi con tu T.Deb *1775, el 23/09/2026 a las 10:35. "
            "Si tienes dudas, encuentranos aqui: 6045109095 o 018000931987. Estamos cerca.")
COMPRA_2 = ("Bancolombia: Compraste $759.600,00 en ONLY 3 con tu T.Deb *5379, el 26/09/2026 a las 16:07. "
            "Si tienes dudas, encuentranos aqui: 6045109095 o 018000931987. Estamos cerca.")
RECIBIDA = ("Bancolombia: Recibiste una transferencia por $1,696,000 de SANDRA JIMENEZ en tu cuenta "
            "**3037, el 26/09/2026 a las 16:40. Si tienes dudas, hablemos: 018000931987. Siempre a tu lado.")
PAGO_QR = ("Bancolombia: ANDRES JULIAN DIAZ BERNATE pagaste $30,000.00 por codigo QR desde tu cuenta "
           "*3037 a la llave 0087671656 el 26/09/2026 a las 17:52. Con codigo QR es facil y de una. "
           "Dudas al 018000912345.")


class TestFamiliasNuevas(unittest.TestCase):
    """Muestras reales del 23–29 sep 2026 (captura de Andrés del 30-sep)."""

    def test_compra_tarjeta_debito_formato_europeo(self):
        r = sms.parsear(COMPRA_1)
        self.assertEqual(r["familia"], "compra_tarjeta")
        self.assertEqual(r["tipo_sugerido"], "GASTO")
        self.assertFalse(r["tipo_inferido"])
        self.assertEqual(r["amount"], 7000.0)
        self.assertEqual(r["origen_last4"], "1775")
        self.assertEqual(r["origen_campo"], "last4_tarjeta")
        self.assertEqual(r["tarjeta_tipo"], "debito")
        self.assertEqual(r["contraparte_nombre"], "Didi")
        self.assertEqual((r["fecha"], r["hora"]), ("2026-09-23", "10:35"))
        self.assertIsNone(r["destino"])

    def test_compra_comercio_con_espacios_y_otra_tarjeta(self):
        r = sms.parsear(COMPRA_2)
        self.assertEqual(r["amount"], 759600.0)
        self.assertEqual(r["contraparte_nombre"], "ONLY 3")
        self.assertEqual(r["origen_last4"], "5379")

    def test_compra_credito_en_dolares_sin_coma_antes_de_el(self):
        r = sms.parsear("Bancolombia: Compraste USD1,00 en LOUNGEKEY con tu T.Cred *7706 el 22/08/26 a las 10:53.")
        self.assertEqual(r["familia"], "compra_tarjeta")
        self.assertEqual((r["currency"], r["amount"], r["tarjeta_tipo"]), ("USD", 1.0, "credito"))

    def test_transferencia_recibida_es_ingreso_con_remitente(self):
        r = sms.parsear(RECIBIDA)
        self.assertEqual(r["familia"], "transferencia_recibida")
        self.assertEqual(r["tipo_sugerido"], "INGRESO")
        self.assertFalse(r["tipo_inferido"])
        self.assertEqual(r["amount"], 1696000.0)
        self.assertEqual(r["contraparte_nombre"], "SANDRA JIMENEZ")
        self.assertEqual((r["origen_last4"], r["origen_campo"]), ("3037", "last4_cuenta"))
        self.assertEqual((r["fecha"], r["hora"]), ("2026-09-26", "16:40"))

    def test_pago_qr_a_llave(self):
        r = sms.parsear(PAGO_QR)
        self.assertEqual(r["familia"], "pago_qr")
        self.assertEqual(r["tipo_sugerido"], "GASTO")
        self.assertFalse(r["tipo_inferido"])
        self.assertEqual(r["amount"], 30000.0)
        self.assertEqual(r["origen_last4"], "3037")
        self.assertEqual(r["destino"], "0087671656")
        self.assertFalse(r["destino_es_celular"])
        self.assertEqual((r["fecha"], r["hora"]), ("2026-09-26", "17:52"))

    def test_pago_qr_a_llave_celular(self):
        r = sms.parsear("Bancolombia: JUAN pagaste $23,000.00 por codigo QR desde tu cuenta *3037 "
                        "a la llave 3001234567 el 29/09/26 a las 23:40.")
        self.assertTrue(r["destino_es_celular"])

    def test_transferiste_sigue_inferido_y_con_contrato_completo(self):
        r = sms.parsear(MUESTRA_1)
        self.assertTrue(r["tipo_inferido"])
        self.assertEqual(r["origen_campo"], "last4_cuenta")
        self.assertIsNone(r["contraparte_nombre"])

    # ── Captura del 30-sep (SMS de agosto 2026) ──

    def test_recibida_variante_llave_nombre_antes_del_monto(self):
        r = sms.parsear("Bancolombia: Andres, recibiste una transferencia de LEIDY DANIELA MOLINA "
                        "MARTINEZ por $505,000.00 en tu cuenta *3037 conectada a la llave 1007365480 "
                        "el 10/08/26 a las 19:41. Con llaves es de una y gratis. Dudas al 018000912345.")
        self.assertEqual(r["familia"], "transferencia_recibida")
        self.assertEqual(r["tipo_sugerido"], "INGRESO")
        self.assertEqual(r["amount"], 505000.0)
        self.assertEqual(r["contraparte_nombre"], "LEIDY DANIELA MOLINA MARTINEZ")
        self.assertEqual(r["origen_last4"], "3037")
        self.assertEqual(r["mi_llave"], "1007365480")
        self.assertEqual((r["fecha"], r["hora"]), ("2026-08-10", "19:41"))

    def test_recibida_clasica_otro_remitente(self):
        r = sms.parsear("Bancolombia: Recibiste una transferencia por $398,000 de CAROLL HUERTAS en tu "
                        "cuenta **3037, el 19/08/2026 a las 11:37. Si tienes dudas, hablemos: 018000931987.")
        self.assertEqual((r["amount"], r["contraparte_nombre"]), (398000.0, "CAROLL HUERTAS"))
        self.assertNotIn("mi_llave", r)

    def test_transferiste_cuenta_origen_sin_asterisco(self):
        r = sms.parsear("Bancolombia: Transferiste $60,000.00 desde tu cuenta 3037 a la cuenta "
                        "*3214892005 el 12/08/2026 a las 17:46. ¿Dudas? Llamanos al 018000931987.")
        self.assertEqual((r["amount"], r["origen_last4"], r["destino"]), (60000.0, "3037", "3214892005"))
        self.assertTrue(r["destino_es_celular"])

    def test_compra_de_agosto(self):
        r = sms.parsear("Bancolombia: Compraste $66.200,00 en MERCA EXPRESS RP con tu T.Deb *5379, el "
                        "12/08/2026 a las 20:38. Si tienes dudas, encuentranos aqui: 6045109095.")
        self.assertEqual((r["amount"], r["contraparte_nombre"], r["origen_last4"]),
                         (66200.0, "MERCA EXPRESS RP", "5379"))


class TestRedDeSeguridad(unittest.TestCase):
    """R-09F-13: qué pasa cuando el banco cambia una plantilla o llega una nueva."""

    INFORMATIVO = ("Bancolombia: Muy bien. Inscribiste la cuenta de un tercero desde APP Bancolombia. "
                   "Si no fuiste tu, llamanos ahora: 6045109095 o 018000931987. Juntos en cada paso.")
    DESCONOCIDO_CON_DINERO = ("Bancolombia: Retiraste $200.000,00 en CAJERO CC ANDINO de tu T.Deb *5379 "
                              "el 01/10/2026 a las 09:15. Dudas: 018000931987.")

    def test_informativo_sin_dinero_no_es_movimiento(self):
        self.assertIsNone(sms.parsear(self.INFORMATIVO))
        self.assertFalse(sms.tiene_dinero(self.INFORMATIVO))       # los teléfonos no son dinero
        self.assertFalse(sms.tiene_dinero("Tu clave dinamica es 123456"))

    def test_tiene_dinero(self):
        self.assertTrue(sms.tiene_dinero("pagaste $30,000.00 por"))
        self.assertTrue(sms.tiene_dinero("por COP 50.000 en"))
        self.assertTrue(sms.tiene_dinero("Compraste USD1,00 en"))

    def test_plantilla_desconocida_con_dinero_lectura_literal(self):
        self.assertIsNone(sms.parsear(self.DESCONOCIDO_CON_DINERO))   # sin muestra real, sin familia
        g = sms.extraer_generico(self.DESCONOCIDO_CON_DINERO)
        self.assertEqual(g["amount"], 200000.0)
        self.assertEqual(g["fecha"], "2026-10-01")
        self.assertEqual(g["hora"], "09:15")
        self.assertEqual(g["last4_candidatos"], ["5379"])

    def test_generico_ignora_numeros_largos_enmascarados_y_fechas_invalidas(self):
        g = sms.extraer_generico("Algo por $5,000 a la cuenta *3214892005 y *3037 el 45/13/26 o 02/10/26.")
        self.assertEqual(g["last4_candidatos"], ["3037"])
        self.assertEqual(g["fecha"], "2026-10-02")
        self.assertIsNone(g["hora"])

    def test_generico_sin_nada(self):
        g = sms.extraer_generico("hola")
        self.assertEqual((g["amount"], g["fecha"], g["last4_candidatos"]), (None, None, []))


class TestNoReconocido(unittest.TestCase):

    def test_no_reconocido_devuelve_none(self):                    # CA-09F-02
        self.assertIsNone(sms.parsear("Bancolombia te informa: tu clave dinamica fue generada el 21/09/26."))
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
