# -*- coding: utf-8 -*-
"""Tests puros de la etapa 09.G: completar tercero y concepto desde el chat.

Sin BD: parseo del reply (una o varias líneas, con documento en la misma
línea), búsqueda determinista de terceros con cursor falso, decisión
asignar / crear / elegir y botonera. Regla 6b: nada se adivina — el documento
manda, y con nombres parecidos decide el humano (así no hay duplicados).
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import bot_driver  # noqa: E402


def _dig(s):
    return "".join(c for c in (s or "") if c.isdigit())


class _FakeCursor:
    """third_parties en memoria: filas (id, tipo, número, nombre, phone).
    Enruta por la forma del SQL de bot_driver (documento, dígitos, nombre)."""

    def __init__(self, terceros=()):
        self.terceros = list(terceros)
        self._rows = []
        self.sqls = []

    def execute(self, sql, params=None):
        self.sqls.append(sql)
        if "COALESCE(phone" in sql and "regexp_replace(identification_number" in sql:
            dig, like, _ = params                       # _buscar_terceros por dígitos
            cel = like.lstrip("%")
            self._rows = [t for t in self.terceros
                          if (not t[2].startswith("SN-") and _dig(t[2]) == dig)
                          or (_dig(t[4]) and _dig(t[4]).endswith(cel))]
        elif "regexp_replace(identification_number" in sql:
            gen, dig = params                           # _tercero_por_documento
            self._rows = [t for t in self.terceros
                          if not t[2].startswith("SN-") and t[2] != gen and _dig(t[2]) == dig][:1]
        elif "translate(lower(name)" in sql:
            *likes, gen, exacto, _ = params             # _buscar_terceros por nombre
            palabras = [p.strip("%") for p in likes]
            self._rows = [t for t in self.terceros
                          if t[2] != gen and all(p in bot_driver._norm(t[3]) for p in palabras)]
            self._rows.sort(key=lambda t: (bot_driver._norm(t[3]) != exacto, t[3]))
        else:
            self._rows = []

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


TERCEROS = [
    (1, "NIT", "999999999", "Sin especificar", None),
    (2, "CC", "10203040", "Juan Pérez", "+57 319 330 1184"),
    (3, "CC", "55667788", "Juan Camilo", None),
    (4, "NIT", "900.123.456-7", "Éxito S.A.", None),
    (5, "NIT", "SN-1a0df8de7e8", "Leidy Daniela Molina Martínez", None),   # provisional
]


class TestParseReply(unittest.TestCase):

    def test_concepto_con_prefijo(self):
        self.assertEqual(bot_driver._parse_reply("Concepto: arriendo septiembre"),
                         {"concepto": "arriendo septiembre", "tercero": None})
        self.assertEqual(bot_driver._parse_reply("c: mercado")["concepto"], "mercado")

    def test_sin_prefijo_es_concepto_literal(self):
        self.assertEqual(bot_driver._parse_reply("fue el arriendo"),
                         {"concepto": "fue el arriendo", "tercero": None})

    def test_tercero_solo_nombre(self):
        r = bot_driver._parse_reply("Tercero: Juan Pérez")
        self.assertIsNone(r["concepto"])
        self.assertEqual(r["tercero"]["nombre"], "Juan Pérez")
        self.assertIsNone(r["tercero"]["num"])
        self.assertFalse(r["tercero"]["nuevo"])

    def test_tercero_solo_numero_es_busqueda(self):
        t = bot_driver._parse_reply("t: 3193301184")["tercero"]
        self.assertEqual((t["buscar_num"], t["nombre"]), ("3193301184", None))
        t = bot_driver._parse_reply("Tercero: 10.203.040")["tercero"]
        self.assertEqual(t["buscar_num"], "10203040")

    def test_tercero_nuevo_con_y_sin_documento(self):
        t = bot_driver._parse_reply("Tercero nuevo: Ana Gómez, CC 1.020.304")["tercero"]
        self.assertEqual((t["nombre"], t["tipo"], t["num"], t["nuevo"]),
                         ("Ana Gómez", "CC", "1020304", True))
        t = bot_driver._parse_reply("tercero nuevo: Ferretería El Tornillo, NIT 900111222")["tercero"]
        self.assertEqual((t["nombre"], t["tipo"], t["num"]), ("Ferretería El Tornillo", "NIT", "900111222"))
        t = bot_driver._parse_reply("Tercero nuevo: Ana Gómez")["tercero"]
        self.assertEqual((t["nombre"], t["num"], t["nuevo"]), ("Ana Gómez", None, True))

    def test_vacio(self):
        self.assertEqual(bot_driver._parse_reply("   "), {"concepto": None, "tercero": None})

    # ── Los dos mensajes reales de Andrés que la primera versión se tragó ──

    def test_caso_real_30_sep_dos_lineas_concepto_y_tercero_con_cc(self):
        r = bot_driver._parse_reply("abono leidy cuota  1V\n"
                                    "Tercero : leidy daniela Molina  cc 1007289007")
        self.assertEqual(r["concepto"], "abono leidy cuota 1V")
        t = r["tercero"]
        self.assertEqual((t["nombre"], t["tipo"], t["num"]), ("leidy daniela Molina", "CC", "1007289007"))
        self.assertFalse(t["nuevo"])

    def test_caso_real_22_sep_todo_en_una_linea(self):
        r = bot_driver._parse_reply("Concepto dulces en colombina tercero: jorge Aguilar cc 100753782")
        self.assertEqual(r["concepto"], "dulces en colombina")
        self.assertEqual((r["tercero"]["nombre"], r["tercero"]["num"]), ("jorge Aguilar", "100753782"))

    def test_orden_indiferente_y_lineas_vacias(self):
        r = bot_driver._parse_reply("Tercero: Juan\n\narriendo octubre\n")
        self.assertEqual(r["concepto"], "arriendo octubre")
        self.assertEqual(r["tercero"]["nombre"], "Juan")

    def test_tercero_con_celular_correo_y_nit(self):
        t = bot_driver._parse_reply(
            "Tercero: Ana Ruiz cc 52.111.222 cel 300 123 4567 ana.ruiz@correo.com")["tercero"]
        self.assertEqual((t["nombre"], t["num"], t["phone"], t["email"]),
                         ("Ana Ruiz", "52111222", "3001234567", "ana.ruiz@correo.com"))
        t = bot_driver._parse_reply("Tercero: Ferretería X nit 900.123.456-7")["tercero"]
        self.assertEqual((t["nombre"], t["tipo"], t["num"]), ("Ferretería X", "NIT", "900.123.456-7"))

    def test_nombres_con_silabas_de_marcadores_no_confunden(self):
        t = bot_driver._parse_reply("Tercero: Cesar Benito Estela cc 123456")["tercero"]
        self.assertEqual((t["nombre"], t["num"]), ("Cesar Benito Estela", "123456"))


class TestBuscarTerceros(unittest.TestCase):

    def test_por_nombre_unico_sin_tildes_ni_mayusculas(self):
        r = bot_driver._buscar_terceros(_FakeCursor(TERCEROS), "perez")
        self.assertEqual([t["id"] for t in r], [2])

    def test_todas_las_palabras_aunque_falten_del_medio(self):
        r = bot_driver._buscar_terceros(_FakeCursor(TERCEROS), "leidy molina")
        self.assertEqual([t["id"] for t in r], [5])

    def test_por_nombre_varios_el_humano_decide(self):
        r = bot_driver._buscar_terceros(_FakeCursor(TERCEROS), "juan")
        self.assertEqual({t["id"] for t in r}, {2, 3})

    def test_por_documento_y_celular(self):
        cur = _FakeCursor(TERCEROS)
        self.assertEqual([t["id"] for t in bot_driver._buscar_terceros(cur, "10.203.040")], [2])
        self.assertEqual([t["id"] for t in bot_driver._buscar_terceros(cur, "3193301184")], [2])
        self.assertEqual([t["id"] for t in bot_driver._buscar_terceros(cur, "+57 319 330 1184")], [2])
        self.assertEqual(bot_driver._buscar_terceros(cur, "9001234567")[0]["name"], "Éxito S.A.")

    def test_sin_coincidencia_y_generico_excluido(self):
        cur = _FakeCursor(TERCEROS)
        self.assertEqual(bot_driver._buscar_terceros(cur, "nadie"), [])
        self.assertEqual(bot_driver._buscar_terceros(cur, "especificar"), [])
        self.assertEqual(bot_driver._buscar_terceros(cur, ""), [])

    def test_documento_exacto_ignora_puntos_y_provisionales(self):
        cur = _FakeCursor(TERCEROS)
        self.assertEqual(bot_driver._tercero_por_documento(cur, "900123456-7")["id"], 4)
        self.assertIsNone(bot_driver._tercero_por_documento(cur, "10878"))        # dígitos de un SN-
        self.assertIsNone(bot_driver._tercero_por_documento(cur, "999999999"))    # el genérico
        self.assertIsNone(bot_driver._tercero_por_documento(cur, "12"))

    def test_tercero_dict_incluye_phone(self):
        d = bot_driver._tercero_dict(TERCEROS[1])
        self.assertEqual(d["phone"], "+57 319 330 1184")
        self.assertNotIn("phone", bot_driver._tercero_dict(TERCEROS[2]))


class TestResolverTerceroDictado(unittest.TestCase):
    """El corazón anti-duplicados: documento manda; parecidos → decide el humano."""

    def _r(self, texto, terceros=TERCEROS):
        t = bot_driver._parse_reply(texto)["tercero"]
        return bot_driver._resolver_tercero_dictado(_FakeCursor(terceros), t)

    def test_documento_existente_asigna_aunque_el_nombre_venga_distinto(self):
        accion, dato, _ = self._r("Tercero: juancho perez cc 10.203.040")
        self.assertEqual((accion, dato["id"]), ("asignar", 2))

    def test_documento_nuevo_sin_parecidos_crea(self):
        self.assertEqual(self._r("Tercero: Sandra Jimenez cc 52111222")[0], "crear")

    def test_documento_nuevo_con_parecidos_pide_elegir_y_permite_crear(self):
        accion, dato, crear = self._r("Tercero: leidy daniela Molina cc 1007289007")
        self.assertEqual(accion, "elegir")
        self.assertEqual([t["id"] for t in dato], [5])          # la provisional sin documento
        self.assertTrue(crear)

    def test_solo_nombre_unico_asigna(self):
        accion, dato, _ = self._r("Tercero: exito")
        self.assertEqual((accion, dato["id"]), ("asignar", 4))

    def test_solo_nombre_varios_elige_sin_crear(self):
        accion, dato, crear = self._r("Tercero: juan")
        self.assertEqual((accion, len(dato), crear), ("elegir", 2, False))

    def test_solo_nombre_inexistente_explica_como_crearlo(self):
        accion, msg, _ = self._r("Tercero: Pedro Inexistente")
        self.assertEqual(accion, "nada")
        self.assertIn("cc", msg)

    def test_tercero_nuevo_con_nombre_ya_existente_no_duplica(self):
        accion, dato, _ = self._r("Tercero nuevo: JUAN PEREZ")
        self.assertEqual((accion, dato["id"]), ("asignar", 2))

    def test_tercero_nuevo_sin_parecidos_crea_provisional(self):
        self.assertEqual(self._r("Tercero nuevo: Panadería La Espiga")[0], "crear")

    def test_solo_numero_por_celular_o_no_encontrado(self):
        accion, dato, _ = self._r("Tercero: 3193301184")
        self.assertEqual((accion, dato["id"]), ("asignar", 2))
        accion, msg, _ = self._r("Tercero: 3000000000")
        self.assertEqual(accion, "nada")
        self.assertIn("3000000000", msg)

    def test_documento_sin_nombre_y_sin_existir_pide_el_nombre(self):
        accion, msg, _ = self._r("Tercero: cc 77889900")
        self.assertEqual(accion, "nada")
        self.assertIn("nombre", msg.lower())

    def test_solo_celular_con_prefijo_busca_por_celular_y_jamas_crea(self):
        # "cel 319…" deja el nombre vacío: se busca por igualdad del celular…
        accion, dato, _ = self._r("Tercero: cel 319 330 1184")
        self.assertEqual((accion, dato["id"]), ("asignar", 2))
        # …y sin coincidencia NO se crea nada (ni con «Tercero nuevo»), se pide el nombre
        for texto in ("Tercero nuevo: cel 3000000000", "Tercero: tel 3000000000",
                      "Tercero nuevo: alguien@correo.com"):
            accion, msg, crear = self._r(texto)
            self.assertEqual((accion, crear), ("nada", False), texto)
            self.assertNotIn("None", msg)
            self.assertIn("nombre", msg.lower())


class TestPendienteCorresponde(unittest.TestCase):
    """Un documento dictado solo se le completa a un provisional cuyo nombre
    coincide con lo dictado (mismo criterio con que se ofrecieron los candidatos)."""

    def test_mismo_criterio_que_los_candidatos(self):
        p = {"nombre": "leidy molina", "num": "1007289007"}
        self.assertTrue(bot_driver._pendiente_corresponde(p, "Leidy Daniela Molina Martínez"))
        self.assertTrue(bot_driver._pendiente_corresponde({"nombre": "LEIDY"}, "leidy daniela"))
        self.assertFalse(bot_driver._pendiente_corresponde(p, "Ferretería X"))
        self.assertFalse(bot_driver._pendiente_corresponde(p, "Leidy Rojas"))       # falta «molina»
        self.assertFalse(bot_driver._pendiente_corresponde({"nombre": None, "num": "1"}, "Leidy"))
        self.assertFalse(bot_driver._pendiente_corresponde(None, "Leidy"))


class TestBotones(unittest.TestCase):

    def test_botonera_tiene_tercero_y_concepto_y_cabe_en_64_bytes(self):
        filas = bot_driver._botones_borrador(123456)
        datas = [d for fila in filas for _, d in fila]
        self.assertIn("tp:123456", datas)
        self.assertIn("cpt:123456", datas)
        for d in datas:
            self.assertLessEqual(len(d.encode()), 64)

    def test_botones_terceros_muestran_documento_crear_y_volver(self):
        candidatos = [bot_driver._tercero_dict(t) for t in (TERCEROS[1], TERCEROS[4])]
        filas = bot_driver._botones_terceros(7, candidatos, crear="leidy daniela Molina")
        self.assertEqual(filas[0][0], ("Juan Pérez · CC 10203040", "tpset:7:2"))
        self.assertIn("sin documento", filas[1][0][0])
        self.assertEqual(filas[2][0], ("➕ Crear nuevo: leidy daniela Molina", "tpnew:7"))
        self.assertEqual(filas[-1][0][1], "tpback:7")
        for fila in filas:
            for etiqueta, data in fila:
                self.assertLessEqual(len(etiqueta), 60)
                self.assertLessEqual(len(data.encode()), 64)

    def test_botones_terceros_sin_crear(self):
        filas = bot_driver._botones_terceros(7, [bot_driver._tercero_dict(TERCEROS[1])])
        self.assertEqual([f[0][1] for f in filas], ["tpset:7:2", "tpback:7"])


if __name__ == "__main__":
    unittest.main()
