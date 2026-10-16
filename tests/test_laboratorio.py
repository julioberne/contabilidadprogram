# -*- coding: utf-8 -*-
"""Laboratorio de rendimiento (scripts/laboratorio/): lógica pura, sin BD ni red.

    python -m unittest tests.test_laboratorio
"""
import os
import sys
import unittest
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (_ROOT, os.path.join(_ROOT, "scripts", "laboratorio"), os.path.join(_ROOT, "scripts", "carga")):
    if p not in sys.path:
        sys.path.insert(0, p)

import auditoria_codigo as aud  # noqa: E402
import carga_acotada as ca  # noqa: E402
import laboratorio as lab  # noqa: E402
import proyeccion as proy  # noqa: E402
from _seguro import exigir_no_produccion  # noqa: E402


class TestAuditoria(unittest.TestCase):
    def test_trinquete_solo_falla_con_ocurrencias_nuevas(self):
        base = {"monto-float": {"a.py": 2}}
        self.assertEqual(aud.comparar({"monto-float": {"a.py": 2}}, base), [])
        self.assertEqual(aud.comparar({"monto-float": {"a.py": 1}}, base), [], "bajar está permitido")
        nuevas = aud.comparar({"monto-float": {"a.py": 3, "b.py": 1}}, base)
        self.assertEqual({(n["archivo"], n["antes"], n["ahora"]) for n in nuevas}, {("a.py", 2, 3), ("b.py", 0, 1)})

    def test_get_sin_sesion(self):
        codigo = '''
@router.get("/api/abierta")
def abierta(x: int = 1):
    pass

@router.get("/api/cerrada")
def cerrada(_u: dict = Depends(require_auth)):
    pass

@router.get("/api/module-flags")
def publica():
    pass
'''
        self.assertEqual([h[1] for h in aud._gets_sin_sesion(codigo)], ["GET /api/abierta"])

    def test_patrones(self):
        import re
        r = {x.id: x for x in aud.REGLAS}
        casos = {
            "descarga-todas-tx": ("txs = obtener_transacciones(None)", "obtener_transacciones(portfolio)"),
            "catalogo-terceros-completo": ("fetch(`${API}/third-parties`)", "fetch(`${API}/third-parties/5/accounts`)"),
            "monto-float": ("float(tx.get('net_value') or 0)", "float(trm)"),
            "paginacion-offset": ("LIMIT %(limit)s OFFSET %(offset)s", "OFFSET 0"),
        }
        for rid, (si, no) in casos.items():
            with self.subTest(regla=rid):
                self.assertTrue(re.search(r[rid].patron, si, flags=re.I), si)
                self.assertFalse(re.search(r[rid].patron, no, flags=re.I), no)

    def test_linea_base_del_repo_pasa(self):
        """El código actual no tiene patrones nuevos frente a la línea base versionada."""
        base = aud.leer_linea_base()
        self.assertIsNotNone(base, "falta scripts/laboratorio/linea_base.json")
        self.assertEqual(aud.comparar(aud.conteos(aud.auditar()), base), [])


class TestCargaAcotada(unittest.TestCase):
    def test_topes_duros(self):
        usuarios, seg = ca.acotar([1, 50, 200], 600)
        self.assertEqual(usuarios, [1, 20, 20])
        self.assertEqual(seg, 60)

    def test_freno(self):
        rapido = [100.0] * 30
        self.assertIsNone(ca.debe_frenar(rapido, [200] * 30, 0.3))
        self.assertIn("p95", ca.debe_frenar([2000.0] * 30, [200] * 30, 0.3))
        self.assertIn("errores", ca.debe_frenar(rapido, [200] * 27 + [500] * 3, 0.3))
        self.assertIn("pool", ca.debe_frenar(rapido, [200] * 30, 0.8))
        self.assertIsNone(ca.debe_frenar([5000.0] * 5, [500] * 5, None), "pocas muestras: no frena")

    def test_horario(self):
        self.assertTrue(ca.en_horario_libre(datetime(2026, 10, 16, 23, 0)))
        self.assertTrue(ca.en_horario_libre(datetime(2026, 10, 16, 3, 0)))
        self.assertFalse(ca.en_horario_libre(datetime(2026, 10, 16, 13, 0)))

    def test_pausa_global(self):
        v = [(100.0, 10600, 200, "diario_opciones"), (100.4, 10620, 200, "diario_grupos"),
             (100.9, 10900, 200, "terceros_catalogo"), (130.0, 300, 200, "panel"), (150.0, 4000, 200, "panel")]
        p = ca.pausas_globales(v)
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["n"], 3)
        self.assertEqual(p[0]["endpoints"], ["diario_grupos", "diario_opciones", "terceros_catalogo"])
        self.assertEqual(ca.pausas_globales([(1.0, 9000, 200, "x"), (1.2, 9000, 200, "x")]), [],
                         "un solo endpoint lento no es pausa global")

    def test_solo_get(self):
        self.assertTrue(all(r.startswith("/api/") for _, _, r in ca.ESCENARIOS))
        import inspect
        self.assertIn('method="GET"', inspect.getsource(ca._get))


class TestProyeccion(unittest.TestCase):
    def test_modelo(self):
        planes = [{"consulta": "indexada", "ejecucion_ms": 5.0, "seq_scans": []},
                  {"consulta": "recorre", "ejecucion_ms": 5.0,
                   "seq_scans": [{"tabla": "transactions"}, {"tabla": "transactions"}, {"tabla": "portfolios"}]}]
        r = proy.proyectar(planes, n0=100, workers=2, pool_max=10, max_connections=60, escalas=(500_100,))
        self.assertEqual(r["conexiones_utiles"], 20)
        fila = r["escalas"][-1]
        self.assertEqual(fila["ms_por_consulta"]["indexada"], 5.0)
        self.assertAlmostEqual(fila["ms_por_consulta"]["recorre"], 5.0 + 2 * 2e-6 * 500_000 * 1000, places=1)
        self.assertEqual(fila["consulta_mas_lenta"], "recorre")
        qps = 20 / (fila["ms_por_consulta"]["recorre"] / 1000 + proy.SOBRECOSTO_S)
        self.assertAlmostEqual(fila["consultas_por_s"], round(qps, 1), places=1)

    def test_conexiones_recortadas_al_80(self):
        self.assertEqual(proy.conexiones_utiles(4, 20, 60), 48)

    def test_carga_util(self):
        u = proy.proyectar_carga_util({"analisis_dataset": 25.0}, {"analisis_dataset": 68})[0]
        self.assertEqual(u["excede_presupuesto_en"], 50_000)


class TestVeredicto(unittest.TestCase):
    def _carga(self, p95, ok_pct=100.0, frenado=None):
        return {"escalones": [{"usuarios": 10, "segundos": 20, "peticiones": 100, "goodput_ok_s": 5, "ok_pct": ok_pct,
                               "p95_interactivo_ms": p95, "n_interactivo": 10, "pausas_globales": [],
                               "endpoints": {"diario_busqueda": {"p95_ms": p95, "p50_ms": 50},
                                             "portafolios": {"p95_ms": 30, "p50_ms": 20}}}],
                "frenado": frenado}

    def _estado(self, filas, prefijo):
        return next(f["estado"] for f in filas if f["criterio"].startswith(prefijo))

    def test_latencia_neta_y_errores(self):
        d = {"carga": self._carga(250), "latencia_base_ms": 20}
        self.assertEqual(self._estado(lab.evaluar(d), "1."), lab.OK)
        d = {"carga": self._carga(2500, ok_pct=90.0), "latencia_base_ms": 20}
        filas = lab.evaluar(d)
        self.assertEqual(self._estado(filas, "1."), lab.CRITICO)
        self.assertEqual(self._estado(filas, "2."), lab.CRITICO)

    def test_trinquete_es_critico(self):
        d = {"auditoria": {"nuevas": [{"regla": "x", "archivo": "y"}], "total_alta": 0, "total_media": 0}}
        self.assertEqual(self._estado(lab.evaluar(d), "6."), lab.CRITICO)

    def test_tabla_sin_indice(self):
        d = {"observatorio": {"tablas": [{"tabla": "bot_messages", "filas": 1081, "recorridos_completos": 95000,
                                          "por_indice": 1400}], "estandar": {"planes": []}, "cache_hit_pct": 100}}
        self.assertEqual(self._estado(lab.evaluar(d), "4."), lab.ALERTA)


class TestGuardaVolumen(unittest.TestCase):
    PROD = "postgres.prodref123"

    def test_permite_local_y_lab(self):
        exigir_no_produccion("localhost", 56432, "postgres", prod_usuario=self.PROD)
        exigir_no_produccion("aws-1-us-east-2.pooler.supabase.com", 6543, "postgres.labref999", prod_usuario=self.PROD)

    def test_rechaza_produccion(self):
        for host, puerto, usuario in [("aws-1-us-east-2.pooler.supabase.com", 6543, self.PROD),
                                      ("aws-1-us-east-2.pooler.supabase.com", 6543, "postgres"),
                                      ("aws-1-us-east-2.pooler.supabase.com", 6543, ""),
                                      ("localhost", 6543, "postgres")]:
            with self.subTest(usuario=usuario, puerto=puerto), self.assertRaises(SystemExit):
                exigir_no_produccion(host, puerto, usuario, prod_usuario=self.PROD)


if __name__ == "__main__":
    unittest.main()
