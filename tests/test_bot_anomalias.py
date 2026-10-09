# -*- coding: utf-8 -*-
"""Bitácora de anomalías del bot (hito E, 9-oct-2026) — tests puros.

Registrar es informativo y best-effort: jamás lanza ni cambia un flujo, deja
el texto tal cual y excluye los chats de prueba en la misma sentencia.
"""
import os
import sys
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import bot_anomalias  # noqa: E402
import bot_driver     # noqa: E402
import bot_sms        # noqa: E402
import db_pool        # noqa: E402
from tests.test_bot_sms import _FakeCursor  # noqa: E402
from tests.test_sms_plantillas_oct import BOLSILLO, CUENTAS, RETIRO, BRE_B  # noqa: E402


class _Cur:
    def __init__(self, filas=(), falla=None):
        self.sql, self.params, self.filas, self.falla = None, None, list(filas), falla
        self.rowcount = 1

    def execute(self, sql, params=None):
        if self.falla:
            raise self.falla
        self.sql, self.params = sql, params

    def fetchall(self):
        return self.filas

    def fetchone(self):
        return self.filas[0] if self.filas else None

    def close(self):
        pass


class _Conn:
    def __init__(self, cur):
        self.cur, self.commits, self.rollbacks = cur, 0, 0

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class TestRegistrar(unittest.TestCase):

    def _registrar(self, cur, *a, **kw):
        conn = _Conn(cur)
        with mock.patch.object(db_pool, "get_conn", return_value=conn), \
                mock.patch.object(db_pool, "put_conn") as put:
            r = bot_anomalias.registrar(*a, **kw)
        put.assert_called_once_with(conn)
        return r, conn

    def test_escribe_literal_y_excluye_chats_de_prueba(self):
        cur = _Cur()
        ok, conn = self._registrar(cur, "sms_plantilla_nueva", "Monto y fecha leídos", draft_id=7,
                                   chat_link_id=3, canal="sms", texto="Bancolombia: algo $1", datos={"x": 1})
        self.assertTrue(ok)
        self.assertEqual(conn.commits, 1)
        self.assertIn("NOT LIKE 'test-%%'", cur.sql)
        self.assertEqual((cur.params["tipo"], cur.params["draft"], cur.params["link"], cur.params["texto"]),
                         ("sms_plantilla_nueva", 7, 3, "Bancolombia: algo $1"))
        self.assertEqual(cur.params["datos"], '{"x": 1}')

    def test_jamas_lanza(self):
        ok, conn = self._registrar(_Cur(falla=RuntimeError('relation "bot_anomalias" does not exist')),
                                   "error_bot", "x")
        self.assertFalse(ok)
        self.assertEqual(conn.rollbacks, 1)
        with mock.patch.object(db_pool, "get_conn", side_effect=RuntimeError("sin pool")):
            self.assertFalse(bot_anomalias.registrar("error_bot"))

    def test_texto_largo_se_recorta(self):
        cur = _Cur()
        self._registrar(cur, "error_bot", texto="a" * 5000)
        self.assertEqual(len(cur.params["texto"]), 2000)


class TestLecturas(unittest.TestCase):

    def test_texto_resumen(self):
        cur = _Cur(filas=[("sms_plantilla_nueva", 3, 2), ("borrador_descartado", 5, 5)])
        t = bot_anomalias.texto_resumen(cur, 7, "u-1")
        self.assertIn("2 / 3 — SMS del banco sin plantilla", t)
        self.assertIn("Bot IA → 📓 Bitácora", t)
        self.assertEqual(cur.params["uid"], "u-1")

    def test_texto_resumen_vacio(self):
        self.assertIn("sin anomalías", bot_anomalias.texto_resumen(_Cur(), 7))

    def test_listar_filtra(self):
        cur = _Cur()
        bot_anomalias.listar(cur, dias=30, tipo="sms_error", solo_abiertas=True, hub_user_id="u-1")
        self.assertIn("a.tipo = %(tipo)s", cur.sql)
        self.assertIn("NOT a.revisada", cur.sql)
        self.assertEqual((cur.params["dias"], cur.params["tipo"]), (30, "sms_error"))

    def test_comando(self):
        self.assertEqual(bot_driver.parse_command("/anomalias"), ("anomalias", None))
        self.assertEqual(bot_driver.parse_command("/bitácora"), ("anomalias", None))
        self.assertTrue(set(bot_anomalias.TIPOS) >= {"sms_plantilla_nueva", "sms_traslado_sin_destino",
                                                      "reply_sin_borrador", "borrador_descartado"})


class TestAnomaliasDeSms(unittest.TestCase):
    """Qué anota cada SMS (la bitácora no cambia el borrador)."""

    def _anotar(self, texto, cuentas=CUENTAS):
        cur = _FakeCursor(portfolios=("Negocio A",), accounts=cuentas)
        res = bot_sms.construir_borrador_sms(cur, texto, "85540", "Negocio A")
        with mock.patch("bot_anomalias.registrar") as reg:
            bot_sms._anotar_anomalias(res, 99, 3, texto, "sms")
        return {c.args[0]: c for c in reg.call_args_list}

    def test_bolsillo_queda_como_traslado_sin_destino(self):
        reg = self._anotar(BOLSILLO)
        self.assertIn("sms_traslado_sin_destino", reg)
        self.assertIn("bolsillo «Personal»", reg["sms_traslado_sin_destino"].args[1])
        self.assertEqual(reg["sms_traslado_sin_destino"].kwargs["draft_id"], 99)
        self.assertNotIn("sms_cuenta_no_registrada", reg)

    def test_tarjeta_sin_registrar(self):
        reg = self._anotar(RETIRO, cuentas=[CUENTAS[0]])
        self.assertEqual(reg["sms_cuenta_no_registrada"].args[1], "Tarjeta *5379 sin cuenta en 💳 Cuentas")

    def test_contraparte_sin_ficha_y_plantilla_nueva(self):
        reg = self._anotar(BRE_B)
        self.assertIn("llave 6550482", reg["sms_contraparte_sin_ficha"].args[1])
        reg = self._anotar("Bancolombia: Realizaste un avance por $200.000,00 con tu T.Cred *5379 el 01/10/2026.")
        self.assertIn("sms_plantilla_nueva", reg)

    def test_sms_completo_no_anota_nada(self):
        reg = self._anotar(RETIRO)
        self.assertEqual(reg, {})


if __name__ == "__main__":
    unittest.main()
