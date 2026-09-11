# -*- coding: utf-8 -*-
"""Eliminar transacción con reversa contable + adjuntar evidencias a una TX
existente (pedidos de Andrés, 2026-09-11). La clave de admin se verifica en
el router (verificar_clave_admin) — aquí se prueba la mecánica del driver."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fin_sys_core"))

import database_driver  # noqa: E402


class FakeCursor:
    def __init__(self, fetchones, fetchalls=None):
        self.ejecutadas = []
        self._fetchones = list(fetchones)
        self._fetchalls = list(fetchalls or [])

    def execute(self, sql, params=None):
        self.ejecutadas.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self._fetchones.pop(0)

    def fetchall(self):
        return self._fetchalls.pop(0)

    def close(self):
        pass


class FakeConn:
    def __init__(self, cur):
        self.cur = cur
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, *a, **k):
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _con_conexion_falsa(cur):
    conn = FakeConn(cur)
    return mock.patch.multiple(
        database_driver,
        get_db_connection=mock.Mock(return_value=conn),
        release_db_connection=mock.Mock(),
        revertir_delta_incremental=mock.Mock(),
    ), conn


class TestEliminarTransaccion(unittest.TestCase):

    def test_elimina_con_reversa_y_cartera(self):
        cur = FakeCursor([("GASTO", 100.0, 100.0, 3, None, 1.0, "COP", "Compra mouse")])
        parche, conn = _con_conexion_falsa(cur)
        with parche:
            info = database_driver.eliminar_transaccion(42)
            # La reversa contable corre ANTES del DELETE, con el snapshot
            database_driver.revertir_delta_incremental.assert_called_once()
            snapshot = database_driver.revertir_delta_incremental.call_args[0][1]
            self.assertEqual(snapshot["type"], "GASTO")
            self.assertEqual(snapshot["account_id"], 3)
        sqls = [s for s, _ in cur.ejecutadas]
        self.assertIn("DELETE FROM cxp_cxc_ledger WHERE transaction_id = %s;", sqls)
        self.assertIn("DELETE FROM transactions WHERE id = %s;", sqls)
        self.assertEqual(conn.commits, 1)
        self.assertEqual(info, {"concept": "Compra mouse", "net_value": 100.0})

    def test_tx_inexistente_no_borra_nada(self):
        cur = FakeCursor([None])
        parche, conn = _con_conexion_falsa(cur)
        with parche:
            with self.assertRaises(ValueError):
                database_driver.eliminar_transaccion(999)
        self.assertEqual(conn.commits, 0)
        self.assertFalse(any("DELETE" in s for s, _ in cur.ejecutadas))


class TestAgregarEvidencias(unittest.TestCase):

    def test_adjunta_y_migra_principal_antigua(self):
        """TX vieja: evidence_file_path poblado pero sin filas en
        transaction_evidences — la principal se migra para no perderse."""
        cur = FakeCursor(
            fetchones=[("/uploads/viejo.jpg",), (0,)],
            fetchalls=[[("/uploads/viejo.jpg",), ("https://bucket/n1.jpg",)]],
        )
        parche, conn = _con_conexion_falsa(cur)
        with parche:
            todas = database_driver.agregar_evidencias(7, ["https://bucket/n1.jpg", ""])
        inserts = [p for s, p in cur.ejecutadas if "INSERT INTO transaction_evidences" in s]
        self.assertEqual([p[1] for p in inserts], ["/uploads/viejo.jpg", "https://bucket/n1.jpg"])
        # Ya había principal: no se toca
        self.assertFalse(any("UPDATE transactions" in s for s, _ in cur.ejecutadas))
        self.assertEqual(conn.commits, 1)
        self.assertEqual(todas, ["/uploads/viejo.jpg", "https://bucket/n1.jpg"])

    def test_sin_principal_la_primera_nueva_asume(self):
        cur = FakeCursor(
            fetchones=[(None,), (0,)],
            fetchalls=[[("https://bucket/a.pdf",)]],
        )
        parche, _ = _con_conexion_falsa(cur)
        with parche:
            database_driver.agregar_evidencias(8, ["https://bucket/a.pdf"])
        updates = [p for s, p in cur.ejecutadas if "UPDATE transactions SET evidence_file_path" in s]
        self.assertEqual(updates, [("https://bucket/a.pdf", 8)])


if __name__ == "__main__":
    unittest.main()
