# -*- coding: utf-8 -*-
"""worker.py — Proceso que hace los trabajos de la cola (estándar H5).

    python -m fin_sys_core.worker          # en Dokploy: servicio `worker`

La API encola (fin_sys_core/cola.py) y responde 202; este proceso toma cada
trabajo, llama a su manejador (fin_sys_core/worker_jobs.py) y deja el
resultado en `operaciones`. Varios trabajos a la vez (FINSYS_WORKER_HILOS,
2 por defecto), cada uno con su latido para que no reaparezca mientras corre.

SEGURIDAD — la BD es la misma en local y en producción: sin
FINSYS_WORKER_PRODUCCION=1 (que solo pone docker-compose) el worker se niega
a tomar otra cola que no sea de prueba. Así un worker local jamás procesa
trabajos de producción.

Variables: FINSYS_COLA (cola a atender, por defecto trabajos_prueba),
FINSYS_WORKER_HILOS, FINSYS_WORKER_ESPERA_S (pausa cuando no hay nada),
FINSYS_WORKER_LATIDO (archivo que se toca en cada vuelta, para el healthcheck).
"""
import logging
import os
import pathlib
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

import fin_sys_core  # noqa: F401  (alias de importación de los drivers)
from fin_sys_core import cola as cola_mod

log = logging.getLogger("finsys.worker")

Manejador = Callable[[Dict[str, Any], Dict[str, Any]], Optional[Dict[str, Any]]]
MANEJADORES: Dict[str, Manejador] = {}


class ErrorDefinitivo(Exception):
    """Error del pedido (dato inválido, no existe, conflicto): reintentar no
    lo arregla, así que la operación queda FALLIDA de una vez con este mensaje."""


def manejador(tipo: str):
    """Decorador: registra la función que hace los trabajos de `tipo`.
    Recibe (datos, op) y devuelve el resultado (dict) que verá el usuario.
    Debe poder correr dos veces sin daño (entrega al menos una vez)."""
    def registrar(fn: Manejador) -> Manejador:
        MANEJADORES[tipo] = fn
        return fn
    return registrar


def cola_permitida(cola: str) -> None:
    """Un worker sin FINSYS_WORKER_PRODUCCION=1 solo atiende colas de prueba."""
    if not cola_mod.es_cola_de_prueba(cola) and os.getenv("FINSYS_WORKER_PRODUCCION") != "1":
        raise SystemExit(f"⛔ La cola '{cola}' es de producción y la BD es compartida: este worker "
                         "solo la atiende con FINSYS_WORKER_PRODUCCION=1 (lo pone docker-compose).")


def procesar_uno(cola: str, vt: int = cola_mod.VT_S) -> bool:
    """Toma y hace UN trabajo. → True si había algo (aunque fallara)."""
    trabajo = cola_mod.tomar(cola, vt)
    if trabajo is None:
        return False
    op = trabajo["op"]
    if op is None:                      # mensaje de una operación que ya terminó
        return True
    fn = MANEJADORES.get(op["tipo"])
    if fn is None:
        cola_mod.fallar({**trabajo, "op": {**op, "intentos": op["max_intentos"]}},
                        f"Tipo de trabajo desconocido: '{op['tipo']}'")
        return True

    vivo = threading.Event()

    def latir():
        # Cada tercio del tiempo de visibilidad: sigue siendo mío.
        while not vivo.wait(max(5, vt // 3)):
            try:
                cola_mod.extender(trabajo, vt)
            except Exception as e:      # el latido nunca tumba el trabajo
                log.warning("latido de la operación %s falló: %s", op["id"], e)

    latido = threading.Thread(target=latir, name=f"latido-{op['id']}", daemon=True)
    latido.start()
    t0 = time.perf_counter()
    try:
        resultado = fn(op.get("datos") or {}, op)
        cola_mod.terminar(trabajo, resultado)
        log.info("✅ operación %s (%s) en %.1f s", op["id"], op["tipo"], time.perf_counter() - t0)
    except ErrorDefinitivo as e:
        cola_mod.fallar({**trabajo, "op": {**op, "intentos": op["max_intentos"]}}, str(e))
        log.info("⛔ operación %s (%s) rechazada: %s", op["id"], op["tipo"], e)
    except Exception as e:
        desenlace = cola_mod.fallar(trabajo, f"{type(e).__name__}: {e}")
        log.warning("❌ operación %s (%s) → %s: %s", op["id"], op["tipo"], desenlace, e)
    finally:
        vivo.set()
        latido.join(timeout=5)
    return True


def _tocar(latido: Optional[str]) -> None:
    if latido:
        try:
            pathlib.Path(latido).touch()
        except OSError:
            pass


def bucle(cola: str, hilos: int, parar: threading.Event, espera_s: float = 1.0,
          latido: Optional[str] = None) -> None:
    """`hilos` vueltas en paralelo hasta que `parar` se encienda."""
    def vuelta():
        while not parar.is_set():
            _tocar(latido)
            try:
                hubo = procesar_uno(cola)
            except Exception as e:      # BD caída o migración sin correr: esperar y seguir
                log.warning("vuelta del worker falló (reintento en 30 s): %s", str(e)[:300])
                parar.wait(30)
                continue
            if not hubo:
                parar.wait(espera_s)

    with ThreadPoolExecutor(max_workers=hilos, thread_name_prefix="worker") as pool:
        for _ in range(hilos):
            pool.submit(vuelta)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cola = cola_mod.cola_por_defecto()
    cola_permitida(cola)
    hilos = max(1, int(os.getenv("FINSYS_WORKER_HILOS", "2")))
    espera = float(os.getenv("FINSYS_WORKER_ESPERA_S", "1"))
    latido = os.getenv("FINSYS_WORKER_LATIDO", "/tmp/finsys-worker-vivo")
    from fin_sys_core import worker_jobs  # noqa: F401  (registra los manejadores)

    parar = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, lambda *_: parar.set())
        except (ValueError, AttributeError):
            pass
    log.info("🧰 worker en la cola '%s' con %s hilos; tipos: %s", cola, hilos, sorted(MANEJADORES))
    bucle(cola, hilos, parar, espera, latido)
    log.info("worker detenido")


if __name__ == "__main__":
    # Con `python -m` este archivo corre como __main__: se usa el módulo
    # canónico para que MANEJADORES sea el mismo en que registra worker_jobs.
    from fin_sys_core.worker import main as _main
    _main()
