# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Estándar de consultas H9.1: alcance por empresa
=================================================================
Plan aprobado por Andrés (3-nov-2026). Tabla NUEVA: no toca tablas existentes.

Crea (idempotente):
  · usuario_empresas: qué empresas (portafolios) ve cada usuario. El dueño y el
    superusuario ven todas sin filas aquí; admin, contador y miembro ven SOLO las
    que tengan aquí. Sin filas = no ven ninguna empresa (falla cerrado).

Lo corre Andrés (el clasificador no deja a Claude correr migrate_*.py):
    python scripts/migrate_h9_alcance.py --dry-run
    python scripts/migrate_h9_alcance.py
    python scripts/migrate_h9_alcance.py --deshacer     # borra la tabla (y sus asignaciones)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_ROOT)


def _cargar_env():
    """El .env del proyecto: el de esta carpeta o, desde un worktree, el de la principal."""
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

TABLA = """
CREATE TABLE IF NOT EXISTS usuario_empresas (
    hub_user_id  uuid        NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    portfolio_id bigint      NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    creada       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (hub_user_id, portfolio_id)
)"""


def main():
    dry = "--dry-run" in sys.argv
    deshacer = "--deshacer" in sys.argv
    conn = psycopg2.connect(host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME", "postgres"),
                            user=os.getenv("DB_USER", "postgres"), password=os.getenv("DB_PASSWORD", ""),
                            port=os.getenv("DB_PORT", "6543"), connect_timeout=15,
                            application_name="finsys-migrate-h9")
    conn.autocommit = False
    cur = conn.cursor()
    print("=" * 70)
    print("  H9.1 — ALCANCE POR EMPRESA" + ("  (DRY-RUN)" if dry else "") + ("  (DESHACER)" if deshacer else ""))
    print("=" * 70)
    print(f"✅ Conectado a {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")
    try:
        cur.execute("SET LOCAL lock_timeout = '5s'")
        if deshacer:
            filas = 0
            if _existe(cur):
                cur.execute("SELECT count(*) FROM usuario_empresas")
                filas = cur.fetchone()[0]
            cur.execute("DROP TABLE IF EXISTS usuario_empresas")
            print(f"  {'🔍' if dry else '✅'} tabla usuario_empresas borrada ({filas} asignaciones)")
        else:
            ya = _existe(cur)
            cur.execute(TABLA)
            print(f"  {'⏭ ' if ya else ('🔍' if dry else '✅')} tabla usuario_empresas"
                  + (" ya existía" if ya else ""))
        if dry:
            conn.rollback()
            print("  ↩️  DRY-RUN: todo se deshizo (nada quedó escrito).")
        else:
            conn.commit()
            print("  ✅ Listo.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def _existe(cur) -> bool:
    cur.execute("SELECT to_regclass('public.usuario_empresas') IS NOT NULL")
    return bool(cur.fetchone()[0])


if __name__ == "__main__":
    main()
