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

import collections
import contextvars
import os
import threading
import time
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
DB_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))
# DB_POOL_MIN = DB_POOL_MAX por defecto (H2, laboratorio 16-oct-2026): el
# ThreadedConnectionPool de psycopg2 CIERRA al devolver toda conexión por
# encima de minconn y abre las nuevas DENTRO de su candado. Con min=2, cada
# petición por encima de 2 simultáneas pagaba un handshake TLS con Supabase
# (~0,5 s desde Colombia, ~50-100 ms desde el VPS) en fila: 10 consultas
# simultáneas tardaban 4,5 s. Con el pool lleno y caliente no se reconecta.
# En modo transacción las conexiones ociosas no ocupan conexiones del servidor.
DB_POOL_MIN = min(DB_POOL_MAX, int(os.getenv("DB_POOL_MIN", str(DB_POOL_MAX))))
# Tope de conexiones DIRECTAS simultáneas cuando el pool no alcanza. Sin esto,
# el agotamiento del pool abría una conexión por hilo SIN LÍMITE (40/worker)
# y multiplicaba la carga contra el pooler (auditoría 2026-09-04).
DB_FALLBACK_MAX = int(os.getenv("DB_FALLBACK_MAX", "5"))

# ── Pool que ESPERA con tope (estándar de consultas, hito H2 / regla P2) ─────
# Antes, con el pool agotado, get_conn() no esperaba: hacía una sonda de
# failover (hasta 4 s en el hilo de la petición) y abría conexiones TLS
# directas (~0,7 s c/u, hasta DB_FALLBACK_MAX), multiplicando la carga contra
# el pooler justo en el pico. Ahora cada préstamo toma un TURNO (semáforo del
# tamaño del pool): si no hay, espera hasta DB_POOL_ESPERA_S; si no llega o ya
# hay DB_POOL_MAX_ESPERA peticiones en fila, PoolSaturado → 503 + Retry-After
# (shared/admision.py). DB_FALLBACK_SI_AGOTADO=1 restaura el comportamiento
# anterior. El failover de canal (abajo) no cambia.
DB_POOL_ESPERA_S = float(os.getenv("DB_POOL_ESPERA_S", "1.0"))
DB_POOL_MAX_ESPERA = int(os.getenv("DB_POOL_MAX_ESPERA", str(2 * DB_POOL_MAX)))
DB_FALLBACK_SI_AGOTADO = os.getenv("DB_FALLBACK_SI_AGOTADO", "0") == "1"


class PoolSaturado(ConnectionError):
    """Todas las conexiones del pool están prestadas y la espera se agotó."""


# Marca por petición: el middleware de shared/admision.py pone aquí un dict y,
# si get_conn rechaza por saturación, la marca convierte el 500 genérico del
# endpoint en un 503 + Retry-After (la mayoría de routers envuelven todo en 500).
saturacion_ctx = contextvars.ContextVar("finsys_saturacion", default=None)

# ── Failover automático de canal (incidente Supabase 08/09-sep-2026) ─────────
# El pooler transaction-mode (:6543) estuvo ~19h aceptando conexiones SIN
# servir queries, y recayó al día siguiente. El session-mode (:5432) siguió
# vivo. Este failover hace solo lo que ese día se hizo a mano ("el puente"):
#   · si el canal primario no FLUYE (sonda con timeout duro), el pool se pasa
#     al respaldo con POOLS MÍNIMOS (límite ~15 conexiones del session mode);
#   · un vigía interno regresa al primario cuando fluye 2 veces seguidas
#     (anti-aleteo).
# Se desactiva con DB_FAILOVER=0, o solo por config si primario == respaldo.
DB_FAILOVER = os.getenv("DB_FAILOVER", "1") == "1"
DB_FAILOVER_PORT = os.getenv("DB_FAILOVER_PORT", "5432")
_RESPALDO_POOL_MIN = 1
_RESPALDO_POOL_MAX = 2
_VIGIA_INTERVALO_S = 45
_SONDAS_PARA_VOLVER = 2

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
# Canal activo del failover (el puerto REAL en uso puede diferir de DB_PORT)
_canal = {"puerto": DB_PORT, "respaldo": False}
_vigia_activo = False
_ultima_sonda_caida = 0.0   # throttle del failover en caliente
_fallback_sem = threading.BoundedSemaphore(DB_FALLBACK_MAX)
# Registro de conexiones de fallback. Las conexiones de psycopg2 son objetos C
# SIN __dict__: asignarles un atributo lanza AttributeError (incidente
# 2026-09-04, tumbó terceros/cartera en local). WeakSet: si un caller pierde
# la conexión sin devolverla, el GC la saca sola del registro.
_fallback_conns = weakref.WeakSet()
# Finalizers por conexión de fallback: si un caller con fuga (los DT-23) pierde
# la conexión, el GC la cierra pero el CUPO del semáforo quedaba perdido para
# siempre — con 5 fugas el sistema entero quedaba en "saturada" permanente
# hasta reiniciar (incidente prod 2026-09-06). El finalize devuelve el cupo.
_fallback_finalizers = {}

# Turnos del pool (H2). Una conexión del pool que se presta con turno queda en
# _turno_conns; put_conn devuelve el turno. Si un caller la pierde sin
# devolverla, el pool de psycopg2 la sigue referenciando en _used (no hay GC):
# el turno queda tomado igual que el cupo del pool, sin descuadre entre ambos.
_turnos = threading.BoundedSemaphore(DB_POOL_MAX)
_turno_conns = weakref.WeakSet()
_metricas_lock = threading.Lock()
_metricas = {"prestamos": 0, "esperas": 0, "rechazos": 0, "esperando": 0}
_esperas_ms = collections.deque(maxlen=500)


def _tomar_turno(espera_s: float) -> bool:
    """True si consiguió turno (sin esperar o esperando ≤ espera_s)."""
    if _turnos.acquire(blocking=False):
        with _metricas_lock:
            _metricas["prestamos"] += 1
        return True
    with _metricas_lock:
        if _metricas["esperando"] >= DB_POOL_MAX_ESPERA:
            _metricas["rechazos"] += 1
            return False
        _metricas["esperando"] += 1
    t0 = time.perf_counter()
    ok = _turnos.acquire(timeout=max(0.0, espera_s))
    ms = (time.perf_counter() - t0) * 1000.0
    with _metricas_lock:
        _metricas["esperando"] -= 1
        _metricas["esperas"] += 1
        _esperas_ms.append(ms)
        if ok:
            _metricas["prestamos"] += 1
        else:
            _metricas["rechazos"] += 1
    return ok


def _devolver_turno():
    try:
        _turnos.release()
    except ValueError:
        pass   # doble devolución defensiva


def _marcar_saturacion():
    marca = saturacion_ctx.get()
    if isinstance(marca, dict):
        marca["saturado"] = True


def _cupo_perdido_por_gc(conn_id):
    """El GC recogió una conexión de fallback fugada: devolver su cupo."""
    _fallback_finalizers.pop(conn_id, None)
    try:
        _fallback_sem.release()
    except ValueError:
        pass
    print("⚠️ [db_pool] Conexión de fallback FUGADA recuperada por GC — "
          "hay un caller sin release (ver DT-23).")


def _canal_fluye(puerto, timeout: float = 5.0) -> bool:
    """¿connect + SELECT 1 responden por ese puerto dentro del timeout?

    La sonda corre en un HILO con tope duro: en el incidente 08/09-sep las
    queries colgaban IGNORANDO statement_timeout — el pooler aceptaba la
    conexión pero jamás entregaba la consulta al servidor."""
    import concurrent.futures

    def _probar():
        kw = dict(_CONN_KWARGS)
        kw["port"] = puerto
        kw["connect_timeout"] = min(int(timeout), 5) or 3
        c = psycopg2.connect(**kw)
        try:
            cur = c.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
        finally:
            c.close()
        return True

    ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        return bool(ex.submit(_probar).result(timeout=timeout))
    except Exception:
        return False
    finally:
        ex.shutdown(wait=False)   # el hilo colgado muere solo; no esperarlo


def _failover_posible() -> bool:
    return DB_FAILOVER and str(DB_PORT) != str(DB_FAILOVER_PORT)


def _swap_pool(puerto, minconn, maxconn, motivo) -> bool:
    """Recrea el pool global en `puerto` bajo lock. → True si quedó activo."""
    global _pool
    with _init_lock:
        if _pool is not None and str(_canal["puerto"]) == str(puerto):
            return True
        try:
            nuevo = ThreadedConnectionPool(minconn, maxconn,
                                           **{**_CONN_KWARGS, "port": puerto})
        except Exception as e:
            print(f"⚠️ [failover] no se pudo abrir pool en :{puerto}: {e}")
            return False
        viejo, _pool = _pool, nuevo
        _canal["puerto"] = puerto
        _canal["respaldo"] = _failover_posible() and str(puerto) == str(DB_FAILOVER_PORT)
        print(f"🔀 [failover] {motivo} → canal :{puerto} (pool {minconn}-{maxconn})")
        if viejo is not None:
            try:
                viejo.closeall()
            except Exception:
                pass
        if _canal["respaldo"]:
            _arrancar_vigia_retorno()
        return True


def _arrancar_vigia_retorno():
    """Hilo daemon: mientras estemos en el respaldo, sondea el primario cada
    _VIGIA_INTERVALO_S y regresa cuando fluya _SONDAS_PARA_VOLVER veces
    seguidas (anti-aleteo). Muere solo al volver."""
    global _vigia_activo
    if _vigia_activo:
        return
    _vigia_activo = True

    def _loop():
        global _vigia_activo
        aciertos = 0
        try:
            while _canal["respaldo"]:
                time.sleep(_VIGIA_INTERVALO_S)
                if not _canal["respaldo"]:
                    break
                aciertos = aciertos + 1 if _canal_fluye(DB_PORT) else 0
                if aciertos >= _SONDAS_PARA_VOLVER:
                    if _swap_pool(DB_PORT, DB_POOL_MIN, DB_POOL_MAX,
                                  "canal primario recuperado"):
                        break
                    aciertos = 0
        finally:
            _vigia_activo = False

    threading.Thread(target=_loop, daemon=True, name="db-failover-vigia").start()


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

    # Failover al ARRANCAR: si el primario no fluye pero el respaldo sí,
    # nacer directamente en el respaldo (el fail-fast del server pasa y la
    # app queda operativa sin intervención humana).
    puerto = DB_PORT
    if _failover_posible() and not _canal_fluye(DB_PORT):
        if _canal_fluye(DB_FAILOVER_PORT):
            puerto = DB_FAILOVER_PORT
            minconn, maxconn = _RESPALDO_POOL_MIN, _RESPALDO_POOL_MAX
            print(f"🔀 [failover] :{DB_PORT} sin flujo al arrancar — "
                  f"nazco en el respaldo :{puerto} con pool mínimo")
        # si ninguno fluye: se intenta el primario y el error será honesto

    try:
        _pool = ThreadedConnectionPool(
            minconn,
            maxconn,
            **{**_CONN_KWARGS, "port": puerto},
            # sslmode se hereda del servidor (Supabase requiere SSL)
        )
        _canal["puerto"] = puerto
        _canal["respaldo"] = _failover_posible() and str(puerto) == str(DB_FAILOVER_PORT)
        if _canal["respaldo"]:
            _arrancar_vigia_retorno()
        print(f"✅ Pool de conexiones inicializado: {minconn}-{maxconn} conexiones a {DB_HOST}:{puerto}/{DB_NAME}")
    except Exception as e:
        print(f"⚠️ [AVISO] No se pudo inicializar el pool de conexiones: {e}")
        _pool = None


def get_conn(espera_s: float = None):
    """
    Obtiene una conexión del pool (inicializándolo perezosamente la primera vez).

    espera_s: cuánto esperar un turno si el pool está lleno (por defecto
    DB_POOL_ESPERA_S). Al vencer → PoolSaturado (503), nunca una conexión
    directa extra (salvo DB_FALLBACK_SI_AGOTADO=1).

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
        if not _tomar_turno(DB_POOL_ESPERA_S if espera_s is None else espera_s):
            if not DB_FALLBACK_SI_AGOTADO:
                _marcar_saturacion()
                raise PoolSaturado(
                    "Base de datos ocupada: todas las conexiones del pool están en uso "
                    f"({getattr(_pool, 'maxconn', DB_POOL_MAX)}). Intenta de nuevo en unos segundos.")
            turno = False          # comportamiento anterior: sigue al fallback directo
        else:
            turno = True
        conn = _prestar_del_pool() if turno else None
        if conn is not None:
            _turno_conns.add(conn)
            return conn
        if turno:
            _devolver_turno()      # no salió conexión viva: el turno no se usa

    return _respaldo_o_directa()


def _prestar_del_pool():
    """Una conexión VIVA del pool, o None (todas muertas / pool agotado)."""
    # Sanear al PRESTAR (incidente local 2026-09-07): tras un corte de red
    # con Supabase ("SSL connection has been closed unexpectedly"), el pool
    # queda lleno de conexiones muertas. `closed` + `poll()` detectan el
    # socket roto SIN round-trip a la BD; la rota se descarta
    # (putconn close=True) y psycopg2 repone una fresca en el siguiente
    # getconn. Sin esto, el veneno circulaba para siempre y solo un
    # reinicio "curaba" el server.
    for _ in range(getattr(_pool, "maxconn", DB_POOL_MAX) + 1):
        try:
            conn = _pool.getconn()
        except Exception as e:
            print(f"⚠️ Pool agotado o error, fallback a conexión directa: {e}")
            break
        try:
            if not conn.closed:
                conn.poll()   # socket muerto → OperationalError inmediato
                # Personalidad neutra al PRESTAR (bug 2026-09-11): un
                # caller previo pudo dejar cursor_factory=RealDictCursor
                # pegado a la conexión (hub_driver, pooled_connection) y
                # el siguiente recibía filas dict donde esperaba tuplas
                # (row[0] → KeyError: '0' — el eliminar de Andrés).
                conn.cursor_factory = None
                return conn
        except Exception:
            pass
        try:
            _pool.putconn(conn, close=True)   # descartar la muerta
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
    else:
        print("⚠️ Pool: todas las conexiones prestadas estaban muertas — "
              "descartadas; fallback directo.")
    return None


def _respaldo_o_directa():
    """Sin conexión del pool: failover en caliente y, si no, conexión directa con tope."""
    # ── Failover EN CALIENTE (2ª recaída, 09-sep): si el primario dejó de
    # fluir con el server corriendo, pasarse al respaldo sin reiniciar nada.
    # Throttle de 20s: no pagar sondas (≈4-8s) en cada request durante la caída.
    global _ultima_sonda_caida
    if (_failover_posible() and not _canal["respaldo"] and _pool is not None
            and time.time() - _ultima_sonda_caida > 20):
        _ultima_sonda_caida = time.time()
        if not _canal_fluye(_canal["puerto"], timeout=4) \
                and _canal_fluye(DB_FAILOVER_PORT, timeout=4):
            if _swap_pool(DB_FAILOVER_PORT, _RESPALDO_POOL_MIN,
                          _RESPALDO_POOL_MAX, "canal primario sin flujo"):
                try:
                    return _pool.getconn()
                except Exception:
                    pass

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
        # El fallback directo respeta el CANAL ACTIVO del failover
        conn = psycopg2.connect(**{**_CONN_KWARGS, "port": _canal["puerto"]})
        _fallback_conns.add(conn)   # put_conn libera el semáforo con esto
        _fallback_finalizers[id(conn)] = weakref.finalize(
            conn, _cupo_perdido_por_gc, id(conn))
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
    if conn in _turno_conns:
        _turno_conns.discard(conn)
        try:
            _devolver_al_pool(conn)
        finally:
            _devolver_turno()
        return
    _devolver_al_pool(conn)


def _devolver_al_pool(conn):
    # Conexión de fallback: cerrarla y devolver el cupo del semáforo.
    if conn in _fallback_conns:
        _fallback_conns.discard(conn)
        fin = _fallback_finalizers.pop(id(conn), None)
        if fin is not None:
            fin.detach()   # devolución normal: el finalizer del GC ya no aplica
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
            # Higiene doble: rollback evita devolver una transacción a medias
            # ("idle in transaction"), y si el rollback FALLA es que el socket
            # está roto — esa conexión se DESCARTA (close=True) en vez de
            # volver al pool. Devolverla rota era el bug que dejaba el pool
            # envenenado tras un corte de red (2026-09-07).
            try:
                if conn.closed:
                    raise psycopg2.OperationalError("conexión ya cerrada")
                conn.rollback()
            except Exception:
                try:
                    _pool.putconn(conn, close=True)
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass
                return
            # Al DEVOLVER, la conexión queda con personalidad neutra: sin esto,
            # el cursor_factory que un caller le pegó viajaba al siguiente
            # (bug 2026-09-11 — ver el saneo espejo en get_conn).
            try:
                conn.cursor_factory = None
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
        return {"active": False, "reason": "Pool no inicializado",
                "init_failed": _init_failed}
    # `_used` / `_pool` son internos de psycopg2.pool.AbstractConnectionPool
    # (estables desde 2.x); si cambian, el health no debe caerse.
    try:
        en_uso = len(getattr(_pool, "_used", {}))
        libres = len(getattr(_pool, "_pool", []))
    except Exception:
        en_uso, libres = None, None
    return {
        "active": True,
        "minconn": _pool.minconn,
        "maxconn": _pool.maxconn,
        "used": en_uso,
        "free": libres,
        "fallback_en_uso": DB_FALLBACK_MAX - _fallback_sem._value,
        "fallback_max": DB_FALLBACK_MAX,
        "puerto": _canal["puerto"],
        "en_respaldo": _canal["respaldo"],
        "init_failed": _init_failed,
        "espera": metricas_espera(),
    }


def metricas_espera() -> dict:
    """Turnos del pool (H2): para /api/health/profundo y el laboratorio."""
    with _metricas_lock:
        esperas = sorted(_esperas_ms)
        m = dict(_metricas)
    p95 = esperas[min(len(esperas) - 1, int(0.95 * (len(esperas) - 1)))] if esperas else 0.0
    return {**m, "turnos_libres": _turnos._value, "turnos": DB_POOL_MAX,
            "p95_ms": round(p95, 1), "max_ms": round(esperas[-1], 1) if esperas else 0.0,
            "timeout_s": DB_POOL_ESPERA_S, "max_en_fila": DB_POOL_MAX_ESPERA,
            "fallback_si_agotado": DB_FALLBACK_SI_AGOTADO}
