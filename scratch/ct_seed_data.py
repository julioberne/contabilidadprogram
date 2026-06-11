#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FIN-SYS Control Tower — Script de Datos Sintéticos y Vinculación
=================================================================
Ejecutar desde: contabilidadprogram/
    python scratch/ct_seed_data.py

Realiza:
  1. Vincula entidades existentes a portafolios reales (portfolio_id)
  2. Crea 4 nuevas entidades en el árbol (árbol de 5 niveles)
  3. Registra 4 workspace_users adicionales con distintos roles
  4. Agrega resource_ids para cada entidad (NIT, RUT, contratos, etc.)
  5. Crea 6 aprobaciones en distintos estados
  6. Invita colaboradores a entidades específicas
  7. Lanza una transacción rápida de prueba via API
"""

import os, sys, json, hashlib, requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fin_sys_core'))

API_BASE = "http://127.0.0.1:8000"

def h(text): return hashlib.md5(text.encode()).hexdigest()
def post(path, body): return requests.post(f"{API_BASE}{path}", json=body)
def get(path): return requests.get(f"{API_BASE}{path}")
def patch_raw(path, body): return requests.patch(f"{API_BASE}{path}", json=body)

# ─────────────────────────────────────────────────────────────────────────────
# PASO 0: Conexión directa a DB para operaciones que la API no cubre aún
# ─────────────────────────────────────────────────────────────────────────────
try:
    from database_driver import get_db_connection
    conn = get_db_connection()
    cur = conn.cursor()
    USE_DB = True
    print("✅ Conexión a PostgreSQL establecida directamente.")
except Exception as e:
    USE_DB = False
    print(f"⚠️  Sin conexión directa a DB: {e} — solo se usará la API REST")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 1: Vincular entidades existentes a portafolios reales
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("PASO 1: Vinculando entidades a portafolios reales")
print("="*60)

ENTITY_PORTFOLIO_MAP = {
    # entity_name (buscar por nombre)  →  portfolio_id
    "Mi Holding Principal":    None,   # HOLDING: no tiene portafolio directo
    "Jardin Infantil Pegasus": 2,      # → EMPRESA INFANTIL PEGASUS
    "Consultora Digital SAS":  1,      # → Negocio A
}

if USE_DB:
    # Obtener IDs actuales
    cur.execute("SELECT id, name FROM entities ORDER BY id;")
    entities_db = {row[1]: row[0] for row in cur.fetchall()}
    print(f"   Entidades encontradas en DB: {list(entities_db.keys())}")

    # Actualizar portfolio_id por entidad
    UPDATES = [
        (2, 2),  # Jardín Infantil Pegasus → portfolio 2 (EMPRESA INFANTIL PEGASUS)
        (3, 1),  # Consultora Digital SAS  → portfolio 1 (Negocio A)
    ]
    for entity_id, portfolio_id in UPDATES:
        cur.execute(
            "UPDATE entities SET portfolio_id = %s WHERE id = %s;",
            (portfolio_id, entity_id)
        )
        print(f"   ✓ Entity {entity_id} → portfolio_id = {portfolio_id}")
    conn.commit()
    print("✅ Vinculación de portafolios completada.")
else:
    print("⚠️  Saltando paso 1 (sin conexión directa a DB)")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 2: Crear nuevas entidades en el árbol jerárquico
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("PASO 2: Creando nuevas entidades (árbol completo de 5 niveles)")
print("="*60)

NEW_ENTITIES = [
    # Nivel 2: Empresa nueva hija del Holding (id=1)
    {
        "name": "Constructora Norte SAS",
        "type": "EMPRESA",
        "parent_id": 1,
        "portfolio_id": 4,  # → Negocio Principal
        "industry": "CONSTRUCCION",
        "sub_industry": "Vivienda VIS",
        "status": "ALERTA",
    },
    # Nivel 3: Sub-empresa de Jardín Infantil Pegasus (id=2)
    {
        "name": "Sede Norte — Pegasus",
        "type": "SUB_EMPRESA",
        "parent_id": 2,
        "portfolio_id": 2,  # Comparte portafolio del padre
        "industry": "EDUCACION",
        "sub_industry": "Jardín Infantil",
        "status": "AL DIA",
    },
    # Nivel 3: Proyecto dentro de Consultora Digital (id=3)
    {
        "name": "Proyecto ERP — Cliente Minero",
        "type": "PROYECTO",
        "parent_id": 3,
        "portfolio_id": None,
        "industry": "TECNOLOGIA",
        "sub_industry": "Desarrollo de Software",
        "status": "AL DIA",
    },
    # Nivel 4: Tarea dentro del Proyecto ERP
    {
        "name": "Fase 1: Levantamiento de Requisitos",
        "type": "TAREA",
        "parent_id": None,  # se actualiza después con el ID del proyecto
        "portfolio_id": None,
        "industry": "TECNOLOGIA",
        "sub_industry": "Consultoría",
        "status": "AL DIA",
    },
]

created_entity_ids = {}
for i, entity in enumerate(NEW_ENTITIES):
    resp = post("/api/ct/entities", entity)
    if resp.status_code == 201:
        data = resp.json()
        eid = data.get("entity_id")
        created_entity_ids[entity["name"]] = eid
        print(f"   ✓ [{entity['type']}] '{entity['name']}' → ID {eid}")
    else:
        print(f"   ✗ Error creando '{entity['name']}': {resp.text}")

# Ahora actualizar la TAREA con el parent_id del PROYECTO recién creado
proyecto_id = created_entity_ids.get("Proyecto ERP — Cliente Minero")
if proyecto_id and USE_DB:
    tarea_id = created_entity_ids.get("Fase 1: Levantamiento de Requisitos")
    if tarea_id:
        cur.execute("UPDATE entities SET parent_id = %s WHERE id = %s;", (proyecto_id, tarea_id))
        conn.commit()
        print(f"   ✓ TAREA {tarea_id} vinculada a PROYECTO {proyecto_id}")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 3: Registrar workspace_users adicionales
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("PASO 3: Creando workspace_users con distintos roles")
print("="*60)

NEW_USERS = [
    {
        "name": "María Contadora",
        "email": "maria@finsys.os",
        "password": "maria2024",
        "role_label": "Contador Externo",
        "permissions": {"ledger": True, "reports": True, "users": False, "approvals": True},
    },
    {
        "name": "Carlos Auditor",
        "email": "carlos@finsys.os",
        "password": "auditor123",
        "role_label": "Auditor Senior",
        "permissions": {"ledger": False, "reports": True, "users": False, "approvals": False},
    },
    {
        "name": "Sofia Socia",
        "email": "sofia@finsys.os",
        "password": "socia2024",
        "role_label": "Socia Inversora",
        "permissions": {"ledger": False, "reports": True, "users": False, "approvals": True},
    },
    {
        "name": "Diego Admin",
        "email": "diego@finsys.os",
        "password": "admin2024",
        "role_label": "Administrador",
        "permissions": {"ledger": True, "reports": True, "users": True, "approvals": True},
    },
]

created_user_ids = {}
for user in NEW_USERS:
    resp = post("/api/ct/users/register", user)
    if resp.status_code == 201:
        data = resp.json()
        uid = data.get("user", {}).get("id")
        created_user_ids[user["name"]] = uid
        print(f"   ✓ [{user['role_label']}] '{user['name']}' → ID {uid}")
    elif "already exists" in resp.text or "duplicate" in resp.text.lower() or resp.status_code == 400:
        print(f"   ⚠ '{user['name']}' ya existe — OK")
    else:
        print(f"   ✗ Error: {resp.status_code} — {resp.text[:100]}")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 4: Agregar Resource IDs a cada entidad
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("PASO 4: Creando inventario de IDs por entidad")
print("="*60)

RESOURCE_IDS = [
    # Entidad 1: Mi Holding Principal
    {"entity_id": 1, "label": "NIT Holding", "value": "901.234.567-1", "category": "FISCAL",
     "expires_at": None, "notes": "Registro DIAN activo"},
    {"entity_id": 1, "label": "Matrícula Mercantil", "value": "MER-2023-00891", "category": "LEGAL",
     "expires_at": "2026-12-31", "notes": "Renovar antes de diciembre"},
    {"entity_id": 1, "label": "Cuenta Bancolombia Principal", "value": "12345678901", "category": "BANCARIO",
     "expires_at": None, "notes": "Cuenta corriente holding"},

    # Entidad 2: Jardín Infantil Pegasus
    {"entity_id": 2, "label": "NIT Pegasus", "value": "830.456.789-5", "category": "FISCAL",
     "expires_at": None, "notes": ""},
    {"entity_id": 2, "label": "Licencia Operación MEN", "value": "LIC-MEN-2024-001234", "category": "LEGAL",
     "expires_at": "2025-06-30", "notes": "⚠️ VENCIDA — Renovar urgente"},
    {"entity_id": 2, "label": "Contrato Arrendamiento Sede", "value": "ARR-2023-456", "category": "COMERCIAL",
     "expires_at": "2026-08-01", "notes": "Sede calle 45 #12-34"},
    {"entity_id": 2, "label": "Nequi Jardín", "value": "300 789 4561", "category": "BANCARIO",
     "expires_at": None, "notes": "Pagos pequeños"},

    # Entidad 3: Consultora Digital SAS
    {"entity_id": 3, "label": "NIT Consultora", "value": "901.100.200-8", "category": "FISCAL",
     "expires_at": None, "notes": "Régimen común"},
    {"entity_id": 3, "label": "RUT Actualizado", "value": "RUT-2024-100200", "category": "FISCAL",
     "expires_at": None, "notes": "Descargado enero 2024"},
    {"entity_id": 3, "label": "Contrato Marco Cliente Minero", "value": "CTR-MINERO-2024-001", "category": "COMERCIAL",
     "expires_at": "2025-01-31", "notes": "⚠️ VENCIDO — Pendiente renovación con cliente"},
    {"entity_id": 3, "label": "Póliza Responsabilidad Civil", "value": "POL-AXA-2024-78901", "category": "LEGAL",
     "expires_at": "2026-11-30", "notes": "Póliza AXA Colpatria"},

    # Entidad 4: Constructora Norte (nueva)
    {"entity_id": 4, "label": "NIT Constructora", "value": "860.987.654-3", "category": "FISCAL",
     "expires_at": None, "notes": "Régimen ordinario"},
    {"entity_id": 4, "label": "Licencia Construcción", "value": "LC-2023-BOG-001122", "category": "LEGAL",
     "expires_at": "2027-03-15", "notes": "Urbanización El Porvenir"},
    {"entity_id": 4, "label": "Fiducia Preventiva", "value": "FID-BBVA-2024-5678", "category": "BANCARIO",
     "expires_at": "2028-01-01", "notes": "Encargo fiduciario preventivo"},
]

# Usar IDs de entidades nuevas si están disponibles
constructora_id = created_entity_ids.get("Constructora Norte SAS", 4)
for r in RESOURCE_IDS:
    # Ajustar entity_id=4 si es diferente
    if r["entity_id"] == 4:
        r["entity_id"] = constructora_id or 4

for resource in RESOURCE_IDS:
    resp = post("/api/ct/resources", resource)
    if resp.status_code == 201:
        print(f"   ✓ [{resource['category']}] '{resource['label']}' → entidad {resource['entity_id']}")
    else:
        print(f"   ✗ Error: {resp.text[:80]}")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 5: Crear aprobaciones en distintos estados
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("PASO 5: Creando aprobaciones en distintos estados")
print("="*60)

APPROVALS = [
    # Pendientes (las más importantes)
    {"entity_id": 2, "description": "Pago nómina educadoras julio 2026", "amount": 8500000, "status_override": None},
    {"entity_id": 2, "description": "Compra materiales didácticos Q3", "amount": 1250000, "status_override": None},
    {"entity_id": 3, "description": "Licencia software de diseño anual", "amount": 3800000, "status_override": None},
    {"entity_id": constructora_id or 4, "description": "Anticipo proveedor cemento - 50 bultos", "amount": 4750000, "status_override": None},
    # Aprobadas
    {"entity_id": 1, "description": "Pago honorarios asesor legal holding", "amount": 2500000, "status_override": "APROBADO"},
    {"entity_id": 2, "description": "Mantenimiento aires acondicionados sede", "amount": 850000, "status_override": "APROBADO"},
    # Rechazada
    {"entity_id": 3, "description": "Viaje feria tecnología Bogotá (ya fue cancelada)", "amount": 650000, "status_override": "RECHAZADO"},
]

created_approval_ids = []
for appr in APPROVALS:
    payload = {
        "entity_id": appr["entity_id"],
        "description": appr["description"],
        "amount": appr["amount"],
        "requested_by": 1,  # Andrés
    }
    resp = post("/api/ct/approvals", payload)
    if resp.status_code == 201:
        aid = resp.json().get("approval_id")
        created_approval_ids.append({"id": aid, "override": appr.get("status_override")})
        print(f"   ✓ Aprobación #{aid}: '{appr['description'][:50]}' — ${appr['amount']:,.0f}")
    else:
        print(f"   ✗ Error: {resp.text[:80]}")

# Resolver las que tienen status_override
for item in created_approval_ids:
    if item["override"] and item["id"]:
        resolve_payload = {
            "status": item["override"],
            "reviewer_id": 1,
            "notes": "Revisado por sistema demo" if item["override"] == "APROBADO" else "Cancelado — no aplica"
        }
        r2 = requests.patch(f"{API_BASE}/api/ct/approvals/{item['id']}/resolve", json=resolve_payload)
        if r2.status_code == 200:
            print(f"   ✓ Aprobación #{item['id']} → {item['override']}")
        else:
            print(f"   ✗ Resolve error: {r2.text[:80]}")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 6: Asignar colaboradores a entidades
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("PASO 6: Invitando colaboradores a entidades")
print("="*60)

# Obtener IDs de usuarios creados desde la API
users_resp = get("/api/ct/users")
if users_resp.status_code == 200:
    all_users = users_resp.json()
    user_map = {u["name"]: u["id"] for u in all_users}
    print(f"   Usuarios en sistema: {list(user_map.keys())}")
else:
    user_map = {}
    print("   ⚠️ No se pudo obtener lista de usuarios")

MEMBER_ASSIGNMENTS = [
    # Jardín Infantil Pegasus
    {"entity_id": 2, "user_name": "María Contadora", "role_label": "Contadora Principal",
     "permissions": {"ledger": True, "reports": True, "users": False, "approvals": True}},
    {"entity_id": 2, "user_name": "Carlos Auditor", "role_label": "Auditor Externo",
     "permissions": {"ledger": False, "reports": True, "users": False, "approvals": False}},
    # Consultora Digital
    {"entity_id": 3, "user_name": "María Contadora", "role_label": "Asesora Financiera",
     "permissions": {"ledger": True, "reports": True, "users": False, "approvals": False}},
    {"entity_id": 3, "user_name": "Diego Admin", "role_label": "Director Operativo",
     "permissions": {"ledger": True, "reports": True, "users": True, "approvals": True}},
    # Holding Principal — Socia inversora
    {"entity_id": 1, "user_name": "Sofia Socia", "role_label": "Socia Inversora",
     "permissions": {"ledger": False, "reports": True, "users": False, "approvals": True}},
    # Constructora Norte
    {"entity_id": constructora_id or 4, "user_name": "Diego Admin", "role_label": "Gerente Proyecto",
     "permissions": {"ledger": True, "reports": True, "users": False, "approvals": True}},
]

for m in MEMBER_ASSIGNMENTS:
    uid = user_map.get(m["user_name"])
    if not uid:
        print(f"   ⚠️ Usuario '{m['user_name']}' no encontrado — saltando")
        continue
    payload = {
        "user_id": uid,
        "role_label": m["role_label"],
        "permissions": m["permissions"],
    }
    resp = post(f"/api/ct/entities/{m['entity_id']}/members", payload)
    if resp.status_code == 201:
        print(f"   ✓ '{m['user_name']}' → entidad {m['entity_id']} como '{m['role_label']}'")
    elif resp.status_code == 400 or "already" in resp.text.lower():
        print(f"   ⚠️ '{m['user_name']}' ya es miembro de entidad {m['entity_id']}")
    else:
        print(f"   ✗ Error: {resp.status_code} {resp.text[:80]}")

# ─────────────────────────────────────────────────────────────────────────────
# PASO 7: Transacciones rápidas de prueba desde el CT
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("PASO 7: Registrando transacciones rápidas de prueba via CT")
print("="*60)

QUICK_TXS = [
    {
        "entity_id": 2,
        "portfolio_name": "EMPRESA INFANTIL PEGASUS",
        "type": "INGRESO",
        "amount": 3800000,
        "concept": "Matrícula alumnos nuevos julio 2026",
        "category": "Ventas",
        "payment_method": "Transferencia",
        "third_party_name": "Familias Nuevas Grupo 2026-2",
        "third_party_id_number": "N/A",
        "third_party_id_type": "NIT",
    },
    {
        "entity_id": 3,
        "portfolio_name": "Negocio A",
        "type": "GASTO",
        "amount": 1500000,
        "concept": "Pago freelancer diseño UX sprint 12",
        "category": "Servicios",
        "payment_method": "Transferencia",
        "third_party_name": "Valentina Rojas Diseño",
        "third_party_id_number": "1032456789",
        "third_party_id_type": "CC",
    },
]

for tx in QUICK_TXS:
    resp = post("/api/ct/quick-transaction", tx)
    if resp.status_code == 201:
        tid = resp.json().get("transaction_id")
        print(f"   ✓ TX#{tid} — {tx['type']} ${tx['amount']:,.0f} — '{tx['concept'][:40]}'")
    else:
        print(f"   ✗ Error TX: {resp.status_code} — {resp.text[:120]}")

# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN FINAL
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("RESUMEN DE EJECUCIÓN")
print("="*60)

# Verificar árbol de entidades
resp = get("/api/ct/entities")
if resp.status_code == 200:
    tree = resp.json()
    total_roots = len(tree)
    def count_all(nodes):
        total = len(nodes)
        for n in nodes:
            if isinstance(n.get("children"), list):
                total += count_all(n["children"])
        return total
    total = count_all(tree)
    print(f"   🏢 Árbol de entidades: {total_roots} raíz(es), {total} nodo(s) total")

# Verificar KPIs del holding
resp = get("/api/ct/entities/1/kpis")
if resp.status_code == 200:
    k = resp.json()
    print(f"   💰 KPIs Holding:")
    print(f"      Ingresos:    ${k.get('total_ingresos', 0):,.0f}")
    print(f"      Egresos:     ${k.get('total_gastos', 0):,.0f}")
    print(f"      Balance:     ${k.get('balance_neto', 0):,.0f}")
    print(f"      Entidades:   {k.get('entity_ids_in_scope', 0)} en scope")
    print(f"      Aprobaciones pendientes: {k.get('pending_approvals', 0)}")

resp = get("/api/ct/approvals")
if resp.status_code == 200:
    appr = resp.json()
    pend = [a for a in appr if a.get('status') == 'PENDIENTE']
    apro = [a for a in appr if a.get('status') == 'APROBADO']
    rech = [a for a in appr if a.get('status') == 'RECHAZADO']
    print(f"   🔔 Aprobaciones: {len(pend)} pendientes / {len(apro)} aprobadas / {len(rech)} rechazadas")

resp = get("/api/ct/users")
if resp.status_code == 200:
    print(f"   👥 Workspace users: {len(resp.json())}")

if USE_DB:
    cur.execute("SELECT COUNT(*) FROM resource_ids;")
    print(f"   🪪 Resource IDs: {cur.fetchone()[0]}")
    cur.close()
    conn.close()

print("\n✅ SEED COMPLETO — Recarga la app para ver los datos.")
print("   Login demo: andres@finsys.os / admin123")
print("   Otros usuarios: maria@finsys.os / maria2024")
print("="*60)
