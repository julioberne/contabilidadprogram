# -*- coding: utf-8 -*-
"""Resolución antiduplicados de terceros (pedido de Andrés, 2026-09-11):
registrar una TX escribiendo solo el NOMBRE del tercero creaba uno nuevo
cada vez (todo caía al genérico 999999999, que además se RENOMBRABA con
cada registro). Reglas de _asegurar_tercero:
  1) número real          → upsert por número (contacto rellena sin destruir)
  2) solo nombre          → reutiliza el registrado con ese nombre, o crea
                            uno propio con número provisional SN-<epoch>
  3) sin nombre ni número → genérico, SIEMPRE "Sin especificar" y sin contacto
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fin_sys_core"))

import database_driver  # noqa: E402
from database_driver import _asegurar_tercero, TERCERO_GENERICO_NUM  # noqa: E402


class FakeCursor:
    """Registra cada execute y sirve fetchone desde una cola predefinida."""

    def __init__(self, fetchones):
        self.ejecutadas = []          # [(sql, params), ...]
        self._fetchones = list(fetchones)

    def execute(self, sql, params=None):
        self.ejecutadas.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self._fetchones.pop(0)


class TestAsegurarTercero(unittest.TestCase):

    def test_numero_real_upsert_directo(self):
        cur = FakeCursor([(7,)])
        tp = {"identification_type": "NIT", "identification_number": "100736548",
              "name": "Ferretería El Tornillo", "phone": "3001234567"}
        self.assertEqual(_asegurar_tercero(cur, tp), 7)
        self.assertEqual(len(cur.ejecutadas), 1)
        sql, params = cur.ejecutadas[0]
        self.assertIn("ON CONFLICT (identification_number)", sql)
        self.assertEqual(params[1], "100736548")
        self.assertEqual(params[2], "Ferretería El Tornillo")
        self.assertEqual(params[4], "3001234567")

    def test_solo_nombre_reutiliza_al_registrado(self):
        """El caso del reporte: el tercero ya existe (p.ej. completado en el
        comprobante) y se registra otra TX escribiendo solo su nombre."""
        cur = FakeCursor([(5,)])
        tp = {"identification_type": "NIT", "identification_number": "",
              "name": "  kevin mateo GONZÁLEZ agudelo ", "email": "nuevo@mail.com"}
        self.assertEqual(_asegurar_tercero(cur, tp), 5)
        self.assertEqual(len(cur.ejecutadas), 2)
        sql_busqueda, params_busqueda = cur.ejecutadas[0]
        self.assertIn("lower(btrim(name))", sql_busqueda)
        self.assertEqual(params_busqueda[1], TERCERO_GENERICO_NUM)  # el genérico jamás cuenta como match
        sql_contacto, params_contacto = cur.ejecutadas[1]
        self.assertIn("UPDATE third_parties", sql_contacto)
        self.assertIn("COALESCE", sql_contacto)          # rellena sin destruir
        self.assertEqual(params_contacto[0], "nuevo@mail.com")
        self.assertEqual(params_contacto[-1], 5)

    def test_solo_nombre_nuevo_crea_con_numero_provisional(self):
        cur = FakeCursor([None, (11,)])   # búsqueda sin match → INSERT
        tp = {"identification_type": "CC", "identification_number": None,
              "name": "Proveedor Nuevo SAS"}
        self.assertEqual(_asegurar_tercero(cur, tp), 11)
        sql_insert, params_insert = cur.ejecutadas[1]
        self.assertIn("INSERT INTO third_parties", sql_insert)
        self.assertTrue(str(params_insert[1]).startswith("SN-"))   # jamás el genérico
        self.assertEqual(params_insert[2], "Proveedor Nuevo SAS")
        self.assertEqual(params_insert[0], "CC")

    def test_anonimo_va_al_generico_con_nombre_canonico(self):
        for tp in ({"identification_type": "NIT", "identification_number": "", "name": ""},
                   {"identification_type": "NIT", "identification_number": TERCERO_GENERICO_NUM,
                    "name": "Sin especificar", "phone": "555"}):
            cur = FakeCursor([(1,)])
            self.assertEqual(_asegurar_tercero(cur, tp), 1)
            self.assertEqual(len(cur.ejecutadas), 1)
            _, params = cur.ejecutadas[0]
            self.assertEqual(params[1], TERCERO_GENERICO_NUM)
            self.assertEqual(params[2], "Sin especificar")   # nunca se renombra
            # y el contacto dictado JAMÁS se pega al genérico compartido
            self.assertEqual(params[3:], (None, None, None, None))

    def test_generico_explicito_con_nombre_real_no_lo_renombra(self):
        """Caso bot (draft_builder manda 999999999 + nombre del LLM): debe
        resolverse como 'solo nombre', no como upsert sobre el genérico."""
        cur = FakeCursor([None, (13,)])
        tp = {"identification_type": "NIT", "identification_number": TERCERO_GENERICO_NUM,
              "name": "Ferretería Dictada"}
        self.assertEqual(_asegurar_tercero(cur, tp), 13)
        sql_insert, params_insert = cur.ejecutadas[1]
        self.assertIn("INSERT INTO third_parties", sql_insert)
        self.assertNotEqual(params_insert[1], TERCERO_GENERICO_NUM)
        self.assertTrue(str(params_insert[1]).startswith("SN-"))


if __name__ == "__main__":
    unittest.main()
