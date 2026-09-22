# -*- coding: utf-8 -*-
"""Tests de integración del tick de SMS (etapa 09.F, CA-09F-06) contra Supabase.

SOLO tocan bot_chat_links (un chat de prueba con chat_id 'test-…'), bot_messages
y transaction_drafts — jamás crean transacciones ni asientos. El envío a
Telegram se reemplaza por una función falsa. Se saltan solos sin BD.

Ejecutar:  .venv\\Scripts\\python.exe -m unittest tests.test_bot_sms_db -v
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

import bot_sms  # noqa: E402

SMS = ("Bancolombia: Transferiste $11,900.00 desde tu cuenta *3037 a la cuenta "
       "*3193301184 el 21/09/26 a las 20:00. ¿Dudas? Llamanos al 018000931987.")


def _db_disponible():
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM transaction_drafts LIMIT 1")
            cur.execute("SELECT 1 FROM sms_ingest_tokens LIMIT 1")
            cur.close()
            return True
        finally:
            put_conn(conn)
    except Exception:
        return False


_DB_OK = _db_disponible()


class _ConChatDePrueba(unittest.TestCase):
    """Base: un chat de Telegram de prueba (chat_id 'test-…') y limpieza total."""

    def setUp(self):
        from db_pool import get_conn, put_conn
        self.get_conn, self.put_conn = get_conn, put_conn
        self.enviados = []
        self.send_fn = lambda chat_id, text, buttons=None: self.enviados.append((chat_id, text, buttons)) or 777
        self.ext_ids = []
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM hub_users ORDER BY created_at LIMIT 1")
            self.uid = str(cur.fetchone()[0])
            self.chat_id = f"test-{uuid.uuid4().hex[:10]}"
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
            cur.execute("DELETE FROM bot_messages WHERE chat_link_id = %s OR external_message_id = ANY(%s)",
                        (self.link_id, self.ext_ids or [""]))
            cur.execute("DELETE FROM bot_chat_links WHERE id = %s", (self.link_id,))
            conn.commit()
        finally:
            self.put_conn(conn)

    def _encolar(self, texto, kind="sms", content=None, link=True):
        ext = uuid.uuid4().hex[:32]
        self.ext_ids.append(ext)
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO bot_messages (chat_link_id, raw_chat_id, direction, channel,
                                          external_message_id, kind, content)
                VALUES (%s, %s, 'IN', 'sms', %s, %s, %s) RETURNING id
            """, (self.link_id if link else None, self.uid, ext, kind,
                  content if content is not None else json.dumps({"from": "85540", "text": texto})))
            mid = cur.fetchone()[0]
            conn.commit()
            return mid
        finally:
            self.put_conn(conn)

    def _fila(self, msg_id):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT kind, draft_id, chat_link_id FROM bot_messages WHERE id = %s", (msg_id,))
            return cur.fetchone()
        finally:
            self.put_conn(conn)


@unittest.skipUnless(_DB_OK, "BD o tablas 09.F no disponibles (correr migrate_sms_bancolombia.py)")
class TestTickSms(_ConChatDePrueba):

    def test_sms_pendiente_crea_borrador_canal_sms_y_envia(self):          # CA-09F-06
        mid = self._encolar(SMS)
        n = bot_sms.procesar_pendientes(self.send_fn)
        self.assertGreaterEqual(n, 1)
        kind, draft_id, _ = self._fila(mid)
        self.assertEqual(kind, "sms")
        self.assertIsNotNone(draft_id)
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT channel, status, payload, raw_text, chat_link_id, bot_summary_message_id "
                        "FROM transaction_drafts WHERE id = %s", (draft_id,))
            ch, st, payload, raw, link, summary_mid = cur.fetchone()
        finally:
            self.put_conn(conn)
        payload = payload if isinstance(payload, dict) else json.loads(payload)
        self.assertEqual((ch, st, raw, link), ("sms", "BORRADOR", SMS, self.link_id))
        self.assertEqual(payload["amount"], 11900.0)
        self.assertEqual(payload["transaction_date"], "2026-09-21")
        self.assertEqual(payload["sms"]["familia"], "transferencia_enviada")
        self.assertEqual(summary_mid, "777")
        mios = [e for e in self.enviados if e[0] == self.chat_id]
        self.assertEqual(len(mios), 1)
        self.assertIn("📲 SMS Bancolombia", mios[0][1])
        self.assertIn(f"BORRADOR #{draft_id}", mios[0][1])
        self.assertEqual(mios[0][2][0][0][1], f"ok:{draft_id}")      # botón ✅ Confirmar

    def test_segunda_pasada_no_duplica(self):
        self._encolar(SMS)
        bot_sms.procesar_pendientes(self.send_fn)
        antes = len(self.enviados)
        bot_sms.procesar_pendientes(self.send_fn)
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM transaction_drafts WHERE chat_link_id = %s", (self.link_id,))
            self.assertEqual(cur.fetchone()[0], 1)
        finally:
            self.put_conn(conn)
        self.assertEqual(len([e for e in self.enviados if e[0] == self.chat_id]),
                         len([e for e in self.enviados[:antes] if e[0] == self.chat_id]))

    def test_fila_envenenada_queda_sms_error_y_no_bloquea(self):
        malo = self._encolar("", content="{esto no es json")
        bueno = self._encolar(SMS)
        bot_sms.procesar_pendientes(self.send_fn)
        self.assertEqual(self._fila(malo)[0], "sms_error")
        self.assertIsNone(self._fila(malo)[1])
        self.assertIsNotNone(self._fila(bueno)[1])
        avisos = [e for e in self.enviados if e[0] == self.chat_id and "No pude convertir" in e[1]]
        self.assertEqual(len(avisos), 1)
        # Una tercera pasada no vuelve a tomar la fila envenenada
        antes = len(self.enviados)
        bot_sms.procesar_pendientes(self.send_fn)
        self.assertEqual(len(self.enviados), antes)

    def test_sms_sin_chat_se_repara_con_el_link_activo(self):
        mid = self._encolar(SMS, kind="sms_sin_chat", link=False)
        bot_sms.procesar_pendientes(self.send_fn)
        kind, draft_id, link = self._fila(mid)
        self.assertEqual((kind, link), ("sms", self.link_id))
        self.assertIsNotNone(draft_id)

    def test_no_reconocido_crea_borrador_sin_monto(self):
        mid = self._encolar("Bancolombia: Compraste $45,000.00 en EXITO con tu T.Deb *7706 el 21/09/26.")
        bot_sms.procesar_pendientes(self.send_fn)
        _, draft_id, _ = self._fila(mid)
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT payload FROM transaction_drafts WHERE id = %s", (draft_id,))
            payload = cur.fetchone()[0]
        finally:
            self.put_conn(conn)
        payload = payload if isinstance(payload, dict) else json.loads(payload)
        self.assertIsNone(payload["amount"])
        self.assertIn("monto", payload["missing_fields"])
        texto = [e for e in self.enviados if e[0] == self.chat_id][0][1]
        self.assertIn("no reconocido", texto)


@unittest.skipUnless(_DB_OK, "BD o tablas 09.F no disponibles")
class TestConfirmarPorId(_ConChatDePrueba):
    """CA-09F-07 / R-09F-08: la confirmación usa payload.account_id aunque el
    nombre de la cuenta haya cambiado. transaction_service.create_transaction
    se reemplaza por un doble: JAMÁS se crea una transacción real."""

    def _draft_directo(self, payload):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM portfolios ORDER BY id LIMIT 1")
            payload["portfolio_name"] = cur.fetchone()[0]
            cur.execute("""
                INSERT INTO transaction_drafts (chat_link_id, user_id, channel, portfolio_name,
                                                status, payload, raw_text)
                VALUES (%s, %s, 'sms', %s, 'BORRADOR', %s, 'test') RETURNING id
            """, (self.link_id, self.uid, payload["portfolio_name"], json.dumps(payload)))
            did = cur.fetchone()[0]
            conn.commit()
            return did
        finally:
            self.put_conn(conn)

    def _cuenta_real(self):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM user_accounts ORDER BY id LIMIT 1")
            return cur.fetchone()
        finally:
            self.put_conn(conn)

    def _payload(self, account_id, payment_method):
        return {"type": "GASTO", "amount": 11900.0, "concept": "test id",
                "payment_method": payment_method, "category": "Otros Gastos",
                "third_party": {"identification_type": "NIT", "identification_number": "999999999",
                                "name": "Sin especificar"},
                "transaction_date": "2026-09-21", "apply_iva": False, "apply_gmf": False,
                "account_id": account_id}

    def test_confirmar_usa_account_id_aunque_el_nombre_no_coincida(self):
        from unittest import mock
        import bot_driver
        import transaction_service
        acc_id, _ = self._cuenta_real()
        did = self._draft_directo(self._payload(acc_id, "nombre que ya no existe"))
        capturado = {}

        def _fake(tx_input):
            capturado["account_id"] = tx_input.account_id
            return {"transaction_id": None, "journal": "fake"}   # → ERROR, sin transacción
        with mock.patch.object(transaction_service, "create_transaction", side_effect=_fake):
            msg = bot_driver.confirmar_draft(did, chat_link_id=self.link_id)
        self.assertEqual(capturado.get("account_id"), acc_id)
        self.assertIn("ERROR", msg)                     # el doble no creó asiento: estado ERROR esperado

    def test_sin_account_id_y_nombre_invalido_no_confirma(self):
        import bot_driver
        did = self._draft_directo(self._payload(None, "nombre que ya no existe"))
        msg = bot_driver.confirmar_draft(did, chat_link_id=self.link_id)
        self.assertIn("No se pudo confirmar", msg)
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT status FROM transaction_drafts WHERE id = %s", (did,))
            self.assertEqual(cur.fetchone()[0], "BORRADOR")
        finally:
            self.put_conn(conn)

    def test_editar_payment_method_borra_account_id(self):
        import bot_driver
        acc_id, _ = self._cuenta_real()
        did = self._draft_directo(self._payload(acc_id, "x"))
        res = bot_driver.editar_draft(did, {"payment_method": "Efectivo"}, hub_user_id=self.uid)
        self.assertIsNone(res.get("error"), res)
        self.assertIsNone(res["payload"]["account_id"])


if __name__ == "__main__":
    unittest.main()
