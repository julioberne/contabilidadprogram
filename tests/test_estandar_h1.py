# -*- coding: utf-8 -*-
"""Estándar de consultas, hito H1 (16-oct-2026). Sin BD: corren en el CI.

- shared/admision.py: clasificación, token bucket, tope de pesadas, modos
  registrar / activo / apagado y falla abierta.
- routers/salud.py: /api/health/vida responde sin BD; la sonda usa caché.
- Sesión obligatoria en los GET que estaban abiertos (401 sin token) y
  /api/module-flags sigue público (lo pide main.jsx antes del login).

    python -m unittest tests.test_estandar_h1
"""
import os
import sys
import time
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from shared import admision as adm  # noqa: E402


def _app_con_admision(estado):
    app = FastAPI()
    adm.install_admission_middleware(app, estado)

    @app.get("/api/lista")
    def lista():
        return {"ok": True}

    @app.get("/api/analytics/dataset")
    def pesada():
        time.sleep(0.2)
        return {"ok": True}

    @app.post("/api/transactions")
    def alta():
        return {"ok": True}

    @app.get("/api/health")
    def salud():
        return {"ok": True}

    return app


class TestClasificacion(unittest.TestCase):
    def test_clases(self):
        self.assertEqual(adm.clasificar("GET", "/api/health/vida"), adm.CRITICA)
        self.assertEqual(adm.clasificar("POST", "/api/transactions"), adm.CRITICA)
        self.assertEqual(adm.clasificar("GET", "/api/analytics/dataset"), adm.INFORME)
        self.assertEqual(adm.clasificar("GET", "/api/contadores/reportes/libro-mayor"), adm.INFORME)
        self.assertEqual(adm.clasificar("GET", "/api/diario/movimientos", "agrupar=tercero"), adm.INFORME)
        self.assertEqual(adm.clasificar("GET", "/api/diario/movimientos", "q=cafe"), adm.INTERACTIVA)

    def test_cubeta(self):
        c = adm._Cubeta(3)
        self.assertEqual([c.tomar(0.0001, 3) for _ in range(4)], [True, True, True, False])


class TestMiddleware(unittest.TestCase):
    def setUp(self):
        self.estado = adm.Admision()
        self.client = TestClient(_app_con_admision(self.estado))

    def _rafaga(self, n, ruta="/api/lista", token="Bearer A"):
        return [self.client.get(ruta, headers={"Authorization": token}).status_code for _ in range(n)]

    def test_registrar_nunca_bloquea_pero_cuenta(self):
        with mock.patch.dict(os.environ, {"FINSYS_ADMISION": "registrar"}):
            codigos = self._rafaga(int(adm.LECTURA_RAFAGA) + 5)
        self.assertTrue(all(c == 200 for c in codigos))
        self.assertGreaterEqual(self.estado.contadores["habria_rechazado"], 1)

    def test_activo_responde_429_con_retry_after(self):
        with mock.patch.dict(os.environ, {"FINSYS_ADMISION": "activo"}):
            codigos = self._rafaga(int(adm.LECTURA_RAFAGA) + 5)
            self.assertIn(429, codigos)
            r = self.client.get("/api/lista", headers={"Authorization": "Bearer A"})
            self.assertEqual(r.status_code, 429)
            self.assertEqual(r.headers.get("Retry-After"), str(adm.RETRY_AFTER_S))
            # otro usuario no se ve afectado (cuota por usuario)
            self.assertEqual(self._rafaga(1, token="Bearer B"), [200])

    def test_activo_nunca_rechaza_escrituras_ni_health(self):
        with mock.patch.dict(os.environ, {"FINSYS_ADMISION": "activo"}):
            self._rafaga(int(adm.LECTURA_RAFAGA) + 5)
            for _ in range(5):
                self.assertEqual(self.client.post("/api/transactions", headers={"Authorization": "Bearer A"}).status_code, 200)
                self.assertEqual(self.client.get("/api/health", headers={"Authorization": "Bearer A"}).status_code, 200)

    def test_tope_de_pesadas_por_usuario(self):
        import threading
        with mock.patch.dict(os.environ, {"FINSYS_ADMISION": "activo"}):
            codigos = []
            hilos = [threading.Thread(target=lambda: codigos.append(
                self.client.get("/api/analytics/dataset", headers={"Authorization": "Bearer A"}).status_code))
                for _ in range(adm.INFORME_SIMULTANEOS_USUARIO + 2)]
            [h.start() for h in hilos]
            [h.join() for h in hilos]
        self.assertIn(429, codigos)
        self.assertGreaterEqual(codigos.count(200), adm.INFORME_SIMULTANEOS_USUARIO)
        self.assertEqual(self.estado._informes_worker, 0, "los cupos se liberan al terminar")

    def test_apagado_no_cuenta(self):
        with mock.patch.dict(os.environ, {"FINSYS_ADMISION": "apagado"}):
            self._rafaga(int(adm.LECTURA_RAFAGA) + 5)
        self.assertEqual(self.estado.contadores["admitidas"], 0)

    def test_falla_abierto(self):
        with mock.patch.dict(os.environ, {"FINSYS_ADMISION": "activo"}), \
                mock.patch.object(self.estado, "entrar", side_effect=RuntimeError("roto")):
            self.assertEqual(self._rafaga(3), [200, 200, 200])


class TestSalud(unittest.TestCase):
    def setUp(self):
        from routers import salud
        self.salud = salud
        salud._cache.update(t=0.0, db=None)
        app = FastAPI()
        app.include_router(salud.router)
        self.client = TestClient(app)

    def test_vida_no_toca_la_bd(self):
        with mock.patch.object(self.salud, "_sonda", side_effect=AssertionError("no debía sondear")):
            r = self.client.get("/api/health/vida")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})

    def test_sonda_con_cache(self):
        llamadas = []
        with mock.patch.object(self.salud, "_sonda", side_effect=lambda: llamadas.append(1) or "connected"):
            estados = [self.salud.sonda_bd() for _ in range(5)]
        self.assertEqual(estados, ["connected"] * 5)
        self.assertEqual(len(llamadas), 1, "una sola sonda dentro del TTL")

    def test_profundo(self):
        with mock.patch.object(self.salud, "_sonda", return_value="connected"):
            d = self.client.get("/api/health/profundo").json()
        self.assertEqual(d["db"], "connected")
        self.assertIn("admision", d)
        self.assertIn(d["admision"]["modo"], ("registrar", "activo", "apagado"))


class TestSesionObligatoria(unittest.TestCase):
    """GET que antes respondían sin sesión → 401 sin token."""

    @classmethod
    def setUpClass(cls):
        from routers.hr import router as hr
        from routers.hub import router as hub
        from routers.inventory import router as inv
        from routers.tags_taxes import router as tags
        from routers.portfolios import router as pfs
        from routers.module_flags import router as flags
        app = FastAPI()
        for r in (hr, hub, inv, tags, pfs, flags):
            app.include_router(r)
        cls.client = TestClient(app)

    def test_401_sin_token(self):
        rutas = [
            "/api/hr/profile/u1", "/api/hr/salary/u1", "/api/hr/payments/u1",
            "/api/hr/companies/u1", "/api/hr/folders/w1", "/api/hr/documents/u1",
            "/api/hr/categories/w1",
            "/api/hub/workspaces", "/api/hub/users?workspace_id=w", "/api/hub/entities?workspace_id=w",
            "/api/hub/projects?workspace_id=w", "/api/hub/tasks?project_id=p",
            "/api/hub/tasks/overview?workspace_id=w", "/api/hub/notes?workspace_id=w&user_id=u",
            "/api/hub/events?workspace_id=w", "/api/hub/metrics?workspace_id=w",
            "/api/hub/users/u1/tasks?workspace_id=w",
            "/api/inventory/movements", "/api/tags", "/api/custom-taxes", "/api/portfolios",
            "/api/module-flags/admin",
        ]
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                self.assertIn(self.client.get(ruta).status_code, (401, 403))

    def test_module_flags_sigue_publico(self):
        # Lo pide main.jsx antes del login. Puede fallar por BD en el CI, pero
        # nunca con 401/403.
        try:
            codigo = self.client.get("/api/module-flags").status_code
        except Exception:
            return   # sin BD el handler puede lanzar: lo importante es que no exige sesión
        self.assertNotIn(codigo, (401, 403))


class TestLaboratorioSoloLocal(unittest.TestCase):
    """El laboratorio de carga jamás corre contra Supabase (BD de producción)."""

    def test_guarda(self):
        sys.path.insert(0, os.path.join(_ROOT, "scripts", "carga"))
        from _seguro import exigir_local
        exigir_local("localhost", 56432)
        exigir_local("127.0.0.1", "55432")
        for host, puerto in [("aws-1-us-east-2.pooler.supabase.com", 6543),
                             ("db.abc.supabase.co", 5432), ("10.0.0.5", 56432),
                             ("localhost", 6543), ("localhost", 5432)]:
            with self.subTest(host=host, puerto=puerto), self.assertRaises(SystemExit):
                exigir_local(host, puerto)


if __name__ == "__main__":
    unittest.main()
