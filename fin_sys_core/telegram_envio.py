# -*- coding: utf-8 -*-
"""telegram_envio.py — Llamadas a la API de Telegram con ritmo y reintentos (H5.4).

Antes, sendMessage/editMessage hacían UN intento: si Telegram respondía 429
(demasiados envíos) o fallaba la red, la respuesta se perdía en silencio.

  · Ritmo: como mucho 1 mensaje cada TG_POR_CHAT_S por chat y TG_GLOBAL_POR_S
    por proceso. Telegram permite ~1/s por chat y 30/s en total; el bot y el
    worker son dos procesos, así que cada uno usa la mitad.
  · 429: se espera lo que pide `retry_after` (hasta ESPERA_429_MAX_S) y se reintenta.
  · Red caída o 5xx: se reintenta tras 1, 2 y 4 s.
  · 4xx del mensaje (texto vacío, "message is not modified"…): no se reintenta.
  · Si al final no salió: queda en la 📓 bitácora de anomalías (tipo envio_perdido).

`llamar` devuelve la respuesta httpx final (o None si nunca hubo respuesta).
"""
import os
import threading
import time
from typing import Any, Callable, Dict, Optional

TG_POR_CHAT_S = float(os.getenv("TG_POR_CHAT_S", "1.25"))
TG_GLOBAL_POR_S = float(os.getenv("TG_GLOBAL_POR_S", "15"))
REINTENTOS = 3
ESPERA_429_MAX_S = 30
_ESPERAS_RED = (1, 2, 4)
# Métodos que mandan algo al chat y cuentan para el ritmo (los demás no).
_CUENTAN = ("sendMessage", "sendPhoto", "editMessageText", "editMessageReplyMarkup")


class Limitador:
    """Ritmo por chat y global, seguro entre hilos. `reloj` y `dormir` se
    inyectan en los tests."""

    def __init__(self, por_chat_s: float = TG_POR_CHAT_S, global_por_s: float = TG_GLOBAL_POR_S,
                 reloj: Callable[[], float] = time.monotonic, dormir: Callable[[float], None] = time.sleep):
        self.por_chat_s = max(0.0, por_chat_s)
        self.intervalo_global = 1.0 / global_por_s if global_por_s > 0 else 0.0
        self.reloj, self.dormir = reloj, dormir
        self._lock = threading.Lock()
        self._proximo_chat: Dict[str, float] = {}
        self._proximo_global = 0.0

    def turno(self, chat_id: Optional[str]) -> float:
        """Reserva el próximo turno y espera hasta él. → segundos esperados."""
        with self._lock:
            ahora = self.reloj()
            t = max(ahora, self._proximo_global)
            if chat_id:
                t = max(t, self._proximo_chat.get(str(chat_id), 0.0))
                self._proximo_chat[str(chat_id)] = t + self.por_chat_s
                if len(self._proximo_chat) > 5000:       # no crece sin fin
                    self._proximo_chat = {k: v for k, v in self._proximo_chat.items() if v > ahora}
            self._proximo_global = t + self.intervalo_global
        espera = t - ahora
        if espera > 0:
            self.dormir(espera)
        return espera


LIMITADOR = Limitador()


def _retry_after(r) -> Optional[float]:
    try:
        return float(((r.json() or {}).get("parameters") or {}).get("retry_after"))
    except Exception:
        return None


def llamar(cliente, url: str, metodo: str, *, chat_id: Optional[str] = None, json: Optional[Dict[str, Any]] = None,
           data: Optional[Dict[str, Any]] = None, files=None, limitador: Optional[Limitador] = None,
           dormir: Callable[[float], None] = time.sleep, registrar: Optional[Callable[..., Any]] = None):
    """POST a {url}/{metodo} con ritmo y reintentos. → respuesta httpx o None."""
    limitador = limitador or LIMITADOR
    ultimo, motivo = None, ""
    for intento in range(REINTENTOS + 1):
        if metodo in _CUENTAN:
            limitador.turno(chat_id)
        try:
            r = cliente.post(f"{url}/{metodo}", json=json, data=data, files=files)
        except Exception as e:                    # red caída, timeout…
            ultimo, motivo = None, f"{type(e).__name__}: {e}"
            if intento < REINTENTOS:
                dormir(_ESPERAS_RED[min(intento, len(_ESPERAS_RED) - 1)])
                continue
            break
        ultimo = r
        if r.status_code == 200:
            return r
        if r.status_code == 429 and intento < REINTENTOS:
            dormir(min(ESPERA_429_MAX_S, _retry_after(r) or 1.0))
            continue
        if r.status_code >= 500 and intento < REINTENTOS:
            dormir(_ESPERAS_RED[min(intento, len(_ESPERAS_RED) - 1)])
            continue
        motivo = f"HTTP {r.status_code}: {(r.text or '')[:160]}"
        if r.status_code < 500 and r.status_code != 429:
            return r                              # error del mensaje: no se reintenta
        break
    _anotar_perdido(metodo, chat_id, motivo, registrar)
    return ultimo


def _anotar_perdido(metodo: str, chat_id: Optional[str], motivo: str, registrar=None) -> None:
    """Un envío que no salió tras los reintentos queda visible en la bitácora."""
    print(f"⚠️ [TG] {metodo} no salió tras {REINTENTOS} reintentos: {motivo}")
    if metodo not in _CUENTAN:
        return
    try:
        if registrar is None:
            from bot_anomalias import registrar
        registrar("envio_perdido", f"Telegram {metodo}: {motivo}"[:300], canal="telegram",
                  datos={"chat_id": str(chat_id or ""), "metodo": metodo})
    except Exception:
        pass
