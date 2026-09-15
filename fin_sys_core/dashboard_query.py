# -*- coding: utf-8 -*-
"""dashboard_query.py — Snapshot del dashboard en UN solo viaje a la BD.

Plan cimientos A2 (2026-09-15). Antes, GET /api/dashboard-data hacía 9
sentencias en 6 préstamos de conexión (portafolios, COUNT, TODAS las
transacciones con 5 LEFT JOIN, cuentas, vínculos, 2 de entidades, perfil,
COA) y recalculaba en Python el delta por cuenta con todas las TXs. A ~45 ms
por viaje VPS↔Supabase eran ~0.45 s de servidor con 25 transacciones, y
crecía linealmente con las TXs.

Aquí todo viaja en UNA sentencia con CTEs que devuelve una fila de
columnas JSON. La matemática replica EXACTAMENTE:
  - routers/dashboard_data.py::_agregar_tx_delta   (delta por cuenta)
  - routers/profile_accounts.py::anotar_portafolio_cuentas (entity_links)
  - routers/profile_accounts.py::filtrar_cuentas_por_portafolio (visibilidad,
    incluida la regla anti-hueco)
  - fin_sys_core/ledger_math.py::calculate_caja_viva (las 4 sumas que
    necesita; el resto lo sigue haciendo la función original vía
    caja_viva_desde_agregados)
  - database_driver.obtener_transacciones (misma lista de columnas, ahora
    paginada en SQL)
scripts/verify_dashboard_parity.py compara ambas rutas campo a campo.

Zero-Impact: database_driver.py y ledger_math.py no se tocan.
"""
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor

from fin_sys_core.db_pool import get_conn, put_conn

# ── Lista de columnas y FROM de obtener_transacciones (copia literal) ────────
TX_SELECT_LIST = """
            t.id, t.type, t.amount, t.concept, t.transaction_date, t.payment_method, t.category,
            t.tax_iva_amount, t.tax_gmf_amount, t.net_value, t.geo_maps_link, t.evidence_file_path,
            t.account_id, t.dest_account_id, t.trm, t.transaction_currency, t.is_recurring,
            t.recurrence_interval, t.recurrence_days, t.recurrence_max_reps, t.recurrence_start_date, t.recurrence_end_date,
            t.tags, t.note,
            (SELECT COALESCE(json_agg(ev.file_path ORDER BY ev.id), '[]'::json)
               FROM transaction_evidences ev
              WHERE ev.transaction_id = t.id) AS evidences,
            p.name as portfolio_name, p.industry_type as portfolio_industry, p.sub_industry_type as portfolio_sub_industry,
            tp.identification_type, tp.identification_number, tp.name as third_party_name,
            tp.id as third_party_id, tp.email as tp_email, tp.phone as tp_phone, tp.address as tp_address,
            a.name as account_name,
            da.name as dest_account_name,
            cxc.type as cxc_type, cxc.due_date as cxc_due_date, cxc.term as cxc_term, cxc.status as cxc_status,
            ast.name as asset_name, ast.custom_tag as asset_tag, ast.is_passive_income_generator as asset_is_passive, ast.recurrence_amount as asset_recurrence_amount
"""
TX_FROM = """
        FROM transactions t
        JOIN portfolios p ON t.portfolio_id = p.id
        LEFT JOIN third_parties tp ON t.third_party_id = tp.id
        LEFT JOIN user_accounts a ON t.account_id = a.id
        LEFT JOIN user_accounts da ON t.dest_account_id = da.id
        LEFT JOIN cxp_cxc_ledger cxc ON t.id = cxc.transaction_id
        LEFT JOIN assets ast ON t.portfolio_id = ast.portfolio_id AND t.transaction_date = ast.purchase_date AND t.amount = ast.purchase_value
"""


def _conv(valor: str, desde: str, hacia: str, trm: str) -> str:
    """Réplica SQL de _agregar_tx_delta._conv (comparaciones con `=`: si la
    moneda de la cuenta es NULL ninguna rama aplica y se devuelve el valor,
    igual que en Python)."""
    return (f"CASE WHEN {desde} = {hacia} THEN {valor} "
            f"WHEN {desde} = 'USD' AND {hacia} = 'COP' THEN {valor} * {trm} "
            f"WHEN {desde} = 'COP' AND {hacia} = 'USD' THEN "
            f"(CASE WHEN {trm} > 0 THEN {valor} / {trm} ELSE 0 END) "
            f"ELSE {valor} END")


_SNAPSHOT_SQL = f"""
WITH pf AS (
    SELECT id, name FROM portfolios WHERE name = %(portfolio)s
),
tx AS (
    -- Normalización idéntica al Python: trm `or 1.0`, moneda `or 'COP'`,
    -- net_value / amount `or 0`.
    SELECT t.id, upper(t.type) AS tipo, t.account_id, t.dest_account_id,
           CASE WHEN COALESCE(t.trm, 0) = 0 THEN 1.0::float8 ELSE t.trm::float8 END AS trm,
           COALESCE(NULLIF(t.transaction_currency, ''), 'COP') AS cur,
           COALESCE(t.net_value, 0)::float8 AS net,
           COALESCE(t.amount, 0)::float8 AS amt
    FROM transactions t
),
mov AS (
    -- Como cuenta ORIGEN (solo si la cuenta existe: por_id.get(account_id))
    SELECT a.id AS account_id,
           CASE tx.tipo
             WHEN 'INGRESO'       THEN  {_conv('tx.net', 'tx.cur', 'a.currency', 'tx.trm')}
             WHEN 'GASTO'         THEN -({_conv('tx.net', 'tx.cur', 'a.currency', 'tx.trm')})
             WHEN 'TRANSFERENCIA' THEN -tx.amt
             ELSE 0
           END AS delta
    FROM tx JOIN user_accounts a ON a.id = tx.account_id
    UNION ALL
    -- Como cuenta DESTINO (solo si origen Y destino existen)
    SELECT d.id, {_conv('tx.amt', 'a.currency', 'd.currency', 'tx.trm')}
    FROM tx
    JOIN user_accounts a ON a.id = tx.account_id
    JOIN user_accounts d ON d.id = tx.dest_account_id
    WHERE tx.tipo = 'TRANSFERENCIA'
),
deltas AS (
    SELECT account_id, SUM(delta) AS tx_delta FROM mov GROUP BY account_id
),
links AS (
    SELECT l.account_id,
           json_agg(json_build_object('id', e.id, 'name', e.name, 'type', e.type)
                    ORDER BY e.name) AS entity_links,
           bool_or(e.portfolio_id = (SELECT id FROM pf)) AS en_portafolio,
           bool_and(e.portfolio_id IS NULL)              AS sin_presupuesto
    FROM account_entity_links l JOIN entities e ON e.id = l.entity_id
    GROUP BY l.account_id
),
cuentas AS (
    SELECT a.id, a.name, a.type, a.currency, a.initial_balance, a.current_balance,
           COALESCE(lk.entity_links, '[]'::json) AS entity_links,
           COALESCE(d.tx_delta, 0)::float8 AS tx_delta_raw
    FROM user_accounts a
    LEFT JOIN deltas d ON d.account_id = a.id
    LEFT JOIN links lk ON lk.account_id = a.id
    WHERE %(portfolio)s::text IS NULL
       OR lk.account_id IS NULL
       OR COALESCE(lk.en_portafolio, false)
       OR COALESCE(lk.sin_presupuesto, false)
),
tx_page AS (
    SELECT {TX_SELECT_LIST}
    {TX_FROM}
    WHERE (%(portfolio)s::text IS NULL OR p.name = %(portfolio)s)
    ORDER BY t.transaction_date DESC, t.id DESC
    LIMIT %(limit)s OFFSET %(offset)s
),
kpi AS (
    -- Las 4 sumas de calculate_caja_viva sobre las TXs del portafolio
    -- (TRANSFERENCIA se ignora; moneda 'USD' exacta, todo lo demás es COP).
    SELECT
      COALESCE(SUM(CASE WHEN upper(t.type) = 'INGRESO' AND t.transaction_currency = 'USD' THEN COALESCE(t.net_value, 0) END), 0)::float8 AS ingresos_usd,
      COALESCE(SUM(CASE WHEN upper(t.type) = 'GASTO'   AND t.transaction_currency = 'USD' THEN COALESCE(t.net_value, 0) END), 0)::float8 AS gastos_usd,
      COALESCE(SUM(CASE WHEN upper(t.type) = 'INGRESO' AND t.transaction_currency IS DISTINCT FROM 'USD' THEN COALESCE(t.net_value, 0) END), 0)::float8 AS ingresos_cop,
      COALESCE(SUM(CASE WHEN upper(t.type) = 'GASTO'   AND t.transaction_currency IS DISTINCT FROM 'USD' THEN COALESCE(t.net_value, 0) END), 0)::float8 AS gastos_cop,
      COUNT(*)::int AS total
    FROM transactions t JOIN portfolios p ON p.id = t.portfolio_id
    WHERE (%(portfolio)s::text IS NULL OR p.name = %(portfolio)s)
)
SELECT
  (SELECT COALESCE(json_agg(row_to_json(x) ORDER BY x.id), '[]'::json)
     FROM (SELECT id, name, industry_type, sub_industry_type FROM portfolios) x)     AS portfolios,
  (SELECT COALESCE(json_agg(row_to_json(c) ORDER BY c.id), '[]'::json) FROM cuentas c) AS accounts,
  (SELECT COALESCE(json_agg(row_to_json(tp) ORDER BY tp.transaction_date DESC, tp.id DESC), '[]'::json)
     FROM tx_page tp)                                                                  AS transactions,
  (SELECT row_to_json(k) FROM kpi k)                                                   AS kpi,
  (SELECT row_to_json(u) FROM (SELECT name, email, role, avatar_style
                                 FROM user_profiles ORDER BY id ASC LIMIT 1) u)      AS profile,
  (SELECT COALESCE(json_agg(row_to_json(ca) ORDER BY ca.code), '[]'::json)
     FROM (SELECT id, code, name, account_type, parent_id, is_group, description
             FROM chart_of_accounts
            WHERE portfolio_id = COALESCE((SELECT id FROM pf), (SELECT MIN(id) FROM portfolios))) ca) AS coa_rows;
"""


def _arbol_coa(filas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Mismo árbol que database_driver.obtener_coa_tree / schemas._build_coa_tree."""
    por_id = {f["id"]: {**f, "children": []} for f in filas}
    raiz = []
    for f in filas:
        nodo = por_id[f["id"]]
        padre = f.get("parent_id")
        if padre and padre in por_id:
            por_id[padre]["children"].append(nodo)
        else:
            raiz.append(nodo)
    return raiz


def _redondear_cuentas(cuentas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """tx_delta / expected_balance con el MISMO round() de Python que el legacy."""
    for c in cuentas:
        delta = float(c.pop("tx_delta_raw", 0.0) or 0.0)
        c["tx_delta"] = round(delta, 2)
        c["expected_balance"] = round(float(c.get("initial_balance") or 0.0) + delta, 2)
    return cuentas


def obtener_dashboard_snapshot(portfolio_name: Optional[str], limit: int = 50,
                               offset: int = 0, incluir_txs: bool = True) -> Dict[str, Any]:
    """Un viaje. Devuelve:
      portfolios, accounts (filtradas por portafolio, con entity_links,
      tx_delta y expected_balance), transactions (página), total_tx_count,
      kpi {ingresos_cop, gastos_cop, ingresos_usd, gastos_usd}, profile
      (dict o None), coa_rows (planas) y coa (árbol)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(_SNAPSHOT_SQL, {
            "portfolio": portfolio_name or None,
            "limit": int(limit) if incluir_txs else 0,
            "offset": int(offset),
        })
        portfolios, accounts, transactions, kpi, profile, coa_rows = cur.fetchone()
        cur.close()
    finally:
        put_conn(conn)

    kpi = kpi or {"ingresos_cop": 0.0, "gastos_cop": 0.0,
                  "ingresos_usd": 0.0, "gastos_usd": 0.0, "total": 0}
    return {
        "portfolios": portfolios or [],
        "accounts": _redondear_cuentas(accounts or []),
        "transactions": transactions or [],
        "total_tx_count": int(kpi.get("total") or 0),
        "kpi": kpi,
        "profile": profile,
        "coa_rows": coa_rows or [],
        "coa": _arbol_coa(coa_rows or []),
    }


def caja_viva_desde_agregados(kpi: Dict[str, Any], accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """calculate_caja_viva solo necesita de las TXs cuatro sumas; el resto
    (patrimonio por cuentas, alertas, campos legacy) lo hace ella misma.
    Cuatro TXs sintéticas → cero duplicación de reglas."""
    from fin_sys_core.ledger_math import calculate_caja_viva
    sinteticas = [
        {"type": "INGRESO", "transaction_currency": "COP", "net_value": kpi.get("ingresos_cop", 0.0)},
        {"type": "GASTO",   "transaction_currency": "COP", "net_value": kpi.get("gastos_cop", 0.0)},
        {"type": "INGRESO", "transaction_currency": "USD", "net_value": kpi.get("ingresos_usd", 0.0)},
        {"type": "GASTO",   "transaction_currency": "USD", "net_value": kpi.get("gastos_usd", 0.0)},
    ]
    return calculate_caja_viva(sinteticas, accounts)


def obtener_cuentas_con_delta(portfolio_name: Optional[str]) -> List[Dict[str, Any]]:
    """Equivale a anotar_portafolio_cuentas + _agregar_tx_delta +
    filtrar_cuentas_por_portafolio (GET /api/accounts) en un viaje."""
    return obtener_dashboard_snapshot(portfolio_name, limit=0, incluir_txs=False)["accounts"]


def obtener_transaccion(tx_id: int) -> Optional[Dict[str, Any]]:
    """Una transacción con la MISMA forma que las filas de
    dashboard-data.transactions (para que el frontend la inserte sin refetch)."""
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(f"SELECT {TX_SELECT_LIST} {TX_FROM} WHERE t.id = %s;", (tx_id,))
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    finally:
        put_conn(conn)
