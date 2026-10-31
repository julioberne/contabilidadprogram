# -*- coding: utf-8 -*-
"""Un envío, una transacción (estándar H8.2, 30-oct-2026).

- Puros (CI sin BD): reservar, repetir, otra huella y sin la migración; la clave
  entra antes que todo y se guarda antes del saldo; una repetición devuelve la
  misma TX sin escribir; el router arma la clave; el bot suelta su conexión
  antes de registrar y nunca retiene dos.
- Contra la BD (se saltan sin DB_HOST o sin la migración): dos envíos simultáneos
  con la misma clave `test-`, uno solo gana.

    python -m unittest tests.test_idempotencia
"""
import os
import sys
import threading
import unittest
import uuid
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import tests  # noqa: F401,E402

import psycopg2.errors  # noqa: E402

from fin_sys_core import idempotencia as idem  # noqa: E402
from tests.test_tx_atomica import FakeConn, _tx_data  # noqa: E402


class _Cur:
    def __init__(self, filas=None, falla=None):
        self.sqls, self.filas, self.falla = [], list(filas or []), falla

    def execute(self, sql, params=None):
        self.sqls.append(" ".join(sql.split()))
        if self.falla and "INSERT" in sql:
            raise self.falla

    def fetchone(self):
        return self.filas.pop(0) if self.filas else None


class TestReservar(unittest.TestCase):
    def test_clave_nueva(self):
        cur = _Cur([("k",)])
        self.assertTrue(idem.reservar(cur, "k", "h"))
        self.assertIn("RELEASE SAVEPOINT idempotencia", cur.sqls)

    def test_repetida_devuelve_su_transaccion(self):
        cur = _Cur([None, ("h", 42)])
        with self.assertRaises(idem.TransaccionRepetida) as e:
            idem.reservar(cur, "k", "h")
        self.assertEqual(e.exception.transaction_id, 42)

    def test_misma_clave_con_otros_datos(self):
        with self.assertRaises(idem.ClaveReusada):
            idem.reservar(_Cur([None, ("otra", 42)]), "k", "h")

    def test_el_bot_no_compara_huella(self):
        with self.assertRaises(idem.TransaccionRepetida):
            idem.reservar(_Cur([None, (None, 42)]), "draft:1")

    def test_sin_la_migracion_sigue_sin_abortar(self):
        cur = _Cur(falla=psycopg2.errors.UndefinedTable("no existe"))
        self.assertFalse(idem.reservar(cur, "k", "h"))
        self.assertEqual(cur.sqls[-1], "ROLLBACK TO SAVEPOINT idempotencia", "la transacción sigue usable")

    def test_otro_error_de_bd_no_se_traga(self):
        with self.assertRaises(ValueError):
            idem.reservar(_Cur(falla=ValueError("otra cosa")), "k", "h")

    def test_huella_estable(self):
        self.assertEqual(idem.huella_de({"a": 1, "b": 2}), idem.huella_de({"b": 2, "a": 1}))
        self.assertNotEqual(idem.huella_de({"a": 1}), idem.huella_de({"a": 2}))


class TestRegistrar(unittest.TestCase):
    def _correr(self, conn, tx, reservar, hook=None):
        import fin_sys_core.database_driver as dd
        pasos = []
        self.saldo = mock.Mock(side_effect=lambda *a: pasos.append("saldo"))
        guardar = mock.Mock(side_effect=lambda *a: pasos.append("guardar"))
        with mock.patch.object(dd, "get_db_connection", return_value=conn), \
             mock.patch.object(dd, "release_db_connection") as soltar, \
             mock.patch.object(dd, "_asegurar_tercero", return_value=7), \
             mock.patch.object(dd, "aplicar_delta_incremental", self.saldo), \
             mock.patch.object(dd, "mock_permitido", return_value=True), \
             mock.patch.object(dd.idempotencia, "reservar", reservar), \
             mock.patch.object(dd.idempotencia, "guardar", guardar):
            try:
                return dd.registrar_transaccion(tx, on_before_commit=lambda *a: pasos.append("asiento")), pasos
            finally:
                soltar.assert_called_once_with(conn)

    def test_clave_nueva_se_guarda_antes_del_saldo(self):
        conn = FakeConn(respuestas=[[(3,)], [(42,)]])
        tx = {**_tx_data(), "idempotency_key": "k", "idempotency_huella": "h"}
        reservar = mock.Mock(return_value=True)
        tx_id, pasos = self._correr(conn, tx, reservar)
        self.assertEqual(tx_id, 42)
        self.assertEqual(pasos, ["asiento", "guardar", "saldo"])
        self.assertEqual(reservar.call_args[0][1:], ("k", "h"))

    def test_sin_clave_ni_siquiera_consulta(self):
        conn = FakeConn(respuestas=[[(3,)], [(42,)]])
        reservar = mock.Mock()
        _, pasos = self._correr(conn, _tx_data(), reservar)
        reservar.assert_not_called()
        self.assertEqual(pasos, ["asiento", "saldo"])

    def test_sin_la_migracion_registra_igual_sin_guardar_clave(self):
        conn = FakeConn(respuestas=[[(3,)], [(42,)]])
        _, pasos = self._correr(conn, {**_tx_data(), "idempotency_key": "k"}, mock.Mock(return_value=False))
        self.assertEqual(pasos, ["asiento", "saldo"])

    def test_repetida_no_escribe_ni_cae_a_la_simulacion(self):
        conn = FakeConn()
        reservar = mock.Mock(side_effect=idem.TransaccionRepetida(42))
        with self.assertRaises(idem.TransaccionRepetida):
            self._correr(conn, {**_tx_data(), "idempotency_key": "k"}, reservar)
        self.assertEqual(conn.commits, 0)
        self.assertGreaterEqual(conn.rollbacks, 1)
        self.assertFalse(any("INSERT INTO transactions" in s for s in conn.sql))
        self.saldo.assert_not_called()


def _entrada():
    from routers.schemas import TransactionInput
    return TransactionInput(portfolio_name="Negocio A", type="GASTO", amount=100.0, concept="x",
                            payment_method="Efectivo", category="Servicios",
                            third_party={"identification_type": "NIT", "identification_number": "1", "name": "X"},
                            transaction_date="2026-10-30")


class TestServicio(unittest.TestCase):
    def test_repetida_devuelve_la_misma_sin_avisar_a_nadie(self):
        from fin_sys_core import transaction_service as ts
        import database_driver
        import kernel.kernel_event_bus as bus
        import kernel.kernel_periods as periodos
        from fin_sys_core import dashboard_query
        with mock.patch.object(database_driver, "registrar_transaccion", side_effect=idem.TransaccionRepetida(42)) as reg, \
             mock.patch.object(periodos, "assert_periodo_abierto_por_nombre"), \
             mock.patch.object(dashboard_query, "obtener_transaccion", return_value={"id": 42}), \
             mock.patch.object(bus, "emit") as emit:
            r = ts.create_transaction(_entrada(), idempotency_key="web:k", huella="h")
        self.assertEqual((r["transaction_id"], r["repetida"], r["journal"]), (42, True, "skipped_duplicate"))
        self.assertEqual(r["transaction"], {"id": 42})
        self.assertEqual(reg.call_args[0][0]["idempotency_key"], "web:k")
        self.assertEqual(reg.call_args[0][0]["idempotency_huella"], "h")
        emit.assert_not_called()


class TestRouter(unittest.TestCase):
    def test_con_cabecera_arma_clave_y_huella(self):
        import transaction_service
        from routers.transactions import create_manual_transaction
        with mock.patch.object(transaction_service, "create_transaction", return_value={}) as crear:
            create_manual_transaction(_entrada(), {}, "abc")
        self.assertEqual(crear.call_args.kwargs["idempotency_key"], "web:abc")
        self.assertEqual(len(crear.call_args.kwargs["huella"]), 64)

    def test_sin_cabecera_como_antes(self):
        import transaction_service
        from routers.transactions import create_manual_transaction
        with mock.patch.object(transaction_service, "create_transaction", return_value={}) as crear:
            create_manual_transaction(_entrada(), {}, None)
        self.assertEqual(crear.call_args.kwargs, {})

    def test_misma_clave_otros_datos_es_422(self):
        import transaction_service
        from fastapi import HTTPException
        from routers.transactions import create_manual_transaction
        with mock.patch.object(transaction_service, "create_transaction", side_effect=idem.ClaveReusada("k")):
            with self.assertRaises(HTTPException) as e:
                create_manual_transaction(_entrada(), {}, "abc")
        self.assertEqual(e.exception.status_code, 422)


class _CurBot:
    def __init__(self):
        self.sqls, self._fila = [], None

    def execute(self, sql, params=None):
        self.sqls.append(" ".join(sql.split()))
        self._fila = None
        if "RETURNING payload, media_path" in sql:
            self._fila = ({"amount": 100, "concept": "x"}, None, [])

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return []


class _ConnBot:
    def __init__(self):
        self.cur = _CurBot()

    def cursor(self):
        return self.cur

    def commit(self):
        pass

    def rollback(self):
        pass


class TestBotUnaConexion(unittest.TestCase):
    def _confirmar(self, crear):
        import bot_driver
        import db_pool
        import transaction_service
        en_uso = {"max": 0, "ahora": 0}
        conns = []

        def tomar():
            en_uso["ahora"] += 1
            en_uso["max"] = max(en_uso["max"], en_uso["ahora"])
            conns.append(_ConnBot())
            return conns[-1]

        def soltar(_):
            en_uso["ahora"] -= 1

        def crear_con_su_conexion(tx_input, **k):
            tomar()
            try:
                return crear(tx_input, **k)
            finally:
                soltar(None)

        preparar = mock.Mock(return_value=("tx_input", None))
        with mock.patch.object(db_pool, "get_conn", tomar), mock.patch.object(db_pool, "put_conn", soltar), \
             mock.patch.object(bot_driver, "_preparar_confirmacion", preparar), \
             mock.patch.object(transaction_service, "create_transaction", crear_con_su_conexion):
            r = bot_driver.confirmar_draft(7, chat_link_id=1)
        self.assertEqual(en_uso["ahora"], 0, "ninguna conexión queda sin devolver")
        return r, en_uso["max"], conns

    def test_nunca_retiene_dos_y_usa_la_clave_del_borrador(self):
        capturado = {}

        def crear(tx_input, **k):
            capturado.update(k)
            return {"transaction_id": 42, "journal": "ok", "net_value": 100}

        r, maximo, conns = self._confirmar(crear)
        self.assertTrue(r.startswith("✅"), r)
        self.assertEqual(maximo, 1, "con dos por confirmación, varias a la vez agotan el pool")
        self.assertEqual(capturado, {"idempotency_key": "draft:7"})
        self.assertTrue(any("status = 'CONFIRMADO'" in s for c in conns for s in c.cur.sqls))

    def test_repetida_tambien_cierra_el_borrador(self):
        r, _, _ = self._confirmar(lambda t, **k: {"transaction_id": 42, "journal": "skipped_duplicate",
                                                  "net_value": 100, "repetida": True})
        self.assertTrue(r.startswith("✅"), r)

    def test_si_registrar_falla_el_borrador_queda_en_error(self):
        def crear(tx_input, **k):
            raise RuntimeError("BD caída")

        r, _, conns = self._confirmar(crear)
        self.assertIn("estado ERROR", r)
        self.assertTrue(any("status = 'ERROR'" in s for c in conns for s in c.cur.sqls))


def _hay_tabla():
    if not os.environ.get("DB_HOST"):
        return False
    from fin_sys_core.db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('idempotency_keys')")
        return cur.fetchone()[0] is not None
    finally:
        conn.rollback()
        put_conn(conn)


@unittest.skipUnless(_hay_tabla(), "requiere BD con migrate_h8.py")
class TestCarreraReal(unittest.TestCase):
    """Solo escribe claves `test-` y las borra al terminar."""

    def setUp(self):
        from fin_sys_core.db_pool import get_conn, put_conn
        self.get_conn, self.put_conn = get_conn, put_conn
        self.clave = f"test-h8-{uuid.uuid4().hex[:12]}"

    def tearDown(self):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM idempotency_keys WHERE clave = %s", (self.clave,))
            conn.commit()
        finally:
            self.put_conn(conn)

    def _envio(self, barrera, resultados):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            barrera.wait(timeout=10)
            try:
                idem.reservar(cur, self.clave, "h")
                idem.guardar(cur, self.clave, 777)
                conn.commit()
                resultados.append("ganó")
            except idem.TransaccionRepetida as e:
                conn.rollback()
                resultados.append(e.transaction_id)
        finally:
            self.put_conn(conn)

    def test_dos_a_la_vez_uno_gana_y_el_otro_recibe_su_transaccion(self):
        barrera, resultados = threading.Barrier(2), []
        hilos = [threading.Thread(target=self._envio, args=(barrera, resultados)) for _ in range(2)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertCountEqual(resultados, ["ganó", 777])

    def test_si_el_primero_hace_rollback_la_clave_se_va_con_el(self):
        conn = self.get_conn()
        try:
            cur = conn.cursor()
            self.assertTrue(idem.reservar(cur, self.clave, "h"))
            conn.rollback()
            self.assertTrue(idem.reservar(cur, self.clave, "h"), "el reintento sigue normal")
            conn.rollback()
        finally:
            self.put_conn(conn)


if __name__ == "__main__":
    unittest.main()
