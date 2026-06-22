"""
seed_hub.py — Script de datos sintéticos para el Project Hub
Crea: 1 workspace, 5 usuarios, jerarquía de entidades, 3 proyectos,
      20 tareas, 5 notas, 8 eventos de calendario.

Uso: python scripts/seed_hub.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar .env
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

import requests
from datetime import datetime, timedelta, date, timezone

BASE = "http://localhost:8000/api/hub"

def post(path, data):
    r = requests.post(f"{BASE}{path}", json=data, timeout=15)
    if not r.ok:
        print(f"  ❌ POST {path}: {r.status_code} — {r.text[:200]}")
        return None
    result = r.json()
    print(f"  ✅ POST {path}: OK")
    return result

def get(path):
    r = requests.get(f"{BASE}{path}", timeout=15)
    return r.json() if r.ok else []

def today_plus(days):
    return (date.today() + timedelta(days=days)).isoformat()

def dt_iso(days=0, hour=9):
    dt = datetime.now(timezone.utc) + timedelta(days=days)
    return dt.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()

# ════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 60)
print("  PROJECT HUB — SEED DE DATOS SINTÉTICOS")
print("═" * 60)

# ── 1. WORKSPACE ─────────────────────────────────────────────────────────────
print("\n[1/6] Creando workspace...")
ws_data = post("/workspaces", {
    "name": "Inversiones FIN-SYS",
    "nit": "900.123.456-7",
})
if not ws_data:
    print("FATAL: No se pudo crear workspace. ¿Está el backend corriendo?")
    sys.exit(1)

WS_ID = ws_data["workspace"]["id"]
print(f"       Workspace ID: {WS_ID}")

# ── 2. USUARIOS ───────────────────────────────────────────────────────────────
print("\n[2/6] Creando usuarios...")
USERS_DEF = [
    {"email": "andres@finsys.io",    "password": "admin123",  "name": "Andrés Ramírez",    "cedula": "1.020.789.123", "role": "owner",  "description": "Fundador y Director General. Supervisa todas las operaciones de la empresa y toma decisiones estratégicas."},
    {"email": "sofia@finsys.io",     "password": "sofia123",  "name": "Sofía Martínez",    "cedula": "1.035.456.789", "role": "admin",  "description": "Directora de Operaciones. Coordina proyectos, gestiona el equipo y garantiza el cumplimiento de plazos."},
    {"email": "camilo@finsys.io",    "password": "camilo123", "name": "Camilo Torres",     "cedula": "1.018.234.567", "role": "member", "description": "Desarrollador Full-Stack. Especialista en React, FastAPI y bases de datos PostgreSQL."},
    {"email": "valentina@finsys.io", "password": "vale123",   "name": "Valentina Gómez",  "cedula": "1.032.567.890", "role": "member", "description": "Analista Financiera. Experta en contabilidad, KPIs y reportes de gestión empresarial."},
    {"email": "daniel@finsys.io",    "password": "daniel123", "name": "Daniel Ospina",     "cedula": "1.025.678.901", "role": "viewer", "description": "Diseñador UX/UI. Crea interfaces brutalistas técnicas con enfoque en la experiencia del usuario."},
]

USERS = {}
for u_def in USERS_DEF:
    result = post("/users/register", {**u_def, "workspace_id": WS_ID})
    if result:
        USERS[u_def["email"]] = result["user"]

if not USERS:
    print("FATAL: Sin usuarios creados.")
    sys.exit(1)

# IDs fáciles de referenciar
U = {
    "andres":    USERS.get("andres@finsys.io",    {}).get("id"),
    "sofia":     USERS.get("sofia@finsys.io",     {}).get("id"),
    "camilo":    USERS.get("camilo@finsys.io",    {}).get("id"),
    "valentina": USERS.get("valentina@finsys.io", {}).get("id"),
    "daniel":    USERS.get("daniel@finsys.io",    {}).get("id"),
}

# ── 3. ENTIDADES (árbol jerárquico) ───────────────────────────────────────────
print("\n[3/6] Creando árbol de entidades...")

# Nivel 0 — Holding
holding = post("/entities", {"workspace_id": WS_ID, "name": "Inversiones FIN-SYS Holding", "entity_type": "HOLDING", "color": "#EF4444"})
H_ID = holding["entity"]["id"] if holding else None

if H_ID:
    # Nivel 1 — Empresas
    tec = post("/entities", {"workspace_id": WS_ID, "name": "FIN-SYS Tech",       "entity_type": "EMPRESA", "parent_id": H_ID, "color": "#0EA5E9"})
    fin = post("/entities", {"workspace_id": WS_ID, "name": "FIN-SYS Capital",    "entity_type": "EMPRESA", "parent_id": H_ID, "color": "#F59E0B"})
    con = post("/entities", {"workspace_id": WS_ID, "name": "FIN-SYS Consulting", "entity_type": "EMPRESA", "parent_id": H_ID, "color": "#10B981"})

    TEC_ID = tec["entity"]["id"] if tec else None
    FIN_ID = fin["entity"]["id"] if fin else None
    CON_ID = con["entity"]["id"] if con else None

    if TEC_ID:
        # Nivel 2 — Proyectos bajo Tech
        post("/entities", {"workspace_id": WS_ID, "name": "Equipo Backend",   "entity_type": "EQUIPO",    "parent_id": TEC_ID, "color": "#8B5CF6"})
        post("/entities", {"workspace_id": WS_ID, "name": "Equipo Frontend",  "entity_type": "EQUIPO",    "parent_id": TEC_ID, "color": "#EC4899"})
        post("/entities", {"workspace_id": WS_ID, "name": "Módulo Trading",   "entity_type": "PROYECTO",  "parent_id": TEC_ID, "color": "#0EA5E9"})

    if FIN_ID:
        post("/entities", {"workspace_id": WS_ID, "name": "Portafolio Pegasus", "entity_type": "PROYECTO", "parent_id": FIN_ID, "color": "#F59E0B"})
        post("/entities", {"workspace_id": WS_ID, "name": "Portafolio Negocio A", "entity_type": "PROYECTO", "parent_id": FIN_ID, "color": "#F59E0B"})

# ── 4. PROYECTOS ──────────────────────────────────────────────────────────────
print("\n[4/6] Creando proyectos y tareas...")

proj_tech = post("/projects", {
    "workspace_id": WS_ID,
    "name": "FIN-SYS OS — Plataforma Principal",
    "description": "Desarrollo y mantenimiento del sistema operativo financiero v2.0",
    "color": "#0EA5E9",
    "entity_id": TEC_ID if H_ID else None,
    "created_by": U["andres"],
})
PT_ID = proj_tech["project"]["id"] if proj_tech else None

proj_trading = post("/projects", {
    "workspace_id": WS_ID,
    "name": "Módulo 08 — Trading NASDAQ",
    "description": "Tracking de posiciones, cálculo PnL e integración con datos de mercado en tiempo real.",
    "color": "#10B981",
    "entity_id": TEC_ID if H_ID else None,
    "created_by": U["andres"],
})
PTR_ID = proj_trading["project"]["id"] if proj_trading else None

proj_ops = post("/projects", {
    "workspace_id": WS_ID,
    "name": "Operaciones Q2 2026",
    "description": "Gestión de operaciones y entregables del segundo trimestre de 2026.",
    "color": "#8B5CF6",
    "created_by": U["sofia"],
})
PO_ID = proj_ops["project"]["id"] if proj_ops else None

# ── 5. TAREAS ─────────────────────────────────────────────────────────────────

# Tareas proyecto Tech (FIN-SYS OS)
TASKS_TECH = [
    {"title": "Migrar endpoints de Control Tower a Router separado",       "status": "done",        "priority": "high",   "due_date": today_plus(-10), "assignee_ids": [U["camilo"]], "description": "Extraer todos los endpoints /api/ct/* a un APIRouter independiente para mejorar la modularidad del server.py."},
    {"title": "Implementar caché Redis para KPIs del CT",                  "status": "done",        "priority": "medium", "due_date": today_plus(-5),  "assignee_ids": [U["camilo"], U["valentina"]], "description": "Los KPIs del Control Tower tardan >2s. Implementar Redis con TTL de 60s para consultas frecuentes."},
    {"title": "Diseñar sistema de notificaciones en tiempo real",          "status": "in_progress", "priority": "high",   "due_date": today_plus(5),   "assignee_ids": [U["camilo"], U["daniel"]], "description": "Implementar WebSockets o SSE para notificaciones de nuevas transacciones y alertas de saldo bajo."},
    {"title": "Actualizar AGENTS.md con reglas del Project Hub",           "status": "done",        "priority": "low",    "due_date": today_plus(-3),  "assignee_ids": [U["sofia"]], "description": "Documentar las reglas de Zero-Impact para el Módulo 08 en el archivo AGENTS.md."},
    {"title": "Pruebas de carga en endpoints /api/hub/*",                  "status": "todo",        "priority": "medium", "due_date": today_plus(10),  "assignee_ids": [U["camilo"]], "description": "Ejecutar pruebas con Locust para medir la capacidad del backend bajo 100 usuarios concurrentes."},
    {"title": "Integrar Supabase Realtime en TaskBoard",                   "status": "in_progress", "priority": "high",   "due_date": today_plus(7),   "assignee_ids": [U["camilo"], U["daniel"]], "description": "Usar Supabase Realtime para actualizar el Kanban automáticamente cuando otro usuario mueve una tarea."},
    {"title": "Audit de seguridad: reemplazar SHA-256 por bcrypt",         "status": "todo",        "priority": "urgent", "due_date": today_plus(3),   "assignee_ids": [U["camilo"]], "description": "La contraseña en hub_driver.py usa SHA-256. Migrar a bcrypt para producción."},
    {"title": "Crear tests unitarios para hub_driver.py",                  "status": "review",      "priority": "medium", "due_date": today_plus(8),   "assignee_ids": [U["camilo"]], "description": "Escribir pytest para las funciones CRUD del hub_driver. Mínimo 80% de cobertura."},
]

# Tareas proyecto Trading
TASKS_TRADING = [
    {"title": "Definir esquema de tablas trading_*",                       "status": "done",        "priority": "high",   "due_date": today_plus(-7),  "assignee_ids": [U["andres"], U["camilo"]], "description": "Diseñar las tablas: trading_positions, trading_trades, trading_watchlist, trading_pnl_daily."},
    {"title": "Integración con API de Alpaca Markets",                     "status": "in_progress", "priority": "urgent", "due_date": today_plus(14),  "assignee_ids": [U["camilo"]], "description": "Conectar con Alpaca Paper Trading API para obtener cotizaciones NASDAQ-100 en tiempo real."},
    {"title": "Componente gráfico de velas (candlestick)",                 "status": "todo",        "priority": "high",   "due_date": today_plus(21),  "assignee_ids": [U["daniel"], U["camilo"]], "description": "Implementar chart de velas con Recharts o TradingView Lightweight Charts para el módulo trading."},
    {"title": "Cálculo automático de PnL diario y acumulado",              "status": "todo",        "priority": "high",   "due_date": today_plus(18),  "assignee_ids": [U["valentina"], U["camilo"]], "description": "Fórmula: PnL = (precio_actual - precio_entrada) * cantidad. Considerar comisiones y FX."},
    {"title": "Dashboard de portfolio con heatmap sectorial",              "status": "todo",        "priority": "medium", "due_date": today_plus(28),  "assignee_ids": [U["daniel"]], "description": "Vista visual del portafolio con colores por sector (Tech, Finance, Energy) y tamaño por peso."},
    {"title": "Alertas de stop-loss y take-profit por email/WhatsApp",     "status": "todo",        "priority": "medium", "due_date": today_plus(35),  "assignee_ids": [U["camilo"], U["valentina"]], "description": "Enviar notificación automática cuando una posición alcanza el nivel de stop-loss o take-profit configurado."},
]

# Tareas Operaciones Q2
TASKS_OPS = [
    {"title": "Revisar estados financieros de Mayo 2026",                  "status": "done",        "priority": "high",   "due_date": today_plus(-8),  "assignee_ids": [U["valentina"]], "description": "Conciliar transacciones de FIN-SYS OS con estados de cuenta de los 7 bancos activos."},
    {"title": "Preparar informe de KPIs para junta directiva",             "status": "review",      "priority": "urgent", "due_date": today_plus(2),   "assignee_ids": [U["valentina"], U["sofia"]], "description": "Dashboard ejecutivo con: ROI por portafolio, balance holding, GMF pagado, flujo neto Q2."},
    {"title": "Renovar contratos con proveedores de tecnología",           "status": "in_progress", "priority": "medium", "due_date": today_plus(15),  "assignee_ids": [U["sofia"]], "description": "Revisar contratos de Supabase, Groq API, Gemini API y negociar planes anuales con descuento."},
    {"title": "Capacitación del equipo en nuevo módulo Project Hub",       "status": "todo",        "priority": "low",    "due_date": today_plus(20),  "assignee_ids": [U["sofia"], U["daniel"], U["camilo"], U["valentina"]], "description": "Sesión de 2 horas para presentar el Módulo 08: registro, workspaces, tareas, notas y calendario."},
    {"title": "Auditoría de permisos de base de datos Supabase",          "status": "todo",        "priority": "high",   "due_date": today_plus(12),  "assignee_ids": [U["camilo"], U["andres"]], "description": "Revisar RLS policies, roles de BD y auditar accesos a las tablas financieras sensibles."},
    {"title": "Migración a infraestructura de producción (Dokploy)",       "status": "todo",        "priority": "high",   "due_date": today_plus(45),  "assignee_ids": [U["camilo"], U["andres"]], "description": "Dockerizar FastAPI, configurar Nginx como reverse proxy y desplegar en servidor VPS con Dokploy."},
]

all_tasks_created = []

def create_tasks(project_id, tasks_list):
    for t in tasks_list:
        if not project_id:
            continue
        assignees = [a for a in t.get("assignee_ids", []) if a]
        result = post("/tasks", {
            "workspace_id": WS_ID,
            "project_id": project_id,
            "title": t["title"],
            "description": t.get("description", ""),
            "status": t["status"],
            "priority": t["priority"],
            "due_date": t.get("due_date"),
            "created_by": U["andres"],
            "assignee_ids": assignees,
        })
        if result and result.get("task"):
            # Si está done, simular completed_at
            if t["status"] == "done":
                task_id = result["task"]["id"]
                requests.put(f"{BASE}/tasks/{task_id}", json={
                    "started_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
                    "completed_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                }, timeout=10)
            all_tasks_created.append(result["task"])

create_tasks(PT_ID,  TASKS_TECH)
create_tasks(PTR_ID, TASKS_TRADING)
create_tasks(PO_ID,  TASKS_OPS)

print(f"       {len(all_tasks_created)} tareas creadas en 3 proyectos")

# ── 6. NOTAS ──────────────────────────────────────────────────────────────────
print("\n[5/6] Creando notas...")

NOTES_DEF = [
    {
        "user_id": U["andres"], "title": "🏗️ Arquitectura del Sistema — Notas del CEO",
        "is_private": False,
        "content": [
            {"id": "a1", "type": "heading", "props": {"level": 1, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Arquitectura FIN-SYS OS v2.0", "styles": {}}], "children": []},
            {"id": "a2", "type": "paragraph", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Este documento describe la arquitectura general del sistema. El stack tecnológico está diseñado para escalar de manera independiente por módulos.", "styles": {}}], "children": []},
            {"id": "a3", "type": "heading", "props": {"level": 2, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Módulos Activos", "styles": {}}], "children": []},
            {"id": "a4", "type": "bulletListItem", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Módulo 01-06: Registro y contabilidad principal (COMPLETO)", "styles": {"bold": True}}], "children": []},
            {"id": "a5", "type": "bulletListItem", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Módulo 07: Control Tower — árbol de 4 niveles (COMPLETO)", "styles": {}}], "children": []},
            {"id": "a6", "type": "bulletListItem", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Módulo 08: Project Hub — colaboración multi-tenant (COMPLETO)", "styles": {}}], "children": []},
            {"id": "a7", "type": "bulletListItem", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Módulo 09: Trading NASDAQ-100 (EN DESARROLLO)", "styles": {}}], "children": []},
            {"id": "a8", "type": "heading", "props": {"level": 2, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Decisiones Técnicas Clave", "styles": {}}], "children": []},
            {"id": "a9", "type": "checkListItem", "props": {"checked": True, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Zero-Impact Policy: nuevos módulos en carpetas aisladas", "styles": {}}], "children": []},
            {"id": "a10", "type": "checkListItem", "props": {"checked": True, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Git con ramas por feature (modulo-07-ct, modulo-08-hub...)", "styles": {}}], "children": []},
            {"id": "a11", "type": "checkListItem", "props": {"checked": False, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Dockerizar para producción con Dokploy", "styles": {}}], "children": []},
            {"id": "a12", "type": "checkListItem", "props": {"checked": False, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Implementar Redis para caché de KPIs", "styles": {}}], "children": []},
        ]
    },
    {
        "user_id": U["valentina"], "title": "📊 KPIs Financieros Q2 — Borrador",
        "is_private": True,
        "content": [
            {"id": "b1", "type": "heading", "props": {"level": 1, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "KPIs Financieros Q2 2026", "styles": {}}], "children": []},
            {"id": "b2", "type": "paragraph", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "BORRADOR — No compartir hasta revisión del CEO", "styles": {"bold": True, "italic": True}}], "children": []},
            {"id": "b3", "type": "table", "props": {}, "content": [{"type": "tableRow", "rows": [{"cells": [{"type": "text", "text": "Portafolio"}, {"type": "text", "text": "Balance"}, {"type": "text", "text": "Variación"}]}, {"cells": [{"type": "text", "text": "Negocio A"}, {"type": "text", "text": "$18,500,000"}, {"type": "text", "text": "+12.3%"}]}, {"cells": [{"type": "text", "text": "Pegasus"}, {"type": "text", "text": "$8,750,000"}, {"type": "text", "text": "+5.8%"}]}]}], "children": []},
            {"id": "b4", "type": "paragraph", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Balance Holding Total: $42,222,500 (+8.7% vs Q1)", "styles": {"bold": True}}], "children": []},
        ]
    },
    {
        "user_id": U["camilo"], "title": "🛠️ Guía de Desarrollo — Módulo Trading",
        "is_private": False,
        "content": [
            {"id": "c1", "type": "heading", "props": {"level": 1, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Módulo 09 Trading — Guía Técnica", "styles": {}}], "children": []},
            {"id": "c2", "type": "heading", "props": {"level": 2, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Stack", "styles": {}}], "children": []},
            {"id": "c3", "type": "bulletListItem", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "API: Alpaca Markets (paper trading para desarrollo)", "styles": {}}], "children": []},
            {"id": "c4", "type": "bulletListItem", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Charts: TradingView Lightweight Charts v4", "styles": {}}], "children": []},
            {"id": "c5", "type": "bulletListItem", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Carpeta: frontend/src/trading/ (nueva, aislada)", "styles": {}}], "children": []},
            {"id": "c6", "type": "heading", "props": {"level": 2, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Comandos útiles", "styles": {}}], "children": []},
            {"id": "c7", "type": "codeBlock", "props": {"language": "bash"}, "content": [{"type": "text", "text": "# Verificar conexión con Alpaca\npython scripts/test_alpaca.py\n\n# Ejecutar health check completo\npython scripts/health_check.py", "styles": {}}], "children": []},
        ]
    },
    {
        "user_id": U["daniel"], "title": "🎨 Design System — Project Hub",
        "is_private": False,
        "content": [
            {"id": "d1", "type": "heading", "props": {"level": 1, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Design System — Project Hub", "styles": {}}], "children": []},
            {"id": "d2", "type": "heading", "props": {"level": 2, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Paleta de Colores", "styles": {}}], "children": []},
            {"id": "d3", "type": "bulletListItem", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Fondo: #0a0a0a — negro profundo", "styles": {}}], "children": []},
            {"id": "d4", "type": "bulletListItem", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Acento: #0EA5E9 — cian sky (diferenciado del amber #fbbf24 del CT)", "styles": {}}], "children": []},
            {"id": "d5", "type": "bulletListItem", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Éxito: #10B981 — verde esmeralda", "styles": {}}], "children": []},
            {"id": "d6", "type": "bulletListItem", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Alerta: #F59E0B — ámbar (warnings, vencimientos)", "styles": {}}], "children": []},
            {"id": "d7", "type": "bulletListItem", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Error: #EF4444 — rojo coral", "styles": {}}], "children": []},
            {"id": "d8", "type": "heading", "props": {"level": 2, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Tipografía", "styles": {}}], "children": []},
            {"id": "d9", "type": "paragraph", "props": {"textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "IBM Plex Mono en todo el sistema. Bordes 2px, border-radius 0px. Sombras duras (box-shadow sin blur).", "styles": {}}], "children": []},
        ]
    },
    {
        "user_id": U["sofia"], "title": "📋 Agenda Semanal — Semana del 9 Jun 2026",
        "is_private": False,
        "content": [
            {"id": "e1", "type": "heading", "props": {"level": 1, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "Agenda Semana 9-13 Junio 2026", "styles": {}}], "children": []},
            {"id": "e2", "type": "checkListItem", "props": {"checked": True, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "LUN 9: Revisión estados financieros Mayo con Valentina", "styles": {}}], "children": []},
            {"id": "e3", "type": "checkListItem", "props": {"checked": True, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "MAR 10: Sprint planning Módulo Trading con Camilo", "styles": {}}], "children": []},
            {"id": "e4", "type": "checkListItem", "props": {"checked": False, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "MIÉ 11: Presentación Project Hub al equipo completo", "styles": {}}], "children": []},
            {"id": "e5", "type": "checkListItem", "props": {"checked": False, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "JUE 12: Informe KPIs para junta directiva (borrador final)", "styles": {}}], "children": []},
            {"id": "e6", "type": "checkListItem", "props": {"checked": False, "textAlignment": "left", "textColor": "default", "backgroundColor": "default"}, "content": [{"type": "text", "text": "VIE 13: Revisión contratos Supabase y Groq API", "styles": {}}], "children": []},
        ]
    },
]

for n_def in NOTES_DEF:
    r = post("/notes", {"workspace_id": WS_ID, "user_id": n_def["user_id"], "title": n_def["title"]})
    if r and r.get("note"):
        note_id = r["note"]["id"]
        requests.put(f"{BASE}/notes/{note_id}", json={
            "content": n_def["content"],
            "is_private": n_def["is_private"],
        }, timeout=15)

# ── 7. EVENTOS DE CALENDARIO ──────────────────────────────────────────────────
print("\n[6/6] Creando eventos de calendario...")

EVENTS_DEF = [
    {
        "title": "🚀 Sprint Review — FIN-SYS OS",
        "description": "Revisión del sprint actual. Presentar: Project Hub completo, pruebas de carga, próximos pasos.",
        "start_time": dt_iso(days=1, hour=10), "end_time": dt_iso(days=1, hour=11),
        "color": "#0EA5E9", "all_day": False,
        "attendee_ids": [U["andres"], U["sofia"], U["camilo"], U["valentina"], U["daniel"]],
    },
    {
        "title": "📊 Presentación KPIs — Junta Directiva",
        "description": "Informe ejecutivo Q2 2026: ROI por portafolio, balance holding, proyecciones Q3.",
        "start_time": dt_iso(days=2, hour=14), "end_time": dt_iso(days=2, hour=16),
        "color": "#F59E0B", "all_day": False,
        "attendee_ids": [U["andres"], U["valentina"]],
    },
    {
        "title": "⚙️ Sprint Planning — Módulo Trading",
        "description": "Definir backlog del Módulo 09 Trading: API Alpaca, gráfico velas, PnL, alertas stop-loss.",
        "start_time": dt_iso(days=3, hour=9), "end_time": dt_iso(days=3, hour=11),
        "color": "#10B981", "all_day": False,
        "attendee_ids": [U["andres"], U["camilo"]],
    },
    {
        "title": "🎓 Capacitación Project Hub",
        "description": "Sesión de onboarding del Módulo 08 para todo el equipo. Duración 2 horas.",
        "start_time": dt_iso(days=4, hour=15), "end_time": dt_iso(days=4, hour=17),
        "color": "#8B5CF6", "all_day": False,
        "attendee_ids": [U["sofia"], U["camilo"], U["valentina"], U["daniel"]],
    },
    {
        "title": "🔐 Auditoría de Seguridad BD",
        "description": "Revisión de RLS policies, roles de base de datos y accesos a tablas financieras sensibles.",
        "start_time": dt_iso(days=7, hour=10), "end_time": dt_iso(days=7, hour=12),
        "color": "#EF4444", "all_day": False,
        "attendee_ids": [U["camilo"], U["andres"]],
    },
    {
        "title": "📅 Renovación Contratos SaaS",
        "description": "Revisión anual de contratos: Supabase Pro, Groq API, Gemini API. Negociar descuentos.",
        "start_time": dt_iso(days=10, hour=11), "end_time": dt_iso(days=10, hour=12),
        "color": "#64748b", "all_day": False,
        "attendee_ids": [U["sofia"]],
    },
    {
        "title": "📦 Deadline — Informe Q2 Final",
        "description": "Entrega del informe financiero completo del Q2 2026 para todos los portafolios.",
        "start_time": dt_iso(days=14, hour=0), "end_time": dt_iso(days=14, hour=23),
        "color": "#EC4899", "all_day": True,
        "attendee_ids": [U["valentina"], U["andres"], U["sofia"]],
    },
    {
        "title": "🐳 Go-Live Producción (Dokploy)",
        "description": "Despliegue definitivo de FIN-SYS OS v2.0 en servidor de producción. Hito crítico.",
        "start_time": dt_iso(days=45, hour=9), "end_time": dt_iso(days=45, hour=18),
        "color": "#0EA5E9", "all_day": True,
        "attendee_ids": [U["andres"], U["camilo"]],
    },
]

for e_def in EVENTS_DEF:
    attendees = [a for a in e_def.pop("attendee_ids", []) if a]
    post("/events", {**e_def, "workspace_id": WS_ID, "created_by": U["andres"], "attendee_ids": attendees})

# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 60)
print("  ✅ SEED COMPLETO")
print("═" * 60)
print(f"\n  Workspace:  Inversiones FIN-SYS  (ID: {WS_ID[:8]}...)")
print(f"  Usuarios:   {len(USERS)} creados")
print(f"  Entidades:  árbol de 3 niveles (holding → empresa → equipo)")
print(f"  Proyectos:  3 (Tech, Trading, Ops)")
print(f"  Tareas:     {len(all_tasks_created)} distribuidas entre 3 proyectos")
print(f"  Notas:      5 con contenido BlockNote real")
print(f"  Eventos:    8 en el calendario (próximas 6 semanas)")
print()
print("  CREDENCIALES DE ACCESO:")
print("  ─────────────────────────────────────────────────────────")
for u_def in USERS_DEF:
    print(f"  [{u_def['role'].upper():6}]  {u_def['email']:30}  /  {u_def['password']}")
print("═" * 60)
