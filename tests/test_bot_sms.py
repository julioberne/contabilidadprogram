# -*- coding: utf-8 -*-
"""Tests puros de bot_sms (etapa 09.F): resolvedores por id, mapeo al payload,
encabezado y clave de dedupe. Cursor falso, sin BD (CA-09F-02/03/04).
"""
import os
import sys
import unittest
from datetime import date

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import bot_sms  # noqa: E402

SMS_OK = ("Bancolombia: Transferiste $11,900.00 desde tu cuenta *3037 a la cuenta "
          "*3193301184 el 21/09/26 a las 20:00. ¿Dudas? Llamanos al 018000931987.")
SMS_PROPIA = ("Bancolombia: Transferiste $4,530,000 desde tu cuenta *3037 a la cuenta "
              "*91232656625 el 21/09/2026 a las 17:24.")
SMS_RARO = "Bancolombia te informa: tu clave dinamica fue generada el 21/09/26."
SMS_COMPRA = ("Bancolombia: Compraste $7.000,00 en Didi con tu T.Deb *7706, el 23/09/2026 a las 10:35. "
              "Si tienes dudas, encuentranos aqui: 6045109095 o 018000931987. Estamos cerca.")
SMS_RECIBIDA = ("Bancolombia: Recibiste una transferencia por $1,696,000 de SANDRA JIMENEZ en tu cuenta "
                "**3037, el 26/09/2026 a las 16:40. Si tienes dudas, hablemos: 018000931987.")
SMS_QR = ("Bancolombia: ANDRES JULIAN DIAZ BERNATE pagaste $30,000.00 por codigo QR desde tu cuenta "
          "*3037 a la llave 0087671656 el 26/09/2026 a las 17:52. Con codigo QR es facil y de una.")


class _FakeCursor:
    """Enruta por la tabla mencionada en el SQL. accounts: dicts con id, name,
    last4_cuenta, last4_tarjeta. terceros: dicts con type, number, name, phone."""

    def __init__(self, portfolios=("Finanzas personales",), accounts=(), terceros=(), medios=()):
        self.portfolios = list(portfolios)
        self.accounts = list(accounts)
        self.terceros = list(terceros)
        # medios de pago registrados (third_party_accounts): dicts con
        # tipo, valor y tercero = (id, type, number, name, phone)
        self.medios = list(medios)
        self._rows = []
        self.sqls = []

    def execute(self, sql, params=None):
        self.sqls.append(sql)
        if "FROM portfolios" in sql:
            self._rows = [(p,) for p in self.portfolios]
        elif "FROM third_party_accounts" in sql:
            self._rows = [m["tercero"] for m in self.medios
                          if (m["tipo"], m["valor"]) == (params[0], params[1])]
        elif "FROM user_accounts" in sql:
            campo = "last4_tarjeta" if "last4_tarjeta" in sql else "last4_cuenta"
            self._rows = [(a["id"], a["name"]) for a in self.accounts
                          if a.get(campo) == params[0]]
        elif "FROM third_parties" in sql and "lower(btrim(name))" in sql:
            buscado = params[0].lower()
            self._rows = [(t["type"], t["number"], t["name"], t["phone"])
                          for t in self.terceros
                          if t["name"].strip().lower() == buscado and t["number"] != "999999999"]
        elif "FROM third_parties" in sql:
            cel = params[0].lstrip("%")
            self._rows = [(t["type"], t["number"], t["name"], t["phone"])
                          for t in self.terceros
                          if "".join(ch for ch in (t["phone"] or "") if ch.isdigit()).endswith(cel)]
        else:
            self._rows = []

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


CUENTAS = [
    {"id": 1, "name": "Efectivo", "last4_cuenta": None, "last4_tarjeta": None},
    {"id": 2, "name": "Bancolombia Ahorros (nombre libre)", "last4_cuenta": "3037", "last4_tarjeta": "7706"},
    {"id": 3, "name": "Nequi", "last4_cuenta": None, "last4_tarjeta": None},
    {"id": 4, "name": "Bancolombia Corriente", "last4_cuenta": "6625", "last4_tarjeta": None},
]
TERCEROS = [
    {"type": "CC", "number": "10203040", "name": "Juan Pérez", "phone": "+57 319 330 1184"},
    {"type": "NIT", "number": "900123456", "name": "Tienda", "phone": None},
]


class TestResolvedores(unittest.TestCase):

    def test_cuenta_por_last4_unica_devuelve_id_y_nombre_actual(self):   # CA-09F-03
        cur = _FakeCursor(accounts=CUENTAS)
        self.assertEqual(bot_sms.resolver_cuenta_por_last4(cur, "3037"), (2, "Bancolombia Ahorros (nombre libre)"))

    def test_cuenta_por_last4_no_registrada(self):
        cur = _FakeCursor(accounts=CUENTAS)
        self.assertEqual(bot_sms.resolver_cuenta_por_last4(cur, "9999"), (None, None))

    def test_cuenta_por_last4_ambigua_devuelve_none(self):
        dobles = CUENTAS + [{"id": 9, "name": "Otra", "last4_cuenta": "3037", "last4_tarjeta": None}]
        cur = _FakeCursor(accounts=dobles)
        self.assertEqual(bot_sms.resolver_cuenta_por_last4(cur, "3037"), (None, None))

    def test_cuenta_por_tarjeta(self):
        cur = _FakeCursor(accounts=CUENTAS)
        self.assertEqual(bot_sms.resolver_cuenta_por_last4(cur, "7706", campo="last4_tarjeta")[0], 2)
        with self.assertRaises(ValueError):
            bot_sms.resolver_cuenta_por_last4(cur, "7706", campo="name")

    def test_last4_invalido_no_consulta(self):
        cur = _FakeCursor(accounts=CUENTAS)
        self.assertEqual(bot_sms.resolver_cuenta_por_last4(cur, "12"), (None, None))
        self.assertEqual(cur.sqls, [])

    def test_tercero_por_celular_con_prefijo_57(self):                    # CA-09F-04
        cur = _FakeCursor(terceros=TERCEROS)
        t = bot_sms.resolver_tercero_por_celular(cur, "3193301184")
        self.assertEqual(t["name"], "Juan Pérez")
        self.assertEqual(t["identification_number"], "10203040")

    def test_tercero_no_encontrado(self):
        cur = _FakeCursor(terceros=TERCEROS)
        self.assertIsNone(bot_sms.resolver_tercero_por_celular(cur, "3000000000"))
        self.assertIsNone(bot_sms.resolver_tercero_por_celular(cur, "1184"))


class TestConstruirBorrador(unittest.TestCase):

    def test_reconocido_con_cuenta_y_tercero(self):                       # CA-09F-03/04
        cur = _FakeCursor(accounts=CUENTAS, terceros=TERCEROS)
        res = bot_sms.construir_borrador_sms(cur, SMS_OK, "85540", "Finanzas personales")
        p = res["payload"]
        self.assertTrue(res["reconocido"])
        self.assertEqual(p["amount"], 11900.0)
        self.assertEqual(p["type"], "GASTO")
        self.assertIn("type", p["inferred_fields"])
        self.assertEqual(p["account_id"], 2)
        self.assertEqual(p["payment_method"], "Bancolombia Ahorros (nombre libre)")
        self.assertNotIn("payment_method", p["inferred_fields"])
        self.assertEqual(p["transaction_date"], "2026-09-21")
        self.assertNotIn("transaction_date", p["inferred_fields"])
        self.assertEqual(p["third_party"]["name"], "Juan Pérez")
        self.assertNotIn("third_party", p["inferred_fields"])
        self.assertEqual(p["concept"], "Transferencia Bancolombia *3037 → *1184 (SMS)")
        self.assertEqual(p["missing_fields"], [])
        self.assertEqual(p["sms"]["familia"], "transferencia_enviada")
        self.assertEqual(p["sms"]["remitente"], "85540")
        self.assertIsNone(p["dest_account_id"])

    def test_sin_cuenta_registrada_no_adivina_efectivo(self):             # CA-09F-03
        cur = _FakeCursor(accounts=[CUENTAS[0], CUENTAS[2]], terceros=TERCEROS)
        res = bot_sms.construir_borrador_sms(cur, SMS_OK, "85540", "Finanzas personales")
        p = res["payload"]
        self.assertIsNone(p["account_id"])
        self.assertEqual(p["payment_method"], "")
        self.assertIn("cuenta", p["missing_fields"])
        self.assertNotIn("payment_method", p["inferred_fields"])
        self.assertIn("no registrada", bot_sms.encabezado_sms(res))

    def test_tercero_desconocido_queda_sin_especificar_inferido(self):
        cur = _FakeCursor(accounts=CUENTAS, terceros=[])
        p = bot_sms.construir_borrador_sms(cur, SMS_OK, "85540", "Finanzas personales")["payload"]
        self.assertEqual(p["third_party"]["name"], "Sin especificar")
        self.assertIn("third_party", p["inferred_fields"])

    def test_destino_cuenta_propia_es_transferencia(self):               # R-09F-07
        cur = _FakeCursor(accounts=CUENTAS)
        p = bot_sms.construir_borrador_sms(cur, SMS_PROPIA, "85540", "Finanzas personales")["payload"]
        self.assertEqual(p["type"], "TRANSFERENCIA")
        self.assertNotIn("type", p["inferred_fields"])
        self.assertEqual(p["account_id"], 2)
        self.assertEqual(p["dest_account_id"], 4)
        self.assertEqual(p["amount"], 4530000.0)
        self.assertIn("entre cuentas", p["concept"])

    def test_no_reconocido_sin_monto_ni_concepto(self):                   # CA-09F-02
        cur = _FakeCursor(accounts=CUENTAS)
        res = bot_sms.construir_borrador_sms(cur, SMS_RARO, "85540", "Finanzas personales")
        p = res["payload"]
        self.assertFalse(res["reconocido"])
        self.assertIsNone(p["amount"])
        self.assertEqual(p["concept"], "")
        self.assertEqual(p["payment_method"], "")
        self.assertEqual(p["missing_fields"], ["monto", "concepto", "cuenta"])
        self.assertEqual(p["transaction_date"], date.today().isoformat())
        self.assertIn("transaction_date", p["inferred_fields"])
        self.assertIn("no reconocido", bot_sms.encabezado_sms(res))
        self.assertIsNone(p["sms"]["familia"])

    # ── Familias nuevas (muestras reales del 23–29 sep 2026) ──

    def test_compra_resuelve_cuenta_por_tarjeta_y_comercio_por_nombre_exacto(self):
        terceros = TERCEROS + [{"type": "NIT", "number": "901111222", "name": "DIDI", "phone": None}]
        cur = _FakeCursor(accounts=CUENTAS, terceros=terceros)
        res = bot_sms.construir_borrador_sms(cur, SMS_COMPRA, "85540", "Finanzas personales")
        p = res["payload"]
        self.assertEqual(p["type"], "GASTO")
        self.assertNotIn("type", p["inferred_fields"])          # una compra ES un gasto
        self.assertEqual(p["amount"], 7000.0)
        self.assertEqual(p["account_id"], 2)                     # por last4_tarjeta = 7706
        self.assertEqual(p["third_party"]["name"], "DIDI")       # igualdad sin mayúsculas
        self.assertEqual(p["concept"], "Compra en Didi con T.Deb *7706 (SMS)")
        self.assertEqual(p["transaction_date"], "2026-09-23")
        self.assertEqual(p["missing_fields"], [])
        self.assertEqual(p["sms"]["contraparte"], "Didi")
        self.assertEqual(p["sms"]["origen_campo"], "last4_tarjeta")

    def test_compra_con_tarjeta_no_registrada_avisa_tarjeta(self):
        sin_tarjeta = [dict(c, last4_tarjeta=None) for c in CUENTAS]
        cur = _FakeCursor(accounts=sin_tarjeta, terceros=TERCEROS)
        res = bot_sms.construir_borrador_sms(cur, SMS_COMPRA, "85540", "Finanzas personales")
        self.assertIsNone(res["payload"]["account_id"])
        self.assertIn("cuenta", res["payload"]["missing_fields"])
        enc = bot_sms.encabezado_sms(res)
        self.assertIn("Tarjeta *7706 no registrada", enc)
        self.assertIn("El banco dice: Didi", enc)                # comercio sin tercero igual

    def test_comercio_parecido_no_cuenta(self):
        terceros = [{"type": "NIT", "number": "901111222", "name": "Didi Colombia SAS", "phone": None}]
        cur = _FakeCursor(accounts=CUENTAS, terceros=terceros)
        p = bot_sms.construir_borrador_sms(cur, SMS_COMPRA, "85540", "Finanzas personales")["payload"]
        self.assertEqual(p["third_party"]["name"], "Sin especificar")

    def test_recibida_es_ingreso_en_mi_cuenta_con_remitente(self):
        terceros = TERCEROS + [{"type": "CC", "number": "52111222", "name": "Sandra Jimenez", "phone": None}]
        cur = _FakeCursor(accounts=CUENTAS, terceros=terceros)
        res = bot_sms.construir_borrador_sms(cur, SMS_RECIBIDA, "85540", "Finanzas personales")
        p = res["payload"]
        self.assertEqual(p["type"], "INGRESO")
        self.assertNotIn("type", p["inferred_fields"])
        self.assertEqual(p["amount"], 1696000.0)
        self.assertEqual(p["account_id"], 2)
        self.assertIsNone(p["dest_account_id"])
        self.assertEqual(p["third_party"]["identification_number"], "52111222")
        self.assertEqual(p["concept"], "Transferencia recibida de SANDRA JIMENEZ en *3037 (SMS)")
        self.assertEqual(p["transaction_date"], "2026-09-26")

    def test_pago_qr_gasto_desde_mi_cuenta_a_llave(self):
        cur = _FakeCursor(accounts=CUENTAS, terceros=TERCEROS)
        res = bot_sms.construir_borrador_sms(cur, SMS_QR, "85540", "Finanzas personales")
        p = res["payload"]
        self.assertEqual(p["type"], "GASTO")
        self.assertNotIn("type", p["inferred_fields"])
        self.assertEqual(p["amount"], 30000.0)
        self.assertEqual(p["account_id"], 2)
        self.assertIsNone(p["dest_account_id"])                  # una llave jamás es "cuenta propia"
        self.assertEqual(p["concept"], "Pago con QR a la llave 0087671656 desde *3037 (SMS)")
        self.assertEqual(p["sms"]["destino"], "0087671656")
        self.assertEqual(p["third_party"]["name"], "Sin especificar")

    def test_tercero_por_nombre_ambiguo_o_generico_devuelve_none(self):
        dobles = [{"type": "CC", "number": "1", "name": "Sandra Jimenez", "phone": None},
                  {"type": "CC", "number": "2", "name": "SANDRA JIMENEZ", "phone": None},
                  {"type": "NIT", "number": "999999999", "name": "Sin especificar", "phone": None}]
        cur = _FakeCursor(terceros=dobles)
        self.assertIsNone(bot_sms.resolver_tercero_por_nombre(cur, "sandra jimenez"))
        self.assertIsNone(bot_sms.resolver_tercero_por_nombre(cur, "Sin especificar"))
        self.assertIsNone(bot_sms.resolver_tercero_por_nombre(cur, ""))

    def test_portafolio_corregido_queda_inferido(self):
        cur = _FakeCursor(portfolios=("Negocio A",), accounts=CUENTAS)
        p = bot_sms.construir_borrador_sms(cur, SMS_OK, "85540", "No existe")["payload"]
        self.assertEqual(p["portfolio_name"], "Negocio A")
        self.assertIn("portfolio_name", p["inferred_fields"])

    def test_sin_portafolios_lanza(self):
        cur = _FakeCursor(portfolios=(), accounts=CUENTAS)
        with self.assertRaises(ValueError):
            bot_sms.construir_borrador_sms(cur, SMS_OK, "85540", "X")

    def test_encabezado_ok_solo_una_linea(self):
        cur = _FakeCursor(accounts=CUENTAS, terceros=TERCEROS)
        res = bot_sms.construir_borrador_sms(cur, SMS_OK, "85540", "Finanzas personales")
        enc = bot_sms.encabezado_sms(res)
        self.assertTrue(enc.startswith("📲 SMS Bancolombia (85540)"))
        self.assertNotIn("⚠️", enc)


class TestRedDeSeguridad(unittest.TestCase):
    """R-09F-13: plantilla cambiada/nueva e informativos."""

    RETIRO = ("Bancolombia: Retiraste $200.000,00 en CAJERO CC ANDINO de tu T.Deb *7706 "
              "el 01/10/2026 a las 09:15. Dudas: 018000931987.")
    INFO = ("Bancolombia: Muy bien. Inscribiste la cuenta de un tercero desde APP Bancolombia. "
            "Si no fuiste tu, llamanos ahora: 6045109095 o 018000931987.")

    def test_plantilla_nueva_con_dinero_lee_monto_fecha_y_mi_cuenta(self):
        cur = _FakeCursor(accounts=CUENTAS)
        res = bot_sms.construir_borrador_sms(cur, self.RETIRO, "85540", "Finanzas personales")
        p = res["payload"]
        self.assertFalse(res["reconocido"])
        self.assertTrue(res["plantilla_nueva"])
        self.assertFalse(res["informativo"])
        self.assertEqual(p["amount"], 200000.0)
        self.assertEqual(p["transaction_date"], "2026-10-01")
        self.assertEqual(p["account_id"], 2)                      # *7706 = tarjeta registrada
        for campo in ("amount", "payment_method", "type"):
            self.assertIn(campo, p["inferred_fields"])            # todo a revisión
        self.assertEqual(p["concept"], "")
        self.assertEqual(p["missing_fields"], ["concepto"])       # no confirmable sin concepto
        self.assertIn("PLANTILLA NUEVA", bot_sms.encabezado_sms(res))
        self.assertTrue(p["sms"]["plantilla_nueva"])

    def test_plantilla_nueva_sin_cuenta_mia_queda_sin_cuenta(self):
        cur = _FakeCursor(accounts=[CUENTAS[0]])
        res = bot_sms.construir_borrador_sms(cur, self.RETIRO, "85540", "Finanzas personales")
        self.assertIsNone(res["payload"]["account_id"])
        self.assertIn("cuenta", res["payload"]["missing_fields"])
        self.assertEqual(res["payload"]["amount"], 200000.0)

    def test_plantilla_nueva_con_dos_cuentas_mias_no_elige(self):
        cur = _FakeCursor(accounts=CUENTAS)
        texto = "Bancolombia: Moviste $50,000.00 de *3037 a *6625 el 02/10/26."
        res = bot_sms.construir_borrador_sms(cur, texto, "85540", "Finanzas personales")
        self.assertIsNone(res["payload"]["account_id"])           # ambiguo = pregunta

    def test_informativo_no_es_movimiento(self):
        cur = _FakeCursor(accounts=CUENTAS)
        res = bot_sms.construir_borrador_sms(cur, self.INFO, "85540", "Finanzas personales")
        self.assertTrue(res["informativo"])
        self.assertFalse(res["plantilla_nueva"])
        self.assertIsNone(res["payload"]["amount"])


class TestMediosDePago(unittest.TestCase):
    """09.G §10: el tercero sale del medio de pago REGISTRADO en su ficha
    (igualdad del identificador completo). Registrar es siempre explícito."""

    LEIDY = (77, "CC", "1007289007", "Leidy Daniela Molina", None)

    def test_celular_registrado_trae_el_tercero_sin_marcarlo_inferido(self):
        cur = _FakeCursor(accounts=CUENTAS,
                          medios=[{"tipo": "celular", "valor": "3193301184", "tercero": self.LEIDY}])
        res = bot_sms.construir_borrador_sms(cur, SMS_OK, "85540", "Finanzas personales")
        p = res["payload"]
        self.assertTrue(res["tercero_por_medio"])
        self.assertEqual(p["third_party"]["name"], "Leidy Daniela Molina")
        self.assertEqual(p["third_party"]["identification_number"], "1007289007")
        self.assertNotIn("third_party", p["inferred_fields"])
        self.assertEqual(p["sms"]["medio"], {"tipo": "celular", "valor": "3193301184"})
        self.assertTrue(p["sms"]["tercero_por_medio"])
        self.assertIn("medio de pago registrado (cel 3193301184)", bot_sms.encabezado_sms(res))

    def test_sin_registrar_el_medio_igual_viaja_en_el_borrador_para_el_boton_guardar(self):
        cur = _FakeCursor(accounts=CUENTAS)
        res = bot_sms.construir_borrador_sms(cur, SMS_OK, "85540", "Finanzas personales")
        self.assertFalse(res["tercero_por_medio"])
        self.assertEqual(res["payload"]["sms"]["medio"], {"tipo": "celular", "valor": "3193301184"})
        self.assertEqual(res["payload"]["third_party"]["name"], "Sin especificar")

    def test_cuenta_registrada_de_un_tercero_gana_a_la_regla_de_cuenta_propia(self):
        # *91232656625 termina en 6625 = last4 de una cuenta MÍA; pero el número
        # COMPLETO está en la ficha de un tercero → es un GASTO a ese tercero.
        cur = _FakeCursor(accounts=CUENTAS,
                          medios=[{"tipo": "cuenta", "valor": "91232656625", "tercero": self.LEIDY}])
        p = bot_sms.construir_borrador_sms(cur, SMS_PROPIA, "85540", "Finanzas personales")["payload"]
        self.assertEqual(p["type"], "GASTO")
        self.assertIsNone(p["dest_account_id"])
        self.assertEqual(p["third_party"]["name"], "Leidy Daniela Molina")

    def test_recibida_por_nombre_del_banco_registrado(self):
        sandra = (80, "CC", "52111222", "Sandra Jiménez Pérez", None)
        cur = _FakeCursor(accounts=CUENTAS,
                          medios=[{"tipo": "nombre_banco", "valor": "SANDRA JIMENEZ", "tercero": sandra}])
        res = bot_sms.construir_borrador_sms(cur, SMS_RECIBIDA, "85540", "Finanzas personales")
        self.assertEqual(res["payload"]["third_party"]["identification_number"], "52111222")
        self.assertEqual(res["payload"]["type"], "INGRESO")
        self.assertNotIn("El banco dice", bot_sms.encabezado_sms(res))

    def test_compra_por_nombre_del_comercio_registrado(self):
        didi = (81, "NIT", "901111222", "DiDi Colombia SAS", None)
        cur = _FakeCursor(accounts=CUENTAS,
                          medios=[{"tipo": "nombre_banco", "valor": "DIDI", "tercero": didi}])
        p = bot_sms.construir_borrador_sms(cur, SMS_COMPRA, "85540", "Finanzas personales")["payload"]
        self.assertEqual(p["third_party"]["name"], "DiDi Colombia SAS")
        self.assertEqual(p["sms"]["medio"], {"tipo": "nombre_banco", "valor": "DIDI"})

    def test_pago_qr_por_llave_registrada(self):
        tienda = (82, "NIT", "900555666", "Tienda La Esquina", None)
        cur = _FakeCursor(accounts=CUENTAS,
                          medios=[{"tipo": "llave", "valor": "0087671656", "tercero": tienda}])
        p = bot_sms.construir_borrador_sms(cur, SMS_QR, "85540", "Finanzas personales")["payload"]
        self.assertEqual(p["third_party"]["name"], "Tienda La Esquina")

    def test_no_reconocido_no_tiene_medio(self):
        cur = _FakeCursor(accounts=CUENTAS)
        res = bot_sms.construir_borrador_sms(cur, SMS_RARO, "85540", "Finanzas personales")
        self.assertIsNone(res["payload"]["sms"]["medio"])
        self.assertFalse(res["tercero_por_medio"])


class TestTerceroDeMedio(unittest.TestCase):
    """UN solo cruce para el SMS que llega y para decidir si se ofrece 💾:
    medio registrado → celular de contacto / nombre exacto de una sola ficha."""

    LEIDY = (77, "CC", "1007289007", "Leidy Daniela Molina", None)

    def test_medio_registrado_gana_al_celular_de_contacto(self):
        # Juan Pérez tiene ese celular en su ficha, pero el medio está registrado a Leidy
        cur = _FakeCursor(terceros=TERCEROS,
                          medios=[{"tipo": "celular", "valor": "3193301184", "tercero": self.LEIDY}])
        t, por_medio = bot_sms.tercero_de_medio(cur, ("celular", "3193301184"))
        self.assertEqual((t["name"], por_medio), ("Leidy Daniela Molina", True))

    def test_sin_registro_cae_al_celular_de_contacto(self):
        cur = _FakeCursor(terceros=TERCEROS)
        t, por_medio = bot_sms.tercero_de_medio(cur, ("celular", "3193301184"))
        self.assertEqual((t["name"], por_medio), ("Juan Pérez", False))
        t, _ = bot_sms.tercero_de_medio(cur, ("llave", "3193301184"))    # llave que es un celular
        self.assertEqual(t["name"], "Juan Pérez")

    def test_nombre_del_banco_cae_al_nombre_exacto_de_la_ficha(self):
        cur = _FakeCursor(terceros=TERCEROS)
        t, por_medio = bot_sms.tercero_de_medio(cur, ("nombre_banco", "TIENDA"), "Tienda")
        self.assertEqual((t["identification_number"], por_medio), ("900123456", False))
        # «Juan Pérez» lleva tilde: NO es igualdad exacta con lo que escribe el banco
        self.assertEqual(bot_sms.tercero_de_medio(cur, ("nombre_banco", "JUAN PEREZ"), "JUAN PEREZ"),
                         (None, False))

    def test_cuenta_o_llave_sin_registrar_no_resuelve_a_nadie(self):
        cur = _FakeCursor(terceros=TERCEROS)
        self.assertEqual(bot_sms.tercero_de_medio(cur, ("cuenta", "91232656625")), (None, False))
        self.assertEqual(bot_sms.tercero_de_medio(cur, ("llave", "0087671656")), (None, False))
        self.assertEqual(bot_sms.tercero_de_medio(cur, None), (None, False))


class TestDedupe(unittest.TestCase):

    def test_clave_estable_32_chars(self):
        a = bot_sms.clave_dedupe("85540", SMS_OK)
        b = bot_sms.clave_dedupe("+85540", SMS_OK + "  ")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 32)
        self.assertNotEqual(a, bot_sms.clave_dedupe("85540", SMS_OK, "1700000000"))
        self.assertNotEqual(a, bot_sms.clave_dedupe("85540", SMS_PROPIA))

    def test_hash_token(self):
        self.assertEqual(len(bot_sms.hash_token("abc")), 64)
        self.assertNotEqual(bot_sms.hash_token("abc"), bot_sms.hash_token("abd"))


if __name__ == "__main__":
    unittest.main()
