# -*- coding: utf-8 -*-
"""Tests puros de la etapa 09.G: completar tercero y concepto desde el chat.

Sin BD: parseo del reply, búsqueda determinista de terceros con cursor falso,
botonera. Regla 6b: nada se adivina — con varios candidatos decide el humano.
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import bot_driver  # noqa: E402


class _FakeCursor:
    """third_parties en memoria: filas (id, tipo, número, nombre, phone)."""

    def __init__(self, terceros=()):
        self.terceros = list(terceros)
        self._rows = []
        self.sqls = []

    def execute(self, sql, params=None):
        self.sqls.append(sql)
        if "regexp_replace(identification_number" in sql:
            dig, like, _ = params
            cel = like.lstrip("%")
            self._rows = [t for t in self.terceros
                          if "".join(c for c in t[2] if c.isdigit()) == dig
                          or "".join(c for c in (t[4] or "") if c.isdigit()).endswith(cel)]
        elif "name ILIKE" in sql:
            q = params[0].strip("%").lower()
            self._rows = [t for t in self.terceros if q in t[3].lower() and t[2] != "999999999"]
            self._rows.sort(key=lambda t: (t[3].lower() != q, t[3]))
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
    (4, "NIT", "900123456", "Éxito S.A.", None),
]


class TestParseReply(unittest.TestCase):

    def test_concepto_con_prefijo(self):
        self.assertEqual(bot_driver._parse_reply("Concepto: arriendo septiembre"),
                         ("concepto", "arriendo septiembre"))
        self.assertEqual(bot_driver._parse_reply("c: mercado"), ("concepto", "mercado"))

    def test_sin_prefijo_es_concepto_literal(self):
        self.assertEqual(bot_driver._parse_reply("fue el arriendo"), ("concepto", "fue el arriendo"))

    def test_tercero(self):
        self.assertEqual(bot_driver._parse_reply("Tercero: Juan Pérez"), ("tercero", "Juan Pérez"))
        self.assertEqual(bot_driver._parse_reply("t: 3193301184"), ("tercero", "3193301184"))

    def test_tercero_nuevo_con_y_sin_documento(self):
        self.assertEqual(bot_driver._parse_reply("Tercero nuevo: Ana Gómez, CC 1.020.304"),
                         ("tercero_nuevo", {"nombre": "Ana Gómez", "tipo": "CC", "num": "1020304"}))
        self.assertEqual(bot_driver._parse_reply("tercero nuevo: Ferretería El Tornillo, NIT 900111222"),
                         ("tercero_nuevo", {"nombre": "Ferretería El Tornillo", "tipo": "NIT", "num": "900111222"}))
        self.assertEqual(bot_driver._parse_reply("Tercero nuevo: Ana Gómez"),
                         ("tercero_nuevo", {"nombre": "Ana Gómez", "tipo": None, "num": None}))

    def test_vacio(self):
        self.assertEqual(bot_driver._parse_reply("   "), (None, None))


class TestBuscarTerceros(unittest.TestCase):

    def test_por_nombre_unico(self):
        r = bot_driver._buscar_terceros(_FakeCursor(TERCEROS), "pérez")
        self.assertEqual([t["id"] for t in r], [2])

    def test_por_nombre_varios_el_humano_decide(self):
        r = bot_driver._buscar_terceros(_FakeCursor(TERCEROS), "juan")
        self.assertEqual({t["id"] for t in r}, {2, 3})

    def test_por_documento_y_celular(self):
        cur = _FakeCursor(TERCEROS)
        self.assertEqual([t["id"] for t in bot_driver._buscar_terceros(cur, "10.203.040")], [2])
        self.assertEqual([t["id"] for t in bot_driver._buscar_terceros(cur, "3193301184")], [2])
        self.assertEqual(bot_driver._buscar_terceros(cur, "900123456")[0]["name"], "Éxito S.A.")

    def test_sin_coincidencia_y_generico_excluido(self):
        cur = _FakeCursor(TERCEROS)
        self.assertEqual(bot_driver._buscar_terceros(cur, "nadie"), [])
        self.assertEqual(bot_driver._buscar_terceros(cur, "especificar"), [])
        self.assertEqual(bot_driver._buscar_terceros(cur, ""), [])

    def test_tercero_dict_incluye_phone(self):
        d = bot_driver._tercero_dict(TERCEROS[1])
        self.assertEqual(d["phone"], "+57 319 330 1184")
        self.assertNotIn("phone", bot_driver._tercero_dict(TERCEROS[2]))


class TestBotones(unittest.TestCase):

    def test_botonera_tiene_tercero_y_concepto_y_cabe_en_64_bytes(self):
        filas = bot_driver._botones_borrador(123456)
        datas = [d for fila in filas for _, d in fila]
        self.assertIn("tp:123456", datas)
        self.assertIn("cpt:123456", datas)
        for d in datas:
            self.assertLessEqual(len(d.encode()), 64)

    def test_botones_terceros_con_volver(self):
        filas = bot_driver._botones_terceros(7, [bot_driver._tercero_dict(t) for t in TERCEROS[1:3]])
        self.assertEqual(filas[0][0][1], "tpset:7:2")
        self.assertEqual(filas[-1][0][1], "tpback:7")


if __name__ == "__main__":
    unittest.main()
