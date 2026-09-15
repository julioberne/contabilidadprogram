# -*- coding: utf-8 -*-
"""kernel_periods.py — Periodos contables y cierre (módulo Contadores, B1).

Tabla `accounting_periods`: una fila por (portafolio, año, mes) SOLO cuando
el periodo se cerró alguna vez. Ausencia de fila = ABIERTO. Reabrir no borra
la fila: la deja en estado ABIERTO como bitácora (quién y cuándo).

`assert_periodo_abierto(portfolio_id, fecha, conn=None)` es el único punto
de verdad: lo llaman registrar_asiento (kernel), el workflow del contador y
—en B5— la creación/edición/borrado de transacciones. Con `conn` externa se
usa esa conexión (misma transacción del llamador) y no se commitea aquí.
"""
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fin_sys_core.db_pool import get_conn, put_conn

logger = logging.getLogger("kernel.periods")

ESTADOS = ("CERRADO", "ABIERTO")


class PeriodoCerradoError(Exception):
    """El periodo (portafolio, año, mes) está cerrado: no se puede asentar."""


def _anio_mes(fecha) -> tuple:
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    if isinstance(fecha, date):
        return fecha.year, fecha.month
    s = str(fecha or "")[:10]
    partes = s.split("-")
    if len(partes) < 2:
        raise ValueError(f"Fecha inválida para periodo: {fecha!r}")
    return int(partes[0]), int(partes[1])


def _con_conexion(conn, fn):
    """Ejecuta fn(cur) con la conexión dada o con una del pool (sin commit
    para lecturas; el llamador commitea si escribe con su propia conexión)."""
    propia = conn is None
    if propia:
        conn = get_conn()
    try:
        cur = conn.cursor()
        try:
            return fn(cur)
        finally:
            cur.close()
    finally:
        if propia:
            put_conn(conn)


def init_accounting_periods_table() -> None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounting_periods (
                id SERIAL PRIMARY KEY,
                portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                anio SMALLINT NOT NULL,
                mes  SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
                estado VARCHAR(10) NOT NULL DEFAULT 'CERRADO',
                cerrado_por VARCHAR(64), cerrado_en TIMESTAMPTZ,
                reabierto_por VARCHAR(64), reabierto_en TIMESTAMPTZ,
                nota TEXT,
                UNIQUE (portfolio_id, anio, mes)
            );
        """)
        conn.commit()
        cur.close()
        print("✅ Kernel: tabla accounting_periods lista")
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Error creando accounting_periods: {e}")
    finally:
        put_conn(conn)


def periodo_esta_cerrado(portfolio_id: Optional[int], fecha, conn=None) -> bool:
    if portfolio_id is None:
        return False
    anio, mes = _anio_mes(fecha)

    def _q(cur):
        cur.execute("""
            SELECT cerrado_por, cerrado_en FROM accounting_periods
            WHERE portfolio_id = %s AND anio = %s AND mes = %s AND estado = 'CERRADO'
        """, (int(portfolio_id), anio, mes))
        return cur.fetchone()
    return _con_conexion(conn, _q) is not None


def assert_periodo_abierto(portfolio_id: Optional[int], fecha, conn=None) -> None:
    """Lanza PeriodoCerradoError si (portafolio, mes de `fecha`) está cerrado.
    portfolio_id None (asiento sin portafolio, p. ej. cartera) → no bloquea."""
    if portfolio_id is None:
        logger.debug("assert_periodo_abierto sin portfolio_id: no se verifica")
        return
    anio, mes = _anio_mes(fecha)

    def _q(cur):
        cur.execute("""
            SELECT cerrado_por, cerrado_en FROM accounting_periods
            WHERE portfolio_id = %s AND anio = %s AND mes = %s AND estado = 'CERRADO'
        """, (int(portfolio_id), anio, mes))
        return cur.fetchone()
    fila = _con_conexion(conn, _q)
    if fila:
        quien, cuando = fila
        detalle = f" (cerrado por {quien} el {str(cuando)[:10]})" if quien else ""
        raise PeriodoCerradoError(
            f"Periodo {anio}-{mes:02d} cerrado para el portafolio {portfolio_id}{detalle}. "
            f"Un administrador debe reabrirlo en el módulo Contadores."
        )


def assert_periodo_abierto_por_nombre(portfolio_name: Optional[str], fecha, conn=None) -> None:
    """Para quien solo conoce el nombre del portafolio (create_transaction)."""
    if not portfolio_name:
        return

    def _q(cur):
        cur.execute("SELECT id FROM portfolios WHERE name = %s", (portfolio_name,))
        r = cur.fetchone()
        return r[0] if r else None
    pid = _con_conexion(conn, _q)
    assert_periodo_abierto(pid, fecha, conn=conn)


def contar_borradores_periodo(portfolio_id: int, anio: int, mes: int, conn=None) -> int:
    def _q(cur):
        cur.execute("""
            SELECT COUNT(DISTINCT entry_group_id) FROM kernel_journal_entries
            WHERE portfolio_id = %s AND estado = 'BORRADOR'
              AND EXTRACT(YEAR FROM fecha) = %s AND EXTRACT(MONTH FROM fecha) = %s
        """, (int(portfolio_id), anio, mes))
        return int(cur.fetchone()[0])
    return _con_conexion(conn, _q)


def listar_periodos(portfolio_id: int, anio: int) -> List[Dict[str, Any]]:
    """12 meses del año con estado derivado y conteo de asientos por estado."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT mes, estado, cerrado_por, cerrado_en, reabierto_por, reabierto_en, nota
            FROM accounting_periods WHERE portfolio_id = %s AND anio = %s
        """, (int(portfolio_id), anio))
        filas = {r[0]: r for r in cur.fetchall()}
        cur.execute("""
            SELECT EXTRACT(MONTH FROM fecha)::int AS mes, estado, COUNT(DISTINCT entry_group_id)
            FROM kernel_journal_entries
            WHERE portfolio_id = %s AND EXTRACT(YEAR FROM fecha) = %s
            GROUP BY 1, 2
        """, (int(portfolio_id), anio))
        conteos: Dict[int, Dict[str, int]] = {}
        for mes, estado, n in cur.fetchall():
            conteos.setdefault(int(mes), {})[estado] = int(n)
        cur.close()
    finally:
        put_conn(conn)
    salida = []
    for mes in range(1, 13):
        f = filas.get(mes)
        salida.append({
            "anio": anio, "mes": mes,
            "estado": (f[1] if f else "ABIERTO"),
            "cerrado_por": f[2] if f else None,
            "cerrado_en": str(f[3]) if f and f[3] else None,
            "reabierto_por": f[4] if f else None,
            "reabierto_en": str(f[5]) if f and f[5] else None,
            "nota": f[6] if f else None,
            "asientos": conteos.get(mes, {}),
        })
    return salida


def cerrar_periodo(portfolio_id: int, anio: int, mes: int, usuario: str,
                   nota: Optional[str] = None) -> Dict[str, Any]:
    """Cierra el mes. Falla (ValueError con conteo) si quedan BORRADORES."""
    if not (1 <= int(mes) <= 12):
        raise ValueError("Mes inválido")
    conn = get_conn()
    try:
        borradores = contar_borradores_periodo(portfolio_id, anio, mes, conn=conn)
        if borradores:
            raise ValueError(
                f"Hay {borradores} asiento(s) en BORRADOR en {anio}-{int(mes):02d}: "
                f"contabilízalos o recházalos antes de cerrar.")
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO accounting_periods (portfolio_id, anio, mes, estado, cerrado_por, cerrado_en, nota)
            VALUES (%s, %s, %s, 'CERRADO', %s, NOW(), %s)
            ON CONFLICT (portfolio_id, anio, mes) DO UPDATE
               SET estado = 'CERRADO', cerrado_por = EXCLUDED.cerrado_por,
                   cerrado_en = NOW(), nota = COALESCE(EXCLUDED.nota, accounting_periods.nota)
            RETURNING id
        """, (int(portfolio_id), int(anio), int(mes), usuario, nota))
        pid = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return {"status": "ok", "id": pid, "estado": "CERRADO",
                "anio": int(anio), "mes": int(mes), "portfolio_id": int(portfolio_id)}
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def reabrir_periodo(portfolio_id: int, anio: int, mes: int, usuario: str,
                    motivo: Optional[str] = None) -> Dict[str, Any]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE accounting_periods
               SET estado = 'ABIERTO', reabierto_por = %s, reabierto_en = NOW(),
                   nota = COALESCE(%s, nota)
             WHERE portfolio_id = %s AND anio = %s AND mes = %s
            RETURNING id
        """, (usuario, motivo, int(portfolio_id), int(anio), int(mes)))
        r = cur.fetchone()
        conn.commit()
        cur.close()
        if not r:
            return {"status": "ya_abierto", "anio": int(anio), "mes": int(mes)}
        return {"status": "ok", "id": r[0], "estado": "ABIERTO", "anio": int(anio), "mes": int(mes)}
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)
