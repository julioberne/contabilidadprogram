# -*- coding: utf-8 -*-
"""Integración de la etapa 09.G §10 contra Supabase: medios de pago del tercero.

Cubre (CA-09G-05/08/09/10):
  · núcleo (agregar / listar / conflicto / mover / eliminar / cascada),
  · los TRES momentos del bot: 1) destino desconocido → tercero a mano → 💾;
    2) mismo destino → el borrador llega con el tercero; 3) otra cuenta de la
    misma persona → se suma a la MISMA ficha (sin duplicar el tercero),
  · corregir: mover un medio a otro tercero (🔁) y el botón en la confirmación,
  · el router de la web.

Aislamiento: cola de SMS de prueba ('sms_prueba', ver test_bot_sms_db), chat y
terceros con sufijo único, todo borrado en tearDown. Jamás crea transacciones
(create_transaction se reemplaza por un doble en el test de confirmación).

Ejecutar:  .venv\\Scripts\\python.exe -m unittest tests.test_terceros_cuentas_db -v
"""
import json
import os
import sys
import unittest
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

from tests.test_bot_sms_db import COLA, _ConChatDePrueba, _DB_OK  # noqa: E402  (carga .env)

import bot_driver  # noqa: E402
import terceros_cuentas as tc  # noqa: E402


def _tabla_lista():
    if not _DB_OK:
        return False
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM third_party_accounts LIMIT 1")
            return True
        finally:
            conn.rollback()
            put_conn(conn)
    except Exception:
        return False


_OK = _tabla_lista()


class _Base(_ConChatDePrueba):

    def setUp(self):
        super().setUp()
        # "x" + hex: un sufijo como "ce1234ab" lo leería el parser del reply como
        # documento «CE 1234» y el tercero nacería sin sufijo (no se limpiaría)
        self.sufijo = "x" + uuid.uuid4().hex[:7]
        self._mid = 5000
        self.celular = "3" + str(uuid.uuid4().int)[:9]
        # Cuenta ajena: sus últimos 4 no pueden coincidir con una cuenta MÍA
        # (sería una transferencia entre cuentas propias y no un gasto).
        propias = {r[0] for r in self._q(
            "SELECT last4_cuenta FROM user_accounts WHERE last4_cuenta IS NOT NULL")}
        while True:
            self.cuenta = "9" + str(uuid.uuid4().int)[:10]
            if self.cuenta[-4:] not in propias:
                break

        def _send(chat_id, text, buttons=None):
            self._mid += 1
            self.enviados.append((chat_id, text, buttons))
            return self._mid
        self.send_fn = _send

    def tearDown(self):
        conn = self.get_conn()
        try:
            cur = conn.cursor()      # los medios caen en cascada con su tercero
            cur.execute("DELETE FROM third_parties WHERE name ILIKE %s", (f"%{self.sufijo}%",))
            conn.commit()
        finally:
            self.put_conn(conn)
        super().tearDown()

    # ── utilidades ──
    def _q(self, sql, params=()):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            filas = cur.fetchall()
            conn.commit()
            return filas
        finally:
            self.put_conn(conn)

    def _crear_tercero(self, nombre, doc=None):
        doc = doc or ("98" + str(uuid.uuid4().int)[:9])
        return self._q("""
            INSERT INTO third_parties (identification_type, identification_number, name)
            VALUES ('CC', %s, %s) RETURNING id
        """, (doc, f"{nombre} {self.sufijo}"))[0][0], doc

    def _medios(self):
        return self._q("""
            SELECT a.tipo, a.valor, a.origen, tp.name
              FROM third_party_accounts a JOIN third_parties tp ON tp.id = a.third_party_id
             WHERE tp.name ILIKE %s ORDER BY a.id
        """, (f"%{self.sufijo}%",))

    def _terceros(self):
        return self._q("SELECT id, identification_number, name FROM third_parties WHERE name ILIKE %s ORDER BY id",
                       (f"%{self.sufijo}%",))

    def _llega_sms(self, destino, monto="50,000.00", hora="01:37"):
        """SMS de transferencia → tick → (draft_id, texto enviado, botones)."""
        texto = (f"Bancolombia: Transferiste ${monto} desde tu cuenta *3037 a la cuenta *{destino} "
                 f"el 30/09/26 a las {hora}. ¿Dudas? Llamanos al 018000931987.")
        mid = self._encolar(texto)
        self._procesar()
        _, draft_id, _ = self._fila(mid)
        self.assertIsNotNone(draft_id)
        mios = [e for e in self.enviados if e[0] == self.chat_id]
        return draft_id, mios[-1][1], mios[-1][2]

    def _payload(self, draft_id):
        p = self._q("SELECT payload FROM transaction_drafts WHERE id = %s", (draft_id,))[0][0]
        return p if isinstance(p, dict) else json.loads(p)

    def _reply(self, draft_id, texto):
        resumen = self._q("SELECT bot_summary_message_id FROM transaction_drafts WHERE id = %s",
                          (draft_id,))[0][0]
        ext = f"t09g10-{uuid.uuid4().hex[:12]}"
        self.ext_ids.append(ext)
        r = bot_driver.handle_message({
            "channel": "telegram", "chat_id": self.chat_id, "external_message_id": ext,
            "kind": "text", "text": texto, "media_path": None, "reply_to_message_id": str(resumen),
        })
        if isinstance(r, dict) and r.get("draft_id"):
            self._mid += 1                       # lo que hace el adaptador de Telegram
            bot_driver.guardar_summary_message_id(r["draft_id"], self._mid)
        return r

    def _boton(self, data):
        return bot_driver.handle_callback("telegram", self.chat_id, data)

    @staticmethod
    def _datas(botones):
        return [d for fila in (botones or []) for _, d in fila]


@unittest.skipUnless(_OK, "BD o tabla third_party_accounts no disponible (migrate_third_party_accounts.py)")
class TestNucleo(_Base):

    def test_agregar_listar_conflicto_mover_eliminar(self):
        a, _ = self._crear_tercero("Ana Prueba")
        b, _ = self._crear_tercero("Beto Prueba")
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            r = tc.agregar(cur, a, "celular", f"+57 {self.celular}", banco="Nequi", origen="bot")
            self.assertTrue(r["ok"])
            self.assertEqual((r["medio"]["valor"], r["medio"]["banco"], r["medio"]["origen"]),
                             (self.celular, "Nequi", "bot"))
            self.assertFalse(r["ya_existia"])
            self.assertTrue(tc.agregar(cur, a, "celular", self.celular)["ya_existia"])   # idempotente
            r = tc.agregar(cur, b, "celular", self.celular)                               # ya es de Ana
            self.assertEqual((r["ok"], r["codigo"]), (False, "de_otro"))
            self.assertEqual(r["dueno"]["id"], a)
            self.assertIn(f"Ana Prueba {self.sufijo}", r["error"])
            self.assertEqual([m["valor"] for m in tc.listar(cur, a)], [self.celular])
            self.assertEqual(tc.buscar_tercero(cur, "celular", self.celular)["id"], a)
            self.assertEqual(tc.buscar_tercero(cur, "llave", self.celular)["id"], a)      # llave = celular

            self.assertTrue(tc.mover(cur, "celular", self.celular, b))
            self.assertEqual(tc.dueno(cur, "celular", self.celular)["id"], b)
            medio_id = tc.listar(cur, b)[0]["id"]
            self.assertFalse(tc.eliminar(cur, medio_id, a))                               # no es de Ana
            self.assertTrue(tc.eliminar(cur, medio_id, b))
            self.assertIsNone(tc.buscar_tercero(cur, "celular", self.celular))
            conn.commit()
        finally:
            self.put_conn(conn)

    def test_el_mismo_celular_como_llave_o_cuenta_es_un_solo_medio(self):
        """Ana lo tiene como llave Bre-B; nadie más puede registrarlo como celular
        ni como «cuenta» (así lo llama el SMS), y «Mover» se lleva todas sus formas."""
        a, _ = self._crear_tercero("Ana Prueba")
        b, _ = self._crear_tercero("Beto Prueba")
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            self.assertTrue(tc.agregar(cur, a, "llave", self.celular)["ok"])
            for tipo in ("celular", "cuenta", "llave"):
                r = tc.agregar(cur, b, tipo, self.celular)
                self.assertEqual((r["ok"], r["codigo"], r["dueno"]["id"]), (False, "de_otro", a), tipo)
            self.assertTrue(tc.agregar(cur, a, "celular", self.celular)["ok"])     # misma ficha: sí
            self.assertEqual({m["tipo"] for m in tc.listar(cur, a)}, {"llave", "celular"})
            self.assertEqual(tc.dueno(cur, "cuenta", self.celular)["id"], a)
            self.assertTrue(tc.mover(cur, "cuenta", self.celular, b))              # por cualquier forma
            self.assertEqual(tc.listar(cur, a), [])
            self.assertEqual({m["tipo"] for m in tc.listar(cur, b)}, {"llave", "celular"})
            self.assertEqual(tc.buscar_tercero(cur, "celular", self.celular)["id"], b)
            conn.commit()
        finally:
            self.put_conn(conn)

    def test_generico_no_puede_tener_medios_y_se_borran_con_el_tercero(self):
        a, _ = self._crear_tercero("Cascada Prueba")
        generico = self._q("SELECT id FROM third_parties WHERE identification_number = '999999999'")
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            if generico:
                r = tc.agregar(cur, generico[0][0], "celular", self.celular)
                self.assertEqual(r["codigo"], "tercero_generico")
            self.assertTrue(tc.agregar(cur, a, "cuenta", self.cuenta)["ok"])
            conn.commit()
            cur.execute("DELETE FROM third_parties WHERE id = %s", (a,))
            conn.commit()
            self.assertIsNone(tc.buscar_tercero(cur, "cuenta", self.cuenta))              # ON DELETE CASCADE
            conn.commit()
        finally:
            self.put_conn(conn)


@unittest.skipUnless(_OK, "BD o tabla third_party_accounts no disponible")
class TestTresMomentos(_Base):
    """El planteamiento de Andrés (30-sep), de punta a punta con el bot."""

    def test_primera_vez_guardar_luego_automatico_y_otra_cuenta_misma_ficha(self):
        doc = "97" + str(uuid.uuid4().int)[:9]

        # ── Momento 1: destino desconocido → a mano + 💾 ──
        d1, texto1, _ = self._llega_sms(self.celular)
        p1 = self._payload(d1)
        self.assertEqual(p1["third_party"]["name"], "Sin especificar")
        self.assertEqual(p1["sms"]["medio"], {"tipo": "celular", "valor": self.celular})
        r = self._reply(d1, f"abono cuota 1\nTercero: Leidy Prueba {self.sufijo} cc {doc}")
        self.assertIn("Tercero CREADO", r["text"])
        self.assertIn("Guardar", r["text"])                                  # explica el botón
        self.assertEqual(self._datas(r["buttons"])[0], f"tpsave:{d1}")       # 💾 arriba
        self.assertIn(f"cel {self.celular}", r["buttons"][0][0][0])
        self.assertEqual(self._medios(), [])                                 # nada se guarda solo

        out = self._boton(f"tpsave:{d1}")
        self.assertEqual(out["alert"], "💾 Guardado")
        self.assertIn("quedó en la ficha", out["text"])
        self.assertNotIn(f"tpsave:{d1}", self._datas(out["edit_buttons"]))   # el botón desaparece
        self.assertEqual([(m[0], m[1], m[2]) for m in self._medios()],
                         [("celular", self.celular, "bot")])
        out2 = self._boton(f"tpsave:{d1}")                                   # tocarlo otra vez no duplica
        self.assertIn("ya está", out2["alert"])
        self.assertEqual(len(self._medios()), 1)

        # ── Momento 2: mismo destino → llega con el tercero puesto ──
        d2, texto2, botones2 = self._llega_sms(self.celular, monto="80,000.00", hora="09:15")
        p2 = self._payload(d2)
        self.assertEqual(p2["third_party"]["identification_number"], doc)
        self.assertNotIn("third_party", p2["inferred_fields"])
        self.assertTrue(p2["sms"]["tercero_por_medio"])
        self.assertIn("medio de pago registrado", texto2)
        self.assertNotIn(f"tpsave:{d2}", self._datas(botones2))

        # ── Momento 3: OTRA cuenta de la misma persona → misma ficha ──
        d3, _, _ = self._llega_sms(self.cuenta, monto="120,000.00", hora="10:30")
        self.assertEqual(self._payload(d3)["third_party"]["name"], "Sin especificar")
        r3 = self._reply(d3, f"Tercero: leidy prueba {self.sufijo}")         # solo el nombre
        self.assertIn("👤 Tercero →", r3["text"])
        self.assertNotIn("CREADO", r3["text"])
        self.assertEqual(self._datas(r3["buttons"])[0], f"tpsave:{d3}")
        self._boton(f"tpsave:{d3}")
        self.assertEqual(len(self._terceros()), 1)                           # UNA ficha…
        self.assertEqual(sorted((m[0], m[1]) for m in self._medios()),      # …con dos medios
                         sorted([("celular", self.celular), ("cuenta", self.cuenta)]))

    def test_celular_de_contacto_en_la_ficha_no_ofrece_guardar(self):
        """Si el celular ya es el teléfono de contacto de UNA ficha, el SMS llega
        con ese tercero: no queda nada por guardar y no se ofrece 💾."""
        tp_id, doc = self._crear_tercero("Dora Prueba")
        self._q("UPDATE third_parties SET phone = %s WHERE id = %s RETURNING id",
                (f"+57 {self.celular}", tp_id))
        d, _, _ = self._llega_sms(self.celular)
        p = self._payload(d)
        self.assertEqual(p["third_party"]["identification_number"], doc)
        self.assertFalse(p["sms"]["tercero_por_medio"])
        r = self._reply(d, "abono cuota 2")
        self.assertNotIn(f"tpsave:{d}", self._datas(r["buttons"]))
        self.assertNotIn("Guardar", r["text"])
        out = self._boton(f"tpsave:{d}")                  # botón forzado: no guarda nada
        self.assertIn("Nada que guardar", out["alert"])
        self.assertEqual(self._medios(), [])

    def test_dictar_el_celular_con_el_tercero_resuelve_el_proximo_sms(self):
        """El flujo real de Andrés: «Tercero: nombre cc N cel X», con X = destino del SMS."""
        doc = "96" + str(uuid.uuid4().int)[:9]
        d1, _, _ = self._llega_sms(self.celular)
        r = self._reply(d1, f"abono cuota 1\nTercero: Leidy Prueba {self.sufijo} cc {doc} cel {self.celular}")
        self.assertIn("Tercero CREADO", r["text"])
        self.assertNotIn(f"tpsave:{d1}", self._datas(r["buttons"]))     # el celular ya está en la ficha
        d2, _, _ = self._llega_sms(self.celular, monto="80,000.00", hora="09:15")
        self.assertEqual(self._payload(d2)["third_party"]["identification_number"], doc)
        self.assertEqual(len(self._terceros()), 1)

    def test_llave_registrada_vale_para_el_celular_y_no_se_ofrece_guardar_otra_vez(self):
        tp_id, doc = self._crear_tercero("Elsa Prueba")
        self._q("INSERT INTO third_party_accounts (third_party_id, tipo, valor) "
                "VALUES (%s, 'llave', %s) RETURNING id", (tp_id, self.celular))
        d, texto, _ = self._llega_sms(self.celular)
        p = self._payload(d)
        self.assertEqual(p["third_party"]["identification_number"], doc)
        self.assertTrue(p["sms"]["tercero_por_medio"])
        r = self._reply(d, "abono")
        self.assertNotIn(f"tpsave:{d}", self._datas(r["buttons"]))
        self.assertEqual(len(self._medios()), 1)

    def test_borrador_anterior_a_la_etapa_tambien_ofrece_guardar(self):
        """Los borradores creados antes de 09.G §10 (p. ej. el #237 real) no traen
        payload.sms.medio: se deriva de familia + destino."""
        doc = "95" + str(uuid.uuid4().int)[:9]
        d, _, _ = self._llega_sms(self.cuenta)
        self._q("UPDATE transaction_drafts SET payload = payload #- '{sms,medio}' "
                "#- '{sms,tercero_por_medio}' WHERE id = %s RETURNING id", (d,))
        self.assertNotIn("medio", self._payload(d)["sms"])
        r = self._reply(d, f"Tercero: Fabio Prueba {self.sufijo} cc {doc}")
        self.assertEqual(self._datas(r["buttons"])[0], f"tpsave:{d}")
        self.assertEqual(self._boton(f"tpsave:{d}")["alert"], "💾 Guardado")
        self.assertEqual([(m[0], m[1]) for m in self._medios()], [("cuenta", self.cuenta)])

    def test_corregir_mover_el_medio_a_otro_tercero(self):
        a, _ = self._crear_tercero("Ana Prueba")
        b, doc_b = self._crear_tercero("Beto Prueba")
        self._q("INSERT INTO third_party_accounts (third_party_id, tipo, valor) VALUES (%s, 'celular', %s) RETURNING id",
                (a, self.celular))
        d, texto, _ = self._llega_sms(self.celular)
        self.assertEqual(self._payload(d)["third_party"]["name"], f"Ana Prueba {self.sufijo}")

        r = self._reply(d, f"Tercero: beto prueba {self.sufijo}")            # no era Ana
        self.assertEqual(self._payload(d)["third_party"]["identification_number"], doc_b)
        self.assertEqual(self._datas(r["buttons"])[0], f"tpmove:{d}")        # 🔁, nunca se mueve solo
        self.assertIn("Mover", r["text"])
        self.assertEqual(self._medios()[0][3], f"Ana Prueba {self.sufijo}")  # sigue siendo de Ana

        out_guardar = self._boton(f"tpsave:{d}")                             # 💾 no pisa al dueño
        self.assertIn("ya está en la ficha", out_guardar["alert"])
        self.assertEqual(self._medios()[0][3], f"Ana Prueba {self.sufijo}")

        out = self._boton(f"tpmove:{d}")
        self.assertEqual(out["alert"], "🔁 Movido")
        self.assertEqual(self._medios()[0][3], f"Beto Prueba {self.sufijo}")

    def test_boton_guardar_tambien_va_con_la_confirmacion(self):
        from unittest import mock
        import transaction_service
        _, doc = self._crear_tercero("Carla Prueba")
        d, _, _ = self._llega_sms(self.cuenta)
        self._reply(d, f"pago factura\nTercero: {doc}")                      # por documento
        self.assertEqual(self._payload(d)["third_party"]["identification_number"], doc)
        self._q("UPDATE transaction_drafts SET payload = jsonb_set(payload, '{account_id}', "
                "(SELECT to_jsonb(MIN(id)) FROM user_accounts)) WHERE id = %s RETURNING id", (d,))
        with mock.patch.object(transaction_service, "create_transaction",
                               return_value={"transaction_id": 1, "journal": "ok", "net_value": 50000}):
            out = self._boton(f"ok:{d}")
        self.assertTrue(out["text"].startswith("✅"), out["text"])
        self.assertEqual(self._datas(out.get("text_buttons")), [f"tpsave:{d}"])
        out2 = self._boton(f"tpsave:{d}")                                    # ya CONFIRMADO: igual se puede
        self.assertEqual(out2["alert"], "💾 Guardado")
        self.assertEqual(out2["edit_buttons"], [])
        self.assertEqual([(m[0], m[1]) for m in self._medios()], [("cuenta", self.cuenta)])


    def test_confirmar_por_texto_tambien_ofrece_guardar(self):
        from unittest import mock
        import transaction_service
        _, doc = self._crear_tercero("Gina Prueba")
        d, _, _ = self._llega_sms(self.cuenta)
        self._reply(d, f"pago factura\nTercero: {doc}")
        self._q("UPDATE transaction_drafts SET payload = jsonb_set(payload, '{account_id}', "
                "(SELECT to_jsonb(MIN(id)) FROM user_accounts)) WHERE id = %s RETURNING id", (d,))
        ext = f"t09g10-{uuid.uuid4().hex[:12]}"
        self.ext_ids.append(ext)
        with mock.patch.object(transaction_service, "create_transaction",
                               return_value={"transaction_id": 1, "journal": "ok", "net_value": 50000}):
            r = bot_driver.handle_message({
                "channel": "telegram", "chat_id": self.chat_id, "external_message_id": ext,
                "kind": "text", "text": f"Confirmar #{d}", "media_path": None,
                "reply_to_message_id": None})
        self.assertIsInstance(r, dict, r)
        self.assertTrue(r["text"].startswith("✅"), r["text"])
        self.assertIn("Guardar", r["text"])
        self.assertEqual(self._datas(r["buttons"]), [f"tpsave:{d}"])
        self.assertEqual(self._medios(), [])                                 # nada se guarda solo


@unittest.skipUnless(_OK, "BD o tabla third_party_accounts no disponible")
class TestRouter(_Base):

    def setUp(self):
        super().setUp()
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers import third_party_accounts as r
        from routers.auth_guard import require_admin, require_auth
        app = FastAPI()
        app.include_router(r.router)
        app.dependency_overrides[require_auth] = lambda: {"uid": self.uid, "role": "owner"}
        app.dependency_overrides[require_admin] = lambda: {"uid": self.uid, "role": "owner"}
        self.client = TestClient(app)

    def test_crud_desde_la_web(self):
        a, _ = self._crear_tercero("Web Ana")
        b, _ = self._crear_tercero("Web Beto")
        base = f"/api/third-parties/{a}/accounts"
        self.assertEqual(self.client.get(base).json(), [])

        r = self.client.post(base, json={"tipo": "cuenta", "valor": f"*{self.cuenta}", "banco": "Bancolombia",
                                         "etiqueta": "ahorros"})
        self.assertEqual(r.status_code, 201, r.text)
        medio = r.json()["medio"]
        self.assertEqual((medio["valor"], medio["origen"], medio["descripcion"]),
                         (self.cuenta, "web", f"cuenta *{self.cuenta}"))
        self.assertEqual(self.client.post(base, json={"tipo": "cuenta", "valor": self.cuenta}).json()["status"],
                         "YA_EXISTIA")
        self.assertEqual(len(self.client.get(base).json()), 1)

        # validaciones y conflicto
        self.assertEqual(self.client.post(base, json={"tipo": "celular", "valor": "123"}).status_code, 422)
        self.assertEqual(self.client.post(base, json={"tipo": "fax", "valor": "123456"}).status_code, 422)
        self.assertEqual(self.client.post("/api/third-parties/0/accounts",
                                          json={"tipo": "cuenta", "valor": "123456"}).status_code, 404)
        r = self.client.post(f"/api/third-parties/{b}/accounts", json={"tipo": "cuenta", "valor": self.cuenta})
        self.assertEqual(r.status_code, 409)
        self.assertIn(f"Web Ana {self.sufijo}", r.json()["detail"])

        # mover a Beto (explícito) y quitar
        r = self.client.post(f"/api/third-parties/{b}/accounts/mover", json={"tipo": "cuenta", "valor": self.cuenta})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.client.get(base).json(), [])
        id_en_b = r.json()["medios"][0]["id"]
        self.assertEqual(self.client.delete(f"{base}/{id_en_b}").status_code, 404)        # ya no es de Ana
        self.assertEqual(self.client.delete(f"/api/third-parties/{b}/accounts/{id_en_b}").status_code, 200)
        self.assertEqual(self.client.post(f"/api/third-parties/{b}/accounts/mover",
                                          json={"tipo": "cuenta", "valor": self.cuenta}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
