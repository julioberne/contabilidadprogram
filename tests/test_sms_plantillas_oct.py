# -*- coding: utf-8 -*-
"""Plantillas de SMS agregadas el 9-oct-2026 y botón 💳 Cuenta (tests puros).

Muestras REALES de la BD (bot_messages, remitente 85540), tal como llegaron:
  · Bre-B a una llave con el nombre del destinatario (8 SMS entre el 30-sep y
    el 8-oct que caían en «plantilla nueva»)
  · pago por Botón Bancolombia · retiro en cajero · ahorro a un bolsillo
y la publicidad con «$» que MacroDroid reenvía con el mismo remitente.
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import bot_driver          # noqa: E402
import bot_sms             # noqa: E402
import sms_bancolombia as sms  # noqa: E402
import terceros_cuentas    # noqa: E402
from tests.test_bot_sms import _FakeCursor  # noqa: E402

BRE_B = ("Bancolombia: ANDRES, transferiste $70,000.00 a la llave 6550482 desde tu cuenta *3037 "
         "a DIDLEXYS MELEANNY VILLASMIL DOMINGUEZ el 08/10/26 a las 12:11. Con Bre-b es de una y "
         "gratis. Dudas al 018000912345.")
BRE_B_ARROBA = ("Bancolombia: ANDRES, transferiste $1,428,000.00 a la llave @9010085432 desde tu "
                "cuenta *3037 a GRUPO EMPRESARIAL VITRINA S A S el 06/10/26 a las 10:47. Con Bre-b "
                "es de una y gratis. Dudas al 018000912345.")
BOTON = ("Bancolombia: Transferiste $12,100.00 por Boton Bancolombia a CAMARA DE COMERCIO DE BOGOTA "
         "desde producto *3037. 09/10/2026 11:03:17 ¿Dudas? 018000931987.")
RETIRO = ("Bancolombia: Retiraste $500.000,00 en CAR_GALERIA de tu T.Deb **5379 el 03/10/2026 a "
          "las 03:51. Si tienes dudas, llamanos al 6045109095. Estamos cerca")
BOLSILLO = ("Bancolombia: ANDRES, tu ahorro de $400.000 ya lo tienes en tu bolsillo Personal de tu "
            "cuenta de ahorros *3037, el 01/10/2026 a las 07:33. Vas muy bien. ¿Dudas? Llamanos al "
            "6045109095.")
PUBLICIDAD = ("Con pereza de cocinar? Pide en Cali Mio  Pollo asado + Papa Salada x solo $49.000 "
              "aqui indll.io/W3QMN .Vig31Oct26.AplicanC&R")
FACTURA = ("Hola ANDRES JULIAN DIAZ BERNATE Sabemos que las mejores conversaciones no deberian tener "
           "pausa Sigue conectado con quien quieras pagando tu factura pospago Claro 573136994026  "
           "aqui Ref pago 1353428183 por $ 82576 Si pagaste omite este mensaje")

CUENTAS = [
    {"id": 2, "name": "Bancolombia Ahorros 3037 julian", "last4_cuenta": "3037", "last4_tarjeta": None},
    {"id": 16, "name": "Bancolombia T.Deb 5379", "last4_cuenta": None, "last4_tarjeta": "5379"},
]


class TestParser(unittest.TestCase):

    def test_bre_b_llave_con_nombre(self):
        d = sms.parsear(BRE_B)
        self.assertEqual(d["familia"], "transferencia_llave")
        self.assertEqual((d["amount"], d["fecha"], d["hora"]), (70000.0, "2026-10-08", "12:11"))
        self.assertEqual((d["origen_last4"], d["destino"]), ("3037", "6550482"))
        self.assertEqual(d["contraparte_nombre"], "DIDLEXYS MELEANNY VILLASMIL DOMINGUEZ")
        self.assertEqual((d["tipo_sugerido"], d["tipo_inferido"]), ("GASTO", True))

    def test_bre_b_llave_alfanumerica(self):
        d = sms.parsear(BRE_B_ARROBA)
        self.assertEqual((d["destino"], d["amount"]), ("@9010085432", 1428000.0))
        self.assertEqual(d["contraparte_nombre"], "GRUPO EMPRESARIAL VITRINA S A S")

    def test_pago_boton_bancolombia(self):
        d = sms.parsear(BOTON)
        self.assertEqual(d["familia"], "pago_boton")
        self.assertEqual((d["amount"], d["fecha"], d["hora"]), (12100.0, "2026-10-09", "11:03"))
        self.assertEqual((d["origen_last4"], d["origen_campo"]), ("3037", "last4_cuenta"))
        self.assertEqual(d["contraparte_nombre"], "CAMARA DE COMERCIO DE BOGOTA")
        self.assertEqual((d["tipo_sugerido"], d["tipo_inferido"]), ("GASTO", False))

    def test_retiro_es_gasto_desde_la_tarjeta(self):
        d = sms.parsear(RETIRO)
        self.assertEqual(d["familia"], "retiro_cajero")
        self.assertEqual((d["amount"], d["fecha"], d["hora"]), (500000.0, "2026-10-03", "03:51"))
        self.assertEqual((d["origen_last4"], d["origen_campo"]), ("5379", "last4_tarjeta"))
        self.assertEqual((d["tipo_sugerido"], d["lugar"]), ("GASTO", "CAR_GALERIA"))
        self.assertIsNone(d["contraparte_nombre"])

    def test_ahorro_bolsillo_es_traslado(self):
        d = sms.parsear(BOLSILLO)
        self.assertEqual(d["familia"], "ahorro_bolsillo")
        self.assertEqual((d["amount"], d["fecha"]), (400000.0, "2026-10-01"))
        self.assertEqual((d["origen_last4"], d["bolsillo"]), ("3037", "Personal"))
        self.assertEqual((d["tipo_sugerido"], d["tipo_inferido"]), ("TRANSFERENCIA", False))

    def test_las_familias_viejas_no_cambian(self):
        viejo = ("Bancolombia: Transferiste $5,000.00 desde tu cuenta *3037 a la cuenta *3193301184 "
                 "el 01/10/26 a las 20:06. ¿Dudas? Llamanos al 018000931987. Estamos cerca.")
        self.assertEqual(sms.parsear(viejo)["familia"], "transferencia_enviada")

    def test_publicidad_no_es_del_banco(self):
        for texto in (PUBLICIDAD, FACTURA):
            self.assertIsNone(sms.parsear(texto))
            self.assertTrue(sms.tiene_dinero(texto))
            self.assertFalse(sms.es_del_banco(texto))
        self.assertTrue(sms.es_del_banco(BOTON))


class TestMedios(unittest.TestCase):

    def test_medio_de_cada_familia(self):
        self.assertEqual(terceros_cuentas.medio_de_sms(sms.parsear(BRE_B)), ("llave", "6550482"))
        self.assertEqual(terceros_cuentas.medio_de_sms(sms.parsear(BOTON)),
                         ("nombre_banco", "CAMARA DE COMERCIO DE BOGOTA"))
        self.assertIsNone(terceros_cuentas.medio_de_sms(sms.parsear(RETIRO)))
        self.assertIsNone(terceros_cuentas.medio_de_sms(sms.parsear(BOLSILLO)))


class TestBorradores(unittest.TestCase):

    def test_bre_b_sin_llave_registrada_cae_al_nombre_exacto(self):
        terceros = [{"type": "CC", "number": "52111222", "name": "Didlexys Meleanny Villasmil Dominguez",
                     "phone": None}]
        cur = _FakeCursor(portfolios=("Negocio A",), accounts=CUENTAS, terceros=terceros)
        res = bot_sms.construir_borrador_sms(cur, BRE_B, "85540", "Negocio A")
        p = res["payload"]
        self.assertEqual(p["third_party"]["identification_number"], "52111222")
        self.assertFalse(res["tercero_por_medio"])
        self.assertEqual(p["sms"]["medio"], {"tipo": "llave", "valor": "6550482"})   # 💾 ofrecerá guardarla
        self.assertEqual(p["concept"],
                         "Transferencia Bre-B a DIDLEXYS MELEANNY VILLASMIL DOMINGUEZ (llave 6550482) "
                         "desde *3037 (SMS)")
        self.assertEqual(p["account_id"], 2)

    def test_bre_b_con_llave_registrada_manda_la_llave(self):
        medios = [{"tipo": "llave", "valor": "6550482", "tercero": (9, "CC", "777", "Didi Villasmil", None)}]
        cur = _FakeCursor(portfolios=("Negocio A",), accounts=CUENTAS, medios=medios)
        res = bot_sms.construir_borrador_sms(cur, BRE_B, "85540", "Negocio A")
        self.assertTrue(res["tercero_por_medio"])

    def test_retiro_resuelve_la_tarjeta(self):
        cur = _FakeCursor(portfolios=("Negocio A",), accounts=CUENTAS)
        p = bot_sms.construir_borrador_sms(cur, RETIRO, "85540", "Negocio A")["payload"]
        self.assertEqual((p["type"], p["account_id"], p["amount"]), ("GASTO", 16, 500000.0))
        self.assertEqual(p["concept"], "Retiro en cajero CAR_GALERIA con T.Deb *5379 (SMS)")
        self.assertEqual(p["missing_fields"], [])

    def test_bolsillo_pide_cuenta_destino(self):
        cur = _FakeCursor(portfolios=("Negocio A",), accounts=CUENTAS)
        res = bot_sms.construir_borrador_sms(cur, BOLSILLO, "85540", "Negocio A")
        p = res["payload"]
        self.assertEqual((p["type"], p["account_id"], p["dest_account_id"]), ("TRANSFERENCIA", 2, None))
        self.assertIn("cuenta destino", p["missing_fields"])
        self.assertIn("bolsillo «Personal»", bot_sms.encabezado_sms(res))
        self.assertIn("Destino: — (elígela con 💳 Cuenta)", bot_driver.render_summary(1, p))

    def test_publicidad_no_genera_borrador(self):
        cur = _FakeCursor(portfolios=("Negocio A",), accounts=CUENTAS)
        for texto in (PUBLICIDAD, FACTURA):
            res = bot_sms.construir_borrador_sms(cur, texto, "85540", "Negocio A")
            self.assertTrue(res["informativo"], texto[:30])
            self.assertFalse(res["plantilla_nueva"])

    def test_plantilla_desconocida_del_banco_sigue_entrando(self):
        texto = "Bancolombia: Pagaste $30.000 a EMPRESA X desde tu cuenta *3037 el 09/10/2026."
        cur = _FakeCursor(portfolios=("Negocio A",), accounts=CUENTAS)
        res = bot_sms.construir_borrador_sms(cur, texto, "85540", "Negocio A")
        self.assertTrue(res["plantilla_nueva"])
        self.assertFalse(res["informativo"])


class TestBotonCuenta(unittest.TestCase):

    def test_botonera_lleva_cuenta_y_cabe(self):
        filas = bot_driver._botones_borrador(123456)
        datas = [d for fila in filas for _, d in fila]
        self.assertIn("acc:123456", datas)
        for extra in ("accsel:123456:d", "accset:123456:d:999999", "accno:123456", "accback:123456"):
            self.assertLessEqual(len(extra.encode()), 64)

    def test_faltantes_de_cuentas(self):
        base = {"amount": 1000, "concept": "x"}
        self.assertEqual(bot_driver._faltantes({**base, "payment_method": "Efectivo"}), [])
        self.assertEqual(bot_driver._faltantes({**base, "payment_method": ""}), ["cuenta"])
        self.assertEqual(bot_driver._faltantes({**base, "account_id": 2, "type": "TRANSFERENCIA"}),
                         ["cuenta destino"])
        self.assertEqual(bot_driver._faltantes({**base, "account_id": 2, "type": "TRANSFERENCIA",
                                                "dest_account_id": 5}), [])

    def test_resumen_de_traslado_muestra_destino(self):
        p = {"type": "TRANSFERENCIA", "amount": 400000, "concept": "Ahorro", "category": "Otros Gastos",
             "payment_method": "Bancolombia Ahorros 3037 julian", "dest_account_name": "Bolsillo Personal",
             "third_party": {"name": "Sin especificar", "identification_type": "NIT",
                             "identification_number": "999999999"},
             "transaction_date": "2026-10-01", "portfolio_name": "Negocio A"}
        lineas = bot_driver.render_summary(3, p).splitlines()
        self.assertEqual(lineas[lineas.index("Pago: Bancolombia Ahorros 3037 julian") + 1],
                         "Destino: Bolsillo Personal")


if __name__ == "__main__":
    unittest.main()
