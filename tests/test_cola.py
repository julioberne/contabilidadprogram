# -*- coding: utf-8 -*-
"""Cola de trabajos pgmq + estado en `operaciones` (estándar H5, 19-oct-2026).

- Puros (CI sin BD): clave, esperas, seguridad de colas, el worker con la cola
  simulada, POST /api/analytics/export con y sin la bandera, /api/operaciones.
- Contra la BD (solo con pgmq y la tabla instaladas; si no, se saltan): ciclo
  completo en la cola `trabajos_prueba`, que limpia sus filas.

    python -m unittest tests.test_cola
"""
import os
import sys
import unittest
import uuid
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import tests  # noqa: F401,E402  (carga .env)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from fin_sys_core import cola  # noqa: E402
from fin_sys_core import worker  # noqa: E402
from fin_sys_core import worker_jobs  # noqa: F401,E402  (registra los manejadores)


class TestPuros(unittest.TestCase):
    def test_clave_determinista(self):
        a = cola.clave_de("x", "u1", {"b": 2, "a": 1})
        self.assertEqual(a, cola.clave_de("x", "u1", {"a": 1, "b": 2}), "el orden de las claves no importa")
        self.assertNotEqual(a, cola.clave_de("x", "u2", {"a": 1, "b": 2}))
        self.assertNotEqual(a, cola.clave_de("x", "u1", {"a": 1, "b": 3}))
        self.assertTrue(a.startswith("x:u1:"))

    def test_espera_creciente_con_tope(self):
        self.assertEqual([cola.espera_reintento(i) for i in (1, 2, 3)], [10, 20, 40])
        self.assertEqual(cola.espera_reintento(20), cola.ESPERA_MAX_S)

    def test_cola_por_defecto_es_la_de_prueba(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FINSYS_COLA", None)
            self.assertEqual(cola.cola_por_defecto(), cola.COLA_PRUEBA)
        with mock.patch.dict(os.environ, {"FINSYS_COLA": "trabajos"}):
            self.assertEqual(cola.cola_por_defecto(), "trabajos")

    def test_worker_local_no_toca_produccion(self):
        with mock.patch.dict(os.environ, {"FINSYS_WORKER_PRODUCCION": ""}):
            with self.assertRaises(SystemExit):
                worker.cola_permitida("trabajos")
            worker.cola_permitida("trabajos_prueba")
            worker.cola_permitida("otra_prueba")
        with mock.patch.dict(os.environ, {"FINSYS_WORKER_PRODUCCION": "1"}):
            worker.cola_permitida("trabajos")

    def test_no_disponible_reconoce_la_migracion_faltante(self):
        self.assertTrue(cola._no_disponible(Exception('relation "operaciones" does not exist')))
        self.assertTrue(cola._no_disponible(Exception('schema "pgmq" does not exist')))
        self.assertFalse(cola._no_disponible(Exception("timeout")))


def _trabajo(tipo="prueba_eco", datos=None, intentos=1, max_intentos=3):
    return {"op": {"id": 9, "tipo": tipo, "cola": cola.COLA_PRUEBA, "datos": datos or {}, "usuario": "u1",
                   "empresa": None, "intentos": intentos, "max_intentos": max_intentos},
            "msg_id": 77, "cola": cola.COLA_PRUEBA}


class TestWorkerConColaSimulada(unittest.TestCase):
    def _procesar(self, trabajo):
        with mock.patch.object(worker.cola_mod, "tomar", return_value=trabajo), \
             mock.patch.object(worker.cola_mod, "terminar") as terminar, \
             mock.patch.object(worker.cola_mod, "fallar", return_value="reintento") as fallar, \
             mock.patch.object(worker.cola_mod, "extender"):
            hubo = worker.procesar_uno(cola.COLA_PRUEBA, vt=30)
        return hubo, terminar, fallar

    def test_sin_trabajo(self):
        hubo, terminar, fallar = self._procesar(None)
        self.assertFalse(hubo)
        terminar.assert_not_called()

    def test_hecho_guarda_el_resultado(self):
        hubo, terminar, fallar = self._procesar(_trabajo(datos={"eco": "hola"}))
        self.assertTrue(hubo)
        terminar.assert_called_once()
        self.assertEqual(terminar.call_args[0][1], {"eco": "hola", "intento": 1})
        fallar.assert_not_called()

    def test_falla_pasajera_se_reintenta(self):
        _, terminar, fallar = self._procesar(_trabajo(datos={"fallar": "transitorio"}))
        terminar.assert_not_called()
        trabajo, motivo = fallar.call_args[0]
        self.assertEqual(trabajo["op"]["intentos"], 1, "con intentos de sobra: reintento")
        self.assertIn("falla pasajera", motivo)

    def test_error_definitivo_no_se_reintenta(self):
        _, _, fallar = self._procesar(_trabajo(datos={"fallar": "definitivo"}))
        trabajo, motivo = fallar.call_args[0]
        self.assertEqual(trabajo["op"]["intentos"], trabajo["op"]["max_intentos"])
        self.assertEqual(motivo, "pedido inválido (prueba)")

    def test_tipo_desconocido_queda_fallido(self):
        _, _, fallar = self._procesar(_trabajo(tipo="nada"))
        trabajo, motivo = fallar.call_args[0]
        self.assertEqual(trabajo["op"]["intentos"], trabajo["op"]["max_intentos"])
        self.assertIn("desconocido", motivo)

    def test_operacion_ya_terminada_se_salta(self):
        hubo, terminar, fallar = self._procesar({"op": None, "msg_id": 1, "cola": cola.COLA_PRUEBA})
        self.assertTrue(hubo)
        terminar.assert_not_called()
        fallar.assert_not_called()


USUARIO = {"uid": "u1", "name": "Andrés", "role": "admin", "su": False}


def _app_exportacion():
    from routers import accounting_files as rt
    from routers.auth_guard import require_contador
    app = FastAPI()
    app.include_router(rt.router)
    app.dependency_overrides[require_contador] = lambda: USUARIO
    return app


class TestExportacionEnCola(unittest.TestCase):
    CUERPO = {"receta": {"x": 1}, "paquete": "p1", "folder_id": 4}

    def test_con_bandera_responde_202_y_encola(self):
        with mock.patch.dict(os.environ, {"FINSYS_EXPORT_EN_COLA": "1"}), \
             mock.patch("fin_sys_core.cola.encolar", return_value={"id": 5, "nueva": True, "cola": "trabajos_prueba"}) as enc:
            r = TestClient(_app_exportacion()).post("/api/analytics/export", json=self.CUERPO)
        self.assertEqual(r.status_code, 202)
        self.assertEqual(r.json(), {"operacion": 5, "estado": "PENDIENTE", "en_cola": True, "nueva": True})
        tipo, datos = enc.call_args[0]
        self.assertEqual(tipo, "exportacion_xlsx")
        self.assertEqual((datos["receta"], datos["paquete"], datos["folder_id"]), ({"x": 1}, "p1", 4))
        self.assertEqual(datos["usuario"], USUARIO)
        self.assertEqual(enc.call_args[1]["usuario"], "u1")

    def test_sin_bandera_o_sin_cola_sigue_sincrona(self):
        import accounting_files_driver as drv
        listo = {"id": 1, "nombre_archivo": "a.xlsx"}
        with mock.patch.dict(os.environ, {"FINSYS_EXPORT_EN_COLA": "0"}), \
             mock.patch.object(drv, "generar", return_value=listo) as gen:
            r = TestClient(_app_exportacion()).post("/api/analytics/export", json=self.CUERPO)
        self.assertEqual((r.status_code, r.json()), (200, listo))
        gen.assert_called_once()
        with mock.patch.dict(os.environ, {"FINSYS_EXPORT_EN_COLA": "1"}), \
             mock.patch("fin_sys_core.cola.encolar", side_effect=cola.ColaNoDisponible("falta")), \
             mock.patch.object(drv, "generar", return_value=listo):
            r = TestClient(_app_exportacion()).post("/api/analytics/export", json=self.CUERPO)
        self.assertEqual((r.status_code, r.json()), (200, listo), "sin migración: síncrona, sin error")


class TestUnaSolaVariable(unittest.TestCase):
    def test_lista_y_sinonimo(self):
        with mock.patch.dict(os.environ, {"FINSYS_EN_COLA": " exportacion , entrega ", "FINSYS_EXPORT_EN_COLA": "0"}):
            self.assertTrue(cola.en_cola("entrega"))
            self.assertTrue(cola.en_cola("exportacion"))
            self.assertFalse(cola.en_cola("diario_csv"))
        with mock.patch.dict(os.environ, {"FINSYS_EN_COLA": "", "FINSYS_EXPORT_EN_COLA": "1"}):
            self.assertTrue(cola.en_cola("exportacion"), "la bandera vieja sigue valiendo")
            self.assertFalse(cola.en_cola("entrega"))
        with mock.patch.dict(os.environ, {"FINSYS_EN_COLA": "", "FINSYS_EXPORT_EN_COLA": ""}):
            self.assertFalse(cola.en_cola("exportacion"))


class TestEntregaEnCola(unittest.TestCase):
    CUERPO = {"ids": [3, 4], "nombre": "Para el contador", "folder_id": None}

    def test_en_la_cola_202(self):
        with mock.patch.dict(os.environ, {"FINSYS_EN_COLA": "entrega"}), \
             mock.patch("fin_sys_core.cola.encolar", return_value={"id": 8, "nueva": True, "cola": "trabajos_prueba"}) as enc:
            r = TestClient(_app_exportacion()).post("/api/accounting-files/entrega", json=self.CUERPO)
        self.assertEqual((r.status_code, r.json()["operacion"]), (202, 8))
        tipo, datos = enc.call_args[0]
        self.assertEqual((tipo, datos["ids"], datos["usuario"]["uid"]), ("entrega_zip", [3, 4], "u1"))

    def test_sin_la_variable_sigue_sincrona(self):
        import entrega_driver
        listo = {"id": 2, "folio": "F-1", "n": 2, "nombre_archivo": "e.zip"}
        with mock.patch.dict(os.environ, {"FINSYS_EN_COLA": "", "FINSYS_EXPORT_EN_COLA": ""}), \
             mock.patch.object(entrega_driver, "crear", return_value=listo):
            r = TestClient(_app_exportacion()).post("/api/accounting-files/entrega", json=self.CUERPO)
        self.assertEqual((r.status_code, r.json()), (201, listo))

    def test_manejador_mapea_errores_del_pedido(self):
        import entrega_driver
        from fin_sys_core.worker import MANEJADORES, ErrorDefinitivo
        with mock.patch.object(entrega_driver, "crear", side_effect=ValueError("ZIP muy grande")):
            with self.assertRaises(ErrorDefinitivo):
                MANEJADORES["entrega_zip"]({"ids": [1]}, {})


class TestRutaOperaciones(unittest.TestCase):
    OP = {"id": 5, "tipo": "exportacion_xlsx", "estado": "HECHA", "resultado": {"id": 1}, "error": None,
          "intentos": 1, "max_intentos": 3, "usuario": "u1", "empresa": None,
          "creada": None, "iniciada": None, "terminada": None}

    def _get(self, user, op=None, error=None):
        from routers import operaciones as rt
        from routers.auth_guard import require_auth
        app = FastAPI()
        app.include_router(rt.router)
        app.dependency_overrides[require_auth] = lambda: user
        with mock.patch("fin_sys_core.cola.estado", return_value=op, side_effect=error):
            return TestClient(app).get("/api/operaciones/5")

    def test_el_duenno_ve_el_resultado(self):
        r = self._get({"uid": "u1", "role": "member"}, self.OP)
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json()["estado"], r.json()["resultado"], r.json()["terminada"]),
                         ("HECHA", {"id": 1}, True))

    def test_otro_usuario_no_la_ve_y_el_admin_si(self):
        self.assertEqual(self._get({"uid": "u2", "role": "member"}, self.OP).status_code, 404)
        self.assertEqual(self._get({"uid": "u2", "role": "admin"}, self.OP).status_code, 200)
        self.assertEqual(self._get({"uid": "u1"}, None).status_code, 404)

    def test_sin_migracion_503(self):
        self.assertEqual(self._get({"uid": "u1"}, error=cola.ColaNoDisponible("falta")).status_code, 503)


def _cola_instalada() -> bool:
    if not os.environ.get("DB_HOST"):
        return False
    try:
        from fin_sys_core.db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT to_regclass('public.operaciones') IS NOT NULL AND "
                        "EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgmq')")
            return bool(cur.fetchone()[0])
        finally:
            put_conn(conn)
    except Exception:
        return False


@unittest.skipUnless(_cola_instalada(), "requiere BD con pgmq y la tabla operaciones (migrate_operaciones.py)")
class TestContraBD(unittest.TestCase):
    """Escribe SOLO en la cola trabajos_prueba y en filas con clave 'test-…', y las borra."""

    def setUp(self):
        self.prefijo = f"test-{uuid.uuid4().hex[:8]}"

    def tearDown(self):
        from fin_sys_core.db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT msg_id FROM operaciones WHERE clave LIKE %s AND msg_id IS NOT NULL",
                        (self.prefijo + "%",))
            for (msg_id,) in cur.fetchall():
                cur.execute("SELECT pgmq.delete(%s::text, %s::bigint)", (cola.COLA_PRUEBA, msg_id))
            cur.execute("DELETE FROM operaciones WHERE clave LIKE %s AND cola = %s",
                        (self.prefijo + "%", cola.COLA_PRUEBA))
            conn.commit()
        finally:
            put_conn(conn)

    def _vaciar_lo_ajeno(self):
        """Procesa hasta encontrar lo propio (otros tests pudieron dejar mensajes)."""
        for _ in range(20):
            if not worker.procesar_uno(cola.COLA_PRUEBA, vt=30):
                return

    def test_ciclo_completo_e_idempotencia(self):
        clave = f"{self.prefijo}:eco"
        a = cola.encolar("prueba_eco", {"eco": "hola"}, usuario="u-test", clave=clave, cola=cola.COLA_PRUEBA)
        b = cola.encolar("prueba_eco", {"eco": "hola"}, usuario="u-test", clave=clave, cola=cola.COLA_PRUEBA)
        self.assertTrue(a["nueva"])
        self.assertEqual((b["id"], b["nueva"]), (a["id"], False), "doble clic: el mismo trabajo")
        self.assertEqual(cola.estado(a["id"])["estado"], "PENDIENTE")
        self._vaciar_lo_ajeno()
        fin = cola.estado(a["id"])
        self.assertEqual((fin["estado"], fin["resultado"]), ("HECHA", {"eco": "hola", "intento": 1}))
        m = cola.metricas(cola.COLA_PRUEBA)
        self.assertTrue(m["activa"])

    def test_definitivo_queda_fallido_sin_reintentos(self):
        a = cola.encolar("prueba_eco", {"fallar": "definitivo"}, usuario="u-test",
                         clave=f"{self.prefijo}:def", cola=cola.COLA_PRUEBA)
        self._vaciar_lo_ajeno()
        fin = cola.estado(a["id"])
        self.assertEqual((fin["estado"], fin["error"], fin["intentos"]), ("FALLIDA", "pedido inválido (prueba)", 1))

    def test_pasajero_vuelve_a_pendiente_con_espera(self):
        a = cola.encolar("prueba_eco", {"fallar": "transitorio"}, usuario="u-test",
                         clave=f"{self.prefijo}:tra", cola=cola.COLA_PRUEBA)
        self._vaciar_lo_ajeno()
        fin = cola.estado(a["id"])
        self.assertEqual(fin["estado"], "PENDIENTE", "con intentos de sobra vuelve a la cola")
        self.assertIn("falla pasajera", fin["error"])
        self.assertEqual(fin["intentos"], 1)


if __name__ == "__main__":
    unittest.main()
