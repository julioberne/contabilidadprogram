# -*- coding: utf-8 -*-
"""saldos_foto.py — Versión del panel y fotos de saldo (estándar de consultas, H7).

Panel por versión (H7.1): `panel_version` sube con cada cambio (triggers de
scripts/migrate_panel_h7.py). El navegador pregunta la versión cada 60 s y solo
recarga el panel si cambió: 10 pestañas sin cambios = 10 lecturas de una fila,
no 10 recorridos de todas las transacciones.

Fotos de saldo (H7.2): `saldos_foto` (cuenta → movimiento acumulado) y
`kpi_foto` (empresa → ingresos/gastos) hasta un corte; el panel suma foto + lo
posterior al corte (dashboard_query.armar_snapshot_sql("tabla")).
  · El corte deja fuera lo creado en los últimos 10 minutos: un movimiento que
    tomó su id antes pero confirmó después cae siempre "después del corte".
  · Los triggers marcan la foto `sucia` (y suben `cambios`) si se edita, borra o
    inserta algo con id ≤ corte, si una cuenta cambia de moneda o se borra. Una
    foto sucia no se usa: el panel calcula completo hasta la próxima.
  · La toma va en dos tiempos: (1) se publica el corte nuevo como sucio; (2) se
    calcula y solo se marca limpia si `cambios` no se movió entretanto.
Todo es solo lectura salvo tomar_foto (tablas propias) y descuadres → bitácora.
Sin la migración, todo responde "no hay versión / no hay foto" y el panel sigue
como antes.
"""
import os
from typing import Any, Dict, List, Optional, Tuple

from fin_sys_core.db_pool import get_conn, put_conn

MINUTOS_MARGEN = 10                  # lo más nuevo que esto no entra en la foto
FOTO_VIEJA_H = 24                    # una foto limpia se renueva cada día


def fotos_activas() -> bool:
    """PANEL_FOTOS=0 apaga el uso de las fotos (el panel calcula completo)."""
    return os.getenv("PANEL_FOTOS", "1") != "0"


_SQL_ESTADO = """
SELECT (SELECT COALESCE(SUM(v.version), 0) FROM panel_version v
         WHERE %(portfolio)s::text IS NULL OR v.portfolio_id = 0
            OR v.portfolio_id = (SELECT id FROM portfolios WHERE name = %(portfolio)s)) AS version,
       (SELECT corte_id FROM saldos_foto_meta WHERE id = 1 AND NOT sucia) AS corte
"""


def estado_panel(cur, portfolio_name: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """(versión, corte de la foto vigente) con el cursor del llamador, dentro de
    un SAVEPOINT: sin la migración devuelve (None, None) sin abortar la transacción."""
    cur.execute("SAVEPOINT panel_h7")
    try:
        cur.execute(_SQL_ESTADO, {"portfolio": portfolio_name or None})
        fila = cur.fetchone()
        cur.execute("RELEASE SAVEPOINT panel_h7")
    except Exception:
        cur.execute("ROLLBACK TO SAVEPOINT panel_h7")
        return None, None
    version, corte = (fila[0], fila[1]) if not isinstance(fila, dict) else (fila["version"], fila["corte"])
    return (int(version) if version is not None else None), (int(corte) if corte is not None else None)


def version(portfolio_name: Optional[str]) -> Optional[int]:
    """Versión del panel de esa empresa (o del consolidado). None sin la migración."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        v, _ = estado_panel(cur, portfolio_name)
        cur.close()
        return v
    finally:
        put_conn(conn)


def _sql_foto() -> Tuple[str, str]:
    """(INSERT de saldos_foto, INSERT de kpi_foto) hasta %(corte)s, con las MISMAS
    expresiones que el panel (dashboard_query)."""
    from fin_sys_core.dashboard_query import _kpi_select, _mov_select, _tx_cte
    saldos = (f"WITH {_tx_cte('tx0', chr(10) + '    WHERE t.id <= %(corte)s')},\n"
              f"mov0 AS ({_mov_select('tx0')}\n)\n"
              "INSERT INTO saldos_foto (account_id, delta)\n"
              "SELECT account_id, SUM(delta) FROM mov0 GROUP BY account_id")
    kpi = ("INSERT INTO kpi_foto (portfolio_id, ingresos_usd, gastos_usd, ingresos_cop, gastos_cop, n)\n"
           "SELECT p.id, k.* FROM portfolios p CROSS JOIN LATERAL (\n"
           + _kpi_select(" AND t.id <= %(corte)s").replace(
               "(%(portfolio)s::text IS NULL OR p.name = %(portfolio)s)", "t.portfolio_id = p.id")
           .replace("FROM transactions t JOIN portfolios p ON p.id = t.portfolio_id", "FROM transactions t")
           + "\n) k")
    return saldos, kpi


def tomar_foto() -> Dict[str, Any]:
    """Saca la foto (dos tiempos). → {"corte", "cuentas", "empresas", "limpia"}."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        # 1) Corte nuevo publicado como SUCIO: desde ya, cualquier cambio con id ≤
        #    corte sube `cambios` (los triggers leen el corte confirmado).
        cur.execute("SELECT COALESCE(MAX(id), 0) FROM transactions "
                    "WHERE created_at < now() - make_interval(mins => %s)", (MINUTOS_MARGEN,))
        corte = int(cur.fetchone()[0])
        cur.execute("UPDATE saldos_foto_meta SET corte_id = %s, sucia = true WHERE id = 1 RETURNING cambios",
                    (corte,))
        cambios0 = int(cur.fetchone()[0])
        conn.commit()
        # 2) Cálculo y, solo si nada cambió entretanto, la foto queda limpia.
        saldos, kpi = _sql_foto()
        cur.execute("DELETE FROM saldos_foto")
        cur.execute(saldos, {"corte": corte})
        n_cuentas = cur.rowcount
        cur.execute("DELETE FROM kpi_foto")
        cur.execute(kpi, {"corte": corte})
        n_empresas = cur.rowcount
        cur.execute("UPDATE saldos_foto_meta SET sucia = false, tomada = now() "
                    "WHERE id = 1 AND corte_id = %s AND cambios = %s", (corte, cambios0))
        limpia = cur.rowcount == 1
        conn.commit()
        cur.close()
        return {"corte": corte, "cuentas": n_cuentas, "empresas": n_empresas, "limpia": limpia}
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def hay_que_tomar() -> bool:
    """¿La foto está sucia, nunca se tomó o tiene más de FOTO_VIEJA_H horas?"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT sucia OR tomada IS NULL OR tomada < now() - make_interval(hours => %s) "
                    "FROM saldos_foto_meta WHERE id = 1", (FOTO_VIEJA_H,))
        fila = cur.fetchone()
        cur.close()
        return bool(fila and fila[0])
    finally:
        put_conn(conn)


def descuadres(tolerancia: float = 0.01) -> List[Dict[str, Any]]:
    """Cuentas cuyo saldo actual no es saldo inicial + sus movimientos (el mismo
    cálculo del panel). Solo informa: NO corrige nada (reconciliar sigue siendo
    una decisión humana, POST /api/reconcile-balances)."""
    from fin_sys_core.dashboard_query import obtener_dashboard_snapshot
    cuentas = obtener_dashboard_snapshot(None, limit=0, incluir_txs=False)["accounts"]
    out = []
    for c in cuentas:
        actual = float(c.get("current_balance") or 0.0)
        esperado = float(c.get("expected_balance") or 0.0)
        if abs(actual - esperado) > tolerancia:
            out.append({"id": c["id"], "nombre": c.get("name"), "actual": round(actual, 2),
                        "esperado": round(esperado, 2), "diferencia": round(actual - esperado, 2)})
    return out


def avisar_descuadres() -> int:
    """Tarea diaria del worker: cada descuadre queda como aviso en la 📓 bitácora."""
    from bot_anomalias import registrar
    lista = descuadres()
    for d in lista:
        registrar("descuadre_cuenta",
                  f"La cuenta «{d['nombre']}» tiene {d['actual']:,.2f} y sus movimientos dan {d['esperado']:,.2f} "
                  f"(diferencia {d['diferencia']:,.2f})", datos=d)
    return len(lista)
