# -*- coding: utf-8 -*-
"""Hito 3 Análisis Inteligente (bot informativo) — tests PUROS (sin BD ni red).

El bot NO adivina (regla 6b): la pregunta analítica exige comando explícito
(/analisis, /pregunta) — jamás se confunde con un registro de gasto. La
respuesta reutiliza la MISMA maquinaria de la web (analytics_qa) y la gráfica
viaja como foto aparte (photo_png_base64 → sendPhoto multipart).
"""
import base64
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fin_sys_core"))

import bot_driver    # noqa: E402
import bot_telegram  # noqa: E402


class TestParseComandoAnalisis(unittest.TestCase):

    def test_analisis_con_pregunta(self):
        self.assertEqual(bot_driver.parse_command("/analisis cuánto gasté este mes"),
                         ("analisis", "cuánto gasté este mes"))
        self.assertEqual(bot_driver.parse_command("/ANÁLISIS cartera vencida"),
                         ("analisis", "cartera vencida"))
        self.assertEqual(bot_driver.parse_command("/pregunta flujo de 6 meses"),
                         ("analisis", "flujo de 6 meses"))

    def test_analisis_sin_pregunta_no_es_comando(self):
        # Sin pregunta no matchea: cae al flujo normal (el LLM del registro
        # dirá que no entiende) — no hay comando a medias.
        self.assertEqual(bot_driver.parse_command("/analisis"), (None, None))

    def test_resumen(self):
        self.assertEqual(bot_driver.parse_command("/resumen"), ("resumen", None))
        self.assertEqual(bot_driver.parse_command("  /Resumen  "), ("resumen", None))

    def test_un_gasto_normal_jamas_es_pregunta(self):
        # Regla 6b: sin comando, un texto es un movimiento — nunca análisis.
        self.assertEqual(bot_driver.parse_command("gasté 20.000 en taxi"), (None, None))
        self.assertEqual(bot_driver.parse_command("cuánto gasté este mes?"), (None, None))

    def test_comandos_viejos_intactos(self):
        self.assertEqual(bot_driver.parse_command("Confirmar #42"), ("confirmar", 42))
        self.assertEqual(bot_driver.parse_command("/empresa"), ("empresa", None))


class TestResponderAnalisis(unittest.TestCase):

    RESPUESTA = {"texto": "Gasto de 2026-09: $4.835.500. — según 30 TXs de 2026-09-01 a 2026-09-20.",
                 "metrica": "gasto_mes", "datos": {}, "grafica_png_base64": "UE5HZmFrZQ=="}

    def test_con_empresa_y_grafica(self):
        with mock.patch("analytics_qa.responder_pregunta",
                        return_value=dict(self.RESPUESTA)) as rp:
            out = bot_driver._responder_analisis("cuánto gasté?", 1, "Finanzas Personales Julian")
        rp.assert_called_once_with("cuánto gasté?", portfolio_id=1)
        self.assertIn("🏢 Finanzas Personales Julian", out["text"])
        self.assertIn("según 30 TXs", out["text"])
        self.assertEqual(out["photo_png_base64"], "UE5HZmFrZQ==")

    def test_consolidado_sin_grafica(self):
        r = dict(self.RESPUESTA, grafica_png_base64=None)
        with mock.patch("analytics_qa.responder_pregunta", return_value=r):
            out = bot_driver._responder_analisis("balance", None, None)
        self.assertIn("Todas las empresas (consolidado)", out["text"])
        self.assertNotIn("photo_png_base64", out)

    def test_pregunta_vacia_pide_ejemplo(self):
        out = bot_driver._responder_analisis("   ", 1, "X")
        self.assertIsInstance(out, str)
        self.assertIn("/analisis", out)

    def test_error_honesto(self):
        with mock.patch("analytics_qa.responder_pregunta",
                        side_effect=RuntimeError("BD caída")):
            out = bot_driver._responder_analisis("gasto", 1, "X")
        self.assertIn("El análisis falló", out)
        self.assertIn("BD caída", out)


class CursorPortafolio:
    def __init__(self, fila):
        self._fila = fila
        self.sql = ""

    def execute(self, sql, params=None):
        self.sql = " ".join(sql.split())
        self.params = list(params or [])

    def fetchone(self):
        return self._fila


class TestPortafolioDelChat(unittest.TestCase):

    def test_prefiere_nombre_del_control_tower(self):
        cur = CursorPortafolio((1, "Finanzas Personales Julian"))
        pid, nombre = bot_driver._portafolio_del_chat(cur, {"default_portfolio": "Negocio A"})
        self.assertEqual((pid, nombre), (1, "Finanzas Personales Julian"))
        self.assertEqual(cur.params, ["Negocio A"])
        self.assertIn("LEFT JOIN entities", cur.sql)

    def test_default_que_no_resuelve_va_consolidado(self):
        cur = CursorPortafolio(None)
        self.assertEqual(bot_driver._portafolio_del_chat(cur, {"default_portfolio": "Fantasma"}),
                         (None, None))


class FakeRespuestaTG:
    def __init__(self, status_code=200, message_id=77):
        self.status_code = status_code
        self.text = "err"
        self._mid = message_id

    def json(self):
        return {"result": {"message_id": self._mid}}


class TestSendPhoto(unittest.TestCase):

    def test_multipart_png(self):
        png = b"\x89PNG-fake"
        with mock.patch.object(bot_telegram, "_client") as cli:
            cli.post.return_value = FakeRespuestaTG()
            mid = bot_telegram.send_photo("123", png, caption="según 30 TXs")
        self.assertEqual(mid, 77)
        args, kwargs = cli.post.call_args
        self.assertTrue(args[0].endswith("/sendPhoto"))
        self.assertEqual(kwargs["data"]["chat_id"], "123")
        self.assertEqual(kwargs["data"]["caption"], "según 30 TXs")
        nombre, contenido, mime = kwargs["files"]["photo"]
        self.assertEqual((nombre, contenido, mime), ("grafica.png", png, "image/png"))

    def test_fallo_devuelve_none_sin_lanzar(self):
        with mock.patch.object(bot_telegram, "_client") as cli:
            cli.post.side_effect = RuntimeError("sin red")
            self.assertIsNone(bot_telegram.send_photo("123", b"x"))
        with mock.patch.object(bot_telegram, "_client") as cli:
            cli.post.return_value = FakeRespuestaTG(status_code=413)
            self.assertIsNone(bot_telegram.send_photo("123", b"x"))

    def test_base64_de_la_web_decodifica_a_los_mismos_bytes(self):
        # El poller decodifica photo_png_base64 antes de sendPhoto.
        png = b"\x89PNG\r\n\x1a\nbytes-reales"
        self.assertEqual(base64.b64decode(base64.b64encode(png).decode("ascii")), png)


if __name__ == "__main__":
    unittest.main()
