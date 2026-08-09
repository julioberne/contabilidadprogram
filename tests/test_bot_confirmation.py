# -*- coding: utf-8 -*-
"""Tests de integración de la máquina de estados del borrador (contra Supabase).

SOLO tocan las tablas del bot (transaction_drafts, bot_messages) — jamás crean
transacciones ni asientos. Se saltan solos si la BD o las tablas no están
disponibles (p.ej. antes de correr scripts/migrate_bot_tables.py).

Ejecutar:  .venv\\Scripts\\python.exe -m unittest discover -s tests -p "test_bot_*.py" -v
"""
import json
import os
import sys
import unittest
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

# .env (mismo loader del proyecto)
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


@unittest.skipUnless(_DB_OK, "BD o tablas del bot no disponibles (correr migrate_bot_tables.py)")
class TestMaquinaDeEstados(unittest.TestCase):
    """Concurrencia y transiciones — sin crear jamás una transacción real."""

    def setUp(self):
        from db_pool import get_conn, put_conn
        self.get_conn, self.put_conn = get_conn, put_conn
        self._draft_ids = []
        self._msg_ext_ids = []

    def tearDown(self):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            if self._draft_ids:
                cur.execute("DELETE FROM transaction_drafts WHERE id = ANY(%s)",
                            (self._draft_ids,))
            if self._msg_ext_ids:
                cur.execute("DELETE FROM bot_messages WHERE external_message_id = ANY(%s)",
                            (self._msg_ext_ids,))
            conn.commit()
        finally:
            self.put_conn(conn)

    def _crear_draft(self, payload, status="BORRADOR"):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO transaction_drafts (channel, portfolio_name, status, payload, raw_text)
                VALUES ('telegram', %s, %s, %s, 'TS-TEST') RETURNING id
            """, (payload.get("portfolio_name", "TS-TEST"), status, json.dumps(payload)))
            draft_id = cur.fetchone()[0]
            conn.commit()
            self._draft_ids.append(draft_id)
            return draft_id
        finally:
            self.put_conn(conn)

    def _status(self, draft_id):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT status, error FROM transaction_drafts WHERE id = %s", (draft_id,))
            return cur.fetchone()
        finally:
            self.put_conn(conn)

    def test_confirmar_con_faltantes_revierte_a_borrador(self):
        # amount None → la validación bloquea ANTES de tocar el pipeline oficial
        draft_id = self._crear_draft({"portfolio_name": "TS-TEST", "type": "GASTO",
                                      "amount": None, "concept": ""})
        respuesta = bot_driver.confirmar_draft(draft_id)
        self.assertIn("No se pudo confirmar", respuesta)
        status, error = self._status(draft_id)
        self.assertEqual(status, "BORRADOR")      # PROCESANDO → revertido
        self.assertIn("monto", error)

    def test_procesando_reciente_no_se_puede_tomar(self):
        draft_id = self._crear_draft({"amount": None}, status="PROCESANDO")
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE transaction_drafts SET updated_at = NOW() WHERE id = %s",
                        (draft_id,))
            conn.commit()
        finally:
            self.put_conn(conn)
        respuesta = bot_driver.confirmar_draft(draft_id)
        self.assertIn("procesando", respuesta.lower())
        self.assertEqual(self._status(draft_id)[0], "PROCESANDO")

    def test_descartar_y_doble_descarte(self):
        draft_id = self._crear_draft({"amount": 1, "concept": "x"})
        r1 = bot_driver.descartar_draft(draft_id)
        self.assertIn("descartado", r1)
        self.assertEqual(self._status(draft_id)[0], "DESCARTADO")
        r2 = bot_driver.descartar_draft(draft_id)
        self.assertIn("ya estaba descartado", r2)

    def test_confirmar_borrador_ajeno_es_rechazado(self):
        draft_id = self._crear_draft({"amount": 1, "concept": "x"})
        # chat_link_id=-1 jamás coincide con el dueño (NULL) del draft de prueba
        respuesta = bot_driver.confirmar_draft(draft_id, chat_link_id=-1)
        self.assertIn("no pertenece", respuesta)
        self.assertEqual(self._status(draft_id)[0], "BORRADOR")

    def test_dedupe_de_mensajes_entrantes(self):
        ext_id = f"ts-test-{uuid.uuid4().hex[:12]}"
        self._msg_ext_ids.append(ext_id)
        msg = {"channel": "telegram", "chat_id": "ts-test-chat",
               "external_message_id": ext_id, "kind": "text", "text": "hola"}
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            primero = bot_driver._registrar_entrante(cur, msg)
            segundo = bot_driver._registrar_entrante(cur, msg)
            conn.commit()
        finally:
            self.put_conn(conn)
        self.assertIsNotNone(primero)   # primera vez: se procesa
        self.assertIsNone(segundo)      # reintento/re-poll: duplicado ignorado


if __name__ == "__main__":
    unittest.main()
