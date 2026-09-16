# -*- coding: utf-8 -*-
"""
FIN-SYS OS — Análisis Inteligente: bitácora de preguntas sin responder
----------------------------------------------------------------------
Archivo NUEVO (pedido de Andrés, 16-sep). Cuando una pregunta en español
no se puede responder (no cae en el catálogo, falló la red hacia el
traductor, o el cálculo rechazó los parámetros), se guarda AQUÍ para
poder revisarla y decidir si amerita una métrica nueva del catálogo.

Reglas:
  - Tabla propia (analytics_question_log), jamás toca las contables.
  - Retención 30 días: cada registro purga lo viejo en la misma pasada
    (no depende de ningún scheduler — hoy no existe ninguno).
  - Best-effort SIEMPRE: si la bitácora falla, la respuesta al usuario
    sale igual. Registrar jamás lanza.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

RETENCION_DIAS = 30

# Códigos de resultado (columna `resultado`):
#   SIN_METRICA     → el catálogo no cubre la pregunta (motivo del traductor)
#   SIN_RED         → no hubo salida a internet hacia Groq/Gemini
#   ERROR_TRADUCTOR → el traductor falló por otra razón
#   ERROR_CALCULO   → eligió métrica pero el catálogo rechazó los parámetros


def _conn_del_pool():
    from database_driver import get_db_connection
    return get_db_connection()


def _devolver(conn):
    if conn is None:
        return
    try:
        from database_driver import release_db_connection
        release_db_connection(conn)
    except Exception:
        pass


def init_analytics_log_table(conn=None) -> None:
    """Crea la tabla si no existe (llamada en el arranque del server)."""
    propia = conn is None
    if propia:
        conn = _conn_del_pool()
        if conn is None:
            return
    try:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS analytics_question_log (
            id SERIAL PRIMARY KEY,
            pregunta TEXT NOT NULL,
            resultado VARCHAR(20) NOT NULL,
            detalle TEXT,
            metrica VARCHAR(50),
            portfolio_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
        cur.close()
    finally:
        if propia:
            _devolver(conn)


def registrar_pregunta(pregunta: str, resultado: str, detalle: str = "",
                       metrica: Optional[str] = None,
                       portfolio_id: Optional[int] = None, conn=None) -> bool:
    """Guarda una pregunta fallida y purga lo de hace más de 30 días.
    Best-effort: devuelve False si no se pudo, jamás lanza."""
    propia = conn is None
    try:
        if propia:
            conn = _conn_del_pool()
            if conn is None:
                return False
        cur = conn.cursor()
        # Purga en la misma pasada: la retención no depende de un scheduler.
        cur.execute(
            "DELETE FROM analytics_question_log "
            "WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '%s days';" % int(RETENCION_DIAS)
        )
        cur.execute("""
            INSERT INTO analytics_question_log (pregunta, resultado, detalle, metrica, portfolio_id)
            VALUES (%s, %s, %s, %s, %s);
        """, ((pregunta or "")[:1000], resultado, (detalle or "")[:1000], metrica, portfolio_id))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"⚠️ [ANALYTICS LOG] No se pudo registrar la pregunta (la respuesta sale igual): {e}")
        try:
            if conn is not None:
                conn.rollback()
        except Exception:
            pass
        return False
    finally:
        if propia:
            _devolver(conn)


def preguntas_recientes(limit: int = 100, conn=None) -> List[Dict[str, Any]]:
    """Las últimas preguntas sin responder (para revisar y mejorar el catálogo)."""
    propia = conn is None
    if propia:
        conn = _conn_del_pool()
        if conn is None:
            return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, pregunta, resultado, detalle, metrica, portfolio_id, created_at
              FROM analytics_question_log
             ORDER BY id DESC
             LIMIT %s;
        """, (int(limit),))
        filas = cur.fetchall()
        cur.close()
        return [{
            "id": f[0], "pregunta": f[1], "resultado": f[2], "detalle": f[3],
            "metrica": f[4], "portfolio_id": f[5],
            "fecha": str(f[6]) if f[6] else None,
        } for f in filas]
    finally:
        if propia:
            _devolver(conn)
