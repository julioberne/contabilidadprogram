# -*- coding: utf-8 -*-
"""Tests puros: responder (reply) a un mensaje de un borrador lo completa y
jamás crea otro (pedido de Andrés, 9-oct-2026).

Antes, el bot recordaba UN solo mensaje por borrador (bot_summary_message_id)
y lo pisaba en cada mensaje nuevo: responder a uno anterior, a uno ya
confirmado o al de instrucciones mandaba el texto al LLM como movimiento
nuevo (borradores #573-575, #590, #613-618 en la BD). Sin BD: cursor falso.
"""
import os
import sys
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import bot_driver    # noqa: E402
import bot_telegram  # noqa: E402

LINK = {"id": 7, "hub_user_id": "u-1", "status": "ACTIVO", "default_portfolio": "Negocio A"}


class _CursorReply:
    """Enruta por la forma del SQL de _draft_por_reply.
    registro: {message_id: (draft_id, kind)} · resumen: {message_id: draft_id}
    borradores: {draft_id: (chat_link_id, status)}"""

    def __init__(self, registro=None, resumen=None, borradores=None):
        self.registro, self.resumen = registro or {}, resumen or {}
        self.borradores = borradores or {}
        self._rows, self.sqls = [], []

    def execute(self, sql, params=None):
        self.sqls.append(sql)
        if "FROM bot_messages" in sql:
            fila = self.registro.get(params[2])
            self._rows = [fila] if fila else []
        elif "bot_summary_message_id = %s" in sql:
            d = self.resumen.get(params[1])
            self._rows = [(d,)] if d else []
        elif "SELECT id, status FROM transaction_drafts" in sql:
            did, link_id = params
            b = self.borradores.get(did)
            self._rows = [(did, b[1])] if b and b[0] == link_id else []
        else:
            self._rows = []

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


def _msg(**kw):
    base = {"channel": "telegram", "chat_id": "555", "kind": "text", "text": "x"}
    base.update(kw)
    return base


class TestMonto(unittest.TestCase):

    def test_formas_de_escribir_un_monto(self):
        casos = {"50000": 50000, "$50.000": 50000, "50.000,00": 50000, "$ 12,100.00": 12100,
                 "50 mil": 50000, "50mil": 50000, "20k": 20000, "1,5 millones": 1_500_000,
                 "2 millones": 2_000_000, "35000 pesos": 35000, "$1.500.000": 1_500_000}
        for texto, esperado in casos.items():
            self.assertEqual(bot_driver._monto_de(texto), esperado, texto)

    def test_no_son_montos(self):
        for texto in ("arriendo", "3193301184", "1007289007", "0", "abono 50000", "", "50.000 arriendo"):
            self.assertIsNone(bot_driver._monto_de(texto), texto)

    def test_numero_largo_con_signo_peso_si_es_monto(self):
        self.assertEqual(bot_driver._monto_de("$1500000000"), 1_500_000_000)


class TestParseReplyMonto(unittest.TestCase):

    def test_linea_de_solo_monto(self):
        self.assertEqual(bot_driver._parse_reply("50000"),
                         {"concepto": None, "tercero": None, "monto": 50000, "etiquetas": []})

    def test_marca_monto_y_valor(self):
        self.assertEqual(bot_driver._parse_reply("Monto: 45.000")["monto"], 45000)
        self.assertEqual(bot_driver._parse_reply("valor 12 mil")["monto"], 12000)

    def test_valor_sin_numero_es_concepto(self):
        r = bot_driver._parse_reply("Valor agregado del servicio")
        self.assertEqual((r["concepto"], r["monto"]), ("Valor agregado del servicio", None))

    def test_todo_junto_concepto_monto_tercero(self):
        r = bot_driver._parse_reply("parqueadero obra\n$12.100\nTercero: Parking Internacional nit 900123456")
        self.assertEqual(r["concepto"], "parqueadero obra")
        self.assertEqual(r["monto"], 12100)
        self.assertEqual(r["tercero"]["nombre"], "Parking Internacional")

    def test_concepto_con_cifras_sigue_siendo_concepto(self):
        r = bot_driver._parse_reply("abono cuota 1 de 50000")
        self.assertEqual((r["concepto"], r["monto"]), ("abono cuota 1 de 50000", None))

    def test_celular_suelto_busca_tercero(self):
        t = bot_driver._parse_reply("3193301184")["tercero"]
        self.assertEqual(t["buscar_num"], "3193301184")

    def test_documento_suelto_busca_tercero(self):
        r = bot_driver._parse_reply("1007289007")
        self.assertEqual((r["tercero"]["buscar_num"], r["monto"], r["concepto"]), ("1007289007", None, None))


class TestTerceroNumeroAlFinal(unittest.TestCase):

    def test_nombre_y_cedula_sin_cc(self):
        t = bot_driver._parse_reply("Tercero Leidy Molina 1007289007")["tercero"]
        self.assertEqual((t["nombre"], t["num"], t["phone"]), ("Leidy Molina", "1007289007", None))

    def test_nombre_y_celular_sin_cel(self):
        t = bot_driver._parse_reply("Tercero: Juan Nequi 3193301184")["tercero"]
        self.assertEqual((t["nombre"], t["num"], t["phone"]), ("Juan Nequi", None, "3193301184"))

    def test_cc_explicito_manda_aunque_parezca_celular(self):
        t = bot_driver._parse_reply("Tercero: Ana cc 3123456789")["tercero"]
        self.assertEqual((t["nombre"], t["num"], t["phone"]), ("Ana", "3123456789", None))

    def test_numero_corto_al_final_no_es_documento(self):
        t = bot_driver._parse_reply("Tercero: Local 123")["tercero"]
        self.assertEqual((t["nombre"], t["num"]), ("Local 123", None))


class TestDraftPorReply(unittest.TestCase):

    def test_registro_de_cualquier_mensaje_del_borrador(self):
        cur = _CursorReply(registro={"900": (635, "text")}, borradores={635: (7, "BORRADOR")})
        r = bot_driver._draft_por_reply(cur, LINK, _msg(reply_to_message_id="900"))
        self.assertEqual(r, {"id": 635, "status": "BORRADOR", "kind": "text"})

    def test_ultimo_resumen_si_no_hay_registro(self):
        cur = _CursorReply(resumen={"901": 640}, borradores={640: (7, "ERROR")})
        r = bot_driver._draft_por_reply(cur, LINK, _msg(reply_to_message_id="901"))
        self.assertEqual((r["id"], r["status"]), (640, "ERROR"))

    def test_numero_escrito_en_el_mensaje_del_bot(self):
        cur = _CursorReply(borradores={578: (7, "BORRADOR")})
        texto = "📲 SMS Bancolombia (85540)\n\n🧾 BORRADOR #578\nTipo: GASTO\n…\n▸ Confirmar #578"
        r = bot_driver._draft_por_reply(cur, LINK, _msg(reply_to_message_id="10", reply_to_bot=True,
                                                         reply_to_text=texto))
        self.assertEqual(r["id"], 578)
        cur = _CursorReply(borradores={12: (7, "BORRADOR")})
        r = bot_driver._draft_por_reply(cur, LINK, _msg(reply_to_message_id="11", reply_to_bot=True,
                                                         reply_to_text="💤 El borrador #12 queda pendiente"))
        self.assertEqual(r["id"], 12)

    def test_texto_de_un_mensaje_que_no_es_del_bot_no_cuenta(self):
        cur = _CursorReply(borradores={578: (7, "BORRADOR")})
        r = bot_driver._draft_por_reply(cur, LINK, _msg(reply_to_message_id="10",
                                                         reply_to_text="BORRADOR #578"))
        self.assertIsNone(r)

    def test_borrador_de_otro_chat_no_se_toca(self):
        cur = _CursorReply(registro={"900": (635, "text")}, borradores={635: (99, "BORRADOR")})
        self.assertIsNone(bot_driver._draft_por_reply(cur, LINK, _msg(reply_to_message_id="900")))
        cur = _CursorReply(borradores={578: (99, "BORRADOR")})
        self.assertIsNone(bot_driver._draft_por_reply(
            cur, LINK, _msg(reply_to_message_id="1", reply_to_bot=True, reply_to_text="BORRADOR #578")))

    def test_sin_reply_no_hay_borrador(self):
        self.assertIsNone(bot_driver._draft_por_reply(_CursorReply(), LINK, _msg()))

    def test_devuelve_el_borrador_aunque_ya_este_confirmado(self):
        cur = _CursorReply(registro={"900": (635, "text")}, borradores={635: (7, "CONFIRMADO")})
        self.assertEqual(bot_driver._draft_por_reply(cur, LINK, _msg(reply_to_message_id="900"))["status"],
                         "CONFIRMADO")


class TestFlujoRespuesta(unittest.TestCase):

    def test_confirmado_avisa_y_no_crea_nada(self):
        cur = _CursorReply()
        with mock.patch.object(bot_driver, "_flujo_reply") as fr, \
                mock.patch.object(bot_driver, "_crear_borrador") as crear:
            texto = bot_driver._flujo_respuesta(cur, LINK, {"id": 635, "status": "CONFIRMADO", "kind": None},
                                                _msg(text="parqueadero"))
        self.assertIn("#635 ya está confirmado", texto)
        fr.assert_not_called()
        crear.assert_not_called()

    def test_texto_va_al_borrador(self):
        with mock.patch.object(bot_driver, "_flujo_reply", return_value={"text": "ok"}) as fr:
            bot_driver._flujo_respuesta(_CursorReply(), LINK, {"id": 635, "status": "BORRADOR", "kind": "text"},
                                        _msg(text="parqueadero obra"))
        fr.assert_called_once()
        self.assertEqual(fr.call_args[0][2:], (635, "parqueadero obra"))

    def test_foto_con_pie_adjunta_y_completa_el_mismo_borrador(self):
        cur = mock.MagicMock()
        with mock.patch.object(bot_driver, "_adjuntar_evidencia",
                               return_value={"text": "📎 Evidencia adjuntada al borrador #635.",
                                             "draft_id": 635, "buttons": []}) as adj, \
                mock.patch.object(bot_driver, "_flujo_reply",
                                  return_value={"text": "📝 Concepto → «recibo»", "draft_id": 635}) as fr, \
                mock.patch.object(bot_driver, "_crear_borrador") as crear:
            r = bot_driver._flujo_respuesta(cur, LINK, {"id": 635, "status": "BORRADOR", "kind": None},
                                            _msg(kind="photo", media_path="https://x/f.jpg", text="recibo"))
        adj.assert_called_once()
        fr.assert_called_once()
        crear.assert_not_called()
        cur.connection.commit.assert_called_once()     # evidencia firme antes de editar_draft
        self.assertTrue(r["text"].startswith("📎 Evidencia adjuntada"))
        self.assertIn("Concepto", r["text"])

    def test_ubicacion_va_al_borrador(self):
        with mock.patch.object(bot_driver, "_ubicacion_a_borrador", return_value="📍") as ub:
            bot_driver._flujo_respuesta(_CursorReply(), LINK, {"id": 9, "status": "BORRADOR", "kind": None},
                                        _msg(kind="location", latitude=4.6, longitude=-74.1))
        self.assertEqual(ub.call_args[0][2], 9)


class _ConnFalsa:
    def __init__(self):
        self.cur = mock.MagicMock()

    def cursor(self):
        return self.cur

    def commit(self):
        pass

    def rollback(self):
        pass


class TestHandleMessageRespuesta(unittest.TestCase):
    """De punta a punta en handle_message, con la BD simulada: una respuesta a
    un mensaje del borrador nunca llega a _crear_borrador (LLM)."""

    def _correr(self, msg, destino):
        import db_pool
        conn = _ConnFalsa()
        with mock.patch.object(db_pool, "get_conn", return_value=conn), \
                mock.patch.object(db_pool, "put_conn"), \
                mock.patch.object(bot_driver, "_registrar_entrante", return_value=1), \
                mock.patch.object(bot_driver, "_get_link", return_value=LINK), \
                mock.patch.object(bot_driver, "_draft_por_reply", return_value=destino), \
                mock.patch.object(bot_driver, "_flujo_reply", return_value={"text": "📝", "draft_id": 1}), \
                mock.patch.object(bot_driver, "_crear_borrador") as crear:
            r = bot_driver.handle_message(msg)
        return r, crear

    def test_respuesta_a_borrador_confirmado(self):
        r, crear = self._correr(_msg(text="Billar", reply_to_message_id="5"),
                                {"id": 3, "status": "CONFIRMADO", "kind": None})
        crear.assert_not_called()
        self.assertIn("ya está confirmado", r)

    def test_respuesta_a_borrador_editable(self):
        r, crear = self._correr(_msg(text="Billar", reply_to_message_id="5"),
                                {"id": 3, "status": "BORRADOR", "kind": None})
        crear.assert_not_called()
        self.assertEqual(r, {"text": "📝", "draft_id": 1})

    def test_texto_suelto_si_crea_borrador(self):
        import bot_sms
        with mock.patch.object(bot_sms, "borrador_desde_chat", return_value=None):
            _, crear = self._correr(_msg(text="Billar"), None)
        crear.assert_called_once()


class TestNormalizeTelegram(unittest.TestCase):

    def _update(self, reply):
        return {"update_id": 1, "message": {"chat": {"id": 555, "type": "private"},
                                            "text": "parqueadero", "reply_to_message": reply}}

    def test_respuesta_a_un_mensaje_del_bot_trae_su_texto(self):
        m = bot_telegram.normalize(self._update({"message_id": 42, "from": {"is_bot": True},
                                                 "text": "🧾 BORRADOR #635"}))
        self.assertEqual((m["reply_to_message_id"], m["reply_to_bot"], m["reply_to_text"]),
                         ("42", True, "🧾 BORRADOR #635"))

    def test_respuesta_a_un_mensaje_propio_no_trae_texto(self):
        m = bot_telegram.normalize(self._update({"message_id": 43, "from": {"is_bot": False},
                                                 "text": "BORRADOR #1"}))
        self.assertEqual(m["reply_to_message_id"], "43")
        self.assertNotIn("reply_to_text", m)

    def test_foto_respondiendo_trae_el_texto_del_bot(self):
        upd = {"update_id": 2, "message": {"chat": {"id": 555, "type": "private"},
                                           "photo": [{"file_id": "f"}], "caption": "recibo",
                                           "reply_to_message": {"message_id": 44, "from": {"is_bot": True},
                                                                "text": "BORRADOR #9"}}}
        with mock.patch.object(bot_telegram, "_descargar_foto", return_value="https://x/f.jpg"):
            m = bot_telegram.normalize(upd)
        self.assertEqual((m["kind"], m["reply_to_text"]), ("photo", "BORRADOR #9"))


class TestBotoneraUnica(unittest.TestCase):

    def test_al_mandar_otro_mensaje_se_quitan_los_botones_del_anterior(self):
        with mock.patch.object(bot_driver, "guardar_summary_message_id", return_value="100"), \
                mock.patch.object(bot_telegram, "edit_message") as em:
            bot_telegram._botonera_en("555", 635, 101)
        em.assert_called_once_with("555", "100", buttons=[])

    def test_mismo_mensaje_o_sin_anterior_no_edita(self):
        for previo in ("101", None):
            with mock.patch.object(bot_driver, "guardar_summary_message_id", return_value=previo), \
                    mock.patch.object(bot_telegram, "edit_message") as em:
                bot_telegram._botonera_en("555", 635, 101)
            em.assert_not_called()


class TestAvisoInformativo(unittest.TestCase):

    def test_falta_monto_no_pide_descartar(self):
        payload = {"type": "GASTO", "amount": None, "concept": "Billar", "category": "Otros Gastos",
                   "payment_method": "Efectivo", "third_party": {"name": "Sin especificar",
                   "identification_type": "NIT", "identification_number": "999999999"},
                   "transaction_date": "2026-10-09", "portfolio_name": "Negocio A"}
        texto = bot_driver.render_summary(5, payload, missing=["monto"])
        self.assertIn("⚠ Falta: monto", texto)
        self.assertIn("responde a este mensaje (ej. 50000)", texto)
        self.assertNotIn("descarta y reenv", texto.lower())


class _CursorTags:
    def __init__(self, filas):
        self.filas, self.params = filas, None

    def execute(self, sql, params=None):
        self.params = params

    def fetchall(self):
        return self.filas


class TestEtiquetasEnRespuesta(unittest.TestCase):
    """Hito D (9-oct-2026): crear y poner etiquetas desde el chat."""

    def test_marca_etiqueta(self):
        r = bot_driver._parse_reply("Etiqueta: obra armenia, viaje")
        self.assertEqual((r["etiquetas"], r["concepto"]), (["obra armenia", "viaje"], None))

    def test_etiqueta_junto_al_concepto(self):
        r = bot_driver._parse_reply("parqueadero\nEtiquetas: obra")
        self.assertEqual((r["concepto"], r["etiquetas"]), ("parqueadero", ["obra"]))
        r = bot_driver._parse_reply("almuerzo equipo etiqueta: obra")
        self.assertEqual((r["concepto"], r["etiquetas"]), ("almuerzo equipo", ["obra"]))

    def test_sin_dos_puntos_es_concepto(self):
        r = bot_driver._parse_reply("Etiqueta de precio")
        self.assertEqual((r["concepto"], r["etiquetas"]), ("Etiqueta de precio", []))

    def test_nombres_de_etiqueta(self):
        self.assertEqual(bot_driver._nombres_etiquetas("#obra; caja\n caja ,  "), ["obra", "caja"])

    def test_botonera_de_etiquetas_ofrece_nueva(self):
        cur = _CursorTags([(5, "obra"), (3, "caja")])
        filas = bot_driver._botones_tags(cur, 9, {"tags": ["obra"]})
        self.assertEqual(filas[0], [("✓ obra", "tagset:9:5")])
        self.assertEqual(filas[1], [("caja", "tagset:9:3")])
        self.assertEqual(filas[-1], [("➕ Nueva etiqueta", "tagnew:9"), ("✔ Listo", "tagdone:9")])
        self.assertEqual(cur.params, (["obra"],))        # las puestas van primero

    def test_respuesta_al_mensaje_que_pide_la_etiqueta(self):
        with mock.patch.object(bot_driver, "_poner_etiquetas",
                               return_value={"nota": "🏷️ Etiquetas → obra", "payload": {"type": "GASTO"}}) as pe, \
                mock.patch.object(bot_driver, "_flujo_reply") as fr:
            r = bot_driver._flujo_respuesta(_CursorReply(), LINK,
                                            {"id": 9, "status": "BORRADOR", "kind": "pedir_etiqueta"},
                                            _msg(text="obra armenia, viaje"))
        pe.assert_called_once()
        self.assertEqual(pe.call_args[0][3], ["obra armenia", "viaje"])
        fr.assert_not_called()                         # no es concepto
        self.assertTrue(r["text"].startswith("🏷️ Etiquetas → obra"))

    def test_markup_acepta_force_reply(self):
        mk = {"force_reply": True, "input_field_placeholder": "x"}
        self.assertIs(bot_telegram._markup(mk), mk)


if __name__ == "__main__":
    unittest.main()
