# -*- coding: utf-8 -*-
"""diario_query.py — Búsqueda, filtros, orden, totales y grupos del Libro
Diario (Módulo 02) en el SERVIDOR.

Pedido de Andrés (16-oct-2026): el Diario carga de 50 en 50, así que un
filtro en el navegador solo vería lo cargado y los totales mentirían. Aquí
todo se resuelve en UNA sentencia (CTEs → una fila de columnas JSON, el
mismo patrón de dashboard_query.py):

  ids        → transacciones que cumplen los filtros (sin duplicar filas)
  pagina     → la página pedida con las MISMAS columnas que el dashboard
               (TX_SELECT_LIST) + `n_iguales` (aviso de posible duplicado)
  totales    → ingresos / gastos / transferencias / neto de TODO lo filtrado
  grupos     → subtotales por tercero, categoría, mes, cuenta, etiqueta…

`construir_filtros` es puro (sin BD) para poder probarlo en el CI.
Los avisos son informativos: nada aquí bloquea ni modifica datos.
"""
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from psycopg2.extras import RealDictCursor

from fin_sys_core.dashboard_query import TX_FROM, TX_SELECT_LIST
from fin_sys_core.db_pool import get_conn, put_conn

TIPOS = ("INGRESO", "GASTO", "TRANSFERENCIA")

# Orden → SQL. Siempre con desempate por id para que la paginación sea estable.
ORDENES = {
    "fecha_desc":   "t.transaction_date DESC, t.id DESC",
    "fecha_asc":    "t.transaction_date ASC, t.id ASC",
    "monto_desc":   "COALESCE(t.net_value, 0) DESC, t.id DESC",
    "monto_asc":    "COALESCE(t.net_value, 0) ASC, t.id ASC",
    "tercero_asc":  "tp.name ASC NULLS LAST, t.transaction_date DESC, t.id DESC",
    "concepto_asc": "t.concept ASC NULLS LAST, t.id DESC",
}

# Agrupación → (expresión de la clave, JOIN extra). La etiqueta despliega el
# arreglo: una TX con 2 etiquetas suma en las dos (se avisa en la interfaz).
GRUPOS = {
    "tercero":   "COALESCE(tp.name, '(sin tercero)')",
    "categoria": "COALESCE(NULLIF(t.category, ''), '(sin categoría)')",
    "mes":       "to_char(t.transaction_date, 'YYYY-MM')",
    "cuenta":    "COALESCE(a.name, NULLIF(t.payment_method, ''), '(sin cuenta)')",
    "etiqueta":  "g.etiqueta",
    "tipo":      "upper(t.type)",
    "empresa":   "p.name",
}
# `ref` = id para convertir el grupo en filtro con un clic (tercero / cuenta).
_REF_GRUPO = {"tercero": "MIN(t.third_party_id)", "cuenta": "MIN(t.account_id)"}
_JOIN_ETIQUETA = ("CROSS JOIN LATERAL unnest(CASE WHEN COALESCE(cardinality(t.tags), 0) = 0 "
                  "THEN ARRAY['(sin etiqueta)']::text[] ELSE t.tags END) AS g(etiqueta)")

# Banderas de calidad / atributos (todas informativas).
BANDERAS = {
    "sin_tercero":   "(t.third_party_id IS NULL OR tp.identification_number LIKE 'SN-%%')",
    "sin_evidencia": ("(COALESCE(t.evidence_file_path, '') = '' AND NOT EXISTS "
                      "(SELECT 1 FROM transaction_evidences ev WHERE ev.transaction_id = t.id))"),
    "con_evidencia": ("(COALESCE(t.evidence_file_path, '') <> '' OR EXISTS "
                      "(SELECT 1 FROM transaction_evidences ev WHERE ev.transaction_id = t.id))"),
    "sin_categoria": "COALESCE(t.category, '') = ''",
    "sin_etiqueta":  "COALESCE(cardinality(t.tags), 0) = 0",
    "con_nota":      "COALESCE(t.note, '') <> ''",
    "recurrentes":   "COALESCE(t.is_recurring, false)",
    "con_impuestos": "(COALESCE(t.tax_iva_amount, 0) > 0 OR COALESCE(t.tax_gmf_amount, 0) > 0)",
    "con_ubicacion": "COALESCE(t.geo_maps_link, '') <> ''",
    "duplicados":    "b.n_iguales > 1",
}

LIMITE_MAX = 5000      # tope por petición (exportar "todo lo filtrado")

# Búsqueda sin tildes ni mayúsculas ("cafe" encuentra "Café") sin depender de
# la extensión unaccent: translate() con las vocales acentuadas del español.
_CON_TILDE = "áéíóúüàèìòùäëïöâêîôûñ"
_SIN_TILDE = "aeiouuaeiouaeioaeioun"


def sin_tildes(texto: str) -> str:
    return texto.lower().translate(str.maketrans(_CON_TILDE, _SIN_TILDE))


def _sql_sin_tildes(col: str) -> str:
    return f"translate(lower({col}), '{_CON_TILDE}', '{_SIN_TILDE}')"


def _lista(valor) -> List[str]:
    """'a,b' | ['a','b'] | None → ['a','b'] sin vacíos."""
    if valor is None:
        return []
    if isinstance(valor, str):
        valor = valor.split(",")
    return [str(v).strip() for v in valor if str(v).strip()]


def _enteros(valor) -> List[int]:
    out = []
    for v in _lista(valor):
        if not re.fullmatch(r"-?\d+", v):
            raise ValueError(f"Identificador inválido: '{v}'")
        out.append(int(v))
    return out


def _fecha(valor: Optional[str], nombre: str) -> Optional[str]:
    if not valor:
        return None
    try:
        return date.fromisoformat(valor).isoformat()
    except ValueError:
        raise ValueError(f"Fecha '{nombre}' inválida: '{valor}' (use AAAA-MM-DD)")


def _numero(valor, nombre: str) -> Optional[float]:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"Monto '{nombre}' inválido: '{valor}'")


def numero_de_busqueda(q: str) -> Optional[float]:
    """'$1.500.000' / '17500' / '1.500,50' → número; texto → None.
    Formato colombiano: el punto separa miles y la coma los decimales."""
    s = q.strip().replace("$", "").replace(" ", "")
    if not s or not re.fullmatch(r"[\d.,]+", s) or not re.search(r"\d", s):
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def construir_filtros(f: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Filtros → (cláusula WHERE sin la palabra WHERE, parámetros con nombre).

    Claves aceptadas (todas opcionales):
      empresas: lista de nombres de portafolio ([] = todas)
      q, tipos, desde, hasta, terceros, cuentas, categorias, etiquetas,
      monto_min, monto_max, moneda, cartera (CXC|CXP|NINGUNA), cartera_estado,
      banderas: lista de claves de BANDERAS
    Lanza ValueError con un mensaje legible si algo no es válido.
    """
    cond: List[str] = []
    p: Dict[str, Any] = {}

    empresas = _lista(f.get("empresas"))
    if empresas:
        cond.append("p.name = ANY(%(empresas)s)")
        p["empresas"] = empresas

    q = (f.get("q") or "").strip()
    if q:
        if len(q) > 120:
            raise ValueError("La búsqueda es demasiado larga (máximo 120 caracteres).")
        p["q"] = "%" + sin_tildes(q).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        campos = ["t.concept", "t.note", "tp.name", "tp.identification_number", "a.name",
                  "da.name", "t.category", "t.payment_method", "p.name",
                  "array_to_string(t.tags, ' ')"]
        partes = [f"{_sql_sin_tildes(c)} LIKE %(q)s" for c in campos]
        m = re.fullmatch(r"#(\d+)", q)
        if m:
            partes.append("t.id = %(q_id)s")
            p["q_id"] = int(m.group(1))
        n = numero_de_busqueda(q)
        if n is not None:
            partes.append("t.net_value = %(q_num)s OR t.amount = %(q_num)s")
            p["q_num"] = n
        cond.append("(" + " OR ".join(partes) + ")")

    tipos = [t.upper() for t in _lista(f.get("tipos"))]
    malos = [t for t in tipos if t not in TIPOS]
    if malos:
        raise ValueError(f"Tipo inválido: {', '.join(malos)}")
    if tipos:
        cond.append("upper(t.type) = ANY(%(tipos)s)")
        p["tipos"] = tipos

    desde, hasta = _fecha(f.get("desde"), "desde"), _fecha(f.get("hasta"), "hasta")
    if desde and hasta and desde > hasta:
        raise ValueError("La fecha 'desde' es posterior a 'hasta'.")
    if desde:
        cond.append("t.transaction_date >= %(desde)s::date")
        p["desde"] = desde
    if hasta:
        cond.append("t.transaction_date <= %(hasta)s::date")
        p["hasta"] = hasta

    terceros = _enteros(f.get("terceros"))
    if terceros:
        cond.append("t.third_party_id = ANY(%(terceros)s)")
        p["terceros"] = terceros

    cuentas = _enteros(f.get("cuentas"))
    if cuentas:
        # Una transferencia toca dos cuentas: aparece si cualquiera coincide.
        cond.append("(t.account_id = ANY(%(cuentas)s) OR t.dest_account_id = ANY(%(cuentas)s))")
        p["cuentas"] = cuentas

    categorias = _lista(f.get("categorias"))
    if categorias:
        cond.append("t.category = ANY(%(categorias)s)")
        p["categorias"] = categorias

    etiquetas = _lista(f.get("etiquetas"))
    if etiquetas:
        cond.append("t.tags && %(etiquetas)s::text[]")
        p["etiquetas"] = etiquetas

    mmin, mmax = _numero(f.get("monto_min"), "mínimo"), _numero(f.get("monto_max"), "máximo")
    if mmin is not None and mmax is not None and mmin > mmax:
        raise ValueError("El monto mínimo es mayor que el máximo.")
    if mmin is not None:
        cond.append("COALESCE(t.net_value, 0) >= %(monto_min)s")
        p["monto_min"] = mmin
    if mmax is not None:
        cond.append("COALESCE(t.net_value, 0) <= %(monto_max)s")
        p["monto_max"] = mmax

    moneda = (f.get("moneda") or "").strip().upper()
    if moneda == "USD":
        cond.append("t.transaction_currency = 'USD'")
    elif moneda == "COP":
        cond.append("t.transaction_currency IS DISTINCT FROM 'USD'")
    elif moneda:
        raise ValueError(f"Moneda inválida: '{moneda}'")

    cartera = (f.get("cartera") or "").strip().upper()
    estado = (f.get("cartera_estado") or "").strip().upper()
    if cartera in ("CXC", "CXP"):
        sub = "SELECT 1 FROM cxp_cxc_ledger cx WHERE cx.transaction_id = t.id AND cx.type = %(cartera)s"
        p["cartera"] = cartera
        if estado:
            sub += " AND upper(cx.status) = %(cartera_estado)s"
            p["cartera_estado"] = estado
        cond.append(f"EXISTS ({sub})")
    elif cartera == "NINGUNA":
        cond.append("NOT EXISTS (SELECT 1 FROM cxp_cxc_ledger cx WHERE cx.transaction_id = t.id)")
    elif cartera:
        raise ValueError(f"Cartera inválida: '{cartera}'")

    for b in _lista(f.get("banderas")):
        if b not in BANDERAS:
            raise ValueError(f"Filtro desconocido: '{b}'")
        cond.append(BANDERAS[b])

    return (" AND ".join(cond) if cond else "TRUE"), p


# FROM para filtrar: sin las uniones a cartera/activos de TX_FROM (pueden
# repetir filas); `b` trae el conteo de "iguales" para el aviso de duplicado.
_FROM_FILTRO = """
    FROM transactions t
    JOIN portfolios p ON p.id = t.portfolio_id
    JOIN base b ON b.id = t.id
    LEFT JOIN third_parties tp ON tp.id = t.third_party_id
    LEFT JOIN user_accounts a ON a.id = t.account_id
    LEFT JOIN user_accounts da ON da.id = t.dest_account_id
"""

# Posible duplicado = misma empresa, fecha, tipo, valor neto y cuenta.
_BASE = """
base AS (
    SELECT t.id,
           COUNT(*) OVER (PARTITION BY t.portfolio_id, t.transaction_date, upper(t.type),
                                       COALESCE(t.net_value, 0), COALESCE(t.account_id, 0))::int AS n_iguales
    FROM transactions t
)"""

_SUMAS = """
      COUNT(*)::int AS n,
      COALESCE(SUM(CASE WHEN upper(t.type) = 'INGRESO' AND t.transaction_currency IS DISTINCT FROM 'USD' THEN COALESCE(t.net_value, 0) END), 0)::float8 AS ingresos_cop,
      COALESCE(SUM(CASE WHEN upper(t.type) = 'GASTO'   AND t.transaction_currency IS DISTINCT FROM 'USD' THEN COALESCE(t.net_value, 0) END), 0)::float8 AS gastos_cop,
      COALESCE(SUM(CASE WHEN upper(t.type) = 'TRANSFERENCIA' AND t.transaction_currency IS DISTINCT FROM 'USD' THEN COALESCE(t.amount, 0) END), 0)::float8 AS transferencias_cop,
      COALESCE(SUM(CASE WHEN upper(t.type) = 'INGRESO' AND t.transaction_currency = 'USD' THEN COALESCE(t.net_value, 0) END), 0)::float8 AS ingresos_usd,
      COALESCE(SUM(CASE WHEN upper(t.type) = 'GASTO'   AND t.transaction_currency = 'USD' THEN COALESCE(t.net_value, 0) END), 0)::float8 AS gastos_usd"""


def armar_sql(where: str, orden: str, agrupar: Optional[str]) -> str:
    if orden not in ORDENES:
        raise ValueError(f"Orden inválido: '{orden}'")
    if agrupar and agrupar not in GRUPOS:
        raise ValueError(f"Agrupación inválida: '{agrupar}'")

    grupos_cte = ""
    grupos_col = "NULL::json AS grupos"
    if agrupar:
        join = _JOIN_ETIQUETA if agrupar == "etiqueta" else ""
        grupos_cte = f""",
grupos AS (
    SELECT {GRUPOS[agrupar]} AS clave,
           {_REF_GRUPO.get(agrupar, "NULL::bigint")} AS ref,
           {_SUMAS}
    FROM transactions t
    JOIN portfolios p ON p.id = t.portfolio_id
    LEFT JOIN third_parties tp ON tp.id = t.third_party_id
    LEFT JOIN user_accounts a ON a.id = t.account_id
    {join}
    WHERE t.id IN (SELECT id FROM ids)
    GROUP BY 1
)"""
        orden_grupo = "g.clave DESC" if agrupar == "mes" else "(g.ingresos_cop + g.gastos_cop) DESC, g.clave"
        grupos_col = (f"(SELECT COALESCE(json_agg(row_to_json(g) ORDER BY {orden_grupo}), '[]'::json) "
                      f"FROM grupos g) AS grupos")

    return f"""
WITH {_BASE},
ids AS (
    SELECT t.id {_FROM_FILTRO}
    WHERE {where}
),
pagina AS (
    SELECT {TX_SELECT_LIST}, b.n_iguales,
           row_number() OVER (ORDER BY {ORDENES[orden]}) AS _pos
    {TX_FROM}
    JOIN base b ON b.id = t.id
    WHERE t.id IN (SELECT id FROM ids)
    ORDER BY {ORDENES[orden]}
    LIMIT %(limit)s OFFSET %(offset)s
),
totales AS (
    SELECT {_SUMAS}
    FROM transactions t
    WHERE t.id IN (SELECT id FROM ids)
){grupos_cte}
SELECT
  (SELECT COALESCE(json_agg(row_to_json(x) ORDER BY x._pos), '[]'::json) FROM pagina x) AS transactions,
  (SELECT row_to_json(s) FROM totales s) AS totales,
  {grupos_col};
"""


def buscar_movimientos(filtros: Dict[str, Any], orden: str = "fecha_desc",
                       agrupar: Optional[str] = None, limit: int = 50,
                       offset: int = 0) -> Dict[str, Any]:
    """Página + totales (+ grupos) de lo filtrado. ValueError si algo no vale."""
    limit = max(0, min(int(limit), LIMITE_MAX))
    offset = max(0, int(offset))
    where, params = construir_filtros(filtros)
    sql = armar_sql(where, orden, agrupar)
    params.update(limit=limit, offset=offset)

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            fila = cur.fetchone() or {}
    finally:
        put_conn(conn)

    txs = fila.get("transactions") or []
    for tx in txs:
        tx.pop("_pos", None)
    tot = fila.get("totales") or {}
    tot["neto_cop"] = round(float(tot.get("ingresos_cop", 0)) - float(tot.get("gastos_cop", 0)), 2)
    tot["neto_usd"] = round(float(tot.get("ingresos_usd", 0)) - float(tot.get("gastos_usd", 0)), 2)
    return {
        "transactions": txs,
        "total": int(tot.get("n", 0)),
        "totales": tot,
        "grupos": fila.get("grupos"),
        "orden": orden,
        "agrupar": agrupar,
    }


_OPCIONES_SQL = """
WITH tx AS (
    SELECT t.* FROM transactions t JOIN portfolios p ON p.id = t.portfolio_id
    WHERE cardinality(%(empresas)s::text[]) = 0 OR p.name = ANY(%(empresas)s)
)
SELECT
  (SELECT COALESCE(json_agg(json_build_object('id', tp.id, 'name', tp.name,
                   'ident', tp.identification_number, 'n', x.n) ORDER BY tp.name), '[]'::json)
     FROM (SELECT third_party_id, COUNT(*) n FROM tx WHERE third_party_id IS NOT NULL GROUP BY 1) x
     JOIN third_parties tp ON tp.id = x.third_party_id)                                   AS terceros,
  (SELECT COALESCE(json_agg(json_build_object('id', a.id, 'name', a.name, 'n', x.n) ORDER BY a.name), '[]'::json)
     FROM (SELECT cid, COUNT(*) n FROM (SELECT account_id cid FROM tx UNION ALL
                                        SELECT dest_account_id FROM tx) u
            WHERE cid IS NOT NULL GROUP BY 1) x
     JOIN user_accounts a ON a.id = x.cid)                                                 AS cuentas,
  (SELECT COALESCE(json_agg(json_build_object('valor', category, 'n', n) ORDER BY category), '[]'::json)
     FROM (SELECT category, COUNT(*) n FROM tx WHERE COALESCE(category, '') <> '' GROUP BY 1) x) AS categorias,
  (SELECT COALESCE(json_agg(json_build_object('valor', e, 'n', n) ORDER BY e), '[]'::json)
     FROM (SELECT e, COUNT(*) n FROM tx, unnest(tx.tags) e GROUP BY 1) x)                  AS etiquetas,
  (SELECT COALESCE(json_agg(json_build_object('id', id, 'valor', name) ORDER BY id), '[]'::json)
     FROM portfolios)                                                                      AS empresas,
  (SELECT json_build_object('min', MIN(transaction_date), 'max', MAX(transaction_date)) FROM tx) AS fechas;
"""


def opciones_filtros(empresas: List[str]) -> Dict[str, Any]:
    """Valores que EXISTEN en las empresas elegidas, con su conteo, para
    llenar los selectores (no se ofrecen opciones que darían 0 filas)."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_OPCIONES_SQL, {"empresas": list(empresas or [])})
            return dict(cur.fetchone() or {})
    finally:
        put_conn(conn)
