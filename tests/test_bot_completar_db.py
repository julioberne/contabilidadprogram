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
            cur.execute("DELETE FROM third_parties WHERE name ILIKE %s", (f"%{self.sufijo}%",))
            conn.commit()
        finally:
            self.put_conn(conn)

    def _terceros(self):
        """Terceros de ESTE test (su nombre lleva el sufijo único)."""
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, identification_type, identification_number, name, phone, email
                  FROM third_parties WHERE name ILIKE %s ORDER BY id
            """, (f"%{self.sufijo}%",))
            return cur.fetchall()
        finally:
            self.put_conn(conn)

    @staticmethod
    def _doc():
        return "99" + str(uuid.uuid4().int)[:9]

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
        self.assertIsInstance(r, dict, r)
        self.assertIn("No encontré", r["text"])
        self.assertIn("cc", r["text"])                       # le dice cómo crearlo
        self.assertEqual(self._payload()["third_party"]["name"], "Sin especificar")
        self.assertEqual(self._terceros(), [])               # sin documento NO se crea solo

    def test_caso_real_dos_lineas_concepto_y_tercero_con_cc(self):
        """El reply de Andrés del 30-sep: concepto + «Tercero : nombre cc N»."""
        doc = self._doc()
        r = self._reply(f"abono cuota  1V\nTercero : Prueba {self.sufijo} Molina  cc {doc}")
        self.assertIsInstance(r, dict, r)
        self.assertIn("Tercero CREADO", r["text"])
        p = self._payload()
        self.assertEqual(p["concept"], "abono cuota 1V")     # la línea del tercero NO entra al concepto
        self.assertEqual(p["third_party"]["name"], f"Prueba {self.sufijo} Molina")
        self.assertEqual(p["third_party"]["identification_number"], doc)
        self.assertEqual(p["third_party"]["identification_type"], "CC")
        self.assertNotIn("third_party", p["inferred_fields"])
        self.assertEqual(len(self._terceros()), 1)

        # Otra vez, escrito distinto pero con el MISMO documento → no duplica
        r2 = self._reply(f"Tercero: PRUEBA {self.sufijo}  c.c. {doc[:2]}.{doc[2:]}")
        self.assertIn("👤 Tercero →", r2["text"])
        self.assertNotIn("CREADO", r2["text"])
        self.assertEqual(len(self._terceros()), 1)
        self.assertEqual(self._payload()["third_party"]["identification_number"], doc)

    def test_celular_y_correo_dictados_quedan_en_la_ficha(self):
        doc = self._doc()
        self._reply(f"Tercero: Prueba {self.sufijo} Ruiz cc {doc} cel 300 123 4567 p{self.sufijo}@correo.com")
        fila = self._terceros()[0]
        self.assertEqual((fila[2], fila[4], fila[5]), (doc, "3001234567", f"p{self.sufijo}@correo.com"))

    def test_parecido_sin_documento_se_completa_al_elegirlo(self):
        nombre = f"Tercero Prueba {self.sufijo}"
        self._reply(f"Tercero nuevo: {nombre}")                          # nace provisional SN-…
        tp_id = self._terceros()[0][0]
        doc = self._doc()
        r = self._reply(f"Tercero: tercero prueba {self.sufijo} cc {doc}")
        self.assertIn("parecidos", r["text"])
        datas = [d for fila in r["buttons"] for _, d in fila]
        self.assertIn(f"tpset:{self.draft_id}:{tp_id}", datas)
        self.assertIn(f"tpnew:{self.draft_id}", datas)
        self.assertIn("tercero_pendiente", self._payload())

        out = bot_driver.handle_callback("telegram", self.chat_id, f"tpset:{self.draft_id}:{tp_id}")
        self.assertIn("completado", out["edit_text"])
        filas = self._terceros()
        self.assertEqual(len(filas), 1)                                  # NO se duplicó
        self.assertEqual(filas[0][2], doc)                               # la ficha quedó con su cédula
        p = self._payload()
        self.assertEqual(p["third_party"]["identification_number"], doc)
        self.assertNotIn("tercero_pendiente", p)

    def test_parecido_pero_es_otra_persona_crear_nuevo(self):
        nombre = f"Tercero Prueba {self.sufijo}"
        self._reply(f"Tercero nuevo: {nombre}")
        doc = self._doc()
        self._reply(f"Tercero: {nombre} cc {doc}")
        out = bot_driver.handle_callback("telegram", self.chat_id, f"tpnew:{self.draft_id}")
        self.assertIn("CREADO", out["edit_text"])
        filas = self._terceros()
        self.assertEqual(len(filas), 2)                                  # decisión explícita del humano
        self.assertEqual(self._payload()["third_party"]["identification_number"], doc)
        # el botón ya no sirve dos veces
        out2 = bot_driver.handle_callback("telegram", self.chat_id, f"tpnew:{self.draft_id}")
        self.assertIn("Ya no tengo", out2["alert"])
        self.assertEqual(len(self._terceros()), 2)

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
