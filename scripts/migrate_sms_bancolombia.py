# -*- coding: utf-8 -*-
"""
migrate_sms_bancolombia.py — Etapa 09.F (22-sep-2026): SMS de Bancolombia → borradores.
=======================================================================================
En UNA transacción, idempotente:
  1. Tabla sms_ingest_tokens (un token por teléfono, hash sha256, allowlist de remitentes).
  2. Columnas user_accounts.last4_cuenta / last4_tarjeta (cuentas POR ID, D-09F-03).
  3. Backfill PRUDENTE de last4_cuenta desde el nombre: solo cuentas cuyo nombre
     contiene EXACTAMENTE un grupo de 4 dígitos (p.ej. "Bancolombia Ahorros 3037 julian").
     Nada se toca si hay 0 o 2+ grupos; Andrés completa el resto en 💳 Cuentas.
  4. Verificación: prerrequisitos del bot, conteo de cuentas con last4, tokens.

Uso:  .venv\\Scripts\\python.exe scripts\\migrate_sms_bancolombia.py [--dry-run]
Correr ANTES del deploy (el server también se auto-cura con init_sms_tables(),
pero el backfill solo lo hace este script). Spec: docs/specs/09-bot-ia/09.F-sms-bancolombia.md
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "fin_sys_core"))
os.chdir(ROOT)
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
    import fin_sys_core  # noqa: F401
    from fin_sys_core.db_pool import get_conn, put_conn
    from bot_sms import DDL_LAST4, DDL_SMS_TOKENS

    print("=" * 70)
    print("  MIGRACIÓN SMS BANCOLOMBIA (09.F)" + ("  — DRY-RUN" if DRY_RUN else ""))
    print("=" * 70)
    conn = get_conn()
    try:
        cur = conn.cursor()

        # 0. Prerrequisitos (tablas del bot)
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ('bot_chat_links', 'bot_messages', 'transaction_drafts', 'hub_users')
        """)
        presentes = {r[0] for r in cur.fetchall()}
        faltan = {"bot_chat_links", "bot_messages", "transaction_drafts", "hub_users"} - presentes
        if faltan:
            print(f"❌ Faltan tablas previas: {sorted(faltan)} — corre scripts/migrate_bot_tables.py primero.")
            conn.rollback()
            return 1
        print("0. prerrequisitos del bot: OK")

        # 1. Tokens
        cur.execute(DDL_SMS_TOKENS)
        print("1. sms_ingest_tokens: OK")

        # 2. Columnas last4
        for sql in DDL_LAST4:
            cur.execute(sql)
        print("2. user_accounts.last4_cuenta / last4_tarjeta: OK")

        # 3. Backfill prudente (exactamente UN grupo de 4 dígitos en el nombre)
        cur.execute(r"""
            UPDATE user_accounts
               SET last4_cuenta = (regexp_match(name, '(?<!\d)(\d{4})(?!\d)'))[1]
             WHERE last4_cuenta IS NULL
               AND (SELECT COUNT(*) FROM regexp_matches(name, '(?<!\d)\d{4}(?!\d)', 'g')) = 1
        """)
        print(f"3. backfill last4_cuenta desde el nombre: {cur.rowcount} cuenta(s)")

        # 4. Verificación
        cur.execute("SELECT id, name, last4_cuenta, last4_tarjeta FROM user_accounts ORDER BY id")
        filas = cur.fetchall()
        print("4. cuentas:")
        for i, n, c, t in filas:
            print(f"   [{i}] {n!r:45} cuenta={c or '—'} tarjeta={t or '—'}")
        sin = [n for _, n, c, t in filas if not c and not t]
        if sin:
            print(f"   ⚠ {len(sin)} cuenta(s) sin últimos 4 dígitos (completar en 💳 Cuentas): {sin}")
        cur.execute("SELECT COUNT(*) FROM sms_ingest_tokens WHERE revoked_at IS NULL")
        print(f"   tokens SMS activos: {cur.fetchone()[0]} (crear con scripts/sms_token.py)")

        if DRY_RUN:
            conn.rollback()
            print("\nDRY-RUN: nada aplicado (rollback).")
        else:
            conn.commit()
            print("\n✅ Migración aplicada.")
        cur.close()
        return 0
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e} — rollback")
        return 1
    finally:
        put_conn(conn)


if __name__ == "__main__":
    sys.exit(run())
