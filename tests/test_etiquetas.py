# -*- coding: utf-8 -*-
"""Editar y borrar etiquetas y plantillas de impuesto desde el panel, SIN BD.

Reglas (decisión de Andrés, 1-oct-2026): renombrar una etiqueta NO toca las
transacciones; borrar una etiqueta en uso → 409 con el conteo, y con
?forzar=1 se quita de las transacciones y borradores abiertos del bot y se
borra. Las plantillas de impuesto se editan/borran sin historia que cuidar.
Hasta ese día `PUT/DELETE /api/tags/{id}` y `/api/custom-taxes/{id}` no
existían (405) y el panel se tragaba el error.

Cubre fin_sys_core/etiquetas.py con un cursor falso y las 4 rutas de
routers/tags_taxes.py con TestClient (guards reales, conexión parcheada).

Ejecutar:  .venv\\Scripts\\python.exe -m unittest tests.test_etiquetas -v
"""
import os
import sys
import unittest
from unittest import mock

import psycopg2.errors

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import fin_sys_core  # noqa: E402,F401
from fin_sys_core import etiquetas as et  # noqa: E402


class FakeCursor:
    """Registra cada execute; sirve fetchone desde una cola; rowcount programable."""

    def __init__(self, fetchones, rowcounts=None, falla_en=None):
        self.ejecutadas = []
        self._fetchones = list(fetchones)
        self._rowcounts = list(rowcounts or [])
        self._falla_en = falla_en
        self.rowcount = 0

    def execute(self, sql, params=None):
        sql = " ".join(sql.split())
        self.ejecutadas.append((sql, params))
        if self._falla_en and self._falla_en[0] in sql:
            raise self._falla_en[1]
        self.rowcount = self._rowcounts.pop(0) if self._rowcounts else 1

    def fetchone(self):
        return self._fetchones.pop(0)

    def close(self):
        pass

    def sqls(self):
        return [s for s, _ in self.ejecutadas]


OFICINA = (5, "Oficina", "#2196F3")


class TestValidar(unittest.TestCase):

    def test_nombre_y_color(self):
        self.assertIsNone(et.validar())
        self.assertIsNone(et.validar(name=" Oficina ", color="#ff9800"))
        self.assertIn("vacío", et.validar(name="   "))
        self.assertIn("100", et.validar(name="x" * 101))
        self.assertIn("hexadecimal", et.validar(color="rojo"))
        self.assertIn("hexadecimal", et.validar(color="#FFF"))


class TestActualizar(unittest.TestCase):

    def test_invalido_no_toca_la_bd(self):
        cur = FakeCursor([])
        r = et.actualizar(cur, 5, name="")
        self.assertEqual((r["ok"], r["codigo"]), (False, "invalido"))
        self.assertEqual(cur.ejecutadas, [])
        r = et.actualizar(cur, 5)
        self.assertEqual(r["codigo"], "sin_cambios")

    def test_no_existe(self):
        cur = FakeCursor([None])
        r = et.actualizar(cur, 99, color="#000000")
        self.assertEqual(r["codigo"], "no_existe")
        self.assertIn("FOR UPDATE", cur.sqls()[0])

    def test_renombrar_cambia_solo_la_definicion(self):
        cur = FakeCursor([OFICINA, None, (5, "Oficina central", "#2196F3")])
        r = et.actualizar(cur, 5, name=" Oficina central ")
        self.assertTrue(r["ok"])
        self.assertEqual(r["tag"], {"id": 5, "name": "Oficina central", "color": "#2196F3"})
        sqls = cur.sqls()
        self.assertEqual(len(sqls), 3)                       # lock, duplicado, UPDATE
        self.assertIn("WHERE name = %s AND id <> %s", sqls[1])
        self.assertTrue(sqls[2].startswith("UPDATE tag_definitions SET name = %s, color = %s"))
        self.assertEqual(cur.ejecutadas[2][1], ("Oficina central", "#2196F3", 5))
        self.assertFalse(any("transactions" in s or "transaction_drafts" in s for s in sqls))  # no propaga

    def test_solo_color_no_consulta_duplicados(self):
        cur = FakeCursor([OFICINA, (5, "Oficina", "#FF9800")])
        r = et.actualizar(cur, 5, color="#FF9800")
        self.assertTrue(r["ok"])
        self.assertEqual(len(cur.ejecutadas), 2)
        self.assertEqual(cur.ejecutadas[1][1], ("Oficina", "#FF9800", 5))

    def test_nombre_duplicado_por_comprobacion_y_por_unique(self):
        cur = FakeCursor([OFICINA, (1,)])
        r = et.actualizar(cur, 5, name="Operativo")
        self.assertEqual(r["codigo"], "nombre_duplicado")
        self.assertIn("«Operativo»", r["error"])
        self.assertEqual(len(cur.ejecutadas), 2)              # sin UPDATE
        cur = FakeCursor([OFICINA, None],
                         falla_en=("UPDATE tag_definitions", psycopg2.errors.UniqueViolation("dup")))
        self.assertEqual(et.actualizar(cur, 5, name="Operativo")["codigo"], "nombre_duplicado")


class TestEliminar(unittest.TestCase):

    def test_no_existe(self):
        cur = FakeCursor([None])
        self.assertEqual(et.eliminar(cur, 99)["codigo"], "no_existe")

    def test_en_uso_sin_forzar_no_toca_nada(self):
        cur = FakeCursor([("Oficina",), (2, [236, 240])])
        r = et.eliminar(cur, 5)
        self.assertEqual((r["ok"], r["codigo"]), (False, "en_uso"))
        self.assertEqual(r["uso"], {"transacciones": 2, "borradores": [236, 240]})
        self.assertEqual(r["error"],
                         "La etiqueta «Oficina» está en 2 transacciones y 2 borradores abiertos del bot (#236, #240).")
        self.assertFalse(any(s.startswith(("UPDATE", "DELETE")) for s in cur.sqls()))
        _, params_uso = cur.ejecutadas[1]
        self.assertEqual(params_uso["abiertos"], ("BORRADOR", "PROCESANDO", "ERROR"))

    def test_forzada_la_quita_de_transacciones_y_borradores_y_borra(self):
        cur = FakeCursor([("Oficina",), (2, [236])], rowcounts=[0, 0, 2, 1, 1])
        r = et.eliminar(cur, 5, forzar=True)
        self.assertEqual(r, {"ok": True, "id": 5, "name": "Oficina",
                             "transacciones_actualizadas": 2, "borradores_actualizados": 1})
        sqls = cur.sqls()
        self.assertIn("UPDATE transactions SET tags = array_remove(tags, %s)", sqls[2])
        self.assertEqual(cur.ejecutadas[2][1], ("Oficina", "Oficina"))
        self.assertIn("UPDATE transaction_drafts", sqls[3])
        self.assertIn("jsonb_array_elements(payload->'tags')", sqls[3])
        self.assertEqual(sqls[4], "DELETE FROM tag_definitions WHERE id = %s")

    def test_sin_uso_borra_directo(self):
        cur = FakeCursor([("dfghj",), (0, [])])
        r = et.eliminar(cur, 1)
        self.assertEqual(r, {"ok": True, "id": 1, "name": "dfghj",
                             "transacciones_actualizadas": 0, "borradores_actualizados": 0})
        self.assertEqual(len(cur.ejecutadas), 3)              # lock, uso, DELETE
        self.assertEqual(cur.sqls()[2], "DELETE FROM tag_definitions WHERE id = %s")


class _ConCliente(unittest.TestCase):

    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers.auth_guard import create_session_token
        from routers.tags_taxes import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.admin = {"Authorization": "Bearer " + create_session_token(
            {"id": "u1", "name": "Andrés", "role": "owner"})}
        self.member = {"Authorization": "Bearer " + create_session_token(
            {"id": "u2", "name": "Vero", "role": "member"})}


class TestEndpointsEtiquetas(_ConCliente):

    def setUp(self):
        super().setUp()
        self.conn = mock.Mock()
        get = mock.patch("fin_sys_core.database_driver.get_db_connection", return_value=self.conn)
        put = mock.patch("fin_sys_core.database_driver.release_db_connection")
        self.get_conn, self.put_conn = get.start(), put.start()
        self.addCleanup(get.stop)
        self.addCleanup(put.stop)

    def _bd(self, fetchones, rowcounts=None):
        cur = FakeCursor(fetchones, rowcounts)
        self.conn.cursor.return_value = cur
        return cur

    def test_guards(self):
        self.assertEqual(self.client.put("/api/tags/5", json={"color": "#000000"}).status_code, 401)
        self.assertEqual(self.client.delete("/api/tags/5", headers=self.member).status_code, 403)
        self.get_conn.assert_not_called()

    def test_put_200_409_422_404_400(self):
        self._bd([OFICINA, None, (5, "Oficina central", "#2196F3")])
        r = self.client.put("/api/tags/5", json={"name": "Oficina central", "color": "#2196F3"}, headers=self.admin)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {"status": "OK", "tag": {"id": 5, "name": "Oficina central", "color": "#2196F3"}})
        self.conn.commit.assert_called_once()

        self._bd([OFICINA, (1,)])
        r = self.client.put("/api/tags/5", json={"name": "Operativo"}, headers=self.admin)
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("Ya existe", r.json()["detail"])

        r = self.client.put("/api/tags/5", json={"color": "rojo"}, headers=self.admin)
        self.assertEqual(r.status_code, 422, r.text)

        self._bd([None])
        self.assertEqual(self.client.put("/api/tags/99", json={"color": "#000000"}, headers=self.admin).status_code, 404)
        self.assertEqual(self.client.put("/api/tags/5", json={}, headers=self.admin).status_code, 400)
        self.conn.commit.assert_called_once()                 # solo el 200 confirmó
        self.conn.rollback.assert_called()

    def test_delete_409_y_luego_forzar(self):
        self._bd([("Oficina",), (2, [236])])
        r = self.client.delete("/api/tags/5", headers=self.admin)
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(r.json()["detail"],
                         "La etiqueta «Oficina» está en 2 transacciones y 1 borrador abierto del bot (#236).")
        self.conn.commit.assert_not_called()

        cur = self._bd([("Oficina",), (2, [236])], rowcounts=[0, 0, 2, 1, 1])
        r = self.client.delete("/api/tags/5?forzar=1", headers=self.admin)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {"status": "ELIMINADO", "id": 5, "name": "Oficina",
                                    "transacciones_actualizadas": 2, "borradores_actualizados": 1})
        self.assertEqual(cur.sqls()[-1], "DELETE FROM tag_definitions WHERE id = %s")
        self.conn.commit.assert_called_once()

    def test_delete_404(self):
        self._bd([None])
        r = self.client.delete("/api/tags/99", headers=self.admin)
        self.assertEqual(r.status_code, 404, r.text)
        self.assertEqual(r.json()["detail"], "Esa etiqueta no existe.")


class TestEndpointsImpuestos(_ConCliente):

    def test_put_valida_y_mapea(self):
        with mock.patch("fin_sys_core.database_driver.actualizar_custom_tax", return_value=True) as act:
            r = self.client.put("/api/custom-taxes/3", json={"name": " ReteICA ", "rate": "0.966", "type": "deductive"},
                                headers=self.admin)
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json(), {"status": "OK", "id": 3, "name": "ReteICA", "rate": 0.966, "tax_type": "DEDUCTIVE"})
            act.assert_called_once_with(3, name="ReteICA", rate=0.966, tax_type="DEDUCTIVE")
        with mock.patch("fin_sys_core.database_driver.actualizar_custom_tax", return_value=False):
            self.assertEqual(self.client.put("/api/custom-taxes/99", json={"rate": 5}, headers=self.admin).status_code, 404)
        with mock.patch("fin_sys_core.database_driver.actualizar_custom_tax") as act:
            for body in ({"name": " "}, {"rate": "abc"}, {"rate": -1}, {"type": "RARO"}):
                r = self.client.put("/api/custom-taxes/3", json=body, headers=self.admin)
                self.assertEqual(r.status_code, 422, body)
            self.assertEqual(self.client.put("/api/custom-taxes/3", json={}, headers=self.admin).status_code, 400)
            act.assert_not_called()
        self.assertEqual(self.client.put("/api/custom-taxes/3", json={"rate": 1}).status_code, 401)

    def test_delete_200_404_y_guards(self):
        with mock.patch("fin_sys_core.database_driver.eliminar_custom_tax", return_value=True) as borrar:
            r = self.client.delete("/api/custom-taxes/3", headers=self.admin)
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json(), {"status": "ELIMINADO", "id": 3})
            borrar.assert_called_once_with(3)
        with mock.patch("fin_sys_core.database_driver.eliminar_custom_tax", return_value=False):
            self.assertEqual(self.client.delete("/api/custom-taxes/99", headers=self.admin).status_code, 404)
        with mock.patch("fin_sys_core.database_driver.eliminar_custom_tax") as borrar:
            self.assertEqual(self.client.delete("/api/custom-taxes/3").status_code, 401)
            self.assertEqual(self.client.delete("/api/custom-taxes/3", headers=self.member).status_code, 403)
            borrar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
