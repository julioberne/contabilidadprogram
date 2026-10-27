# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Estándar de consultas H7: versión del panel y fotos de saldo
==============================================================================
Permiso de Andrés (27-oct-2026): triggers en 4 tablas existentes que SOLO suben
un número de versión o marcan la foto como vieja (no cambian columnas ni datos).

Crea (idempotente):
  · panel_version (empresa → versión; 0 = cuentas compartidas). Cada cambio en
    transactions / transaction_evidences / cxp_cxc_ledger sube la versión de su
    empresa; un cambio en user_accounts sube la 0 (la ven todas). El panel deja
    de recargar si la versión no cambió.
  · saldos_foto_meta (1 fila: corte_id, tomada, sucia), saldos_foto (cuenta →
    movimiento acumulado hasta el corte) y kpi_foto (empresa → ingresos y gastos
    hasta el corte). El panel calcula foto + lo posterior al corte.
  · Triggers: la foto queda `sucia` si se edita, borra o inserta un movimiento
    con id ≤ corte, si una cuenta cambia de moneda o se borra, o con TRUNCATE.

Lo corre Andrés (el clasificador no deja a Claude correr migrate_*.py):
    python scripts/migrate_panel_h7.py --dry-run
    python scripts/migrate_panel_h7.py
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

TABLAS = [
    ("panel_version", """
CREATE TABLE IF NOT EXISTS panel_version (
    portfolio_id integer     PRIMARY KEY,          -- 0 = cuentas compartidas
    version      bigint      NOT NULL DEFAULT 0,
    actualizada  timestamptz NOT NULL DEFAULT now()
)"""),
    ("saldos_foto_meta", """
CREATE TABLE IF NOT EXISTS saldos_foto_meta (
    id       integer     PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    corte_id bigint,
    tomada   timestamptz,
    sucia    boolean     NOT NULL DEFAULT true,
    cambios  bigint      NOT NULL DEFAULT 0     -- sube con cada cambio que invalida la foto
)"""),
    ("saldos_foto", """
CREATE TABLE IF NOT EXISTS saldos_foto (
    account_id integer PRIMARY KEY,
    delta      float8  NOT NULL DEFAULT 0
)"""),
    ("kpi_foto", """
CREATE TABLE IF NOT EXISTS kpi_foto (
    portfolio_id integer PRIMARY KEY,
    ingresos_cop float8  NOT NULL DEFAULT 0,
    gastos_cop   float8  NOT NULL DEFAULT 0,
    ingresos_usd float8  NOT NULL DEFAULT 0,
    gastos_usd   float8  NOT NULL DEFAULT 0,
    n            bigint  NOT NULL DEFAULT 0
)"""),
]

FUNCIONES = [
    ("panel_subir", """
CREATE OR REPLACE FUNCTION panel_subir(pid integer) RETURNS void LANGUAGE sql AS $$
    INSERT INTO panel_version (portfolio_id, version) VALUES (COALESCE(pid, 0), 1)
    ON CONFLICT (portfolio_id) DO UPDATE SET version = panel_version.version + 1, actualizada = now();
$$"""),
    ("panel_foto_sucia", """
CREATE OR REPLACE FUNCTION panel_foto_sucia() RETURNS void LANGUAGE sql AS $$
    UPDATE saldos_foto_meta SET sucia = true, cambios = cambios + 1 WHERE id = 1;
$$"""),
    ("panel_tx_cambio", """
CREATE OR REPLACE FUNCTION panel_tx_cambio() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE corte bigint;
BEGIN
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        PERFORM panel_subir(NEW.portfolio_id);
    END IF;
    IF TG_OP = 'DELETE' OR (TG_OP = 'UPDATE' AND NEW.portfolio_id IS DISTINCT FROM OLD.portfolio_id) THEN
        PERFORM panel_subir(OLD.portfolio_id);
    END IF;
    SELECT corte_id INTO corte FROM saldos_foto_meta WHERE id = 1;
    IF corte IS NOT NULL AND ((TG_OP IN ('UPDATE', 'DELETE') AND OLD.id <= corte)
                              OR (TG_OP = 'INSERT' AND NEW.id <= corte)) THEN
        PERFORM panel_foto_sucia();
    END IF;
    RETURN NULL;
END $$"""),
    ("panel_tx_truncate", """
CREATE OR REPLACE FUNCTION panel_tx_truncate() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    UPDATE panel_version SET version = version + 1, actualizada = now();
    PERFORM panel_foto_sucia();
    RETURN NULL;
END $$"""),
    ("panel_hija_cambio", """
CREATE OR REPLACE FUNCTION panel_hija_cambio() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE tid bigint; pid integer;
BEGIN
    tid := CASE WHEN TG_OP = 'DELETE' THEN OLD.transaction_id ELSE NEW.transaction_id END;
    SELECT portfolio_id INTO pid FROM transactions WHERE id = tid;
    PERFORM panel_subir(pid);
    RETURN NULL;
END $$"""),
    ("panel_cuenta_cambio", """
CREATE OR REPLACE FUNCTION panel_cuenta_cambio() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM panel_subir(0);
    IF TG_OP = 'DELETE' OR (TG_OP = 'UPDATE' AND NEW.currency IS DISTINCT FROM OLD.currency) THEN
        PERFORM panel_foto_sucia();
    END IF;
    RETURN NULL;
END $$"""),
]

TRIGGERS = [
    ("transactions", "panel_tx_cambio",
     "AFTER INSERT OR UPDATE OR DELETE ON transactions FOR EACH ROW EXECUTE FUNCTION panel_tx_cambio()"),
    ("transactions", "panel_tx_truncate",
     "AFTER TRUNCATE ON transactions FOR EACH STATEMENT EXECUTE FUNCTION panel_tx_truncate()"),
    ("transaction_evidences", "panel_evidencia_cambio",
     "AFTER INSERT OR UPDATE OR DELETE ON transaction_evidences FOR EACH ROW EXECUTE FUNCTION panel_hija_cambio()"),
    ("cxp_cxc_ledger", "panel_cartera_cambio",
     "AFTER INSERT OR UPDATE OR DELETE ON cxp_cxc_ledger FOR EACH ROW EXECUTE FUNCTION panel_hija_cambio()"),
    ("user_accounts", "panel_cuenta_cambio",
     "AFTER INSERT OR UPDATE OR DELETE ON user_accounts FOR EACH ROW EXECUTE FUNCTION panel_cuenta_cambio()"),
]


def main():
    dry = "--dry-run" in sys.argv
    conn = psycopg2.connect(host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME", "postgres"),
                            user=os.getenv("DB_USER", "postgres"), password=os.getenv("DB_PASSWORD", ""),
                            port=os.getenv("DB_PORT", "6543"), connect_timeout=15,
                            application_name="finsys-migrate-panel-h7")
    conn.autocommit = False
    cur = conn.cursor()
    print("=" * 70)
    print("  H7 — VERSIÓN DEL PANEL + FOTOS DE SALDO" + ("  (DRY-RUN)" if dry else ""))
    print("=" * 70)
    print(f"✅ Conectado a {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}")
    try:
        for nombre, sql in TABLAS:
            print(f"  {'🔍' if dry else '✅'} tabla {nombre}")
            cur.execute(sql)
        cur.execute("ALTER TABLE saldos_foto_meta ADD COLUMN IF NOT EXISTS cambios bigint NOT NULL DEFAULT 0")
        cur.execute("INSERT INTO saldos_foto_meta (id, sucia) VALUES (1, true) ON CONFLICT (id) DO NOTHING")
        for nombre, sql in FUNCIONES:
            print(f"  {'🔍' if dry else '✅'} función {nombre}")
            cur.execute(sql)
        for tabla, nombre, definicion in TRIGGERS:
            cur.execute("SELECT 1 FROM pg_trigger WHERE tgname = %s AND NOT tgisinternal", (nombre,))
            if cur.fetchone():
                print(f"  ⏭  trigger {nombre} ya existe")
                continue
            print(f"  {'🔍' if dry else '✅'} trigger {nombre} en {tabla}")
            cur.execute(f"CREATE TRIGGER {nombre} {definicion}")
        # Versión inicial de cada empresa (y la 0) para que el panel tenga con qué comparar.
        cur.execute("INSERT INTO panel_version (portfolio_id, version) SELECT id, 1 FROM portfolios "
                    "ON CONFLICT (portfolio_id) DO NOTHING")
        cur.execute("INSERT INTO panel_version (portfolio_id, version) VALUES (0, 1) ON CONFLICT DO NOTHING")
        if dry:
            conn.rollback()
            print("  ↩️  DRY-RUN: todo se deshizo (nada quedó escrito).")
        else:
            conn.commit()
            cur.execute("SELECT count(*) FROM panel_version")
            print(f"  ✅ panel_version: {cur.fetchone()[0]} filas · la primera foto la saca el worker")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
