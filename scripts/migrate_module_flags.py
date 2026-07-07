"""Crear tabla module_flags y seed datos iniciales."""
import sys, os
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'fin_sys_core'))

# Cargar .env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            ls = line.strip()
            if ls and not ls.startswith('#') and '=' in ls:
                k, v = ls.split('=', 1)
                os.environ[k.strip()] = v.strip()

from database_driver import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

# Crear tabla
cur.execute("""
CREATE TABLE IF NOT EXISTS module_flags (
    id          SERIAL PRIMARY KEY,
    module_id   TEXT NOT NULL,
    enabled     BOOLEAN DEFAULT true,
    company_id  INTEGER DEFAULT NULL,
    role_filter TEXT DEFAULT NULL,
    updated_at  TIMESTAMPTZ DEFAULT now(),
    updated_by  TEXT DEFAULT 'system',
    UNIQUE(module_id, company_id, role_filter)
)
""")

# Índice
cur.execute("CREATE INDEX IF NOT EXISTS idx_module_flags_company ON module_flags(company_id)")

# Seed
seeds = [
    ('contabilidad', True),
    ('control-tower', True),
    ('project-hub', True),
    ('contabilidad-v2', True),
    ('bot', False),
    ('trading', False),
]
for mod_id, enabled in seeds:
    cur.execute("""
        INSERT INTO module_flags (module_id, enabled, company_id, role_filter, updated_by)
        VALUES (%s, %s, NULL, NULL, 'system')
        ON CONFLICT (module_id, company_id, role_filter) DO NOTHING
    """, (mod_id, enabled))

conn.commit()

# Verificar
cur.execute("SELECT module_id, enabled, company_id, role_filter FROM module_flags ORDER BY module_id")
rows = cur.fetchall()
for r in rows:
    print(f"  {r[0]:20s} enabled={r[1]}  company={r[2]}  role={r[3]}")

print(f"\n✅ module_flags: {len(rows)} registros")
cur.close()
