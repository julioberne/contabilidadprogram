# -*- coding: utf-8 -*-
"""Bot sin carril único (estándar H5.4, 25-oct-2026). Sin BD y sin Telegram real.

- es_pesado: voz, texto libre, /analisis y foto con texto van al worker; lo
  que responde a un borrador, los botones y los comandos cortos, no.
- procesar_mensaje: con `bot` en FINSYS_EN_COLA encola y muestra «escribiendo…»
  sin procesar; sin la variable, o si encolar falla, procesa como siempre.
- Manejador bot_mensaje: misma salida que el poller; reintenta y, en el último
  intento, responde el «⚠ Error interno» de siempre.
- telegram_envio: ritmo por chat, 429 con retry_after, 5xx/red con espera,
  4xx sin reintento, envío perdido a la bitácora.

    python -m unittest tests.test_bot_cola
"""
import os
import sys
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import bot_telegram  # noqa: E402
import telegram_envio as te  # noqa: E402

TEXTO = {"channel": "telegram", "chat_id": "c1", "external_message_id": "900", "kind": "text", "text": "almuerzo 25000"}


class TestEsPesado(unittest.TestCase):
    def test_clasificacion(self):
        p = bot_telegram.es_pesado
        self.assertTrue(p({"kind": "audio"}))
        self.assertTrue(p({"kind": "text", "text": "almuerzo 25000"}))
        self.assertTrue(p({"kind": "text", "text": "/analisis gastos de octubre"}))
        self.assertTrue(p({"kind": "text", "text": "/análisis@FinsysBot"}))
        self.assertTrue(p({"kind": "photo", "text": "factura luz"}))
        self.assertFalse(p({"kind": "photo", "text": None}), "foto sin texto: solo BD")
        self.assertFalse(p({"kind": "photo", "text": "x", "reply_to_message_id": "5"}))
        self.assertFalse(p({"kind": "text", "text": "Tercero: Ana", "reply_to_message_id": "5"}),
                         "responder a un borrador es liviano")
        self.assertFalse(p({"kind": "text", "text": "/empresa Negocio"}))
        self.assertFalse(p({"kind": "text", "text": "  "}))
        self.assertFalse(p({"kind": "location"}))


class TestProcesarMensaje(unittest.TestCase):
    def setUp(self):
        self.driver = mock.Mock()
        self.driver.handle_message.return_value = "listo"

    def _correr(self, entorno, msg=TEXTO, encolar=None):
        with mock.patch.dict(os.environ, entorno), \
             mock.patch("fin_sys_core.cola.encolar", encolar or mock.Mock(return_value={"id": 1})) as enc, \
             mock.patch.object(bot_telegram, "enviar_accion") as accion, \
             mock.patch.object(bot_telegram, "send_message", return_value=11) as enviar:
            via = bot_telegram.procesar_mensaje(self.driver, msg)
        return via, enc, accion, enviar

    def test_pesado_con_la_cola_activa_se_encola(self):
        via, enc, accion, enviar = self._correr({"FINSYS_EN_COLA": "bot"})
        self.assertEqual(via, "cola")
        self.driver.handle_message.assert_not_called()
        tipo, datos = enc.call_args[0]
        self.assertEqual((tipo, datos), ("bot_mensaje", TEXTO))
        self.assertEqual(enc.call_args[1]["clave"], "bot:telegram:900", "idempotente por update")
        accion.assert_called_once_with("c1")
        enviar.assert_not_called()

    def test_sin_la_variable_como_siempre(self):
        via, enc, _, enviar = self._correr({"FINSYS_EN_COLA": "", "FINSYS_EXPORT_EN_COLA": ""})
        self.assertEqual(via, "inline")
        enc.assert_not_called()
        self.driver.handle_message.assert_called_once_with(TEXTO)
        enviar.assert_called_once_with("c1", "listo")

    def test_si_encolar_falla_se_procesa_aqui(self):
        via, _, _, enviar = self._correr({"FINSYS_EN_COLA": "bot"}, encolar=mock.Mock(side_effect=RuntimeError("BD")))
        self.assertEqual(via, "inline")
        enviar.assert_called_once_with("c1", "listo")

    def test_liviano_nunca_va_a_la_cola(self):
        msg = {**TEXTO, "text": "Tercero: Ana", "reply_to_message_id": "77"}
        via, enc, _, _ = self._correr({"FINSYS_EN_COLA": "bot"}, msg=msg)
        self.assertEqual(via, "inline")
        enc.assert_not_called()


class TestEntregarRespuesta(unittest.TestCase):
    def test_dict_con_borrador_y_texto_suelto(self):
        driver = mock.Mock()
        with mock.patch.object(bot_telegram, "send_message", return_value=55) as enviar, \
             mock.patch.object(bot_telegram, "_botonera_en") as botonera:
            bot_telegram.entregar_respuesta(TEXTO, {"text": "Borrador #9", "buttons": [[("✅", "ok")]],
                                                    "draft_id": 9}, driver)
            bot_telegram.entregar_respuesta(TEXTO, "hola", driver)
            bot_telegram.entregar_respuesta(TEXTO, None, driver)
        self.assertEqual(enviar.call_count, 2)
        botonera.assert_called_once_with("c1", 9, 55)
        self.assertEqual(driver.log_outbound.call_count, 2)


class TestManejadorBotMensaje(unittest.TestCase):
    def _correr(self, op, efecto):
        from fin_sys_core.worker_jobs import bot_mensaje
        import bot_driver
        with mock.patch.object(bot_driver, "handle_message", side_effect=efecto), \
             mock.patch.object(bot_telegram, "enviar_accion"), \
             mock.patch.object(bot_telegram, "entregar_respuesta") as entregar:
            r = bot_mensaje(TEXTO, op)
        return r, entregar

    def test_misma_salida_que_el_poller(self):
        r, entregar = self._correr({"intentos": 1, "max_intentos": 3}, ["Borrador listo"])
        self.assertEqual(entregar.call_args[0][:2], (TEXTO, "Borrador listo"))
        self.assertTrue(r["respondido"])

    def test_error_reintenta_y_al_final_avisa(self):
        with self.assertRaises(RuntimeError):
            self._correr({"intentos": 1, "max_intentos": 3}, RuntimeError("BD caída"))
        r, entregar = self._correr({"intentos": 3, "max_intentos": 3}, RuntimeError("BD caída"))
        self.assertIn("Error interno", entregar.call_args[0][1])


class _Resp:
    def __init__(self, status, cuerpo=None, texto=""):
        self.status_code, self._cuerpo, self.text = status, cuerpo or {}, texto

    def json(self):
        return self._cuerpo


class _Cliente:
    def __init__(self, respuestas):
        self.respuestas, self.llamadas = list(respuestas), 0

    def post(self, url, **kw):
        self.llamadas += 1
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


class TestEnvios(unittest.TestCase):
    def _llamar(self, respuestas, metodo="sendMessage"):
        cliente, esperas, anotadas = _Cliente(respuestas), [], []
        lim = te.Limitador(por_chat_s=0, global_por_s=0)
        r = te.llamar(cliente, "https://x", metodo, chat_id="c1", json={}, limitador=lim,
                      dormir=esperas.append, registrar=lambda *a, **k: anotadas.append((a, k)))
        return r, cliente, esperas, anotadas

    def test_429_espera_lo_pedido_y_reintenta(self):
        r, cliente, esperas, anotadas = self._llamar([_Resp(429, {"parameters": {"retry_after": 7}}), _Resp(200)])
        self.assertEqual((r.status_code, cliente.llamadas, esperas, anotadas), (200, 2, [7.0], []))

    def test_429_largo_se_acota(self):
        _, _, esperas, _ = self._llamar([_Resp(429, {"parameters": {"retry_after": 999}}), _Resp(200)])
        self.assertEqual(esperas, [te.ESPERA_429_MAX_S])

    def test_red_y_5xx_con_espera_creciente_y_luego_bitacora(self):
        r, cliente, esperas, anotadas = self._llamar(
            [ConnectionError("sin red"), _Resp(502), _Resp(503), _Resp(500)])
        self.assertEqual(cliente.llamadas, 4)
        self.assertEqual(esperas, [1, 2, 4])
        self.assertEqual(r.status_code, 500)
        self.assertEqual(anotadas[0][0][0], "envio_perdido")

    def test_4xx_del_mensaje_no_se_reintenta_ni_se_anota(self):
        r, cliente, esperas, anotadas = self._llamar([_Resp(400, texto="message is not modified")])
        self.assertEqual((r.status_code, cliente.llamadas, esperas, anotadas), (400, 1, [], []))

    def test_ritmo_por_chat(self):
        t = [100.0]
        dormidas = []

        def dormir(s):
            dormidas.append(round(s, 2))
            t[0] += s
        lim = te.Limitador(por_chat_s=1.25, global_por_s=1000, reloj=lambda: t[0], dormir=dormir)
        lim.turno("c1")
        lim.turno("c1")                 # el mismo chat espera su turno
        lim.turno("c2")                 # otro chat casi no espera (solo el global)
        self.assertEqual(dormidas[0], 1.25)
        self.assertLessEqual(len(dormidas), 2)
        self.assertTrue(len(dormidas) == 1 or dormidas[1] <= 0.01)

    def test_send_message_usa_el_envio_con_reintentos(self):
        with mock.patch.object(te, "llamar", return_value=_Resp(200, {"result": {"message_id": 42}})) as ll:
            self.assertEqual(bot_telegram.send_message("c1", "hola"), 42)
        self.assertEqual(ll.call_args[0][2], "sendMessage")
        self.assertEqual(ll.call_args[1]["chat_id"], "c1")


if __name__ == "__main__":
    unittest.main()
