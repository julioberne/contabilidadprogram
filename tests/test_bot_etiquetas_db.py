# -*- coding: utf-8 -*-
"""Integración con la BD (hito D, 9-oct-2026): ➕ Nueva etiqueta desde el bot.

BD compartida con producción: etiquetas «zz-test-…» y un chat `test-tg-…`
(canal 'whatsapp'); todo se borra en tearDown.
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

from tests.test_bot_webapp_db import _Base, get_conn, put_conn  # noqa: E402


class TestEtiquetaNueva(_Base):

    def setUp(self):
        super().setUp()
        self.nombre = f"zz-test-{self.sufijo}"

    def tearDown(self):
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM tag_definitions WHERE name ILIKE %s", (f"zz-test-{self.sufijo}%",))
            cur.execute("DELETE FROM bot_messages WHERE raw_chat_id = %s", (self.chat_id,))
            conn.commit()
        finally:
            put_conn(conn)
        super().tearDown()

    def test_crear_o_usar_no_duplica(self):
        from etiquetas import crear_o_usar
        conn = get_conn()
        try:
            cur = conn.cursor()
            a = crear_o_usar(cur, self.nombre)
            b = crear_o_usar(cur, "  " + self.nombre.upper() + " ")
            conn.commit()
        finally:
            put_conn(conn)
        self.assertTrue(a["creada"])
        self.assertFalse(b["creada"])
        self.assertEqual(a["tag"]["id"], b["tag"]["id"])
        self.assertFalse(crear_o_usar(None, "   ")["ok"])          # se valida antes de tocar la BD

    def test_responder_etiqueta_la_crea_y_la_pone_solo_en_el_borrador(self):
        conn = get_conn()
        try:
            cur = conn.cursor()
            r = self.bot._flujo_reply(cur, {"id": self.link_id, "hub_user_id": self.uid}, self.draft_id,
                                      f"parqueadero\nEtiqueta: {self.nombre}")
            conn.commit()
        finally:
            put_conn(conn)
        self.assertIn(f"creada: {self.nombre}", r["text"])
        p, _ = self._payload()
        self.assertEqual((p["tags"], p["concept"]), ([self.nombre], "parqueadero"))

    def test_boton_nueva_pide_el_nombre_con_force_reply(self):
        out = self.bot.handle_callback("whatsapp", self.chat_id, f"tags:{self.draft_id}")
        self.assertEqual(out["edit_buttons"][-1][0], ("➕ Nueva etiqueta", f"tagnew:{self.draft_id}"))
        out = self.bot.handle_callback("whatsapp", self.chat_id, f"tagnew:{self.draft_id}")
        self.assertEqual(out["text_kind"], "pedir_etiqueta")
        self.assertTrue(out["text_buttons"]["force_reply"])
        self.assertIn(f"#{self.draft_id}", out["text"])

    def test_respuesta_al_mensaje_registrado_como_pedir_etiqueta(self):
        self.bot.vincular_mensaje("telegram", self.chat_id, self.draft_id, 777, kind="pedir_etiqueta")
        conn = get_conn()
        try:
            cur = conn.cursor()
            link = {"id": self.link_id, "hub_user_id": self.uid}
            msg = {"channel": "telegram", "chat_id": self.chat_id, "kind": "text",
                   "reply_to_message_id": "777", "text": f"{self.nombre}-a, {self.nombre}-b"}
            destino = self.bot._draft_por_reply(cur, link, msg)
            self.assertEqual(destino["kind"], "pedir_etiqueta")
            r = self.bot._flujo_respuesta(cur, link, destino, msg)
            conn.commit()
        finally:
            put_conn(conn)
        self.assertIn("🏷️ Etiquetas →", r["text"])
        p, _ = self._payload()
        self.assertEqual(p["tags"], [f"{self.nombre}-a", f"{self.nombre}-b"])
        self.assertEqual(p["concept"], "Transferencia (SMS)")      # el concepto no se tocó


if __name__ == "__main__":
    unittest.main()
