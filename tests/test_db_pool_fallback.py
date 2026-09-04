# -*- coding: utf-8 -*-
"""Tests del fallback con tope de db_pool (sin BD real).

Regresión del incidente 2026-09-04: marcar la conexión de fallback con un
atributo (`conn._finsys_fallback = True`) explotaba con AttributeError porque
las conexiones de psycopg2 son objetos C sin __dict__ — igual que este Fake
con __slots__. El registro debe ser externo (WeakSet).
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fin_sys_core"))

import db_pool  # noqa: E402


class FakeConn:
    """Como psycopg2: SIN __dict__ — cualquier setattr lanza AttributeError."""
    __slots__ = ("__weakref__", "cerrada")

    def __init__(self):
        self.cerrada = False

    def close(self):
        self.cerrada = True

    def rollback(self):
        pass


class TestFallbackConTope(unittest.TestCase):
    def setUp(self):
        # Estado limpio: sin pool y con el latch de init marcado como fallido
        # para que get_conn vaya DIRECTO al fallback.
        self._pool_orig = db_pool._pool
        self._failed_orig = db_pool._init_failed
        db_pool._pool = None
        db_pool._init_failed = True

    def tearDown(self):
        db_pool._pool = self._pool_orig
        db_pool._init_failed = self._failed_orig

    def test_fallback_no_setea_atributos_en_la_conexion(self):
        with mock.patch.object(db_pool.psycopg2, "connect", return_value=FakeConn()):
            conn = db_pool.get_conn()          # AttributeError aquí = regresión
        self.assertIn(conn, db_pool._fallback_conns)
        db_pool.put_conn(conn)
        self.assertTrue(conn.cerrada)
        self.assertNotIn(conn, db_pool._fallback_conns)

    def test_put_conn_devuelve_el_cupo_del_semaforo(self):
        with mock.patch.object(db_pool.psycopg2, "connect", side_effect=lambda **k: FakeConn()):
            # Consumir TODOS los cupos y devolverlos N veces: si put_conn no
            # liberara el semáforo, la segunda ronda se quedaría sin cupos.
            for _ in range(2):
                conns = [db_pool.get_conn() for _ in range(db_pool.DB_FALLBACK_MAX)]
                for c in conns:
                    db_pool.put_conn(c)

    def test_tope_alcanzado_falla_rapido_y_claro(self):
        with mock.patch.object(db_pool.psycopg2, "connect", side_effect=lambda **k: FakeConn()):
            conns = [db_pool.get_conn() for _ in range(db_pool.DB_FALLBACK_MAX)]
            with mock.patch.object(db_pool._fallback_sem, "acquire", return_value=False):
                with self.assertRaises(ConnectionError):
                    db_pool.get_conn()
            for c in conns:
                db_pool.put_conn(c)

    def test_connect_fallido_libera_el_cupo(self):
        with mock.patch.object(db_pool.psycopg2, "connect", side_effect=OSError("sin red")):
            for _ in range(db_pool.DB_FALLBACK_MAX + 2):   # más veces que cupos
                with self.assertRaises(OSError):
                    db_pool.get_conn()


if __name__ == "__main__":
    unittest.main()
