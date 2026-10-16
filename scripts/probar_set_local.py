# -*- coding: utf-8 -*-
"""Hito H1 del estándar de consultas: ¿funciona `SET LOCAL statement_timeout`
a través del pooler de Supabase en modo transacción (:6543)?

SOLO LECTURA: no escribe nada en la BD. Lo único que hace es `SET LOCAL`
(vive dentro de la transacción y muere con su ROLLBACK) y `pg_sleep`.
No usa `SET` de sesión: en modo transacción se filtraría a otros clientes
que reciban la misma conexión del servidor.

Además imprime los valores reales que el plan necesita (versión, conexiones
máximas, timeouts por rol, conexiones abiertas por aplicación).

    .venv\\Scripts\\python.exe scripts\\probar_set_local.py
"""
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import tests  # noqa: F401,E402  (carga .env si existe)
import fin_sys_core  # noqa: F401,E402
from psycopg2 import errors  # noqa: E402

from fin_sys_core.db_pool import get_conn, put_conn  # noqa: E402


def _uno(cur, sql, params=None):
    cur.execute(sql, params)
    return cur.fetchone()[0]


def datos_reales(cur):
    print("── Valores reales de la BD")
    for nombre, sql in [
        ("versión", "SHOW server_version"),
        ("max_connections", "SHOW max_connections"),
        ("usuario", "SELECT current_user"),
        ("statement_timeout (rol actual)", "SHOW statement_timeout"),
        ("idle_in_transaction_session_timeout", "SHOW idle_in_transaction_session_timeout"),
        ("puerto del cliente (env DB_PORT)", None),
    ]:
        valor = os.getenv("DB_PORT") if sql is None else _uno(cur, sql)
        print(f"   {nombre:40} {valor}")
    cur.execute("""SELECT rolname, COALESCE(array_to_string(rolconfig, ', '), '—')
                   FROM pg_roles
                   WHERE rolname IN ('postgres','authenticated','anon','authenticator','service_role')
                      OR rolname LIKE 'finsys%%'
                   ORDER BY 1""")
    print("── Configuración por rol (rolconfig)")
    for rol, conf in cur.fetchall():
        print(f"   {rol:20} {conf}")
    cur.execute("""SELECT COALESCE(NULLIF(application_name, ''), '(sin nombre)'), usename, state, COUNT(*)
                   FROM pg_stat_activity WHERE datname = current_database()
                   GROUP BY 1, 2, 3 ORDER BY 4 DESC LIMIT 12""")
    print("── Conexiones abiertas ahora (aplicación, usuario, estado, n)")
    for fila in cur.fetchall():
        print("   ", " | ".join(str(x) for x in fila))


def prueba_set_local(conn):
    print("── Prueba 1: SET LOCAL statement_timeout = 200ms + pg_sleep(2)")
    cur = conn.cursor()
    t0 = time.perf_counter()
    try:
        cur.execute("SET LOCAL statement_timeout = '200ms'")
        cur.execute("SELECT pg_sleep(2)")
        conn.rollback()
        print(f"   ✗ NO se cortó (duró {time.perf_counter() - t0:.2f}s) → SET LOCAL no aplica por este puerto")
        return False
    except errors.QueryCanceled:
        conn.rollback()
        print(f"   ✓ cortada a los {time.perf_counter() - t0:.2f}s (QueryCanceled)")
        return True
    finally:
        cur.close()


def prueba_no_se_filtra(conn):
    print("── Prueba 2: la transacción siguiente NO hereda el timeout (pg_sleep 0.5s)")
    cur = conn.cursor()
    t0 = time.perf_counter()
    try:
        cur.execute("SELECT pg_sleep(0.5)")
        conn.rollback()
        print(f"   ✓ terminó normal en {time.perf_counter() - t0:.2f}s")
        return True
    except errors.QueryCanceled:
        conn.rollback()
        print("   ✗ se cortó: el SET LOCAL se filtró a la transacción siguiente")
        return False
    finally:
        cur.close()


def main():
    conn = get_conn()
    try:
        cur = conn.cursor()
        datos_reales(cur)
        conn.rollback()
        cur.close()
        ok1 = prueba_set_local(conn)
        ok2 = prueba_no_se_filtra(conn)
    finally:
        put_conn(conn)
    veredicto = ok1 and ok2
    print("── Veredicto:", "SET LOCAL sirve por este puerto (P6 sin roles nuevos)" if veredicto
          else "usar timeouts por ROL de Postgres (P5) — los roles suben a H2")
    return 0 if veredicto else 1


if __name__ == "__main__":
    sys.exit(main())
