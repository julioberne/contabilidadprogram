# -*- coding: utf-8 -*-
"""Integración con la BD (9-oct-2026): botón 💳 Cuenta y registro de mensajes
por borrador (responder a CUALQUIER mensaje del borrador lo completa).

BD compartida con producción: chat `test-tg-…` en el canal 'whatsapp' (el
poller real solo atiende 'telegram'); el borrador, sus mensajes y el chat se
borran en tearDown. Las cuentas (user_accounts) solo se LEEN.
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

from tests.test_bot_webapp_db import _Base, get_conn, put_conn  # noqa: E402


class _BaseCuentas(_Base):

    def setUp(self):
        super().setUp()
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM user_accounts ORDER BY id LIMIT 2")
            self.cuentas = cur.fetchall()
        finally:
            put_conn(conn)
        if len(self.cuentas) < 2:
            self.skipTest("hacen falta 2 cuentas en user_accounts")

    def tearDown(self):
        conn = get_conn()
        try:
            cur = conn.cursor()
            # vincular_mensaje no conoce el chat_link_id: se limpia por chat
            cur.execute("DELETE FROM bot_messages WHERE raw_chat_id = %s", (self.chat_id,))
            conn.commit()
        finally:
            put_conn(conn)
        super().tearDown()


class TestBotonCuenta(_BaseCuentas):

    def test_cuenta_de_pago_por_id(self):
        cid, nombre = self.cuentas[0]
        p = self.bot.editar_draft(self.draft_id, {"account_id": cid}, hub_user_id=self.uid)["payload"]
        self.assertEqual((p["account_id"], p["payment_method"]), (cid, nombre.strip()))
        self.assertNotIn("cuenta", p["missing_fields"])

    def test_destino_convierte_en_traslado_y_se_puede_quitar(self):
        (o, _), (d, nombre_d) = self.cuentas
        self.bot.editar_draft(self.draft_id, {"account_id": o}, hub_user_id=self.uid)
        p = self.bot.editar_draft(self.draft_id, {"dest_account_id": d}, hub_user_id=self.uid)["payload"]
        self.assertEqual((p["type"], p["dest_account_id"], p["dest_account_name"]),
                         ("TRANSFERENCIA", d, nombre_d.strip()))
        self.assertEqual(p["missing_fields"], [])
        p = self.bot.editar_draft(self.draft_id, {"dest_account_id": None}, hub_user_id=self.uid)["payload"]
        self.assertEqual((p["type"], p["dest_account_id"]), ("GASTO", None))
        self.assertIn("type", p["inferred_fields"])          # vuelve a revisión

    def test_destino_igual_al_origen_se_rechaza(self):
        o = self.cuentas[0][0]
        self.bot.editar_draft(self.draft_id, {"account_id": o}, hub_user_id=self.uid)
        r = self.bot.editar_draft(self.draft_id, {"dest_account_id": o}, hub_user_id=self.uid)
        self.assertIn("misma", r["error"])

    def test_cuenta_inexistente(self):
        r = self.bot.editar_draft(self.draft_id, {"account_id": 99999999}, hub_user_id=self.uid)
        self.assertIn("ya no existe", r["error"])

    def test_botones_de_cuenta(self):
        out = self.bot.handle_callback("whatsapp", self.chat_id, f"acc:{self.draft_id}")
        datas = [d for fila in out["edit_buttons"] for _, d in fila]
        self.assertIn(f"accsel:{self.draft_id}:d", datas)
        out = self.bot.handle_callback("whatsapp", self.chat_id, f"accsel:{self.draft_id}:o")
        cid, nombre = self.cuentas[0]
        self.assertIn((nombre.strip()[:60], f"accset:{self.draft_id}:o:{cid}"),
                      [b for fila in out["edit_buttons"] for b in fila])
        out = self.bot.handle_callback("whatsapp", self.chat_id, f"accset:{self.draft_id}:o:{cid}")
        self.assertIn(f"Pago: {nombre.strip()}", out["edit_text"])
        self.assertEqual(out["draft_id"], self.draft_id)


class TestRegistroDeMensajes(_BaseCuentas):

    def _msg(self, rid, **kw):
        m = {"channel": "telegram", "chat_id": self.chat_id, "reply_to_message_id": rid}
        m.update(kw)
        return m

    def test_cualquier_mensaje_registrado_lleva_al_borrador(self):
        self.bot.log_outbound("telegram", self.chat_id, "resumen", draft_id=self.draft_id, message_id=111)
        self.bot.vincular_mensaje("telegram", self.chat_id, self.draft_id, 112)
        link = {"id": self.link_id}
        conn = get_conn()
        try:
            cur = conn.cursor()
            for rid in ("111", "112"):
                r = self.bot._draft_por_reply(cur, link, self._msg(rid))
                self.assertEqual((r["id"], r["status"]), (self.draft_id, "BORRADOR"), rid)
            self.assertIsNone(self.bot._draft_por_reply(cur, link, self._msg("113")))
        finally:
            put_conn(conn)

    def test_guardar_resumen_devuelve_el_anterior(self):
        _, previo = self._payload()
        self.assertEqual(self.bot.guardar_summary_message_id(self.draft_id, 500), previo)
        self.assertEqual(self.bot.guardar_summary_message_id(self.draft_id, 501), "500")
        self.assertEqual(self._payload()[1], "501")


if __name__ == "__main__":
    unittest.main()
