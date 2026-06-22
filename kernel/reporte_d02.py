"""Reporte directo contra BD - sin necesitar servidor corriendo"""
import sys, os

# Cargar .env
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                os.environ[k.strip()] = v.strip()

sys.path.insert(0, ".")
sys.path.insert(0, "fin_sys_core")

from db_pool import get_conn, put_conn, init_pool
from psycopg2.extras import RealDictCursor

init_pool(minconn=1, maxconn=3)
conn = get_conn()
cur = conn.cursor(cursor_factory=RealDictCursor)

print()
print("=" * 65)
print("  REPORTE DE ESTADO — D02 FIN (Finanzas & Contabilidad)")
print("  Fecha: 19 Jun 2026  |  FIN-SYS OS v2.0")
print("=" * 65)

# 1. Portafolios
cur.execute("SELECT id, name, industry_type FROM portfolios ORDER BY id")
portafolios = cur.fetchall()
print(f"\n[1] PORTAFOLIOS ({len(portafolios)} activos)")
for p in portafolios:
    print(f"  ID:{p['id']} | {p['name']:<30} | {p['industry_type']}")

# 2. Cuentas bancarias
cur.execute("SELECT name, type, currency, current_balance FROM user_accounts ORDER BY id")
cuentas = cur.fetchall()
total = sum(float(c['current_balance']) for c in cuentas if c['currency'] == 'COP')
print(f"\n[2] CUENTAS BANCARIAS ({len(cuentas)} cuentas)")
for c in cuentas:
    bal = float(c['current_balance'])
    print(f"  {c['name']:<28} {c['currency']} ${bal:>14,.2f}")
print(f"  {'─'*50}")
print(f"  {'TOTAL COP':<28}     ${total:>14,.2f}")

# 3. Transacciones
cur.execute("SELECT type, COUNT(*) as n, SUM(amount) as total FROM transactions GROUP BY type ORDER BY type")
resumen_tx = cur.fetchall()
cur.execute("SELECT COUNT(*) as total FROM transactions")
total_tx = cur.fetchone()['total']
print(f"\n[3] TRANSACCIONES ({total_tx} total)")
for r in resumen_tx:
    print(f"  {r['type']:<15} {r['n']:>3} TXs   ${float(r['total'] or 0):>14,.2f}")

# Ultimas 5
cur.execute("""
    SELECT t.type, t.amount, t.concept, t.transaction_date, tp.name as tercero
    FROM transactions t
    LEFT JOIN third_parties tp ON t.third_party_id = tp.id
    ORDER BY t.id DESC LIMIT 5
""")
ultimas = cur.fetchall()
print(f"\n  Ultimas 5 transacciones:")
for t in ultimas:
    tipo = t['type'][0]
    print(f"  [{tipo}] {str(t['transaction_date'])} | {str(t['concept'])[:32]:<32} | ${float(t['amount']):>12,.2f}")

# 4. Terceros
cur.execute("SELECT COUNT(*) as n FROM third_parties")
n_terceros = cur.fetchone()['n']
print(f"\n[4] TERCEROS REGISTRADOS: {n_terceros}")

# 5. CXC / CXP
cur.execute("SELECT type, status, COUNT(*) as n, SUM(remaining_balance) as saldo FROM cxp_cxc_ledger GROUP BY type, status")
cxc = cur.fetchall()
if cxc:
    print(f"\n[5] CUENTAS POR COBRAR / PAGAR")
    for r in cxc:
        print(f"  {r['type']} | {r['status']:<12} | {r['n']} registros | ${float(r['saldo'] or 0):>12,.2f}")
else:
    print(f"\n[5] CUENTAS POR COBRAR / PAGAR: Sin registros")

# 6. COA
cur.execute("SELECT COUNT(*) as n, COUNT(*) FILTER (WHERE is_group=false) as hojas FROM chart_of_accounts WHERE portfolio_id=1")
coa = cur.fetchone()
cur.execute("SELECT account_type, COUNT(*) as n FROM chart_of_accounts WHERE portfolio_id=1 GROUP BY account_type ORDER BY account_type")
coa_tipos = cur.fetchall()
print(f"\n[6] PLAN DE CUENTAS — Negocio A")
print(f"  Total cuentas: {coa['n']}  (hojas: {coa['hojas']})")
for t in coa_tipos:
    print(f"  {t['account_type']:<12} {t['n']} cuentas")

# 7. Kernel Journal Entries
try:
    cur.execute("SELECT COUNT(*) as n, SUM(debito) as db, SUM(credito) as cr FROM kernel_journal_entries")
    je = cur.fetchone()
    total_db = float(je['db'] or 0)
    total_cr = float(je['cr'] or 0)
    cuadra = abs(total_db - total_cr) < 0.01
    cur.execute("SELECT COUNT(DISTINCT entry_group_id) as grupos FROM kernel_journal_entries")
    grupos = cur.fetchone()['grupos']
    cur.execute("SELECT modulo_origen, COUNT(*) as n FROM kernel_journal_entries GROUP BY modulo_origen")
    por_modulo = cur.fetchall()
    print(f"\n[7] MOTOR CONTABLE — Journal Entries (Partida Doble)")
    print(f"  Total asientos : {je['n']}")
    print(f"  Grupos (TXs)   : {grupos}")
    print(f"  Total Debitos  : ${total_db:>14,.2f}")
    print(f"  Total Creditos : ${total_cr:>14,.2f}")
    print(f"  Partida Doble  : {'CUADRA ✓' if cuadra else 'NO CUADRA ✗'}")
    for m in por_modulo:
        print(f"  Modulo '{m['modulo_origen']}': {m['n']} asientos")
    # Resumen financiero desde journal_entries
    cur.execute("""
        SELECT cuenta_tipo,
               SUM(debito) as db,
               SUM(credito) as cr,
               SUM(debito)-SUM(credito) as saldo
        FROM kernel_journal_entries
        GROUP BY cuenta_tipo ORDER BY cuenta_tipo
    """)
    balances = cur.fetchall()
    activos = ingresos = gastos = pasivos = 0
    for b in balances:
        t = (b['cuenta_tipo'] or '').upper()
        s = float(b['saldo'] or 0)
        if t == 'ACTIVO':    activos  = s
        elif t == 'INGRESO': ingresos = abs(float(b['cr'] or 0))
        elif t == 'GASTO':   gastos   = s
        elif t == 'PASIVO':  pasivos  = abs(float(b['cr'] or 0))
    utilidad = ingresos - gastos
    print(f"\n[8] ESTADOS FINANCIEROS (desde journal_entries)")
    print(f"  Activos        : ${activos:>14,.2f}")
    print(f"  Pasivos        : ${pasivos:>14,.2f}")
    print(f"  ─────────────────────────────────────")
    print(f"  Ingresos       : ${ingresos:>14,.2f}")
    print(f"  Gastos         : ${gastos:>14,.2f}")
    print(f"  ─────────────────────────────────────")
    print(f"  UTILIDAD NETA  : ${utilidad:>14,.2f}")
    ec = abs(activos - (pasivos + utilidad)) < 1
    print(f"  Ec. contable   : {'A = P + U  OK' if ec else 'REVISAR'}")
except Exception as e:
    print(f"\n[7] MOTOR CONTABLE: {e}")

cur.close()
put_conn(conn)

print()
print("=" * 65)
print("  FUNCIONALIDADES — ESTADO")
print("=" * 65)
features = [
    ("Registro manual de TX",            "OPERATIVO",   "POST /api/transactions"),
    ("Registro por voz (IA Groq)",       "OPERATIVO",   "POST /api/upload-voice-transaction"),
    ("Motor IVA 19%",                    "OPERATIVO",   "tax_motor.py"),
    ("Motor GMF 4x1000",                 "OPERATIVO",   "tax_motor.py"),
    ("Partida Doble (Kernel)",           "OPERATIVO",   "kernel_accounting.py"),
    ("Bus de Eventos (K5)",              "OPERATIVO",   "kernel_event_bus.py"),
    ("Plan de Cuentas NIIF",             "OPERATIVO",   "chart_of_accounts"),
    ("4 Portafolios activos",            "OPERATIVO",   "portfolios"),
    ("7 Cuentas bancarias",              "OPERATIVO",   "user_accounts"),
    ("Paginacion TX (limit/offset)",     "OPERATIVO",   "GET /api/transactions"),
    ("Edicion de TX",                    "OPERATIVO",   "PUT /api/transactions/{id}"),
    ("Cuentas por Cobrar/Pagar",         "PARCIAL",     "cxp_cxc_ledger (sin UI completa)"),
    ("Dashboard KPIs",                   "PARCIAL",     "KPIs no consumen journal_entries aun"),
    ("Activos fijos",                    "PARCIAL",     "tabla assets existe, sin UI"),
    ("COA editable en UI",               "PARCIAL",     "backend OK, UI basica"),
    ("Estados Financieros en UI",        "NO INICIADO", "pendiente Sesion 1.12-1.13"),
    ("RBAC / Roles de usuario",          "NO INICIADO", "pendiente Fase 5"),
    ("Multi-tenant workspace_id",        "NO INICIADO", "pendiente Fase 0 Sprint 2"),
]
for f, estado, detalle in features:
    icono = "OK" if estado == "OPERATIVO" else ("~~" if estado == "PARCIAL" else "--")
    print(f"  [{icono}] {f:<40} {estado}")
    if estado != "OPERATIVO":
        print(f"        {detalle}")

print()
print("=" * 65)
