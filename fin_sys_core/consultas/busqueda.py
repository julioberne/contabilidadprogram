# -*- coding: utf-8 -*-
"""Búsqueda remota única (estándar de consultas, hito H3 — reglas F1/F2, B1).

Un solo contrato para todos los selectores (web, Mini App de Telegram y bot):
el servidor devuelve como mucho `limite` resultados (top-N) y `mas=True` si
hay más ("escribe más para afinar"). Nunca el catálogo completo.

Escalera por largo de la búsqueda (texto normalizado, sin tildes):
    0 caracteres → los más usados (recientes/frecuentes)
    1 carácter   → nombre que EMPIEZA por esa letra, o documento exacto
    2+           → nombre que CONTIENE el texto; si trae dígitos (≥3), también
                   documento o celular que los contienen
Orden: documento exacto, nombre que empieza, nombre que contiene; dentro de
cada grupo, los más usados primero y luego por nombre.

"Usado" = en las últimas VENTANA_USO transacciones (se leen por la llave
primaria): la búsqueda cuesta lo mismo con 1.000 que con 5 millones de TX.
Antes agrupaba TODAS las transacciones en cada tecla (16-oct-2026).

`ids` / `ident` resuelven fichas concretas (el tercero asignado, chips ya
elegidos) sin buscar. Solo lectura, con SET LOCAL statement_timeout.
"""
import re
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor

from fin_sys_core.db_pool import get_conn, put_conn

LIMITE_DEFECTO = 8
LIMITE_MAX = 50
TIMEOUT_MS = 2000
MAX_IDS = 100
VENTANA_USO = 2000      # últimas transacciones que cuentan como "uso" de un tercero

_CON_TILDE = "áéíóúüàèìòùäëïöâêîôûñ"
_SIN_TILDE = "aeiouuaeiouaeioaeioun"
COLUMNAS_TERCERO = "tp.id, tp.identification_type, tp.identification_number, tp.name, tp.email, tp.phone, tp.website, tp.address"


def normalizar(texto: str) -> str:
    return (texto or "").strip().lower().translate(str.maketrans(_CON_TILDE, _SIN_TILDE))


def digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def _sql_norm(col: str) -> str:
    return f"translate(lower(COALESCE({col}, '')), '{_CON_TILDE}', '{_SIN_TILDE}')"


def _like_seguro(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _limite(limite) -> int:
    try:
        n = int(limite)
    except (TypeError, ValueError):
        n = LIMITE_DEFECTO
    return max(1, min(n, LIMITE_MAX))


def _ids(valor) -> List[int]:
    if not valor:
        return []
    partes = valor.split(",") if isinstance(valor, str) else list(valor)
    out = []
    for p in partes:
        p = str(p).strip()
        if not p:
            continue
        if not re.fullmatch(r"\d+", p):
            raise ValueError(f"Identificador inválido: '{p}'")
        out.append(int(p))
    if len(out) > MAX_IDS:
        raise ValueError(f"Máximo {MAX_IDS} identificadores por consulta")
    return out


def nombre_exacto(nombre: str) -> str:
    """Como el índice lower(btrim(name)) de third_parties, con espacios colapsados."""
    return re.sub(r"\s+", " ", (nombre or "").strip().lower())


def _uso(unir: str = "LEFT JOIN") -> str:
    """Uso de cada tercero en las últimas VENTANA_USO transacciones (parámetro
    %(ventana)s): n, fecha más reciente y última TX registrada."""
    return (f"{unir} (SELECT third_party_id, COUNT(*) AS n, MAX(transaction_date) AS ultima, "
            "MAX(id) AS ultimo FROM (SELECT id, third_party_id, transaction_date FROM transactions "
            "WHERE third_party_id IS NOT NULL ORDER BY id DESC LIMIT %(ventana)s) v GROUP BY 1) u "
            "ON u.third_party_id = tp.id")


def armar_recientes(limite: int, excluir_ident: Optional[str] = None, columnas: str = COLUMNAS_TERCERO):
    """(sql, params) de los terceros de las últimas VENTANA_USO transacciones, el
    último registrado primero. Lo usan el selector vacío (web, Mini App) y
    «👤 Tercero» del bot (que excluye el genérico)."""
    p: Dict[str, Any] = {"lim": _limite(limite) + 1, "ventana": VENTANA_USO}
    filtro = ""
    if excluir_ident:
        p["excluir"] = excluir_ident
        filtro = "WHERE tp.identification_number <> %(excluir)s "
    return (f"SELECT {columnas}, u.n AS usos FROM third_parties tp {_uso('JOIN')} "
            f"{filtro}ORDER BY u.ultimo DESC LIMIT %(lim)s"), p


def armar_busqueda_terceros(q: str, limite: int, ids=None, ident: Optional[str] = None,
                            nombre: Optional[str] = None, despues: Optional[tuple] = None,
                            orden: str = "relevancia", con_total: bool = False):
    """(sql, params) puros, para poder probarlos sin BD.

    nombre: coincidencia EXACTA del nombre (detector de duplicados del registro).
    orden='nombre' + despues=(nombre, id) + con_total: listado paginado por CURSOR
    (regla B3: sin OFFSET; cada página cuesta lo mismo aunque sea la número 1.000)."""
    lim = _limite(limite)
    lista_ids = _ids(ids)
    if orden not in ("relevancia", "nombre"):
        raise ValueError(f"Orden inválido: '{orden}'")
    # Fichas concretas y listados por nombre no necesitan el uso: 0 AS usos.
    if nombre and not (lista_ids or ident):
        p = {"nombre": nombre_exacto(nombre), "lim": lim + 1}
        return (f"SELECT {COLUMNAS_TERCERO}, 0 AS usos FROM third_parties tp "
                "WHERE lower(btrim(tp.name)) = %(nombre)s ORDER BY tp.id LIMIT %(lim)s"), p
    if lista_ids or ident:
        cond, p = [], {}
        if lista_ids:
            cond.append("tp.id = ANY(%(ids)s)")
            p["ids"] = lista_ids
        if ident:
            cond.append("tp.identification_number = %(ident)s")
            p["ident"] = ident.strip()
        p["lim"] = max(lim, len(lista_ids)) + 1
        return (f"SELECT {COLUMNAS_TERCERO}, 0 AS usos FROM third_parties tp "
                f"WHERE {' OR '.join(cond)} ORDER BY tp.name LIMIT %(lim)s"), p

    texto = normalizar(q)
    dig = digitos(q)
    p: Dict[str, Any] = {"lim": lim + 1}
    total = ", COUNT(*) OVER () AS _total" if con_total else ""
    if orden == "nombre":
        # Listado paginado y estable (nombre, id) para el panel de gestión.
        conds = []
        if texto:
            p["contiene"] = "%" + _like_seguro(texto) + "%"
            p["exacto"] = q.strip()
            conds.append(f"({_sql_norm('tp.name')} LIKE %(contiene)s OR tp.identification_number = %(exacto)s)")
        filtro = " AND ".join(conds) or "TRUE"
        cursor = filtro
        if despues:
            p["c_nombre"], p["c_id"] = str(despues[0]), int(despues[1])
            cursor = f"{filtro} AND (tp.name, tp.id) > (%(c_nombre)s, %(c_id)s)"
        if con_total:
            # El total cuenta TODO lo filtrado (no solo desde el cursor).
            total = f", (SELECT COUNT(*) FROM third_parties tp WHERE {filtro}) AS _total"
        return (f"SELECT {COLUMNAS_TERCERO}, 0 AS usos{total} FROM third_parties tp "
                f"WHERE {cursor} ORDER BY tp.name, tp.id LIMIT %(lim)s"), p
    if not texto:
        # Los recientes: con 50.000 terceros, nadie quiere el catálogo entero.
        # buscar_terceros completa por nombre si la ventana trae pocos.
        return armar_recientes(limite)

    nombre = _sql_norm("tp.name")
    p["exacto"] = q.strip()
    p["ventana"] = VENTANA_USO
    if len(texto) == 1:
        p["prefijo"] = _like_seguro(texto) + "%"
        cond = f"({nombre} LIKE %(prefijo)s OR tp.identification_number = %(exacto)s)"
    else:
        p["prefijo"] = _like_seguro(texto) + "%"
        p["contiene"] = "%" + _like_seguro(texto) + "%"
        partes = [f"{nombre} LIKE %(contiene)s", "tp.identification_number = %(exacto)s"]
        if len(dig) >= 3:
            p["dig"] = "%" + dig + "%"
            partes.append("regexp_replace(COALESCE(tp.identification_number, ''), '\\D', '', 'g') LIKE %(dig)s")
            partes.append("regexp_replace(COALESCE(tp.phone, ''), '\\D', '', 'g') LIKE %(dig)s")
        cond = "(" + " OR ".join(partes) + ")"
    orden = (f"CASE WHEN tp.identification_number = %(exacto)s THEN 0 "
             f"WHEN {nombre} LIKE %(prefijo)s THEN 1 ELSE 2 END, "
             "COALESCE(u.n, 0) DESC, tp.name")
    return (f"SELECT {COLUMNAS_TERCERO}, COALESCE(u.n, 0) AS usos FROM third_parties tp {_uso()} "
            f"WHERE {cond} ORDER BY {orden} LIMIT %(lim)s"), p


def _ejecutar(sql: str, params: dict) -> List[dict]:
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = %s", (f"{TIMEOUT_MS}ms",))
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        put_conn(conn)


def _respuesta(filas: List[dict], limite: int, q: str) -> dict:
    lim = _limite(limite)
    return {"items": filas[:lim], "mas": len(filas) > lim, "q": q or "", "limite": lim}


def buscar_terceros(q: str = "", limite=LIMITE_DEFECTO, ids=None, ident: Optional[str] = None,
                    nombre: Optional[str] = None, despues: Optional[tuple] = None,
                    orden: str = "relevancia", con_total: bool = False) -> dict:
    sql, p = armar_busqueda_terceros(q, limite, ids, ident, nombre, despues, orden, con_total)
    filas = _ejecutar(sql, p)
    if "ventana" in p and "exacto" not in p and len(filas) < p["lim"]:
        # Caja vacía con pocos recientes (empresa nueva): se completa por nombre.
        ya = [f["id"] for f in filas]
        filas += _ejecutar(f"SELECT {COLUMNAS_TERCERO}, 0 AS usos FROM third_parties tp "
                           "WHERE tp.id <> ALL(%(ya)s) ORDER BY tp.name LIMIT %(faltan)s",
                           {"ya": ya, "faltan": p["lim"] - len(filas)})
    if ids or ident or nombre:
        return {"items": filas, "mas": False, "q": "", "limite": len(filas)}
    total = filas[0].get("_total") if (con_total and filas) else (0 if con_total else None)
    for f in filas:
        f.pop("_total", None)
    r = _respuesta(filas, limite, q)
    if con_total:
        r["total"] = int(total or 0)
        ultimo = r["items"][-1] if r["items"] else None
        r["siguiente"] = {"nombre": ultimo["name"], "id": ultimo["id"]} if (ultimo and r["mas"]) else None
    return r


def buscar_cuentas(q: str = "", limite=LIMITE_DEFECTO, ids=None) -> dict:
    lim = _limite(limite)
    lista_ids = _ids(ids)
    if lista_ids:
        filas = _ejecutar("SELECT id, name, type, currency FROM user_accounts WHERE id = ANY(%(ids)s) ORDER BY name",
                          {"ids": lista_ids})
        return {"items": filas, "mas": False, "q": "", "limite": len(filas)}
    texto = normalizar(q)
    p = {"lim": lim + 1, "contiene": "%" + _like_seguro(texto) + "%"}
    filas = _ejecutar(f"SELECT id, name, type, currency FROM user_accounts WHERE {_sql_norm('name')} LIKE %(contiene)s "
                      "ORDER BY name LIMIT %(lim)s", p)
    return _respuesta(filas, lim, q)


def buscar_etiquetas(q: str = "", limite=LIMITE_DEFECTO) -> dict:
    lim = _limite(limite)
    texto = normalizar(q)
    p = {"lim": lim + 1, "contiene": "%" + _like_seguro(texto) + "%"}
    filas = _ejecutar(f"SELECT * FROM tag_definitions WHERE {_sql_norm('name')} LIKE %(contiene)s "
                      "ORDER BY name LIMIT %(lim)s", p)
    return _respuesta(filas, lim, q)
