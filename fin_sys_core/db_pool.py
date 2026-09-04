# -*- coding: utf-8 -*-
"""
db_pool.py — Pool de Conexiones Centralizado para FIN-SYS OS v2.0
==================================================================
Reemplaza las llamadas directas a psycopg2.connect() en todos los drivers.
Un solo ThreadedConnectionPool compartido por database_driver, hub_driver,
hr_driver y control_tower_driver.

USO:
    from fin_sys_core.db_pool import get_conn, put_conn

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(...)
        conn.commit()
    finally:
        put_conn(conn)

    # O con context manager:
    with pooled_connection() as conn:
        cur = conn.cursor()
        ...
"""

import os
import threading
import weakref
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# ── Configuración desde variables de entorno ──────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "fin_sys_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
# Tamaño del pool configurable por entorno (antes hardcodeado 2-10).
DB_POOL_MIN = int(os.getenv("DB_POOL_MIN", "2"))
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))
# Tope de conexiones DIRECTAS simultáneas cuando el pool no alcanza. Sin esto,
# el agotamiento del pool abría una conexión por hilo SIN LÍMITE (40/worker)
# y multiplicaba la carga contra el pooler (auditoría 2026-09-04).
DB_FALLBACK_MAX = int(os.getenv("DB_FALLBACK_MAX", "5"))

# Parámetros comunes de conexión: keepalives para que una red caída no deje
# conexiones zombis retenidas, y nombre visible en pg_stat_activity.
_CONN_KWARGS = dict(
    host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD,
    port=DB_PORT, connect_timeout=10,
    keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3,
    application_name=os.getenv("DB_APP_NAME", "finsys-backend"),
)

# ── Pool global ───────────────────────────────────────────────────────────────
_pool: ThreadedConnectionPool | None = None
_init_lock = threading.Lock()
_init_failed = False   # si la creación del pool falló, no reintentar en cada get
_fallback_sem = threading.BoundedSemaphore(DB_FALLBACK_MAX)
# Registro de conexiones de fallback. Las conexiones de psycopg2 son objetos C
# SIN __dict__: asignarles un atributo lanza AttributeError (incidente
# 2026-09-04, tumbó terceros/cartera en local). WeakSet: si un caller pierde
# la conexión sin devolverla, el GC la saca sola del registro.
_fallback_conns = weakref.WeakSet()


def init_pool(minconn: int = DB_POOL_MIN, maxconn: int = DB_POOL_MAX):
    """
    Inicializa el pool de conexiones. Llamar UNA VEZ al iniciar el servidor.
    minconn: conexiones que se abren inmediatamente
    maxconn: máximo de conexiones simultáneas permitidas
    Configurables por env: DB_POOL_MIN / DB_POOL_MAX.
    """
    global _pool
    if _pool is not None:
        return  # Ya inicializado

    try:
        _pool = ThreadedConnectionPool(
            minconn,
            maxconn,
            **_CONN_KWARGS,
            # sslmode se hereda del servidor (Supabase requiere SSL)
        )
        print(f"✅ Pool de conexiones inicializado: {minconn}-{maxconn} conexiones a {DB_HOST}:{DB_PORT}/{DB_NAME}")
    except Exception as e:
        print(f"⚠️ [AVISO] No se pudo inicializar el pool de conexiones: {e}")
        _pool = None


def get_conn():
    """
    Obtiene una conexión del pool (inicializándolo perezosamente la primera vez).

    BUG histórico (2026-08-24): init_pool() existía pero NINGÚN entrypoint lo
    llamaba, así que cada get_conn() caía al fallback y abría una conexión TLS
    nueva a Supabase (~0.7s c/u) — el dashboard hacía 7-8 de esas por request.
    La inicialización perezosa cubre server, poller del bot y scripts por igual.
    IMPORTANTE: Siempre devolver la conexión con put_conn() al terminar.
    """
    global _init_failed
    if _pool is None and not _init_failed:
        with _init_lock:
            if _pool is None and not _init_failed:
                init_pool()
                if _pool is None:
                    _init_failed = True   # sin pool posible: fallback directo estable

    if _pool is not None:
        try:
            return _pool.getconn()
        except Exception as e:
            print(f"⚠️ Pool agotado o error, fallback a conexión directa: {e}")

    # Fallback CON TOPE (DB_FALLBACK_MAX simultáneas): si el pool se agota, el
    # sistema debe fallar rápido y visible, no inundar el pooler de Supabase
    # con una conexión por hilo. El semáforo se libera en put_conn().
    if not _fallback_sem.acquire(timeout=5):
        raise ConnectionError(
            "Base de datos saturada: pool agotado y tope de conexiones "
            f"directas ({DB_FALLBACK_MAX}) alcanzado. Reintenta en unos segundos."
        )
    conn = None
    try:
        conn = psycopg2.connect(**_CONN_KWARGS)
        _fallback_conns.add(conn)   # put_conn libera el semáforo con esto
        return conn
    except Exception:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        _fallback_sem.release()
        raise


def put_conn(conn):
    """
    Devuelve una conexión al pool para su reutilización.
    Si el pool no está activo, cierra la conexión directamente.
    """
    if conn is None:
        return
    # Conexión de fallback: cerrarla y devolver el cupo del semáforo.
    if conn in _fallback_conns:
        _fallback_conns.discard(conn)
        try:
            conn.close()
        finally:
            try:
                _fallback_sem.release()
            except ValueError:
                pass   # doble release defensivo: no romper por contarlo dos veces
        return
    try:
        if _pool is not None:
            # Higiene: jamás devolver al pool una transacción a medias — el
            # siguiente usuario heredaría un "idle in transaction".
            try:
                conn.rollback()
            except Exception:
                pass
            _pool.putconn(conn)
        else:
            conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


@contextmanager
def pooled_connection(cursor_factory=None):
    """
    Context manager para usar conexiones del pool de forma segura.

    Uso:
        with pooled_connection() as conn:
            cur = conn.cursor()
            cur.execute(...)
            conn.commit()

        with pooled_connection(cursor_factory=RealDictCursor) as conn:
            ...
    """
    conn = get_conn()
    if cursor_factory:
        # Configurar el cursor_factory para esta conexión
        conn.cursor_factory = cursor_factory
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def close_pool():
    """Cierra todas las conexiones del pool. Llamar al apagar el servidor."""
    global _pool
    if _pool is not None:
        try:
            _pool.closeall()
            print("🔌 Pool de conexiones cerrado.")
        except Exception:
            pass
        _pool = None


def pool_status() -> dict:
    """Devuelve información sobre el estado del pool (para health checks)."""
    if _pool is None:
        return {"active": False, "reason": "Pool no inicializado"}
    return {
        "active": True,
        "minconn": _pool.minconn,
        "maxconn": _pool.maxconn,
    }
