# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Estándar de consultas H5: cola de trabajos (pgmq) y tabla
`operaciones` (estado de cada trabajo) — 19-oct-2026
==========================================================================
Decisión de Andrés (19-oct): la COLA es pgmq (Supabase Queues) y la tabla
`operaciones` guarda solo el ESTADO que ve el usuario (202 + /api/operaciones).
Lo pesado (exportaciones, ZIP, PDF, voz, IA, envíos a Telegram) deja de
correr dentro de la petición: lo hace el servicio `worker`.

Crea (idempotente):
  · la extensión pgmq (esquema `pgmq`);
  · las colas `trabajos` (producción) y `trabajos_prueba` (tests y local);
  · la tabla `operaciones` y sus índices. La clave única vale solo mientras
    el trabajo está PENDIENTE o EN_CURSO: un doble clic no encola dos veces,
    pero el mismo pedido se puede repetir cuando el anterior terminó.

Lo corre Andrés (el clasificador no deja a Claude correr migrate_*.py):
    python scripts/migrate_operaciones.py --dry-run    # solo muestra
    python scripts/migrate_operaciones.py              # aplica
NO expongas las colas por PostgREST (en el panel de Supabase → Queues, dejar
apagado "Expose Queues via PostgREST"): la app habla con pgmq por SQL.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_ROOT)


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

COLAS = ("trabajos", "trabajos_prueba")

TABLA = """
CREATE TABLE IF NOT EXISTS operaciones (
    id           bigserial PRIMARY KEY,
    tipo         text        NOT NULL,
    cola         text        NOT NULL,
    clave        text        NOT NULL,
    estado       text        NOT NULL DEFAULT 'PENDIENTE'
                 CHECK (estado IN ('PENDIENTE', 'EN_CURSO', 'HECHA', 'FALLIDA')),
    datos        jsonb       NOT NULL DEFAULT '{}'::jsonb,
    resultado    jsonb,
    error        text,
    intentos     integer     NOT NULL DEFAULT 0,
    max_intentos integer     NOT NULL DEFAULT 3,
    msg_id       bigint,
    usuario      text,
    empresa      text,
    creada       timestamptz NOT NULL DEFAULT now(),
    iniciada     timestamptz,
    terminada    timestamptz,
    actualizada  timestamptz NOT NULL DEFAULT now()
)"""

INDICES = [
    ("uq_operaciones_clave_en_vuelo",
     "CREATE UNIQUE INDEX IF NOT EXISTS uq_operaciones_clave_en_vuelo ON operaciones (clave) "
     "WHERE estado IN ('PENDIENTE', 'EN_CURSO')"),
    ("idx_operaciones_usuario",
     "CREATE INDEX IF NOT EXISTS idx_operaciones_usuario ON operaciones (usuario, id DESC)"),
    ("idx_operaciones_en_vuelo",
     "CREATE INDEX IF NOT EXISTS idx_operaciones_en_vuelo ON operaciones (cola, estado, id) "
     "WHERE estado IN ('PENDIENTE', 'EN_CURSO')"),
]


def connect():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        port=os.getenv("DB_PORT", "6543"),
        connect_timeout=15,
        application_name="finsys-migrate-operaciones",
    )
    conn.autocommit = True
    return conn


def paso(cur, dry, descripcion, sql, params=None):
    if dry:
        print(f"  🔍 {descripcion}: {' '.join(sql.split())[:160]}")
        return
    cur.execute(sql, params)
    print(f"  ✅ {descripcion}")


def main():
    dry = "--dry-run" in sys.argv
    print("=" * 70)
    print("  H5 — COLA pgmq + TABLA operaciones" + ("  (DRY-RUN)" if dry else ""))
    print("=" * 70)
    conn = connect()
    cur = conn.cursor()
    print(f"✅ Conectado a {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")

    cur.execute("SELECT installed_version FROM pg_available_extensions WHERE name = 'pgmq'")
    fila = cur.fetchone()
    if not fila:
        print("  ❌ pgmq no está disponible en esta BD: no se puede seguir.")
        sys.exit(1)
    if fila[0]:
        print(f"  ⏭  pgmq ya está activa (versión {fila[0]})")
    else:
        paso(cur, dry, "extensión pgmq", "CREATE EXTENSION IF NOT EXISTS pgmq")

    existentes = set()
    if not dry or fila[0]:
        cur.execute("SELECT queue_name FROM pgmq.list_queues()")
        existentes = {r[0] for r in cur.fetchall()}
    for cola in COLAS:
        if cola in existentes:
            print(f"  ⏭  cola {cola} ya existe")
        else:
            paso(cur, dry, f"cola {cola}", "SELECT pgmq.create(%s)", (cola,))

    paso(cur, dry, "tabla operaciones", TABLA)
    for nombre, sql in INDICES:
        paso(cur, dry, f"índice {nombre}", sql)

    if not dry:
        cur.execute("SELECT queue_name FROM pgmq.list_queues() ORDER BY 1")
        print(f"  ✅ Colas: {[r[0] for r in cur.fetchall()]}")
        cur.execute("SELECT count(*) FROM operaciones")
        print(f"  ✅ operaciones: {cur.fetchone()[0]} filas")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
