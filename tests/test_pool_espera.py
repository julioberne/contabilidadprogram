# -*- coding: utf-8 -*-
"""Estándar de consultas, hito H2: el pool ESPERA su turno con tope (sin BD).

- Con el pool lleno, get_conn espera hasta `espera_s` y, si no hay turno,
  lanza PoolSaturado (nunca abre conexiones directas extra).
- Una ráfaga de muchos hilos contra un pool chico se atiende entera, en fila.
- La fila tiene tope (DB_POOL_MAX_ESPERA): lo que excede se rechaza al instante.
- El middleware convierte el 500 del endpoint en 503 + Retry-After.

    python -m unittest tests.test_pool_espera
"""
import os
import sys
import threading
import time
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fin_sys_core import db_pool  # noqa: E402


class Conn:
    def __init__(self):
        self.closed = 0
        self.cursor_factory = None

    def poll(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = 1


class PoolChico:
    """Como ThreadedConnectionPool: getconn/putconn con `maxconn` conexiones."""

    def __init__(self, n):
        self.maxconn = n
        self.libres = [Conn() for _ in range(n)]
        self.lock = threading.Lock()

    def getconn(self):
        with self.lock:
            if not self.libres:
                raise Exception("connection pool exhausted")
            return self.libres.pop()

    def putconn(self, conn, close=False):
        with self.lock:
            if not close:
                self.libres.append(conn)


class TestPoolQueEspera(unittest.TestCase):
    N = 3

    def setUp(self):
        self.orig = (db_pool._pool, db_pool._init_failed, db_pool._turnos, dict(db_pool._metricas))
        db_pool._pool = PoolChico(self.N)
        db_pool._init_failed = False
        db_pool._turnos = threading.BoundedSemaphore(self.N)
        db_pool._metricas.update(prestamos=0, esperas=0, rechazos=0, esperando=0)
        db_pool._esperas_ms.clear()
        self.directa = mock.patch.object(db_pool.psycopg2, "connect",
                                         side_effect=AssertionError("no debía abrir conexión directa"))
        self.directa.start()

    def tearDown(self):
        self.directa.stop()
        db_pool._pool, db_pool._init_failed, db_pool._turnos, m = self.orig
        db_pool._metricas.clear()
        db_pool._metricas.update(m)

    def test_lleno_espera_y_rechaza_con_pool_saturado(self):
        conns = [db_pool.get_conn() for _ in range(self.N)]
        t0 = time.perf_counter()
        with self.assertRaises(db_pool.PoolSaturado):
            db_pool.get_conn(espera_s=0.2)
        self.assertGreaterEqual(time.perf_counter() - t0, 0.18, "debe esperar su turno antes de rendirse")
        self.assertEqual(db_pool.metricas_espera()["rechazos"], 1)
        for c in conns:
            db_pool.put_conn(c)
        self.assertEqual(db_pool.metricas_espera()["turnos_libres"], self.N)

    def test_al_liberarse_una_la_espera_la_recibe(self):
        conns = [db_pool.get_conn() for _ in range(self.N)]
        threading.Timer(0.15, db_pool.put_conn, args=(conns[0],)).start()
        c = db_pool.get_conn(espera_s=2.0)
        self.assertIs(c, conns[0])
        for x in [c] + conns[1:]:
            db_pool.put_conn(x)

    def test_rafaga_se_atiende_en_fila_sin_errores(self):
        errores, ok = [], []

        def trabajo():
            try:
                c = db_pool.get_conn(espera_s=5.0)
                time.sleep(0.03)
                db_pool.put_conn(c)
                ok.append(1)
            except Exception as e:
                errores.append(e)

        with mock.patch.object(db_pool, "DB_POOL_MAX_ESPERA", 100):
            hilos = [threading.Thread(target=trabajo) for _ in range(30)]
            [h.start() for h in hilos]
            [h.join() for h in hilos]
        self.assertEqual(errores, [])
        self.assertEqual(len(ok), 30)
        m = db_pool.metricas_espera()
        self.assertEqual(m["turnos_libres"], self.N)
        self.assertGreater(m["esperas"], 0)

    def test_fila_con_tope_rechaza_al_instante(self):
        conns = [db_pool.get_conn() for _ in range(self.N)]
        with mock.patch.object(db_pool, "DB_POOL_MAX_ESPERA", 0):
            t0 = time.perf_counter()
            with self.assertRaises(db_pool.PoolSaturado):
                db_pool.get_conn(espera_s=5.0)
            self.assertLess(time.perf_counter() - t0, 0.1)
        for c in conns:
            db_pool.put_conn(c)

    def test_marca_de_saturacion(self):
        conns = [db_pool.get_conn() for _ in range(self.N)]
        marca = {"saturado": False}
        token = db_pool.saturacion_ctx.set(marca)
        try:
            with self.assertRaises(db_pool.PoolSaturado):
                db_pool.get_conn(espera_s=0.05)
        finally:
            db_pool.saturacion_ctx.reset(token)
        self.assertTrue(marca["saturado"])
        for c in conns:
            db_pool.put_conn(c)

    def test_conexion_muerta_no_consume_turno(self):
        muerta = Conn()
        muerta.closed = 1
        db_pool._pool.libres = [muerta] + db_pool._pool.libres[:-1]
        c = db_pool.get_conn()
        self.assertFalse(c.closed)
        db_pool.put_conn(c)
        self.assertEqual(db_pool.metricas_espera()["turnos_libres"], self.N)


class TestMiddleware503(unittest.TestCase):
    def test_endpoint_que_envuelve_en_500_sale_como_503(self):
        from fastapi import FastAPI, HTTPException
        from fastapi.testclient import TestClient
        from shared.admision import install_saturation_middleware

        app = FastAPI()
        install_saturation_middleware(app)

        @app.get("/api/lista")
        def lista():                       # ruta síncrona: corre en el threadpool
            try:
                raise_saturado()
            except Exception as e:         # como casi todos los routers
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/api/traga_error")
        def traga():                       # como obtener_portafolios: error → [] con 200
            try:
                raise_saturado()
            except Exception:
                return []

        @app.get("/api/otro_error")
        def otro():
            raise HTTPException(status_code=500, detail="otro")

        def raise_saturado():
            db_pool._marcar_saturacion()
            raise db_pool.PoolSaturado("ocupada")

        c = TestClient(app)
        r = c.get("/api/lista")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.headers.get("Retry-After"), "2")
        self.assertEqual(c.get("/api/traga_error").status_code, 503,
                         "un 200 con datos vacíos por saturación también es 503")
        self.assertEqual(c.get("/api/otro_error").status_code, 500, "un 500 cualquiera no se toca")


if __name__ == "__main__":
    unittest.main()
