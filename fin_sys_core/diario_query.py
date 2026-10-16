# -*- coding: utf-8 -*-
"""diario_query.py — Búsqueda, filtros, orden, totales y grupos del Libro
Diario (Módulo 02) en el SERVIDOR.

Pedido de Andrés (16-oct-2026): el Diario carga de 50 en 50, así que un
filtro en el navegador solo vería lo cargado y los totales mentirían. Aquí
todo se resuelve en UNA sentencia (CTEs → una fila de columnas JSON, el
mismo patrón de dashboard_query.py).

Estándar de consultas, hito H4 (16-oct-2026): el costo sigue a lo pedido.
  · Solo la página (sin totales ni grupos, p. ej. «cargar más»): ORDER BY +
    LIMIT directos sobre transactions; en orden por fecha con CURSOR
    (despues_fecha/despues_id), así la página 1.000 cuesta lo que la 1 (B3).
  · Primera página: lo filtrado se lee UNA vez (`filtradas`) y de ahí salen
    página, totales y grupos (antes se releía transactions tres veces).
  · Posible duplicado: se compara fila por fila con su empresa y fecha,
    solo para las filas de la página (antes, una ventana sobre TODAS las
    transacciones de TODAS las empresas en cada petición).
  · Búsqueda por largo (B8): 1 letra no busca, 2 = palabras que empiezan
    así, 3+ = contiene. «#id» y montos valen siempre.
  · Opciones top-50 por lista con `mas` y búsqueda en el servidor (B10).
  · Cupo por worker (P4): DIARIO_SIMULTANEAS consultas a la vez; la
    siguiente espera DIARIO_ESPERA_S y, si no hay cupo, DiarioOcupado → 503.

`construir_filtros` y `armar_sql` son puros (sin BD) para probarlos en el CI.
Los avisos son informativos: nada aquí bloquea ni modifica datos.
"""
import os
import re
import threading
from contextlib import contextmanager
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
# Los mismos órdenes sobre las filas ya filtradas (alias f).
_ORDENES_F = {
    "fecha_desc":   "f.transaction_date DESC, f.id DESC",
    "fecha_asc":    "f.transaction_date ASC, f.id ASC",
    "monto_desc":   "COALESCE(f.net_value, 0) DESC, f.id DESC",
    "monto_asc":    "COALESCE(f.net_value, 0) ASC, f.id ASC",
    "tercero_asc":  "f.tp_name ASC NULLS LAST, f.transaction_date DESC, f.id DESC",
    "concepto_asc": "f.concept ASC NULLS LAST, f.id DESC",
}
ORDENES_CURSOR = ("fecha_desc", "fecha_asc")   # los que paginan por cursor

# Agrupación → expresión de la clave sobre las filas filtradas (alias f). La
# etiqueta despliega el arreglo: una TX con 2 etiquetas suma en las dos (se
# avisa en la interfaz).
GRUPOS = {
    "tercero":   "COALESCE(f.tp_name, '(sin tercero)')",
    "categoria": "COALESCE(NULLIF(f.category, ''), '(sin categoría)')",
    "mes":       "to_char(f.transaction_date, 'YYYY-MM')",
    "cuenta":    "COALESCE(f.a_name, NULLIF(f.payment_method, ''), '(sin cuenta)')",
    "etiqueta":  "g.etiqueta",
    "tipo":      "upper(f.type)",
    "empresa":   "f.p_name",
}
# `ref` = id para convertir el grupo en filtro con un clic (tercero / cuenta).
_REF_GRUPO = {"tercero": "MIN(f.third_party_id)", "cuenta": "MIN(f.account_id)"}
_JOIN_ETIQUETA = ("CROSS JOIN LATERAL unnest(CASE WHEN COALESCE(cardinality(f.tags), 0) = 0 "
                  "THEN ARRAY['(sin etiqueta)']::text[] ELSE f.tags END) AS g(etiqueta)")

# Posible duplicado = misma empresa, fecha, tipo, valor neto y cuenta. Se
# compara fila por fila (lo sirve el índice de empresa/fecha), nunca con una
# ventana sobre TODAS las transacciones (lo que hacía el CTE `base` hasta H4).
_MISMO = ("t2.portfolio_id = t.portfolio_id AND t2.transaction_date = t.transaction_date "
          "AND upper(t2.type) = upper(t.type) AND COALESCE(t2.net_value, 0) = COALESCE(t.net_value, 0) "
          "AND COALESCE(t2.account_id, 0) = COALESCE(t.account_id, 0)")
_N_IGUALES = f"(SELECT COUNT(*) FROM transactions t2 WHERE {_MISMO})::int"

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
    "duplicados":    f"EXISTS (SELECT 1 FROM transactions t2 WHERE t2.id <> t.id AND {_MISMO})",
}

LIMITE_MAX = 5000      # tope por petición (exportar "todo lo filtrado")
OFFSET_MAX = 2000      # B3: más allá, afinar el filtro u ordenar por fecha (cursor)
TOPE_OPCIONES = 50     # B10: valores por lista en los selectores

# Tiempo máximo por sentencia (estándar de consultas P6). `SET LOCAL` vive solo
# dentro de la transacción y muere con el rollback de put_conn; probado por el
# pooler :6543 con scripts/probar_set_local.py (16-oct-2026). Una consulta que
# se pasa lanza psycopg2.errors.QueryCanceled → el router responde 503.
TIMEOUT_MOVIMIENTOS_MS = 5000
TIMEOUT_OPCIONES_MS = 3000

# Cupo del Diario por worker (P4): con un pool de 10, el Diario no puede
# quedarse con todo. La consulta que no consigue cupo en DIARIO_ESPERA_S → 503.
DIARIO_SIMULTANEAS = max(1, int(os.getenv("DIARIO_SIMULTANEAS", "3")))
DIARIO_ESPERA_S = float(os.getenv("DIARIO_ESPERA_S", "2"))
_cupo = threading.BoundedSemaphore(DIARIO_SIMULTANEAS)


class DiarioOcupado(Exception):
    """No hubo cupo para otra consulta del Diario en este worker (→ 503)."""


@contextmanager
def _con_cupo():
    if not _cupo.acquire(timeout=DIARIO_ESPERA_S):
        raise DiarioOcupado("El Diario está atendiendo muchas consultas a la vez. "
                            "Intenta de nuevo en unos segundos.")
    try:
        yield
    finally:
        _cupo.release()


def _con_timeout(cur, ms: int) -> None:
    cur.execute("SET LOCAL statement_timeout = %s", (f"{int(ms)}ms",))

# Búsqueda sin tildes ni mayúsculas ("cafe" encuentra "Café") sin depender de
# la extensión unaccent: translate() con las vocales acentuadas del español.
_CON_TILDE = "áéíóúüàèìòùäëïöâêîôûñ"
_SIN_TILDE = "aeiouuaeiouaeioaeioun"
_CAMPOS_Q = ["t.concept", "t.note", "tp.name", "tp.identification_number", "a.name",
             "da.name", "t.category", "t.payment_method", "p.name",
             "array_to_string(t.tags, ' ')"]


def sin_tildes(texto: str) -> str:
    return texto.lower().translate(str.maketrans(_CON_TILDE, _SIN_TILDE))


def _sql_sin_tildes(col: str) -> str:
    return f"translate(lower({col}), '{_CON_TILDE}', '{_SIN_TILDE}')"


def _like_seguro(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _patron_contiene(texto: str) -> str:
    """Valor de %(q)s: el texto sin tildes, con sus % y _ literales."""
    return "%" + _like_seguro(sin_tildes(texto)) + "%"


def _contiene_q(col: str) -> str:
    """La única búsqueda «contiene» del Diario (B6: desde 3 caracteres en los
    movimientos; en las listas de opciones, sobre lo ya agregado por empresa)."""
    return f"{_sql_sin_tildes(col)} LIKE %(q)s"


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


def aviso_busqueda(q: Optional[str]) -> Optional[str]:
    """Aviso informativo cuando la búsqueda es tan corta que no se aplica."""
    q = (q or "").strip()
    if not q or len(sin_tildes(q)) >= 2 or re.fullmatch(r"#\d+", q) or numero_de_busqueda(q) is not None:
        return None
    return "Escribe al menos 2 letras para buscar."


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
        texto = sin_tildes(q)
        partes: List[str] = []
        if len(texto) >= 3:
            p["q"] = _patron_contiene(q)
            partes += [_contiene_q(c) for c in _CAMPOS_Q]
        elif len(texto) == 2:
            # 2 letras: palabras que EMPIEZAN así (B8); «contiene» traería casi todo.
            p["q_palabra"] = r"\m" + re.escape(texto)
            partes += [f"{_sql_sin_tildes(c)} ~ %(q_palabra)s" for c in _CAMPOS_Q]
        m = re.fullmatch(r"#(\d+)", q)
        if m:
            partes.append("t.id = %(q_id)s")
            p["q_id"] = int(m.group(1))
        n = numero_de_busqueda(q)
        if n is not None:
            partes.append("t.net_value = %(q_num)s OR t.amount = %(q_num)s")
            p["q_num"] = n
        if partes:                       # 1 letra sola: no se busca (aviso_busqueda)
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
# repetir filas).
_FROM_FILTRO = """
    FROM transactions t
    JOIN portfolios p ON p.id = t.portfolio_id
    LEFT JOIN third_parties tp ON tp.id = t.third_party_id
    LEFT JOIN user_accounts a ON a.id = t.account_id
    LEFT JOIN user_accounts da ON da.id = t.dest_account_id
"""

# Lo que la página, los totales y los grupos necesitan de cada fila filtrada.
_COLS_FILTRADAS = ("t.id, t.type, t.transaction_currency, t.net_value, t.amount, t.transaction_date, "
                   "t.concept, t.category, t.payment_method, t.tags, t.third_party_id, t.account_id, "
                   "tp.name AS tp_name, a.name AS a_name, p.name AS p_name")


def _sumas(a: str) -> str:
    return f"""
      COUNT(*)::int AS n,
      COALESCE(SUM(CASE WHEN upper({a}.type) = 'INGRESO' AND {a}.transaction_currency IS DISTINCT FROM 'USD' THEN COALESCE({a}.net_value, 0) END), 0)::float8 AS ingresos_cop,
      COALESCE(SUM(CASE WHEN upper({a}.type) = 'GASTO'   AND {a}.transaction_currency IS DISTINCT FROM 'USD' THEN COALESCE({a}.net_value, 0) END), 0)::float8 AS gastos_cop,
      COALESCE(SUM(CASE WHEN upper({a}.type) = 'TRANSFERENCIA' AND {a}.transaction_currency IS DISTINCT FROM 'USD' THEN COALESCE({a}.amount, 0) END), 0)::float8 AS transferencias_cop,
      COALESCE(SUM(CASE WHEN upper({a}.type) = 'INGRESO' AND {a}.transaction_currency = 'USD' THEN COALESCE({a}.net_value, 0) END), 0)::float8 AS ingresos_usd,
      COALESCE(SUM(CASE WHEN upper({a}.type) = 'GASTO'   AND {a}.transaction_currency = 'USD' THEN COALESCE({a}.net_value, 0) END), 0)::float8 AS gastos_usd"""


# B3: OFFSET solo hasta OFFSET_MAX y en los órdenes sin cursor; por fecha va el cursor.
_LIMITE_PAGINA = "LIMIT %(limit)s OFFSET %(offset)s"


def _cursor(orden: str, alias: str) -> str:
    """Filas DESPUÉS de la última vista (%(k_fecha)s, %(k_id)s) en orden por fecha."""
    op = "<" if orden == "fecha_desc" else ">"
    return f"({alias}.transaction_date, {alias}.id) {op} (%(k_fecha)s::date, %(k_id)s)"


# La página: columnas del dashboard + aviso de duplicado, solo para sus filas.
_PAGINA = f"""
pagina AS (
    SELECT {TX_SELECT_LIST}, {_N_IGUALES} AS n_iguales, s._pos
    {TX_FROM}
    JOIN sel s ON s.id = t.id
)"""
_COL_PAGINA = ("(SELECT COALESCE(json_agg(row_to_json(x) ORDER BY x._pos), '[]'::json) "
               "FROM pagina x) AS transactions")


def armar_sql(where: str, orden: str, agrupar: Optional[str], totales: bool = True,
              cursor: bool = False) -> str:
    """SQL del Diario. Parámetros: los de construir_filtros + %(limit)s y
    %(offset)s (+ %(k_fecha)s y %(k_id)s con `cursor`)."""
    if orden not in ORDENES:
        raise ValueError(f"Orden inválido: '{orden}'")
    if agrupar and agrupar not in GRUPOS:
        raise ValueError(f"Agrupación inválida: '{agrupar}'")
    if cursor and orden not in ORDENES_CURSOR:
        raise ValueError("Continuar desde una fila solo vale con orden por fecha.")

    if not (totales or agrupar):
        # Solo la página: ORDER BY + LIMIT directos sobre transactions.
        extra = f" AND {_cursor(orden, 't')}" if cursor else ""
        return f"""
WITH sel AS (
    SELECT t.id, row_number() OVER (ORDER BY {ORDENES[orden]}) AS _pos
    {_FROM_FILTRO}
    WHERE ({where}){extra}
    ORDER BY {ORDENES[orden]}
    {_LIMITE_PAGINA}
),{_PAGINA}
SELECT {_COL_PAGINA}, NULL::json AS totales, NULL::json AS grupos;
"""

    grupos_cte = ""
    grupos_col = "NULL::json AS grupos"
    if agrupar:
        join = _JOIN_ETIQUETA if agrupar == "etiqueta" else ""
        grupos_cte = f""",
grupos AS (
    SELECT {GRUPOS[agrupar]} AS clave,
           {_REF_GRUPO.get(agrupar, "NULL::bigint")} AS ref,
           {_sumas("f")}
    FROM filtradas f
    {join}
    GROUP BY 1
)"""
        orden_grupo = "g.clave DESC" if agrupar == "mes" else "(g.ingresos_cop + g.gastos_cop) DESC, g.clave"
        grupos_col = (f"(SELECT COALESCE(json_agg(row_to_json(g) ORDER BY {orden_grupo}), '[]'::json) "
                      f"FROM grupos g) AS grupos")

    cond_sel = f"WHERE {_cursor(orden, 'f')}" if cursor else ""
    return f"""
WITH filtradas AS MATERIALIZED (
    SELECT {_COLS_FILTRADAS}
    {_FROM_FILTRO}
    WHERE {where}
),
sel AS (
    SELECT f.id, row_number() OVER (ORDER BY {_ORDENES_F[orden]}) AS _pos
    FROM filtradas f
    {cond_sel}
    ORDER BY {_ORDENES_F[orden]}
    {_LIMITE_PAGINA}
),{_PAGINA},
totales AS (
    SELECT {_sumas("f")}
    FROM filtradas f
){grupos_cte}
SELECT
  {_COL_PAGINA},
  (SELECT row_to_json(s) FROM totales s) AS totales,
  {grupos_col};
"""


def buscar_movimientos(filtros: Dict[str, Any], orden: str = "fecha_desc",
                       agrupar: Optional[str] = None, limit: int = 50,
                       offset: int = 0, totales: bool = True,
                       despues: Optional[Tuple[str, Any]] = None) -> Dict[str, Any]:
    """Página (+ totales y grupos) de lo filtrado. ValueError si algo no vale.

    totales=False → solo la página (más barata; «cargar más»).
    despues=(fecha, id) → continúa después de esa fila (solo orden por fecha).
    `siguiente` trae el cursor para la próxima página cuando el orden lo admite."""
    limit = max(0, min(int(limit), LIMITE_MAX))
    offset = max(0, int(offset))
    if offset > OFFSET_MAX:
        raise ValueError(f"Para ver más de {OFFSET_MAX} filas en este orden, afina el filtro "
                         "u ordena por fecha.")
    where, params = construir_filtros(filtros)
    cursor = bool(despues)
    sql = armar_sql(where, orden, agrupar, totales=totales, cursor=cursor)
    params.update(limit=limit, offset=offset)
    if cursor:
        if len(despues) != 2 or not despues[0] or despues[1] in (None, ""):
            raise ValueError("Para continuar hacen falta despues_fecha y despues_id.")
        params["k_fecha"] = _fecha(str(despues[0]), "despues_fecha")
        params["k_id"] = _enteros(str(despues[1]))[0]

    with _con_cupo():
        conn = get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                _con_timeout(cur, TIMEOUT_MOVIMIENTOS_MS)
                cur.execute(sql, params)
                fila = cur.fetchone() or {}
        finally:
            put_conn(conn)

    txs = fila.get("transactions") or []
    for tx in txs:
        tx.pop("_pos", None)
    tot = fila.get("totales")
    if tot is not None:
        tot["neto_cop"] = round(float(tot.get("ingresos_cop", 0)) - float(tot.get("gastos_cop", 0)), 2)
        tot["neto_usd"] = round(float(tot.get("ingresos_usd", 0)) - float(tot.get("gastos_usd", 0)), 2)
    siguiente = None
    if orden in ORDENES_CURSOR and limit and len(txs) == limit:
        ultima = txs[-1]
        siguiente = {"fecha": ultima.get("transaction_date"), "id": ultima.get("id")}
    return {
        "transactions": txs,
        "total": int(tot.get("n", 0)) if tot is not None else None,
        "totales": tot,
        "grupos": fila.get("grupos"),
        "orden": orden,
        "agrupar": agrupar,
        "siguiente": siguiente,
        "aviso": aviso_busqueda(filtros.get("q")),
    }


# Listas de los selectores: (agregado sobre `tx`, unión, objeto JSON, texto
# para buscar, orden de despliegue, condición de «ya elegido»).
_LISTAS = {
    "terceros": (
        "SELECT third_party_id AS k, COUNT(*) AS n FROM tx WHERE third_party_id IS NOT NULL GROUP BY 1",
        "JOIN third_parties tp ON tp.id = x.k",
        "json_build_object('id', tp.id, 'name', tp.name, 'ident', tp.identification_number, 'n', x.n)",
        f"({_contiene_q('tp.name')} OR {_contiene_q('tp.identification_number')})",
        "tp.name", "tp.id = ANY(%(sel_terceros)s::bigint[])"),
    "cuentas": (
        "SELECT cid AS k, COUNT(*) AS n FROM (SELECT account_id cid FROM tx UNION ALL "
        "SELECT dest_account_id FROM tx) u WHERE cid IS NOT NULL GROUP BY 1",
        "JOIN user_accounts a ON a.id = x.k",
        "json_build_object('id', a.id, 'name', a.name, 'n', x.n)",
        _contiene_q("a.name"),
        "a.name", "a.id = ANY(%(sel_cuentas)s::bigint[])"),
    "categorias": (
        "SELECT category AS k, COUNT(*) AS n FROM tx WHERE COALESCE(category, '') <> '' GROUP BY 1",
        "",
        "json_build_object('valor', x.k, 'n', x.n)",
        _contiene_q("x.k"),
        "x.k", "x.k = ANY(%(sel_categorias)s::text[])"),
    "etiquetas": (
        "SELECT e AS k, COUNT(*) AS n FROM tx, unnest(tx.tags) e GROUP BY 1",
        "",
        "json_build_object('valor', x.k, 'n', x.n)",
        _contiene_q("x.k"),
        "x.k", "x.k = ANY(%(sel_etiquetas)s::text[])"),
}
_ID_LISTA = {"terceros": "tp.id", "cuentas": "a.id", "categorias": "x.k", "etiquetas": "x.k"}


def armar_opciones(campo: Optional[str] = None, q: Optional[str] = None) -> str:
    """SQL de las opciones: top TOPE_OPCIONES por uso en cada lista (+ lo ya
    elegido, para que los chips tengan nombre) y `mas` por lista. Con `campo`
    solo esa lista, filtrada por `q` (búsqueda del selector en el servidor)."""
    if campo and campo not in _LISTAS:
        raise ValueError(f"Lista inválida: '{campo}'")
    nombres = [campo] if campo else list(_LISTAS)
    ctes, cols, mas = [], [], []
    for nom in nombres:
        agg, union, objeto, texto, orden, elegido = _LISTAS[nom]
        filtro = texto if (campo and q) else "TRUE"
        ctes.append(f"""c_{nom} AS (
    SELECT {objeto} AS item, {orden} AS _orden,
           row_number() OVER (ORDER BY x.n DESC, {orden}, {_ID_LISTA[nom]}) AS _rk,
           ({elegido}) AS _elegido
    FROM ({agg}) x {union}
    WHERE {filtro}
)""")
        cols.append(f"(SELECT COALESCE(json_agg(item ORDER BY _orden), '[]'::json) FROM c_{nom} "
                    f"WHERE _rk <= %(tope)s OR _elegido) AS {nom}")
        mas.append(f"'{nom}', (SELECT COUNT(*) > %(tope)s FROM c_{nom})")
    cols.append(f"json_build_object({', '.join(mas)}) AS mas")
    if not campo:
        cols.append("(SELECT COALESCE(json_agg(json_build_object('id', id, 'valor', name) ORDER BY id), "
                    "'[]'::json) FROM portfolios) AS empresas")
        cols.append("(SELECT json_build_object('min', MIN(transaction_date), 'max', MAX(transaction_date)) "
                    "FROM tx) AS fechas")
    return f"""
WITH tx AS (
    SELECT t.third_party_id, t.account_id, t.dest_account_id, t.category, t.tags, t.transaction_date
    FROM transactions t JOIN portfolios p ON p.id = t.portfolio_id
    WHERE cardinality(%(empresas)s::text[]) = 0 OR p.name = ANY(%(empresas)s)
),
{(',' + chr(10)).join(ctes)}
SELECT
  {(',' + chr(10) + '  ').join(cols)};
"""


def opciones_filtros(empresas: List[str], campo: Optional[str] = None, q: Optional[str] = None,
                     sel: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Valores que EXISTEN en las empresas elegidas, con su conteo, para
    llenar los selectores (no se ofrecen opciones que darían 0 filas). Los
    TOPE_OPCIONES más usados por lista; `mas[lista]` dice si hay más."""
    sel = sel or {}
    sql = armar_opciones(campo, (q or "").strip() or None)
    params = {
        "empresas": list(empresas or []), "tope": TOPE_OPCIONES,
        "q": _patron_contiene((q or "").strip()),
        "sel_terceros": _enteros(sel.get("terceros")), "sel_cuentas": _enteros(sel.get("cuentas")),
        "sel_categorias": _lista(sel.get("categorias")), "sel_etiquetas": _lista(sel.get("etiquetas")),
    }
    with _con_cupo():
        conn = get_conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                _con_timeout(cur, TIMEOUT_OPCIONES_MS)
                cur.execute(sql, params)
                return dict(cur.fetchone() or {})
        finally:
            put_conn(conn)
