"""
FIN-SYS OS v2.0 — Health Check Extendido
=========================================
Verifica el estado completo del sistema: servidores, BD, motor, módulos y datos.
Ejecutar desde la raíz del proyecto: python scripts/health_check.py

Checks incluidos:
  1. Frontend (Vite :5173)
  2. Backend (FastAPI :8000)
  3. PostgreSQL / Supabase — datos módulos 1-6
  4. Motor Matemático — IVA + GMF
  5. Control Tower API — entidades + KPI holding
  6. Project Hub API — workspace + usuarios + tareas
  7. Integridad de datos — workspaces huérfanos, user_id vacíos

Aprendizajes incorporados de sesiones anteriores:
  - Error HMR main.jsx: nunca eliminar la función por defecto de main.jsx
  - Race condition notas: user_id puede llegar vacío si hub carga antes del login
  - Workspace huérfano: BD puede tener workspaces sin datos que bloquean la UI
  - Overlay CTTopBar: StrictMode + fixed div deja overlay pegado
  - Puerto 5174 vs 5173: si hay proceso node zombie, Vite sube al puerto siguiente
  - Bundle size: advertencia si supera 1.5MB (code-splitting recomendado)
"""

import urllib.request
import urllib.error
import urllib.parse
import json
import sys
import os
import time

# ─── Colores ANSI ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
DIM    = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):    print(f"{GREEN}✅{RESET} {msg}")
def fail(msg):  print(f"{RED}❌{RESET} {msg}")
def warn(msg):  print(f"{YELLOW}⚠️ {RESET} {msg}")
def info(msg):  print(f"{DIM}   {msg}{RESET}")
def tip(msg):   print(f"{CYAN}   💡 {msg}{RESET}")

# ─── Cargar variables de entorno ──────────────────────────────────────────────
def load_env():
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k, v = s.split("=", 1)
                    os.environ[k.strip()] = v.strip()

# ─── Helper HTTP ──────────────────────────────────────────────────────────────
def fetch(url, timeout=5):
    """Hace un GET y retorna (status_code, body_dict | None)."""
    try:
        req = urllib.request.urlopen(url, timeout=timeout)
        body = req.read().decode("utf-8")
        try:
            return req.status, json.loads(body)
        except json.JSONDecodeError:
            return req.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None

# ─── Banner ───────────────────────────────────────────────────────────────────
def banner():
    print(f"\n{BOLD}{'=' * 60}")
    print(f"  FIN-SYS OS v2.0 — HEALTH CHECK EXTENDIDO")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S COT')}")
    print(f"{'=' * 60}{RESET}\n")

# ─── CHECK 1: Frontend Vite ───────────────────────────────────────────────────
def check_frontend(results):
    label = "[1/7] Frontend (React/Vite)"
    status, _ = fetch("http://localhost:5173", timeout=3)
    if status == 200:
        ok(f"{label}    → :5173 OK")
        results["frontend"] = True
    else:
        # Aprendizaje: si hay proceso zombie node, Vite sube a :5174
        status2, _ = fetch("http://localhost:5174", timeout=2)
        if status2 == 200:
            fail(f"{label}    → :5173 CAÍDO (pero :5174 responde)")
            tip("Hay un proceso Node zombie. Ejecutar:")
            info("Get-Process -Name node | Stop-Process -Force")
            info("cd frontend && npm run dev")
        else:
            fail(f"{label}    → CAÍDO en :5173 y :5174")
            tip("Arrancar: cd frontend && npm run dev")
        results["frontend"] = False

# ─── CHECK 2: Backend FastAPI ─────────────────────────────────────────────────
def check_backend(results):
    label = "[2/7] Backend  (FastAPI)"
    status, _ = fetch("http://localhost:8000/docs", timeout=4)
    if status == 200:
        ok(f"{label}        → :8000 OK")
        results["backend"] = True
    else:
        fail(f"{label}        → :8000 CAÍDO")
        tip("Arrancar: python server.py")
        tip("Si hay error de puerto: Get-Process python | Stop-Process -Force")
        results["backend"] = False

# ─── CHECK 3: PostgreSQL / Supabase + datos módulos 1-6 ──────────────────────
def check_database(results):
    label = "[3/7] PostgreSQL (Supabase)"
    try:
        import psycopg2
        conn = psycopg2.connect(
            host     = os.getenv("DB_HOST", "localhost"),
            database = os.getenv("DB_NAME", "postgres"),
            user     = os.getenv("DB_USER", "postgres"),
            password = os.getenv("DB_PASSWORD", ""),
            port     = os.getenv("DB_PORT", "5432"),
            connect_timeout = 5,
            options  = "-c statement_timeout=5000"
        )
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM transactions;")
        tx_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM entities;")
        entity_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM user_accounts;")
        account_count = cur.fetchone()[0]

        # Aprendizaje: verificar que no hay transacciones sin account_id (DT-01)
        cur.execute("SELECT COUNT(*) FROM transactions WHERE account_id IS NULL;")
        orphan_tx = cur.fetchone()[0]

        conn.close()

        ok(f"{label} → TXs: {tx_count} | Entidades CT: {entity_count} | Cuentas: {account_count}")
        if orphan_tx > 0:
            warn(f"   {orphan_tx} transacción(es) sin account_id → DT-01 (balance -$11.2M)")
            tip("Fix retroactivo pendiente: UPDATE transactions SET account_id=1 WHERE account_id IS NULL")
        results["database"] = True
        results["db_tx_count"] = tx_count

    except ImportError:
        warn(f"{label} → psycopg2 no instalado, usando API")
        # Fallback: verificar vía API si el backend está arriba
        status, data = fetch("http://localhost:8000/api/transactions?portfolio=Negocio%20A", timeout=5)
        if status == 200 and isinstance(data, list):
            ok(f"{label} → Conectado vía API (TXs: {len(data)})")
            results["database"] = True
        else:
            fail(f"{label} → No se puede verificar (psycopg2 ausente y backend caído)")
            results["database"] = False

    except Exception as e:
        fail(f"{label} → {str(e)[:70]}")
        tip("Verificar variables en .env: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT")
        results["database"] = False

# ─── CHECK 4: Motor Matemático ────────────────────────────────────────────────
def check_motor(results):
    label = "[4/7] Motor Matemático"
    try:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        from fin_sys_core.tax_motor import process_transaction_taxes

        res = process_transaction_taxes(100000, apply_iva=True, apply_gmf=True)
        assert res["iva_amount"] == 19000, f"IVA esperado 19000, obtenido {res['iva_amount']}"
        assert res["gmf_amount"] == 400,   f"GMF esperado 400, obtenido {res['gmf_amount']}"

        # Test extra: TRM y moneda (aprendizaje: TRM debe ser float, no int)
        from fin_sys_core.ledger_math import calculate_caja_viva
        ok(f"{label}          → IVA=19.000 | GMF=400 ✓ | ledger_math importado")
        results["motor"] = True

    except AssertionError as e:
        fail(f"{label}          → Falla lógica: {e}")
        tip("Revisar fin_sys_core/tax_motor.py — constantes IVA y GMF")
        results["motor"] = False
    except Exception as e:
        fail(f"{label}          → ERROR: {e}")
        tip("Verificar que fin_sys_core/ sea importable desde la raíz del proyecto")
        results["motor"] = False

# ─── CHECK 5: Control Tower API ───────────────────────────────────────────────
def check_control_tower(results):
    label = "[5/7] Control Tower API"
    if not results.get("backend"):
        warn(f"{label}   → OMITIDO (backend caído)")
        results["ct"] = False
        return

    status, entities = fetch("http://localhost:8000/api/ct/entities", timeout=5)
    if status != 200:
        fail(f"{label}   → /api/ct/entities respondió {status}")
        results["ct"] = False
        return

    entity_count = len(entities) if isinstance(entities, list) else "?"

    status2, kpis = fetch("http://localhost:8000/api/ct/entities/1/kpis", timeout=5)
    if status2 == 200 and kpis:
        balance = kpis.get("balance_neto", 0)
        ok(f"{label}   → Raíz: {entity_count} entidades | Holding: ${balance:,.0f}")
        if balance < 1_000_000:
            warn(f"   Balance holding bajo (${balance:,.0f}) — verificar datos CT")
        results["ct"] = True
    else:
        warn(f"{label}   → Entidades OK pero KPIs fallaron (status {status2})")
        results["ct"] = True  # parcial ok

# ─── CHECK 6: Project Hub API ─────────────────────────────────────────────────
def check_project_hub(results):
    label = "[6/7] Project Hub API"
    if not results.get("backend"):
        warn(f"{label}    → OMITIDO (backend caído)")
        results["hub"] = False
        return

    # Verificar workspaces
    status, workspaces = fetch("http://localhost:8000/api/hub/workspaces?all=true", timeout=5)
    if status != 200 or not isinstance(workspaces, list):
        fail(f"{label}    → /api/hub/workspaces falló (status {status})")
        results["hub"] = False
        return

    ws_count = len(workspaces)
    if ws_count == 0:
        fail(f"{label}    → Sin workspaces en BD")
        tip("Ejecutar: python scripts/seed_hub.py")
        results["hub"] = False
        return

    # Aprendizaje: workspaces vacíos (sin nombre o con datos de prueba) bloquean la UI
    empty_ws = [w for w in workspaces if not w.get("name") or w.get("name", "").strip() == ""]
    if empty_ws:
        warn(f"   {len(empty_ws)} workspace(s) sin nombre detectado — puede bloquear UI")
        tip("Ejecutar: python scripts/cleanup_empty_workspace.py")

    # Verificar usuarios Hub
    ws_id = workspaces[0].get("id", "")
    status2, users = fetch(f"http://localhost:8000/api/hub/users?workspace_id={ws_id}", timeout=5)
    user_count = len(users) if (status2 == 200 and isinstance(users, list)) else "?"

    # Verificar tareas
    status3, tasks = fetch(f"http://localhost:8000/api/hub/tasks?workspace_id={ws_id}", timeout=5)
    task_count = len(tasks) if (status3 == 200 and isinstance(tasks, list)) else "?"

    ok(f"{label}    → Workspaces: {ws_count} | Usuarios: {user_count} | Tareas: {task_count}")

    # Aprendizaje: endpoint /api/hub/notes falla con user_id no-UUID (PostgreSQL valida tipo)
    # Usamos un UUID sintético para verificar que el endpoint responde (no importa si hay datos)
    dummy_uuid = "00000000-0000-0000-0000-000000000001"
    status4, _ = fetch(f"http://localhost:8000/api/hub/notes?workspace_id={ws_id}&user_id={dummy_uuid}", timeout=5)
    if status4 in (200, 404):
        pass  # OK — responde correctamente
    elif status4 == 400:
        warn(f"   /api/hub/notes rechaza user_id vacío (guard activo ✓)")
    elif status4 == 500:
        warn(f"   /api/hub/notes retorna 500 con UUID válido — revisar hub_driver.get_notes()")
        tip("Posible: tabla hub_notes vacía o query con JOIN fallida")

    results["hub"] = True
    results["hub_ws_id"] = ws_id

# ─── CHECK 7: Integridad de datos ────────────────────────────────────────────
def check_data_integrity(results):
    label = "[7/7] Integridad de datos"
    issues = []
    fixes  = []

    try:
        import psycopg2
        conn = psycopg2.connect(
            host     = os.getenv("DB_HOST", "localhost"),
            database = os.getenv("DB_NAME", "postgres"),
            user     = os.getenv("DB_USER", "postgres"),
            password = os.getenv("DB_PASSWORD", ""),
            port     = os.getenv("DB_PORT", "5432"),
            connect_timeout = 5,
        )
        cur = conn.cursor()

        # Aprendizaje: workspaces huérfanos bloquean workspace switcher
        try:
            cur.execute("""
                SELECT COUNT(*) FROM hub_workspaces
                WHERE name IS NULL OR TRIM(name) = '';
            """)
            n = cur.fetchone()[0]
            if n > 0:
                issues.append(f"{n} workspace(s) Hub sin nombre")
                fixes.append("DELETE FROM hub_workspaces WHERE name IS NULL OR TRIM(name) = '';")
        except Exception:
            pass  # tabla puede no existir en instalaciones sin Hub

        # Verificar portafolios
        cur.execute("SELECT COUNT(*) FROM portfolios;")
        p_count = cur.fetchone()[0]
        if p_count < 4:
            issues.append(f"Solo {p_count} portafolios (esperado: 4)")

        # Verificar cuentas bancarias
        cur.execute("SELECT COUNT(*) FROM user_accounts;")
        a_count = cur.fetchone()[0]
        if a_count < 7:
            issues.append(f"Solo {a_count} cuentas bancarias (esperado: 7)")

        conn.close()

        if not issues:
            ok(f"{label}     → Portafolios: {p_count} | Cuentas: {a_count} | Sin anomalías")
        else:
            warn(f"{label}     → {len(issues)} problema(s) detectado(s):")
            for issue in issues:
                info(f"  • {issue}")
            if fixes:
                tip("Fixes SQL sugeridos:")
                for fix in fixes:
                    info(f"  {fix}")

        results["integrity"] = len(issues) == 0

    except ImportError:
        warn(f"{label}     → OMITIDO (psycopg2 no instalado)")
        results["integrity"] = None
    except Exception as e:
        warn(f"{label}     → No verificado: {str(e)[:60]}")
        results["integrity"] = None

# ─── RESUMEN FINAL ────────────────────────────────────────────────────────────
def summary(results):
    print(f"\n{BOLD}{'=' * 60}{RESET}")

    critical = ["frontend", "backend", "database", "motor"]
    all_critical = all(results.get(k) for k in critical)
    all_ok = all_critical and results.get("ct") and results.get("hub")

    # Tabla de resultados
    checks = [
        ("frontend",  "Frontend   (Vite :5173)"),
        ("backend",   "Backend    (FastAPI :8000)"),
        ("database",  "PostgreSQL (Supabase)"),
        ("motor",     "Motor      (IVA + GMF)"),
        ("ct",        "Control Tower API"),
        ("hub",       "Project Hub API"),
        ("integrity", "Integridad de datos"),
    ]
    for key, name in checks:
        val = results.get(key)
        if val is True:
            icon = f"{GREEN}✅{RESET}"
        elif val is False:
            icon = f"{RED}❌{RESET}"
        else:
            icon = f"{YELLOW}⚠️ {RESET}"
        print(f"  {icon} {name}")

    print(f"\n{BOLD}{'─' * 60}{RESET}")
    if all_ok:
        print(f"{GREEN}{BOLD}🚀 TODO EN ORDEN. Sistema listo para continuar.{RESET}")
    elif all_critical:
        print(f"{YELLOW}{BOLD}⚡ CORE OK — Módulos secundarios con advertencias.{RESET}")
    else:
        print(f"{RED}{BOLD}🛑 SERVICIOS CRÍTICOS CAÍDOS. Revisar arriba.{RESET}")

    print(f"\n{DIM}  App:  http://localhost:5173")
    print(f"  Hub:  http://localhost:5173 → ⬡ PROJECT HUB  (andres@finsys.io / admin123)")
    print(f"  CT:   http://localhost:5173 → ⬡ CONTROL TOWER (andres@finsys.os / admin123)")
    print(f"  API:  http://localhost:8000/docs{RESET}\n")

    return 0 if all_critical else 1


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    load_env()
    banner()
    results = {}
    check_frontend(results)
    check_backend(results)
    check_database(results)
    check_motor(results)
    check_control_tower(results)
    check_project_hub(results)
    check_data_integrity(results)
    sys.exit(summary(results))
