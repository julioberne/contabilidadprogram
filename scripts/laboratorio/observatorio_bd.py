# -*- coding: utf-8 -*-
"""Observatorio de la BD (laboratorio de rendimiento, criterios 3 y 4).

SOLO LECTURA. Cada consulta corre con `SET LOCAL statement_timeout` (10 s) y
la transacción se descarta con ROLLBACK. Sirve contra la BD compartida
(producción): no escribe nada ni crea objetos.

Mide:
- pg_stat_statements: lo que más tiempo total y medio consume.
- Tablas: filas, tamaño, recorridos completos (seq_scan) vs por índice.
- Índices que nunca se usan; cache hit ratio.
- Conexiones por estado y usuario; bloqueos en espera; consultas largas.
- EXPLAIN ANALYZE de las consultas estándar (Diario, panel): tiempo y si
  recorren tablas enteras (Seq Scan) — lo que crece con el holding.

    python scripts/laboratorio/observatorio_bd.py            # resumen legible
    python scripts/laboratorio/observatorio_bd.py --json
"""
import argparse
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

TIMEOUT_MS = 10000


def _consulta(conn, sql, params=None):
    cur = conn.cursor()
    try:
        cur.execute("SET LOCAL statement_timeout = %s", (f"{TIMEOUT_MS}ms",))
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, fila)) for fila in cur.fetchall()]
    finally:
        cur.close()
        conn.rollback()


def _seguro(conn, sql, params=None):
    try:
        return _consulta(conn, sql, params)
    except Exception as e:                       # p. ej. sin permiso a pg_stat_statements
        conn.rollback()
        return {"error": str(e).split("\n")[0][:200]}


def top_sentencias(conn, n=10):
    return _seguro(conn, """
        SELECT left(regexp_replace(query, '\\s+', ' ', 'g'), 140) AS consulta,
               calls AS llamadas, round(total_exec_time::numeric, 0) AS total_ms,
               round(mean_exec_time::numeric, 1) AS media_ms, round(max_exec_time::numeric, 0) AS max_ms,
               rows AS filas
        FROM pg_stat_statements
        WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
          AND query NOT ILIKE '%%pg_stat_statements%%'
        ORDER BY total_exec_time DESC LIMIT %s""", (n,))


def tablas(conn):
    return _seguro(conn, """
        SELECT relname AS tabla, n_live_tup AS filas,
               pg_total_relation_size(relid) AS bytes,
               seq_scan AS recorridos_completos, COALESCE(seq_tup_read, 0) AS filas_leidas_en_recorridos,
               COALESCE(idx_scan, 0) AS por_indice
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(relid) DESC LIMIT 15""")


def indices_sin_uso(conn):
    return _seguro(conn, """
        SELECT s.relname AS tabla, s.indexrelname AS indice, pg_relation_size(s.indexrelid) AS bytes
        FROM pg_stat_user_indexes s JOIN pg_index i ON i.indexrelid = s.indexrelid
        WHERE s.schemaname = 'public' AND s.idx_scan = 0 AND NOT i.indisunique AND NOT i.indisprimary
        ORDER BY pg_relation_size(s.indexrelid) DESC LIMIT 15""")


def cache_hit(conn):
    filas = _seguro(conn, """
        SELECT COALESCE(round(100.0 * sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0), 2), 100)
               AS porcentaje FROM pg_statio_user_tables""")
    return filas[0]["porcentaje"] if isinstance(filas, list) and filas else None


def conexiones(conn):
    return _seguro(conn, """
        SELECT usename AS usuario, COALESCE(state, '(fondo)') AS estado, COUNT(*) AS n,
               COALESCE(max(EXTRACT(EPOCH FROM now() - query_start))::int, 0) AS max_s
        FROM pg_stat_activity WHERE datname = current_database()
        GROUP BY 1, 2 ORDER BY 3 DESC""")


def limites(conn):
    filas = _seguro(conn, """SELECT current_setting('server_version') AS version,
                                    current_setting('max_connections')::int AS max_connections,
                                    (SELECT COUNT(*) FROM pg_stat_activity) AS conexiones_abiertas,
                                    (SELECT COUNT(*) FROM pg_locks WHERE NOT granted) AS bloqueos_en_espera,
                                    (SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'
                                       AND now() - query_start > interval '5 seconds') AS consultas_largas""")
    return filas[0] if isinstance(filas, list) and filas else filas


def _recorrer_plan(nodo, salida):
    if nodo.get("Node Type") == "Seq Scan":
        salida.append({"tabla": nodo.get("Relation Name"), "filas": nodo.get("Actual Rows"),
                       "filas_plan": nodo.get("Plan Rows")})
    for hijo in nodo.get("Plans", []) or []:
        _recorrer_plan(hijo, salida)


def explicar(conn, nombre, sql, params):
    cur = conn.cursor()
    try:
        cur.execute("SET LOCAL statement_timeout = %s", (f"{TIMEOUT_MS}ms",))
        t0 = time.perf_counter()
        cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, params)
        plan = cur.fetchone()[0][0]
        ms_cliente = (time.perf_counter() - t0) * 1000
        seq = []
        _recorrer_plan(plan["Plan"], seq)
        return {"consulta": nombre, "ejecucion_ms": round(plan.get("Execution Time", 0), 1),
                "planificacion_ms": round(plan.get("Planning Time", 0), 1),
                "ida_y_vuelta_ms": round(ms_cliente, 1), "seq_scans": seq}
    except Exception as e:
        conn.rollback()
        return {"consulta": nombre, "error": str(e).split("\n")[0][:200]}
    finally:
        cur.close()
        conn.rollback()


def consultas_estandar(conn):
    """EXPLAIN ANALYZE de las consultas que el estándar vigila, sobre la
    empresa con más transacciones (el peor caso real de hoy)."""
    from fin_sys_core.diario_query import armar_sql, construir_filtros
    filas = _seguro(conn, """SELECT p.name, COUNT(*) n FROM transactions t JOIN portfolios p ON p.id = t.portfolio_id
                             GROUP BY 1 ORDER BY 2 DESC LIMIT 1""")
    if not isinstance(filas, list) or not filas:
        return {"empresa": None, "planes": []}
    empresa = filas[0]["name"]
    casos = [
        ("diario_pagina", {"empresas": [empresa]}, "fecha_desc", None),
        ("diario_busqueda", {"empresas": [empresa], "q": "pago"}, "fecha_desc", None),
        ("diario_filtros", {"empresas": [empresa], "tipos": "GASTO", "monto_min": "1000"}, "monto_desc", None),
        ("diario_grupos_tercero", {"empresas": [empresa]}, "fecha_desc", "tercero"),
    ]
    planes = []
    for nombre, filtros, orden, agrupar in casos:
        where, params = construir_filtros(filtros)
        params.update(limit=50, offset=0)
        planes.append(explicar(conn, nombre, armar_sql(where, orden, agrupar), params))
    try:
        from fin_sys_core.dashboard_query import _SNAPSHOT_SQL
        planes.append(explicar(conn, "panel_snapshot", _SNAPSHOT_SQL,
                               {"portfolio": empresa, "limit": 50, "offset": 0}))
    except Exception as e:
        planes.append({"consulta": "panel_snapshot", "error": str(e)[:200]})
    return {"empresa": empresa, "transacciones_empresa": filas[0]["n"], "planes": planes}


def observar() -> dict:
    import fin_sys_core  # noqa: F401  (alias de drivers + pool)
    from fin_sys_core.db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        return {"limites": limites(conn), "cache_hit_pct": cache_hit(conn), "conexiones": conexiones(conn),
                "tablas": tablas(conn), "indices_sin_uso": indices_sin_uso(conn),
                "top_sentencias": top_sentencias(conn), "estandar": consultas_estandar(conn)}
    finally:
        put_conn(conn)


def _mb(b):
    return f"{(b or 0) / 1048576:.1f} MB"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    d = observar()
    if args.json:
        print(json.dumps(d, ensure_ascii=False, default=str))
        return 0
    print("── Límites:", d["limites"], "· cache hit:", d["cache_hit_pct"], "%")
    print("── Tablas más grandes (filas · tamaño · recorridos completos / por índice)")
    for t in (d["tablas"] if isinstance(d["tablas"], list) else []):
        print(f"   {t['tabla']:32} {t['filas']:>8} · {_mb(t['bytes']):>9} · {t['recorridos_completos']:>7} / {t['por_indice']}")
    print("── Consultas estándar sobre", d["estandar"].get("empresa"))
    for p in d["estandar"]["planes"]:
        if "error" in p:
            print(f"   {p['consulta']:24} ERROR {p['error']}")
            continue
        seq = ", ".join(f"{s['tabla']}({s['filas']})" for s in p["seq_scans"]) or "—"
        print(f"   {p['consulta']:24} {p['ejecucion_ms']:>7} ms  seq scans: {seq}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
