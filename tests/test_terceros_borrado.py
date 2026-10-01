# -*- coding: utf-8 -*-
"""Borrar un tercero desde la web (👤 Terceros → 🗑), SIN BD.

Regla (decisión de Andrés, 30-sep-2026): 404 no existe · 409 genérico · 409
con historia (transacciones, cartera, inventario o borradores abiertos del
bot; el detail dice cuánta) · 200 sin historia. Hasta ese día el botón llamaba
a `DELETE /api/third-parties/{id}`, que no existía (405), y el error se tragaba.

Cubre la lógica de fin_sys_core/terceros_borrado.py con un cursor falso y el
endpoint de routers/cartera.py con TestClient (guards reales: 401 sin sesión,
403 sin rol admin) y la conexión parcheada.

Ejecutar:  .venv\\Scripts\\python.exe -m unittest tests.test_terceros_borrado -v
"""
import os
import sys
import unittest
from unittest import mock

import psycopg2.errors

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import fin_sys_core  # noqa: E402,F401  (un solo objeto por módulo)
from fin_sys_core import terceros_borrado as tb  # noqa: E402


class FakeCursor:
    """Registra cada execute y sirve fetchone desde una cola predefinida."""

    def __init__(self, fetchones, falla_en=None):
        self.ejecutadas = []          # [(sql normalizado, params), ...]
        self._fetchones = list(fetchones)
        self._falla_en = falla_en     # (fragmento de SQL, excepción a lanzar)

    def execute(self, sql, params=None):
        sql = " ".join(sql.split())
        self.ejecutadas.append((sql, params))
        if self._falla_en and self._falla_en[0] in sql:
            raise self._falla_en[1]

    def fetchone(self):
        return self._fetchones.pop(0)

    def close(self):
        pass

    def sql(self, i):
        return self.ejecutadas[i][0]


FILA_ANA = ("CC", "1122334455", "  Ana Prueba ")     # como la devuelve la BD (con espacios)
SIN_USO = (0, 0, 0, [])


class TestMensajes(unittest.TestCase):

    def test_describir_uso_singular_plural_y_conjuncion(self):
        self.assertEqual(tb.describir_uso({}), "")
        self.assertEqual(tb.describir_uso({"transacciones": 1}), "1 transacción")
        self.assertEqual(tb.describir_uso({"transacciones": 18, "cartera": 1}),
                         "18 transacciones y 1 cuenta de cartera (CXC/CXP)")
        self.assertEqual(
            tb.describir_uso({"transacciones": 2, "cartera": 3, "inventario": 1, "borradores": [236]}),
            "2 transacciones, 3 cuentas de cartera (CXC/CXP), 1 movimiento de inventario "
            "y 1 borrador abierto del bot (#236)")

    def test_describir_uso_recorta_la_lista_de_borradores(self):
        self.assertEqual(tb.describir_uso({"borradores": [1, 2, 3, 4, 5, 6, 7]}),
                         "7 borradores abiertos del bot (#1, #2, #3, #4, #5…)")

    def test_mensaje_en_uso_aconseja_segun_la_historia(self):
        solo_borrador = tb.mensaje_en_uso("Ana Prueba", {"borradores": [236]})
        self.assertIn("No se puede eliminar a «Ana Prueba»: tiene 1 borrador abierto del bot (#236).",
                      solo_borrador)
        self.assertIn("Bandeja del bot", solo_borrador)
        con_txs = tb.mensaje_en_uso("Ana Prueba", {"transacciones": 18, "borradores": [236]})
        self.assertIn("18 transacciones y 1 borrador abierto del bot (#236)", con_txs)
        self.assertIn("primero reasigna o elimina esos registros", con_txs)
        self.assertNotIn("Bandeja", con_txs)


class TestEliminar(unittest.TestCase):

    def test_no_existe(self):
        cur = FakeCursor([None])
        r = tb.eliminar(cur, 999)
        self.assertEqual((r["ok"], r["codigo"]), (False, "no_existe"))
        self.assertEqual(len(cur.ejecutadas), 1)
        self.assertIn("FOR UPDATE", cur.sql(0))          # la fila queda bloqueada
        self.assertEqual(cur.ejecutadas[0][1], (999,))

    def test_generico_jamas_se_borra(self):
        cur = FakeCursor([("NIT", "999999999", "Sin especificar")])
        r = tb.eliminar(cur, 38)
        self.assertEqual((r["ok"], r["codigo"]), (False, "generico"))
        self.assertIn("genérico", r["error"])
        self.assertEqual(len(cur.ejecutadas), 1)         # ni conteo ni DELETE

    def test_con_historia_devuelve_el_conteo_y_no_borra(self):
        cur = FakeCursor([FILA_ANA, (18, 1, 0, [])])
        r = tb.eliminar(cur, 2)
        self.assertEqual((r["ok"], r["codigo"]), (False, "en_uso"))
        self.assertEqual(r["uso"], {"transacciones": 18, "cartera": 1, "inventario": 0, "borradores": []})
        self.assertIn("«Ana Prueba»: tiene 18 transacciones y 1 cuenta de cartera (CXC/CXP)", r["error"])
        self.assertFalse(any("DELETE" in s for s, _ in cur.ejecutadas))
        # el conteo busca los borradores por documento y solo los abiertos
        sql_uso, params_uso = cur.ejecutadas[1]
        self.assertIn("transaction_drafts", sql_uso)
        self.assertIn("inventory_movements", sql_uso)
        self.assertEqual(params_uso["numero"], "1122334455")
        self.assertEqual(params_uso["abiertos"], ("BORRADOR", "PROCESANDO", "ERROR"))

    def test_borrador_abierto_del_bot_tambien_bloquea(self):
        cur = FakeCursor([FILA_ANA, (0, 0, 0, [236, 240])])
        r = tb.eliminar(cur, 25)
        self.assertEqual(r["codigo"], "en_uso")
        self.assertEqual(r["uso"]["borradores"], [236, 240])
        self.assertIn("2 borradores abiertos del bot (#236, #240)", r["error"])
        self.assertIn("Bandeja", r["error"])

    def test_sin_historia_borra_la_ficha(self):
        cur = FakeCursor([FILA_ANA, SIN_USO])
        r = tb.eliminar(cur, 34)
        self.assertEqual(r, {"ok": True, "id": 34, "name": "Ana Prueba",
                             "identification_type": "CC", "identification_number": "1122334455"})
        self.assertEqual(len(cur.ejecutadas), 3)
        sql_delete, params_delete = cur.ejecutadas[2]
        self.assertEqual(sql_delete, "DELETE FROM third_parties WHERE id = %s")
        self.assertEqual(params_delete, (34,))

    def test_fk_de_la_bd_manda_si_el_conteo_no_lo_vio(self):
        cur = FakeCursor([FILA_ANA, SIN_USO],
                         falla_en=("DELETE FROM third_parties", psycopg2.errors.ForeignKeyViolation("fk")))
        r = tb.eliminar(cur, 34)
        self.assertEqual((r["ok"], r["codigo"]), (False, "en_uso"))
        self.assertIn("«Ana Prueba»", r["error"])


class TestEndpoint(unittest.TestCase):
    """DELETE /api/third-parties/{id} con la conexión parcheada y tokens reales."""

    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers.auth_guard import create_session_token
        from routers.cartera import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.admin = {"Authorization": "Bearer " + create_session_token(
            {"id": "u1", "name": "Andrés", "role": "owner"})}
        self.member = {"Authorization": "Bearer " + create_session_token(
            {"id": "u2", "name": "Vero", "role": "member"})}
        self.conn = mock.Mock()
        get = mock.patch("fin_sys_core.database_driver.get_db_connection", return_value=self.conn)
        put = mock.patch("fin_sys_core.database_driver.release_db_connection")
        self.get_conn, self.put_conn = get.start(), put.start()
        self.addCleanup(get.stop)
        self.addCleanup(put.stop)

    def _bd(self, fetchones, falla_en=None):
        cur = FakeCursor(fetchones, falla_en)
        self.conn.cursor.return_value = cur
        return cur

    def test_sin_sesion_401_y_sin_rol_admin_403_no_tocan_la_bd(self):
        self.assertEqual(self.client.delete("/api/third-parties/34").status_code, 401)
        self.assertEqual(self.client.delete("/api/third-parties/34", headers=self.member).status_code, 403)
        self.get_conn.assert_not_called()

    def test_200_borra_y_confirma(self):
        cur = self._bd([FILA_ANA, SIN_USO])
        r = self.client.delete("/api/third-parties/34", headers=self.admin)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {"status": "ELIMINADO", "id": 34, "name": "Ana Prueba"})
        self.assertIn("DELETE FROM third_parties", cur.sql(2))
        self.conn.commit.assert_called_once()
        self.put_conn.assert_called_once_with(self.conn)

    def test_409_con_historia_explica_y_no_confirma(self):
        self._bd([FILA_ANA, (18, 1, 0, [])])
        r = self.client.delete("/api/third-parties/2", headers=self.admin)
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("tiene 18 transacciones y 1 cuenta de cartera (CXC/CXP)", r.json()["detail"])
        self.conn.commit.assert_not_called()
        self.conn.rollback.assert_called()
        self.put_conn.assert_called_once_with(self.conn)

    def test_409_generico_y_404_inexistente(self):
        self._bd([("NIT", "999999999", "Sin especificar")])
        r = self.client.delete("/api/third-parties/38", headers=self.admin)
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("genérico", r.json()["detail"])
        self._bd([None])
        r = self.client.delete("/api/third-parties/999999", headers=self.admin)
        self.assertEqual(r.status_code, 404, r.text)
        self.assertEqual(r.json()["detail"], "Ese tercero no existe.")
        self.conn.commit.assert_not_called()

    def test_500_con_el_error_visible_y_la_conexion_devuelta(self):
        self._bd([FILA_ANA], falla_en=("FROM third_parties WHERE id", RuntimeError("se cayó la BD")))
        r = self.client.delete("/api/third-parties/34", headers=self.admin)
        self.assertEqual(r.status_code, 500, r.text)
        self.assertEqual(r.json()["detail"], "se cayó la BD")
        self.conn.rollback.assert_called()
        self.put_conn.assert_called_once_with(self.conn)


if __name__ == "__main__":
    unittest.main()
