# -*- coding: utf-8 -*-
"""Tests puros: listas del bot sin catálogos ni recortes en silencio (estándar
de consultas, cierre de H3 — 16-oct-2026). Sin BD: cursor falso.

- «👤 Tercero» usa la consulta acotada de la búsqueda (últimas VENTANA_USO TX),
  nunca un GROUP BY sobre todas las transacciones.
- «Cuenta: nombre» y «Empresa: nombre» al responder el borrador, resueltos de
  forma DETERMINISTA (Regla 6b): igual o única → se aplica; varias → botones
  solo de esas; ninguna → no se toca nada.
- Los botones de cuentas, empresas y etiquetas avisan cuando la lista quedó
  recortada (antes lo que pasaba del tope nunca aparecía).

    python -m unittest tests.test_bot_listas
"""
import os
import sys
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import bot_driver  # noqa: E402
import db_pool     # noqa: E402

LINK = {"id": 7, "hub_user_id": "u-1", "status": "ACTIVO", "default_portfolio": "Negocio A"}


class _Cur:
    """Devuelve las filas de la primera regla cuyo fragmento está en el SQL."""

    def __init__(self, *reglas):
        self.reglas = list(reglas)
        self.sqls, self.params, self._rows = [], [], []
        self.connection = mock.MagicMock()

    def execute(self, sql, params=None):
        self.sqls.append(sql)
        self.params.append(params)
        self._rows = next((list(f) for frag, f in self.reglas if frag in sql), [])

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None


def _callback(cur, data):
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    with mock.patch.object(db_pool, "get_conn", return_value=conn), \
            mock.patch.object(db_pool, "put_conn"), \
            mock.patch.object(bot_driver, "_get_link", return_value=LINK):
        return bot_driver.handle_callback("telegram", "123", data)


def _datas(filas):
    return [d for fila in filas for _, d in fila]


class TestTercerosRecientes(unittest.TestCase):
    def test_consulta_acotada_sin_generico(self):
        filas = [(i, "CC", str(1000 + i), f"T{i}", None, 3) for i in range(1, 10)]
        cur = _Cur(("FROM third_parties", filas))
        r = bot_driver._terceros_recientes(cur, 8)
        sql, p = cur.sqls[0], cur.params[0]
        self.assertIn("FROM transactions WHERE third_party_id IS NOT NULL ORDER BY id DESC "
                      "LIMIT %(ventana)s", sql)
        self.assertNotIn("GROUP BY third_party_id", sql)      # la consulta vieja
        self.assertEqual(p["excluir"], bot_driver._TERCERO_GENERICO)
        self.assertEqual(len(r), 8, "pide uno de más pero devuelve el tope")
        self.assertEqual(r[0], {"id": 1, "identification_type": "CC",
                                "identification_number": "1001", "name": "T1"})


class TestParseMarcadores(unittest.TestCase):
    def test_cuenta_y_empresa(self):
        r = bot_driver._parse_reply("pago luz\nCuenta: Nequi  Ahorros\nEmpresa: Constructora Blu")
        self.assertEqual((r["concepto"], r["cuenta"], r["empresa"]),
                         ("pago luz", "Nequi Ahorros", "Constructora Blu"))

    def test_en_la_misma_linea(self):
        r = bot_driver._parse_reply("almuerzo equipo cuenta: Bancolombia")
        self.assertEqual((r["concepto"], r["cuenta"]), ("almuerzo equipo", "Bancolombia"))

    def test_sin_dos_puntos_es_concepto(self):
        r = bot_driver._parse_reply("cuenta de cobro abril empresa nueva")
        self.assertEqual(r["concepto"], "cuenta de cobro abril empresa nueva")
        self.assertNotIn("cuenta", r)
        self.assertNotIn("empresa", r)


class TestElegirPorNombre(unittest.TestCase):
    C = [(1, "Bancolombia Ahorros", "a"), (2, "Bancolombia", "b"), (3, "Crédito Banco", "c")]

    def test_igual_gana_aunque_otras_contengan(self):
        self.assertEqual(bot_driver._elegir_por_nombre("bancolombia", self.C), ("uno", self.C[1]))

    def test_una_sola_que_contiene_y_sin_tildes(self):
        self.assertEqual(bot_driver._elegir_por_nombre("credito", self.C), ("uno", self.C[2]))
        self.assertEqual(bot_driver._elegir_por_nombre("ahorros", self.C), ("uno", self.C[0]))

    def test_varias_y_homonimas(self):
        self.assertEqual(bot_driver._elegir_por_nombre("banc", self.C), ("varias", self.C))
        dobles = [(4, "Caja", "x"), (5, "caja", "y")]
        self.assertEqual(bot_driver._elegir_por_nombre("Caja", dobles), ("varias", dobles))

    def test_ninguna(self):
        self.assertEqual(bot_driver._elegir_por_nombre("davivienda", self.C), ("ninguna", None))


class TestPonerPorNombre(unittest.TestCase):
    def test_cuenta_unica_se_aplica(self):
        cur = _Cur(("FROM user_accounts", [(5, "Nequi", None)]))
        with mock.patch.object(bot_driver, "editar_draft",
                               return_value={"payload": {"payment_method": "Nequi"}}) as ed:
            r = bot_driver._poner_por_nombre(cur, LINK, 9, "cuenta", "nequi")
        ed.assert_called_once_with(9, {"account_id": 5}, hub_user_id="u-1")
        cur.connection.commit.assert_called_once()        # antes de la otra conexión
        self.assertEqual(r["nota"], "💳 Cuenta → Nequi")
        self.assertIn("LIKE %(contiene)s", cur.sqls[0])
        self.assertEqual((cur.params[0]["contiene"], cur.params[0]["lim"]),
                         ("%nequi%", bot_driver._TOPE_COINCIDENCIAS + 1))

    def test_menos_de_tres_letras_solo_el_nombre_igual(self):
        cur = _Cur(("FROM user_accounts", [(3, "AV", None)]))
        with mock.patch.object(bot_driver, "editar_draft", return_value={"payload": {}}):
            r = bot_driver._poner_por_nombre(cur, LINK, 9, "cuenta", "av")
        self.assertNotIn("LIKE", cur.sqls[0])
        self.assertIn("= %(igual)s", cur.sqls[0])
        self.assertEqual(r["nota"], "💳 Cuenta → AV")

    def test_cuenta_con_varias_muestra_solo_esas(self):
        cur = _Cur(("FROM user_accounts", [(5, "Banco A", None), (8, "Banco B", None)]))
        with mock.patch.object(bot_driver, "editar_draft") as ed:
            r = bot_driver._poner_por_nombre(cur, LINK, 9, "cuenta", "banco")
        ed.assert_not_called()
        self.assertEqual(_datas(r["botones"]), ["accset:9:o:5", "accset:9:o:8", "accback:9"])
        self.assertIn("hay varias cuentas", r["nota"])

    def test_ninguna_no_toca_nada(self):
        cur = _Cur(("FROM entities", []))
        with mock.patch.object(bot_driver, "editar_draft") as ed:
            r = bot_driver._poner_por_nombre(cur, LINK, 9, "empresa", "Inexistente")
        ed.assert_not_called()
        self.assertEqual(r, {"nota": "🏢 No encontré ninguna empresa «Inexistente»: no la cambié."})

    def test_empresa_unica_usa_su_portafolio(self):
        cur = _Cur(("FROM entities", [(22, "Constructora Blu", "EMPRESA")]))
        with mock.patch.object(bot_driver, "_portafolio_de_entidad", return_value="Constructora Blu") as pf, \
                mock.patch.object(bot_driver, "editar_draft", return_value={"payload": {}}) as ed:
            r = bot_driver._poner_por_nombre(cur, LINK, 9, "empresa", "constructora")
        pf.assert_called_once_with(cur, 22)
        ed.assert_called_once_with(9, {"portfolio_name": "Constructora Blu"}, hub_user_id="u-1")
        self.assertEqual(r["nota"], "🏢 Empresa → Constructora Blu")
        self.assertIn("'ARCHIVADA'", cur.sqls[0])

    def test_empresas_varias_con_icono_y_tope(self):
        filas = [(i, f"Obra {i}", "PROYECTO") for i in range(1, bot_driver._TOPE_COINCIDENCIAS + 2)]
        cur = _Cur(("FROM entities", filas))
        r = bot_driver._poner_por_nombre(cur, LINK, 9, "empresa", "obra")
        self.assertEqual(len(r["botones"]), bot_driver._TOPE_COINCIDENCIAS + 1)   # + « Volver
        self.assertEqual(r["botones"][0], [("📐 Obra 1", "empset:9:1")])
        self.assertIn("Hay más", r["nota"])

    def test_error_de_editar_draft_se_devuelve(self):
        cur = _Cur(("FROM user_accounts", [(5, "Nequi", None)]))
        with mock.patch.object(bot_driver, "editar_draft", return_value={"error": "No editable"}):
            self.assertEqual(bot_driver._poner_por_nombre(cur, LINK, 9, "cuenta", "Nequi"), "No editable")


class TestFlujoReply(unittest.TestCase):
    def test_botonera_del_tercero_tiene_prioridad(self):
        cur = _Cur(("FROM user_accounts", [(5, "Banco A", None), (8, "Banco B", None)]),
                   ("SELECT payload FROM transaction_drafts", [({"type": "GASTO"},)]))
        candidatos = [{"id": 1, "name": "Ana", "identification_type": "CC", "identification_number": "1"},
                      {"id": 2, "name": "Ana M", "identification_type": "CC", "identification_number": "2"}]
        with mock.patch.object(bot_driver, "_resolver_tercero_dictado",
                               return_value=("elegir", candidatos, False)), \
                mock.patch.object(bot_driver, "_tomar_pendiente"), \
                mock.patch.object(bot_driver, "render_summary", return_value="RESUMEN"):
            r = bot_driver._flujo_reply(cur, LINK, 9, "Tercero: Ana\nCuenta: banco")
        self.assertEqual(_datas(r["buttons"])[:2], ["tpset:9:1", "tpset:9:2"])
        self.assertIn("La cuenta elígela después", r["text"])

    def test_solo_cuenta_con_varias_deja_sus_botones(self):
        cur = _Cur(("FROM user_accounts", [(5, "Banco A", None), (8, "Banco B", None)]),
                   ("SELECT payload FROM transaction_drafts", [({"type": "GASTO"},)]))
        with mock.patch.object(bot_driver, "render_summary", return_value="RESUMEN"):
            r = bot_driver._flujo_reply(cur, LINK, 9, "Cuenta: banco")
        self.assertEqual(_datas(r["buttons"]), ["accset:9:o:5", "accset:9:o:8", "accback:9"])


class TestAvisoDeListaRecortada(unittest.TestCase):
    def test_etiquetas(self):
        cur = _Cur(("FROM tag_definitions", [(i, f"e{i}") for i in range(bot_driver._TOPE_ETIQUETAS + 1)]))
        avisos = []
        filas = bot_driver._botones_tags(cur, 9, {"tags": []}, avisos)
        self.assertEqual(len(filas), bot_driver._TOPE_ETIQUETAS + 1)   # + ➕ / ✔
        self.assertIn("Etiqueta: nombre", avisos[0])
        self.assertIn(f"LIMIT {bot_driver._TOPE_ETIQUETAS + 1}", cur.sqls[0])
        avisos = []
        bot_driver._botones_tags(_Cur(("FROM tag_definitions", [(1, "obra")])), 9, {"tags": []}, avisos)
        self.assertEqual(avisos, [])

    def test_cuentas_por_boton(self):
        cuentas = [(i, f"Cuenta {i}") for i in range(1, bot_driver._TOPE_CUENTAS + 2)]
        out = _callback(_Cur(("FROM user_accounts", cuentas)), "accsel:9:o")
        self.assertEqual(len(out["edit_buttons"]), bot_driver._TOPE_CUENTAS + 1)   # + « Volver
        self.assertIn("Cuenta: nombre", out["alert"])
        out = _callback(_Cur(("FROM user_accounts", cuentas[:3])), "accsel:9:o")
        self.assertEqual(out["alert"], "Elige la cuenta de pago")

    def test_empresas_por_boton(self):
        filas = [(i, f"E{i}", "EMPRESA") for i in range(1, bot_driver._TOPE_EMPRESAS + 2)]
        out = _callback(_Cur(("FROM entities", filas)), "emp:9")
        self.assertEqual(len(out["edit_buttons"]), bot_driver._TOPE_EMPRESAS + 1)
        self.assertIn("Empresa: nombre", out["alert"])

    def test_comando_empresa_dice_cuantas_faltan(self):
        cur = _Cur(("FROM entities", [(f"E{i}", 30) for i in range(bot_driver._TOPE_EMPRESAS)]))
        texto = bot_driver._cmd_empresa(cur, LINK, "")
        self.assertIn(f"… y {30 - bot_driver._TOPE_EMPRESAS} más", texto)

    def test_callbacks_caben_en_64_bytes(self):
        for d in ("accset:999999999:o:999999999", "empset:999999999:999999999", "accback:999999999"):
            self.assertLessEqual(len(d.encode()), 64)


if __name__ == "__main__":
    unittest.main()
