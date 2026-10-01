# -*- coding: utf-8 -*-
"""Etapa 09.I — Mini App de Telegram (v1): tests PUROS (sin BD, van en el CI).

Cubre la parte del bot que no necesita Postgres: el botón «📝 Completar
tercero» en la botonera del borrador y su traducción a un botón web_app por
el adaptador de Telegram.
"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "fin_sys_core"))

import fin_sys_core  # noqa: E402,F401  (alias de módulos: `import bot_driver`)
import bot_driver    # noqa: E402


class TestBotonMiniApp(unittest.TestCase):

    def test_la_botonera_lleva_el_boton_de_la_mini_app(self):
        filas = bot_driver._botones_borrador(507)
        web = [(lbl, d) for fila in filas for lbl, d in fila if d.startswith("webapp:")]
        self.assertEqual(len(web), 1)
        etiqueta, data = web[0]
        self.assertEqual(etiqueta, "📝 Completar tercero")
        self.assertTrue(data.startswith("webapp:https://"), data)      # Telegram exige HTTPS
        self.assertTrue(data.endswith("/tg.html?draft=507"), data)
        self.assertEqual(data, f"webapp:{bot_driver.WEBAPP_BASE}/tg.html?draft=507")
        # va después de 👤 Tercero / 📝 Concepto y antes de 💤 Dejar en borrador
        datas = [d for fila in filas for _, d in fila]
        self.assertLess(datas.index("tp:507"), datas.index(data))
        self.assertLess(datas.index(data), datas.index("hold:507"))

    def test_los_demas_botones_siguen_cabiendo_en_64_bytes(self):
        for fila in bot_driver._botones_borrador(99999999):
            for _, d in fila:
                if not d.startswith("webapp:"):
                    self.assertLessEqual(len(d.encode()), 64)

    def test_la_botonera_con_medio_conserva_el_boton(self):
        filas = bot_driver._botones_con_medio(9, None)
        self.assertTrue(any(d.startswith("webapp:") for fila in filas for _, d in fila))

    def test_el_adaptador_traduce_webapp_a_boton_web_app(self):
        import bot_telegram
        mk = bot_telegram._markup([
            [("✅ Confirmar", "ok:1"), ("❌ Descartar", "no:1")],
            [("📝 Completar tercero", "webapp:https://x.test/tg.html?draft=1")],
        ])
        self.assertEqual(mk["inline_keyboard"][0][0], {"text": "✅ Confirmar", "callback_data": "ok:1"})
        self.assertEqual(mk["inline_keyboard"][1][0],
                         {"text": "📝 Completar tercero", "web_app": {"url": "https://x.test/tg.html?draft=1"}})
        self.assertIsNone(bot_telegram._markup(None))

    def test_el_adaptador_recorta_callbacks_largos_pero_no_urls(self):
        import bot_telegram
        largo = "x" * 100
        mk = bot_telegram._markup([[("a", largo), ("b", "webapp:https://x.test/" + largo)]])
        self.assertEqual(len(mk["inline_keyboard"][0][0]["callback_data"]), 64)
        self.assertEqual(mk["inline_keyboard"][0][1]["web_app"]["url"], "https://x.test/" + largo)


if __name__ == "__main__":
    unittest.main()
