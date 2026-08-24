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

# ── Pool global ───────────────────────────────────────────────────────────────
_pool: ThreadedConnectionPool | None = None
_init_lock = threading.Lock()
_init_failed = False   # si la creación del pool falló, no reintentar en cada get


def init_pool(minconn: int = 2, maxconn: int = 10):
    """
    Inicializa el pool de conexiones. Llamar UNA VEZ al iniciar el servidor.
    minconn: conexiones que se abren inmediatamente
    maxconn: máximo de conexiones simultáneas permitidas
    """
    global _pool
    if _pool is not None:
        return  # Ya inicializado

    try:
        _pool = ThreadedConnectionPool(
            minconn,
            maxconn,
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            connect_timeout=10,
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

    # Fallback: conexión directa (comportamiento original)
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        connect_timeout=10,
    )


def put_conn(conn):
    """
    Devuelve una conexión al pool para su reutilización.
    Si el pool no está activo, cierra la conexión directamente.
    """
    if conn is None:
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
