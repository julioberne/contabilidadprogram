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

    def test_conexion_fugada_devuelve_el_cupo_via_gc(self):
        """Incidente prod 2026-09-06: un caller con fuga perdía la conexión de
        fallback; el GC la cerraba pero el CUPO del semáforo quedaba perdido
        para siempre → 'saturada' permanente. El finalize debe devolverlo."""
        import gc
        with mock.patch.object(db_pool.psycopg2, "connect", side_effect=lambda **k: FakeConn()):
            for _ in range(db_pool.DB_FALLBACK_MAX + 3):   # más fugas que cupos
                conn = db_pool.get_conn()
                del conn                     # FUGA deliberada: nadie hace put_conn
                gc.collect()
            # Si los cupos no volvieran, este get_conn agotaría el semáforo
            c = db_pool.get_conn()
            db_pool.put_conn(c)

    def test_connect_fallido_libera_el_cupo(self):
        with mock.patch.object(db_pool.psycopg2, "connect", side_effect=OSError("sin red")):
            for _ in range(db_pool.DB_FALLBACK_MAX + 2):   # más veces que cupos
                with self.assertRaises(OSError):
                    db_pool.get_conn()


class FakePoolConn:
    """Conexión 'del pool': igual que psycopg2 (sin __dict__), con socket
    simulable. `muerta=True` reproduce el corte SSL de Supabase."""
    __slots__ = ("__weakref__", "closed", "viva", "cerrada")

    def __init__(self, muerta=False):
        self.closed = 0
        self.viva = not muerta
        self.cerrada = False

    def poll(self):
        if not self.viva:
            raise RuntimeError("SSL connection has been closed unexpectedly")

    def rollback(self):
        if not self.viva:
            raise RuntimeError("SSL connection has been closed unexpectedly")

    def close(self):
        self.cerrada = True
        self.closed = 1


class FakePool:
    maxconn = 10

    def __init__(self, conns):
        self.conns = list(conns)
        self.descartadas = []   # putconn(close=True)
        self.devueltas = []     # putconn normal

    def getconn(self):
        if not self.conns:
            raise Exception("connection pool exhausted")
        return self.conns.pop(0)

    def putconn(self, conn, close=False):
        if close:
            conn.close()
            self.descartadas.append(conn)
        else:
            self.devueltas.append(conn)


class TestPoolSeCuraSolo(unittest.TestCase):
    """Incidente local 2026-09-07: un corte de red con Supabase dejó el pool
    lleno de conexiones muertas que circulaban para siempre (put→get de
    veneno); solo reiniciar el server lo 'curaba'. El pool debe sanearse solo:
    descartar muertas al prestar Y al devolver."""

    def setUp(self):
        self._pool_orig = db_pool._pool
        self._failed_orig = db_pool._init_failed

    def tearDown(self):
        db_pool._pool = self._pool_orig
        db_pool._init_failed = self._failed_orig

    def test_get_conn_descarta_muertas_y_entrega_una_viva(self):
        muertas = [FakePoolConn(muerta=True) for _ in range(3)]
        viva = FakePoolConn()
        db_pool._pool = FakePool(muertas + [viva])
        db_pool._init_failed = False

        conn = db_pool.get_conn()

        self.assertIs(conn, viva)
        self.assertEqual(db_pool._pool.descartadas, muertas)
        self.assertTrue(all(m.cerrada for m in muertas))
        self.assertEqual(db_pool._pool.devueltas, [])

    def test_put_conn_no_devuelve_veneno_al_pool(self):
        db_pool._pool = FakePool([])
        db_pool._init_failed = False

        rota = FakePoolConn(muerta=True)
        db_pool.put_conn(rota)
        self.assertIn(rota, db_pool._pool.descartadas)
        self.assertEqual(db_pool._pool.devueltas, [])

        sana = FakePoolConn()
        db_pool.put_conn(sana)
        self.assertIn(sana, db_pool._pool.devueltas)
        self.assertFalse(sana.cerrada)

    def test_conexion_ya_cerrada_no_vuelve_al_pool(self):
        db_pool._pool = FakePool([])
        db_pool._init_failed = False
        cerrada = FakePoolConn()
        cerrada.close()
        db_pool.put_conn(cerrada)
        self.assertIn(cerrada, db_pool._pool.descartadas)
        self.assertEqual(db_pool._pool.devueltas, [])


if __name__ == "__main__":
    unittest.main()
