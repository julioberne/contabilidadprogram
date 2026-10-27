# -*- coding: utf-8 -*-
"""Transacciones acotadas (estándar H6, 27-oct-2026).

- Puros (CI sin BD): la consulta filtra por ids, empresas y fechas en la BD, con
  el mismo orden que la descarga completa de siempre.
- Contra la BD (SOLO LECTURA; se saltan sin DB_HOST): las filas son IGUALES a las
  de obtener_transacciones filtradas en Python (lo que hacían los llamadores).

    python -m unittest tests.test_transacciones_acotadas
"""
import os
import sys
import unittest
from datetime import date

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import tests  # noqa: F401,E402

from fin_sys_core.consultas import transacciones as tr  # noqa: E402


class TestArmar(unittest.TestCase):
    def test_por_ids(self):
        sql, p = tr.armar_por_ids([5, "3", 5])
        self.assertIn("WHERE t.id = ANY(%(ids)s)", sql)
        self.assertTrue(sql.endswith("ORDER BY t.transaction_date DESC, t.id DESC"))
        self.assertEqual(p, {"ids": [3, 5]})
        with self.assertRaises(ValueError):
            tr.armar_por_ids(range(tr.MAX_IDS + 1))

    def test_por_filtro(self):
        sql, p = tr.armar_por_filtro(["Negocio A", ""], date(2026, 9, 1), date(2026, 9, 30))
        self.assertIn("p.name = ANY(%(empresas)s)", sql)
        self.assertIn("t.transaction_date::date >= %(desde)s", sql)
        self.assertIn("t.transaction_date::date <= %(hasta)s", sql)
        self.assertEqual(p["empresas"], ["Negocio A"])
        sql, p = tr.armar_por_filtro()
        # sin filtros = todas (exportar todo el historial sigue valiendo)
        self.assertNotIn("p.name = ANY", sql)
        self.assertNotIn("transaction_date::date", sql)
        self.assertEqual(p, {})

    def test_vacio_no_consulta(self):
        self.assertEqual(tr.por_ids([]), [])


class TestDatasetAnalisis(unittest.TestCase):
    """H6.2: Análisis por defecto con los últimos 12 meses de todas las empresas."""

    def test_periodo(self):
        from routers.analytics import periodo_dataset
        self.assertEqual(periodo_dataset(12, date(2026, 10, 27)), (date(2025, 10, 28), date(2026, 10, 27)))
        self.assertEqual(periodo_dataset(3, date(2026, 5, 31)), (date(2026, 3, 1), date(2026, 5, 31)))
        self.assertEqual(periodo_dataset(12, date(2028, 2, 29)), (date(2027, 3, 1), date(2028, 2, 29)))
        self.assertEqual(periodo_dataset(0), (None, None), "0 = todo el historial")

    def _get(self, url, filas):
        from unittest import mock

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from routers import analytics as rt
        from routers.auth_guard import require_auth
        app = FastAPI()
        app.include_router(rt.router)
        app.dependency_overrides[require_auth] = lambda: {"uid": "u1"}
        parches = (mock.patch("fin_sys_core.consultas.transacciones.por_filtro", return_value=filas),
                   mock.patch.object(rt, "_nombres_de_empresa", return_value={}),
                   mock.patch.object(rt, "TOPE_DATASET", 3))
        with parches[0] as pf, parches[1], parches[2]:
            r = TestClient(app).get(url)
        return r, pf

    @staticmethod
    def _tx(i):
        return {"id": i, "portfolio_name": "Negocio A", "transaction_date": date(2026, 9, i), "type": "GASTO",
                "amount": 10, "net_value": 10}

    def test_por_defecto_12_meses_y_tope_con_aviso(self):
        r, pf = self._get("/api/analytics/dataset", [self._tx(i) for i in range(1, 5)])
        d = r.json()
        empresas, desde, hasta = pf.call_args[0]
        self.assertIsNone(empresas)
        self.assertEqual((hasta - desde).days, 364)
        self.assertEqual(pf.call_args[1]["limite"], 4, "pide uno de más para saber si se cortó")
        self.assertEqual((d["n"], d["truncado"]), (3, True))
        self.assertIn("más recientes", d["aviso"])

    def test_empresa_y_todo_el_historial(self):
        r, pf = self._get("/api/analytics/dataset?meses=0&empresa=Negocio%20A", [self._tx(1), self._tx(1)])
        self.assertEqual(pf.call_args[0], (["Negocio A"], None, None))
        d = r.json()
        self.assertEqual((d["n"], d["truncado"], d["aviso"], d["desde"]), (1, False, None, None),
                         "la fila repetida por la unión con activos ya no se cuenta dos veces")


@unittest.skipUnless(os.environ.get("DB_HOST"), "requiere BD")
class TestIgualQueAntes(unittest.TestCase):
    """Solo lectura."""

    @classmethod
    def setUpClass(cls):
        from fin_sys_core.database_driver import obtener_transacciones
        cls.todas = obtener_transacciones(None)
        if not cls.todas:
            raise unittest.SkipTest("sin transacciones")

    def test_sin_filtros_igual_a_la_descarga_completa(self):
        self.assertEqual(tr.por_filtro(), self.todas)

    def test_por_ids_igual_al_filtro_en_python(self):
        ids = {t["id"] for t in self.todas[::3]}
        esperado = [t for t in self.todas if t["id"] in ids]
        self.assertEqual(tr.por_ids(ids), esperado)

    def test_por_empresa_y_fechas_igual_al_filtro_en_python(self):
        from fin_sys_core.export_xlsx import _a_fecha
        empresa = self.todas[0]["portfolio_name"]
        fechas = sorted(f for t in self.todas if (f := _a_fecha(t.get("transaction_date"))))
        desde, hasta = fechas[len(fechas) // 4], fechas[(3 * len(fechas)) // 4]
        esperado = [t for t in self.todas if t.get("portfolio_name") == empresa
                    and (f := _a_fecha(t.get("transaction_date"))) is not None and desde <= f <= hasta]
        self.assertEqual(tr.por_filtro([empresa], desde, hasta), esperado)


if __name__ == "__main__":
    unittest.main()
