# -*- coding: utf-8 -*-
"""TX + asiento en UNA transacción de BD (plan cimientos A3). Sin BD real.

- registrar_transaccion(on_before_commit=hook): si el hook lanza un error de
  BD, NO hay commit y SÍ hay rollback (nada queda escrito).
- registrar_asiento(evento, conn=externa): no toma ni devuelve conexión del
  pool, no commitea; usa SAVEPOINT; un error de configuración hace
  ROLLBACK TO SAVEPOINT y relanza (la transacción del llamador sigue sana).
- build_journal_event: None sin regla; __BANK__ resuelto; 2 líneas cuadradas.
"""
import os
import sys
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import fin_sys_core  # noqa: E402,F401


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.description = None
        self._rows = []

    def execute(self, sql, params=None):
        self.conn.sql.append(" ".join(str(sql).split()))
        if self.conn.fail_on and self.conn.fail_on in str(sql):
            raise RuntimeError(f"fallo simulado en: {self.conn.fail_on}")
        self._rows = self.conn.respuestas.pop(0) if self.conn.respuestas else []

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def close(self):
        pass


class FakeConn:
    def __init__(self, respuestas=None, fail_on=None):
        self.sql = []
        self.respuestas = list(respuestas or [])
        self.fail_on = fail_on
        self.commits = 0
        self.rollbacks = 0
        self.cursor_factory = None

    def cursor(self, cursor_factory=None):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _tx_data():
    return {
        "portfolio_name": "Negocio A", "type": "GASTO", "amount": 100.0,
        "concept": "test", "payment_method": "Efectivo", "category": "Servicios",
        "transaction_date": "2026-09-15",
        "third_party": {"identification_type": "NIT", "identification_number": "1",
                        "name": "X", "email": None, "phone": None, "website": None},
        "tax_iva_percentage": 0, "tax_iva_amount": 0, "tax_gmf_percentage": 0,
        "tax_gmf_amount": 0, "custom_tax_amount": 0, "net_value": 100.0,
        "geo_latitude": None, "geo_longitude": None, "geo_maps_link": None,
        "account_id": None, "dest_account_id": None, "trm": 1, "transaction_currency": "COP",
        "cxc_cxp": None, "asset": None, "evidence_file_path": None, "is_recurring": False,
        "recurrence_interval": None, "recurrence_days": None, "recurrence_max_reps": None,
        "recurrence_start_date": None, "recurrence_end_date": None, "tags": None,
        "evidence_files": None,
    }


class TestRegistrarTransaccionConHook(unittest.TestCase):
    def _driver(self, conn):
        import fin_sys_core.database_driver as dd
        patches = [
            mock.patch.object(dd, "get_db_connection", return_value=conn),
            mock.patch.object(dd, "release_db_connection"),
            mock.patch.object(dd, "_asegurar_tercero", return_value=7),
            mock.patch.object(dd, "aplicar_delta_incremental"),
            mock.patch.object(dd, "mock_permitido", return_value=False),
            mock.patch.object(dd, "IS_POSTGRES_ACTIVE", True),
        ]
        return dd, patches

    def test_hook_falla_por_bd_no_hay_commit(self):
        # respuestas: SELECT portfolios → id 3; INSERT transactions → id 42
        conn = FakeConn(respuestas=[[(3,)], [(42,)]])
        dd, patches = self._driver(conn)
        for p in patches:
            p.start()
        try:
            def hook(c, tx_id):
                self.assertIs(c, conn)
                self.assertEqual(tx_id, 42)
                raise RuntimeError("psycopg2 caído")
            with self.assertRaises(RuntimeError):
                dd.registrar_transaccion(_tx_data(), on_before_commit=hook)
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(conn.commits, 0, "no debe commitear si el asiento falló")
        self.assertGreaterEqual(conn.rollbacks, 1, "debe hacer rollback de la TX")

    def test_hook_ok_commitea_una_vez(self):
        conn = FakeConn(respuestas=[[(3,)], [(42,)]])
        dd, patches = self._driver(conn)
        for p in patches:
            p.start()
        try:
            llamado = {}
            def hook(c, tx_id):
                llamado["tx_id"] = tx_id
            tx_id = dd.registrar_transaccion(_tx_data(), on_before_commit=hook)
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(tx_id, 42)
        self.assertEqual(llamado["tx_id"], 42)
        self.assertEqual(conn.commits, 1)
        # el hook corre ANTES del commit
        self.assertLess(len([s for s in conn.sql if "INSERT INTO transactions" in s]), 2)

    def test_sin_hook_comportamiento_de_siempre(self):
        conn = FakeConn(respuestas=[[(3,)], [(42,)]])
        dd, patches = self._driver(conn)
        for p in patches:
            p.start()
        try:
            self.assertEqual(dd.registrar_transaccion(_tx_data()), 42)
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(conn.commits, 1)


class TestRegistrarAsientoConConexionExterna(unittest.TestCase):
    def _evento(self, ref="TX-1"):
        return {"fecha": "2026-09-15", "modulo_origen": "zero_coa", "referencia": ref,
                "descripcion": "t", "omitir_dedupe": True,
                "asientos": [{"cuenta_codigo": "5105", "debito": 10, "credito": 0},
                             {"cuenta_codigo": "111005", "debito": 0, "credito": 10}]}

    def test_no_toca_el_pool_ni_commitea(self):
        import kernel.kernel_accounting as ka
        conn = FakeConn()
        with mock.patch.object(ka, "get_conn", side_effect=AssertionError("no debe pedir conexión")), \
             mock.patch.object(ka, "put_conn", side_effect=AssertionError("no debe devolver conexión")), \
             mock.patch("shared.rules_cache.codigos_conocidos", return_value=True), \
             mock.patch.object(ka, "execute_values") as ev:
            r = ka.registrar_asiento(self._evento(), conn=conn)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["lineas"], 2)
        self.assertEqual(conn.commits, 0)
        self.assertIn("SAVEPOINT asiento", conn.sql)
        self.assertIn("RELEASE SAVEPOINT asiento", conn.sql)
        self.assertTrue(ev.called)
        # con omitir_dedupe no hay SELECT de idempotencia
        self.assertFalse(any("SELECT entry_group_id" in s for s in conn.sql))

    def test_cuenta_inexistente_rollback_to_savepoint_y_relanza(self):
        import kernel.kernel_accounting as ka
        # la caché no conoce los códigos → consulta BD → devuelve solo uno
        conn = FakeConn(respuestas=[[], [("5105",)]])
        with mock.patch("shared.rules_cache.codigos_conocidos", return_value=False):
            with self.assertRaises(ka.CuentaNoExisteError):
                ka.registrar_asiento(self._evento(), conn=conn)
        self.assertIn("ROLLBACK TO SAVEPOINT asiento", conn.sql)
        self.assertEqual(conn.rollbacks, 0, "la transacción del llamador sigue sana")

    def test_descuadre_no_toca_la_bd(self):
        import kernel.kernel_accounting as ka
        conn = FakeConn()
        ev = self._evento()
        ev["asientos"][1]["credito"] = 9.99
        with self.assertRaises(ka.PartidaDobleError):
            ka.registrar_asiento(ev, conn=conn)
        self.assertEqual(conn.sql, [])

    def test_sin_conexion_externa_usa_pool_y_commitea(self):
        import kernel.kernel_accounting as ka
        conn = FakeConn(respuestas=[[]])   # dedupe → nada
        with mock.patch.object(ka, "get_conn", return_value=conn), \
             mock.patch.object(ka, "put_conn") as put, \
             mock.patch("shared.rules_cache.codigos_conocidos", return_value=True), \
             mock.patch.object(ka, "execute_values"):
            ev = self._evento(); ev.pop("omitir_dedupe")
            r = ka.registrar_asiento(ev)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(conn.commits, 1)
        put.assert_called_once_with(conn)
        self.assertNotIn("SAVEPOINT asiento", conn.sql)


class TestBuildJournalEvent(unittest.TestCase):
    def test_sin_regla_devuelve_none(self):
        from shared.helpers import build_journal_event
        with mock.patch("shared.rules_cache.get_rule", return_value=None):
            self.assertIsNone(build_journal_event("X", "GASTO", 10, referencia="TX-1"))

    def test_resuelve_bank_y_cuadra(self):
        from shared.helpers import build_journal_event
        with mock.patch("shared.rules_cache.get_rule", return_value=("5105", "__BANK__", "Regla")), \
             mock.patch("shared.rules_cache.resolve_bank_code", return_value="110505"):
            ev = build_journal_event("Servicios", "GASTO", 123.45, account_id=9,
                                     referencia="TX-9", descripcion="d", fecha="2026-09-15")
        self.assertEqual(ev["referencia"], "TX-9")
        self.assertEqual(ev["modulo_origen"], "zero_coa")
        self.assertEqual([a["cuenta_codigo"] for a in ev["asientos"]], ["5105", "110505"])
        self.assertEqual(sum(a["debito"] for a in ev["asientos"]),
                         sum(a["credito"] for a in ev["asientos"]))
        self.assertEqual(ev["asientos"][0]["cuenta_tipo"], "GASTO")
        self.assertEqual(ev["asientos"][1]["cuenta_tipo"], "ACTIVO")


if __name__ == "__main__":
    unittest.main()
