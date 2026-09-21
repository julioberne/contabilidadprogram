# -*- coding: utf-8 -*-
"""
FIN-SYS OS — Análisis Inteligente (B0): catálogo whitelisted de métricas
------------------------------------------------------------------------
Archivo NUEVO (Zero-Impact). El ÚNICO lugar del que pueden nacer cifras
para el frente de análisis: la IA (B3) solo ELIGE una métrica de este
menú y sus parámetros; el SQL es auditable y la empresa (portfolio_id)
la inyecta SIEMPRE el backend — jamás el LLM (criterios inmutables 1-2).

Cada métrica devuelve:
  {
    "metrica": id, "etiqueta": ..., "unidad": "COP",
    "valor":   número principal (si aplica),
    "valores": lista/dict con el detalle (si aplica),
    "origen":  {"n_txs": N, "desde": "YYYY-MM-DD", "hasta": "YYYY-MM-DD",
                "sello": "según N TXs de <rango>", ...},
    "nota":    aclaración honesta (opcional — criterio inmutable 4),
  }

Convenciones de cifra (misma verdad que el dashboard, dashboard_query.py):
  - INGRESO/GASTO por upper(t.type); la cifra es SUM(net_value).
  - Los montos en USD NO se suman al COP: se cuentan aparte y se avisa
    en origen.usd_excluidas (jamás mezclar monedas en silencio).
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Any, Callable, Dict, List, Optional

# Monedas: todo lo que no sea USD se trata como COP (mismo criterio que el
# KPI del dashboard: transaction_currency IS DISTINCT FROM 'USD').
_ES_COP = "(t.transaction_currency IS DISTINCT FROM 'USD')"

_RE_MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _hoy() -> _dt.date:
    """Fecha de hoy (función propia para poder congelarla en tests)."""
    return _dt.date.today()


def _mes_actual() -> str:
    return _hoy().strftime("%Y-%m")


def _rango_mes(mes: str) -> tuple[_dt.date, _dt.date]:
    """['2026-09'] → (2026-09-01, 2026-09-30)."""
    anio, m = int(mes[:4]), int(mes[5:7])
    ini = _dt.date(anio, m, 1)
    fin = (_dt.date(anio + 1, 1, 1) if m == 12 else _dt.date(anio, m + 1, 1)) - _dt.timedelta(days=1)
    return ini, fin


def _mes_anterior(mes: str) -> str:
    anio, m = int(mes[:4]), int(mes[5:7])
    return f"{anio - 1}-12" if m == 1 else f"{anio}-{m - 1:02d}"


def _f(x: Any) -> float:
    """Decimal/None → float honesto."""
    return float(x) if x is not None else 0.0


def _sello(n_txs: int, desde: Any = None, hasta: Any = None, fuente: str = "TXs") -> Dict[str, Any]:
    """Sello de origen (criterio inmutable 3)."""
    d = str(desde) if desde else None
    h = str(hasta) if hasta else None
    if n_txs == 0:
        texto = f"sin {fuente} en el rango consultado"
    elif d and h and d != h:
        texto = f"según {n_txs} {fuente} de {d} a {h}"
    elif d:
        texto = f"según {n_txs} {fuente} de {d}"
    else:
        texto = f"según {n_txs} {fuente}"
    return {"n_txs": n_txs, "desde": d, "hasta": h, "sello": texto}


def _where_portafolio(portfolio_id: Optional[int], alias: str = "t") -> tuple[str, list]:
    """Filtro de empresa inyectado por CÓDIGO (criterio inmutable 2)."""
    if portfolio_id is None:
        return "", []
    return f" AND {alias}.portfolio_id = %s", [int(portfolio_id)]


# ══════════════════════════════════════════════════════════════════════
# Funciones de métrica — fn(cur, portfolio_id, params_ya_validados)
# ══════════════════════════════════════════════════════════════════════

def _resumen_periodo(cur, portfolio_id, params):
    desde = params.get("desde") or _hoy().replace(day=1).isoformat()
    hasta = params.get("hasta") or _hoy().isoformat()
    extra, extra_params = _where_portafolio(portfolio_id)
    cur.execute(f"""
        SELECT COUNT(*) FILTER (WHERE {_ES_COP}),
               COALESCE(SUM(t.net_value) FILTER (WHERE upper(t.type) = 'INGRESO' AND {_ES_COP}), 0),
               COALESCE(SUM(t.net_value) FILTER (WHERE upper(t.type) = 'GASTO'   AND {_ES_COP}), 0),
               COUNT(*) FILTER (WHERE NOT {_ES_COP}),
               MIN(t.transaction_date), MAX(t.transaction_date)
          FROM transactions t
         WHERE t.transaction_date BETWEEN %s AND %s{extra};
    """, [desde, hasta] + extra_params)
    n_cop, ingresos, gastos, n_usd, d_min, d_max = cur.fetchone()
    ingresos, gastos = _f(ingresos), _f(gastos)
    origen = _sello(int(n_cop or 0), d_min or desde, d_max or hasta)
    if n_usd:
        origen["usd_excluidas"] = int(n_usd)
    res = {
        "valor": ingresos - gastos,
        "valores": {"ingresos": ingresos, "gastos": gastos, "neto": ingresos - gastos},
        "origen": origen,
    }
    if not n_cop:
        res["nota"] = "No hay transacciones en COP en ese rango."
    return res


_AGRUPADORES = {
    # etiqueta SQL + joins necesarios. '(sin ...)' visible: la calidad de
    # datos jamás se esconde (criterio inmutable 4).
    "categoria": ("COALESCE(NULLIF(btrim(t.category), ''), '(sin categoría)')", ""),
    "tercero":   ("COALESCE(tp.name, '(sin tercero)')",
                  " LEFT JOIN third_parties tp ON tp.id = t.third_party_id"),
    "cuenta":    ("COALESCE(a.name, '(sin cuenta)')",
                  " LEFT JOIN user_accounts a ON a.id = t.account_id"),
}


def _movimiento_mes(cur, portfolio_id, params, tipo: str):
    mes = params.get("mes") or _mes_actual()
    agrupar_por = params.get("agrupar_por") or "categoria"
    desde, hasta = _rango_mes(mes)
    extra, extra_params = _where_portafolio(portfolio_id)
    base_where = f"upper(t.type) = %s AND t.transaction_date BETWEEN %s AND %s{extra}"
    base_params = [tipo, desde.isoformat(), hasta.isoformat()] + extra_params

    valores = []
    if agrupar_por != "ninguno":
        etiqueta_sql, join_sql = _AGRUPADORES[agrupar_por]
        cur.execute(f"""
            SELECT {etiqueta_sql} AS etiqueta,
                   COALESCE(SUM(t.net_value) FILTER (WHERE {_ES_COP}), 0) AS total,
                   COUNT(*) FILTER (WHERE {_ES_COP}) AS n
              FROM transactions t{join_sql}
             WHERE {base_where}
             GROUP BY 1
             ORDER BY 2 DESC;
        """, base_params)
        valores = [{"etiqueta": r[0], "valor": _f(r[1]), "n_txs": int(r[2] or 0)}
                   for r in cur.fetchall() if r[2]]

    cur.execute(f"""
        SELECT COUNT(*) FILTER (WHERE {_ES_COP}),
               COALESCE(SUM(t.net_value) FILTER (WHERE {_ES_COP}), 0),
               COUNT(*) FILTER (WHERE NOT {_ES_COP}),
               MIN(t.transaction_date), MAX(t.transaction_date)
          FROM transactions t
         WHERE {base_where};
    """, base_params)
    n_cop, total, n_usd, d_min, d_max = cur.fetchone()
    origen = _sello(int(n_cop or 0), d_min or desde, d_max or hasta)
    if n_usd:
        origen["usd_excluidas"] = int(n_usd)
    res = {"valor": _f(total), "valores": valores, "origen": origen,
           "detalle": {"mes": mes, "agrupar_por": agrupar_por}}
    if not n_cop:
        res["nota"] = f"No hay {tipo.lower()}s en COP registrados en {mes}."
    return res


def _gasto_mes(cur, portfolio_id, params):
    return _movimiento_mes(cur, portfolio_id, params, "GASTO")


def _ingreso_mes(cur, portfolio_id, params):
    return _movimiento_mes(cur, portfolio_id, params, "INGRESO")


def _variacion_mensual(cur, portfolio_id, params):
    tipo = params.get("tipo") or "GASTO"
    mes = params.get("mes") or _mes_actual()
    anterior = _mes_anterior(mes)
    totales, n_total = {}, 0
    extra, extra_params = _where_portafolio(portfolio_id)
    for m in (anterior, mes):
        desde, hasta = _rango_mes(m)
        cur.execute(f"""
            SELECT COUNT(*) FILTER (WHERE {_ES_COP}),
                   COALESCE(SUM(t.net_value) FILTER (WHERE {_ES_COP}), 0)
              FROM transactions t
             WHERE upper(t.type) = %s AND t.transaction_date BETWEEN %s AND %s{extra};
        """, [tipo, desde.isoformat(), hasta.isoformat()] + extra_params)
        n, total = cur.fetchone()
        totales[m] = {"n": int(n or 0), "total": _f(total)}
        n_total += int(n or 0)
    v_ant, v_act = totales[anterior]["total"], totales[mes]["total"]
    delta = v_act - v_ant
    pct = round(delta / v_ant * 100, 1) if v_ant else None
    res = {
        "valor": delta,
        "valores": {"mes": mes, "total_mes": v_act, "mes_anterior": anterior,
                    "total_mes_anterior": v_ant, "delta": delta, "pct": pct},
        "origen": _sello(n_total, _rango_mes(anterior)[0], _rango_mes(mes)[1]),
        "detalle": {"tipo": tipo},
    }
    if pct is None:
        res["nota"] = (f"En {anterior} no hubo {tipo.lower()}s en COP: "
                       "el porcentaje de variación no se puede calcular (no se inventa).")
    return res


def _flujo_mensual(cur, portfolio_id, params):
    meses = params.get("meses") or 6
    hoy = _hoy()
    # Primer día del mes (meses-1) atrás
    total_meses = hoy.year * 12 + (hoy.month - 1) - (meses - 1)
    desde = _dt.date(total_meses // 12, total_meses % 12 + 1, 1)
    extra, extra_params = _where_portafolio(portfolio_id)
    cur.execute(f"""
        SELECT to_char(t.transaction_date, 'YYYY-MM') AS mes,
               COALESCE(SUM(t.net_value) FILTER (WHERE upper(t.type) = 'INGRESO' AND {_ES_COP}), 0),
               COALESCE(SUM(t.net_value) FILTER (WHERE upper(t.type) = 'GASTO'   AND {_ES_COP}), 0),
               COUNT(*) FILTER (WHERE {_ES_COP}),
               COUNT(*) FILTER (WHERE NOT {_ES_COP})
          FROM transactions t
         WHERE t.transaction_date BETWEEN %s AND %s{extra}
         GROUP BY 1
         ORDER BY 1;
    """, [desde.isoformat(), hoy.isoformat()] + extra_params)
    filas = cur.fetchall()
    valores = [{"mes": r[0], "ingresos": _f(r[1]), "gastos": _f(r[2]),
                "neto": _f(r[1]) - _f(r[2]), "n_txs": int(r[3] or 0)} for r in filas]
    n_cop = sum(v["n_txs"] for v in valores)
    n_usd = sum(int(r[4] or 0) for r in filas)
    origen = _sello(n_cop, desde, hoy)
    if n_usd:
        origen["usd_excluidas"] = n_usd
    res = {"valores": valores, "origen": origen, "detalle": {"meses": meses}}
    if not n_cop:
        res["nota"] = f"No hay transacciones en COP en los últimos {meses} meses."
    return res


def _balance_cuentas(cur, portfolio_id, params):
    # Las cuentas (user_accounts) son GLOBALES — no tienen empresa. Se dice
    # claro en la nota en vez de fingir un filtro que no existe.
    cur.execute("""
        SELECT name, current_balance, currency, type
          FROM user_accounts
         ORDER BY current_balance DESC;
    """)
    filas = cur.fetchall()
    valores = [{"etiqueta": r[0], "valor": _f(r[1]), "moneda": r[2] or "COP", "tipo": r[3]}
               for r in filas]
    total_cop = sum(v["valor"] for v in valores if v["moneda"] != "USD")
    origen = _sello(len(valores), fuente="cuentas (saldo actual)")
    res = {"valor": total_cop, "valores": valores, "origen": origen}
    notas = ["Las cuentas son globales: este balance no se filtra por empresa."]
    if portfolio_id is not None:
        notas.append("Se ignoró el filtro de empresa por esa razón.")
    if any(v["moneda"] == "USD" for v in valores):
        notas.append("El total excluye cuentas en USD (se listan aparte).")
    res["nota"] = " ".join(notas)
    if not valores:
        res["nota"] = "No hay cuentas registradas."
    return res


def _cartera_vencida(cur, portfolio_id, params):
    # Mismo criterio que /api/cartera/summary: vencida = pendiente con
    # due_date < hoy. Con filtro de empresa, solo entra la cartera ligada a
    # una TX de esa empresa (el ledger suelto no tiene empresa).
    extra, extra_params = _where_portafolio(portfolio_id)
    join_tx = " LEFT JOIN transactions t ON t.id = l.transaction_id"
    where_emp = extra
    cur.execute(f"""
        SELECT COUNT(*) FILTER (WHERE l.due_date < CURRENT_DATE),
               COALESCE(SUM(l.remaining_balance) FILTER (WHERE l.due_date < CURRENT_DATE), 0),
               COUNT(*),
               COALESCE(SUM(l.remaining_balance), 0),
               MIN(l.due_date) FILTER (WHERE l.due_date < CURRENT_DATE),
               MAX(l.due_date) FILTER (WHERE l.due_date < CURRENT_DATE)
          FROM cxp_cxc_ledger l{join_tx}
         WHERE l.type = 'CXC' AND l.status NOT IN ('PAGADO', 'CANCELADO'){where_emp};
    """, extra_params)
    n_venc, monto_venc, n_pend, monto_pend, d_min, d_max = cur.fetchone()
    n_venc, n_pend = int(n_venc or 0), int(n_pend or 0)
    monto_venc, monto_pend = _f(monto_venc), _f(monto_pend)

    cur.execute(f"""
        SELECT tp.name, COALESCE(SUM(l.remaining_balance), 0), COUNT(*), MIN(l.due_date)
          FROM cxp_cxc_ledger l
          JOIN third_parties tp ON tp.id = l.third_party_id{join_tx}
         WHERE l.type = 'CXC' AND l.status NOT IN ('PAGADO', 'CANCELADO')
           AND l.due_date < CURRENT_DATE{where_emp}
         GROUP BY tp.name
         ORDER BY 2 DESC
         LIMIT 10;
    """, extra_params)
    clientes = [{"etiqueta": r[0], "valor": _f(r[1]), "n_cuentas": int(r[2] or 0),
                 "vencida_desde": str(r[3]) if r[3] else None} for r in cur.fetchall()]

    pct = round(monto_venc / monto_pend * 100, 1) if monto_pend else None
    origen = _sello(n_venc, d_min, d_max, fuente="cuentas por cobrar vencidas")
    res = {
        "valor": monto_venc,
        "valores": {"monto_vencido": monto_venc, "n_vencidas": n_venc,
                    "monto_pendiente_total": monto_pend, "n_pendientes": n_pend,
                    "pct_vencida": pct, "clientes": clientes},
        "origen": origen,
    }
    if portfolio_id is not None:
        res["nota"] = "Solo cartera ligada a transacciones de la empresa filtrada."
    if not n_pend:
        res["nota"] = "No hay cuentas por cobrar pendientes."
    return res


def _conteo_terceros(cur, portfolio_id, params):
    # Primera métrica nacida de la BITÁCORA (pregunta sin responder del 16-sep):
    # "total de terceros". El conteo de terceros es GLOBAL (no tienen empresa);
    # el filtro de empresa/mes solo aplica a "con movimiento" (vía transactions).
    mes = params.get("mes")
    cur.execute("""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE identification_number LIKE 'SN-%')
          FROM third_parties;
    """)
    total, provisionales = cur.fetchone()

    where_mes, mes_params = "", []
    if mes:
        desde, hasta = _rango_mes(mes)
        where_mes = " AND t.transaction_date BETWEEN %s AND %s"
        mes_params = [desde.isoformat(), hasta.isoformat()]
    extra, extra_params = _where_portafolio(portfolio_id)
    cur.execute(f"""
        SELECT COUNT(DISTINCT t.third_party_id), COUNT(*),
               MIN(t.transaction_date), MAX(t.transaction_date)
          FROM transactions t
         WHERE t.third_party_id IS NOT NULL{where_mes}{extra};
    """, mes_params + extra_params)
    con_mov, n_txs, d_min, d_max = cur.fetchone()

    valores = {
        "total_terceros": int(total or 0),
        "provisionales": int(provisionales or 0),
        "con_movimiento": int(con_mov or 0),
        "mes": mes,
    }
    res = {"valor": int(total or 0), "unidad": "terceros", "valores": valores,
           "origen": _sello(int(n_txs or 0), d_min, d_max)}
    notas = ["El total de terceros es global (los terceros no tienen empresa)."]
    if portfolio_id is not None:
        notas.append("El filtro de empresa solo aplica a 'con movimiento'.")
    if not valores["total_terceros"]:
        notas = ["No hay terceros registrados."]
    res["nota"] = " ".join(notas)
    return res


def _calidad_datos(cur, portfolio_id, params):
    extra, extra_params = _where_portafolio(portfolio_id)
    cur.execute(f"""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE NULLIF(btrim(t.category), '') IS NULL),
               COUNT(*) FILTER (WHERE NULLIF(btrim(t.evidence_file_path), '') IS NULL
                                  AND NOT EXISTS (SELECT 1 FROM transaction_evidences ev
                                                   WHERE ev.transaction_id = t.id)),
               MIN(t.transaction_date), MAX(t.transaction_date)
          FROM transactions t
         WHERE TRUE{extra};
    """, extra_params)
    n_total, sin_categoria, sin_evidencia, d_min, d_max = cur.fetchone()
    cur.execute("""
        SELECT COUNT(*) FILTER (WHERE identification_number LIKE 'SN-%'),
               COALESCE((SELECT SUM(n - 1) FROM (
                   SELECT COUNT(*) AS n FROM third_parties
                    GROUP BY lower(btrim(name)) HAVING COUNT(*) > 1) d), 0)
          FROM third_parties;
    """)
    provisionales, duplicados = cur.fetchone()
    n_total = int(n_total or 0)
    valores = {
        "txs_total": n_total,
        "txs_sin_categoria": int(sin_categoria or 0),
        "txs_sin_evidencia": int(sin_evidencia or 0),
        "terceros_numero_provisional": int(provisionales or 0),
        "terceros_nombres_duplicados": int(duplicados or 0),
    }
    res = {"valores": valores, "origen": _sello(n_total, d_min, d_max)}
    if portfolio_id is not None:
        res["nota"] = "Los conteos de terceros son globales (no tienen empresa)."
    if not n_total:
        res["nota"] = "No hay transacciones registradas."
    return res


# ══════════════════════════════════════════════════════════════════════
# EL CATÁLOGO — la whitelist completa (criterio inmutable 1)
# ══════════════════════════════════════════════════════════════════════

_P_MES = {"tipo": "mes", "descripcion": "Mes en formato YYYY-MM (por defecto: el mes actual)",
          "requerido": False}
_P_AGRUPAR = {"tipo": "opcion", "opciones": ["categoria", "tercero", "cuenta", "ninguno"],
              "descripcion": "Cómo desglosar el total (por defecto: categoria)", "requerido": False}

# Plantillas SQL "para humanos" (pedido de Andrés 16-sep): la consulta real de
# cada métrica, condensada y con {parámetros} marcados, para mostrarla en el
# módulo — la auditabilidad visible. [..] = solo si el usuario filtró empresa.
# "cop" abrevia: t.transaction_currency IS DISTINCT FROM 'USD' (el USD se
# cuenta aparte, jamás se suma al COP).

_SQL_RESUMEN = """\
SELECT COUNT(*)              FILTER (WHERE cop),
       SUM(t.net_value)      FILTER (WHERE upper(t.type)='INGRESO' AND cop),
       SUM(t.net_value)      FILTER (WHERE upper(t.type)='GASTO'   AND cop),
       MIN(t.transaction_date), MAX(t.transaction_date)
  FROM transactions t
 WHERE t.transaction_date BETWEEN {desde} AND {hasta}
   [AND t.portfolio_id = {empresa}]"""

_SQL_MOVIMIENTO = """\
SELECT {agrupar_por},                       -- categoría | tercero | cuenta
       SUM(t.net_value) FILTER (WHERE cop),
       COUNT(*)         FILTER (WHERE cop)
  FROM transactions t
  [LEFT JOIN third_parties / user_accounts según agrupar_por]
 WHERE upper(t.type) = '{TIPO}'
   AND t.transaction_date BETWEEN {mes}-01 AND fin de {mes}
   [AND t.portfolio_id = {empresa}]
 GROUP BY 1  ORDER BY 2 DESC"""

_SQL_VARIACION = """\
-- la misma consulta corre 2 veces: {mes} y el mes anterior
SELECT COUNT(*) FILTER (WHERE cop), SUM(t.net_value) FILTER (WHERE cop)
  FROM transactions t
 WHERE upper(t.type) = {tipo}
   AND t.transaction_date BETWEEN inicio AND fin del mes
   [AND t.portfolio_id = {empresa}]
-- delta y % en Python; sin mes base => % = null (no se inventa)"""

_SQL_FLUJO = """\
SELECT to_char(t.transaction_date, 'YYYY-MM'),
       SUM(t.net_value) FILTER (WHERE upper(t.type)='INGRESO' AND cop),
       SUM(t.net_value) FILTER (WHERE upper(t.type)='GASTO'   AND cop),
       COUNT(*)         FILTER (WHERE cop)
  FROM transactions t
 WHERE t.transaction_date BETWEEN hace {meses} meses AND hoy
   [AND t.portfolio_id = {empresa}]
 GROUP BY 1  ORDER BY 1"""

_SQL_BALANCE = """\
SELECT name, current_balance, currency, type
  FROM user_accounts
 ORDER BY current_balance DESC
-- las cuentas son globales: no existe filtro de empresa (se avisa en la nota)"""

_SQL_CARTERA = """\
SELECT COUNT(*)                 FILTER (WHERE l.due_date < CURRENT_DATE),
       SUM(l.remaining_balance) FILTER (WHERE l.due_date < CURRENT_DATE),
       COUNT(*), SUM(l.remaining_balance)
  FROM cxp_cxc_ledger l
  LEFT JOIN transactions t ON t.id = l.transaction_id
 WHERE l.type = 'CXC' AND l.status NOT IN ('PAGADO', 'CANCELADO')
   [AND t.portfolio_id = {empresa}]
-- + top 10 clientes: mismo WHERE + JOIN third_parties, GROUP BY nombre"""

_SQL_TERCEROS = """\
SELECT COUNT(*),                    -- total global: los terceros no tienen empresa
       COUNT(*) FILTER (WHERE identification_number LIKE 'SN-%')
  FROM third_parties;
SELECT COUNT(DISTINCT t.third_party_id)   -- cuántos se movieron
  FROM transactions t
 WHERE t.third_party_id IS NOT NULL
   [AND t.transaction_date dentro de {mes}]
   [AND t.portfolio_id = {empresa}]"""

_SQL_CALIDAD = """\
SELECT COUNT(*),
       COUNT(*) FILTER (WHERE btrim(t.category) = '' OR t.category IS NULL),
       COUNT(*) FILTER (WHERE sin archivo NI evidencias adjuntas)
  FROM transactions t
 WHERE TRUE [AND t.portfolio_id = {empresa}]
-- + terceros (global): número provisional 'SN-%' y nombres duplicados"""

CATALOGO: Dict[str, Dict[str, Any]] = {
    "resumen_periodo": {
        "etiqueta": "Resumen del periodo",
        "descripcion": "Ingresos, gastos y neto entre dos fechas (por defecto: el mes en curso).",
        "params": {
            "desde": {"tipo": "fecha", "descripcion": "Fecha inicial YYYY-MM-DD", "requerido": False},
            "hasta": {"tipo": "fecha", "descripcion": "Fecha final YYYY-MM-DD", "requerido": False},
        },
        "fn": _resumen_periodo,
        "sql": _SQL_RESUMEN,
    },
    "gasto_mes": {
        "etiqueta": "Gasto del mes",
        "descripcion": "Total gastado en un mes, desglosado por categoría, tercero o cuenta.",
        "params": {"mes": _P_MES, "agrupar_por": _P_AGRUPAR},
        "fn": _gasto_mes,
        "sql": _SQL_MOVIMIENTO,
    },
    "ingreso_mes": {
        "etiqueta": "Ingreso del mes",
        "descripcion": "Total de ingresos de un mes, desglosado por categoría, tercero o cuenta.",
        "params": {"mes": _P_MES, "agrupar_por": _P_AGRUPAR},
        "fn": _ingreso_mes,
        "sql": _SQL_MOVIMIENTO,
    },
    "variacion_mensual": {
        "etiqueta": "Variación mes a mes",
        "descripcion": "Compara el gasto (o ingreso) de un mes contra el mes anterior: delta y porcentaje.",
        "params": {
            "tipo": {"tipo": "opcion", "opciones": ["GASTO", "INGRESO"],
                     "descripcion": "Qué comparar (por defecto: GASTO)", "requerido": False},
            "mes": _P_MES,
        },
        "fn": _variacion_mensual,
        "sql": _SQL_VARIACION,
    },
    "flujo_mensual": {
        "etiqueta": "Flujo mensual",
        "descripcion": "Serie de ingresos vs gastos por mes de los últimos N meses (por defecto 6).",
        "params": {
            "meses": {"tipo": "entero", "min": 1, "max": 36,
                      "descripcion": "Cuántos meses hacia atrás (1-36)", "requerido": False},
        },
        "fn": _flujo_mensual,
        "sql": _SQL_FLUJO,
    },
    "balance_cuentas": {
        "etiqueta": "Balance por cuenta",
        "descripcion": "Saldo actual de cada cuenta (bancos, efectivo, tarjetas) y total en COP.",
        "params": {},
        "fn": _balance_cuentas,
        "sql": _SQL_BALANCE,
    },
    "cartera_vencida": {
        "etiqueta": "Cartera vencida",
        "descripcion": "Cuentas por cobrar vencidas: monto, % sobre lo pendiente y top clientes.",
        "params": {},
        "fn": _cartera_vencida,
        "sql": _SQL_CARTERA,
    },
    "conteo_terceros": {
        "etiqueta": "Conteo de terceros",
        "descripcion": "Cuántos terceros (clientes/proveedores) hay registrados y cuántos tuvieron movimiento (opcionalmente en un mes).",
        "params": {"mes": _P_MES},
        "fn": _conteo_terceros,
        "sql": _SQL_TERCEROS,
    },
    "calidad_datos": {
        "etiqueta": "Calidad de datos",
        "descripcion": "TXs sin categoría o sin evidencia y terceros provisionales o duplicados.",
        "params": {},
        "fn": _calidad_datos,
        "sql": _SQL_CALIDAD,
    },
}


def catalogo_publico() -> List[Dict[str, Any]]:
    """El catálogo sin las funciones (para GET /api/analytics/catalog y el prompt)."""
    return [
        {"id": mid, "etiqueta": m["etiqueta"], "descripcion": m["descripcion"],
         "params": m["params"], "sql": m.get("sql", "")}
        for mid, m in CATALOGO.items()
    ]


def catalogo_para_prompt() -> str:
    """Versión compacta en texto para inyectar en el prompt del LLM (B3)."""
    lineas = []
    for m in catalogo_publico():
        ps = []
        for nombre, spec in m["params"].items():
            det = spec["tipo"]
            if spec.get("opciones"):
                det = "|".join(spec["opciones"])
            ps.append(f"{nombre}({det}): {spec['descripcion']}")
        lineas.append(f"- {m['id']}: {m['descripcion']}"
                      + (f" Parámetros opcionales: {'; '.join(ps)}" if ps else ""))
    return "\n".join(lineas)


def _validar_params(metric_id: str, crudos: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Whitelist de parámetros: lo no declarado se DESCARTA (si el LLM manda
    'empresa' o 'portfolio', muere aquí — criterio inmutable 2)."""
    spec = CATALOGO[metric_id]["params"]
    crudos = crudos or {}
    limpios: Dict[str, Any] = {}
    for nombre, s in spec.items():
        valor = crudos.get(nombre)
        if valor in (None, ""):
            if s.get("requerido"):
                raise ValueError(f"Falta el parámetro requerido '{nombre}' de la métrica {metric_id}.")
            continue
        tipo = s["tipo"]
        if tipo == "mes":
            valor = str(valor)
            if not _RE_MES.match(valor):
                raise ValueError(f"'{nombre}' debe ser un mes YYYY-MM (recibí: {valor!r}).")
        elif tipo == "fecha":
            valor = str(valor)
            if not _RE_FECHA.match(valor):
                raise ValueError(f"'{nombre}' debe ser una fecha YYYY-MM-DD (recibí: {valor!r}).")
            _dt.date.fromisoformat(valor)   # valida que exista (2026-02-31 no)
        elif tipo == "entero":
            try:
                valor = int(valor)
            except (TypeError, ValueError):
                raise ValueError(f"'{nombre}' debe ser un número entero (recibí: {valor!r}).")
            if not (s.get("min", valor) <= valor <= s.get("max", valor)):
                raise ValueError(f"'{nombre}' debe estar entre {s['min']} y {s['max']}.")
        elif tipo == "opcion":
            valor = str(valor).strip()
            if valor not in s["opciones"]:
                if valor.lower() in s["opciones"]:
                    valor = valor.lower()
                elif valor.upper() in s["opciones"]:
                    valor = valor.upper()
                else:
                    raise ValueError(f"'{nombre}' debe ser una de: {', '.join(s['opciones'])}.")
        limpios[nombre] = valor
    return limpios


def ejecutar_metrica(metric_id: str, params: Optional[Dict[str, Any]] = None,
                     portfolio_id: Optional[int] = None, conn=None) -> Dict[str, Any]:
    """Punto de entrada ÚNICO del catálogo.

    - metric_id fuera del catálogo → ValueError (nunca SQL libre).
    - params se validan contra la whitelist (lo desconocido se descarta).
    - portfolio_id lo pone el BACKEND desde la sesión/selector — jamás el LLM.
    - conn inyectable para tests; sin ella, se toma (y devuelve) del pool.
    """
    if metric_id not in CATALOGO:
        raise ValueError(
            f"La métrica '{metric_id}' no existe en el catálogo. "
            f"Disponibles: {', '.join(sorted(CATALOGO))}."
        )
    limpios = _validar_params(metric_id, params)
    meta = CATALOGO[metric_id]

    conn_propia = conn is None
    if conn_propia:
        from database_driver import get_db_connection, release_db_connection
        conn = get_db_connection()
        if conn is None:
            raise RuntimeError("Base de datos no disponible: la métrica no se puede calcular (no se inventa).")
    try:
        cur = conn.cursor()
        resultado = meta["fn"](cur, portfolio_id, limpios)
        try:
            cur.close()
        except Exception:
            pass
    finally:
        if conn_propia:
            try:
                conn.rollback()   # solo lecturas; suelta cualquier snapshot
            except Exception:
                pass
            from database_driver import release_db_connection
            release_db_connection(conn)

    resultado.setdefault("unidad", "COP")
    resultado["metrica"] = metric_id
    resultado["etiqueta"] = meta["etiqueta"]
    resultado["portfolio_id"] = portfolio_id
    return resultado
