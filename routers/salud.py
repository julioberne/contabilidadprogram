# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: salud del servidor (estándar de consultas, H1/P12).

GET /api/health/vida      → vida (liveness) SIN tocar la BD. Es lo que mira el
                            healthcheck de Docker: si la BD cae, el contenedor
                            NO debe reiniciarse en bucle (Builders' Library de
                            AWS: el health de vida no depende de dependencias).
GET /api/health/profundo  → BD + pool + admisión, para alarmas y monitoreo.

`sonda_bd()` guarda su resultado SALUD_TTL_S segundos y una sola sonda corre a
la vez (single-flight): con N pestañas sondeando /api/health cada 30 s, la BD
recibe como mucho una consulta cada SALUD_TTL_S por worker, no N.
"""
import concurrent.futures
import threading
import time

from fastapi import APIRouter

router = APIRouter(tags=["system"])

SALUD_TTL_S = 10.0
_TIMEOUT_SONDA_S = 4.0

_lock = threading.Lock()
_cache = {"t": 0.0, "db": None}
_en_curso = {"fut": None}
_ejecutor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="sonda-bd")


def _sonda() -> str:
    # ⚠️ SIEMPRE devolver la conexión al pool, jamás conn.close() (ver server.py).
    conn = None
    try:
        from fin_sys_core.database_driver import get_db_connection, release_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return "connected"
    except Exception as e:
        return f"error: {e}"
    finally:
        if conn is not None:
            try:
                from fin_sys_core.database_driver import release_db_connection
                release_db_connection(conn)
            except Exception:
                pass


def sonda_bd() -> str:
    """Estado de la BD con caché corta y una sola sonda a la vez. Nunca tarda
    más de ~4 s aunque la red a Supabase esté caída."""
    ahora = time.monotonic()
    with _lock:
        if _cache["db"] is not None and ahora - _cache["t"] < SALUD_TTL_S:
            return _cache["db"]
        fut = _en_curso["fut"]
        if fut is None or fut.done():
            fut = _en_curso["fut"] = _ejecutor.submit(_sonda)
    try:
        estado = fut.result(timeout=_TIMEOUT_SONDA_S)
    except concurrent.futures.TimeoutError:
        estado = "error: la base de datos no respondió en 4s (timeout)"
    except Exception as e:
        estado = f"error: {e}"
    with _lock:
        _cache.update(t=time.monotonic(), db=estado)
    return estado


def estado_pool() -> dict:
    try:
        from fin_sys_core.db_pool import pool_status
        return pool_status()
    except Exception as e:
        return {"active": False, "reason": str(e)}


@router.get("/api/health/vida")
def salud_vida():
    return {"status": "ok"}


@router.get("/api/health/profundo")
def salud_profunda():
    from fin_sys_core.cola import metricas
    from shared.admision import resumen
    # cola: largo, edad del mensaje más viejo y operaciones en vuelo (H5);
    # {"activa": false} mientras no se corra scripts/migrate_operaciones.py.
    return {"status": "ok", "db": sonda_bd(), "pool": estado_pool(),
            "admision": resumen(), "cola": metricas(), "version": "2.0"}
