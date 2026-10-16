# -*- coding: utf-8 -*-
"""Búsqueda y filtros del Libro Diario en el servidor (16-oct-2026).

- construir_filtros / armar_sql: puros, corren en el CI sin BD.
- buscar_movimientos / opciones_filtros: SOLO LECTURA contra la BD real
  (se saltan si no hay DB_HOST). Comparan los totales filtrados con una
  suma hecha en Python sobre la lista completa del portafolio.

    python -m unittest tests.test_diario_filtros
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import tests  # noqa: F401,E402  (carga .env)

from fin_sys_core.diario_query import (  # noqa: E402
    BANDERAS, GRUPOS, ORDENES, armar_sql, construir_filtros, numero_de_busqueda,
)


class TestConstruirFiltros(unittest.TestCase):
    def test_sin_filtros_es_true(self):
        where, p = construir_filtros({})
        self.assertEqual(where, "TRUE")
        self.assertEqual(p, {})

    def test_listas_desde_csv(self):
        where, p = construir_filtros({"tipos": "ingreso, gasto", "terceros": "3,7",
                                      "etiquetas": "Bonaire obra", "empresas": "Negocio A"})
        self.assertEqual(p["tipos"], ["INGRESO", "GASTO"])
        self.assertEqual(p["terceros"], [3, 7])
        self.assertEqual(p["etiquetas"], ["Bonaire obra"])
        self.assertEqual(p["empresas"], ["Negocio A"])
        self.assertIn("t.tags && %(etiquetas)s::text[]", where)

    def test_cuenta_incluye_destino_de_transferencia(self):
        where, _ = construir_filtros({"cuentas": "2"})
        self.assertIn("t.dest_account_id = ANY(%(cuentas)s)", where)

    def test_busqueda_texto_numero_e_id(self):
        _, p = construir_filtros({"q": "Café"})
        self.assertEqual(p["q"], "%cafe%")
        _, p = construir_filtros({"q": "100%"})
        self.assertEqual(p["q"], "%100\\%%")         # el % del usuario es literal
        self.assertNotIn("q_num", p)
        _, p = construir_filtros({"q": "$17.500"})
        self.assertEqual(p["q_num"], 17500.0)
        _, p = construir_filtros({"q": "#88"})
        self.assertEqual(p["q_id"], 88)

    def test_numero_formato_colombiano(self):
        self.assertEqual(numero_de_busqueda("1.500.000"), 1500000.0)
        self.assertEqual(numero_de_busqueda("1.500,50"), 1500.5)
        self.assertIsNone(numero_de_busqueda("abc"))
        self.assertIsNone(numero_de_busqueda("..."))

    def test_errores_legibles(self):
        casos = [
            {"tipos": "OTRO"}, {"desde": "2026-13-01"}, {"terceros": "x"},
            {"desde": "2026-10-02", "hasta": "2026-10-01"},
            {"monto_min": "10", "monto_max": "5"}, {"moneda": "EUR"},
            {"cartera": "XX"}, {"banderas": "inventada"}, {"q": "x" * 121},
        ]
        for f in casos:
            with self.subTest(f=f), self.assertRaises(ValueError):
                construir_filtros(f)

    def test_banderas_y_cartera(self):
        where, p = construir_filtros({"banderas": "sin_tercero,duplicados",
                                      "cartera": "cxc", "cartera_estado": "pendiente"})
        self.assertIn(BANDERAS["sin_tercero"], where)
        self.assertIn("b.n_iguales > 1", where)
        self.assertEqual(p["cartera"], "CXC")
        self.assertEqual(p["cartera_estado"], "PENDIENTE")

    def test_sql_rechaza_orden_y_grupo_inventados(self):
        with self.assertRaises(ValueError):
            armar_sql("TRUE", "DROP", None)
        with self.assertRaises(ValueError):
            armar_sql("TRUE", "fecha_desc", "nada")
        for o in ORDENES:
            for g in [None, *GRUPOS]:
                self.assertIn("WITH", armar_sql("TRUE", o, g))


@unittest.skipUnless(os.environ.get("DB_HOST"), "requiere BD")
class TestContraBD(unittest.TestCase):
    """Solo lectura: no crea ni borra nada."""

    @classmethod
    def setUpClass(cls):
        from fin_sys_core.dashboard_query import obtener_dashboard_snapshot
        snap = obtener_dashboard_snapshot(None, limit=0, incluir_txs=False)
        cls.empresa = None
        for pf in snap["portfolios"]:
            s = obtener_dashboard_snapshot(pf["name"], limit=5000)
            if s["total_tx_count"] > 0:
                cls.empresa, cls.todas = pf["name"], s["transactions"]
                break
        if not cls.empresa:
            raise unittest.SkipTest("ningún portafolio con transacciones")

    def _buscar(self, **f):
        from fin_sys_core.diario_query import buscar_movimientos
        orden = f.pop("orden", "fecha_desc")
        agrupar = f.pop("agrupar", None)
        limit = f.pop("limit", 5000)
        return buscar_movimientos({"empresas": [self.empresa], **f}, orden=orden,
                                  agrupar=agrupar, limit=limit)

    @staticmethod
    def _suma(txs, tipo):
        return round(sum(float(t["net_value"] or 0) for t in txs
                         if (t["type"] or "").upper() == tipo
                         and t.get("transaction_currency") != "USD"), 2)

    def test_sin_filtros_igual_al_dashboard(self):
        r = self._buscar()
        self.assertEqual(r["total"], len(self.todas))
        self.assertEqual([t["id"] for t in r["transactions"]], [t["id"] for t in self.todas])
        self.assertAlmostEqual(r["totales"]["ingresos_cop"], self._suma(self.todas, "INGRESO"), places=2)
        self.assertAlmostEqual(r["totales"]["gastos_cop"], self._suma(self.todas, "GASTO"), places=2)

    def test_tipo_gasto_y_totales(self):
        r = self._buscar(tipos="GASTO")
        esperado = [t for t in self.todas if t["type"].upper() == "GASTO"]
        self.assertEqual(r["total"], len(esperado))
        self.assertTrue(all(t["type"].upper() == "GASTO" for t in r["transactions"]))
        self.assertEqual(r["totales"]["ingresos_cop"], 0)
        self.assertAlmostEqual(r["totales"]["gastos_cop"], self._suma(esperado, "GASTO"), places=2)

    def test_orden_por_monto(self):
        r = self._buscar(orden="monto_desc")
        montos = [float(t["net_value"] or 0) for t in r["transactions"]]
        self.assertEqual(montos, sorted(montos, reverse=True))

    def test_paginacion_estable(self):
        a = self._buscar(limit=10)["transactions"]
        from fin_sys_core.diario_query import buscar_movimientos
        b = buscar_movimientos({"empresas": [self.empresa]}, limit=10, offset=10)["transactions"]
        self.assertFalse({t["id"] for t in a} & {t["id"] for t in b})

    def test_busqueda_por_concepto(self):
        palabra = next((t["concept"].split()[0] for t in self.todas if t.get("concept")), None)
        if not palabra:
            self.skipTest("sin conceptos")
        r = self._buscar(q=palabra)
        self.assertGreater(r["total"], 0)

    def test_fechas(self):
        f = self.todas[len(self.todas) // 2]["transaction_date"]
        r = self._buscar(desde=f, hasta=f)
        self.assertTrue(all(t["transaction_date"] == f for t in r["transactions"]))
        self.assertEqual(r["total"], sum(1 for t in self.todas if t["transaction_date"] == f))

    def test_grupos_suman_lo_mismo_que_los_totales(self):
        for g in ("tercero", "categoria", "mes", "cuenta", "tipo", "empresa"):
            with self.subTest(g=g):
                r = self._buscar(agrupar=g, limit=0)
                self.assertEqual(sum(x["n"] for x in r["grupos"]), r["total"])
                self.assertAlmostEqual(sum(x["gastos_cop"] for x in r["grupos"]),
                                       r["totales"]["gastos_cop"], places=2)

    def test_opciones(self):
        from fin_sys_core.diario_query import opciones_filtros
        o = opciones_filtros([self.empresa])
        for k in ("terceros", "cuentas", "categorias", "etiquetas", "empresas", "fechas"):
            self.assertIn(k, o)
        self.assertTrue(any(e["valor"] == self.empresa for e in o["empresas"]))


@unittest.skipUnless(os.environ.get("DB_HOST"), "requiere BD")
class TestLibroMayorSinDesde(unittest.TestCase):
    """Regresión 16-oct: sin `desde`, el saldo inicial sumaba TODO y el final
    salía al doble. Solo lectura sobre una cuenta con movimientos reales."""

    def test_saldo_inicial_cero_y_final_igual_a_movimientos(self):
        from fin_sys_core.db_pool import get_conn, put_conn
        from kernel import kernel_reports as rep
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT portfolio_id, cuenta_codigo FROM kernel_journal_entries "
                        f"WHERE {rep.EN_LIBROS} AND portfolio_id IS NOT NULL "
                        f"GROUP BY 1, 2 ORDER BY COUNT(*) DESC LIMIT 1")
            fila = cur.fetchone()
        finally:
            put_conn(conn)
        if not fila:
            self.skipTest("sin asientos en libros")
        lm = rep.libro_mayor(fila[0], fila[1])
        self.assertEqual(lm["saldo_inicial"], 0.0)
        self.assertAlmostEqual(lm["saldo_final"], lm["total_debito"] - lm["total_credito"], places=2)
        # con `desde`, inicial + movimientos del rango = saldo sin filtro
        if lm["movimientos"]:
            medio = lm["movimientos"][len(lm["movimientos"]) // 2]["fecha"]
            parte = rep.libro_mayor(fila[0], fila[1], medio)
            self.assertAlmostEqual(parte["saldo_final"], lm["saldo_final"], places=2)


if __name__ == "__main__":
    unittest.main()
