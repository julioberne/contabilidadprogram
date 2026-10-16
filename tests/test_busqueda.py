# -*- coding: utf-8 -*-
"""Búsqueda remota única (estándar de consultas, H3).

- armar_busqueda_terceros: puro (CI sin BD) — escalera por largo, tope, ids.
- Contra la BD (solo lectura, se salta sin DB_HOST): nunca más de `limite`,
  `mas` correcto y resolución por id.

    python -m unittest tests.test_busqueda
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import tests  # noqa: F401,E402

from fin_sys_core.consultas.busqueda import (  # noqa: E402
    LIMITE_MAX, VENTANA_USO, armar_busqueda_terceros, armar_contiene, armar_recientes, digitos,
    normalizar,
)


class TestArmar(unittest.TestCase):
    def test_vacio_trae_los_recientes_con_tope(self):
        sql, p = armar_busqueda_terceros("", 8)
        self.assertIn("ORDER BY u.ultimo DESC", sql)
        self.assertEqual(p["lim"], 9, "pide uno de más para saber si hay más")
        self.assertEqual(p["ventana"], VENTANA_USO)

    def test_el_uso_nunca_agrupa_todas_las_transacciones(self):
        """Antes cada tecla agrupaba TODAS las TX; ahora solo la ventana por llave primaria."""
        for q in ("", "T", "Café", "318 866"):
            sql, p = armar_busqueda_terceros(q, 8)
            self.assertIn("ORDER BY id DESC LIMIT %(ventana)s", sql, q)
            self.assertEqual(p["ventana"], VENTANA_USO)
        for kw in ({"ids": "3"}, {"ident": "900123"}, {"nombre": "Pedro"},
                   {"orden": "nombre", "con_total": True}):
            sql, _ = armar_busqueda_terceros("", 8, **kw)
            self.assertNotIn("transactions", sql, kw)

    def test_recientes_del_bot_sin_generico(self):
        sql, p = armar_recientes(8, excluir_ident="999999999", columnas="tp.id, tp.name")
        self.assertTrue(sql.startswith("SELECT tp.id, tp.name, u.n AS usos"))
        self.assertIn("tp.identification_number <> %(excluir)s", sql)
        self.assertEqual((p["excluir"], p["lim"]), ("999999999", 9))

    def test_una_letra_es_prefijo(self):
        _, p = armar_busqueda_terceros("T", 8)
        self.assertEqual(p["prefijo"], "t%")
        self.assertNotIn("contiene", p)

    def test_dos_o_mas_contiene_y_digitos(self):
        _, p = armar_busqueda_terceros("Café", 8)
        self.assertEqual(p["contiene"], "%cafe%")
        self.assertNotIn("dig", p)
        _, p = armar_busqueda_terceros("318 866", 8)
        self.assertEqual(p["dig"], "%318866%")

    def test_comodines_del_usuario_son_literales(self):
        _, p = armar_busqueda_terceros("50%_x", 8)
        self.assertEqual(p["contiene"], "%50\\%\\_x%")

    def test_tope_y_ids(self):
        _, p = armar_busqueda_terceros("ab", 10_000)
        self.assertEqual(p["lim"], LIMITE_MAX + 1)
        sql, p = armar_busqueda_terceros("", 8, ids="3,7")
        self.assertEqual(p["ids"], [3, 7])
        self.assertIn("tp.id = ANY", sql)
        with self.assertRaises(ValueError):
            armar_busqueda_terceros("", 8, ids="3,x")
        with self.assertRaises(ValueError):
            armar_busqueda_terceros("", 8, ids=",".join(str(i) for i in range(101)))

    def test_nombre_exacto_y_paginado(self):
        sql, p = armar_busqueda_terceros("", 8, nombre="  Pedro   PÉREZ ")
        self.assertEqual(p["nombre"], "pedro pérez")
        self.assertIn("lower(btrim(tp.name)) = %(nombre)s", sql)
        sql, p = armar_busqueda_terceros("ped", 50, despues=("Pedro", 7), orden="nombre", con_total=True)
        self.assertIn("ORDER BY tp.name, tp.id", sql)
        self.assertIn("(tp.name, tp.id) > (%(c_nombre)s, %(c_id)s)", sql)
        self.assertNotIn("OFFSET", sql)
        self.assertEqual((p["c_nombre"], p["c_id"]), ("Pedro", 7))
        with self.assertRaises(ValueError):
            armar_busqueda_terceros("", 8, orden="DROP")

    def test_contiene_de_catalogos_chicos(self):
        sql, p = armar_contiene("user_accounts", "id, name", "Café", 8)
        self.assertTrue(sql.startswith("SELECT id, name FROM user_accounts WHERE TRUE AND "))
        self.assertIn("LIKE %(contiene)s ORDER BY name LIMIT %(lim)s", sql)
        self.assertEqual((p["contiene"], p["lim"]), ("%cafe%", 9))
        sql, _ = armar_contiene("entities", "id", "ab", 8, extra="x = 1", igual_primero=True, minimo=3)
        self.assertIn("WHERE x = 1 AND ", sql)
        self.assertNotIn("LIKE", sql, "con menos del mínimo solo vale el nombre igual")
        self.assertIn("= %(igual)s) DESC, name", sql)

    def test_normalizar(self):
        self.assertEqual(normalizar("  Peña Café "), "pena cafe")
        self.assertEqual(digitos("+57 318-866"), "57318866")


@unittest.skipUnless(os.environ.get("DB_HOST"), "requiere BD")
class TestContraBD(unittest.TestCase):
    def test_tope_mas_e_ids(self):
        from fin_sys_core.consultas.busqueda import buscar_terceros
        r = buscar_terceros("", 3)
        self.assertLessEqual(len(r["items"]), 3)
        if r["mas"]:
            self.assertEqual(len(r["items"]), 3)
        if r["items"]:
            t = r["items"][0]
            for k in ("id", "name", "identification_number", "phone", "email", "address"):
                self.assertIn(k, t)
            uno = buscar_terceros(ids=str(t["id"]))
            self.assertEqual([x["id"] for x in uno["items"]], [t["id"]])
            pref = buscar_terceros(t["name"][:3], 50)
            self.assertIn(t["id"], [x["id"] for x in pref["items"]])
            exacto = buscar_terceros(nombre=t["name"].upper())
            self.assertIn(t["id"], [x["id"] for x in exacto["items"]])
            p1 = buscar_terceros("", 2, orden="nombre", con_total=True)
            sig = p1["siguiente"]
            p2 = (buscar_terceros("", 2, despues=(sig["nombre"], sig["id"]), orden="nombre", con_total=True)
                  if sig else {"items": [], "total": p1["total"]})
            self.assertEqual(p1["total"], p2["total"], "el total no depende del cursor")
            self.assertGreaterEqual(p1["total"], len(p1["items"]))
            self.assertFalse({x["id"] for x in p1["items"]} & {x["id"] for x in p2["items"]})


if __name__ == "__main__":
    unittest.main()
