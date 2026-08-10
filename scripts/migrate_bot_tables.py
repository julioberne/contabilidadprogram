"""Migración Etapa B (Módulo 09 — Bot IA): tablas del bot.

Crea las 4 tablas del MVP de Telegram (idempotente, CREATE TABLE IF NOT EXISTS):
  - bot_chat_links     → identidad chat ↔ hub_users (allowlist por vinculación)
  - bot_link_codes     → códigos de vinculación de un solo uso (hash, 10 min)
  - transaction_drafts → borradores persistentes (Regla 6: IA nunca escribe
                         directo al libro; el borrador vive en OTRA tabla)
  - bot_messages       → auditoría + idempotencia de mensajes entrantes

Se ejecuta ANTES del deploy (el startup del server NO crea estas tablas,
solo las usa). Una segunda ejecución no cambia nada.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

# Load .env
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _, _val = _line.partition('=')
                os.environ.setdefault(_key.strip(), _val.strip().strip('"').strip("'"))

from fin_sys_core.db_pool import get_conn, put_conn

DDL = """
CREATE TABLE IF NOT EXISTS bot_chat_links (
    id SERIAL PRIMARY KEY,
    channel TEXT NOT NULL CHECK (channel IN ('telegram','whatsapp')),
    chat_id TEXT NOT NULL,
    -- hub_users.id es UUID (no serial) — verificado en la BD viva
    hub_user_id UUID NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    default_portfolio TEXT DEFAULT 'Personal',
    status TEXT NOT NULL DEFAULT 'ACTIVO' CHECK (status IN ('ACTIVO','BLOQUEADO')),
    display_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (channel, chat_id)
);

CREATE TABLE IF NOT EXISTS bot_link_codes (
    code_hash TEXT PRIMARY KEY,
    hub_user_id UUID NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transaction_drafts (
    id SERIAL PRIMARY KEY,
    chat_link_id INTEGER REFERENCES bot_chat_links(id) ON DELETE SET NULL,
    user_id UUID REFERENCES hub_users(id) ON DELETE SET NULL,
    channel TEXT,
    portfolio_name TEXT,
    status TEXT NOT NULL DEFAULT 'BORRADOR'
        CHECK (status IN ('BORRADOR','PROCESANDO','CONFIRMADO','ERROR','DESCARTADO')),
    schema_version INTEGER NOT NULL DEFAULT 1,
    payload JSONB NOT NULL DEFAULT '{}',
    raw_text TEXT,
    media_path TEXT,
    external_message_id TEXT,
    error TEXT,
    confirmed_transaction_id BIGINT,   -- transactions.id es bigint
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_drafts_status ON transaction_drafts(status);
CREATE INDEX IF NOT EXISTS idx_drafts_user ON transaction_drafts(user_id);

CREATE TABLE IF NOT EXISTS bot_messages (
    id SERIAL PRIMARY KEY,
    chat_link_id INTEGER REFERENCES bot_chat_links(id) ON DELETE SET NULL,
    raw_chat_id TEXT,
    direction TEXT NOT NULL CHECK (direction IN ('IN','OUT')),
    channel TEXT NOT NULL,
    external_message_id TEXT,
    kind TEXT,
    content TEXT,
    draft_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- Idempotencia: un update de Telegram (update_id) o un wamid de WhatsApp
-- reintentado NUNCA se procesa dos veces.
CREATE UNIQUE INDEX IF NOT EXISTS uq_bot_messages_in
    ON bot_messages(channel, external_message_id)
    WHERE direction = 'IN' AND external_message_id IS NOT NULL;
"""

TABLAS = ['bot_chat_links', 'bot_link_codes', 'transaction_drafts', 'bot_messages']


def main():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(DDL)
        conn.commit()
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ANY(%s)
            ORDER BY table_name
        """, (TABLAS,))
        creadas = [r[0] for r in cur.fetchall()]
        for t in TABLAS:
            print(f"  {'✓' if t in creadas else '✗ FALTA'} {t}")
        cur.close()
        ok = len(creadas) == len(TABLAS)
        print("RESULTADO: OK — 4 tablas del bot presentes" if ok else "RESULTADO: REVISAR")
        return 0 if ok else 1
    finally:
        put_conn(conn)


if __name__ == "__main__":
    sys.exit(main())
