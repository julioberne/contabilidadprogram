# -*- coding: utf-8 -*-
"""Transacciones acotadas (estándar de consultas, hito H6 — reglas B1/B2).

`database_driver.obtener_transacciones` sin portafolio trae TODAS las transacciones
de TODAS las empresas; varios llamadores las traían para quedarse con unas pocas
(el compendio con las elegidas, la exportación con una empresa y un período).
Aquí el filtro va a la BD y las filas salen IGUALES: mismas columnas
(TX_SELECT_LIST, copia literal de obtener_transacciones), mismas uniones
(TX_FROM) y mismo orden (fecha y id descendentes). Por eso los llamadores
siguen pasando el resultado por export_xlsx._sin_duplicados, como antes (el
LEFT JOIN con assets puede repetir filas).

Sin `database_driver.py` (🔴): consultas nuevas en un módulo nuevo.
"""
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Tuple

from psycopg2.extras import RealDictCursor

from fin_sys_core.dashboard_query import TX_FROM, TX_SELECT_LIST
from fin_sys_core.db_pool import get_conn, put_conn

MAX_IDS = 20000           # tope de ids por consulta (una exportación "transacciones")
_ORDEN = " ORDER BY t.transaction_date DESC, t.id DESC"


def _ids(valores: Iterable[Any]) -> List[int]:
    out = sorted({int(v) for v in valores})
    if len(out) > MAX_IDS:
        raise ValueError(f"Máximo {MAX_IDS} transacciones por pedido.")
    return out


def armar_por_ids(ids: Iterable[Any]) -> Tuple[str, Dict[str, Any]]:
    """(sql, params) de las transacciones con esos ids."""
    return (f"SELECT {TX_SELECT_LIST} {TX_FROM} WHERE t.id = ANY(%(ids)s){_ORDEN}",
            {"ids": _ids(ids)})


def armar_por_filtro(empresas: Optional[Iterable[str]] = None, desde: Optional[date] = None,
                     hasta: Optional[date] = None) -> Tuple[str, Dict[str, Any]]:
    """(sql, params) por nombre de empresa (vacío = todas) y fechas inclusivas.
    Igual que el filtro en Python de antes: la fecha se compara como día y las
    filas sin fecha quedan fuera cuando hay rango."""
    cond, p = [], {}
    nombres = sorted({str(e) for e in (empresas or []) if e})
    if nombres:
        cond.append("p.name = ANY(%(empresas)s)")
        p["empresas"] = nombres
    if desde is not None:
        cond.append("t.transaction_date::date >= %(desde)s")
        p["desde"] = desde
    if hasta is not None:
        cond.append("t.transaction_date::date <= %(hasta)s")
        p["hasta"] = hasta
    where = f" WHERE {' AND '.join(cond)}" if cond else ""
    return f"SELECT {TX_SELECT_LIST} {TX_FROM}{where}{_ORDEN}", p


def _leer(sql: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        put_conn(conn)


def por_ids(ids: Iterable[Any]) -> List[Dict[str, Any]]:
    """Solo las transacciones pedidas (compendio, exportación por selección)."""
    lista = list(ids or [])
    if not lista:
        return []
    return _leer(*armar_por_ids(lista))


def por_filtro(empresas: Optional[Iterable[str]] = None, desde: Optional[date] = None,
               hasta: Optional[date] = None) -> List[Dict[str, Any]]:
    """Las de esas empresas (vacío = todas) entre `desde` y `hasta` (exportación por período)."""
    return _leer(*armar_por_filtro(empresas, desde, hasta))
