"""Test: Registrar TX via API → verificar que journal entry se genera automáticamente"""
import urllib.request
import json

BASE = "http://127.0.0.1:8000"

def post(path, data):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    r = urllib.request.urlopen(req)
    return json.loads(r.read())

def get(path):
    r = urllib.request.urlopen(f"{BASE}{path}")
    return json.loads(r.read())

print("=" * 65)
print("TEST: Flujo completo Frontend -> TX -> Journal Entry automatico")
print("=" * 65)

# 1. Estado ANTES
print("\n1. Journal entries ANTES:")
entries_before = get("/api/kernel/journal-entries")
print(f"   Total: {len(entries_before)}")

# 2. Registrar una TX de GASTO via API real
print("\n2. Registrando TX de GASTO via POST /api/transactions...")
tx = post("/api/transactions", {
    "type": "GASTO",
    "amount": 350000,
    "concept": "Pago hosting servidor (TEST KERNEL E2E)",
    "transaction_date": "2026-06-19",
    "payment_method": "Transferencia",
    "category": "Infraestructura",
    "portfolio_name": "Negocio A",
    "third_party": {
        "identification_type": "NIT",
        "identification_number": "900.999.001-1",
        "name": "Cloud Hosting SAS"
    },
    "apply_iva": False,
    "apply_gmf": True,
    "account_id": 2
})
print(f"   TX creada: {tx}")

# 3. Estado DESPUES
print("\n3. Journal entries DESPUES:")
entries_after = get("/api/kernel/journal-entries")
print(f"   Total: {len(entries_after)}")
new_count = len(entries_after) - len(entries_before)
print(f"   Nuevos asientos: {new_count}")

if new_count > 0:
    new_entries = entries_after[:new_count]  # Los mas recientes estan primero (ORDER BY fecha DESC)
    print(f"\n   Asientos generados automaticamente:")
    for e in new_entries:
        db = float(e['debito'])
        cr = float(e['credito'])
        print(f"   {e['entry_group_id']} | {e['cuenta_codigo']} {e.get('cuenta_nombre',''):<25} | Db={db:>12,.2f} | Cr={cr:>12,.2f}")
    
    total_db = sum(float(e['debito']) for e in new_entries)
    total_cr = sum(float(e['credito']) for e in new_entries)
    print(f"\n4. Validacion partida doble:")
    print(f"   Total Debitos:  ${total_db:>12,.2f}")
    print(f"   Total Creditos: ${total_cr:>12,.2f}")
    print(f"   Cuadra: {'SI' if abs(total_db - total_cr) < 0.01 else 'NO'}")
else:
    print("\n   WARNING: No se generaron asientos nuevos")

# 5. Resumen financiero general
print("\n5. Resumen financiero completo:")
resumen = get("/api/kernel/resumen-financiero")
for k, v in resumen.items():
    if isinstance(v, (int, float)):
        print(f"   {k:<20}: ${v:>15,.2f}")
    else:
        print(f"   {k:<20}: {'OK' if v else 'FALLO'}")

# 6. Event bus status
print("\n6. Event Bus:")
bus = get("/api/kernel/event-bus/status")
print(f"   Listeners: {len(bus['listeners'])} eventos registrados")
print(f"   Eventos recientes: {len(bus['recent_events'])}")
for ev in bus['recent_events']:
    print(f"   -> {ev['type']} (origen: {ev.get('modulo_origen','?')})")

print("\n" + "=" * 65)
print("TEST COMPLETADO")
print("=" * 65)
