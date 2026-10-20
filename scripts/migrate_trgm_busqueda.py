# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Plan B del estándar de consultas: índices trigram para la
búsqueda «contiene» de terceros (16-oct-2026)
==========================================================================
/api/buscar/terceros (web, Mini App y bot) busca con LIKE '%texto%' sobre el
nombre sin tildes y, con 3+ dígitos, sobre el documento y el celular sin
signos. Sin índice eso recorre third_parties entera en cada tecla; con
pg_trgm + GIN la búsqueda cuesta según lo encontrado (regla B6: desde 3
caracteres). Las expresiones son EXACTAMENTE las de
fin_sys_core/consultas/busqueda.py (se importan de ahí: si cambian, el índice
deja de servir y el --explain lo muestra).

Lo corre Andrés (el clasificador no deja a Claude correr migrate_*.py):
    python scripts/migrate_trgm_busqueda.py --dry-run        # solo muestra
    python scripts/migrate_trgm_busqueda.py --explain        # aplica + EXPLAIN antes/después
    python scripts/migrate_trgm_busqueda.py --concurrently   # sin bloquear escrituras

Idempotente (IF NOT EXISTS). Activar pg_trgm es configuración de la BD: queda
en el esquema `extensions` de Supabase (o `public` si no existe). CONCURRENTLY
necesita autocommit (cada sentencia es su propia transacción; vale por :6543).
Si un CREATE ... CONCURRENTLY falla a medias deja un índice INVALID: el paso
final lo detecta para hacer DROP INDEX y reintentar.
"""
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_ROOT)
sys.path.insert(0, _ROOT)


def _cargar_env():
    """El .env del proyecto: el de esta carpeta o, desde un worktree
    (.claude/worktrees/<x>, que no lo tiene), el de la carpeta principal."""
    import pathlib
    raiz = pathlib.Path(_ROOT)
    for base in (raiz, *raiz.parents):
        env = base / ".env"
        if env.is_file():
            with open(env, "r", encoding="utf-8") as f:
                for line in f:
                    ls = line.strip()
                    if ls and not ls.startswith("#") and "=" in ls:
                        k, v = ls.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
            return env
    return None


if not _cargar_env() or not os.getenv("DB_HOST"):
    sys.exit("❌ No encontré el .env con DB_HOST (ni aquí ni en la carpeta principal): no me conecto a ciegas.")

import psycopg2  # noqa: E402

from fin_sys_core.consultas.busqueda import _sql_norm  # noqa: E402

_DIGITOS = "regexp_replace(COALESCE({col}, ''), '\\D', '', 'g')"

# (nombre, expresión indexada sobre third_parties) — las mismas de busqueda.py
INDICES = [
    ("idx_tp_nombre_trgm", _sql_norm("name"), "nombre que contiene el texto (sin tildes)"),
    ("idx_tp_documento_trgm", _DIGITOS.format(col="identification_number"), "documento que contiene 3+ dígitos"),
    ("idx_tp_celular_trgm", _DIGITOS.format(col="phone"), "celular que contiene 3+ dígitos"),
]

EXPLAIN_QUERIES = [
    ("tercero contiene 'mar'",
     f"SELECT tp.id FROM third_parties tp WHERE {_sql_norm('tp.name')} LIKE '%mar%' LIMIT 9"),
    ("documento contiene '318'",
     f"SELECT tp.id FROM third_parties tp WHERE {_DIGITOS.format(col='tp.identification_number')} LIKE '%318%' LIMIT 9"),
]


def connect():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        port=os.getenv("DB_PORT", "6543"),
        connect_timeout=15,
        application_name="finsys-migrate-trgm",
    )
    conn.autocommit = True   # imprescindible para CONCURRENTLY
    return conn


def explain(cur, etiqueta):
    for nombre, sql in EXPLAIN_QUERIES:
        try:
            cur.execute("EXPLAIN (ANALYZE, FORMAT TEXT) " + sql)
            plan = [r[0] for r in cur.fetchall()]
            usa = next((ln.strip() for ln in plan if "idx_tp_" in ln), "sin índice trigram (Seq Scan)")
            tiempo = next((ln.strip() for ln in plan if "Execution Time" in ln), "")
            print(f"    [{etiqueta}] {nombre}: {usa[:90]} | {tiempo}")
        except Exception as e:
            print(f"    [{etiqueta}] {nombre}: EXPLAIN falló: {e}")


def esquema_extension(cur, dry):
    """Activa pg_trgm (si falta) y devuelve el esquema donde vive."""
    cur.execute("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace "
                "WHERE e.extname = 'pg_trgm'")
    fila = cur.fetchone()
    if fila:
        print(f"  ⏭  pg_trgm ya está activa (esquema {fila[0]})")
        return fila[0]
    cur.execute("SELECT 1 FROM pg_namespace WHERE nspname = 'extensions'")
    esquema = "extensions" if cur.fetchone() else "public"
    sql = f"CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA {esquema}"
    if dry:
        print(f"  🔍 {sql}")
    else:
        cur.execute(sql)
        print(f"  ✅ pg_trgm activada en el esquema {esquema}")
    return esquema


def main():
    dry = "--dry-run" in sys.argv
    conc = "--concurrently" in sys.argv
    do_explain = "--explain" in sys.argv
    print("=" * 70)
    print("  PLAN B — ÍNDICES TRIGRAM DE BÚSQUEDA" + ("  (DRY-RUN)" if dry else ""))
    print("=" * 70)
    conn = connect()
    cur = conn.cursor()
    print(f"✅ Conectado a {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")

    if do_explain:
        explain(cur, "antes")

    esquema = esquema_extension(cur, dry)
    for nombre, expresion, motivo in INDICES:
        cur.execute("SELECT 1 FROM pg_indexes WHERE indexname = %s", (nombre,))
        if cur.fetchone():
            print(f"  ⏭  {nombre} ya existe")
            continue
        sql = (f"CREATE INDEX {'CONCURRENTLY ' if conc else ''}IF NOT EXISTS {nombre} "
               f"ON third_parties USING gin (({expresion}) {esquema}.gin_trgm_ops)")
        if dry:
            print(f"  🔍 {nombre}: {sql}")
            continue
        t0 = time.perf_counter()
        try:
            cur.execute(sql)
            print(f"  ✅ {nombre} ({motivo}) en {time.perf_counter() - t0:.2f}s")
        except Exception as e:
            print(f"  ❌ {nombre}: {e}")

    if not dry:
        cur.execute("SELECT indexrelid::regclass::text FROM pg_index WHERE NOT indisvalid")
        invalidos = [r[0] for r in cur.fetchall()]
        if invalidos:
            print(f"  ⚠️ Índices INVALID (CONCURRENTLY a medias): {invalidos} — DROP INDEX y reintentar")
        else:
            print("  ✅ Sin índices inválidos")
        cur.execute("ANALYZE third_parties")

    if do_explain:
        explain(cur, "después")
        print("  ℹ️ Con pocos terceros Postgres puede preferir recorrer la tabla aunque el índice exista: "
              "es lo correcto; el índice entra solo cuando conviene.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
