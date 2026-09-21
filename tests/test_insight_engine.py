# -*- coding: utf-8 -*-
"""Análisis Inteligente hito 2 (B1) — insights automáticos (tests puros).

El motor NO calcula cifras: solo llama al catálogo (aquí, mockeado vía
insight_engine._ejecutar) y decide tarjetas. Se verifica:
  - reglas: variación fuerte → alerta; cartera vencida → alerta; datos
    sucios → info; todo bien → tarjetas "ok" (jamás silencio total con datos).
  - una métrica que falla NO tumba las demás (error honesto en "errores").
  - orden por severidad y sello de origen en toda tarjeta (criterio 3).
  - resumen_texto para Telegram y tick_resumen_telegram (reloj en la BD,
    apagado con ANALYTICS_RESUMEN_HORAS=0, best-effort jamás lanza).
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fin_sys_core"))

import insight_engine  # noqa: E402


def _r(metrica, valor=None, valores=None, sello="según 10 TXs de 2026-09-01 a 2026-09-15",
       n_txs=10, detalle=None, etiqueta=""):
    return {"metrica": metrica, "etiqueta": etiqueta or metrica, "valor": valor,
            "valores": valores, "detalle": detalle or {},
            "origen": {"n_txs": n_txs, "sello": sello}, "portfolio_id": None}


RESUMEN_OK = _r("resumen_periodo", 200000.0,
                {"ingresos": 1200000.0, "gastos": 1000000.0, "neto": 200000.0})
VARIACION_FUERTE = _r("variacion_mensual", 450000.0,
                      {"mes": "2026-09", "total_mes": 1450000.0, "mes_anterior": "2026-08",
                       "total_mes_anterior": 1000000.0, "delta": 450000.0, "pct": 45.0})
VARIACION_NORMAL = _r("variacion_mensual", 50000.0,
                      {"mes": "2026-09", "total_mes": 1050000.0, "mes_anterior": "2026-08",
                       "total_mes_anterior": 1000000.0, "delta": 50000.0, "pct": 5.0})
CARTERA_VENCIDA = _r("cartera_vencida", 4000000.0,
                     {"monto_vencido": 4000000.0, "n_vencidas": 3,
                      "monto_pendiente_total": 10000000.0, "n_pendientes": 10,
                      "pct_vencida": 40.0,
                      "clientes": [{"etiqueta": "Cliente Moroso SAS", "valor": 2500000.0}]})
CARTERA_AL_DIA = _r("cartera_vencida", 0.0,
                    {"monto_vencido": 0.0, "n_vencidas": 0,
                     "monto_pendiente_total": 3000000.0, "n_pendientes": 4,
                     "pct_vencida": 0.0, "clientes": []})
CALIDAD_SUCIA = _r("calidad_datos", None,
                   {"txs_total": 120, "txs_sin_categoria": 7, "txs_sin_evidencia": 30,
                    "terceros_numero_provisional": 4, "terceros_nombres_duplicados": 0})
CALIDAD_LIMPIA = _r("calidad_datos", None,
                    {"txs_total": 120, "txs_sin_categoria": 0, "txs_sin_evidencia": 0,
                     "terceros_numero_provisional": 0, "terceros_nombres_duplicados": 0})


def _fake_catalogo(fixtures):
    """→ función con la firma de insight_engine._ejecutar servida de fixtures."""
    def _ejecutar(metric_id, params=None, portfolio_id=None, conn=None):
        r = fixtures[metric_id]
        if isinstance(r, Exception):
            raise r
        return r
    return _ejecutar


ESCENARIO_ALERTAS = {"resumen_periodo": RESUMEN_OK, "variacion_mensual": VARIACION_FUERTE,
                     "cartera_vencida": CARTERA_VENCIDA, "calidad_datos": CALIDAD_SUCIA}
ESCENARIO_SANO = {"resumen_periodo": RESUMEN_OK, "variacion_mensual": VARIACION_NORMAL,
                  "cartera_vencida": CARTERA_AL_DIA, "calidad_datos": CALIDAD_LIMPIA}


class TestGenerarInsights(unittest.TestCase):

    def test_escenario_con_alertas(self):
        with patch.object(insight_engine, "_ejecutar", _fake_catalogo(ESCENARIO_ALERTAS)):
            data = insight_engine.generar_insights()
        por_id = {i["id"]: i for i in data["insights"]}
        self.assertEqual(data["errores"], [])
        # Gasto subió 45% (> umbral 30) → alerta con la cifra en %
        self.assertEqual(por_id["variacion_gasto"]["nivel"], "alerta")
        self.assertEqual(por_id["variacion_gasto"]["cifra"], "+45.0%")
        # Cartera vencida → alerta, cifra en COP y mayor deudor nombrado
        self.assertEqual(por_id["cartera_vencida"]["nivel"], "alerta")
        self.assertEqual(por_id["cartera_vencida"]["cifra"], "$4.000.000")
        self.assertIn("Cliente Moroso SAS", por_id["cartera_vencida"]["texto"])
        # Datos sucios → info con el desglose (el cero no se lista)
        self.assertEqual(por_id["datos_sucios"]["nivel"], "info")
        self.assertIn("7 TXs sin categoría", por_id["datos_sucios"]["texto"])
        self.assertIn("4 terceros provisionales", por_id["datos_sucios"]["texto"])
        self.assertNotIn("duplicados", por_id["datos_sucios"]["texto"])
        # Orden por severidad: las alertas van primero
        niveles = [i["nivel"] for i in data["insights"]]
        self.assertEqual(niveles, sorted(niveles, key=lambda n: {"alerta": 0, "info": 1, "ok": 2}[n]))
        # Criterio 3: toda tarjeta con sello
        for i in data["insights"]:
            self.assertIn("según", i["sello"])

    def test_escenario_sano_da_tarjetas_ok(self):
        with patch.object(insight_engine, "_ejecutar", _fake_catalogo(ESCENARIO_SANO)):
            data = insight_engine.generar_insights()
        ids = {i["id"] for i in data["insights"]}
        # Variación de 5% NO amerita tarjeta (señal, no ruido)
        self.assertNotIn("variacion_gasto", ids)
        self.assertEqual(ids, {"pulso_mes", "cartera_al_dia", "datos_limpios"})
        self.assertTrue(all(i["nivel"] == "ok" for i in data["insights"]))

    def test_variacion_sin_base_no_inventa(self):
        sin_base = dict(VARIACION_FUERTE)
        sin_base["valores"] = dict(sin_base["valores"], pct=None)
        with patch.object(insight_engine, "_ejecutar",
                          _fake_catalogo(dict(ESCENARIO_SANO, variacion_mensual=sin_base))):
            data = insight_engine.generar_insights()
        self.assertNotIn("variacion_gasto", {i["id"] for i in data["insights"]})

    def test_metrica_que_falla_no_tumba_las_demas(self):
        roto = dict(ESCENARIO_ALERTAS, cartera_vencida=RuntimeError("BD caída"))
        with patch.object(insight_engine, "_ejecutar", _fake_catalogo(roto)):
            data = insight_engine.generar_insights()
        self.assertEqual(len(data["errores"]), 1)
        self.assertIn("cartera", data["errores"][0])
        self.assertIn("BD caída", data["errores"][0])
        self.assertIn("variacion_gasto", {i["id"] for i in data["insights"]})


class TestResumenTexto(unittest.TestCase):

    def test_resumen_con_sellos_y_consolidado(self):
        with patch.object(insight_engine, "_ejecutar", _fake_catalogo(ESCENARIO_ALERTAS)):
            texto = insight_engine.resumen_texto(None)
        self.assertIn("resumen automático", texto)
        self.assertIn("⚠ El gasto subió fuerte", texto)
        self.assertIn("según 10 TXs", texto)                 # criterio 3 también por Telegram
        self.assertIn("Consolidado de todas las empresas", texto)


class CursorTick:
    def __init__(self, horas_desde_ultimo, chats):
        self._fetchones = [(horas_desde_ultimo,)]
        self._chats = [(c,) for c in chats]
        self.inserts = []

    def execute(self, sql, params=None):
        self._ultima = " ".join(sql.split())
        if "INSERT INTO bot_messages" in self._ultima:
            self.inserts.append(list(params))

    def fetchone(self):
        return self._fetchones.pop(0)

    def fetchall(self):
        return self._chats

    def close(self):
        pass


class ConnTick:
    def __init__(self, cur):
        self._cur = cur
        self.commits = 0

    def cursor(self):
        return self._cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


class TestTickResumenTelegram(unittest.TestCase):

    def setUp(self):
        patcher = patch.object(insight_engine, "_ejecutar", _fake_catalogo(ESCENARIO_SANO))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_envia_cuando_nunca_se_ha_enviado(self):
        cur = CursorTick(horas_desde_ultimo=None, chats=["111", "222"])
        enviados = []
        ok = insight_engine.tick_resumen_telegram(
            lambda chat, texto: enviados.append((chat, texto)) or 99,
            conn=ConnTick(cur))
        self.assertTrue(ok)
        self.assertEqual([c for c, _ in enviados], ["111", "222"])
        self.assertIn("resumen automático", enviados[0][1])
        # Marca de envío en bot_messages (kind resumen_analytics) por chat
        self.assertEqual(len(cur.inserts), 2)
        self.assertEqual(cur.inserts[0][1], insight_engine.RESUMEN_KIND)

    def test_no_reenvia_antes_de_tiempo(self):
        cur = CursorTick(horas_desde_ultimo=2.0, chats=["111"])   # default: cada 24h
        ok = insight_engine.tick_resumen_telegram(lambda *a: 99, conn=ConnTick(cur))
        self.assertFalse(ok)
        self.assertEqual(cur.inserts, [])

    def test_apagado_con_cero_horas(self):
        with patch.dict(os.environ, {"ANALYTICS_RESUMEN_HORAS": "0"}):
            ok = insight_engine.tick_resumen_telegram(lambda *a: 99, conn=None)
        self.assertFalse(ok)

    def test_sin_chats_vinculados_no_envia(self):
        cur = CursorTick(horas_desde_ultimo=None, chats=[])
        ok = insight_engine.tick_resumen_telegram(lambda *a: 99, conn=ConnTick(cur))
        self.assertFalse(ok)

    def test_jamas_lanza(self):
        class ConnRota:
            def cursor(self):
                raise RuntimeError("sin BD")

            def rollback(self):
                pass

        ok = insight_engine.tick_resumen_telegram(lambda *a: 99, conn=ConnRota())
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
