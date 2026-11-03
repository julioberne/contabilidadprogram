# -*- coding: utf-8 -*-
"""Escritura del libro (estándar H8, 30-oct-2026).

- Puros (CI sin BD): delta en Decimal al centavo, lo que se suma es lo que se
  revierte; cuentas en orden ascendente de id; el saldo es lo último antes del
  commit, al crear y al borrar.
- Contra la BD (se saltan sin DB_HOST): los triggers del panel corren al commit
  (tras migrate_h8.py); 200 pares A→B y B→A simultáneos sobre
  dos cuentas `test-h8-*` que se crean y se borran aquí, sin interbloqueo y sin
  perder un centavo; crear y borrar una TX real pasa por el trigger del panel
  (dentro de una transacción que se deshace).

    python -m unittest tests.test_escritura_h8
"""
import os
import sys
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import tests  # noqa: F401,E402

from fin_sys_core import incremental_balance as ib  # noqa: E402


class _Cur:
    """Monedas fijas; guarda los UPDATE en orden."""

    def __init__(self, monedas):
        self.monedas, self.updates, self.filas = monedas, [], []

    def execute(self, sql, params=None):
        if "SELECT id, currency" in sql:
            self.filas = [(i, self.monedas[i]) for i in params[0] if i in self.monedas]
        elif "UPDATE user_accounts" in sql:
            self.updates.append((params[1], params[0]))

    def fetchall(self):
        return self.filas

    def close(self):
        pass


class _Conn:
    def __init__(self, monedas):
        self.cur = _Cur(monedas)

    def cursor(self):
        return self.cur


def _traslado(origen, destino, monto="100"):
    return {"type": "TRANSFERENCIA", "amount": monto, "net_value": monto, "account_id": origen,
            "dest_account_id": destino, "trm": 1, "transaction_currency": "COP"}


class TestDelta(unittest.TestCase):
    def test_es_decimal_y_sin_ruido_de_float(self):
        tx = {"type": "INGRESO", "net_value": 0.1 + 0.2, "amount": 0, "trm": 1, "transaction_currency": "COP"}
        self.assertEqual(ib.calcular_delta_cuenta(tx, "COP"), Decimal("0.30"))

    def test_conversion_al_centavo(self):
        tx = {"type": "GASTO", "net_value": Decimal("10.01"), "amount": 0, "trm": Decimal("3999.4567"),
              "transaction_currency": "USD"}
        self.assertEqual(ib.calcular_delta_cuenta(tx, "COP"), Decimal("-40034.56"))

    def test_la_mitad_redondea_como_numeric(self):
        tx = {"type": "INGRESO", "net_value": 1, "amount": 0, "trm": Decimal("1.005"),
              "transaction_currency": "USD"}
        self.assertEqual(ib.calcular_delta_cuenta(tx, "COP"), Decimal("1.01"))
        tx["type"] = "GASTO"
        self.assertEqual(ib.calcular_delta_cuenta(tx, "COP"), Decimal("-1.01"))

    def test_lo_que_se_suma_es_lo_que_se_revierte(self):
        """Con delta sin redondear, sumar y revertir sobre numeric(15,2) deja 1 centavo."""
        tx = {"type": "INGRESO", "net_value": 1, "amount": 0, "trm": Decimal("12.345"),
              "transaction_currency": "USD", "account_id": 1}
        conn = _Conn({1: "COP"})
        ib.aplicar_delta_incremental(conn, tx)
        ib.revertir_delta_incremental(conn, tx)
        self.assertEqual(sum(d for _, d in conn.cur.updates), Decimal("0"))


class TestOrden(unittest.TestCase):
    def test_traslado_bloquea_de_menor_a_mayor_en_ambos_sentidos(self):
        for origen, destino in ((3, 9), (9, 3)):
            conn = _Conn({3: "COP", 9: "COP"})
            ib.aplicar_delta_incremental(conn, _traslado(origen, destino))
            self.assertEqual([c for c, _ in conn.cur.updates], [3, 9])
            self.assertEqual(dict(conn.cur.updates), {origen: Decimal("-100.00"), destino: Decimal("100.00")})

    def test_revertir_tambien_va_en_orden(self):
        conn = _Conn({3: "COP", 9: "COP"})
        ib.revertir_delta_incremental(conn, _traslado(9, 3))
        self.assertEqual(conn.cur.updates, [(3, Decimal("-100.00")), (9, Decimal("100.00"))])

    def test_editar_es_un_solo_paso_y_neto(self):
        conn = _Conn({3: "COP", 5: "COP", 9: "COP"})
        ib.reemplazar_delta_incremental(conn, _traslado(9, 3, "100"), _traslado(9, 5, "30"))
        self.assertEqual(conn.cur.updates, [(3, Decimal("-100.00")), (5, Decimal("30.00")), (9, Decimal("70.00"))])

    def test_editar_sin_cambio_de_monto_no_toca_la_cuenta(self):
        conn = _Conn({3: "COP", 9: "COP"})
        ib.reemplazar_delta_incremental(conn, _traslado(9, 3), _traslado(9, 3))
        self.assertEqual(conn.cur.updates, [])

    def test_sin_cuenta_o_cuenta_inexistente_no_toca_nada(self):
        conn = _Conn({3: "COP"})
        ib.aplicar_delta_incremental(conn, {"type": "GASTO", "account_id": None})
        ib.aplicar_delta_incremental(conn, _traslado(8, 3))          # origen borrado
        self.assertEqual(conn.cur.updates, [])
        ib.aplicar_delta_incremental(conn, _traslado(3, 8))          # destino borrado: solo el origen
        self.assertEqual(conn.cur.updates, [(3, Decimal("-100.00"))])


class TestSaldoAlFinal(unittest.TestCase):
    def test_al_crear_el_asiento_va_antes_que_el_saldo(self):
        from tests.test_tx_atomica import FakeConn, _tx_data
        import fin_sys_core.database_driver as dd
        pasos = []
        conn = FakeConn(respuestas=[[(3,)], [(42,)]])
        with mock.patch.object(dd, "get_db_connection", return_value=conn), \
             mock.patch.object(dd, "release_db_connection"), \
             mock.patch.object(dd, "_asegurar_tercero", return_value=7), \
             mock.patch.object(dd, "aplicar_delta_incremental", side_effect=lambda *a: pasos.append("saldo")), \
             mock.patch.object(dd, "mock_permitido", return_value=False):
            dd.registrar_transaccion(_tx_data(), on_before_commit=lambda *a: pasos.append("asiento"))
        self.assertEqual(pasos, ["asiento", "saldo"])

    def test_al_borrar_el_saldo_va_despues_de_los_delete(self):
        from tests.test_tx_atomica import FakeConn
        import fin_sys_core.database_driver as dd
        conn = FakeConn(respuestas=[[("GASTO", 1, 1, 2, None, 1, "COP", "x")]])

        def saldo(*a):
            self.assertTrue(any("DELETE FROM transactions" in s for s in conn.sql), "el DELETE va primero")

        with mock.patch.object(dd, "get_db_connection", return_value=conn), \
             mock.patch.object(dd, "release_db_connection"), \
             mock.patch.object(dd, "revertir_delta_incremental", side_effect=saldo) as rev:
            dd.eliminar_transaccion(1)
        rev.assert_called_once()
        self.assertEqual(conn.commits, 1)


@unittest.skipUnless(os.environ.get("DB_HOST"), "requiere BD")
class TestConcurrenciaReal(unittest.TestCase):
    """Escribe SOLO en dos cuentas `test-h8-*` propias, y las borra al terminar."""

    PARES = 200

    def setUp(self):
        from fin_sys_core.db_pool import get_conn, put_conn
        self.get_conn, self.put_conn = get_conn, put_conn
        sello = uuid.uuid4().hex[:8]
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""INSERT INTO user_accounts (name, type, currency, initial_balance, current_balance)
                           VALUES (%s, 'Efectivo', 'COP', 0, 1000), (%s, 'Efectivo', 'COP', 0, 1000)
                           RETURNING id""", (f"test-h8-a-{sello}", f"test-h8-b-{sello}"))
            self.a, self.b = sorted(r[0] for r in cur.fetchall())
            conn.commit()
        finally:
            put_conn(conn)

    def tearDown(self):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM user_accounts WHERE id IN (%s, %s) AND name LIKE 'test-h8-%%'", (self.a, self.b))
            conn.commit()
            self.assertEqual(cur.rowcount, 2)
        finally:
            self.put_conn(conn)

    def _mover(self, origen, destino, errores, barrera):
        conn = self.get_conn()
        try:
            barrera.wait(timeout=10)
            ib.aplicar_delta_incremental(conn, _traslado(origen, destino, "1.25"))
            conn.commit()
        except Exception as e:                       # deadlock detected, entre otros
            conn.rollback()
            errores.append(str(e)[:200])
        finally:
            self.put_conn(conn)

    def test_200_pares_cruzados_sin_interbloqueo(self):
        errores = []

        def ronda(_):
            barrera = threading.Barrier(2)
            uno = threading.Thread(target=self._mover, args=(self.a, self.b, errores, barrera))
            dos = threading.Thread(target=self._mover, args=(self.b, self.a, errores, barrera))
            uno.start(); dos.start(); uno.join(); dos.join()

        with ThreadPoolExecutor(max_workers=4) as hilos:
            list(hilos.map(ronda, range(self.PARES)))
        self.assertEqual(errores, [])
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT current_balance FROM user_accounts WHERE id IN (%s, %s) ORDER BY id", (self.a, self.b))
            saldos = [r[0] for r in cur.fetchall()]
        finally:
            conn.rollback()
            self.put_conn(conn)
        self.assertEqual(saldos, [Decimal("1000.00"), Decimal("1000.00")], "cada par se cancela exacto")


def _triggers_al_commit():
    if not os.environ.get("DB_HOST"):
        return False
    from fin_sys_core.db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT bool_and(tgdeferrable) FROM pg_trigger "
                    "WHERE tgname IN ('panel_tx_cambio', 'panel_cuenta_cambio') AND NOT tgisinternal")
        return bool(cur.fetchone()[0])
    finally:
        conn.rollback()
        put_conn(conn)


@unittest.skipUnless(_triggers_al_commit(), "requiere BD con migrate_h8.py")
class TestTriggersAlCommit(unittest.TestCase):
    """La versión del panel sube al hacer commit y no queda bloqueada mientras se
    escribe. Solo toca una cuenta `test-h8-*` propia, que se borra al terminar."""

    def setUp(self):
        from fin_sys_core.db_pool import get_conn, put_conn
        self.get_conn, self.put_conn = get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""INSERT INTO user_accounts (name, type, currency, initial_balance, current_balance)
                           VALUES (%s, 'Efectivo', 'COP', 0, 0) RETURNING id""", (f"test-h8-v-{uuid.uuid4().hex[:8]}",))
            self.cuenta = cur.fetchone()[0]
            conn.commit()
        finally:
            put_conn(conn)

    def tearDown(self):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM user_accounts WHERE id = %s AND name LIKE 'test-h8-%%'", (self.cuenta,))
            conn.commit()
        finally:
            self.put_conn(conn)

    def test_la_version_sube_al_commit_sin_bloquear_antes(self):
        escritor, otro = self.get_conn(), self.get_conn()
        try:
            co = otro.cursor()
            co.execute("SELECT version FROM panel_version WHERE portfolio_id = 0")
            antes = co.fetchone()[0]
            otro.rollback()
            escritor.cursor().execute("UPDATE user_accounts SET current_balance = current_balance + 1 WHERE id = %s",
                                      (self.cuenta,))
            # Con los triggers de H7 la fila 0 ya estaría tomada aquí y NOWAIT fallaría.
            co.execute("SELECT version FROM panel_version WHERE portfolio_id = 0 FOR UPDATE NOWAIT")
            self.assertEqual(co.fetchone()[0], antes, "antes del commit la versión no cambia")
            otro.rollback()
            escritor.commit()
            co.execute("SELECT version FROM panel_version WHERE portfolio_id = 0")
            self.assertGreater(co.fetchone()[0], antes, "al hacer commit sube")
        finally:
            escritor.rollback()
            otro.rollback()
            self.put_conn(escritor)
            self.put_conn(otro)


@unittest.skipUnless(_triggers_al_commit(), "requiere BD con migrate_h8.py")
class TestTriggerDeTransacciones(unittest.TestCase):
    """Escribe en `transactions`, no solo en cuentas: ahí `portfolio_id` es bigint y
    `panel_subir` recibe integer; sin el `::integer` toda TX fallaba al commit
    (30-oct a 3-nov). Todo va dentro de una transacción que se deshace:
    SET CONSTRAINTS ALL IMMEDIATE corre ahí mismo los triggers diferidos, sin
    dejar filas ni subir la versión de verdad."""

    def test_crear_y_borrar_una_transaccion_pasa_por_el_trigger(self):
        from fin_sys_core.db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""INSERT INTO transactions (portfolio_id, third_party_id, type, amount, concept,
                               transaction_date, payment_method, category, net_value)
                           SELECT p.id, t.id, 'GASTO', 1, %s, CURRENT_DATE, 'Efectivo', 'Otros Gastos', 1
                             FROM (SELECT id FROM portfolios ORDER BY id LIMIT 1) p,
                                  (SELECT id FROM third_parties ORDER BY id LIMIT 1) t
                           RETURNING id, portfolio_id""", (f"test-h8-tx-{uuid.uuid4().hex[:8]}",))
            tx, pid = cur.fetchone()

            def version():
                cur.execute("SELECT version FROM panel_version WHERE portfolio_id = %s", (pid,))
                fila = cur.fetchone()
                return fila[0] if fila else 0

            antes = version()
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")   # el trigger del INSERT corre aquí, como al commit
            creada = version()
            self.assertGreater(creada, antes, "al crear sube la versión de la empresa (NEW.portfolio_id)")
            cur.execute("DELETE FROM transactions WHERE id = %s", (tx,))
            self.assertGreater(version(), creada, "al borrar también (OLD.portfolio_id)")
        finally:
            conn.rollback()
            put_conn(conn)


if __name__ == "__main__":
    unittest.main()
