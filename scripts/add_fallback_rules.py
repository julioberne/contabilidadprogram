"""Agregar posting rules de fallback para categorías del frontend."""
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

RULES = [
    ("Ingreso Genérico",        "__FALLBACK__",           "INGRESO", "__BANK__", "4120",   "Fallback ingreso"),
    ("Gasto Genérico",          "__FALLBACK__",           "GASTO",   "5105",     "__BANK__","Fallback gasto"),
    ("Servicios Profesionales", "Servicios Profesionales","INGRESO", "__BANK__", "4120",   "Ingreso por servicios profesionales"),
    ("Venta de Productos",      "Venta de Productos",     "INGRESO", "__BANK__", "413505", "Venta de productos"),
    ("Servicios Públicos",      "Servicios Públicos",     "GASTO",   "513525",   "__BANK__","Pago servicios públicos"),
]

conn = get_conn()
cur = conn.cursor()
n = 0
for rule_name, cat, txtype, db, cr, desc in RULES:
    cur.execute("""
        INSERT INTO posting_rules (rule_name, category, transaction_type, debit_account_code, credit_account_code, description, is_active)
        VALUES (%s,%s,%s,%s,%s,%s,TRUE) ON CONFLICT DO NOTHING;
    """, (rule_name, cat, txtype, db, cr, desc))
    if cur.rowcount > 0:
        n += 1
        print(f"  + {rule_name}")
    else:
        print(f"  = {rule_name} (exists)")
conn.commit()
cur.close()
put_conn(conn)
print(f"\n{n} reglas nuevas")
