# -*- coding: utf-8 -*-
"""Análisis 13.5 — organizador contable 📦 (tests puros, sin base de datos).

Cubre el driver con un cursor falso (patrón FakeCursor de test_analytics_catalog)
y el router con TestClient (guards reales):
  · paquetes → hojas exactas; hojas a mano → 'personalizado' (CA-135-01)
  · folio EXP-AAAA-NNNN por secuencia; purga solo de lo GENERADO no fijado (CA-135-06)
  · huella de datos y vigencia: +TXs, TX eliminada (CA-135-10), asientos
  · generar: SHA-256 del contenido, nombre visible, folio en la carátula, empresa y período
  · subidas: tipo por contenido (firma), tope de tamaño, nombre seguro
  · vista previa de xlsx (fórmulas visibles) y csv
  · endpoints: 401 sin sesión, 403 sin rol, DELETE solo admin (CA-135-07), 503 sin migración

Ejecutar:  .venv\\Scripts\\python.exe -m unittest tests.test_accounting_files -v
"""
import hashlib
import io
import json
import os
import sys
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

from openpyxl import Workbook

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import fin_sys_core  # noqa: E402,F401  (un solo objeto por módulo)
from fin_sys_core import accounting_files_driver as drv  # noqa: E402
from fin_sys_core import export_xlsx as ex  # noqa: E402


# ── Cursor falso: cada execute consume una respuesta de la cola ───────────

class R:
    def __init__(self, *filas, rowcount=0):
        self.filas = list(filas)
        self.rowcount = rowcount


class FakeCursor:
    def __init__(self, *respuestas):
        self.ejecutadas = []
        self._cola = list(respuestas)
        self._actual = R()
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.ejecutadas.append((" ".join(sql.split()), params))
        self._actual = self._cola.pop(0) if self._cola else R()
        self.rowcount = self._actual.rowcount

    def fetchone(self):
        return self._actual.filas[0] if self._actual.filas else None

    def fetchall(self):
        return list(self._actual.filas)

    def close(self):
        pass

    def sql(self, i):
        return self.ejecutadas[i][0]


class FakeConn:
    def __init__(self, cur):
        self._cur = cur

    def cursor(self):
        return self._cur


def _xlsx_bytes(con_formula=True) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "LIBRO DIARIO"
    ws.append(["Fecha", "Cuenta", "Débito"])
    ws.append([date(2026, 9, 3), "110505", 1500.5])
    ws.append([date(2026, 9, 4), "413505", 200])
    if con_formula:
        ws.append(["", "TOTAL", "=SUM(C2:C3)"])
    wb.create_sheet("MAYOR").append(["x"])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


HUELLA = {"n_txs": 10, "suma_neto": "1000.00", "max_tx": 90, "n_lineas": 20,
          "debitos": "1000.00", "max_linea": 400}


# ══ Paquetes y receta ═════════════════════════════════════════════════════

class TestPaquetes(unittest.TestCase):

    def test_libro_completo_son_todas_las_hojas_del_motor(self):
        self.assertEqual(drv.HOJAS_COMPLETO, [h for h in ex.HOJAS_PERIODO if h != "caratula"])

    def test_cada_paquete_genera_exactamente_sus_hojas(self):
        for clave, p in drv.PAQUETES.items():
            r_in, k = drv.preparar_receta({"modo": "periodo", "hasta": "2026-09-30"}, clave)
            r = ex.normalizar_receta(r_in)
            self.assertEqual(set(r["hojas"]) - {"caratula"}, set(p["hojas"]), clave)
            self.assertEqual(r["hojas"][0], "caratula")
            self.assertEqual(drv.paquete_efectivo(k, r), clave)

    def test_hojas_a_mano_quedan_personalizado_y_solo_lo_marcado(self):
        r_in, k = drv.preparar_receta({"hojas": "diario,mayor", "hasta": "2026-09-30"}, "cierre_mes")
        r = ex.normalizar_receta(r_in)
        self.assertEqual(r["hojas"], ["caratula", "diario", "mayor"])
        self.assertEqual(drv.paquete_efectivo(k, r), drv.PAQUETE_LIBRE)

    def test_sin_paquete_es_personalizado(self):
        _, k = drv.preparar_receta({"hojas": ["impuestos"]}, None)
        self.assertEqual(k, drv.PAQUETE_LIBRE)

    def test_modo_transacciones_es_relacion(self):
        _, k = drv.preparar_receta({"modo": "transacciones", "tx_ids": [1]}, "cierre_mes")
        self.assertEqual(k, drv.PAQUETE_RELACION)

    def test_paquete_desconocido(self):
        with self.assertRaises(ValueError):
            drv.preparar_receta({}, "cierre_anual")

    def test_receta_guardable_sin_folio_y_con_fechas_iso(self):
        r = ex.normalizar_receta({"portfolio_id": 3, "desde": "2026-09-01", "hasta": "2026-09-30",
                                  "folio": "EXP-2026-0001"})
        g = drv.receta_json(r, "mes_anterior")
        self.assertNotIn("folio", g)
        self.assertEqual((g["desde"], g["hasta"], g["relativo"]), ("2026-09-01", "2026-09-30", "mes_anterior"))
        json.dumps(g)   # serializable


class TestEtiquetas(unittest.TestCase):

    def test_periodos_legibles(self):
        e = drv.etiqueta_periodo
        self.assertEqual(e(date(2026, 9, 1), date(2026, 9, 30)), "sep 2026")
        self.assertEqual(e(date(2026, 1, 1), date(2026, 12, 31)), "año 2026")
        self.assertEqual(e(date(2026, 7, 1), date(2026, 9, 30)), "T3 2026")
        self.assertEqual(e(date(2026, 9, 5), date(2026, 9, 20)), "05/09/2026 – 20/09/2026")
        self.assertEqual(e(None, date(2026, 9, 30)), "hasta 30/09/2026")
        self.assertEqual(e(date(2026, 2, 1), date(2026, 2, 28)), "feb 2026")

    def test_nombre_por_defecto(self):
        r = {"modo": "periodo", "desde": date(2026, 9, 1), "hasta": date(2026, 9, 30)}
        datos = {"empresas": [{"nombre": "Pegasus"}]}
        self.assertEqual(drv.nombre_por_defecto("cierre_mes", r, datos), "Cierre de mes · Pegasus · sep 2026")
        self.assertEqual(drv.nombre_por_defecto("banco", r, {"empresas": []}),
                         "Banco / crédito · Consolidado · sep 2026")
        self.assertEqual(drv.nombre_por_defecto("relacion", {"modo": "transacciones"}, {"txs": [{}, {}, {}]}),
                         "Relación de 3 transacciones")


# ══ Huella y vigencia (§4.6) ══════════════════════════════════════════════

class TestHuella(unittest.TestCase):

    def test_alcances(self):
        self.assertEqual(drv.alcance_de_receta({"modo": "periodo", "portfolios": [3], "desde": "2026-09-01",
                                                "hasta": "2026-09-30"}),
                         {"pids": [3], "desde": "2026-09-01", "hasta": "2026-09-30"})
        self.assertEqual(drv.alcance_de_receta({"portfolios": [], "hasta": "2026-09-30"})["pids"], None)
        self.assertEqual(drv.alcance_de_receta({"modo": "transacciones", "tx_ids": [9, 2, 9]}),
                         {"tx_ids": [2, 9]})

    def test_calcula_n_alcances_en_una_consulta(self):
        cur = FakeCursor(R((0, 10, 1000, 90, None, 20, 1000, 400),
                           (1, 2, 50.5, 12, [7, 12], 4, 50.5, 33)))
        hs = drv.calcular_huellas(cur, [{"pids": [3], "desde": "2026-09-01", "hasta": "2026-09-30"},
                                        {"tx_ids": [7, 12, 15]}])
        self.assertEqual(len(cur.ejecutadas), 1)
        sql, params = cur.ejecutadas[0]
        self.assertIn("jsonb_to_recordset", sql)
        self.assertIn("estado IN ('CONTABILIZADO', 'ANULADO')", sql)
        payload = json.loads(params[0])
        self.assertEqual(payload[1]["tx_ids"], [7, 12, 15])
        self.assertEqual(hs[0], HUELLA)
        self.assertNotIn("tx_vivas", hs[0])
        self.assertEqual(hs[1]["tx_vivas"], [7, 12])
        self.assertEqual(hs[1]["suma_neto"], "50.50")

    def test_sin_alcances_no_consulta(self):
        cur = FakeCursor()
        self.assertEqual(drv.calcular_huellas(cur, []), [])
        self.assertEqual(cur.ejecutadas, [])

    def test_igual_es_vigente(self):
        self.assertEqual(drv.comparar_huella(HUELLA, dict(HUELLA)), ("VIGENTE", []))

    def test_tx_nuevas_en_el_rango(self):
        ahora = {**HUELLA, "n_txs": 13, "max_tx": 95, "n_lineas": 26, "max_linea": 410, "debitos": "1200.00"}
        estado, det = drv.comparar_huella(HUELLA, ahora)
        self.assertEqual(estado, "CAMBIO")
        self.assertIn("+3 TX(s) registrada(s) después", det)
        self.assertIn("los asientos en libros cambiaron (+6 líneas)", det)

    def test_valor_editado_mismas_txs(self):
        estado, det = drv.comparar_huella(HUELLA, {**HUELLA, "suma_neto": "1250.00"})
        self.assertEqual(estado, "CAMBIO")
        self.assertEqual(det, ["cambió el valor neto del período: 1.000,00 → 1.250,00"])

    def test_relacion_con_tx_eliminada(self):   # CA-135-10
        antes = {**HUELLA, "tx_vivas": [7, 12, 15]}
        ahora = {**HUELLA, "tx_vivas": [7, 15], "suma_neto": "800.00"}
        estado, det = drv.comparar_huella(antes, ahora)
        self.assertEqual(estado, "CAMBIO")
        self.assertEqual(det, ["la TX #12 se eliminó"])

    def test_sin_huella(self):
        self.assertEqual(drv.comparar_huella(None, HUELLA), ("SIN_HUELLA", []))

    def test_vigencias_solo_de_generados(self):
        filas = [{"id": 1, "origen": "GENERADO", "receta": {"modo": "periodo", "hasta": "2026-09-30"},
                  "huella_datos": HUELLA},
                 {"id": 2, "origen": "SUBIDO", "receta": None, "huella_datos": None}]
        cur = FakeCursor(R((0, 11, 1100, 91, None, 20, 1000, 400)))
        v = drv._vigencias(cur, filas)
        self.assertEqual(list(v), [1])
        self.assertEqual(v[1]["estado"], "CAMBIO")


# ══ Folio y purga ═════════════════════════════════════════════════════════

class TestFolioYPurga(unittest.TestCase):

    def test_folio_por_secuencia(self):
        cur = FakeCursor(R((7,)))
        self.assertEqual(drv.siguiente_folio(cur, 2026), "EXP-2026-0007")
        self.assertIn("nextval('accounting_files_folio_seq')", cur.sql(0))
        self.assertEqual(drv.siguiente_folio(FakeCursor(R((12345,))), 2027), "EXP-2027-12345")

    def test_purga_jamas_toca_fijados_ni_subidos(self):   # CA-135-06
        cur = FakeCursor(R(rowcount=4))
        self.assertEqual(drv.purgar(cur), 4)
        sql, params = cur.ejecutadas[0]
        self.assertTrue(sql.startswith("DELETE FROM accounting_files"))
        self.assertIn("origen = 'GENERADO'", sql)
        self.assertIn("NOT fijado", sql)
        self.assertIn("creado_en < NOW() - make_interval(days => %s)", sql)
        self.assertEqual(params, (drv.RETENCION_DIAS,))
        self.assertEqual(drv.RETENCION_DIAS, 90)


# ══ Subidas ═══════════════════════════════════════════════════════════════

class TestSubida(unittest.TestCase):

    def test_tipo_por_contenido(self):
        d = drv.detectar_tipo
        self.assertEqual(d(b"%PDF-1.7 ...", "extracto.pdf"), (drv.MIME_PDF, "pdf"))
        self.assertEqual(d(b"%PDF-1.4 ...", "sin_extension"), (drv.MIME_PDF, "pdf"))
        self.assertEqual(d(b"\x89PNG\r\n\x1a\nxxxx", "a.png"), (drv.MIME_PNG, "png"))
        self.assertEqual(d(b"\xff\xd8\xff\xe0xxxx", "foto.jpeg"), (drv.MIME_JPG, "jpg"))
        self.assertEqual(d(_xlsx_bytes(), "libro.xlsx"), (drv.MIME_XLSX, "xlsx"))
        self.assertEqual(d("fecha;valor\n2026-09-01;100\n".encode(), "movs.csv"), (drv.MIME_CSV, "csv"))

    def test_rechazos(self):
        d = drv.detectar_tipo
        for contenido, nombre in ((b"MZ\x90\x00", "virus.exe"), (b"PK\x03\x04basura", "x.xlsx"),
                                  (b"PK\x03\x04basura", "x.zip"), (b"texto plano", "nota.txt"),
                                  (b"a,b\x00c", "bin.csv"), (b"", "vacio.pdf")):
            with self.assertRaises(ValueError, msg=nombre):
                d(contenido, nombre)

    def test_tope_de_tamano(self):
        with mock.patch.object(drv, "MAX_BYTES", 10):
            with self.assertRaisesRegex(ValueError, "tope"):
                drv.detectar_tipo(b"%PDF-" + b"x" * 20, "grande.pdf")

    def test_nombre_seguro(self):
        self.assertEqual(drv._nombre_seguro("C:\\Users\\x\\Extracto sep.PDF", "pdf"), "Extracto sep.pdf")
        self.assertEqual(drv._nombre_seguro('../../etc/"pass"<>.csv', "csv"), "pass.csv")
        self.assertEqual(drv._nombre_seguro("libro.xlsx.exe", "pdf"), "libro.xlsx.pdf")
        self.assertEqual(drv._nombre_seguro("", "png"), "documento.png")

    def test_subir_archiva_como_subido_en_soportes(self):
        cur = FakeCursor(R((7,)),                     # id del tipo 'soportes'
                         R(rowcount=0),               # purga
                         R((55, datetime(2026, 10, 5, 10, 0))))
        out = drv.subir(b"%PDF-1.7 extracto", "Extracto Bancolombia.pdf",
                        {"anio": "2026", "mes": "9", "nota": "septiembre"},
                        usuario={"name": "Andrés", "uid": "1"}, conn=FakeConn(cur))
        self.assertEqual(out["id"], 55)
        self.assertEqual(out["nombre"], "Extracto Bancolombia")
        self.assertEqual(out["sha256"], hashlib.sha256(b"%PDF-1.7 extracto").hexdigest())
        self.assertIn("WHERE clave = %s", cur.sql(0))
        self.assertEqual(cur.ejecutadas[0][1], ("soportes",))
        sql, p = cur.ejecutadas[2]
        self.assertIn("VALUES ('SUBIDO'", sql)
        self.assertEqual(p[2], 7)                                       # tipo
        self.assertEqual((p[4], p[5]), (date(2026, 9, 1), date(2026, 9, 30)))
        self.assertEqual((p[8], p[9]), (drv.MIME_PDF, len(b"%PDF-1.7 extracto")))
        self.assertEqual((p[11], p[12]), ("Andrés", "septiembre"))

    def test_periodo_de_subida(self):
        self.assertEqual(drv._periodo_mes(None, None), (None, None))
        self.assertEqual(drv._periodo_mes(2026, None), (date(2026, 1, 1), date(2026, 12, 31)))
        with self.assertRaises(ValueError):
            drv._periodo_mes(None, 9)
        with self.assertRaises(ValueError):
            drv._periodo_mes(2026, 13)


# ══ Generar (motor simulado) ══════════════════════════════════════════════

SELLO = {"n_txs": 4, "n_asientos": 4, "hojas": ["CARÁTULA", "LIBRO DIARIO"], "empresas": [],
         "rango_real": {"desde": "03/09/2026", "hasta": "28/09/2026"},
         "totales_control": {"cuadra": True}, "advertencias": []}


class TestGenerar(unittest.TestCase):

    def setUp(self):
        self.vistos = []

        def construir(datos, r, usuario=None, ahora=None):
            self.vistos.append(dict(r))
            return b"PK\x03\x04-libro-" + (r["folio"] or "").encode(), dict(SELLO, nombre=r["nombre"])

        self.parches = [
            mock.patch.object(ex, "recolectar", return_value={
                "empresas": [{"id": 3, "nombre": "Pegasus", "portafolio": "Negocio A", "nit": ""}],
                "txs": [{"id": 1}, {"id": 2}]}),
            mock.patch.object(ex, "construir_libro", side_effect=construir),
            mock.patch.object(ex, "hoy_colombia", return_value=date(2026, 10, 5)),
        ]
        for p in self.parches:
            p.start()

    def tearDown(self):
        for p in self.parches:
            p.stop()

    def test_cierre_de_mes_archiva_con_folio_sha_y_huella(self):
        cur = FakeCursor(R((0, 10, 1000, 90, None, 20, 1000, 400)),   # huella
                         R((7,)),                                     # nextval
                         R((1,)),                                     # tipo 'libros'
                         R(rowcount=2),                               # purga
                         R((101, datetime(2026, 10, 5, 9, 30))))      # INSERT
        out = drv.generar({"portfolio_id": 3, "desde": "2026-09-01", "hasta": "2026-09-30"},
                          {"name": "Andrés", "role": "owner"}, paquete="cierre_mes", conn=FakeConn(cur))
        self.assertEqual(out["folio"], "EXP-2026-0007")
        self.assertEqual(out["nombre"], "Cierre de mes · Pegasus · sep 2026")
        self.assertEqual(out["purgados"], 2)
        contenido = b"PK\x03\x04-libro-EXP-2026-0007"
        self.assertEqual(out["sha256"], hashlib.sha256(contenido).hexdigest())
        # La carátula lleva el folio y el nombre visible.
        self.assertEqual(self.vistos[-1]["folio"], "EXP-2026-0007")
        self.assertEqual(self.vistos[-1]["nombre"], "Cierre de mes · Pegasus · sep 2026")
        self.assertTrue(out["nombre_archivo"].startswith("EXP-2026-0007_FINSYS_PEGASUS_2026-09-01_2026-09-30"))
        # La huella se toma ANTES del folio (falsa alarma > falsa tranquilidad).
        self.assertIn("jsonb_to_recordset", cur.sql(0))
        self.assertIn("nextval", cur.sql(1))
        sql, p = cur.ejecutadas[4]
        self.assertIn("INSERT INTO accounting_files", sql)
        (folio, nombre, nombre_archivo, tipo, paquete, receta, pid, desde, hasta, folder, archivo, mime,
         tamano, sha, hojas, sello, huella, quien, reemplaza) = p
        self.assertEqual((tipo, paquete, pid, folder, reemplaza), (1, "cierre_mes", 3, None, None))
        self.assertEqual((desde, hasta), (date(2026, 9, 1), date(2026, 9, 30)))
        self.assertEqual((archivo, mime, tamano), (contenido, drv.MIME_XLSX, len(contenido)))
        self.assertNotIn("folio", json.loads(receta))
        self.assertIsNone(json.loads(receta)["nombre"])   # el visible no se guarda: regenerar lo deriva
        self.assertEqual(json.loads(huella), HUELLA)
        self.assertEqual(quien, "Andrés")

    def test_relacion_toma_empresa_y_periodo_de_las_txs(self):
        cur = FakeCursor(R((0, 2, 50, 12, [7, 12], 4, 50, 33)),       # huella
                         R((3,)),                                     # empresas de las TXs
                         R((8,)), R((6,)), R(rowcount=0),
                         R((102, datetime(2026, 10, 5, 9, 31))))
        out = drv.generar({"modo": "transacciones", "tx_ids": [7, 12], "nombre": "Viaje Medellín"},
                          {"name": "Andrés"}, conn=FakeConn(cur))
        self.assertEqual(out["paquete"], "relacion")
        self.assertEqual(out["nombre"], "Viaje Medellín")
        self.assertIn("FINSYS_RELACION_VIAJE-MEDELLIN", out["nombre_archivo"])
        self.assertIn("nextval", cur.sql(2))
        self.assertEqual(cur.ejecutadas[3][1], ("relaciones",))
        p = cur.ejecutadas[5][1]
        self.assertEqual((p[6], p[7], p[8]), (3, date(2026, 9, 3), date(2026, 9, 28)))
        self.assertEqual(json.loads(p[16])["tx_vivas"], [7, 12])

    def test_libro_sobre_el_tope_no_se_archiva(self):
        cur = FakeCursor(R((0, 1, 1, 1, None, 1, 1, 1)), R((9,)))
        with mock.patch.object(drv, "MAX_BYTES", 5):
            with self.assertRaisesRegex(ValueError, "tope"):
                drv.generar({"hasta": "2026-09-30"}, {}, paquete="completo", conn=FakeConn(cur))
        self.assertFalse(any("INSERT" in s for s, _ in cur.ejecutadas))

    def test_carpeta_inexistente_falla_antes_de_gastar_folio(self):
        cur = FakeCursor(R())   # SELECT 1 FROM accounting_folders → nada
        with self.assertRaisesRegex(ValueError, "carpeta 99 no existe"):
            drv.generar({"hasta": "2026-09-30"}, {}, paquete="banco", folder_id=99, conn=FakeConn(cur))
        self.assertFalse(any("nextval" in s for s, _ in cur.ejecutadas))

    def test_regenerar_crea_folio_nuevo_que_reemplaza(self):   # CA-135-05
        receta = drv.receta_json(ex.normalizar_receta(
            {"portfolio_id": 3, "desde": "2026-09-01", "hasta": "2026-09-30",
             "hojas": drv.PAQUETES["cierre_mes"]["hojas"]}))
        cur = FakeCursor(R(("GENERADO", receta, "cierre_mes", 4, 1)))
        with mock.patch.object(drv, "generar", return_value={"id": 120, "folio": "EXP-2026-0020"}) as g:
            out = drv.regenerar(101, {"name": "Andrés"}, conn=FakeConn(cur))
        self.assertEqual(out["folio"], "EXP-2026-0020")
        kw = g.call_args.kwargs
        self.assertEqual((kw["paquete"], kw["folder_id"], kw["tipo_documental_id"], kw["reemplaza_a"]),
                         ("cierre_mes", 4, 1, 101))
        self.assertEqual(g.call_args.args[0]["desde"], "2026-09-01")

    def test_regenerar_subido_o_inexistente(self):
        with self.assertRaises(ValueError):
            drv.regenerar(5, conn=FakeConn(FakeCursor(R(("SUBIDO", None, None, None, 7)))))
        with self.assertRaises(drv.NoEncontrado):
            drv.regenerar(5, conn=FakeConn(FakeCursor(R())))


# ══ Vista previa ══════════════════════════════════════════════════════════

class TestVistaPrevia(unittest.TestCase):

    def test_xlsx_muestra_filas_y_formulas(self):
        v = drv.vista_xlsx(_xlsx_bytes(), None, 50)
        self.assertEqual(v["hojas"], ["LIBRO DIARIO", "MAYOR"])
        self.assertEqual(v["hoja"], "LIBRO DIARIO")
        self.assertEqual(v["filas"][0], ["Fecha", "Cuenta", "Débito"])
        self.assertEqual(v["filas"][1], ["2026-09-03", "110505", 1500.5])
        self.assertEqual(v["filas"][3][2], "=SUM(C2:C3)")
        self.assertFalse(v["mas_filas"])

    def test_xlsx_limite_y_hoja(self):
        v = drv.vista_xlsx(_xlsx_bytes(), "LIBRO DIARIO", 2)
        self.assertEqual(len(v["filas"]), 2)
        self.assertTrue(v["mas_filas"])
        self.assertEqual(drv.vista_xlsx(_xlsx_bytes(), "MAYOR", 5)["filas"], [["x"]])

    def test_csv_con_punto_y_coma(self):
        v = drv.vista_csv("fecha;valor\n2026-09-01;100\n".encode("utf-8-sig"))
        self.assertEqual(v["filas"], [["fecha", "valor"], ["2026-09-01", "100"]])

    def test_pdf_va_como_binario(self):
        cur = FakeCursor(R((memoryview(b"%PDF-1.7"), drv.MIME_PDF, "extracto.pdf")))
        v = drv.vista_previa(9, conn=FakeConn(cur))
        self.assertEqual((v["tipo"], v["contenido"]), ("binario", b"%PDF-1.7"))


# ══ Listado ═══════════════════════════════════════════════════════════════

class TestListar(unittest.TestCase):

    def test_filtros_y_vigencia_en_lote(self):
        fila = (1, "GENERADO", "EXP-2026-0001", "Cierre", "EXP.xlsx", 1, "cierre_mes", 3, "Pegasus",
                "Negocio A", date(2026, 9, 1), date(2026, 9, 30), None, drv.MIME_XLSX, 1000, "a" * 64,
                ["CARÁTULA"], "Andrés", datetime(2026, 10, 1, 8, 0), False, None, 0, None, None,
                {"modo": "periodo", "portfolios": [3], "desde": "2026-09-01", "hasta": "2026-09-30"}, HUELLA)
        cur = FakeCursor(R((1,)), R(fila), R((0, 10, 1000, 90, None, 20, 1000, 400)))
        out = drv.listar({"portfolio_id": 3, "anio": 2026, "mes": 9, "q": "50%_"}, conn=FakeConn(cur))
        sql_count, p = cur.ejecutadas[0]
        self.assertIn("f.portfolio_id = %s", sql_count)
        self.assertEqual(p, [3, 2026, 9] + ["%50\\%\\_%"] * 4)
        item = out["items"][0]
        self.assertEqual(out["total"], 1)
        self.assertEqual(item["vigencia"], {"estado": "VIGENTE", "detalles": []})
        self.assertEqual(item["empresa"], "Pegasus")
        self.assertEqual(item["vence_el"], (datetime(2026, 10, 1) + timedelta(days=90)).date().isoformat())
        self.assertNotIn("receta", item)
        self.assertNotIn("huella_datos", item)
        self.assertEqual(len(cur.ejecutadas), 3)   # conteo + página + UNA de vigencia

    def test_consolidado_es_portfolio_cero(self):
        where, params = drv._where({"portfolio_id": 0, "tipo": 0})
        self.assertIn("f.portfolio_id IS NULL", where)
        self.assertIn("f.tipo_documental_id IS NULL", where)
        self.assertEqual(params, [])


# ══ Endpoints (guards reales) ═════════════════════════════════════════════

class _PgError(Exception):
    pgcode = "42P01"


class TestRouter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers.accounting_files import router
        from routers.auth_guard import create_session_token
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

        def token(role):
            return {"Authorization": "Bearer " + create_session_token({"id": 1, "name": "Prueba", "role": role})}
        cls.contador, cls.member, cls.owner = token("contador"), token("member"), token("owner")

    RUTAS = [("post", "/api/analytics/export/preflight"), ("post", "/api/analytics/export"),
             ("get", "/api/analytics/export/paquetes"), ("post", "/api/analytics/export/paquetes"),
             ("delete", "/api/analytics/export/paquetes/1"),
             ("get", "/api/accounting-files"), ("get", "/api/accounting-files/resumen"),
             ("get", "/api/accounting-files/cierres?anio=2026"), ("post", "/api/accounting-files/upload"),
             ("get", "/api/accounting-files/1"), ("get", "/api/accounting-files/1/download"),
             ("get", "/api/accounting-files/1/preview"), ("patch", "/api/accounting-files/1"),
             ("post", "/api/accounting-files/1/regenerar"), ("delete", "/api/accounting-files/1"),
             ("get", "/api/accounting-folders"), ("post", "/api/accounting-folders"),
             ("patch", "/api/accounting-folders/1"), ("delete", "/api/accounting-folders/1"),
             ("get", "/api/accounting-doc-types"), ("post", "/api/accounting-doc-types"),
             ("patch", "/api/accounting-doc-types/1"), ("delete", "/api/accounting-doc-types/1")]

    def test_sin_sesion_todo_401(self):   # CA-135-07
        for metodo, ruta in self.RUTAS:
            self.assertEqual(getattr(self.client, metodo)(ruta).status_code, 401, f"{metodo} {ruta}")

    def test_rol_member_403(self):
        for metodo, ruta in self.RUTAS:
            r = getattr(self.client, metodo)(ruta, headers=self.member)
            self.assertEqual(r.status_code, 403, f"{metodo} {ruta}")

    def test_borrar_es_solo_admin(self):   # CA-135-07
        for ruta in ("/api/accounting-files/1", "/api/accounting-folders/1", "/api/accounting-doc-types/1",
                     "/api/analytics/export/paquetes/1"):
            self.assertEqual(self.client.delete(ruta, headers=self.contador).status_code, 403, ruta)
        with mock.patch.object(drv, "eliminar", return_value={"eliminado": True, "id": 1}):
            self.assertEqual(self.client.delete("/api/accounting-files/1", headers=self.owner).status_code, 200)

    def test_rutas_fijas_no_chocan_con_el_id(self):
        with mock.patch.object(drv, "resumen", return_value={"archivos": 0}) as m:
            r = self.client.get("/api/accounting-files/resumen", headers=self.contador)
        self.assertEqual((r.status_code, r.json()), (200, {"archivos": 0}))
        m.assert_called_once()

    def test_errores_del_driver(self):
        casos = [(ValueError("mala receta"), 400), (drv.NoEncontrado("no"), 404),
                 (drv.Conflicto("repetido"), 409), (_PgError("relation does not exist"), 503)]
        for error, codigo in casos:
            with mock.patch.object(drv, "ficha", side_effect=error):
                r = self.client.get("/api/accounting-files/1", headers=self.contador)
            self.assertEqual(r.status_code, codigo, repr(error))
        with mock.patch.object(drv, "ficha", side_effect=_PgError("x")):
            self.assertIn("migrate_exports", self.client.get("/api/accounting-files/1",
                                                             headers=self.contador).json()["detail"])

    def test_descarga_entrega_los_bytes_y_el_sha(self):
        a = {"contenido": b"PK-libro", "mime_type": drv.MIME_XLSX, "sha256": "f" * 64,
             "nombre_archivo": "EXP-2026-0007_Cierre año.xlsx"}
        with mock.patch.object(drv, "descargar", return_value=a):
            r = self.client.get("/api/accounting-files/7/download", headers=self.contador)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"PK-libro")
        self.assertEqual(r.headers["x-finsys-sha256"], "f" * 64)
        self.assertIn("attachment;", r.headers["content-disposition"])
        self.assertIn("filename*=UTF-8''EXP-2026-0007_Cierre%20a%C3%B1o.xlsx", r.headers["content-disposition"])
        self.assertEqual(r.headers["cache-control"], "no-store")

    def test_preview_pdf_inline_y_tabla_json(self):
        with mock.patch.object(drv, "vista_previa", return_value={
                "tipo": "binario", "contenido": b"%PDF-1.7", "mime_type": drv.MIME_PDF, "nombre_archivo": "e.pdf"}):
            r = self.client.get("/api/accounting-files/9/preview", headers=self.contador)
        self.assertEqual((r.status_code, r.content), (200, b"%PDF-1.7"))
        self.assertTrue(r.headers["content-disposition"].startswith("inline;"))
        tabla = {"tipo": "tabla", "hojas": ["A"], "hoja": "A", "columnas": 1, "filas": [["x"]], "mas_filas": False}
        with mock.patch.object(drv, "vista_previa", return_value=tabla) as m:
            r = self.client.get("/api/accounting-files/9/preview?hoja=A&limite=10", headers=self.contador)
        self.assertEqual(r.json(), tabla)
        m.assert_called_once_with(9, "A", 10)

    def test_subida_multipart_y_tope(self):
        with mock.patch.object(drv, "subir", return_value={"id": 3}) as m:
            r = self.client.post("/api/accounting-files/upload", headers=self.contador,
                                 files={"archivo": ("extracto.pdf", b"%PDF-1.7", "application/pdf")},
                                 data={"anio": "2026", "mes": "9", "tipo_documental_id": "5"})
        self.assertEqual((r.status_code, r.json()), (200, {"id": 3}))
        contenido, nombre, meta = m.call_args.args
        self.assertEqual((contenido, nombre, meta["anio"], meta["mes"], meta["tipo_documental_id"]),
                         (b"%PDF-1.7", "extracto.pdf", 2026, 9, 5))
        with mock.patch.object(drv, "MAX_BYTES", 4):
            r = self.client.post("/api/accounting-files/upload", headers=self.contador,
                                 files={"archivo": ("x.pdf", b"%PDF-1.7", "application/pdf")})
        self.assertEqual(r.status_code, 413)

    def test_exportar_pasa_receta_y_destino(self):
        with mock.patch.object(drv, "generar", return_value={"id": 1, "folio": "EXP-2026-0001"}) as m:
            r = self.client.post("/api/analytics/export", headers=self.contador,
                                 json={"receta": {"portfolio_id": 3, "hasta": "2026-09-30"},
                                       "paquete": "cierre_mes", "folder_id": 2})
        self.assertEqual(r.json()["folio"], "EXP-2026-0001")
        self.assertEqual(m.call_args.kwargs["paquete"], "cierre_mes")
        self.assertEqual(m.call_args.kwargs["folder_id"], 2)
        self.assertEqual(m.call_args.args[1]["role"], "contador")


if __name__ == "__main__":
    unittest.main()
