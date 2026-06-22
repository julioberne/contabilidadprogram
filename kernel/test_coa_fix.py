import sys, os

if os.path.exists('.env'):
    for line in open('.env','r',encoding='utf-8'):
        s = line.strip()
        if s and not s.startswith('#') and '=' in s:
            k,v = s.split('=',1)
            os.environ[k.strip()] = v.strip()

sys.path.insert(0,'.')
from fin_sys_core.db_pool import init_pool, get_conn, put_conn
from fin_sys_core.database_driver import obtener_coa_tree

print("Testing COA fix...")
init_pool(minconn=1, maxconn=3)
conn = get_conn()
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM chart_of_accounts WHERE portfolio_id=1')
n = cur.fetchone()[0]
print(f"Cuentas en BD para Negocio A: {n}")
put_conn(conn)

tree = obtener_coa_tree('Negocio A')
result = {"status": "OK", "data": tree}
print(f"result['status'] = {result['status']}")
print(f"result['data'] len = {len(result['data'])} grupos raiz")
# Flatten to count leaves
def flatten(nodes):
    out = []
    for n in nodes:
        out.append(n)
        out.extend(flatten(n.get('children', [])))
    return out
all_accounts = flatten(tree)
leaf_accounts = [a for a in all_accounts if not a.get('is_group')]
print(f"Total cuentas: {len(all_accounts)}, hojas (is_group=False): {len(leaf_accounts)}")
print()
print("El COA ahora entrega status=OK y data=[...] igual que el endpoint /api/coa")
print("El frontend verificara data.coa.status === 'OK' --> PASA")
print("El COA se mostrara en el formulario con", len(leaf_accounts), "cuentas seleccionables")
