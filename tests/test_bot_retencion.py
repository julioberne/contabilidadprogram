# -*- coding: utf-8 -*-
"""Tests de integración de la retención 30/60/90 (etapa 09.F, CA-09F-08).

Crean borradores y mensajes con fechas viejas bajo un chat de prueba, corren
purgar() con un send_fn falso y limpian lo que quede. Jamás tocan CONFIRMADOS
reales: el CONFIRMADO del test es propio (sin transacción asociada).

Ejecutar:  .venv\\Scripts\\python.exe -m unittest tests.test_bot_retencion -v
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

import bot_retencion  # noqa: E402


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
class TestRetencion(unittest.TestCase):

    def setUp(self):
        from db_pool import get_conn, put_conn
        self.get_conn, self.put_conn = get_conn, put_conn
        self.enviados = []
        self.send_fn = lambda chat_id, text, buttons=None: self.enviados.append((chat_id, text))
        self.draft_ids = []
        self.msg_ids = []
        os.environ["BOT_RETENCION_ACTIVA"] = "1"
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM hub_users ORDER BY created_at LIMIT 1")
            self.uid = str(cur.fetchone()[0])
            self.chat_id = f"test-ret-{uuid.uuid4().hex[:8]}"
            cur.execute("""
                INSERT INTO bot_chat_links (channel, chat_id, hub_user_id, default_portfolio, status)
                VALUES ('telegram', %s, %s, 'Personal', 'ACTIVO') RETURNING id
            """, (self.chat_id, self.uid))
            self.link_id = cur.fetchone()[0]
            conn.commit()
        finally:
            self.put_conn(conn)

    def tearDown(self):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM transaction_drafts WHERE chat_link_id = %s", (self.link_id,))
            cur.execute("DELETE FROM bot_messages WHERE chat_link_id = %s", (self.link_id,))
            cur.execute("DELETE FROM bot_chat_links WHERE id = %s", (self.link_id,))
            conn.commit()
        finally:
            self.put_conn(conn)

    def _draft(self, status, dias):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO transaction_drafts (chat_link_id, channel, portfolio_name, status,
                                                payload, raw_text, created_at, updated_at)
                VALUES (%s, 'sms', 'Personal', %s, %s, 'test retención',
                        NOW() - INTERVAL '%s days', NOW() - INTERVAL '%s days')
                RETURNING id
            """ % ("%s", "%s", "%s", int(dias), int(dias)),
                (self.link_id, status, json.dumps({"amount": 1, "concept": "t"})))
            did = cur.fetchone()[0]
            conn.commit()
            self.draft_ids.append(did)
            return did
        finally:
            self.put_conn(conn)

    def _msg(self, dias, draft_id=None):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO bot_messages (chat_link_id, raw_chat_id, direction, channel, kind,
                                          content, draft_id, created_at)
                VALUES (%s, %s, 'IN', 'sms', 'sms', 'viejo', %s, NOW() - INTERVAL '%s days')
                RETURNING id
            """ % ("%s", "%s", "%s", int(dias)), (self.link_id, self.uid, draft_id))
            mid = cur.fetchone()[0]
            conn.commit()
            self.msg_ids.append(mid)
            return mid
        finally:
            self.put_conn(conn)

    def _estado(self, draft_id):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT status FROM transaction_drafts WHERE id = %s", (draft_id,))
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            self.put_conn(conn)

    def _msg_existe(self, mid):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM bot_messages WHERE id = %s", (mid,))
            return cur.fetchone() is not None
        finally:
            self.put_conn(conn)

    def test_descartado_31_dias_se_borra_y_29_se_queda(self):
        viejo = self._draft("DESCARTADO", 31)
        joven = self._draft("DESCARTADO", 29)
        res = bot_retencion.purgar(self.send_fn)
        self.assertGreaterEqual(res["descartados_borrados"], 1)
        self.assertIsNone(self._estado(viejo))
        self.assertEqual(self._estado(joven), "DESCARTADO")

    def test_borrador_y_error_61_dias_pasan_a_descartado_con_aviso(self):
        b = self._draft("BORRADOR", 61)
        e = self._draft("ERROR", 61)
        joven = self._draft("BORRADOR", 59)
        bot_retencion.purgar(self.send_fn)
        self.assertEqual(self._estado(b), "DESCARTADO")
        self.assertEqual(self._estado(e), "DESCARTADO")
        self.assertEqual(self._estado(joven), "BORRADOR")
        avisos = [t for c, t in self.enviados if c == self.chat_id]
        self.assertEqual(len(avisos), 1)
        self.assertIn(f"#{b}", avisos[0])
        self.assertIn(f"#{e}", avisos[0])

    def test_confirmado_nunca_se_toca(self):
        c = self._draft("CONFIRMADO", 400)
        bot_retencion.purgar(self.send_fn)
        self.assertEqual(self._estado(c), "CONFIRMADO")

    def test_mensaje_91_dias_sin_borrador_se_borra_y_con_borrador_vivo_se_queda(self):
        suelto = self._msg(91)
        vivo = self._draft("BORRADOR", 1)
        con_draft = self._msg(91, draft_id=vivo)
        bot_retencion.purgar(self.send_fn)
        self.assertFalse(self._msg_existe(suelto))
        self.assertTrue(self._msg_existe(con_draft))

    def test_kill_switch(self):
        os.environ["BOT_RETENCION_ACTIVA"] = "0"
        try:
            viejo = self._draft("DESCARTADO", 40)
            res = bot_retencion.purgar(self.send_fn)
            self.assertEqual(res, {"descartados_borrados": 0, "borradores_vencidos": 0, "mensajes_borrados": 0})
            self.assertEqual(self._estado(viejo), "DESCARTADO")
        finally:
            os.environ["BOT_RETENCION_ACTIVA"] = "1"


if __name__ == "__main__":
    unittest.main()
