# -*- coding: utf-8 -*-
"""Análisis Inteligente B0 — catálogo whitelisted de métricas (tests puros).

Verifica los criterios inmutables sin base de datos (patrón FakeCursor de
test_terceros_resolucion):
  1. Ninguna cifra nace de la IA: solo métricas del catálogo, id desconocido → error.
  2. La empresa va amarrada por código: portfolio_id entra al SQL solo si el
     BACKEND lo pasa; parámetros 'empresa'/'portfolio' del LLM se descartan.
  3. Sello de origen en toda respuesta ("según N TXs de <rango>").
  4. Errores honestos: sin datos se dice, no se rellena.
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fin_sys_core"))

import metrics_catalog  # noqa: E402
from metrics_catalog import CATALOGO, catalogo_para_prompt, catalogo_publico, ejecutar_metrica  # noqa: E402


class FakeCursor:
    """Registra cada execute; sirve fetchone/fetchall desde colas predefinidas."""

    def __init__(self, fetchones=(), fetchalls=()):
        self.ejecutadas = []          # [(sql_normalizado, params), ...]
        self._fetchones = list(fetchones)
        self._fetchalls = list(fetchalls)

    def execute(self, sql, params=None):
        self.ejecutadas.append((" ".join(sql.split()), list(params or [])))

    def fetchone(self):
        return self._fetchones.pop(0)

    def fetchall(self):
        return self._fetchalls.pop(0)

    def close(self):
        pass


class FakeConn:
    def __init__(self, cur):
        self._cur = cur

    def cursor(self):
        return self._cur


def correr(metric_id, params=None, portfolio_id=None, cur=None):
    cur = cur if cur is not None else FakeCursor()
    return ejecutar_metrica(metric_id, params, portfolio_id=portfolio_id, conn=FakeConn(cur)), cur


class TestCatalogo(unittest.TestCase):

    def test_catalogo_completo_y_publico_sin_funciones(self):
        esperadas = {"resumen_periodo", "gasto_mes", "ingreso_mes", "variacion_mensual",
                     "flujo_mensual", "balance_cuentas", "cartera_vencida", "calidad_datos",
                     "conteo_terceros"}
        self.assertEqual(set(CATALOGO), esperadas)
        publico = catalogo_publico()
        self.assertEqual({m["id"] for m in publico}, esperadas)
        for m in publico:
            self.assertNotIn("fn", m)          # la función jamás viaja al cliente
            self.assertTrue(m["descripcion"])
            # Auditabilidad visible (16-sep): cada métrica publica su SQL
            self.assertIn("SELECT", m["sql"])
            self.assertIn("FROM", m["sql"])

    def test_prompt_incluye_todas_las_metricas(self):
        prompt = catalogo_para_prompt()
        for mid in CATALOGO:
            self.assertIn(mid, prompt)
        self.assertIn("YYYY-MM", prompt)       # el LLM ve el formato de los params

    def test_metrica_desconocida_es_error(self):
        with self.assertRaises(ValueError) as ctx:
            ejecutar_metrica("sql_libre", conn=FakeConn(FakeCursor()))
        self.assertIn("no existe en el catálogo", str(ctx.exception))


class TestValidacionParams(unittest.TestCase):

    def test_mes_malformado(self):
        for malo in ("2026-13", "septiembre", "2026/09", "26-09"):
            with self.assertRaises(ValueError):
                correr("gasto_mes", {"mes": malo})

    def test_fecha_inexistente(self):
        with self.assertRaises(ValueError):
            correr("resumen_periodo", {"desde": "2026-02-31"})

    def test_entero_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            correr("flujo_mensual", {"meses": 99})

    def test_opcion_se_normaliza(self):
        cur = FakeCursor(fetchones=[(2, 100.0), (3, 250.0)])
        res, cur = correr("variacion_mensual", {"tipo": "gasto", "mes": "2026-09"}, cur=cur)
        self.assertEqual(cur.ejecutadas[0][1][0], "GASTO")   # 'gasto' → 'GASTO'
        self.assertEqual(res["detalle"]["tipo"], "GASTO")

    def test_params_desconocidos_se_descartan_incluida_la_empresa(self):
        """Criterio inmutable 2: si el LLM manda 'empresa'/'portfolio', muere
        en la whitelist — el SQL no cambia y no hay error."""
        cur = FakeCursor(fetchones=[(0, 0, 0, None, None)], fetchalls=[[]])
        res, cur = correr("gasto_mes",
                          {"mes": "2026-09", "empresa": 99, "portfolio": 99, "sql": "DROP TABLE"},
                          portfolio_id=None, cur=cur)
        for sql, params in cur.ejecutadas:
            self.assertNotIn("portfolio_id", sql)
            self.assertNotIn(99, params)


class TestEmpresaAmarrada(unittest.TestCase):

    def test_sin_portafolio_no_filtra(self):
        cur = FakeCursor(fetchones=[(2, 500.0, 300.0, 0, datetime.date(2026, 9, 1), datetime.date(2026, 9, 10))])
        _, cur = correr("resumen_periodo", {"desde": "2026-09-01", "hasta": "2026-09-15"}, cur=cur)
        self.assertNotIn("portfolio_id", cur.ejecutadas[0][0])

    def test_con_portafolio_filtra_por_codigo(self):
        cur = FakeCursor(fetchones=[(2, 500.0, 300.0, 0, datetime.date(2026, 9, 1), datetime.date(2026, 9, 10))])
        res, cur = correr("resumen_periodo", {"desde": "2026-09-01", "hasta": "2026-09-15"},
                          portfolio_id=7, cur=cur)
        sql, params = cur.ejecutadas[0]
        self.assertIn("t.portfolio_id = %s", sql)
        self.assertEqual(params[-1], 7)
        self.assertEqual(res["portfolio_id"], 7)


class TestGastoMes(unittest.TestCase):

    def test_agrupado_con_sello_y_usd_excluidas(self):
        cur = FakeCursor(
            fetchalls=[[("Nómina", 5000000, 3), ("Arriendo", 2000000, 1), ("Vacía", 0, 0)]],
            fetchones=[(4, 7000000, 2, datetime.date(2026, 9, 2), datetime.date(2026, 9, 14))],
        )
        res, cur = correr("gasto_mes", {"mes": "2026-09"}, cur=cur)
        sql_grupos, params_grupos = cur.ejecutadas[0]
        self.assertIn("GROUP BY 1", sql_grupos)
        self.assertEqual(params_grupos[0], "GASTO")
        self.assertEqual(params_grupos[1:3], ["2026-09-01", "2026-09-30"])
        self.assertEqual(res["valor"], 7000000.0)
        # El grupo con 0 TXs en COP no se lista (era solo USD o vacío)
        self.assertEqual([v["etiqueta"] for v in res["valores"]], ["Nómina", "Arriendo"])
        self.assertEqual(res["origen"]["sello"], "según 4 TXs de 2026-09-02 a 2026-09-14")
        self.assertEqual(res["origen"]["usd_excluidas"], 2)

    def test_sin_datos_es_honesto(self):
        cur = FakeCursor(fetchalls=[[]], fetchones=[(0, 0, 0, None, None)])
        res, _ = correr("gasto_mes", {"mes": "2026-01"}, cur=cur)
        self.assertEqual(res["valor"], 0.0)
        self.assertIn("No hay", res["nota"])
        self.assertIn("sin", res["origen"]["sello"])

    def test_ingreso_mes_filtra_ingreso(self):
        cur = FakeCursor(fetchalls=[[]], fetchones=[(0, 0, 0, None, None)])
        _, cur = correr("ingreso_mes", {"mes": "2026-09", "agrupar_por": "tercero"}, cur=cur)
        self.assertEqual(cur.ejecutadas[0][1][0], "INGRESO")
        self.assertIn("third_parties", cur.ejecutadas[0][0])


class TestVariacionMensual(unittest.TestCase):

    def test_delta_y_porcentaje(self):
        cur = FakeCursor(fetchones=[(3, 1000000.0), (5, 1250000.0)])   # anterior, actual
        res, _ = correr("variacion_mensual", {"mes": "2026-09"}, cur=cur)
        v = res["valores"]
        self.assertEqual(v["mes_anterior"], "2026-08")
        self.assertEqual(v["delta"], 250000.0)
        self.assertEqual(v["pct"], 25.0)
        self.assertEqual(res["origen"]["n_txs"], 8)

    def test_enero_compara_contra_diciembre(self):
        cur = FakeCursor(fetchones=[(1, 10.0), (1, 20.0)])
        res, _ = correr("variacion_mensual", {"mes": "2026-01"}, cur=cur)
        self.assertEqual(res["valores"]["mes_anterior"], "2025-12")

    def test_sin_base_no_inventa_porcentaje(self):
        cur = FakeCursor(fetchones=[(0, 0.0), (2, 500.0)])
        res, _ = correr("variacion_mensual", {"mes": "2026-09"}, cur=cur)
        self.assertIsNone(res["valores"]["pct"])
        self.assertIn("no se puede calcular", res["nota"])


class TestCarteraVencida(unittest.TestCase):

    def test_totales_pct_y_clientes(self):
        cur = FakeCursor(
            fetchones=[(3, 4000000.0, 10, 10000000.0, datetime.date(2026, 7, 1), datetime.date(2026, 9, 1))],
            fetchalls=[[("Cliente Moroso SAS", 2500000.0, 2, datetime.date(2026, 7, 1)),
                        ("Otro Deudor", 1500000.0, 1, datetime.date(2026, 8, 15))]],
        )
        res, cur = correr("cartera_vencida", cur=cur)
        self.assertIn("l.status NOT IN ('PAGADO', 'CANCELADO')", cur.ejecutadas[0][0])
        self.assertIn("l.type = 'CXC'", cur.ejecutadas[0][0])
        v = res["valores"]
        self.assertEqual(v["monto_vencido"], 4000000.0)
        self.assertEqual(v["pct_vencida"], 40.0)
        self.assertEqual(v["clientes"][0]["etiqueta"], "Cliente Moroso SAS")
        self.assertIn("según 3", res["origen"]["sello"])

    def test_filtro_de_empresa_via_transaccion(self):
        cur = FakeCursor(fetchones=[(0, 0, 0, 0, None, None)], fetchalls=[[]])
        res, cur = correr("cartera_vencida", portfolio_id=4, cur=cur)
        for sql, params in cur.ejecutadas:
            self.assertIn("t.portfolio_id = %s", sql)
            self.assertEqual(params[-1], 4)


class TestBalanceYCalidad(unittest.TestCase):

    def test_balance_cuentas_ignora_empresa_y_lo_dice(self):
        cur = FakeCursor(fetchalls=[[("Banco M", 8000000.0, "COP", "BANCO"),
                                     ("Broker", 1000.0, "USD", "INVERSION")]])
        res, cur = correr("balance_cuentas", portfolio_id=3, cur=cur)
        self.assertNotIn("portfolio", cur.ejecutadas[0][0])
        self.assertEqual(res["valor"], 8000000.0)          # USD fuera del total COP
        self.assertIn("globales", res["nota"])
        self.assertIn("cuentas", res["origen"]["sello"])

    def test_calidad_datos(self):
        cur = FakeCursor(fetchones=[
            (120, 7, 30, datetime.date(2026, 1, 5), datetime.date(2026, 9, 14)),
            (4, 2),
        ])
        res, _ = correr("calidad_datos", cur=cur)
        v = res["valores"]
        self.assertEqual(v["txs_sin_categoria"], 7)
        self.assertEqual(v["txs_sin_evidencia"], 30)
        self.assertEqual(v["terceros_numero_provisional"], 4)
        self.assertEqual(v["terceros_nombres_duplicados"], 2)
        self.assertEqual(res["origen"]["sello"], "según 120 TXs de 2026-01-05 a 2026-09-14")


class TestConteoTerceros(unittest.TestCase):
    """Primera métrica nacida de la bitácora (hito 2)."""

    def test_totales_y_sello(self):
        cur = FakeCursor(fetchones=[
            (12, 3),                                        # total, provisionales (global)
            (8, 40, datetime.date(2026, 1, 5), datetime.date(2026, 9, 14)),
        ])
        res, cur = correr("conteo_terceros", cur=cur)
        v = res["valores"]
        self.assertEqual(v["total_terceros"], 12)
        self.assertEqual(v["provisionales"], 3)
        self.assertEqual(v["con_movimiento"], 8)
        self.assertEqual(res["valor"], 12)
        self.assertEqual(res["unidad"], "terceros")         # jamás se disfraza de COP
        self.assertEqual(res["origen"]["sello"], "según 40 TXs de 2026-01-05 a 2026-09-14")
        self.assertIn("global", res["nota"])

    def test_mes_y_empresa_solo_afectan_con_movimiento(self):
        cur = FakeCursor(fetchones=[(12, 3), (2, 5, datetime.date(2026, 9, 1), datetime.date(2026, 9, 10))])
        res, cur = correr("conteo_terceros", {"mes": "2026-09"}, portfolio_id=7, cur=cur)
        sql_global, params_global = cur.ejecutadas[0]
        self.assertNotIn("portfolio_id", sql_global)        # el total es global
        sql_mov, params_mov = cur.ejecutadas[1]
        self.assertIn("t.portfolio_id = %s", sql_mov)
        self.assertEqual(params_mov, ["2026-09-01", "2026-09-30", 7])
        self.assertIn("con movimiento", res["nota"].lower())


class TestFlujoMensual(unittest.TestCase):

    def test_serie_y_defaults(self):
        original = metrics_catalog._hoy
        metrics_catalog._hoy = lambda: datetime.date(2026, 9, 15)
        try:
            cur = FakeCursor(fetchalls=[[("2026-08", 900.0, 400.0, 3, 0),
                                         ("2026-09", 1200.0, 700.0, 5, 1)]])
            res, cur = correr("flujo_mensual", {"meses": 2}, cur=cur)
            self.assertEqual(cur.ejecutadas[0][1][:2], ["2026-08-01", "2026-09-15"])
            self.assertEqual(res["valores"][1]["neto"], 500.0)
            self.assertEqual(res["origen"]["n_txs"], 8)
            self.assertEqual(res["origen"]["usd_excluidas"], 1)
        finally:
            metrics_catalog._hoy = original


if __name__ == "__main__":
    unittest.main()
