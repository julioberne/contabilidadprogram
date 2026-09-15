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

    def tearDown(self):
        ai_engine.structure_analytics_question = self._structure
        metrics_catalog.ejecutar_metrica = self._ejecutar

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

    def test_no_entiendo_devuelve_motivo_sin_datos(self):
        ai_engine.structure_analytics_question = lambda p, c: {
            "metrica": None, "params": {}, "motivo": "Esa pregunta no está en el catálogo."}
        res = responder_pregunta("¿lloverá mañana?")
        self.assertEqual(res["texto"], "Esa pregunta no está en el catálogo.")
        self.assertIsNone(res["datos"])
        self.assertIsNone(res["grafica_png_base64"])

    def test_error_de_catalogo_es_honesto(self):
        ai_engine.structure_analytics_question = lambda p, c: {
            "metrica": "gasto_mes", "params": {"mes": "mal-formado"}, "motivo": ""}

        def fake_ejecutar(*a, **kw):
            raise ValueError("'mes' debe ser un mes YYYY-MM (recibí: 'mal-formado').")

        metrics_catalog.ejecutar_metrica = fake_ejecutar
        res = responder_pregunta("gasto del mes trece")
        self.assertIn("No pude calcularlo", res["texto"])
        self.assertIn("YYYY-MM", res["texto"])
        self.assertIsNone(res["datos"])


if __name__ == "__main__":
    unittest.main()
