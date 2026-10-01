# -*- coding: utf-8 -*-
"""Etapa 09.I — Mini App de Telegram (v1): tests CON BD (solo local).

La BD es compartida con producción: el chat de prueba usa el canal 'whatsapp'
(el poller real solo atiende 'telegram', así que jamás toma estos borradores),
los terceros llevan sufijo único y todo se borra en tearDown. No se crean
transacciones.
"""
import json
import os
import sys
import unittest
import uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "fin_sys_core"))
_env = os.path.join(ROOT, ".env")
if os.path.exists(_env):
    for _line in open(_env, encoding="utf-8"):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

import fin_sys_core  # noqa: E402,F401

try:
    from db_pool import get_conn, put_conn   # noqa: E402
    _c = get_conn()
    _c.cursor().execute("SELECT 1 FROM transaction_drafts LIMIT 1")
    put_conn(_c)
    _OK = True
except Exception:   # pragma: no cover
    _OK = False


@unittest.skipUnless(_OK, "BD no disponible")
class _Base(unittest.TestCase):

    def setUp(self):
        import bot_driver
        self.bot = bot_driver
        self.sufijo = "x" + uuid.uuid4().hex[:7]
        self.terceros = []
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM hub_users ORDER BY created_at LIMIT 1")
            self.uid = str(cur.fetchone()[0])
            self.chat_id = f"test-tg-{self.sufijo}"
            # canal 'whatsapp': el tick de producción (canal 'telegram') no lo ve
            cur.execute("""
                INSERT INTO bot_chat_links (channel, chat_id, hub_user_id, default_portfolio, status)
                VALUES ('whatsapp', %s, %s, 'Personal', 'ACTIVO') RETURNING id
            """, (self.chat_id, self.uid))
            self.link_id = cur.fetchone()[0]
            cur.execute("SELECT name FROM portfolios ORDER BY id LIMIT 1")
            portafolio = cur.fetchone()[0]
            payload = {"type": "GASTO", "amount": 50000.0, "concept": "Transferencia (SMS)",
                       "payment_method": "", "category": "Otros Gastos",
                       "third_party": {"identification_type": "NIT",
                                       "identification_number": "999999999", "name": "Sin especificar"},
                       "transaction_date": "2026-10-01", "portfolio_name": portafolio,
                       "inferred_fields": ["third_party", "type"], "missing_fields": ["cuenta"]}
            cur.execute("""
                INSERT INTO transaction_drafts (chat_link_id, user_id, channel, portfolio_name, status,
                                                payload, raw_text, bot_summary_message_id)
                VALUES (%s, %s, 'sms', %s, 'BORRADOR', %s, 'sms', %s) RETURNING id
            """, (self.link_id, self.uid, portafolio, json.dumps(payload), f"m-{self.sufijo}"))
            self.draft_id = cur.fetchone()[0]
            conn.commit()
        finally:
            put_conn(conn)

    def tearDown(self):
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM transaction_drafts WHERE chat_link_id = %s", (self.link_id,))
            cur.execute("DELETE FROM bot_messages WHERE chat_link_id = %s", (self.link_id,))
            cur.execute("DELETE FROM bot_chat_links WHERE id = %s", (self.link_id,))
            if self.terceros:
                cur.execute("DELETE FROM third_parties WHERE id = ANY(%s)", (self.terceros,))
            conn.commit()
        finally:
            put_conn(conn)

    def _payload(self):
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT payload, bot_summary_message_id FROM transaction_drafts WHERE id = %s",
                        (self.draft_id,))
            p, mid = cur.fetchone()
            return (p if isinstance(p, dict) else json.loads(p)), mid
        finally:
            put_conn(conn)


class TestAvisoAlChat(_Base):

    def test_marcar_y_reenviar_el_resumen(self):
        self.assertTrue(self.bot.marcar_aviso_chat(self.draft_id, hub_user_id=self.uid))
        self.assertTrue(self._payload()[0].get("avisar_chat"))

        enviados = []

        def send(chat_id, texto, botones=None):
            enviados.append((chat_id, texto, botones))
            return 777

        self.assertEqual(self.bot.avisar_chat_pendientes(send, canal="whatsapp"), 1)
        self.assertEqual(len(enviados), 1)
        chat_id, texto, botones = enviados[0]
        self.assertEqual(chat_id, self.chat_id)
        self.assertIn("Borrador actualizado", texto)
        self.assertIn(f"#{self.draft_id}", texto)
        datas = [d for fila in botones for _, d in fila]
        self.assertIn(f"ok:{self.draft_id}", datas)
        self.assertTrue(any(d.startswith("webapp:") for d in datas))
        payload, mid = self._payload()
        self.assertNotIn("avisar_chat", payload)          # la marca se quita
        self.assertEqual(str(mid), "777")                  # el resumen nuevo es el vigente
        # segunda vuelta: nada pendiente
        self.assertEqual(self.bot.avisar_chat_pendientes(send, canal="whatsapp"), 0)
        self.assertEqual(len(enviados), 1)

    def test_no_marca_el_borrador_de_otro_usuario(self):
        self.assertFalse(self.bot.marcar_aviso_chat(self.draft_id, hub_user_id=str(uuid.uuid4())))
        self.assertNotIn("avisar_chat", self._payload()[0])

    def test_un_fallo_de_envio_no_reintenta_en_bucle(self):
        self.bot.marcar_aviso_chat(self.draft_id, hub_user_id=self.uid)

        def send_roto(chat_id, texto, botones=None):
            raise RuntimeError("telegram caído")

        self.assertEqual(self.bot.avisar_chat_pendientes(send_roto, canal="whatsapp"), 0)
        self.assertNotIn("avisar_chat", self._payload()[0])   # la marca ya no está: no se reintenta solo

    def test_telegram_devuelve_none_no_cuenta_como_enviado(self):
        """El adaptador real no lanza: devuelve None ante un error de Telegram."""
        self.bot.marcar_aviso_chat(self.draft_id, hub_user_id=self.uid)
        self.assertEqual(self.bot.avisar_chat_pendientes(lambda *a, **k: None, canal="whatsapp"), 0)
        payload, mid = self._payload()
        self.assertNotIn("avisar_chat", payload)
        self.assertEqual(str(mid), f"m-{self.sufijo}")        # el resumen vigente no cambió
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM bot_messages WHERE chat_link_id = %s AND direction = 'OUT'", (self.link_id,))
            self.assertEqual(cur.fetchone()[0], 0)              # nada se audita como enviado
        finally:
            put_conn(conn)

    def test_la_segunda_edicion_no_se_pierde(self):
        """Revisión 1-oct: la marca se quita y el payload se lee en una sola sentencia,
        así que si el humano edita de nuevo antes del envío, sale la versión más reciente."""
        self.bot.marcar_aviso_chat(self.draft_id, hub_user_id=self.uid)
        self.bot.editar_draft(self.draft_id, {"concept": "segunda edición"}, hub_user_id=self.uid)
        self.bot.marcar_aviso_chat(self.draft_id, hub_user_id=self.uid)
        textos = []
        self.assertEqual(self.bot.avisar_chat_pendientes(lambda c, t, b=None: textos.append(t) or 5, canal="whatsapp"), 1)
        self.assertIn("segunda edición", textos[0])
        self.assertEqual(self.bot.avisar_chat_pendientes(lambda c, t, b=None: 6, canal="whatsapp"), 0)


class TestRouter(_Base):

    def setUp(self):
        super().setUp()
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers import bot as rb
        from routers import cartera as rc
        from routers.auth_guard import require_admin, require_auth
        app = FastAPI()
        app.include_router(rb.router)
        app.include_router(rc.router)
        usuario = {"uid": self.uid, "role": "owner"}
        app.dependency_overrides[require_auth] = lambda: usuario
        app.dependency_overrides[require_admin] = lambda: usuario
        self.client = TestClient(app)

    def _nombre(self, base):
        return f"{base} {self.sufijo}"

    def test_crear_sin_documento_dos_veces_no_falla(self):
        r1 = self.client.post("/api/third-parties", json={"name": self._nombre("Prov Uno")})
        self.assertEqual(r1.status_code, 200, r1.text)
        self.terceros.append(r1.json()["id"])
        self.assertTrue(r1.json()["provisional"])
        self.assertTrue(r1.json()["identification_number"].startswith("SN-"))
        r2 = self.client.post("/api/third-parties", json={"name": self._nombre("Prov Dos"), "identification_number": ""})
        self.assertEqual(r2.status_code, 200, r2.text)      # antes: 500 por el UNIQUE sobre ''
        self.terceros.append(r2.json()["id"])
        self.assertNotEqual(r1.json()["identification_number"], r2.json()["identification_number"])

    def test_documento_repetido_responde_409_con_la_ficha(self):
        numero = "9" + self.sufijo[1:].encode().hex()[:9]      # dígitos imposibles de chocar con datos reales
        r1 = self.client.post("/api/third-parties", json={"name": self._nombre("Dueña"), "identification_type": "CC",
                                                          "identification_number": numero})
        self.assertEqual(r1.status_code, 200, r1.text)
        self.terceros.append(r1.json()["id"])
        r2 = self.client.post("/api/third-parties", json={"name": self._nombre("Otra Persona"),
                                                          "identification_number": numero})
        self.assertEqual(r2.status_code, 409, r2.text)
        cuerpo = r2.json()
        self.assertEqual(cuerpo["codigo"], "existe")
        self.assertEqual(cuerpo["tercero"]["id"], r1.json()["id"])
        self.assertIn("ya pertenece", cuerpo["detail"])
        self.assertIn(self._nombre("Dueña"), cuerpo["detail"])

    def test_editar_la_ficha_con_el_contrato_del_post(self):
        numero = "9" + self.sufijo[1:].encode().hex()[:9]
        a = self.client.post("/api/third-parties", json={"name": self._nombre("Dueña"), "identification_type": "CC",
                                                         "identification_number": numero}).json()
        self.terceros.append(a["id"])
        b = self.client.post("/api/third-parties", json={"name": self._nombre("Provisional")}).json()
        self.terceros.append(b["id"])
        # documento de otra ficha → 409 con la ficha completa (nunca 500 crudo)
        r = self.client.put(f"/api/third-parties/{b['id']}", json={"identification_number": numero})
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(r.json()["tercero"]["id"], a["id"])
        self.assertIn("address", r.json()["tercero"])
        # vacío y genérico → 400; tipo fuera del catálogo → 422
        self.assertEqual(self.client.put(f"/api/third-parties/{b['id']}", json={"identification_number": "  "}).status_code, 400)
        self.assertEqual(self.client.put(f"/api/third-parties/{b['id']}", json={"identification_number": "999999999"}).status_code, 400)
        self.assertEqual(self.client.put(f"/api/third-parties/{b['id']}", json={"identification_type": "PASAPORTE_X"}).status_code, 422)
        # formalizar el provisional con un número nuevo, recortado
        r = self.client.put(f"/api/third-parties/{b['id']}", json={"identification_number": f" {numero}1 ", "identification_type": "cc"})
        self.assertEqual(r.status_code, 200, r.text)
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT identification_number, identification_type FROM third_parties WHERE id = %s", (b["id"],))
            self.assertEqual(cur.fetchone(), (f"{numero}1", "CC"))
            conn.rollback()
        finally:
            put_conn(conn)
        # id inexistente → 404
        self.assertEqual(self.client.put("/api/third-parties/999999999", json={"name": "x"}).status_code, 404)
        # el POST también rechaza tipos y tamaños que antes acababan en 500
        self.assertEqual(self.client.post("/api/third-parties", json={"name": "x", "identification_type": ["CC"]}).status_code, 422)
        self.assertEqual(self.client.post("/api/third-parties", json={"name": "n" * 101}).status_code, 422)

    def test_confirmar_usa_la_ficha_vigente(self):
        """Formalizar el documento de un provisional ya asignado: al confirmar
        mandan los datos vigentes de la ficha (no nace otra con el SN- viejo)."""
        b = self.client.post("/api/third-parties", json={"name": self._nombre("Formal")}).json()
        self.terceros.append(b["id"])
        numero = "8" + self.sufijo[1:].encode().hex()[:9]
        self.client.put(f"/api/third-parties/{b['id']}", json={"identification_number": numero})
        conn = get_conn()
        try:
            cur = conn.cursor()
            tp = self.bot._tercero_vigente(cur, {"id": b["id"], "identification_type": "CC",
                                                  "identification_number": b["identification_number"],
                                                  "name": "viejo", "phone": "3000000000"})
            self.assertEqual((tp["identification_number"], tp["name"], tp["phone"]),
                             (numero, self._nombre("Formal"), "3000000000"))
            # sin id o con una ficha inexistente, se devuelve tal cual
            self.assertEqual(self.bot._tercero_vigente(cur, {"name": "x"}), {"name": "x"})
            self.assertEqual(self.bot._tercero_vigente(cur, {"id": 999999999, "name": "x"})["name"], "x")
            conn.rollback()
        finally:
            put_conn(conn)

    def test_leer_borrador_y_editarlo_con_aviso(self):
        r = self.client.get(f"/api/bot/drafts/{self.draft_id}")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["chat_channel"], "whatsapp")
        self.assertTrue(r.json()["editable"])
        self.assertEqual(self.client.get("/api/bot/drafts/999999999").status_code, 404)

        rt = self.client.post("/api/third-parties", json={"name": self._nombre("Asignada")})
        self.terceros.append(rt.json()["id"])
        t = rt.json()
        r = self.client.put(f"/api/bot/drafts/{self.draft_id}", json={
            "third_party": {"id": t["id"], "identification_type": t["identification_type"],
                            "identification_number": t["identification_number"], "name": t["name"]},
            "avisar_chat": True})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["avisar_chat"])
        payload, _ = self._payload()
        self.assertEqual(payload["third_party"]["id"], t["id"])
        self.assertTrue(payload.get("avisar_chat"))
        # sin la marca, el PUT se comporta como siempre
        r = self.client.put(f"/api/bot/drafts/{self.draft_id}", json={"concept": "arriendo"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertNotIn("avisar_chat", r.json())


if __name__ == "__main__":
    unittest.main()
