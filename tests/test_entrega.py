# -*- coding: utf-8 -*-
"""📦 Compendio de entrega en ZIP (13.5 §11) — tests puros, sin base de datos.

  · el ZIP lleva los archivos byte a byte, 00 - INDICE.csv (con SHA-256) y LEEME.txt
  · huella que no coincide o libros que cambiaron → advertencia en el índice y en el LEEME
  · se archiva como GENERADO con folio propio y paquete 'entrega'; no se regenera
  · límites: máximo 50 archivos, tope de tamaño, no se anida una entrega en otra

Ejecutar:  .venv\\Scripts\\python.exe -m unittest tests.test_entrega -v
"""
import csv
import hashlib
import io
import json
import os
import sys
import unittest
import zipfile
from datetime import date, datetime
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import fin_sys_core  # noqa: E402,F401
from fin_sys_core import accounting_files_driver as afd  # noqa: E402
from fin_sys_core import entrega_driver as ent  # noqa: E402
from tests.test_accounting_files import FakeConn, FakeCursor, R  # noqa: E402

XLSX = b"PK\x03\x04 libro de prueba"
PDF = b"%PDF-1.4 extracto"


def _fila(**kw):
    base = {"id": 4, "origen": "GENERADO", "folio": "EXP-2026-0004", "nombre": "Cierre de mes · Pegasus · sep 2026",
            "nombre_archivo": "EXP-2026-0004_cierre.xlsx", "mime_type": afd.MIME_XLSX, "archivo": XLSX,
            "sha256": hashlib.sha256(XLSX).hexdigest(), "tamano_bytes": len(XLSX), "portfolio_id": 3,
            "empresa": "Pegasus", "periodo_desde": date(2026, 9, 1), "periodo_hasta": date(2026, 9, 30),
            "tipo": "Libros", "creado_por": "Andrés", "creado_en": datetime(2026, 10, 1, 9, 0),
            "receta": {"modo": "periodo"}, "huella_datos": {"x": 1}, "paquete": "cierre_mes"}
    base.update(kw)
    return base


def _tupla(f):
    return tuple(f[k] for k in ent._COLS)


SUBIDO = _fila(id=7, origen="SUBIDO", folio=None, nombre="Extracto Bancolombia: septiembre", nombre_archivo="extracto.pdf",
               mime_type="application/pdf", archivo=PDF, sha256="0" * 64, portfolio_id=None, empresa=None,
               periodo_desde=None, periodo_hasta=None, tipo="Bancos", receta=None, huella_datos=None, paquete=None)


class TestZip(unittest.TestCase):

    def test_contenido_indice_y_leeme(self):
        z = ent.armar_zip([_fila(), SUBIDO], "EXP-2026-0010", "Entrega al contador", "Revisar el IVA",
                          {4: {"estado": "CAMBIO"}}, datetime(2026, 10, 6, 12, 0))
        zf = zipfile.ZipFile(io.BytesIO(z["contenido"]))
        nombres = zf.namelist()
        self.assertEqual(nombres[0], "01 - EXP-2026-0004 - Cierre de mes · Pegasus · sep 2026.xlsx")
        self.assertEqual(nombres[1], "02 - SUBIDO - Extracto Bancolombia_ septiembre.pdf")   # ':' no va en nombres
        self.assertIn("00 - INDICE.csv", nombres)
        self.assertEqual(zf.read(nombres[0]), XLSX)                                         # byte a byte
        texto = zf.read("00 - INDICE.csv").decode("utf-8-sig")
        filas = list(csv.DictReader(io.StringIO(texto), delimiter=";"))
        self.assertEqual(filas[0]["SHA-256"], hashlib.sha256(XLSX).hexdigest())
        self.assertEqual((filas[0]["Integridad"], filas[0]["Vigencia al empaquetar"]), ("OK", "Los libros cambiaron después"))
        self.assertEqual((filas[1]["Integridad"], filas[1]["Origen"], filas[1]["Empresa"]),
                         ("NO COINCIDE", "Subido", "Consolidado"))
        self.assertEqual(filas[0]["Período"], "01/09/2026 a 30/09/2026")
        leeme = zf.read("LEEME.txt").decode("utf-8")
        self.assertIn("EXP-2026-0010", leeme)
        self.assertIn("Revisar el IVA", leeme)
        self.assertEqual(len(z["advertencias"]), 2)                                         # cambió + huella


class TestCrear(unittest.TestCase):

    def _crear(self, filas, **datos):
        cur = FakeCursor(R(*[_tupla(f) for f in filas]), R((10,)), R(), R((1,)), R((77, datetime(2026, 10, 6))))
        with mock.patch.object(ent, "_vigencias", return_value={}):
            r = ent.crear({"ids": [f["id"] for f in filas], **datos}, {"name": "Andrés"}, conn=FakeConn(cur))
        return r, cur

    def test_archiva_con_folio_y_paquete_entrega(self):
        r, cur = self._crear([_fila(), SUBIDO], nombre="Para el banco", nota="ok")
        self.assertEqual((r["id"], r["n"], r["paquete"]), (77, 2, "entrega"))
        self.assertRegex(r["folio"], r"^EXP-\d{4}-0010$")
        self.assertTrue(r["nombre_archivo"].endswith("_Para el banco.zip"))
        p = cur.ejecutadas[-1][1]
        self.assertIn("INSERT INTO accounting_files", cur.sql(len(cur.ejecutadas) - 1))
        self.assertEqual((p[4], p[11]), ("entrega", "application/zip"))
        self.assertEqual(json.loads(p[5])["ids"], [4, 7])
        self.assertIsNone(p[6])                                     # empresas mezcladas → sin empresa única
        self.assertEqual((p[7], p[8]), (date(2026, 9, 1), date(2026, 9, 30)))
        self.assertEqual(hashlib.sha256(p[10]).hexdigest(), r["sha256"])

    def test_limites(self):
        for ids in ([], list(range(1, 52)), ["x"]):
            with self.assertRaises(ValueError):
                ent.crear({"ids": ids}, None, conn=FakeConn(FakeCursor()))
        with self.assertRaises(afd.NoEncontrado):
            ent.crear({"ids": [4, 99]}, None, conn=FakeConn(FakeCursor(R(_tupla(_fila())))))
        with self.assertRaises(ValueError):                         # no se anida una entrega en otra
            ent.crear({"ids": [4]}, None, conn=FakeConn(FakeCursor(R(_tupla(_fila(paquete="entrega"))))))
        with mock.patch.object(ent, "MAX_BYTES", 10), self.assertRaises(ValueError):
            self._crear([_fila()])

    def test_no_se_regenera(self):
        cur = FakeCursor(R(("GENERADO", {"modo": "entrega", "ids": [4]}, "entrega", None, 1)))
        with self.assertRaises(ValueError) as e:
            afd.regenerar(77, conn=FakeConn(cur))
        self.assertIn("no se regenera", str(e.exception))


class TestRuta(unittest.TestCase):

    def test_permisos_y_respuesta(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers.accounting_files import router
        from routers.auth_guard import create_session_token
        app = FastAPI()
        app.include_router(router)
        cli = TestClient(app)
        contador = {"Authorization": "Bearer " + create_session_token({"id": 1, "name": "P", "role": "contador"})}
        member = {"Authorization": "Bearer " + create_session_token({"id": 1, "name": "P", "role": "member"})}
        self.assertEqual(cli.post("/api/accounting-files/entrega", json={"ids": [1]}).status_code, 401)
        self.assertEqual(cli.post("/api/accounting-files/entrega", json={"ids": [1]}, headers=member).status_code, 403)
        with mock.patch.object(ent, "crear", return_value={"id": 5, "folio": "EXP-1"}) as m:
            r = cli.post("/api/accounting-files/entrega", json={"ids": [4, 7], "nombre": "x"}, headers=contador)
        self.assertEqual((r.status_code, r.json()["folio"]), (201, "EXP-1"))
        self.assertEqual(m.call_args.args[0]["ids"], [4, 7])


if __name__ == "__main__":
    unittest.main()
