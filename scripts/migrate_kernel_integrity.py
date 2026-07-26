# -*- coding: utf-8 -*-
"""
migrate_kernel_integrity.py — F3: saneamiento del libro diario del kernel.

Hace, en orden y en UNA transacción:
  1. Backfill de cuenta_tipo (''/NULL) desde el primer dígito del PUC
     — sin esto, los asientos Zero-COA eran invisibles en el resumen financiero.
  2. Dedup histórico: para cada referencia con MÁS de un grupo de asientos
     (efecto de la doble vía fin + zero_coa), conserva el grupo zero_coa más
     reciente (posting_rules = fuente de verdad) y borra el resto. Si ningún
     grupo es zero_coa, conserva el más reciente.
  3. Añade la columna linea y la numera por grupo (orden por id).
  4. Crea el índice ÚNICO parcial uq_journal_modulo_ref_linea → idempotencia:
     re-emitir la misma referencia ya no puede duplicar asientos.

Idempotente: correr de nuevo no borra nada adicional ni falla.

Uso:  python scripts/migrate_kernel_integrity.py [--dry-run]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DRY_RUN = "--dry-run" in sys.argv


def _load_env():
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def run():
    _load_env()
    from fin_sys_core.db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()

        # ── 1. Backfill de cuenta_tipo desde el PUC ──────────────────────────
        cur.execute("""
            UPDATE kernel_journal_entries
            SET cuenta_tipo = CASE substring(cuenta_codigo from 1 for 1)
                WHEN '1' THEN 'ACTIVO'
                WHEN '2' THEN 'PASIVO'
                WHEN '3' THEN 'PATRIMONIO'
                WHEN '4' THEN 'INGRESO'
                WHEN '5' THEN 'GASTO'
                WHEN '6' THEN 'GASTO'
                WHEN '7' THEN 'GASTO'
                ELSE cuenta_tipo
            END
            WHERE cuenta_tipo IS NULL OR cuenta_tipo = '';
        """)
        print(f"1. cuenta_tipo backfilled: {cur.rowcount} líneas")

        # ── 2. Dedup histórico por referencia ────────────────────────────────
        cur.execute("""
            SELECT referencia
            FROM kernel_journal_entries
            WHERE referencia IS NOT NULL AND referencia <> ''
            GROUP BY referencia
            HAVING COUNT(DISTINCT entry_group_id) > 1;
        """)
        refs_dup = [r[0] for r in cur.fetchall()]
        print(f"2. referencias con grupos duplicados: {len(refs_dup)}")

        borradas = 0
        for ref in refs_dup:
            # Grupos de esta referencia, del más reciente al más viejo
            cur.execute("""
                SELECT entry_group_id, modulo_origen, MAX(id) AS max_id
                FROM kernel_journal_entries
                WHERE referencia = %s
                GROUP BY entry_group_id, modulo_origen
                ORDER BY max_id DESC;
            """, (ref,))
            grupos = cur.fetchall()
            # Preferir el grupo zero_coa más reciente; si no hay, el más reciente
            keep = next((g[0] for g in grupos if g[1] == "zero_coa"), grupos[0][0])
            perdedores = [g[0] for g in grupos if g[0] != keep]
            cur.execute("""
                DELETE FROM kernel_journal_entries
                WHERE referencia = %s AND entry_group_id = ANY(%s);
            """, (ref, perdedores))
            borradas += cur.rowcount
            print(f"   {ref}: conservo {keep}, borro {len(perdedores)} grupo(s) ({cur.rowcount} líneas)")
        print(f"   → total líneas duplicadas eliminadas: {borradas}")

        # ── 2.5 Asientos huérfanos: referencia TX-n sin transacción n ────────
        # Provienen de resets antiguos que borraban transactions pero no el
        # diario. Al reiniciarse la secuencia de ids, una TX nueva reutiliza
        # el id y "hereda" el asiento viejo → duplicación fantasma.
        cur.execute("""
            DELETE FROM kernel_journal_entries k
            WHERE k.referencia ~ '^TX-[0-9]+$'
              AND NOT EXISTS (
                  SELECT 1 FROM transactions t
                  WHERE t.id = CAST(SUBSTRING(k.referencia FROM 4) AS INTEGER)
              );
        """)
        print(f"2.5 asientos huérfanos eliminados: {cur.rowcount} líneas")

        # ── 3. Columna linea + numeración por grupo ──────────────────────────
        cur.execute("ALTER TABLE kernel_journal_entries ADD COLUMN IF NOT EXISTS linea INTEGER;")
        cur.execute("""
            WITH numeradas AS (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY entry_group_id ORDER BY id) AS rn
                FROM kernel_journal_entries
                WHERE linea IS NULL
            )
            UPDATE kernel_journal_entries k
            SET linea = n.rn
            FROM numeradas n
            WHERE k.id = n.id;
        """)
        print(f"3. linea numerada: {cur.rowcount} líneas")

        # ── 4. Índice único de idempotencia ──────────────────────────────────
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_journal_modulo_ref_linea
                ON kernel_journal_entries(modulo_origen, referencia, linea)
                WHERE referencia IS NOT NULL AND referencia <> '' AND linea IS NOT NULL;
        """)
        print("4. índice único uq_journal_modulo_ref_linea creado/asegurado")

        if DRY_RUN:
            conn.rollback()
            print("\n[DRY-RUN] rollback — nada persistido")
        else:
            conn.commit()
            print("\nOK — migración aplicada")

        # Verificación post: ninguna referencia con >1 grupo
        cur.execute("""
            SELECT COUNT(*) FROM (
                SELECT referencia FROM kernel_journal_entries
                WHERE referencia <> '' GROUP BY referencia
                HAVING COUNT(DISTINCT entry_group_id) > 1
            ) t;
        """)
        print(f"verificación: referencias aún duplicadas = {cur.fetchone()[0]} (esperado 0)")
        cur.close()
    finally:
        put_conn(conn)


if __name__ == "__main__":
    run()
