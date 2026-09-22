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
SMS_RARO = "Bancolombia: Compraste $45,000.00 en EXITO con tu T.Deb *1234 el 21/09/26."


class _FakeCursor:
    """Enruta por la tabla mencionada en el SQL. accounts: dicts con id, name,
    last4_cuenta, last4_tarjeta. terceros: dicts con type, number, name, phone."""

    def __init__(self, portfolios=("Finanzas personales",), accounts=(), terceros=()):
        self.portfolios = list(portfolios)
        self.accounts = list(accounts)
        self.terceros = list(terceros)
        self._rows = []
        self.sqls = []

    def execute(self, sql, params=None):
        self.sqls.append(sql)
        if "FROM portfolios" in sql:
            self._rows = [(p,) for p in self.portfolios]
        elif "FROM user_accounts" in sql:
            campo = "last4_tarjeta" if "last4_tarjeta" in sql else "last4_cuenta"
            self._rows = [(a["id"], a["name"]) for a in self.accounts
                          if a.get(campo) == params[0]]
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
