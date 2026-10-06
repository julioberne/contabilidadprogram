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
from tests.test_accounting_files import FakeConn, FakeCursor, R, _PgError  # noqa: E402
from fin_sys_core import compendio_aviso as aviso  # noqa: E402

UA_ANDROID = ("Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/129.0.0.0 Mobile Safari/537.36")
UA_IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
             "Version/17.6 Mobile/15E148 Safari/604.1")
UA_WINDOWS_EDGE = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0")

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

    def test_abrir_describe_comprobantes_sin_su_url_y_solo_lee(self):
        snap = _snap()
        cur = FakeCursor(R((9, "EXP-2026-0007", snap, AHORA + timedelta(days=3), None)),
                         R((45, None, [BUCKET + "evidence/f.jpg"]), (57, "/uploads/v.pdf", [])))
        d = drv.abrir(self.TOKEN, conn=FakeConn(cur))
        por_id = {t["id"]: t for t in d["txs"]}
        self.assertEqual(por_id[45]["soportes"], [{"j": 0, "nombre": "f.jpg", "tipo": "imagen", "servible": True}])
        self.assertFalse(por_id[57]["soportes"][0]["servible"])
        self.assertNotIn("supabase", json.dumps(d))                            # CA-136-02
        self.assertEqual(len(cur.ejecutadas), 2)                               # la visita la anota el router aparte
        self.assertEqual(d["_id"], 9)
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


class TestSeguimiento(unittest.TestCase):   # 13.6-c

    def test_robots_y_vistas_previas_no_son_el_cliente(self):
        for ua in ("WhatsApp/2.23.20.0 A", "TelegramBot (like TwitterBot)", "facebookexternalhit/1.1",
                   "Mozilla/5.0 (compatible; Googlebot/2.1)", "curl/8.4.0", "python-requests/2.31", ""):
            self.assertTrue(drv.es_robot(ua), ua)
        for ua in (UA_ANDROID, UA_IPHONE, UA_WINDOWS_EDGE, "Mozilla/5.0 (Linux; Android 10; CUBOT X30) Chrome/120.0"):
            self.assertFalse(drv.es_robot(ua), ua)

    def test_dispositivo(self):
        self.assertEqual(drv.dispositivo_de(UA_ANDROID), "📱 Android · Chrome")
        self.assertEqual(drv.dispositivo_de(UA_IPHONE), "📱 iPhone · Safari")
        self.assertEqual(drv.dispositivo_de(UA_WINDOWS_EDGE), "💻 Windows · Edge")
        self.assertEqual(drv.dispositivo_de("algo raro"), "🌐 Otro")

    def test_visitante_es_huella_sin_ip(self):   # CA-136-13
        v = drv.visitante_de(9, "181.50.12.7", UA_ANDROID)
        self.assertRegex(v, r"^[0-9a-f]{12}$")
        self.assertEqual(v, drv.visitante_de(9, "181.50.12.7", UA_ANDROID))
        self.assertNotEqual(v, drv.visitante_de(10, "181.50.12.7", UA_ANDROID))   # otra huella por compendio
        self.assertNotEqual(v, drv.visitante_de(9, "181.50.12.8", UA_ANDROID))

    def test_primera_apertura_y_sin_repetir(self):   # CA-136-09
        cur = FakeCursor(R((1,)), R((1, "EXP-2026-0007", "Viaje")))
        r = drv.anotar(9, "abrio", "181.50.12.7", UA_ANDROID, conn=FakeConn(cur))
        self.assertEqual((r["nuevo"], r["primera"], r["folio"]), (True, True, "EXP-2026-0007"))
        self.assertIn("visitas = visitas + 1", cur.sql(1))
        self.assertNotIn("181.50.12.7", json.dumps([str(p) for _, p in cur.ejecutadas]))   # CA-136-13
        cur = FakeCursor(R((2,)), R((2, "EXP", "x")))
        self.assertFalse(drv.anotar(9, "abrio", "1.1.1.1", UA_ANDROID, conn=FakeConn(cur))["primera"])
        cur = FakeCursor(R())                                                   # repetido dentro de 10 min
        self.assertEqual(drv.anotar(9, "abrio", "1.1.1.1", UA_ANDROID, conn=FakeConn(cur)),
                         {"nuevo": False, "primera": False, "dispositivo": "📱 Android · Chrome"})
        self.assertEqual(len(cur.ejecutadas), 1)
        cur = FakeCursor()
        self.assertTrue(drv.anotar(9, "abrio", "1.1.1.1", "WhatsApp/2.23.20.0 A", conn=FakeConn(cur))["robot"])
        self.assertEqual(cur.ejecutadas, [])

    def test_evento_publico_solo_tx_y_del_rango(self):   # CA-136-14
        fila = R((9, "EXP", _snap(), AHORA + timedelta(days=3), None))
        for tipo, i in (("abrio", 0), ("tx", 5), ("tx", -1), ("tx", True), ("tx", "0"), ("tx", None)):
            with self.assertRaises(drv.NoDisponible, msg=f"{tipo},{i}"):
                drv.evento_publico(TestPublico.TOKEN, tipo, i, "1.1.1.1", UA_ANDROID, conn=FakeConn(FakeCursor(fila)))
        vencido = R((9, "EXP", _snap(), AHORA - timedelta(days=1), None))
        with self.assertRaises(drv.NoDisponible):
            drv.evento_publico(TestPublico.TOKEN, "tx", 0, "1.1.1.1", UA_ANDROID, conn=FakeConn(FakeCursor(vencido)))
        cur = FakeCursor(fila, R((5,)), R())
        self.assertTrue(drv.evento_publico(TestPublico.TOKEN, "tx", 1, "1.1.1.1", UA_ANDROID, conn=FakeConn(cur))["nuevo"])
        self.assertEqual((cur.ejecutadas[1][1]["t"], cur.ejecutadas[1][1]["i"]), ("tx", 1))

    def test_resumir_que_reviso(self):   # CA-136-11
        snap = drv.armar_snapshot(TXS, EMPRESAS, OPC, "x", None)       # i: 0=#45, 1=#60, 2=#61, 3=#57
        t0 = AHORA - timedelta(hours=3)
        ev = [
            {"tipo": "abrio", "tx_i": None, "soporte_j": None, "visitante": "aaa", "dispositivo": "📱 Android · Chrome", "en": t0},
            {"tipo": "tx", "tx_i": 3, "soporte_j": None, "visitante": "aaa", "dispositivo": "📱 Android · Chrome", "en": t0 + timedelta(minutes=1)},
            {"tipo": "comprobante", "tx_i": 3, "soporte_j": 0, "visitante": "aaa", "dispositivo": "x", "en": t0 + timedelta(minutes=2)},
            {"tipo": "abrio", "tx_i": None, "soporte_j": None, "visitante": "bbb", "dispositivo": "💻 Windows · Edge", "en": AHORA - timedelta(seconds=30)},
            {"tipo": "tx", "tx_i": 99, "soporte_j": None, "visitante": "bbb", "dispositivo": "x", "en": AHORA - timedelta(seconds=20)},
        ]
        r = drv.resumir(snap, ev, {57: 2, 45: 1}, creado_en=t0 - timedelta(hours=2), ahora=AHORA)
        self.assertEqual(r["resumen"]["aperturas"], 2)
        self.assertEqual(r["resumen"]["visitantes"], 2)
        self.assertEqual((r["resumen"]["revisadas"], r["resumen"]["total"]), (1, 4))
        self.assertTrue(r["resumen"]["en_vivo"])
        self.assertEqual(r["resumen"]["horas_hasta_primera"], 2.0)
        por_id = {t["id"]: t for t in r["por_tx"]}
        self.assertEqual((por_id[57]["revisada"], por_id[57]["aperturas"], por_id[57]["comprobantes_vistos"],
                          por_id[57]["comprobantes_total"]), (True, 1, 1, 2))
        self.assertFalse(por_id[45]["revisada"])
        self.assertEqual(r["eventos"][0]["visitante"], "Visitante 2")             # más reciente primero
        self.assertEqual(r["eventos"][-1]["visitante"], "Visitante 1")
        self.assertEqual(r["eventos"][2]["concepto"], "Pago gym")
        self.assertIsNone(r["eventos"][0]["concepto"])                           # índice fuera de la foto
        vacio = drv.resumir(snap, [], {}, ahora=AHORA)["resumen"]
        self.assertEqual((vacio["aperturas"], vacio["en_vivo"], vacio["primera"]), (0, False, None))

    def test_listar_con_estadisticas_y_sin_tabla_de_eventos(self):
        cur = FakeCursor(R(_fila_bd()), R(), R((9, 2, 1, AHORA - timedelta(hours=1), AHORA - timedelta(seconds=10))), R())
        f = drv.listar(conn=FakeConn(cur))[0]
        self.assertEqual((f["visitantes"], f["revisadas"], f["en_vivo"]), (2, 1, True))

        class SinEventos(FakeCursor):
            def execute(self, sql, params=None):
                if "FROM accounting_compendio_eventos" in sql:
                    raise _PgError("relation does not exist")
                super().execute(sql, params)
        cur = SinEventos(R(_fila_bd()))
        f = drv.listar(conn=FakeConn(cur))[0]
        self.assertEqual((f["visitantes"], f["en_vivo"]), (0, False))
        self.assertIn("ROLLBACK TO SAVEPOINT", cur.sql(-1))


class TestAviso(unittest.TestCase):   # CA-136-12

    def test_sin_variable_no_avisa(self):
        with mock.patch.dict(os.environ, {"COMPENDIO_AVISO_TELEGRAM": "", "TELEGRAM_BOT_TOKEN": "x"}), \
                mock.patch.object(aviso, "enviar") as enviar:
            self.assertEqual(aviso.avisar_primera_apertura("EXP-1", "Viaje", "📱 Android"), 0)
        enviar.assert_not_called()

    def test_avisa_a_los_chats_configurados(self):
        with mock.patch.dict(os.environ, {"COMPENDIO_AVISO_TELEGRAM": "1", "TELEGRAM_BOT_TOKEN": "x",
                                          "COMPENDIO_AVISO_CHAT": "111, 222"}), \
                mock.patch.object(aviso, "enviar", side_effect=[True, Exception("caído")]) as enviar:
            self.assertEqual(aviso.avisar_primera_apertura("EXP-1", "Viaje", "📱 Android"), 1)
        self.assertEqual([c.args[0] for c in enviar.call_args_list], ["111", "222"])
        self.assertIn("EXP-1", enviar.call_args_list[0].args[1])

    def test_destinos_por_defecto_owners_con_telegram(self):
        with mock.patch.dict(os.environ, {"COMPENDIO_AVISO_CHAT": ""}):
            cur = FakeCursor(R(("555",), ("777",)))
            self.assertEqual(aviso.destinos(conn=FakeConn(cur)), ["555", "777"])
        self.assertIn("owner", cur.sql(0))


def _png(ancho=400, alto=200) -> bytes:
    import io as _io
    from PIL import Image
    buf = _io.BytesIO()
    Image.new("RGB", (ancho, alto), (200, 30, 30)).save(buf, "PNG")
    return buf.getvalue()


def _pdf_anexo(paginas=2) -> bytes:
    from fpdf import FPDF
    p = FPDF()
    p.set_font("Helvetica", "", 12)
    for k in range(paginas):
        p.add_page()
        p.cell(0, 10, f"ANEXO-PRUEBA {k + 1}")
    return bytes(p.output())


class TestPdf(unittest.TestCase):   # 13.6-d · CA-136-05/07

    def _generar(self, **env):
        from fin_sys_core import compendio_pdf
        snap = drv.armar_snapshot(TXS[:3], EMPRESAS, OPC, "Viaje Medellín 🚕", "Nota — con guion")  # i: 0=#45 1=#60 2=#61
        snap["folio"] = "EXP-2026-0042"
        urls = {45: [BUCKET + "evidence/f.png", BUCKET + "evidence/factura.pdf"],
                60: ["/uploads/voz.ogg", BUCKET + "evidence/nota.ogg"], 61: []}
        bytes_por_url = {BUCKET + "evidence/f.png": _png(), BUCKET + "evidence/factura.pdf": _pdf_anexo(2)}
        with mock.patch.dict(os.environ, env):
            return compendio_pdf.generar(snap, urls, bytes_por_url.get, drv.describir_soporte, "2026-10-21T00:00:00+00:00")

    def test_paginas_anexos_y_marcadores(self):
        import io as _io
        from pypdf import PdfReader
        r = PdfReader(_io.BytesIO(self._generar()))
        textos = [p.extract_text() or "" for p in r.pages]
        # portada, índice, TX #45, sus 2 páginas de anexo, TX #60, TX #61
        self.assertEqual(len(r.pages), 7)
        self.assertIn("EXP-2026-0042", textos[0])
        self.assertIn("Pegasus SAS", textos[0])
        self.assertIn("Viaje Medellín", textos[0])                       # tildes sí, emoji fuera
        self.assertIn("COP: Ingresos $500.000", textos[0])
        self.assertIn("USD", textos[0])
        self.assertIn("INDICE", textos[1])
        self.assertIn("Venta", textos[2])
        self.assertIn("anexo a continuación", textos[2])
        self.assertIn("ANEXO-PRUEBA 1", textos[3])
        self.assertIn("ANEXO-PRUEBA 2", textos[4])
        self.assertIn("nota de voz", textos[5])
        self.assertIn("no disponible", textos[5])
        self.assertIn("no tiene comprobantes", textos[6])
        titulos = [o.title if not isinstance(o, list) else "[hijos]" for o in r.outline]
        self.assertEqual(titulos[:2], ["Portada", "Indice"])
        self.assertIn("[hijos]", titulos)                                  # el PDF anexo cuelga de su TX
        self.assertEqual(r.get_destination_page_number(r.outline[2]), 2)
        self.assertEqual(r.get_destination_page_number(r.outline[4]), 5)   # TX #60 tras los 2 anexos
        self.assertGreaterEqual(len(r.pages[1].get("/Annots") or []), 3)   # el índice enlaza a cada TX

    def test_presupuesto_de_tamano(self):
        import io as _io
        from pypdf import PdfReader
        r = PdfReader(_io.BytesIO(self._generar(COMPENDIO_MAX_MB="0.2")))
        self.assertEqual(len(r.pages), 5)                                  # sin anexos
        self.assertIn("omitido por tamaño", r.pages[2].extract_text())

    def test_texto_latin1_y_plata(self):
        from fin_sys_core import compendio_pdf as cp
        self.assertEqual(cp._t("Año — “ok” 🚕"), 'Año - "ok" ')
        self.assertEqual(cp.plata(1234567.5), "$1.234.567,50")
        self.assertEqual(cp.plata(-25, "USD"), "-USD 25")
        self.assertEqual(cp.nombre_archivo({"folio": "EXP-1", "nombre": "Viaje / Medellín"}, "pdf"), "EXP-1 Viaje Medellín.pdf")


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
                ("get", "/api/compendios"), ("patch", "/api/compendios/1"),
                ("get", "/api/compendios/1/seguimiento"), ("get", "/api/compendios/actividad"),
                ("get", "/api/compendios/1/pdf")]

    def test_pdf_publico_cuenta_la_descarga(self):
        d = {"id": 9, "snapshot": {**_snap(), "folio": "EXP-7"}, "urls": {}, "expira_en": None}
        with mock.patch.object(drv, "para_descarga", return_value=d), \
                mock.patch.object(self.mod, "_pdf", return_value=b"%PDF-1.7 x"), \
                mock.patch.object(drv, "anotar", return_value={"nuevo": True}) as anotar:
            r = self.client.get("/api/publico/compendio/" + "a" * 43 + "/pdf")
            self.client.get("/api/publico/compendio/" + "a" * 43 + "/pdf?previa=1")
        self.assertEqual((r.status_code, r.headers["content-type"]), (200, "application/pdf"))
        self.assertTrue(r.headers["content-disposition"].startswith('attachment; filename="EXP-7 Septiembre.pdf"'))
        self.assertEqual(r.headers["x-robots-tag"], "noindex, nofollow")
        self.assertEqual(anotar.call_count, 1)                              # ?previa=1 no cuenta
        self.assertEqual(anotar.call_args.args[:2], (9, "pdf"))
        with mock.patch.object(drv, "para_descarga", side_effect=drv.NoDisponible()):
            self.assertEqual(self.client.get("/api/publico/compendio/x/pdf").status_code, 404)

    def test_pdf_ritmo_estricto(self):
        with mock.patch.object(drv, "para_descarga", side_effect=drv.NoDisponible()):
            codigos = [self.client.get("/api/publico/compendio/x/pdf").status_code for _ in range(7)]
        self.assertEqual(codigos[-1], 429)

    def test_evento_del_visor(self):   # CA-136-14
        ruta = "/api/publico/compendio/" + "a" * 43 + "/evento"
        with mock.patch.object(drv, "evento_publico", return_value={"nuevo": True}) as m:
            r = self.client.post(ruta, json={"tipo": "tx", "i": 2}, headers={"User-Agent": UA_ANDROID})
        self.assertEqual(r.status_code, 204)
        self.assertEqual(m.call_args.args[1:3], ("tx", 2))
        self.assertEqual(m.call_args.args[4], UA_ANDROID)
        with mock.patch.object(drv, "evento_publico", side_effect=drv.NoDisponible()):
            self.assertEqual(self.client.post(ruta, json={"tipo": "tx", "i": 99}).status_code, 404)

    def test_primera_apertura_avisa_en_segundo_plano(self):   # CA-136-12
        snap = {**_snap(), "_id": 9}
        with mock.patch.object(drv, "abrir", return_value=snap), \
                mock.patch.object(drv, "anotar", return_value={"nuevo": True, "primera": True, "folio": "EXP-7",
                                                               "nombre": "Viaje", "dispositivo": "📱 Android"}) as anotar, \
                mock.patch.object(aviso, "activo", return_value=True), \
                mock.patch.object(aviso, "avisar_primera_apertura") as avisar:
            r = self.client.get("/c/" + "a" * 43, headers={"User-Agent": UA_ANDROID})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(anotar.call_args.args[:2], (9, "abrio"))
        avisar.assert_called_once_with("EXP-7", "Viaje", "📱 Android")
        self.assertNotIn('"_id"', r.text)
        with mock.patch.object(drv, "abrir", return_value={**_snap(), "_id": 9}), \
                mock.patch.object(drv, "anotar", return_value={"nuevo": True, "primera": False}), \
                mock.patch.object(aviso, "avisar_primera_apertura") as avisar:
            self.client.get("/c/" + "a" * 43)
        avisar.assert_not_called()

    def test_vista_previa_interna_no_cuenta(self):
        with mock.patch.object(drv, "abrir", return_value={**_snap(), "_id": 9}), \
                mock.patch.object(drv, "anotar") as anotar:
            r = self.client.get("/c/" + "a" * 43 + "?previa=1")
        self.assertEqual(r.status_code, 200)
        anotar.assert_not_called()
        self.assertIn('"previa": true', r.text)
        url = BUCKET + "evidence/f.jpg"
        with mock.patch.object(drv, "soporte", return_value={"url": url, **drv.describir_soporte(url), "_id": 9}), \
                mock.patch.object(self.mod, "_traer", return_value=b"jpg"), mock.patch.object(drv, "anotar") as anotar:
            self.client.get("/api/publico/compendio/" + "a" * 43 + "/soporte/0/0?previa=1")
        anotar.assert_not_called()

    def test_si_el_registro_falla_la_pagina_igual_sale(self):
        with mock.patch.object(drv, "abrir", return_value={**_snap(), "_id": 9}), \
                mock.patch.object(drv, "anotar", side_effect=_PgError("relation does not exist")):
            self.assertEqual(self.client.get("/c/" + "a" * 43).status_code, 200)

    def test_ver_comprobante_se_anota(self):
        url = BUCKET + "evidence/f.jpg"
        with mock.patch.object(drv, "soporte", return_value={"url": url, **drv.describir_soporte(url), "_id": 9}), \
                mock.patch.object(self.mod, "_traer", return_value=b"jpg"), \
                mock.patch.object(drv, "anotar", return_value={"nuevo": True}) as anotar:
            r = self.client.get("/api/publico/compendio/" + "a" * 43 + "/soporte/3/1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((anotar.call_args.args[0], anotar.call_args.args[1], anotar.call_args.args[4:6]),
                         (9, "comprobante", (3, 1)))

    def test_seguimiento_y_actividad(self):
        with mock.patch.object(drv, "seguimiento", return_value={"resumen": {"aperturas": 2}}):
            r = self.client.get("/api/compendios/9/seguimiento", headers=self.contador)
        self.assertEqual((r.status_code, r.json()["resumen"]["aperturas"]), (200, 2))
        with mock.patch.object(drv, "actividad", side_effect=_PgError("relation does not exist")):
            r = self.client.get("/api/compendios/actividad", headers=self.contador)
        self.assertEqual((r.status_code, r.json()), (200, []))

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
