# -*- coding: utf-8 -*-
"""tareas.py — Tareas periódicas en el worker (estándar de consultas, H5.5).

Antes corrían DENTRO del bucle del bot, antes de cada getUpdates (que espera
hasta 45 s): un SMS tardaba hasta 45 s en volverse borrador y cualquier tick
lento frenaba a todos los chats. Con `tareas` en FINSYS_EN_COLA las corre el
worker con su propio reloj y el poller solo atiende Telegram:

    SMS → borrador → Telegram ............ cada 5 s
    avisos de la Mini App ................ cada 5 s
    resumen analítico (decide la BD) ..... cada 15 min
    retención 30/60/90 + bitácora ........ cada hora
    limpieza de la cola (30 días) ........ cada hora

Cada tarea atrapa sus errores: ninguna tumba al worker ni frena a las demás.
Solo arranca con FINSYS_WORKER_PRODUCCION=1 (la BD es la de producción: un
worker local jamás procesa SMS reales ni escribe a chats reales).
"""
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

log = logging.getLogger("finsys.tareas")


@dataclass
class Tarea:
    nombre: str
    cada_s: float
    fn: Callable[[], object]


def activas() -> bool:
    """¿Las tareas periódicas viven en el worker? (la misma variable en el bot
    y en el worker: nunca las corren los dos)."""
    from fin_sys_core.cola import en_cola
    return en_cola("tareas")


def _enviar():
    import bot_telegram
    return bot_telegram.send_message


def _sms():
    from bot_sms import procesar_pendientes
    return procesar_pendientes(_enviar())


def _avisos_mini_app():
    import bot_driver
    import bot_telegram
    return bot_driver.avisar_chat_pendientes(bot_telegram.send_message,
                                             quitar_botones=bot_telegram._quitar_botones)


def _resumen():
    from insight_engine import tick_resumen_telegram
    return tick_resumen_telegram(_enviar())


def _retencion():
    from bot_anomalias import purgar as purgar_bitacora
    from bot_retencion import purgar
    res = purgar(_enviar())
    return {**(res or {}), "bitacora": purgar_bitacora()}


def _limpieza_cola():
    from fin_sys_core.cola import purgar
    return purgar(int(os.getenv("FINSYS_OPERACIONES_DIAS", "30")))


TAREAS: List[Tarea] = [
    Tarea("sms", 5, _sms),
    Tarea("avisos_mini_app", 5, _avisos_mini_app),
    Tarea("resumen", 900, _resumen),
    Tarea("retencion", 3600, _retencion),
    Tarea("limpieza_cola", 3600, _limpieza_cola),
]


def correr_vencidas(proximas: Dict[str, float], ahora: float,
                    tareas: Optional[List[Tarea]] = None) -> List[str]:
    """Corre las tareas cuyo turno llegó y agenda la siguiente. Un error en una
    no impide las demás. → nombres de las que corrieron."""
    corridas = []
    for t in (tareas if tareas is not None else TAREAS):
        if ahora < proximas.get(t.nombre, 0.0):
            continue
        proximas[t.nombre] = ahora + t.cada_s
        corridas.append(t.nombre)
        try:
            res = t.fn()
            if res:
                log.info("⏱️ %s → %s", t.nombre, res)
        except Exception as e:
            log.warning("⏱️ tarea %s falló (se reintenta en %ss): %s", t.nombre, t.cada_s, e)
    return corridas


def bucle(parar: threading.Event, tareas: Optional[List[Tarea]] = None, paso_s: float = 1.0,
          reloj: Callable[[], float] = time.monotonic) -> None:
    proximas: Dict[str, float] = {}
    while not parar.is_set():
        correr_vencidas(proximas, reloj(), tareas)
        parar.wait(paso_s)


def arrancar(parar: threading.Event) -> Optional[threading.Thread]:
    """Hilo del programador, solo en el worker de producción con `tareas` activas."""
    if os.getenv("FINSYS_WORKER_PRODUCCION") != "1" or not activas():
        return None
    h = threading.Thread(target=bucle, args=(parar,), name="tareas", daemon=True)
    h.start()
    log.info("⏱️ tareas periódicas en el worker: %s", ", ".join(f"{t.nombre}/{t.cada_s:g}s" for t in TAREAS))
    return h
