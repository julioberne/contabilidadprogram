# -*- coding: utf-8 -*-
"""Tests puros de fin_sys_core/terceros_cuentas.py (etapa 09.G §10): normalización
de los medios de pago de un tercero, qué medio trae cada SMS y el cruce por
igualdad. Sin BD. Regla 6b: nada se adivina — igualdad del identificador completo.
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import sms_bancolombia as sms  # noqa: E402
import terceros_cuentas as tc  # noqa: E402


class _FakeCursor:
    """medios: {(tipo, valor): (id, tipo_doc, numero, nombre, phone)}"""

    def __init__(self, medios=None):
        self.medios = dict(medios or {})
        self._rows = []
        self.sqls = []

    def execute(self, sql, params=None):
        self.sqls.append(sql)
        if "FROM third_party_accounts" in sql and params:
            fila = self.medios.get((params[0], params[1]))
            self._rows = [fila] if fila else []
        else:
            self._rows = []

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class TestNormalizar(unittest.TestCase):

    def test_celular(self):
        self.assertEqual(tc.normalizar("celular", "3213795458"), "3213795458")
        self.assertEqual(tc.normalizar("celular", "+57 321 379 5458"), "3213795458")
        self.assertEqual(tc.normalizar("celular", "321-379-5458"), "3213795458")
        self.assertIsNone(tc.normalizar("celular", "1234567890"))     # no empieza por 3
        self.assertIsNone(tc.normalizar("celular", "321379545"))      # 9 dígitos

    def test_cuenta(self):
        self.assertEqual(tc.normalizar("cuenta", "*91232656625"), "91232656625")
        self.assertEqual(tc.normalizar("cuenta", "912-326 56625"), "91232656625")
        self.assertIsNone(tc.normalizar("cuenta", "123"))

    def test_llave_conserva_ceros_y_alias(self):
        self.assertEqual(tc.normalizar("llave", " 0087671656 "), "0087671656")
        self.assertEqual(tc.normalizar("llave", "@AndresJ"), "@andresj")
        self.assertEqual(tc.normalizar("llave", "Ana.Ruiz@Correo.com"), "ana.ruiz@correo.com")
        self.assertIsNone(tc.normalizar("llave", "ab"))

    def test_nombre_banco_mayusculas_sin_tildes(self):
        self.assertEqual(tc.normalizar("nombre_banco", "  Sandra   Jiménez "), "SANDRA JIMENEZ")
        self.assertEqual(tc.normalizar("nombre_banco", "MERCA EXPRESS RP."), "MERCA EXPRESS RP")
        self.assertIsNone(tc.normalizar("nombre_banco", "x"))

    def test_tipo_desconocido(self):
        self.assertIsNone(tc.normalizar("correo", "a@b.co"))
        self.assertIsNone(tc.normalizar("celular", None))

    def test_describir(self):
        self.assertEqual(tc.describir("celular", "3213795458"), "cel 3213795458")
        self.assertEqual(tc.describir("cuenta", "91232656625"), "cuenta *91232656625")
        self.assertEqual(tc.describir("llave", "0087671656"), "llave 0087671656")
        self.assertEqual(tc.describir("nombre_banco", "SANDRA JIMENEZ"), "«SANDRA JIMENEZ»")


class TestMedioDeSms(unittest.TestCase):
    """Qué identificador de la contraparte trae cada plantilla REAL."""

    def _medio(self, texto):
        return tc.medio_de_sms(sms.parsear(texto))

    def test_transferencia_a_celular_y_a_cuenta(self):
        self.assertEqual(self._medio("Bancolombia: Transferiste $50,000.00 desde tu cuenta *3037 a la "
                                     "cuenta *3213795458 el 30/09/26 a las 01:37."),
                         ("celular", "3213795458"))
        self.assertEqual(self._medio("Bancolombia: Transferiste $15,000,000 desde tu cuenta *3037 a la "
                                     "cuenta *91232656625 el 29/09/2026 a las 10:06."),
                         ("cuenta", "91232656625"))

    def test_pago_qr_es_llave(self):
        self.assertEqual(self._medio("Bancolombia: ANDRES pagaste $23,000.00 por codigo QR desde tu cuenta "
                                     "*3037 a la llave 0092952142 el 29/09/2026 a las 23:32."),
                         ("llave", "0092952142"))

    def test_recibida_y_compra_son_nombre_del_banco(self):
        self.assertEqual(self._medio("Bancolombia: Recibiste una transferencia por $398,000 de CAROLL "
                                     "HUERTAS en tu cuenta **3037, el 19/08/2026 a las 11:37."),
                         ("nombre_banco", "CAROLL HUERTAS"))
        self.assertEqual(self._medio("Bancolombia: Andres, recibiste una transferencia de LEIDY DANIELA "
                                     "MOLINA MARTINEZ por $505,000.00 en tu cuenta *3037 conectada a la "
                                     "llave 1007365480 el 10/08/26 a las 19:41."),
                         ("nombre_banco", "LEIDY DANIELA MOLINA MARTINEZ"))
        self.assertEqual(self._medio("Bancolombia: Compraste $66.200,00 en MERCA EXPRESS RP con tu T.Deb "
                                     "*5379, el 12/08/2026 a las 20:38."),
                         ("nombre_banco", "MERCA EXPRESS RP"))

    def test_sin_sms_no_hay_medio(self):
        self.assertIsNone(tc.medio_de_sms(None))
        self.assertIsNone(tc.medio_de_sms({"familia": "otra"}))


class TestMedioDePayload(unittest.TestCase):
    """El botón 💾 lee el medio del BORRADOR. Los borradores anteriores a la
    etapa no lo traen: se deriva de lo que sí guardaron, con el mismo resultado."""

    def test_usa_el_medio_guardado(self):
        self.assertEqual(tc.medio_de_payload({"medio": {"tipo": "cuenta", "valor": "91232656625"},
                                              "familia": "pago_qr", "destino": "0000"}),
                         ("cuenta", "91232656625"))

    def test_borrador_antiguo_se_deriva_de_familia_destino_y_contraparte(self):
        self.assertEqual(tc.medio_de_payload({"familia": "transferencia_enviada", "destino": "3213795458"}),
                         ("celular", "3213795458"))
        self.assertEqual(tc.medio_de_payload({"familia": "transferencia_enviada", "destino": "91232656625"}),
                         ("cuenta", "91232656625"))
        self.assertEqual(tc.medio_de_payload({"familia": "pago_qr", "destino": "0087671656"}),
                         ("llave", "0087671656"))
        self.assertEqual(tc.medio_de_payload({"familia": "compra_tarjeta", "contraparte": "Didi"}),
                         ("nombre_banco", "DIDI"))

    def test_derivado_coincide_con_el_del_sms_completo(self):
        for texto in (
            "Bancolombia: Transferiste $50,000.00 desde tu cuenta *3037 a la cuenta *3213795458 el "
            "30/09/26 a las 01:37.",
            "Bancolombia: Transferiste $15,000,000 desde tu cuenta *3037 a la cuenta *91232656625 el "
            "29/09/2026 a las 10:06.",
            "Bancolombia: ANDRES pagaste $23,000.00 por codigo QR desde tu cuenta *3037 a la llave "
            "0092952142 el 29/09/2026 a las 23:32.",
            "Bancolombia: Recibiste una transferencia por $398,000 de CAROLL HUERTAS en tu cuenta "
            "**3037, el 19/08/2026 a las 11:37.",
            "Bancolombia: Compraste $66.200,00 en MERCA EXPRESS RP con tu T.Deb *5379, el 12/08/2026 "
            "a las 20:38.",
        ):
            s = sms.parsear(texto)
            antiguo = {"familia": s["familia"], "destino": s["destino"],
                       "contraparte": s.get("contraparte_nombre")}
            self.assertIsNotNone(tc.medio_de_sms(s), texto)
            self.assertEqual(tc.medio_de_payload(antiguo), tc.medio_de_sms(s), texto)

    def test_sin_datos_no_hay_medio(self):
        self.assertIsNone(tc.medio_de_payload(None))
        self.assertIsNone(tc.medio_de_payload({}))
        self.assertIsNone(tc.medio_de_payload({"familia": None, "medio": None}))
        self.assertIsNone(tc.medio_de_payload({"medio": {"tipo": "fax", "valor": "1"}}))


class TestBuscar(unittest.TestCase):

    LEIDY = (77, "CC", "1007289007", "Leidy Daniela Molina", "3213795458")

    def test_igualdad_exacta(self):
        cur = _FakeCursor({("cuenta", "91232656625"): self.LEIDY})
        t = tc.buscar_tercero(cur, "cuenta", "91232656625")
        self.assertEqual((t["id"], t["name"], t["identification_number"], t["phone"]),
                         (77, "Leidy Daniela Molina", "1007289007", "3213795458"))
        self.assertIsNone(tc.buscar_tercero(cur, "cuenta", "9123265662"))      # un dígito menos
        self.assertIsNone(tc.buscar_tercero(cur, "llave", "91232656625"))      # otro tipo

    def test_celular_y_llave_son_equivalentes(self):
        cur = _FakeCursor({("celular", "3213795458"): self.LEIDY})
        self.assertEqual(tc.buscar_tercero(cur, "llave", "3213795458")["id"], 77)
        cur = _FakeCursor({("llave", "3213795458"): self.LEIDY})
        self.assertEqual(tc.buscar_tercero(cur, "celular", "3213795458")["id"], 77)
        # una llave que NO es celular no busca como celular
        cur = _FakeCursor({("celular", "0087671656"): self.LEIDY})
        self.assertIsNone(tc.buscar_tercero(cur, "llave", "0087671656"))

    def test_un_celular_registrado_en_la_web_como_cuenta_tambien_cruza(self):
        # El SMS dice «a la cuenta *3213795458» y en la ficha lo escribieron como
        # «Cuenta bancaria»: es el mismo número de celular → mismo medio.
        cur = _FakeCursor({("cuenta", "3213795458"): self.LEIDY})
        self.assertEqual(tc.buscar_tercero(cur, "celular", "3213795458")["id"], 77)
        self.assertEqual(tc.dueno(cur, "llave", "3213795458")["id"], 77)
        # una cuenta que no tiene forma de celular NO equivale a nada más
        self.assertEqual(tc._equivalentes("cuenta", "91232656625"), [("cuenta", "91232656625")])
        self.assertEqual(tc._equivalentes("nombre_banco", "3213795458"), [("nombre_banco", "3213795458")])
        self.assertEqual(tc._equivalentes("celular", "3213795458")[0], ("celular", "3213795458"))
        self.assertEqual({t for t, _ in tc._equivalentes("llave", "3213795458")},
                         {"celular", "llave", "cuenta"})

    def test_buscar_seguro_no_lanza_si_la_tabla_no_existe(self):
        class _Roto(_FakeCursor):
            def execute(self, sql, params=None):
                if "third_party_accounts" in sql:
                    raise RuntimeError('relation "third_party_accounts" does not exist')
                super().execute(sql, params)
        self.assertIsNone(tc.buscar_tercero_seguro(_Roto(), "celular", "3213795458"))


class TestAgregarValidaciones(unittest.TestCase):

    def test_tipo_y_valor_invalidos_no_tocan_la_bd(self):
        cur = _FakeCursor()
        r = tc.agregar(cur, 1, "correo", "a@b.co")
        self.assertEqual((r["ok"], r["codigo"]), (False, "tipo_invalido"))
        r = tc.agregar(cur, 1, "celular", "12345")
        self.assertEqual((r["ok"], r["codigo"]), (False, "valor_invalido"))
        self.assertIn("10 dígitos", r["error"])
        self.assertEqual(cur.sqls, [])

    def test_tercero_inexistente(self):
        r = tc.agregar(_FakeCursor(), 999, "celular", "3213795458")
        self.assertEqual(r["codigo"], "tercero_no_existe")


if __name__ == "__main__":
    unittest.main()
