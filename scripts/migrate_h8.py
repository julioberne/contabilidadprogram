# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Estándar de consultas H8: escritura del libro
===============================================================
Permiso de Andrés (30-oct-2026). No toca columnas ni datos de negocio.

Crea (idempotente):
  · idempotency_keys: clave de cada envío ↔ transacción que creó. La clave entra
    en la MISMA transacción de BD: existe si y solo si la transacción quedó
    guardada. Un doble clic o un reintento devuelve la misma, no crea otra.
Cambia:
  · Los 4 triggers del panel (H7) pasan a correr al hacer commit. Hoy suben la
    versión en medio de la escritura y dejan bloqueada la fila de la empresa
    (y la 0, común a todas) mientras se escribe el asiento. Mismos nombres,
    mismas funciones: solo cambia cuándo corren.

Lo corre Andrés (el clasificador no deja a Claude correr migrate_*.py):
    python scripts/migrate_h8.py --dry-run
    python scripts/migrate_h8.py
    python scripts/migrate_h8.py --deshacer     # vuelve a los triggers de H7
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
CREATE TABLE IF NOT EXISTS idempotency_keys (
    clave          text        PRIMARY KEY,
    huella         text,                          -- contenido del envío; NULL = no se compara
    transaction_id bigint,
    creada         timestamptz NOT NULL DEFAULT now()
)"""
INDICE = "CREATE INDEX IF NOT EXISTS idx_idempotency_creada ON idempotency_keys (creada)"

# Al correr en el commit, la transacción madre puede ya no existir (se borró junto
# con su cartera): sin este IF subiría la fila 0 antes que la de la empresa, en
# orden contrario al de crear. El borrado de la madre ya sube la empresa.
FUNCION_HIJA = """
CREATE OR REPLACE FUNCTION panel_hija_cambio() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE tid bigint; pid integer;
BEGIN
    tid := CASE WHEN TG_OP = 'DELETE' THEN OLD.transaction_id ELSE NEW.transaction_id END;
    SELECT portfolio_id INTO pid FROM transactions WHERE id = tid;
    IF pid IS NOT NULL THEN
        PERFORM panel_subir(pid);
    END IF;
    RETURN NULL;
END $$"""

TRIGGERS = [
    ("transactions", "panel_tx_cambio", "panel_tx_cambio"),
    ("transaction_evidences", "panel_evidencia_cambio", "panel_hija_cambio"),
    ("cxp_cxc_ledger", "panel_cartera_cambio", "panel_hija_cambio"),
    ("user_accounts", "panel_cuenta_cambio", "panel_cuenta_cambio"),
]


def main():
    dry = "--dry-run" in sys.argv
    deshacer = "--deshacer" in sys.argv
    conn = psycopg2.connect(host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME", "postgres"),
                            user=os.getenv("DB_USER", "postgres"), password=os.getenv("DB_PASSWORD", ""),
                            port=os.getenv("DB_PORT", "6543"), connect_timeout=15,
                            application_name="finsys-migrate-h8")
    conn.autocommit = False
    cur = conn.cursor()
    print("=" * 70)
    print("  H8 — ESCRITURA DEL LIBRO" + ("  (DRY-RUN)" if dry else "") + ("  (DESHACER)" if deshacer else ""))
    print("=" * 70)
    print(f"✅ Conectado a {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")
    try:
        cur.execute("SET LOCAL lock_timeout = '5s'")      # no hacer fila detrás de una escritura larga
        if not deshacer:
            cur.execute(TABLA)
            cur.execute(INDICE)
            print(f"  {'🔍' if dry else '✅'} tabla idempotency_keys")
            cur.execute(FUNCION_HIJA)
            print(f"  {'🔍' if dry else '✅'} función panel_hija_cambio")
        for tabla, nombre, funcion in TRIGGERS:
            cur.execute("SELECT tgdeferrable FROM pg_trigger WHERE tgname = %s AND NOT tgisinternal", (nombre,))
            fila = cur.fetchone()
            if fila is None:
                sys.exit(f"❌ Falta el trigger {nombre} de H7: corre primero migrate_panel_h7.py.")
            if bool(fila[0]) != deshacer:
                print(f"  ⏭  trigger {nombre} ya está como se pide")
                continue
            print(f"  {'🔍' if dry else '✅'} trigger {nombre} en {tabla}: "
                  + ("en el momento (H7)" if deshacer else "al hacer commit"))
            cur.execute(f"DROP TRIGGER {nombre} ON {tabla}")
            if deshacer:
                cur.execute(f"CREATE TRIGGER {nombre} AFTER INSERT OR UPDATE OR DELETE ON {tabla} "
                            f"FOR EACH ROW EXECUTE FUNCTION {funcion}()")
            else:
                cur.execute(f"CREATE CONSTRAINT TRIGGER {nombre} AFTER INSERT OR UPDATE OR DELETE ON {tabla} "
                            f"DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION {funcion}()")
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


if __name__ == "__main__":
    main()
