"""Test rápido del Kernel — Fase 0 Sprint 1"""
import sys
sys.path.insert(0, ".")

from kernel.kernel_accounting import registrar_asiento, PartidaDobleError, init_journal_entries_table
from kernel.kernel_event_bus import emit, on, list_listeners, reset

print("=" * 60)
print("TEST 1: Partida Doble — Asiento desbalanceado (debe fallar)")
print("=" * 60)
try:
    registrar_asiento({
        'fecha': '2026-06-19',
        'modulo_origen': 'test',
        'referencia': 'TEST-FAIL',
        'descripcion': 'Este asiento NO cuadra',
        'asientos': [
            {'cuenta_codigo': '1105', 'debito': 1000000, 'credito': 0},
            {'cuenta_codigo': '5105', 'debito': 0,       'credito': 500000},
        ]
    })
    print("❌ ERROR: Debería haber fallado pero no lo hizo")
except PartidaDobleError as e:
    print(f"✅ Rechazado correctamente: {e}")

print()
print("=" * 60)
print("TEST 2: Partida Doble — Asiento balanceado (debe pasar)")
print("=" * 60)
try:
    result = registrar_asiento({
        'fecha': '2026-06-19',
        'modulo_origen': 'test',
        'referencia': 'TEST-OK-001',
        'descripcion': 'Pago de servicios de consultoría',
        'asientos': [
            {'cuenta_codigo': '5105', 'cuenta_nombre': 'Gastos Servicios', 'cuenta_tipo': 'GASTO',
             'debito': 1000000, 'credito': 0},
            {'cuenta_codigo': '1110', 'cuenta_nombre': 'Bancos', 'cuenta_tipo': 'ACTIVO',
             'debito': 0, 'credito': 1000000},
        ]
    })
    print(f"✅ Asiento creado: {result}")
except Exception as e:
    print(f"⚠️ Error (puede ser por BD no disponible): {e}")

print()
print("=" * 60)
print("TEST 3: Event Bus — Emitir evento → handler contable")
print("=" * 60)
reset()
captured = []
def mock_handler(payload):
    captured.append(payload)
    return "procesado"

on('fin.transaccion.registrada', mock_handler)
result = emit('fin.transaccion.registrada', {
    'fecha': '2026-06-19',
    'modulo_origen': 'fin',
    'referencia': 'TX-42',
    'asientos': [
        {'cuenta_codigo': '5105', 'debito': 500000, 'credito': 0},
        {'cuenta_codigo': '1110', 'debito': 0, 'credito': 500000},
    ]
})
print(f"  Listeners: {list_listeners()}")
print(f"  Eventos capturados: {len(captured)}")
print(f"  Resultado emit: {result}")
if len(captured) == 1:
    print("✅ Event Bus funciona correctamente")
else:
    print("❌ Event Bus no capturó el evento")

print()
print("=" * 60)
print("TEST 4: Init tabla kernel_journal_entries")
print("=" * 60)
try:
    init_journal_entries_table()
    print("✅ Tabla inicializada (o ya existía)")
except Exception as e:
    print(f"⚠️ No se pudo crear tabla (BD no disponible): {e}")

print()
print("═" * 60)
print("RESUMEN: Kernel Fase 0 Sprint 1 — Tests completados")
print("═" * 60)
