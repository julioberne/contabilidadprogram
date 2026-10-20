# -*- coding: utf-8 -*-
"""CSV grande del Libro Diario por la cola (estándar H5.3, 20-oct-2026). Sin BD.

- Mismas columnas y formato que aCsv del navegador (diarioFiltros.js).
- Recorre lo filtrado por cursor hasta el final (sin el tope de 5.000).
- Si no cabe en el organizador va en ZIP; si ni así cabe, pide acotar.
- POST /api/diario/csv: 202 con la cola activa, 409 sin ella, 400 con filtros malos.

    python -m unittest tests.test_diario_csv
"""
import io
import os
import sys
import unittest
import zipfile
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import tests  # noqa: F401,E402

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from fin_sys_core import diario_csv as dc  # noqa: E402

TX = {"id": 88, "transaction_date": "2026-10-16", "type": "GASTO", "concept": 'Café; "doble"',
      "net_value": 50000.0, "amount": 1500.5, "transaction_currency": None, "category": "5105 - Gastos",
      "third_party_name": "Ana", "identification_number": "123", "account_name": "Nequi",
      "dest_account_name": None, "tags": ["obra", "viaje"], "note": "línea1\nlínea2", "portfolio_name": "Negocio A"}


class TestFormatoIgualAlNavegador(unittest.TestCase):
    def test_fila_como_aCsv(self):
        # aCsv: números con coma y sin ".0"; listas con " | "; comillas si hay ; " o salto.
        self.assertEqual(dc.fila_csv(TX),
                         '88;2026-10-16;GASTO;"Café; ""doble""";50000;1500,5;;5105 - Gastos;Ana;123;'
                         'Nequi;;obra | viaje;"línea1\nlínea2";Negocio A')

    def test_encabezado_y_bom(self):
        r = dc.armar_csv([TX, TX])
        texto = r["contenido"].decode("utf-8")
        self.assertTrue(texto.startswith("﻿ID;Fecha;Tipo;Concepto;Valor neto;Valor bruto;Moneda;"))
        self.assertEqual(r["n"], 2)

    def test_tope_corta_con_aviso(self):
        with self.assertRaises(ValueError):
            dc.armar_csv([TX] * 50, tope_bytes=500)


def _buscar_falso(total, por_pagina=None):
    """Imita buscar_movimientos con cursor sobre `total` filas."""
    filas = [{**TX, "id": i, "transaction_date": f"2026-01-{1 + i % 28:02d}"} for i in range(total, 0, -1)]
    llamadas = []

    def buscar(filtros, orden, limit, totales, despues):
        llamadas.append((orden, limit, totales, despues))
        tam = por_pagina or limit
        ini = 0 if despues is None else next(k for k, f in enumerate(filas) if f["id"] == despues[1]) + 1
        pag = filas[ini:ini + tam]
        sig = {"fecha": pag[-1]["transaction_date"], "id": pag[-1]["id"]} if len(pag) == tam else None
        return {"transactions": pag, "siguiente": sig}
    return buscar, llamadas


class TestRecorridoYGuardado(unittest.TestCase):
    def test_sigue_el_cursor_hasta_el_final_sin_tope(self):
        buscar, llamadas = _buscar_falso(2501, por_pagina=1000)
        filas = list(dc.recorrer({}, "fecha_desc", buscar))
        self.assertEqual(len(filas), 2501)
        self.assertEqual(len({f["id"] for f in filas}), 2501, "sin repetidos")
        self.assertEqual([c[3] is None for c in llamadas], [True, False, False])
        self.assertTrue(all(c[2] is False for c in llamadas), "solo páginas, sin totales")

    def test_orden_sin_cursor_sale_por_fecha(self):
        self.assertEqual(dc.orden_para_csv("monto_desc"), "fecha_desc")
        self.assertEqual(dc.orden_para_csv("fecha_asc"), "fecha_asc")

    def test_generar_guarda_en_el_organizador(self):
        buscar, _ = _buscar_falso(30)
        guardado = {}

        def guardar(contenido, nombre, nombre_archivo, mime, usuario, folder_id, receta):
            guardado.update(contenido=contenido, nombre_archivo=nombre_archivo, mime=mime, receta=receta)
            return {"id": 5, "folio": "F-9", "nombre_archivo": nombre_archivo}
        r = dc.generar({"empresas": ["Negocio A"]}, "monto_desc", {"uid": "u1"}, buscar=buscar, guardar=guardar)
        self.assertEqual((r["id"], r["n"], r["orden_usado"], r["comprimido"]), (5, 30, "fecha_desc", False))
        self.assertEqual(guardado["mime"], "text/csv")
        self.assertTrue(guardado["nombre_archivo"].endswith(".csv"))
        self.assertEqual(guardado["receta"]["orden"], "monto_desc")

    def test_si_no_cabe_va_comprimido(self):
        buscar, _ = _buscar_falso(400)
        guardado = {}

        def guardar(contenido, nombre, nombre_archivo, mime, usuario, folder_id, receta):
            guardado.update(contenido=contenido, mime=mime)
            return {"id": 6, "folio": "F-10", "nombre_archivo": nombre_archivo}
        with mock.patch("fin_sys_core.accounting_files_driver.MAX_BYTES", 20_000):
            r = dc.generar({}, "fecha_desc", None, buscar=buscar, guardar=guardar)
        self.assertTrue(r["comprimido"])
        self.assertEqual(guardado["mime"], "application/zip")
        with zipfile.ZipFile(io.BytesIO(guardado["contenido"])) as z:
            # cada fila termina en la empresa (la nota trae un salto de línea entre comillas)
            self.assertEqual(z.read(z.namelist()[0]).decode("utf-8").count(";Negocio A"), 400)


USUARIO = {"uid": "u1", "name": "Andrés", "role": "contador", "su": False}


def _app():
    from routers import diario as rt
    from routers.auth_guard import require_contador
    app = FastAPI()
    app.include_router(rt.router)
    app.dependency_overrides[require_contador] = lambda: USUARIO
    return app


class TestRutaCsv(unittest.TestCase):
    def test_sin_cola_409(self):
        with mock.patch.dict(os.environ, {"FINSYS_EN_COLA": "", "FINSYS_EXPORT_EN_COLA": ""}):
            r = TestClient(_app()).post("/api/diario/csv?portfolio=Negocio%20A")
        self.assertEqual(r.status_code, 409)

    def test_con_cola_202_y_los_filtros_viajan(self):
        with mock.patch.dict(os.environ, {"FINSYS_EN_COLA": "diario_csv"}), \
             mock.patch("fin_sys_core.cola.encolar", return_value={"id": 3, "nueva": True, "cola": "trabajos_prueba"}) as enc:
            r = TestClient(_app()).post("/api/diario/csv?portfolio=Negocio%20A&tipos=GASTO&orden=monto_desc")
        self.assertEqual((r.status_code, r.json()["operacion"]), (202, 3))
        tipo, datos = enc.call_args[0]
        self.assertEqual(tipo, "diario_csv")
        self.assertEqual((datos["filtros"]["empresas"], datos["filtros"]["tipos"], datos["orden"]),
                         (["Negocio A"], "GASTO", "monto_desc"))

    def test_filtros_malos_400_antes_de_encolar(self):
        with mock.patch.dict(os.environ, {"FINSYS_EN_COLA": "diario_csv"}), \
             mock.patch("fin_sys_core.cola.encolar") as enc:
            r = TestClient(_app()).post("/api/diario/csv?tipos=OTRO")
            r2 = TestClient(_app()).post("/api/diario/csv?orden=DROP")
        self.assertEqual((r.status_code, r2.status_code), (400, 400))
        enc.assert_not_called()


if __name__ == "__main__":
    unittest.main()
