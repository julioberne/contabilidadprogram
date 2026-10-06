# -*- coding: utf-8 -*-
"""Exportación 13.6 — 🤝 Compendio para el cliente (tests puros, sin base de datos).

  · código del link: HMAC de un nonce; en la BD solo su SHA-256; se rearma con la clave
  · la foto: orden por fecha, totales por moneda (USD aparte), sin asientos, NIT opcional
  · ubicación: solo https de Google Maps (nada de javascript:)
  · comprobantes: en vivo, solo por índice y solo del bucket propio (CA-136-04)
  · vigencia: 7/15/30/90; ampliar suma; revocar es definitivo (CA-136-03)
  · visor: los datos no pueden cerrar el <script>; CSP con nonce (CA-136-08)
  · endpoints: privados 401/403; públicos 404 "no disponible", cabeceras y límite de ritmo

Ejecutar:  .venv\\Scripts\\python.exe -m unittest tests.test_compendios -v
"""
import json
import os
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import fin_sys_core  # noqa: E402,F401  (un solo objeto por módulo)
from fin_sys_core import compendio_driver as drv  # noqa: E402
from fin_sys_core import compendio_visor as visor  # noqa: E402
from tests.test_accounting_files import FakeConn, FakeCursor, R  # noqa: E402

BUCKET = drv.prefijo_bucket()
AHORA = datetime.now(timezone.utc)

TXS = [
    {"id": 57, "transaction_date": "2026-09-20", "type": "GASTO", "net_value": 109000, "amount": 109000,
     "concept": "Pago gym", "category": "Salud", "portfolio_name": "Negocio A", "third_party_name": "Fitness SAS",
     "identification_type": "NIT", "identification_number": "900123", "transaction_currency": "COP",
     "geo_maps_link": "https://www.google.com/maps?q=6.2,-75.5", "account_name": "Bancolombia"},
    {"id": 45, "transaction_date": "2026-09-02", "type": "INGRESO", "net_value": 500000, "amount": 500000,
     "concept": "Venta", "category": "Ventas", "portfolio_name": "Negocio A", "transaction_currency": "COP",
     "geo_maps_link": "javascript:alert(1)"},
    {"id": 60, "transaction_date": "2026-09-10", "type": "GASTO", "net_value": 25, "amount": 25,
     "concept": "Licencia", "category": "Software", "portfolio_name": "Negocio A", "transaction_currency": "USD"},
    {"id": 61, "transaction_date": "2026-09-11", "type": "TRANSFERENCIA", "net_value": 70000, "amount": 70000,
     "concept": "Traslado", "portfolio_name": "Negocio A", "transaction_currency": "COP"},
]
EMPRESAS = {"Negocio A": {"nombre": "Pegasus SAS", "nit": "901000"}}
OPC = {"identificacion": True, "ubicaciones": True}


class TestCodigoDelLink(unittest.TestCase):

    def test_hmac_del_nonce_y_hash(self):
        t = drv.token_de("abc")
        self.assertEqual(t, drv.token_de("abc"))
        self.assertNotEqual(t, drv.token_de("abd"))
        self.assertRegex(t, drv._TOKEN)
        self.assertEqual(len(drv.hash_token(t)), 64)

    def test_ruta_solo_si_el_hash_coincide(self):
        t = drv.token_de("n1")
        self.assertEqual(drv.ruta_de({"nonce": "n1", "token_hash": drv.hash_token(t)}), f"/c/{t}")
        self.assertIsNone(drv.ruta_de({"nonce": "n1", "token_hash": "0" * 64}))   # otra clave de servidor
        self.assertIsNone(drv.ruta_de({"nonce": None, "token_hash": "x"}))


class TestFoto(unittest.TestCase):

    def test_orden_totales_por_moneda_y_sin_sumar_transferencias(self):
        s = drv.armar_snapshot(TXS, EMPRESAS, OPC, "Septiembre", "Hola")
        self.assertEqual([t["id"] for t in s["txs"]], [45, 60, 61, 57])
        self.assertEqual([t["i"] for t in s["txs"]], [0, 1, 2, 3])
        self.assertEqual(s["totales"]["COP"], {"n": 3, "ingresos": 500000.0, "gastos": 109000.0, "neto": 391000.0})
        self.assertEqual(s["totales"]["USD"], {"n": 1, "ingresos": 0.0, "gastos": 25.0, "neto": -25.0})
        self.assertEqual(s["rango"], {"desde": "2026-09-02", "hasta": "2026-09-20"})
        self.assertEqual(s["empresas"], [{"nombre": "Pegasus SAS", "nit": "901000"}])
        self.assertEqual((s["nombre"], s["nota"], s["n"]), ("Septiembre", "Hola", 4))

    def test_sin_asientos_y_ubicacion_segura(self):
        s = drv.armar_snapshot(TXS, EMPRESAS, OPC, "x", None)
        por_id = {t["id"]: t for t in s["txs"]}
        self.assertNotIn("asientos", s)
        self.assertEqual(por_id[57]["maps"], "https://www.google.com/maps?q=6.2,-75.5")
        self.assertIsNone(por_id[45]["maps"])                       # javascript: no pasa
        self.assertEqual(por_id[57]["identificacion"], "NIT 900123")
        self.assertEqual(por_id[57]["empresa"], "Pegasus SAS")

    def test_opciones_ocultan_identificacion_y_ubicacion(self):
        s = drv.armar_snapshot(TXS, EMPRESAS, {"identificacion": False, "ubicaciones": False}, "x", None)
        self.assertTrue(all("identificacion" not in t and "maps" not in t for t in s["txs"]))

    def test_maps_seguro(self):
        ok = ["https://www.google.com/maps?q=1,2", "https://maps.google.com.co/?q=1", "https://maps.app.goo.gl/abc",
              "https://goo.gl/maps/x"]
        malos = ["http://www.google.com/maps?q=1", "javascript:alert(1)", "https://evil.com/google.com",
                 "https://google.com.evil.io/maps", "", None, "data:text/html,hola"]
        for u in ok:
            self.assertEqual(drv.maps_seguro(u), u, u)
        for u in malos:
            self.assertIsNone(drv.maps_seguro(u), u)

    def test_validaciones(self):
        for v in (0, 10, "x", 365):
            with self.assertRaises(ValueError):
                drv._vigencia(v)
        self.assertEqual(drv._vigencia(None), 15)
        self.assertEqual(drv._vigencia("30"), 30)
        for v in ([], None, ["a"], [0], list(range(1, drv.MAX_TX + 2))):
            with self.assertRaises(ValueError):
                drv._tx_ids(v)
        self.assertEqual(drv._tx_ids([5, 3, 5]), [3, 5])


class TestComprobantes(unittest.TestCase):

    def test_describir(self):
        d = drv.describir_soporte(BUCKET + "evidence/abc/factura%20marzo.JPG", BUCKET)
        self.assertEqual((d["tipo"], d["mime"], d["servible"], d["nombre"]),
                         ("imagen", "image/jpeg", True, "factura marzo.JPG"))
        self.assertEqual(drv.describir_soporte(BUCKET + "evidence/x.pdf", BUCKET)["tipo"], "pdf")
        self.assertEqual(drv.describir_soporte(BUCKET + "evidence/nota.ogg", BUCKET)["tipo"], "audio")
        svg = drv.describir_soporte(BUCKET + "evidence/x.svg", BUCKET)
        self.assertEqual((svg["tipo"], svg["mime"]), ("otro", "application/octet-stream"))   # nunca inline
        for u in ("/uploads/evidence/x.jpg", "https://otro.sitio/x.jpg", BUCKET + "../secreto.jpg",
                  BUCKET + "evidence/x.jpg?token=1", BUCKET):
            self.assertFalse(drv.describir_soporte(u, BUCKET)["servible"], u)

    def test_vivos_en_el_orden_del_boton_ver(self):
        cur = FakeCursor(R((57, "/uploads/viejo.jpg", json.dumps([BUCKET + "a.jpg", BUCKET + "b.pdf"])),
                           (45, None, [])))
        vivos = drv.soportes_vivos(cur, [57, 45])
        self.assertEqual(vivos[57], ["/uploads/viejo.jpg", BUCKET + "a.jpg", BUCKET + "b.pdf"])
        self.assertEqual(vivos[45], [])
        self.assertEqual(cur.ejecutadas[0][1], ([57, 45],))


def _fila_bd(**kw):
    base = {"id": 9, "folio": "EXP-2026-0007", "nombre": "x", "nota": None, "n": 2, "creado_por": "Prueba",
            "creado_en": AHORA, "expira_en": AHORA + timedelta(days=5), "revocado_en": None, "revocado_por": None,
            "visitas": 0, "ultima_visita": None, "nonce": "n1", "token_hash": drv.hash_token(drv.token_de("n1"))}
    base.update(kw)
    return tuple(base[k] for k in drv._COLS)


class TestCiclo(unittest.TestCase):

    def test_estado(self):
        self.assertEqual(drv.estado({"expira_en": AHORA + timedelta(hours=1)}), "vigente")
        self.assertEqual(drv.estado({"expira_en": AHORA - timedelta(seconds=1)}), "vencido")
        self.assertEqual(drv.estado({"expira_en": AHORA + timedelta(days=9), "revocado_en": AHORA}), "revocado")

    def test_crear_guarda_solo_el_hash(self):
        cur = FakeCursor(R((7,)), R((99, AHORA)))
        with mock.patch.object(drv, "_leer_txs", return_value=(TXS, [], EMPRESAS)):
            r = drv.crear({"tx_ids": [57, 45], "vigencia_dias": 30, "nombre": " Viaje ", "nota": "línea 1\nlínea 2"},
                          {"name": "Andrés"}, conn=FakeConn(cur))
        self.assertEqual(r["folio"], f"EXP-{AHORA.year}-0007")
        self.assertEqual((r["id"], r["n"], r["nombre"], r["vigencia_dias"]), (99, 4, "Viaje", 30))
        token = r["ruta"].split("/c/")[1]
        params = cur.ejecutadas[1][1]
        self.assertNotIn(token, json.dumps([str(p) for p in params]))          # el código no se guarda
        self.assertEqual(params[7], drv.hash_token(token))
        self.assertEqual(drv.token_de(params[6]), token)                       # se rearma desde el nonce
        self.assertEqual(params[2], "línea 1\nlínea 2")                        # la nota conserva sus líneas
        snap = json.loads(params[4])
        self.assertEqual(snap["folio"], r["folio"])
        self.assertAlmostEqual((params[8] - AHORA).days, 30, delta=1)

    def test_ampliar_suma_desde_el_vencimiento(self):
        expira = AHORA + timedelta(days=5)
        cur = FakeCursor(R(_fila_bd(expira_en=expira)), R())
        r = drv.actualizar(9, {"ampliar_dias": 7}, {"name": "A"}, conn=FakeConn(cur))
        self.assertEqual(cur.ejecutadas[1][1][0], expira + timedelta(days=7))
        self.assertEqual(r["estado"], "vigente")
        self.assertTrue(r["ruta"].startswith("/c/"))
        self.assertNotIn("token_hash", r)
        self.assertNotIn("nonce", r)

    def test_revocar_es_definitivo(self):
        cur = FakeCursor(R(_fila_bd()), R())
        r = drv.actualizar(9, {"revocar": True}, {"name": "A"}, conn=FakeConn(cur))
        self.assertEqual((r["estado"], r["ruta"]), ("revocado", None))
        cur = FakeCursor(R(_fila_bd(revocado_en=AHORA)))
        with self.assertRaises(drv.Conflicto):
            drv.actualizar(9, {"ampliar_dias": 15}, None, conn=FakeConn(cur))
        with self.assertRaises(drv.NoEncontrado):
            drv.actualizar(9, {"revocar": True}, None, conn=FakeConn(FakeCursor(R())))

    def test_listar_no_expone_el_hash(self):
        cur = FakeCursor(R(_fila_bd(), _fila_bd(id=8, expira_en=AHORA - timedelta(days=1))))
        filas = drv.listar(conn=FakeConn(cur))
        self.assertEqual([f["estado"] for f in filas], ["vigente", "vencido"])
        self.assertIsNone(filas[1]["ruta"])
        self.assertTrue(all("token_hash" not in f and "nonce" not in f for f in filas))


def _snap():
    s = drv.armar_snapshot(TXS[:2], EMPRESAS, OPC, "Septiembre", None)
    s["folio"] = "EXP-2026-0007"
    return s


class TestPublico(unittest.TestCase):
    TOKEN = drv.token_de("n1")

    def test_codigo_mal_formado_no_toca_la_bd(self):
        cur = FakeCursor()
        for t in ("", "corto", "a" * 70, "../../etc", "x" * 39 + "!"):
            with self.assertRaises(drv.NoDisponible):
                drv.abrir(t, conn=FakeConn(cur))
        self.assertEqual(cur.ejecutadas, [])

    def test_vencido_o_inexistente_es_lo_mismo(self):
        for fila in (None, (9, "EXP", json.dumps(_snap()), AHORA - timedelta(days=1), None),
                     (9, "EXP", json.dumps(_snap()), AHORA + timedelta(days=1), AHORA)):
            cur = FakeCursor(R(fila) if fila else R())
            with self.assertRaises(drv.NoDisponible):
                drv.abrir(self.TOKEN, conn=FakeConn(cur))

    def test_abrir_describe_comprobantes_sin_su_url_y_cuenta_la_visita(self):
        snap = _snap()
        cur = FakeCursor(R((9, "EXP-2026-0007", snap, AHORA + timedelta(days=3), None)),
                         R((45, None, [BUCKET + "evidence/f.jpg"]), (57, "/uploads/v.pdf", [])), R())
        d = drv.abrir(self.TOKEN, conn=FakeConn(cur))
        por_id = {t["id"]: t for t in d["txs"]}
        self.assertEqual(por_id[45]["soportes"], [{"j": 0, "nombre": "f.jpg", "tipo": "imagen", "servible": True}])
        self.assertFalse(por_id[57]["soportes"][0]["servible"])
        self.assertNotIn("supabase", json.dumps(d))                            # CA-136-02
        self.assertIn("visitas = visitas + 1", cur.sql(2))
        self.assertEqual(cur.ejecutadas[0][1], (drv.hash_token(self.TOKEN),))

    def test_soporte_solo_por_indice_y_del_bucket(self):   # CA-136-04
        snap = _snap()
        fila = R((9, "EXP", snap, AHORA + timedelta(days=3), None))
        cur = FakeCursor(fila, R((45, None, [BUCKET + "evidence/f.jpg", "https://otro.sitio/x.jpg"])))
        s = drv.soporte(self.TOKEN, 0, 0, conn=FakeConn(cur))
        self.assertEqual((s["url"], s["mime"]), (BUCKET + "evidence/f.jpg", "image/jpeg"))
        casos = [(5, 0, [fila]), (-1, 0, [fila]),
                 (0, 1, [fila, R((45, None, [BUCKET + "a.jpg", "https://otro.sitio/x.jpg"]))]),
                 (0, 3, [fila, R((45, None, [BUCKET + "a.jpg"]))])]
        for i, j, respuestas in casos:
            with self.assertRaises(drv.NoDisponible, msg=f"{i},{j}"):
                drv.soporte(self.TOKEN, i, j, conn=FakeConn(FakeCursor(*respuestas)))


class TestVisor(unittest.TestCase):

    def test_los_datos_no_cierran_el_script(self):
        datos = {"nombre": "__DATOS__ </script><script>alert(1)</script>", "folio": "EXP-1",
                 "txs": [{"concepto": "</script><img src=x onerror=alert(1)>", "i": 0}], "base": "/x"}
        html, nonce = visor.pagina(datos)
        self.assertEqual(html.lower().count("</script>"), 2)                  # solo los dos propios
        self.assertNotIn("<img src=x", html)
        self.assertIn(f'<script nonce="{nonce}">', html)
        self.assertIn(f"'nonce-{nonce}'", visor.csp(nonce))
        self.assertIn("<title>__DATOS__ &lt;/script&gt;", html)               # el título no se reemplaza
        m = re.search(r'<script type="application/json" id="datos">(.*?)</script>', html, re.S)
        self.assertEqual(json.loads(m.group(1))["txs"][0]["concepto"], "</script><img src=x onerror=alert(1)>")


class TestRouter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from routers import compendios
        from routers.auth_guard import create_session_token
        cls.mod = compendios
        app = FastAPI()
        app.include_router(compendios.router)
        cls.client = TestClient(app)

        def token(role):
            return {"Authorization": "Bearer " + create_session_token({"id": 1, "name": "Prueba", "role": role})}
        cls.contador, cls.member = token("contador"), token("member")

    def setUp(self):
        self.mod._RITMO.clear()

    PRIVADAS = [("post", "/api/compendios/preflight"), ("post", "/api/compendios"),
                ("get", "/api/compendios"), ("patch", "/api/compendios/1")]

    def test_privadas_401_y_403(self):
        for metodo, ruta in self.PRIVADAS:
            self.assertEqual(getattr(self.client, metodo)(ruta).status_code, 401, ruta)
            self.assertEqual(getattr(self.client, metodo)(ruta, headers=self.member).status_code, 403, ruta)

    def test_crear_y_errores(self):
        with mock.patch.object(drv, "crear", return_value={"id": 1, "ruta": "/c/x"}) as m:
            r = self.client.post("/api/compendios", json={"tx_ids": [1, 2], "vigencia_dias": 7}, headers=self.contador)
        self.assertEqual((r.status_code, r.json()["ruta"]), (201, "/c/x"))
        self.assertEqual(m.call_args[0][0]["vigencia_dias"], 7)
        with mock.patch.object(drv, "crear", side_effect=ValueError("La vigencia debe ser…")):
            r = self.client.post("/api/compendios", json={"tx_ids": [1]}, headers=self.contador)
        self.assertEqual(r.status_code, 400)
        with mock.patch.object(drv, "actualizar", side_effect=drv.Conflicto("revocado")):
            r = self.client.patch("/api/compendios/1", json={"ampliar_dias": 7}, headers=self.contador)
        self.assertEqual(r.status_code, 409)

    def _cabeceras_publicas(self, r):
        self.assertEqual(r.headers["x-robots-tag"], "noindex, nofollow")
        self.assertEqual(r.headers["referrer-policy"], "no-referrer")
        self.assertEqual(r.headers["x-content-type-options"], "nosniff")
        self.assertIn("frame-ancestors", r.headers["content-security-policy"])

    def test_pagina_no_disponible(self):   # CA-136-03
        with mock.patch.object(drv, "abrir", side_effect=drv.NoDisponible()):
            r = self.client.get("/c/" + "a" * 43)
        self.assertEqual(r.status_code, 404)
        self.assertIn("ya no está disponible", r.text)
        self.assertEqual(r.headers["cache-control"], "no-store")
        self._cabeceras_publicas(r)

    def test_pagina_vigente_con_csp_y_nonce(self):   # CA-136-08
        with mock.patch.object(drv, "abrir", return_value=_snap()):
            r = self.client.get("/c/" + "a" * 43)
        self.assertEqual(r.status_code, 200)
        self._cabeceras_publicas(r)
        self.assertEqual(r.headers["cache-control"], "no-store")
        nonce = re.search(r"'nonce-([^']+)'", r.headers["content-security-policy"]).group(1)
        self.assertIn(f'<script nonce="{nonce}">', r.text)
        self.assertIn('"base": "/api/publico/compendio/' + "a" * 43 + '"', r.text)

    def test_soporte_servido_por_el_servidor(self):
        url = BUCKET + "evidence/f.pdf"
        with mock.patch.object(drv, "soporte", return_value={"url": url, **drv.describir_soporte(url)}), \
                mock.patch.object(self.mod, "_traer", return_value=b"%PDF-1.4") as traer:
            r = self.client.get("/api/publico/compendio/" + "a" * 43 + "/soporte/0/0")
        self.assertEqual((r.status_code, r.content), (200, b"%PDF-1.4"))
        self.assertEqual(r.headers["content-type"], "application/pdf")
        self.assertTrue(r.headers["content-disposition"].startswith("inline"))
        self.assertEqual(r.headers["content-security-policy"], "frame-ancestors 'self'")
        traer.assert_called_once_with(url, drv.max_bytes_soporte())
        otro = BUCKET + "evidence/x.svg"
        with mock.patch.object(drv, "soporte", return_value={"url": otro, **drv.describir_soporte(otro)}), \
                mock.patch.object(self.mod, "_traer", return_value=b"<svg/>"):
            r = self.client.get("/api/publico/compendio/" + "a" * 43 + "/soporte/0/1")
        self.assertTrue(r.headers["content-disposition"].startswith("attachment"))
        self.assertEqual(r.headers["content-type"], "application/octet-stream")
        with mock.patch.object(drv, "soporte", side_effect=drv.NoDisponible()):
            self.assertEqual(self.client.get("/api/publico/compendio/x/soporte/0/0").status_code, 404)

    def test_limite_de_ritmo(self):
        with mock.patch.dict(os.environ, {"COMPENDIO_RITMO_POR_MIN": "10"}), \
                mock.patch.object(drv, "abrir", side_effect=drv.NoDisponible()):
            codigos = [self.client.get("/c/" + "a" * 43).status_code for _ in range(11)]
        self.assertEqual(codigos[:10], [404] * 10)
        self.assertEqual(codigos[10], 429)


if __name__ == "__main__":
    unittest.main()
