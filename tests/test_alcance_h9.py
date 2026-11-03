# -*- coding: utf-8 -*-
"""Alcance por empresa (estándar H9.1, 3-nov-2026).

- Puros (CI sin BD): el dueño pasa sin consultas; para los demás, empresa ajena
  o sin empresa → 403, ruta no clasificada → 403, registro de otra empresa →
  403; query, body JSON y formulario.
- Trinquete sobre las rutas reales de server.app: la clase de cada ruta cuadra
  con sus parámetros (una GLOBAL no puede recibir empresa; una EMPRESA debe).
- Contra la BD (se saltan sin DB_HOST): las consultas de los resolvedores y de
  la membresía corren contra las tablas reales (solo lectura).

    python -m unittest tests.test_alcance_h9
"""
import os
import sys
import unittest
import uuid
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import tests  # noqa: F401,E402

from fastapi import Body, Depends, FastAPI, Form  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from routers.auth_guard import create_session_token  # noqa: E402
from shared import alcance  # noqa: E402

CONTADOR = str(uuid.uuid4())
NOMBRES = {1: "Negocio A", 2: "Otra Empresa"}


def _cabecera(role, uid=CONTADOR, su=False):
    return {"Authorization": "Bearer " + create_session_token({"id": uid, "name": "P", "role": role,
                                                               "is_superuser": su})}


def _app():
    app = FastAPI(dependencies=[Depends(alcance.verificar)])

    @app.get("/api/dashboard-data")
    def dash(portfolio: str = None):
        return {"ok": True}

    @app.get("/api/diario/movimientos")
    def mov(empresas: str = None, portfolio: str = None):
        return {"ok": True}

    @app.post("/api/transactions")
    def crear(body: dict = Body(...)):
        return {"ok": True}

    @app.put("/api/transactions/{tx_id}")
    def editar(tx_id: int, body: dict = Body(None)):
        return {"ok": True}

    @app.post("/api/accounting-files/upload")
    def subir(portfolio_id: int = Form(None)):
        return {"ok": True}

    @app.get("/api/bot/drafts/{draft_id}")
    def borrador(draft_id: int):
        return {"ok": True}

    @app.get("/api/tags")
    def tags():
        return {"ok": True}

    @app.get("/api/org/consolidated")       # no clasificada: solo el dueño
    def consolidado():
        return {"ok": True}

    return app


class _Base(unittest.TestCase):
    def setUp(self):
        alcance.limpiar_cache()
        self.c = TestClient(_app())
        self.bd = mock.patch.object(alcance, "_empresas_de_bd", return_value=frozenset({1}))
        self.nom = mock.patch.object(alcance, "portafolios", return_value=NOMBRES)
        self.empresas_de_bd = self.bd.start()
        self.nom.start()
        self.addCleanup(self.bd.stop)
        self.addCleanup(self.nom.stop)
        self.addCleanup(alcance.limpiar_cache)


class TestDueno(_Base):
    def test_el_dueno_pasa_todo_sin_consultar(self):
        self.empresas_de_bd.side_effect = AssertionError("el dueño no consulta la BD")
        for h in (_cabecera("owner"), _cabecera("member", su=True)):
            self.assertEqual(self.c.get("/api/org/consolidated", headers=h).status_code, 200)
            self.assertEqual(self.c.get("/api/dashboard-data?portfolio=Otra Empresa", headers=h).status_code, 200)
            self.assertEqual(self.c.get("/api/dashboard-data", headers=h).status_code, 200)

    def test_sin_token_no_hace_nada(self):
        # La ruta responde 401 con su propio require_auth; aquí no tiene, así que 200.
        self.assertEqual(self.c.get("/api/org/consolidated").status_code, 200)
        self.assertEqual(self.c.get("/api/org/consolidated", headers={"Authorization": "Bearer basura"}).status_code, 200)


class TestEmpresa(_Base):
    def test_su_empresa_por_nombre_id_o_mayusculas(self):
        h = _cabecera("contador")
        for q in ("portfolio=Negocio A", "portfolio=1", "portfolio=negocio a"):
            self.assertEqual(self.c.get(f"/api/dashboard-data?{q}", headers=h).status_code, 200, q)

    def test_empresa_ajena_o_inexistente_es_403(self):
        h = _cabecera("contador")
        for q in ("portfolio=Otra Empresa", "portfolio=2", "portfolio=No Existe"):
            r = self.c.get(f"/api/dashboard-data?{q}", headers=h)
            self.assertEqual(r.status_code, 403, q)
            self.assertEqual(r.json()["detail"], alcance.AJENA)

    def test_sin_empresa_no_hay_consolidado(self):
        r = self.c.get("/api/dashboard-data", headers=_cabecera("admin"))
        self.assertEqual((r.status_code, r.json()["detail"]), (403, alcance.ELIGE))

    def test_lista_de_empresas(self):
        h = _cabecera("contador")
        self.assertEqual(self.c.get("/api/diario/movimientos?empresas=Negocio A", headers=h).status_code, 200)
        self.assertEqual(self.c.get("/api/diario/movimientos?empresas=Negocio A,Otra Empresa",
                                    headers=h).status_code, 403)
        self.assertEqual(self.c.get("/api/diario/movimientos?empresas=*", headers=h).status_code, 403)

    def test_body_json_y_formulario(self):
        h = _cabecera("admin")
        self.assertEqual(self.c.post("/api/transactions", json={"portfolio_name": "Negocio A"},
                                     headers=h).status_code, 200)
        self.assertEqual(self.c.post("/api/transactions", json={"portfolio_name": "Otra Empresa"},
                                     headers=h).status_code, 403)
        self.assertEqual(self.c.post("/api/transactions", json={"concept": "x"}, headers=h).status_code, 403)
        self.assertEqual(self.c.post("/api/accounting-files/upload", data={"portfolio_id": "1"},
                                     headers=h).status_code, 200)
        self.assertEqual(self.c.post("/api/accounting-files/upload", data={"portfolio_id": "2"},
                                     headers=h).status_code, 403)

    def test_sin_empresas_asignadas_no_ve_ninguna(self):
        self.empresas_de_bd.return_value = frozenset()
        self.assertEqual(self.c.get("/api/dashboard-data?portfolio=Negocio A",
                                    headers=_cabecera("member")).status_code, 403)


class TestClases(_Base):
    def test_ruta_no_clasificada_es_solo_del_dueno(self):
        r = self.c.get("/api/org/consolidated", headers=_cabecera("admin"))
        self.assertEqual((r.status_code, r.json()["detail"]), (403, alcance.SOLO_DUENO))

    def test_global_sin_empresa_no_consulta(self):
        self.empresas_de_bd.side_effect = AssertionError("una ruta GLOBAL sin empresa no consulta")
        self.assertEqual(self.c.get("/api/tags", headers=_cabecera("member")).status_code, 200)

    def test_global_con_empresa_ajena_tambien_es_403(self):
        self.assertEqual(self.c.get("/api/tags?portfolio=Otra Empresa", headers=_cabecera("member")).status_code, 403)


class TestRegistro(_Base):
    def _con(self, resultado):
        p = mock.patch.object(alcance, "_empresa_del_registro", return_value=resultado)
        p.start()
        self.addCleanup(p.stop)

    def test_transaccion_de_otra_empresa(self):
        self._con((True, 2, False))
        self.assertEqual(self.c.put("/api/transactions/7", json={}, headers=_cabecera("admin")).status_code, 403)

    def test_transaccion_suya_e_inexistente(self):
        self._con((True, 1, False))
        self.assertEqual(self.c.put("/api/transactions/7", json={}, headers=_cabecera("admin")).status_code, 200)
        self._con((False, None, False))
        self.assertEqual(self.c.put("/api/transactions/8", json={}, headers=_cabecera("admin")).status_code, 200)

    def test_no_se_puede_mover_a_una_empresa_ajena(self):
        self._con((True, 1, False))
        r = self.c.put("/api/transactions/7", json={"portfolio_name": "Otra Empresa"}, headers=_cabecera("admin"))
        self.assertEqual(r.status_code, 403)

    def test_registro_sin_empresa(self):
        self._con((True, None, False))           # asiento sin empresa: terreno del dueño
        self.assertEqual(self.c.put("/api/transactions/7", json={}, headers=_cabecera("admin")).status_code, 403)
        self._con((True, -1, True))              # borrador del bot aún sin empresa
        self.assertEqual(self.c.get("/api/bot/drafts/5", headers=_cabecera("member")).status_code, 200)

    def test_si_la_bd_falla_es_503(self):
        p = mock.patch.object(alcance, "_empresa_del_registro", side_effect=RuntimeError("sin red"))
        p.start()
        self.addCleanup(p.stop)
        r = self.c.put("/api/transactions/7", json={}, headers=_cabecera("admin"))
        self.assertEqual(r.status_code, 503)


class TestAyudas(unittest.TestCase):
    def tearDown(self):
        alcance.limpiar_cache()

    def test_token_de_servicio_sin_usuario_real(self):
        with mock.patch.object(alcance, "_consultar", side_effect=AssertionError("no consulta")):
            self.assertEqual(alcance._empresas_de_bd("health"), frozenset())

    def test_cache_y_limpieza(self):
        user = {"uid": CONTADOR, "role": "contador"}
        with mock.patch.object(alcance, "_empresas_de_bd", return_value=frozenset({1})) as bd:
            alcance.empresas_permitidas(user)
            alcance.empresas_permitidas(user)
            self.assertEqual(bd.call_count, 1, "dentro del minuto no vuelve a la BD")
            alcance.limpiar_cache(CONTADOR)
            alcance.empresas_permitidas(user)
            self.assertEqual(bd.call_count, 2)

    def test_filtrar_portafolios(self):
        lista = [{"id": 1, "name": "Negocio A"}, {"id": 2, "name": "Otra Empresa"}]
        with mock.patch.object(alcance, "_empresas_de_bd", return_value=frozenset({2})):
            self.assertEqual(alcance.filtrar_portafolios({"uid": CONTADOR, "role": "member"}, lista), [lista[1]])
        self.assertEqual(alcance.filtrar_portafolios({"uid": "x", "role": "owner"}, lista), lista)


# ── Trinquete sobre las rutas reales ─────────────────────────────────────────

def _nombres_de(dep, out=None):
    """Nombres de query y de campos del body en todo el árbol de dependencias."""
    from pydantic import BaseModel
    out = set() if out is None else out
    out.update(p.name for p in dep.query_params)
    for p in dep.body_params:
        tipo = getattr(getattr(p, "field_info", None), "annotation", None)
        if isinstance(tipo, type) and issubclass(tipo, BaseModel):
            out.update(tipo.model_fields)
        else:
            out.add(p.name)
    for d in dep.dependencies:
        _nombres_de(d, out)
    return out


class TestTrinquete(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.routing import APIRoute
        import server
        cls.rutas = {}
        for r in server.app.routes:
            if isinstance(r, APIRoute):
                for m in r.methods:
                    cls.rutas[(m, r.path)] = r

    def test_toda_ruta_clasificada_existe(self):
        sobran = sorted(f"{m} {p}" for m, p in alcance.RUTAS if (m, p) not in self.rutas)
        self.assertEqual(sobran, [], "clasificadas en shared/alcance.py pero ya no existen")

    def test_la_dependencia_esta_en_todas_las_rutas(self):
        sin = sorted(f"{m} {p}" for (m, p), r in self.rutas.items()
                     if not any(d.call is alcance.verificar for d in r.dependant.dependencies))
        self.assertEqual(sin, [])

    def test_una_global_no_recibe_empresa(self):
        malas = sorted(f"{m} {p}" for (m, p), clase in alcance.RUTAS.items()
                       if clase == alcance.GLOBAL and (m, p) in self.rutas
                       and _nombres_de(self.rutas[(m, p)].dependant) & set(alcance.PARAMS_EMPRESA))
        self.assertEqual(malas, [], "reciben empresa: deben ser EMPRESA")

    def test_una_empresa_recibe_empresa(self):
        malas = sorted(f"{m} {p}" for (m, p), clase in alcance.RUTAS.items()
                       if clase == alcance.EMPRESA and (m, p) in self.rutas
                       and not _nombres_de(self.rutas[(m, p)].dependant) & set(alcance.PARAMS_EMPRESA))
        self.assertEqual(malas, [], "no reciben empresa: siempre responderían 403")

    def test_cada_registro_tiene_su_resolvedor(self):
        malas = []
        for (m, p), clase in alcance.RUTAS.items():
            if isinstance(clase, tuple):
                param = clase[1]
                if param not in alcance.RESOLVERES or "{" + param + "}" not in p:
                    malas.append(f"{m} {p} ({param})")
        self.assertEqual(malas, [])


@unittest.skipUnless(os.environ.get("DB_HOST"), "requiere BD")
class TestConsultasReales(unittest.TestCase):
    """Solo lectura: las consultas calzan con las tablas y tipos de producción."""

    def test_resolvedores(self):
        prueba = {"entry_group_id": "no-existe-h9"}
        for param in alcance.RESOLVERES:
            encontrado, _, _ = alcance._empresa_del_registro(param, prueba.get(param, -1))
            self.assertFalse(encontrado, param)

    def test_portafolios_y_membresia(self):
        alcance.limpiar_cache()
        self.assertTrue(alcance.portafolios(), "hay portafolios")
        self.assertEqual(alcance._empresas_de_bd(str(uuid.uuid4())), frozenset())


if __name__ == "__main__":
    unittest.main()
