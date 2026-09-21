# -*- coding: utf-8 -*-
"""Análisis Inteligente B3 — traductor de preguntas + respuesta con gráfica.

Tests puros: el LLM se mockea (patrón respuestas fijas), la métrica se
inyecta. Verifican los criterios inmutables de la capa de preguntas:
  - El LLM solo ELIGE del catálogo; su elección se sanea (_normalizar).
  - La empresa la inyecta el backend: cualquier 'empresa' del LLM se bota.
  - Toda respuesta redactada termina con el sello de origen.
  - La gráfica es PNG real (matplotlib Agg) y si falla, la respuesta sigue.
"""
import base64
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fin_sys_core"))

import ai_engine  # noqa: E402
import analytics_log  # noqa: E402
import analytics_qa  # noqa: E402
import metrics_catalog  # noqa: E402
from analytics_qa import _fmt_cop, _generar_grafica, _texto_respuesta, responder_pregunta  # noqa: E402


class FakeResponse:
    def __init__(self, contenido: dict):
        self.status_code = 200
        self._contenido = contenido

    def json(self):
        return {"choices": [{"message": {"content": json.dumps(self._contenido)}}]}


class FakeHttp:
    """Reemplaza ai_engine._http_client y captura el payload enviado a Groq."""

    def __init__(self, contenido):
        self.contenido = contenido
        self.payloads = []

    def post(self, url, headers=None, json=None, **kw):
        self.payloads.append(json)
        return FakeResponse(self.contenido)


class TestStructureAnalyticsQuestion(unittest.TestCase):

    def setUp(self):
        self._key, self._http = ai_engine.GROQ_API_KEY, ai_engine._http_client
        ai_engine.GROQ_API_KEY = "clave-de-prueba"

    def tearDown(self):
        ai_engine.GROQ_API_KEY, ai_engine._http_client = self._key, self._http

    def test_catalogo_viaja_en_el_prompt_y_devuelve_eleccion(self):
        fake = FakeHttp({"metrica": "gasto_mes", "params": {"mes": "2026-09"}, "motivo": ""})
        ai_engine._http_client = fake
        res = ai_engine.structure_analytics_question(
            "¿cuánto gasté este mes?", metrics_catalog.catalogo_para_prompt())
        self.assertEqual(res, {"metrica": "gasto_mes", "params": {"mes": "2026-09"}, "motivo": ""})
        payload = fake.payloads[0]
        system = payload["messages"][0]["content"]
        for mid in metrics_catalog.CATALOGO:
            self.assertIn(mid, system)                       # el menú completo va al LLM
        self.assertIn("no decides la empresa", system.lower())
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertIn("¿cuánto gasté este mes?", payload["messages"][1]["content"])

    def test_el_llm_jamas_manda_la_empresa(self):
        """Cinturón doble del criterio 2: aunque el LLM cuele 'empresa',
        el normalizador la elimina antes de tocar el catálogo."""
        ai_engine._http_client = FakeHttp({
            "metrica": "gasto_mes",
            "params": {"mes": "2026-09", "empresa": 5, "portfolio_id": 9, "company": "X"},
            "motivo": "",
        })
        res = ai_engine.structure_analytics_question("gasto de Finanzas", "catálogo")
        self.assertEqual(res["params"], {"mes": "2026-09"})

    def test_no_entiendo_es_honesto(self):
        ai_engine._http_client = FakeHttp({
            "metrica": None, "params": {},
            "motivo": "El catálogo no tiene métricas de inventario.",
        })
        res = ai_engine.structure_analytics_question("¿cuántos tornillos hay en bodega?", "catálogo")
        self.assertIsNone(res["metrica"])
        self.assertIn("inventario", res["motivo"])

    def test_respuesta_no_dict_se_normaliza(self):
        ai_engine._http_client = FakeHttp({"metrica": ["lista", "rara"], "params": "no-dict"})
        res = ai_engine.structure_analytics_question("pregunta", "catálogo")
        self.assertIsNone(res["metrica"])
        self.assertEqual(res["params"], {})

    def test_pregunta_vacia(self):
        with self.assertRaises(ValueError):
            ai_engine.structure_analytics_question("   ", "catálogo")


RESULTADO_GASTO = {
    "metrica": "gasto_mes", "etiqueta": "Gasto del mes", "unidad": "COP",
    "valor": 7000000.0,
    "valores": [{"etiqueta": "Nómina", "valor": 5000000.0, "n_txs": 3},
                {"etiqueta": "Arriendo", "valor": 2000000.0, "n_txs": 1}],
    "origen": {"n_txs": 4, "desde": "2026-09-02", "hasta": "2026-09-14",
               "sello": "según 4 TXs de 2026-09-02 a 2026-09-14"},
    "detalle": {"mes": "2026-09", "agrupar_por": "categoria"},
    "portfolio_id": None,
}


class TestTextoRespuesta(unittest.TestCase):

    def test_formato_cop(self):
        self.assertEqual(_fmt_cop(1234567.4), "$1.234.567")
        self.assertEqual(_fmt_cop(-2500), "-$2.500")

    def test_gasto_con_sello(self):
        texto = _texto_respuesta(RESULTADO_GASTO)
        self.assertIn("$7.000.000", texto)
        self.assertIn("Nómina ($5.000.000)", texto)
        self.assertTrue(texto.endswith("— según 4 TXs de 2026-09-02 a 2026-09-14."))

    def test_nota_honesta_y_usd_en_el_sello(self):
        r = dict(RESULTADO_GASTO, nota="No hay gastos en COP registrados en 2026-01.",
                 origen=dict(RESULTADO_GASTO["origen"], usd_excluidas=2))
        texto = _texto_respuesta(r)
        self.assertIn("No hay gastos", texto)
        self.assertIn("2 TXs en USD excluidas", texto)

    def test_variacion_sin_base(self):
        r = {"metrica": "variacion_mensual", "etiqueta": "Variación",
             "valores": {"mes": "2026-09", "total_mes": 500.0, "mes_anterior": "2026-08",
                         "total_mes_anterior": 0.0, "delta": 500.0, "pct": None},
             "detalle": {"tipo": "GASTO"},
             "origen": {"sello": "según 2 TXs de 2026-08-01 a 2026-09-30"}}
        self.assertIn("sin base de comparación", _texto_respuesta(r))

    def test_conteo_terceros(self):
        r = {"metrica": "conteo_terceros", "etiqueta": "Conteo de terceros", "unidad": "terceros",
             "valor": 12,
             "valores": {"total_terceros": 12, "provisionales": 3, "con_movimiento": 8,
                         "mes": "2026-09"},
             "nota": "El total de terceros es global (los terceros no tienen empresa).",
             "origen": {"sello": "según 40 TXs de 2026-01-05 a 2026-09-14"}}
        texto = _texto_respuesta(r)
        self.assertIn("Terceros registrados: 12", texto)
        self.assertIn("3 con número provisional", texto)
        self.assertIn("Con movimiento en 2026-09: 8", texto)
        self.assertNotIn("$", texto.split("—")[0])           # conteo, jamás dinero
        self.assertIn("según 40 TXs", texto)


class TestGrafica(unittest.TestCase):

    def test_barras_png_real(self):
        b64 = _generar_grafica(RESULTADO_GASTO)
        self.assertIsNotNone(b64)
        png = base64.b64decode(b64)
        self.assertTrue(png.startswith(b"\x89PNG"), "el resultado debe ser un PNG real")

    def test_flujo_mensual_png(self):
        r = {"metrica": "flujo_mensual", "etiqueta": "Flujo mensual",
             "valores": [{"mes": "2026-08", "ingresos": 900.0, "gastos": 400.0, "neto": 500.0},
                         {"mes": "2026-09", "ingresos": 1200.0, "gastos": 700.0, "neto": 500.0}],
             "origen": {"sello": "según 8 TXs de 2026-08-01 a 2026-09-15"}}
        png = base64.b64decode(_generar_grafica(r))
        self.assertTrue(png.startswith(b"\x89PNG"))

    def test_sin_forma_graficable_devuelve_none_sin_reventar(self):
        self.assertIsNone(_generar_grafica({"metrica": "gasto_mes", "valores": []}))
        self.assertIsNone(_generar_grafica({"metrica": "desconocida", "valores": {"x": 1}}))


class TestResponderPregunta(unittest.TestCase):

    def setUp(self):
        self._structure = ai_engine.structure_analytics_question
        self._ejecutar = metrics_catalog.ejecutar_metrica
        self._registrar = analytics_log.registrar_pregunta
        self.registradas = []
        analytics_log.registrar_pregunta = (
            lambda *a, **kw: self.registradas.append((a, kw)) or True)

    def tearDown(self):
        ai_engine.structure_analytics_question = self._structure
        metrics_catalog.ejecutar_metrica = self._ejecutar
        analytics_log.registrar_pregunta = self._registrar

    def test_cadena_completa_con_empresa_del_backend(self):
        llamadas = {}
        ai_engine.structure_analytics_question = lambda p, c: {
            "metrica": "gasto_mes", "params": {"mes": "2026-09"}, "motivo": ""}

        def fake_ejecutar(mid, params, portfolio_id=None, conn=None):
            llamadas["args"] = (mid, params, portfolio_id)
            return dict(RESULTADO_GASTO, portfolio_id=portfolio_id)

        metrics_catalog.ejecutar_metrica = fake_ejecutar
        res = responder_pregunta("¿cuánto gasté?", portfolio_id=7)
        # La empresa viene del BACKEND (7), jamás de la elección del LLM
        self.assertEqual(llamadas["args"], ("gasto_mes", {"mes": "2026-09"}, 7))
        self.assertIn("según 4 TXs", res["texto"])
        self.assertEqual(res["metrica"], "gasto_mes")
        self.assertIsNotNone(res["grafica_png_base64"])
        self.assertEqual(res["datos"]["valor"], 7000000.0)

    def test_no_entiendo_dice_que_y_por_que_y_registra(self):
        ai_engine.structure_analytics_question = lambda p, c: {
            "metrica": None, "params": {},
            "motivo": "El catálogo no tiene métricas de inventario."}
        res = responder_pregunta("¿cuántos tornillos hay en bodega?", portfolio_id=3)
        # El texto dice QUÉ no se encontró y POR QUÉ (pedido 16-sep)
        self.assertIn("¿cuántos tornillos hay en bodega?", res["texto"])
        self.assertIn("El catálogo no tiene métricas de inventario.", res["texto"])
        self.assertIn("registrada", res["texto"])
        self.assertEqual(res["error"], "SIN_METRICA")
        self.assertIsNone(res["datos"])
        # Y quedó en la bitácora con su motivo y la empresa
        (args, kw), = self.registradas
        self.assertEqual(args[:2], ("¿cuántos tornillos hay en bodega?", "SIN_METRICA"))
        self.assertIn("inventario", args[2])
        self.assertEqual(kw.get("portfolio_id"), 3)

    def test_sin_red_es_claro_y_registra(self):
        def revienta(p, c):
            raise RuntimeError("❌ Error en Groq: [Errno 11001] getaddrinfo failed")
        ai_engine.structure_analytics_question = revienta
        res = responder_pregunta("¿cuánto gasté?")
        self.assertEqual(res["error"], "SIN_RED")
        self.assertIn("internet", res["texto"])
        self.assertIn("getaddrinfo", res["texto"])       # el error concreto, resumido
        self.assertNotIn("Traceback", res["texto"])
        (args, _kw), = self.registradas
        self.assertEqual(args[1], "SIN_RED")

    def test_error_de_catalogo_es_honesto_y_registra(self):
        ai_engine.structure_analytics_question = lambda p, c: {
            "metrica": "gasto_mes", "params": {"mes": "mal-formado"}, "motivo": ""}

        def fake_ejecutar(*a, **kw):
            raise ValueError("'mes' debe ser un mes YYYY-MM (recibí: 'mal-formado').")

        metrics_catalog.ejecutar_metrica = fake_ejecutar
        res = responder_pregunta("gasto del mes trece")
        self.assertIn("gasto_mes", res["texto"])          # qué entendió
        self.assertIn("YYYY-MM", res["texto"])            # por qué falló
        self.assertEqual(res["error"], "ERROR_CALCULO")
        self.assertIsNone(res["datos"])
        (args, kw), = self.registradas
        self.assertEqual(args[1], "ERROR_CALCULO")
        self.assertEqual(kw.get("metrica"), "gasto_mes")

    def test_respuesta_buena_no_registra_nada(self):
        ai_engine.structure_analytics_question = lambda p, c: {
            "metrica": "gasto_mes", "params": {}, "motivo": ""}
        metrics_catalog.ejecutar_metrica = lambda *a, **kw: dict(RESULTADO_GASTO)
        res = responder_pregunta("¿cuánto gasté?")
        self.assertNotIn("error", res)
        self.assertEqual(self.registradas, [])


class FakeConnLog:
    def __init__(self, cur, commit_falla=False):
        self._cur = cur
        self.commits = 0
        self.rollbacks = 0
        self._falla = commit_falla

    def cursor(self):
        return self._cur

    def commit(self):
        if self._falla:
            raise RuntimeError("commit caído")
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class CursorLog:
    def __init__(self):
        self.ejecutadas = []

    def execute(self, sql, params=None):
        self.ejecutadas.append((" ".join(sql.split()), list(params) if params else []))

    def fetchall(self):
        return []

    def close(self):
        pass


class TestBitacoraSQL(unittest.TestCase):

    def test_registrar_purga_e_inserta(self):
        cur = CursorLog()
        conn = FakeConnLog(cur)
        ok = analytics_log.registrar_pregunta(
            "total de terceros", "SIN_METRICA", "no hay métrica de terceros",
            portfolio_id=2, conn=conn)
        self.assertTrue(ok)
        self.assertEqual(conn.commits, 1)
        sql_purga, _ = cur.ejecutadas[0]
        self.assertIn("DELETE FROM analytics_question_log", sql_purga)
        self.assertIn("INTERVAL '30 days'", sql_purga)     # retención pactada
        sql_insert, params = cur.ejecutadas[1]
        self.assertIn("INSERT INTO analytics_question_log", sql_insert)
        self.assertEqual(params[0], "total de terceros")
        self.assertEqual(params[1], "SIN_METRICA")
        self.assertEqual(params[4], 2)

    def test_registrar_jamas_lanza(self):
        conn = FakeConnLog(CursorLog(), commit_falla=True)
        self.assertFalse(analytics_log.registrar_pregunta("x", "SIN_RED", conn=conn))
        self.assertEqual(conn.rollbacks, 1)

    def test_init_crea_tabla(self):
        cur = CursorLog()
        analytics_log.init_analytics_log_table(conn=FakeConnLog(cur))
        self.assertIn("CREATE TABLE IF NOT EXISTS analytics_question_log", cur.ejecutadas[0][0])


if __name__ == "__main__":
    unittest.main()
