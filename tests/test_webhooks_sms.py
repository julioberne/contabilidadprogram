# -*- coding: utf-8 -*-
"""Tests puros del webhook de SMS (etapa 09.F, CA-09F-05). Sin BD: se parchea
db_pool.get_conn con una conexión falsa y bot_sms.resolver_identidad /
encolar_sms con dobles. Corre en CI.
"""
import os
import sys
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import bot_sms  # noqa: E402
import db_pool  # noqa: E402
from routers import webhooks_sms  # noqa: E402
from routers.auth_guard import require_auth  # noqa: E402

SMS = ("Bancolombia: Transferiste $11,900.00 desde tu cuenta *3037 a la cuenta "
       "*3193301184 el 21/09/26 a las 20:00.")
IDENTIDAD = {"token_id": 1, "hub_user_id": "u-1", "allowlist": ["85540"],
             "chat_link_id": 7, "chat_id": "123"}


class _Cur:
    def __init__(self, count=0):
        self.count = count
        self.sqls = []

    def execute(self, sql, params=None):
        self.sqls.append(sql)

    def fetchone(self):
        return (self.count,)

    def fetchall(self):
        return []

    def close(self):
        pass


class _Conn:
    def __init__(self, count=0):
        self.cur = _Cur(count)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _app():
    app = FastAPI()
    app.include_router(webhooks_sms.router)
    app.dependency_overrides[require_auth] = lambda: {"uid": "u-1", "role": "owner"}
    return app


class TestWebhook(unittest.TestCase):

    def setUp(self):
        self.conn = _Conn()
        self.p_get = mock.patch.object(db_pool, "get_conn", return_value=self.conn)
        self.p_put = mock.patch.object(db_pool, "put_conn", lambda c: None)
        self.p_id = mock.patch.object(bot_sms, "resolver_identidad",
                                      side_effect=lambda cur, tok: IDENTIDAD if tok == "bueno" else None)
        self.encolados = []

        def _encolar(cur, identidad, remitente, texto, sent_stamp=None):
            self.encolados.append((remitente, texto, sent_stamp))
            return (42, False) if len(self.encolados) == 1 else (None, True)
        self.p_enc = mock.patch.object(bot_sms, "encolar_sms", side_effect=_encolar)
        for p in (self.p_get, self.p_put, self.p_id, self.p_enc):
            p.start()
        self.client = TestClient(_app())

    def tearDown(self):
        for p in (self.p_get, self.p_put, self.p_id, self.p_enc):
            p.stop()

    def _post(self, token="bueno", data=None, form=False, raw=None, ctype=None):
        headers = {}
        if token is not None:
            headers["X-SMS-Token"] = token
        if raw is not None:
            headers["Content-Type"] = ctype or "application/json"
            return self.client.post("/api/webhooks/sms", content=raw, headers=headers)
        if form:
            return self.client.post("/api/webhooks/sms", data=data, headers=headers)
        return self.client.post("/api/webhooks/sms", json=data, headers=headers)

    def test_sin_token_401(self):
        self.assertEqual(self._post(token=None, data={"from": "85540", "text": SMS}).status_code, 401)

    def test_token_invalido_401(self):
        r = self._post(token="malo", data={"from": "85540", "text": SMS})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.encolados, [])
        self.assertEqual(self.conn.rollbacks, 1)

    def test_remitente_no_permitido_403(self):
        self.assertEqual(self._post(data={"from": "1234", "text": SMS}).status_code, 403)
        self.assertEqual(self.encolados, [])

    def test_body_mayor_4kb_413(self):
        r = self._post(data={"from": "85540", "text": "x" * 5000})
        self.assertEqual(r.status_code, 413)

    def test_content_type_raro_415(self):
        r = self._post(raw=b"hola", ctype="text/plain")
        self.assertEqual(r.status_code, 415)

    def test_json_invalido_400(self):
        self.assertEqual(self._post(raw=b"{no json", ctype="application/json").status_code, 400)

    def test_texto_vacio_422(self):
        self.assertEqual(self._post(data={"from": "85540", "text": "  "}).status_code, 422)

    def test_json_ok_202_inserta(self):
        r = self._post(data={"from": "+85540", "text": SMS, "sentStamp": "1700000000"})
        self.assertEqual(r.status_code, 202)
        self.assertEqual(r.json(), {"status": "ACEPTADO", "id": 42, "chat_vinculado": True})
        self.assertEqual(self.encolados, [("85540", SMS, "1700000000")])
        self.assertEqual(self.conn.commits, 1)

    def test_form_urlencoded_ok_202(self):
        r = self._post(data={"from": "85540", "text": SMS}, form=True)
        self.assertEqual(r.status_code, 202)
        self.assertEqual(self.encolados[0][1], SMS)

    def test_alias_macrodroid_sms_number_sms_message(self):
        r = self._post(data={"sms_number": "85540", "sms_message": SMS}, form=True)
        self.assertEqual(r.status_code, 202)

    def test_duplicado_202_sin_insertar(self):
        self._post(data={"from": "85540", "text": SMS})
        r = self._post(data={"from": "85540", "text": SMS})
        self.assertEqual(r.status_code, 202)
        self.assertEqual(r.json(), {"status": "DUPLICADO"})

    def test_rate_limit_429(self):
        self.conn.cur.count = 60
        r = self._post(data={"from": "85540", "text": SMS})
        self.assertEqual(r.status_code, 429)
        self.assertEqual(self.encolados, [])


class TestTokens(unittest.TestCase):

    def setUp(self):
        self.conn = _Conn(count=9)          # RETURNING id → 9
        self.p_get = mock.patch.object(db_pool, "get_conn", return_value=self.conn)
        self.p_put = mock.patch.object(db_pool, "put_conn", lambda c: None)
        self.p_get.start()
        self.p_put.start()
        self.client = TestClient(_app())

    def tearDown(self):
        self.p_get.stop()
        self.p_put.stop()

    def test_crear_token_devuelve_plano_una_vez(self):
        r = self.client.post("/api/webhooks/sms/token", json={"label": "Moto", "remitentes": ["85540", "+891333"]})
        self.assertEqual(r.status_code, 201)
        d = r.json()
        self.assertEqual(d["id"], 9)
        self.assertGreaterEqual(len(d["token"]), 40)
        self.assertEqual(d["remitentes"], ["85540", "891333"])
        self.assertIn("INSERT INTO sms_ingest_tokens", self.conn.cur.sqls[0])
        self.assertNotIn(d["token"], self.conn.cur.sqls[0])   # solo viaja el hash

    def test_crear_token_sin_cuerpo_usa_default_85540(self):
        r = self.client.post("/api/webhooks/sms/token")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["remitentes"], ["85540"])

    def test_revocar_inexistente_404(self):
        self.conn.cur.rowcount = 0
        r = self.client.delete("/api/webhooks/sms/tokens/5")
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
