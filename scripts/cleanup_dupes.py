"""
Limpieza: Eliminar journal entries duplicados.
Mantenemos solo los asientos generados por el kernel (modulo_origen='zero_coa') 
que son los correctos con las cuentas PUC precisas.
Para TX anteriores al listener (TX-1 a TX-6), mantenemos los existentes.
"""
import urllib.request, json, sys, os
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

conn = get_conn()
cur = conn.cursor()

# Find duplicated references (TX with >2 journal lines)
cur.execute("""
    SELECT referencia, COUNT(*) as cnt
    FROM kernel_journal_entries
    WHERE referencia LIKE 'TX-%'
    GROUP BY referencia
    HAVING COUNT(*) > 2
    ORDER BY referencia;
""")
dupes = cur.fetchall()
print(f"Refs con duplicados: {len(dupes)}")

deleted = 0
for ref, cnt in dupes:
    # Keep only the entry_group that has modulo_origen='zero_coa' (the correct one)
    # If both are zero_coa, keep the one with the later id
    cur.execute("""
        SELECT DISTINCT entry_group_id, modulo_origen
        FROM kernel_journal_entries
        WHERE referencia = %s
        ORDER BY entry_group_id;
    """, (ref,))
    groups = cur.fetchall()
    
    if len(groups) <= 1:
        continue
    
    # Keep the LAST group (most recent/correct), delete the first
    to_delete = groups[0][0]
    to_keep = groups[-1][0]
    
    cur.execute("""
        DELETE FROM kernel_journal_entries
        WHERE entry_group_id = %s AND referencia = %s;
    """, (to_delete, ref))
    d = cur.rowcount
    deleted += d
    print(f"  {ref}: deleted {to_delete} ({d} rows), kept {to_keep}")

conn.commit()
cur.close()
put_conn(conn)

print(f"\nTotal deleted: {deleted} duplicate entries")

# Verify final count
r = urllib.request.urlopen("http://127.0.0.1:8000/api/journal-entries?limit=200")
entries = json.loads(r.read())
print(f"Journal entries remaining: {len(entries)}")

# Verify all balanced
from collections import defaultdict
groups = defaultdict(list)
for e in entries:
    groups[e.get('referencia','')].append(e)

all_ok = True
for ref, items in sorted(groups.items()):
    total_db = sum(float(i.get('debito',0) or 0) for i in items)
    total_cr = sum(float(i.get('credito',0) or 0) for i in items)
    balanced = abs(total_db - total_cr) < 0.01
    lines = len(items)
    if not balanced:
        print(f"  ❌ {ref}: {lines} lines, Db={total_db:,.0f} Cr={total_cr:,.0f}")
        all_ok = False
    else:
        print(f"  ✅ {ref}: {lines} lines, ${total_db:,.0f}")

print(f"\n{'✅ TODOS CUADRADOS' if all_ok else '❌ HAY DESCUADRADOS'}")
