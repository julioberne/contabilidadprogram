# -*- coding: utf-8 -*-
"""Integración contra Supabase: DELETE /api/third-parties/{id} (👤 Terceros → 🗑).

La BD es la MISMA de producción. Aislamiento:
  · los terceros de prueba llevan un sufijo único en el nombre y se borran en
    tearDown (sus medios de pago caen en cascada);
  · los casos "con historia" (transacción, cartera, borrador del bot) corren
    dentro de UNA transacción que SIEMPRE termina en rollback: ninguna fila
    llega a confirmarse ni la ve nadie más;
  · el genérico solo recibe un DELETE que el endpoint rechaza antes de tocar
    nada (y los FK RESTRICT de la BD lo protegen de todos modos).
Se salta solo sin BD.

Ejecutar:  .venv\\Scripts\\python.exe -m unittest tests.test_terceros_borrado_db -v
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
from fin_sys_core import terceros_borrado as tb  # noqa: E402


def _db_disponible():
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            for tabla in ("third_parties", "transactions", "cxp_cxc_ledger",
                          "inventory_movements", "transaction_drafts", "third_party_accounts"):
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
class TestBorrarTerceroEnBD(unittest.TestCase):

    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from db_pool import get_conn, put_conn
        from routers.auth_guard import require_admin, require_auth
        from routers.cartera import router
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
            cur.execute("DELETE FROM third_parties WHERE name ILIKE %s", (f"%{self.sufijo}%",))
            conn.commit()
        finally:
            self.put_conn(conn)

    # ── utilidades ──
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

    @staticmethod
    def _doc():
        return "98" + str(uuid.uuid4().int)[:9]

    def _crear_tercero(self, nombre, cur=None):
        """Tercero de prueba. Con `cur` queda dentro de la transacción del llamador."""
        doc = self._doc()
        sql = ("INSERT INTO third_parties (identification_type, identification_number, name) "
               "VALUES ('CC', %s, %s) RETURNING id")
        params = (doc, f"{nombre} {self.sufijo}")
        if cur is not None:
            cur.execute(sql, params)
            return cur.fetchone()[0], doc
        return self._q(sql, params)[0][0], doc

    def _existe(self, tp_id):
        return bool(self._q("SELECT 1 FROM third_parties WHERE id = %s", (tp_id,)))

    # ── por el endpoint (commit real) ──
    def test_sin_historia_se_borra_y_sus_medios_de_pago_caen_en_cascada(self):
        tp_id, _ = self._crear_tercero("Borrable Prueba")
        cuenta = "9" + str(uuid.uuid4().int)[:10]
        self._q("INSERT INTO third_party_accounts (third_party_id, tipo, valor) "
                "VALUES (%s, 'cuenta', %s) RETURNING id", (tp_id, cuenta))
        r = self.client.delete(f"/api/third-parties/{tp_id}")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {"status": "ELIMINADO", "id": tp_id, "name": f"Borrable Prueba {self.sufijo}"})
        self.assertFalse(self._existe(tp_id))
        self.assertEqual(self._q("SELECT 1 FROM third_party_accounts WHERE tipo = 'cuenta' AND valor = %s",
                                 (cuenta,)), [])

    def test_404_si_no_existe(self):
        libre = self._q("SELECT COALESCE(MAX(id), 0) + 100000 FROM third_parties")[0][0]
        r = self.client.delete(f"/api/third-parties/{libre}")
        self.assertEqual(r.status_code, 404, r.text)
        self.assertEqual(r.json()["detail"], "Ese tercero no existe.")

    def test_generico_409_y_sigue_ahi(self):
        generico = self._q("SELECT id FROM third_parties WHERE identification_number = '999999999'")
        if not generico:
            self.skipTest("esta BD no tiene el tercero genérico")
        r = self.client.delete(f"/api/third-parties/{generico[0][0]}")
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("genérico", r.json()["detail"])
        self.assertTrue(self._existe(generico[0][0]))

    # ── con historia: todo dentro de una transacción que termina en rollback ──
    def _en_transaccion_descartada(self, montar):
        """montar(cur, tp_id, doc) arma la historia; devuelve el resultado de
        eliminar(). Nada se confirma jamás."""
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            tp_id, doc = self._crear_tercero("Historia Prueba", cur)
            montar(cur, tp_id, doc)
            return tb.eliminar(cur, tp_id)
        finally:
            conn.rollback()
            self.put_conn(conn)

    def test_con_transaccion_409(self):
        portafolio = self._q("SELECT MIN(id) FROM portfolios")[0][0]
        if portafolio is None:
            self.skipTest("sin portafolios")

        def montar(cur, tp_id, _doc):
            cur.execute("""
                INSERT INTO transactions (portfolio_id, third_party_id, type, amount, concept,
                                          transaction_date, payment_method, category, net_value)
                VALUES (%s, %s, 'GASTO', 1000, %s, CURRENT_DATE, 'EFECTIVO', 'PRUEBA', 1000)
            """, (portafolio, tp_id, f"prueba {self.sufijo}"))
        r = self._en_transaccion_descartada(montar)
        self.assertEqual((r["ok"], r["codigo"]), (False, "en_uso"))
        self.assertEqual(r["uso"], {"transacciones": 1, "cartera": 0, "inventario": 0, "borradores": []})
        self.assertIn("tiene 1 transacción.", r["error"])

    def test_con_cartera_409(self):
        def montar(cur, tp_id, _doc):
            cur.execute("""
                INSERT INTO cxp_cxc_ledger (third_party_id, type, original_amount, remaining_balance,
                                            due_date, term, status)
                VALUES (%s, 'CXC', 5000, 5000, CURRENT_DATE + 30, '30', 'PENDIENTE')
            """, (tp_id,))
        r = self._en_transaccion_descartada(montar)
        self.assertEqual(r["codigo"], "en_uso")
        self.assertEqual(r["uso"]["cartera"], 1)
        self.assertIn("1 cuenta de cartera (CXC/CXP)", r["error"])

    def test_borrador_abierto_del_bot_409_pero_descartado_no_bloquea(self):
        def payload(doc):
            return json.dumps({"third_party": {"identification_type": "CC", "identification_number": doc,
                                               "name": f"Historia Prueba {self.sufijo}"},
                               "concept": f"prueba {self.sufijo}"})

        def abierto(cur, tp_id, doc):
            cur.execute("INSERT INTO transaction_drafts (status, payload) VALUES ('BORRADOR', %s::jsonb) "
                        "RETURNING id", (payload(doc),))
            self.draft_id = cur.fetchone()[0]
        r = self._en_transaccion_descartada(abierto)
        self.assertEqual(r["codigo"], "en_uso")
        self.assertEqual(r["uso"]["borradores"], [self.draft_id])
        self.assertIn(f"1 borrador abierto del bot (#{self.draft_id})", r["error"])
        self.assertIn("Bandeja", r["error"])

        def descartado(cur, tp_id, doc):
            cur.execute("INSERT INTO transaction_drafts (status, payload) VALUES ('DESCARTADO', %s::jsonb)",
                        (payload(doc),))
        r = self._en_transaccion_descartada(descartado)
        self.assertTrue(r["ok"], r)                       # se borró dentro de la transacción…
        self.assertFalse(self._existe(r["id"]))           # …y el rollback no dejó rastro


if __name__ == "__main__":
    unittest.main()
