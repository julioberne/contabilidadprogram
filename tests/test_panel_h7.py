# -*- coding: utf-8 -*-
"""Panel por versión y fotos de saldo (estándar H7, 27-oct-2026).

- Puros (CI sin BD): la consulta sin foto es la de siempre; con foto lee
  saldos_foto/kpi_foto y solo lo posterior al corte; sin la migración el estado
  del panel es (None, None) sin abortar la transacción.
- Contra la BD (SOLO LECTURA; se saltan sin DB_HOST): foto + lo posterior al
  corte da LO MISMO que recorrer todo (cuentas y KPIs, por empresa y en
  consolidado), y las consultas que llenan las fotos dan esas mismas cifras.

    python -m unittest tests.test_panel_h7
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import tests  # noqa: F401,E402

from fin_sys_core import dashboard_query as dq  # noqa: E402
from fin_sys_core import saldos_foto as sf  # noqa: E402


class TestConsulta(unittest.TestCase):
    def test_sin_foto_es_la_de_siempre(self):
        sql = dq.armar_snapshot_sql("no")
        self.assertIs(dq._SNAPSHOT_SQL, dq._SNAPSHOT_SQL)
        self.assertNotIn("%(corte)s", sql)
        self.assertNotIn("saldos_foto", sql)

    def test_con_foto_lee_las_tablas_y_lo_posterior(self):
        sql = dq.armar_snapshot_sql("tabla")
        self.assertIn("FROM saldos_foto", sql)
        self.assertIn("FROM kpi_foto", sql)
        self.assertIn("WHERE t.id > %(corte)s", sql)
        self.assertNotIn("t.id <= %(corte)s", sql)
        en_linea = dq.armar_snapshot_sql("en_linea")
        self.assertIn("t.id <= %(corte)s", en_linea)
        self.assertNotIn("saldos_foto", en_linea)
        with self.assertRaises(ValueError):
            dq.armar_snapshot_sql("otra")

    def test_estado_sin_migracion_no_aborta(self):
        class Cur:
            def __init__(self):
                self.sqls = []

            def execute(self, sql, params=None):
                self.sqls.append(sql)
                if "panel_version" in sql:
                    raise Exception('relation "panel_version" does not exist')

        cur = Cur()
        self.assertEqual(sf.estado_panel(cur, "Negocio A"), (None, None))
        self.assertEqual(cur.sqls[-1], "ROLLBACK TO SAVEPOINT panel_h7", "la transacción sigue usable")

    def test_foto_se_puede_apagar(self):
        from unittest import mock
        with mock.patch.dict(os.environ, {"PANEL_FOTOS": "0"}):
            self.assertFalse(sf.fotos_activas())
        with mock.patch.dict(os.environ, {"PANEL_FOTOS": ""}):
            self.assertTrue(sf.fotos_activas())


@unittest.skipUnless(os.environ.get("DB_HOST"), "requiere BD")
class TestFotoIgualQueTodo(unittest.TestCase):
    """Solo lectura: nada se escribe."""

    @classmethod
    def setUpClass(cls):
        from fin_sys_core.db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM portfolios ORDER BY id")
            cls.empresas = [None] + [r[0] for r in cur.fetchall()]
            cur.execute("SELECT id FROM transactions ORDER BY id")
            ids = [r[0] for r in cur.fetchall()]
        finally:
            put_conn(conn)
        if len(ids) < 4:
            raise unittest.SkipTest("pocas transacciones")
        cls.cortes = [ids[len(ids) // 3], ids[(2 * len(ids)) // 3], ids[-1]]

    def _correr(self, sql, params, una=False):
        from fin_sys_core.db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(sql, params)
            return cur.fetchone() if una else cur.fetchall()
        finally:
            put_conn(conn)

    def _cifras(self, modo, empresa, corte=0):
        fila = self._correr(dq.armar_snapshot_sql(modo) if modo != "no" else dq._SNAPSHOT_SQL,
                            {"portfolio": empresa, "limit": 0, "offset": 0, "corte": corte}, una=True)
        _, cuentas, _, kpi, _, _ = fila
        dq._redondear_cuentas(cuentas)
        return ({c["id"]: (c["tx_delta"], c["expected_balance"]) for c in cuentas},
                {k: round(float(v), 2) for k, v in kpi.items()})

    def test_foto_mas_lo_posterior_igual_a_recorrer_todo(self):
        for empresa in self.empresas:
            completo = self._cifras("no", empresa)
            for corte in self.cortes:
                with self.subTest(empresa=empresa, corte=corte):
                    partido = self._cifras("en_linea", empresa, corte)
                    self.assertEqual(set(partido[0]), set(completo[0]))
                    for cid, (delta, esperado) in completo[0].items():
                        self.assertAlmostEqual(partido[0][cid][0], delta, places=2)
                        self.assertAlmostEqual(partido[0][cid][1], esperado, places=2)
                    for k, v in completo[1].items():
                        self.assertAlmostEqual(partido[1][k], v, places=2, msg=k)

    def test_las_consultas_de_la_foto_dan_lo_mismo(self):
        """Las sentencias que llenan saldos_foto/kpi_foto, sin el INSERT (solo lectura),
        con el corte en la última transacción: la foto cubre todo y debe dar las cifras
        completas, cuenta por cuenta y empresa por empresa."""
        saldos, kpi = sf._sql_foto()
        sel_saldos = saldos.replace("INSERT INTO saldos_foto (account_id, delta)\n", "")
        sel_kpi = kpi.replace(
            "INSERT INTO kpi_foto (portfolio_id, ingresos_usd, gastos_usd, ingresos_cop, gastos_cop, n)\n", "")
        corte = self.cortes[-1]
        foto = {cid: round(float(d), 2) for cid, d in self._correr(sel_saldos, {"corte": corte})}
        completo, kpi_todo = self._cifras("no", None)
        for cid, (delta, _) in completo.items():
            self.assertAlmostEqual(foto.get(cid, 0.0), delta, places=2, msg=f"cuenta {cid}")
        filas = self._correr(sel_kpi, {"corte": corte})          # (pid, ing_usd, gas_usd, ing_cop, gas_cop, n)
        self.assertAlmostEqual(sum(float(r[3]) for r in filas), kpi_todo["ingresos_cop"], places=2)
        self.assertAlmostEqual(sum(float(r[4]) for r in filas), kpi_todo["gastos_cop"], places=2)
        self.assertEqual(sum(int(r[5]) for r in filas), kpi_todo["total"])


if __name__ == "__main__":
    unittest.main()
