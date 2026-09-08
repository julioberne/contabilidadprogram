# -*- coding: utf-8 -*-
"""Etapa E del bot (2026-09-09): fotos como evidencia + botones inline +
/empresa. Tests PUROS (sin BD ni red): parsing, normalización y formatos."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fin_sys_core"))

import bot_driver    # noqa: E402
import bot_telegram  # noqa: E402


class TestComandoEmpresa(unittest.TestCase):
    def test_empresa_sin_argumento(self):
        self.assertEqual(bot_driver.parse_command("/empresa"), ("empresa", None))

    def test_empresa_con_nombre(self):
        self.assertEqual(bot_driver.parse_command("/empresa constructora blu"),
                         ("empresa", "constructora blu"))

    def test_comandos_viejos_intactos(self):
        self.assertEqual(bot_driver.parse_command("Confirmar #42"), ("confirmar", 42))
        self.assertEqual(bot_driver.parse_command("/borradores"), ("borradores", None))


class TestBotones(unittest.TestCase):
    def test_botonera_estandar(self):
        filas = bot_driver._botones_borrador(43)
        planos = [data for fila in filas for _, data in fila]
        for esperado in ("ok:43", "no:43", "emp:43", "tags:43", "hold:43"):
            self.assertIn(esperado, planos)
        # límite de Telegram: callback_data ≤ 64 bytes
        for d in planos:
            self.assertLessEqual(len(d.encode()), 64)

    def test_resumen_muestra_tags_y_ubicacion(self):
        payload = {"type": "GASTO", "amount": 1000, "concept": "x",
                   "category": "Otros Gastos", "payment_method": "Efectivo",
                   "third_party": {"name": "n", "identification_type": "NIT",
                                    "identification_number": "1"},
                   "transaction_date": "2026-09-08", "portfolio_name": "Negocio A",
                   "tags": ["obra", "urgente"],
                   "geo_maps_link": "https://www.google.com/maps?q=1,2"}
        r = bot_driver.render_summary(9, payload)
        self.assertIn("obra, urgente", r)
        self.assertIn("📍 Ubicación adjunta", r)

    def test_markup_telegram(self):
        mk = bot_telegram._markup([[("✅ Confirmar", "ok:1")], [("« Volver", "empback:1")]])
        self.assertEqual(mk["inline_keyboard"][0][0],
                         {"text": "✅ Confirmar", "callback_data": "ok:1"})
        self.assertIsNone(bot_telegram._markup(None))
        self.assertEqual(bot_telegram._markup([]), {"inline_keyboard": []})


class TestNormalizeFoto(unittest.TestCase):
    def _update(self, message):
        return {"update_id": 99, "message": {"chat": {"id": 5, "type": "private"}, **message}}

    def test_foto_con_caption_y_reply(self):
        with mock.patch.object(bot_telegram, "_descargar_foto",
                               return_value="https://x/evidence/f.jpg"):
            msg = bot_telegram.normalize(self._update({
                "photo": [{"file_id": "chica"}, {"file_id": "grande"}],
                "caption": "mercado 45.000",
                "reply_to_message": {"message_id": 777},
            }))
        self.assertEqual(msg["kind"], "photo")
        self.assertEqual(msg["media_path"], "https://x/evidence/f.jpg")
        self.assertEqual(msg["text"], "mercado 45.000")
        self.assertEqual(msg["reply_to_message_id"], "777")

    def test_grupo_se_ignora(self):
        u = {"update_id": 1, "message": {"chat": {"id": -9, "type": "group"}, "text": "hola"}}
        self.assertIsNone(bot_telegram.normalize(u))

    def test_texto_normal_intacto(self):
        msg = bot_telegram.normalize(self._update({"text": "gasté 20.000 en taxi"}))
        self.assertEqual(msg["kind"], "text")
        self.assertEqual(msg["text"], "gasté 20.000 en taxi")

    def test_ubicacion(self):
        msg = bot_telegram.normalize(self._update({
            "location": {"latitude": 4.6482, "longitude": -74.0648},
            "reply_to_message": {"message_id": 321},
        }))
        self.assertEqual(msg["kind"], "location")
        self.assertAlmostEqual(msg["latitude"], 4.6482)
        self.assertEqual(msg["reply_to_message_id"], "321")


if __name__ == "__main__":
    unittest.main()
