# -*- coding: utf-8 -*-
"""Integración contra Supabase: PUT/DELETE de etiquetas y plantillas de impuesto.

La BD es la MISMA de producción. Aislamiento:
  · etiquetas y plantillas de prueba con sufijo único en el nombre, borradas en
    tearDown;
  · los casos que necesitan transacciones o borradores (quitar la etiqueta con
    ?forzar, renombrar sin propagar) corren dentro de UNA transacción que
    SIEMPRE termina en rollback: ninguna fila llega a confirmarse.
Se salta solo sin BD.

Ejecutar:  .venv\\Scripts\\python.exe -m unittest tests.test_etiquetas_db -v
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

import fin_sys_core  # noqa: E402,F401
from fin_sys_core import etiquetas as et  # noqa: E402


def _db_disponible():
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            for tabla in ("tag_definitions", "custom_taxes_templates", "transactions", "transaction_drafts"):
                cur.execute(f"SELECT 1 FROM {tabla} LIMIT 1")
            cur.close()
            return True
        finally:
            conn.rollback()
            put_conn(conn)
    except Exception:
        return False


_DB_OK = _db_disponible()


@unittest.skipUnless(_DB_OK, "BD o tablas no disponibles")
class TestEtiquetasEnBD(unittest.TestCase):

    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from db_pool import get_conn, put_conn
        from routers.auth_guard import require_admin, require_auth
        from routers.tags_taxes import router
        self.get_conn, self.put_conn = get_conn, put_conn
        self.sufijo = uuid.uuid4().hex[:8]
        app = FastAPI()
        app.include_router(router)
        admin = {"uid": "test", "name": f"test {self.sufijo}", "role": "owner"}
        app.dependency_overrides[require_auth] = lambda: admin
        app.dependency_overrides[require_admin] = lambda: admin
        self.client = TestClient(app)

    def tearDown(self):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM tag_definitions WHERE name ILIKE %s", (f"%{self.sufijo}%",))
            cur.execute("DELETE FROM custom_taxes_templates WHERE name ILIKE %s", (f"%{self.sufijo}%",))
            conn.commit()
        finally:
            self.put_conn(conn)

    def _q(self, sql, params=()):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            filas = cur.fetchall() if cur.description else []
            conn.commit()
            return filas
        finally:
            self.put_conn(conn)

    def _crear_tag(self, nombre, cur=None, color="#000000"):
        sql = "INSERT INTO tag_definitions (name, color) VALUES (%s, %s) RETURNING id"
        params = (f"{nombre} {self.sufijo}", color)
        if cur is not None:
            cur.execute(sql, params)
            return cur.fetchone()[0]
        return self._q(sql, params)[0][0]

    def _tag(self, tag_id):
        filas = self._q("SELECT name, color FROM tag_definitions WHERE id = %s", (tag_id,))
        return filas[0] if filas else None

    # ── por el endpoint (commit real) ──
    def test_editar_renombrar_duplicado_y_borrar(self):
        a = self._crear_tag("Etiqueta A")
        b = self._crear_tag("Etiqueta B")
        r = self.client.put(f"/api/tags/{a}", json={"name": f"Etiqueta A2 {self.sufijo}", "color": "#FF9800"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["tag"], {"id": a, "name": f"Etiqueta A2 {self.sufijo}", "color": "#FF9800"})
        self.assertEqual(self._tag(a), (f"Etiqueta A2 {self.sufijo}", "#FF9800"))

        r = self.client.put(f"/api/tags/{a}", json={"name": f"Etiqueta B {self.sufijo}"})
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(self._tag(a)[0], f"Etiqueta A2 {self.sufijo}")          # sin cambios

        r = self.client.delete(f"/api/tags/{a}")                                  # sin uso: directo
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {"status": "ELIMINADO", "id": a, "name": f"Etiqueta A2 {self.sufijo}",
                                    "transacciones_actualizadas": 0, "borradores_actualizados": 0})
        self.assertIsNone(self._tag(a))
        self.assertEqual(self.client.delete(f"/api/tags/{a}").status_code, 404)
        self.assertEqual(self.client.put(f"/api/tags/{a}", json={"color": "#000000"}).status_code, 404)
        self.assertIsNotNone(self._tag(b))

    # ── con historia: todo dentro de una transacción que termina en rollback ──
    def _con_historia(self, fn):
        """Crea etiqueta + transacción + borradores (abierto y descartado) que la
        llevan, ejecuta fn(cur, tag_id, nombre, tx_id, draft_abierto, draft_descartado)
        y hace rollback pase lo que pase."""
        portafolio = self._q("SELECT MIN(id) FROM portfolios")[0][0]
        tercero = self._q("SELECT MIN(id) FROM third_parties")[0][0]
        if portafolio is None or tercero is None:
            self.skipTest("sin portafolios o terceros")
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            tag_id = self._crear_tag("Historia", cur)
            nombre = f"Historia {self.sufijo}"
            cur.execute("""
                INSERT INTO transactions (portfolio_id, third_party_id, type, amount, concept, transaction_date,
                                          payment_method, category, net_value, tags)
                VALUES (%s, %s, 'GASTO', 1000, %s, CURRENT_DATE, 'EFECTIVO', 'PRUEBA', 1000, %s) RETURNING id
            """, (portafolio, tercero, f"prueba {self.sufijo}", [nombre, "otra"]))
            tx_id = cur.fetchone()[0]
            payload = json.dumps({"concept": f"prueba {self.sufijo}", "tags": [nombre, "otra"]})
            cur.execute("INSERT INTO transaction_drafts (status, payload) VALUES ('BORRADOR', %s::jsonb) RETURNING id",
                        (payload,))
            abierto = cur.fetchone()[0]
            cur.execute("INSERT INTO transaction_drafts (status, payload) VALUES ('DESCARTADO', %s::jsonb) RETURNING id",
                        (payload,))
            descartado = cur.fetchone()[0]
            fn(cur, tag_id, nombre, tx_id, abierto, descartado)
        finally:
            conn.rollback()
            self.put_conn(conn)

    def test_borrar_en_uso_409_y_forzada_la_quita_de_donde_esta(self):
        def fn(cur, tag_id, nombre, tx_id, abierto, descartado):
            r = et.eliminar(cur, tag_id)
            self.assertEqual((r["ok"], r["codigo"]), (False, "en_uso"))
            self.assertEqual(r["uso"], {"transacciones": 1, "borradores": [abierto]})
            self.assertEqual(r["error"],
                             f"La etiqueta «{nombre}» está en 1 transacción y 1 borrador abierto del bot (#{abierto}).")

            r = et.eliminar(cur, tag_id, forzar=True)
            self.assertEqual(r, {"ok": True, "id": tag_id, "name": nombre,
                                 "transacciones_actualizadas": 1, "borradores_actualizados": 1})
            cur.execute("SELECT tags FROM transactions WHERE id = %s", (tx_id,))
            self.assertEqual(cur.fetchone()[0], ["otra"])
            cur.execute("SELECT payload->'tags' FROM transaction_drafts WHERE id = %s", (abierto,))
            self.assertEqual(cur.fetchone()[0], ["otra"])
            cur.execute("SELECT payload->'tags' FROM transaction_drafts WHERE id = %s", (descartado,))
            self.assertEqual(cur.fetchone()[0], [nombre, "otra"])              # el descartado no se toca
            cur.execute("SELECT 1 FROM tag_definitions WHERE id = %s", (tag_id,))
            self.assertIsNone(cur.fetchone())
        self._con_historia(fn)

    def test_renombrar_no_propaga(self):
        def fn(cur, tag_id, nombre, tx_id, abierto, _descartado):
            r = et.actualizar(cur, tag_id, name=f"Historia nueva {self.sufijo}")
            self.assertTrue(r["ok"], r)
            cur.execute("SELECT tags FROM transactions WHERE id = %s", (tx_id,))
            self.assertEqual(cur.fetchone()[0], [nombre, "otra"])              # conserva el nombre viejo
            cur.execute("SELECT payload->'tags' FROM transaction_drafts WHERE id = %s", (abierto,))
            self.assertEqual(cur.fetchone()[0], [nombre, "otra"])
            self.assertEqual(et.uso_de_etiqueta(cur, f"Historia nueva {self.sufijo}"),
                             {"transacciones": 0, "borradores": []})
        self._con_historia(fn)

    # ── plantillas de impuesto, por los endpoints ──
    def test_tasas_crear_editar_borrar(self):
        r = self.client.post("/api/custom-taxes", json={"name": f"Tasa {self.sufijo}", "rate": 1.5, "tax_type": "ADDITIVE"})
        self.assertEqual(r.status_code, 201, r.text)
        tax_id = r.json()["id"]
        r = self.client.put(f"/api/custom-taxes/{tax_id}", json={"name": f"Tasa2 {self.sufijo}", "rate": "2.25", "type": "DEDUCTIVE"})
        self.assertEqual(r.status_code, 200, r.text)
        fila = [t for t in self.client.get("/api/custom-taxes").json() if t["id"] == tax_id][0]
        self.assertEqual((fila["name"], float(fila["rate"]), fila["type"]), (f"Tasa2 {self.sufijo}", 2.25, "DEDUCTIVE"))
        self.assertEqual(self.client.delete(f"/api/custom-taxes/{tax_id}").json(), {"status": "ELIMINADO", "id": tax_id})
        self.assertEqual(self.client.delete(f"/api/custom-taxes/{tax_id}").status_code, 404)
        self.assertEqual(self.client.put(f"/api/custom-taxes/{tax_id}", json={"rate": 1}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
