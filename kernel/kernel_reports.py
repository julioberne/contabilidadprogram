# -*- coding: utf-8 -*-
"""kernel_reports.py — Reportes contables desde el libro diario (B4).

SOLO asientos "en libros" (CONTABILIZADO + ANULADO, cuyo espejo los cancela)
del portafolio indicado (None = consolidado). Cada reporte es UNA consulta.

  libro_mayor(portfolio_id, cuenta, desde, hasta)
  balance_prueba(portfolio_id, desde, hasta)
  balance_general(portfolio_id, hasta)
  estado_resultados(portfolio_id, desde, hasta)
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor

from fin_sys_core.db_pool import get_conn, put_conn

EN_LIBROS = "estado IN ('CONTABILIZADO', 'ANULADO')"


def _f(v):
    if isinstance(v, Decimal):
        return float(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def _pf(portfolio_id: Optional[int]):
    return ("AND portfolio_id = %(pid)s", {"pid": int(portfolio_id)}) if portfolio_id is not None else ("", {})


def libro_mayor(portfolio_id: Optional[int], cuenta_codigo: str,
                fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None) -> Dict[str, Any]:
    pf_sql, params = _pf(portfolio_id)
    params.update({"cta": cuenta_codigo, "desde": fecha_desde, "hasta": fecha_hasta})
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(f"""
            SELECT COALESCE(SUM(debito) - SUM(credito), 0) AS saldo_inicial,
                   MAX(cuenta_nombre) AS cuenta_nombre, MAX(cuenta_tipo) AS cuenta_tipo
            FROM kernel_journal_entries
            WHERE cuenta_codigo = %(cta)s AND {EN_LIBROS} {pf_sql}
              AND (%(desde)s::date IS NULL OR fecha < %(desde)s::date)
        """, params)
        ini = cur.fetchone()
        cur.execute(f"""
            SELECT id, fecha, entry_group_id, referencia, descripcion, debito, credito, estado,
                   cuenta_nombre, cuenta_tipo
            FROM kernel_journal_entries
            WHERE cuenta_codigo = %(cta)s AND {EN_LIBROS} {pf_sql}
              AND (%(desde)s::date IS NULL OR fecha >= %(desde)s::date)
              AND (%(hasta)s::date IS NULL OR fecha <= %(hasta)s::date)
            ORDER BY fecha, id
        """, params)
        filas = [dict(r) for r in cur.fetchall()]
        cur.close()
    finally:
        put_conn(conn)
    saldo = Decimal(ini["saldo_inicial"] or 0)
    movs, td, tc = [], Decimal(0), Decimal(0)
    for r in filas:
        saldo += Decimal(r["debito"] or 0) - Decimal(r["credito"] or 0)
        td += Decimal(r["debito"] or 0); tc += Decimal(r["credito"] or 0)
        movs.append({**{k: _f(v) for k, v in r.items()}, "saldo_acumulado": float(saldo)})
    nombre = ini["cuenta_nombre"] or (filas[0]["cuenta_nombre"] if filas else "")
    tipo = ini["cuenta_tipo"] or (filas[0]["cuenta_tipo"] if filas else "")
    return {"cuenta_codigo": cuenta_codigo, "cuenta_nombre": nombre, "cuenta_tipo": tipo,
            "saldo_inicial": float(ini["saldo_inicial"] or 0), "movimientos": movs,
            "total_debito": float(td), "total_credito": float(tc), "saldo_final": float(saldo)}


def balance_prueba(portfolio_id: Optional[int], fecha_desde: Optional[str] = None,
                   fecha_hasta: Optional[str] = None) -> Dict[str, Any]:
    pf_sql, params = _pf(portfolio_id)
    params.update({"desde": fecha_desde, "hasta": fecha_hasta})
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(f"""
            SELECT cuenta_codigo, MAX(cuenta_nombre) AS cuenta_nombre, MAX(cuenta_tipo) AS cuenta_tipo,
                   COALESCE(SUM(CASE WHEN %(desde)s::date IS NOT NULL AND fecha < %(desde)s::date THEN debito - credito END), 0) AS saldo_inicial,
                   COALESCE(SUM(CASE WHEN (%(desde)s::date IS NULL OR fecha >= %(desde)s::date)
                                      AND (%(hasta)s::date IS NULL OR fecha <= %(hasta)s::date) THEN debito END), 0) AS mov_debito,
                   COALESCE(SUM(CASE WHEN (%(desde)s::date IS NULL OR fecha >= %(desde)s::date)
                                      AND (%(hasta)s::date IS NULL OR fecha <= %(hasta)s::date) THEN credito END), 0) AS mov_credito
            FROM kernel_journal_entries
            WHERE {EN_LIBROS} {pf_sql}
              AND (%(hasta)s::date IS NULL OR fecha <= %(hasta)s::date)
            GROUP BY cuenta_codigo
            ORDER BY cuenta_codigo
        """, params)
        filas = [dict(r) for r in cur.fetchall()]
        cur.close()
    finally:
        put_conn(conn)
    cuentas, tot = [], {"saldo_inicial_db": 0, "saldo_inicial_cr": 0, "mov_debito": 0, "mov_credito": 0,
                        "saldo_final_db": 0, "saldo_final_cr": 0}
    for r in filas:
        ini = Decimal(r["saldo_inicial"]); db = Decimal(r["mov_debito"]); cr = Decimal(r["mov_credito"])
        fin = ini + db - cr
        c = {"cuenta_codigo": r["cuenta_codigo"], "cuenta_nombre": r["cuenta_nombre"], "cuenta_tipo": r["cuenta_tipo"],
             "saldo_inicial_db": float(max(ini, 0)), "saldo_inicial_cr": float(max(-ini, 0)),
             "mov_debito": float(db), "mov_credito": float(cr),
             "saldo_final_db": float(max(fin, 0)), "saldo_final_cr": float(max(-fin, 0))}
        if any(abs(v) > 0 for k, v in c.items() if isinstance(v, float)):
            cuentas.append(c)
            for k in tot:
                tot[k] += c[k]
    tot = {k: round(v, 2) for k, v in tot.items()}
    cuadra = (abs(tot["mov_debito"] - tot["mov_credito"]) < 0.01
              and abs(tot["saldo_final_db"] - tot["saldo_final_cr"]) < 0.01)
    return {"cuentas": cuentas, "totales": tot, "cuadra": cuadra,
            "fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta}


def _saldos_por_cuenta(portfolio_id, fecha_desde, fecha_hasta) -> List[Dict[str, Any]]:
    pf_sql, params = _pf(portfolio_id)
    params.update({"desde": fecha_desde, "hasta": fecha_hasta})
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(f"""
            SELECT cuenta_codigo, MAX(cuenta_nombre) AS cuenta_nombre, MAX(cuenta_tipo) AS cuenta_tipo,
                   SUM(debito) - SUM(credito) AS saldo
            FROM kernel_journal_entries
            WHERE {EN_LIBROS} {pf_sql}
              AND (%(desde)s::date IS NULL OR fecha >= %(desde)s::date)
              AND (%(hasta)s::date IS NULL OR fecha <= %(hasta)s::date)
            GROUP BY cuenta_codigo ORDER BY cuenta_codigo
        """, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        put_conn(conn)


def _agrupar(filas, tipos, signo):
    """Cuentas de esos tipos con saldo (con signo natural) y subtotales por
    grupo (2 primeros dígitos del PUC)."""
    cuentas, grupos, total = [], {}, Decimal(0)
    for r in filas:
        if (r["cuenta_tipo"] or "").upper() not in tipos:
            continue
        saldo = Decimal(r["saldo"] or 0) * signo
        if saldo == 0:
            continue
        cuentas.append({"cuenta_codigo": r["cuenta_codigo"], "cuenta_nombre": r["cuenta_nombre"],
                        "cuenta_tipo": r["cuenta_tipo"], "saldo": float(saldo)})
        g = str(r["cuenta_codigo"])[:2]
        grupos[g] = grupos.get(g, Decimal(0)) + saldo
        total += saldo
    return {"cuentas": cuentas, "grupos": {k: float(v) for k, v in sorted(grupos.items())}, "total": float(total)}


def estado_resultados(portfolio_id: Optional[int], fecha_desde: Optional[str] = None,
                      fecha_hasta: Optional[str] = None) -> Dict[str, Any]:
    filas = _saldos_por_cuenta(portfolio_id, fecha_desde, fecha_hasta)
    ingresos = _agrupar(filas, ("INGRESO",), -1)     # saldo acreedor → positivo
    gastos = _agrupar(filas, ("GASTO",), 1)          # saldo deudor → positivo
    return {"ingresos": ingresos, "gastos": gastos,
            "utilidad_neta": round(ingresos["total"] - gastos["total"], 2),
            "fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta}


def balance_general(portfolio_id: Optional[int], fecha_hasta: Optional[str] = None) -> Dict[str, Any]:
    filas = _saldos_por_cuenta(portfolio_id, None, fecha_hasta)
    activos = _agrupar(filas, ("ACTIVO",), 1)
    pasivos = _agrupar(filas, ("PASIVO",), -1)
    patrimonio = _agrupar(filas, ("PATRIMONIO",), -1)
    ingresos = _agrupar(filas, ("INGRESO",), -1)["total"]
    gastos = _agrupar(filas, ("GASTO",), 1)["total"]
    utilidad = round(ingresos - gastos, 2)
    izq = activos["total"]
    der = pasivos["total"] + patrimonio["total"] + utilidad
    return {"activos": activos, "pasivos": pasivos, "patrimonio": patrimonio,
            "utilidad_ejercicio": utilidad, "total_pasivo_patrimonio": round(der, 2),
            "ecuacion_contable": abs(izq - der) < 0.01, "diferencia": round(izq - der, 2),
            "fecha_hasta": fecha_hasta}
