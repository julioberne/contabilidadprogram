# -*- coding: utf-8 -*-
"""cola.py — Trabajos en segundo plano (estándar de consultas, hito H5).

Decisión de Andrés (19-oct-2026): la COLA es pgmq (Supabase Queues) y la tabla
`operaciones` guarda el ESTADO que ve el usuario. Lo pesado (exportaciones,
ZIP, PDF, voz, IA, envíos a Telegram) deja de correr dentro de la petición:
la API encola y responde 202; el servicio `worker` (fin_sys_core/worker.py)
lo hace y deja el resultado en `operaciones`.

  encolar   → fila en `operaciones` + pgmq.send, en la MISMA transacción (con
              `cur`, la del llamador: el trabajo nace con el asiento o no nace).
              Clave determinista: un doble clic no encola dos veces mientras el
              primero esté PENDIENTE o EN_CURSO.
  tomar     → pgmq.read con tiempo de visibilidad: si el worker muere, el
              mensaje reaparece y otro lo retoma (entrega al menos una vez: los
              trabajos deben poder correr dos veces sin daño).
  terminar  → HECHA + pgmq.archive (queda el rastro en pgmq.a_<cola>).
  fallar    → reintento con espera creciente (pgmq.set_vt) o FALLIDA al agotar
              los intentos (pgmq no tiene cola de muertos: es este estado).
  metricas  → edad del mensaje más viejo (la señal de capacidad, regla 4).

Cada llamada a pgmq es UNA sentencia SQL: funciona por el pooler :6543.
La cola por defecto es `trabajos_prueba`: la de producción (`trabajos`) solo la
usan la API y el worker de Dokploy (FINSYS_COLA=trabajos en docker-compose),
porque la BD es la misma en local y en producción.
"""
import hashlib
import json
import os
from typing import Any, Dict, Optional

from psycopg2.extras import Json, RealDictCursor

from fin_sys_core.db_pool import get_conn, put_conn

COLA_PRODUCCION = "trabajos"
COLA_PRUEBA = "trabajos_prueba"
ESTADOS = ("PENDIENTE", "EN_CURSO", "HECHA", "FALLIDA")
VT_S = int(os.getenv("FINSYS_COLA_VT_S", "300"))      # visibilidad de un mensaje tomado
ESPERA_MAX_S = 300                                     # tope de la espera entre reintentos


class ColaNoDisponible(Exception):
    """pgmq o la tabla `operaciones` no existen todavía (falta la migración)."""


def cola_por_defecto() -> str:
    return (os.getenv("FINSYS_COLA") or COLA_PRUEBA).strip()


def es_cola_de_prueba(cola: str) -> bool:
    return cola == COLA_PRUEBA or cola.endswith("_prueba")


def en_cola(trabajo: str) -> bool:
    """¿Este trabajo va por la cola? FINSYS_EN_COLA=exportacion,entrega,diario_csv
    (H5.3: una sola variable). FINSYS_EXPORT_EN_COLA=1 sigue valiendo como
    «exportacion». Vacía = todo síncrono, como antes de H5."""
    lista = {t.strip().lower() for t in (os.getenv("FINSYS_EN_COLA") or "").split(",") if t.strip()}
    if os.getenv("FINSYS_EXPORT_EN_COLA") == "1":
        lista.add("exportacion")
    return trabajo in lista


def clave_de(tipo: str, usuario: Optional[str], datos: Dict[str, Any]) -> str:
    """Clave determinista: mismo tipo, usuario y datos → misma clave."""
    huella = hashlib.sha1(json.dumps(datos, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return f"{tipo}:{usuario or '-'}:{huella[:20]}"


def espera_reintento(intentos: int) -> int:
    """10 s, 20 s, 40 s… con tope de ESPERA_MAX_S."""
    return int(min(ESPERA_MAX_S, 10 * 2 ** max(0, intentos - 1)))


_SQL_ALTA = """
INSERT INTO operaciones (tipo, cola, clave, datos, usuario, empresa, max_intentos)
VALUES (%(tipo)s, %(cola)s, %(clave)s, %(datos)s, %(usuario)s, %(empresa)s, %(max_intentos)s)
ON CONFLICT (clave) WHERE estado IN ('PENDIENTE', 'EN_CURSO') DO NOTHING
RETURNING id"""
_SQL_EN_VUELO = ("SELECT id FROM operaciones WHERE clave = %s AND estado IN ('PENDIENTE', 'EN_CURSO') "
                 "ORDER BY id DESC LIMIT 1")
_SQL_ENVIAR = "SELECT pgmq.send(%s::text, %s::jsonb)"
_SQL_MSG = "UPDATE operaciones SET msg_id = %s, actualizada = now() WHERE id = %s"
_SQL_LEER = "SELECT msg_id, read_ct, message FROM pgmq.read(%s::text, %s::integer, 1)"
_SQL_EMPEZAR = """
UPDATE operaciones
   SET estado = 'EN_CURSO', intentos = %(intentos)s, iniciada = COALESCE(iniciada, now()), actualizada = now()
 WHERE id = %(id)s AND estado IN ('PENDIENTE', 'EN_CURSO')
RETURNING id, tipo, cola, datos, usuario, empresa, intentos, max_intentos"""
_SQL_ARCHIVAR = "SELECT pgmq.archive(%s::text, %s::bigint)"
_SQL_VISIBLE_EN = "SELECT pgmq.set_vt(%s::text, %s::bigint, %s::integer)"
_SQL_HECHA = """
UPDATE operaciones SET estado = 'HECHA', resultado = %s, error = NULL, terminada = now(), actualizada = now()
 WHERE id = %s"""
_SQL_FALLIDA = """
UPDATE operaciones SET estado = 'FALLIDA', error = %s, terminada = now(), actualizada = now() WHERE id = %s"""
_SQL_REINTENTO = "UPDATE operaciones SET estado = 'PENDIENTE', error = %s, actualizada = now() WHERE id = %s"
_SQL_ESTADO = """
SELECT id, tipo, estado, resultado, error, intentos, max_intentos, usuario, empresa,
       creada, iniciada, terminada
  FROM operaciones WHERE id = %s"""
_SQL_METRICAS = "SELECT queue_length, oldest_msg_age_sec, newest_msg_age_sec, total_messages FROM pgmq.metrics(%s::text)"
_SQL_CONTEOS = ("SELECT estado, count(*) AS n FROM operaciones WHERE cola = %s AND estado IN ('PENDIENTE', 'EN_CURSO') "
                "GROUP BY 1")


def _no_disponible(e: Exception) -> bool:
    """¿El error es porque falta pgmq o la tabla (migración sin correr)?"""
    texto = str(e).lower()
    return any(s in texto for s in ('relation "operaciones" does not exist', 'schema "pgmq" does not exist',
                                    "function pgmq.", "pgmq.q_"))


def encolar(tipo: str, datos: Dict[str, Any], *, usuario: Optional[str] = None, empresa: Optional[str] = None,
            clave: Optional[str] = None, cola: Optional[str] = None, max_intentos: int = 3,
            cur=None) -> Dict[str, Any]:
    """Encola un trabajo → {"id", "nueva", "cola"}. Con `cur` va dentro de la
    transacción del llamador (no hace commit); sin `cur`, abre y confirma la suya.
    Si ya hay uno igual en vuelo devuelve ese (nueva=False)."""
    cola = cola or cola_por_defecto()
    clave = clave or clave_de(tipo, usuario, datos)
    propia = cur is None
    conn = get_conn() if propia else None
    try:
        c = conn.cursor() if propia else cur
        c.execute(_SQL_ALTA, {"tipo": tipo, "cola": cola, "clave": clave, "datos": Json(datos),
                              "usuario": usuario, "empresa": empresa, "max_intentos": int(max_intentos)})
        fila = c.fetchone()
        if fila:
            op_id = int(fila[0])
            c.execute(_SQL_ENVIAR, (cola, Json({"operacion": op_id, "tipo": tipo})))
            c.execute(_SQL_MSG, (int(c.fetchone()[0]), op_id))
            nueva = True
        else:
            c.execute(_SQL_EN_VUELO, (clave,))
            op_id, nueva = int(c.fetchone()[0]), False
        if propia:
            conn.commit()
        return {"id": op_id, "nueva": nueva, "cola": cola}
    except Exception as e:
        if _no_disponible(e):
            raise ColaNoDisponible("La cola de trabajos aún no está instalada "
                                   "(falta scripts/migrate_operaciones.py).") from e
        raise
    finally:
        if propia:
            put_conn(conn)


def tomar(cola: str, vt: int = VT_S) -> Optional[Dict[str, Any]]:
    """Toma el próximo trabajo de `cola` (invisible `vt` segundos para los
    demás) → {"op", "msg_id", "cola"} o None si no hay nada que hacer."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_SQL_LEER, (cola, int(vt)))
            msg = cur.fetchone()
            if not msg:
                conn.commit()
                return None
            op_id = int((msg["message"] or {}).get("operacion") or 0)
            cur.execute(_SQL_EMPEZAR, {"id": op_id, "intentos": int(msg["read_ct"])})
            op = cur.fetchone()
            if not op:
                # La operación ya terminó (o no existe): el mensaje sobra.
                cur.execute(_SQL_ARCHIVAR, (cola, int(msg["msg_id"])))
                conn.commit()
                return {"op": None, "msg_id": int(msg["msg_id"]), "cola": cola}
            conn.commit()
            return {"op": dict(op), "msg_id": int(msg["msg_id"]), "cola": cola}
    finally:
        put_conn(conn)


def extender(trabajo: Dict[str, Any], segundos: int = VT_S) -> None:
    """Latido: el trabajo sigue vivo, que no reaparezca para otro worker."""
    _ejecutar(_SQL_VISIBLE_EN, (trabajo["cola"], trabajo["msg_id"], int(segundos)))


def terminar(trabajo: Dict[str, Any], resultado: Optional[Dict[str, Any]] = None) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(_SQL_HECHA, (Json(resultado or {}), trabajo["op"]["id"]))
            cur.execute(_SQL_ARCHIVAR, (trabajo["cola"], trabajo["msg_id"]))
        conn.commit()
    finally:
        put_conn(conn)


def fallar(trabajo: Dict[str, Any], error: str) -> str:
    """Reintento con espera creciente, o FALLIDA al agotar los intentos.
    → "reintento" | "fallida"."""
    op = trabajo["op"]
    error = (error or "error desconocido")[:2000]
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if int(op["intentos"]) >= int(op["max_intentos"]):
                cur.execute(_SQL_FALLIDA, (error, op["id"]))
                cur.execute(_SQL_ARCHIVAR, (trabajo["cola"], trabajo["msg_id"]))
                desenlace = "fallida"
            else:
                cur.execute(_SQL_REINTENTO, (error, op["id"]))
                cur.execute(_SQL_VISIBLE_EN, (trabajo["cola"], trabajo["msg_id"],
                                              espera_reintento(int(op["intentos"]))))
                desenlace = "reintento"
        conn.commit()
        return desenlace
    finally:
        put_conn(conn)


def estado(op_id: int) -> Optional[Dict[str, Any]]:
    """Estado de una operación para /api/operaciones/{id}."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_SQL_ESTADO, (int(op_id),))
            fila = cur.fetchone()
            return dict(fila) if fila else None
    except Exception as e:
        if _no_disponible(e):
            raise ColaNoDisponible("La cola de trabajos aún no está instalada.") from e
        raise
    finally:
        put_conn(conn)


def metricas(cola: Optional[str] = None) -> Dict[str, Any]:
    """Para /api/health/profundo: largo, edad del más viejo y operaciones en vuelo.
    Nunca lanza: si falta la migración, {"activa": False}."""
    cola = cola or cola_por_defecto()
    try:
        conn = get_conn()
    except Exception as e:
        return {"activa": False, "cola": cola, "motivo": str(e)[:200]}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_SQL_METRICAS, (cola,))
            m = dict(cur.fetchone() or {})
            cur.execute(_SQL_CONTEOS, (cola,))
            en_vuelo = {r["estado"]: int(r["n"]) for r in cur.fetchall()}
        return {"activa": True, "cola": cola, "largo": int(m.get("queue_length") or 0),
                "edad_mas_viejo_s": m.get("oldest_msg_age_sec"), "en_vuelo": en_vuelo}
    except Exception as e:
        return {"activa": False, "cola": cola,
                "motivo": "falta la migración" if _no_disponible(e) else str(e)[:200]}
    finally:
        put_conn(conn)


def _ejecutar(sql: str, params) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    finally:
        put_conn(conn)
