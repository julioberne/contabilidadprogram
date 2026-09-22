# -*- coding: utf-8 -*-
"""Integración de la etapa 09.G contra Supabase (CA-09G-04): un reply al resumen
del borrador pone el concepto o el tercero en el payload. Usa un chat de
prueba y un tercero de prueba, y borra todo en tearDown. Jamás crea
transacciones.

Ejecutar:  .venv\\Scripts\\python.exe -m unittest tests.test_bot_completar_db -v
"""
import json
import os
import sys
import unittest
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

_env = os.path.join(_ROOT, ".env")
if os.path.exists(_env):
    with open(_env, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

import bot_driver  # noqa: E402


def _db_disponible():
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM transaction_drafts LIMIT 1")
            cur.close()
            return True
        finally:
            put_conn(conn)
    except Exception:
        return False


_DB_OK = _db_disponible()


@unittest.skipUnless(_DB_OK, "BD o tablas del bot no disponibles")
class TestReplyCompletar(unittest.TestCase):

    def setUp(self):
        from db_pool import get_conn, put_conn
        self.get_conn, self.put_conn = get_conn, put_conn
        self.sufijo = uuid.uuid4().hex[:8]
        self.ext_ids = []
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM hub_users ORDER BY created_at LIMIT 1")
            self.uid = str(cur.fetchone()[0])
            self.chat_id = f"test-09g-{self.sufijo}"
            cur.execute("""
                INSERT INTO bot_chat_links (channel, chat_id, hub_user_id, default_portfolio, status)
                VALUES ('telegram', %s, %s, 'Personal', 'ACTIVO') RETURNING id
            """, (self.chat_id, self.uid))
            self.link_id = cur.fetchone()[0]
            cur.execute("SELECT name FROM portfolios ORDER BY id LIMIT 1")
            portafolio = cur.fetchone()[0]
            payload = {"type": "GASTO", "amount": 11900.0, "concept": "Transferencia (SMS)",
                       "payment_method": "", "category": "Otros Gastos",
                       "third_party": {"identification_type": "NIT",
                                       "identification_number": "999999999", "name": "Sin especificar"},
                       "transaction_date": "2026-09-21", "portfolio_name": portafolio,
                       "inferred_fields": ["third_party", "type"], "missing_fields": ["cuenta"]}
            cur.execute("""
                INSERT INTO transaction_drafts (chat_link_id, user_id, channel, portfolio_name, status,
                                                payload, raw_text, bot_summary_message_id)
                VALUES (%s, %s, 'sms', %s, 'BORRADOR', %s, 'sms', %s) RETURNING id
            """, (self.link_id, self.uid, portafolio, json.dumps(payload), f"m-{self.sufijo}"))
            self.draft_id = cur.fetchone()[0]
            conn.commit()
        finally:
            self.put_conn(conn)

    def tearDown(self):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM transaction_drafts WHERE chat_link_id = %s", (self.link_id,))
            cur.execute("DELETE FROM bot_messages WHERE chat_link_id = %s OR external_message_id = ANY(%s)",
                        (self.link_id, self.ext_ids or [""]))
            cur.execute("DELETE FROM bot_chat_links WHERE id = %s", (self.link_id,))
            cur.execute("DELETE FROM third_parties WHERE name = %s", (f"Tercero Prueba {self.sufijo}",))
            conn.commit()
        finally:
            self.put_conn(conn)

    def _reply(self, texto):
        ext = f"t09g-{uuid.uuid4().hex[:12]}"
        self.ext_ids.append(ext)
        return bot_driver.handle_message({
            "channel": "telegram", "chat_id": self.chat_id, "external_message_id": ext,
            "kind": "text", "text": texto, "media_path": None,
            "reply_to_message_id": f"m-{self.sufijo}",
        })

    def _payload(self):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT payload FROM transaction_drafts WHERE id = %s", (self.draft_id,))
            p = cur.fetchone()[0]
            return p if isinstance(p, dict) else json.loads(p)
        finally:
            self.put_conn(conn)

    def test_reply_concepto_literal(self):                                  # CA-09G-04
        r = self._reply("Concepto: arriendo septiembre")
        self.assertIsInstance(r, dict)
        self.assertEqual(r["draft_id"], self.draft_id)
        self.assertIn("arriendo septiembre", r["text"])
        self.assertEqual(self._payload()["concept"], "arriendo septiembre")

    def test_reply_tercero_nuevo_crea_y_asigna(self):
        nombre = f"Tercero Prueba {self.sufijo}"
        r = self._reply(f"Tercero nuevo: {nombre}")
        self.assertIsInstance(r, dict, r)
        p = self._payload()
        self.assertEqual(p["third_party"]["name"], nombre)
        self.assertTrue(p["third_party"]["identification_number"].startswith("SN-"))
        self.assertNotIn("third_party", p["inferred_fields"])

    def test_reply_tercero_inexistente_explica(self):
        r = self._reply(f"Tercero: nadie-{self.sufijo}")
        self.assertIsInstance(r, str)
        self.assertIn("No encontré", r)
        self.assertEqual(self._payload()["third_party"]["name"], "Sin especificar")

    def test_reply_a_mensaje_ajeno_cae_al_registrador_normal(self):
        # reply a un message_id que no es de ningún borrador → flujo normal
        # (un comando determinista, para no tocar el LLM)
        ext = f"t09g-{uuid.uuid4().hex[:12]}"
        self.ext_ids.append(ext)
        r = bot_driver.handle_message({
            "channel": "telegram", "chat_id": self.chat_id, "external_message_id": ext,
            "kind": "text", "text": "/borradores", "media_path": None,
            "reply_to_message_id": "otro-mensaje",
        })
        self.assertIsInstance(r, str)
        self.assertIn(f"#{self.draft_id}", r)


if __name__ == "__main__":
    unittest.main()
