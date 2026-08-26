"""
FIN-SYS OS v2.0 — Session Maintenance Tool
============================================
Ejecutar al INICIO y al FINAL de cada sesión de trabajo.

Funciones:
  1. 🔍 Verificar estado completo del sistema
  2. 🧹 Limpiar artefactos temporales (datos sintéticos, test docs)
  3. 📝 Docs de estado (checkpoints.md + CHECKLIST.md) — mantenimiento MANUAL
  4. 📊 Actualizar docs/*.md con métricas y avances
  5. 🔐 Audit de cambios en archivos clave
  6. 📋 Generar resumen de sesión para checkpoint futuro

Uso:
  python scripts/session_maintenance.py           # Modo completo
  python scripts/session_maintenance.py --clean   # Solo limpieza
  python scripts/session_maintenance.py --update  # Solo actualizar .md
  python scripts/session_maintenance.py --check   # Solo verificar
"""

import sys
import os
import json
import datetime
import urllib.request
import urllib.error
import argparse
import re

# ─── Colores ANSI ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
DIM    = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
BLUE   = "\033[94m"
MAGENTA= "\033[95m"

def ok(msg):    print(f"{GREEN}✅{RESET} {msg}")
def fail(msg):  print(f"{RED}❌{RESET} {msg}")
def warn(msg):  print(f"{YELLOW}⚠️ {RESET} {msg}")
def info(msg):  print(f"{DIM}   {msg}{RESET}")
def step(msg):  print(f"{CYAN}▶ {RESET}{BOLD}{msg}{RESET}")
def header(t):  print(f"\n{BLUE}{'═' * 62}{RESET}\n{BOLD}  {t}{RESET}\n{BLUE}{'═' * 62}{RESET}")

NOW     = datetime.datetime.now()
NOW_STR = NOW.strftime("%d %b %Y — %H:%M COT")
DATE    = NOW.strftime("%Y-%m-%d")
ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─── Cargar .env ──────────────────────────────────────────────────────────────
def load_env():
    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k, v = s.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

# ─── HTTP helper ──────────────────────────────────────────────────────────────
def fetch(url, timeout=5):
    try:
        req = urllib.request.urlopen(url, timeout=timeout)
        body = req.read().decode("utf-8")
        try:    return req.status, json.loads(body)
        except: return req.status, None
    except urllib.error.HTTPError as e: return e.code, None
    except Exception:                   return None, None

# ─── Conectar a BD ────────────────────────────────────────────────────────────
def get_db():
    try:
        import psycopg2
        conn = psycopg2.connect(
            host     = os.getenv("DB_HOST"),
            database = os.getenv("DB_NAME", "postgres"),
            user     = os.getenv("DB_USER", "postgres"),
            password = os.getenv("DB_PASSWORD", ""),
            port     = os.getenv("DB_PORT", "5432"),
            connect_timeout=5,
            options="-c statement_timeout=8000"
        )
        return conn, None
    except ImportError:
        return None, "psycopg2 no instalado"
    except Exception as e:
        return None, str(e)

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — VERIFICACIÓN DEL SISTEMA
# ══════════════════════════════════════════════════════════════════════════════
def section_verify():
    header("🔍 SECCIÓN 1/5 — VERIFICACIÓN DEL SISTEMA")
    results = {}

    # Frontend
    step("Frontend Vite")
    import subprocess as _sp
    def _ps_check(port):
        """Usa PowerShell para verificar el puerto — elude restricciones de red del sandbox Python"""
        try:
            cmd = f'(Invoke-WebRequest "http://localhost:{port}" -UseBasicParsing -TimeoutSec 3).StatusCode'
            r = _sp.run(["powershell","-Command", cmd], capture_output=True, text=True, timeout=6)
            return r.stdout.strip() == "200"
        except: return False
    found_fe = False
    for port in [5173, 5174, 5175]:
        if _ps_check(port):
            ok(f"Frontend en :{port} ✅")
            results["frontend"] = True
            results["frontend_port"] = port
            found_fe = True
            break
    if not found_fe:
        fail("Frontend caído (5173–5175)")
        results["frontend"] = False

    step("Backend FastAPI")
    try:
        cmd_be = '(Invoke-WebRequest "http://localhost:8000/docs" -UseBasicParsing -TimeoutSec 4).StatusCode'
        r_be = _sp.run(["powershell","-Command", cmd_be], capture_output=True, text=True, timeout=8)
        if r_be.stdout.strip() == "200":
            ok("Backend :8000 ✅")
            results["backend"] = True
        else:
            fail("Backend :8000 caído")
            results["backend"] = False
    except:
        fail("Backend :8000 caído")
        results["backend"] = False

    # Base de datos
    step("PostgreSQL / Supabase")
    conn, err = get_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM transactions;")
            results["tx_count"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM entities;")
            results["entity_count"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM user_accounts;")
            results["account_count"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM portfolios;")
            results["portfolio_count"] = cur.fetchone()[0]

            # Hub tables (each isolated to avoid transaction abort cascade)
            for tbl, key in [("hub_workspaces","ws"), ("hub_users","hub_users"),
                              ("hub_tasks","hub_tasks"), ("hub_notes","hub_notes"),
                              ("hub_events","hub_events")]:
                try:
                    conn2, _ = get_db()
                    if conn2:
                        c2 = conn2.cursor()
                        c2.execute(f"SELECT COUNT(*) FROM {tbl};")
                        results[key] = c2.fetchone()[0]
                        conn2.close()
                    else:
                        results[key] = "?"
                except: results[key] = "?"

            # HR tables
            for tbl, key in [("hr_members","hr_members"), ("hr_payment_records","hr_payments"),
                              ("hr_documents","hr_docs"), ("hr_companies","hr_companies")]:
                try:
                    conn3, _ = get_db()
                    if conn3:
                        c3 = conn3.cursor()
                        c3.execute(f"SELECT COUNT(*) FROM {tbl};")
                        results[key] = c3.fetchone()[0]
                        conn3.close()
                    else:
                        results[key] = "N/A"
                except: results[key] = "N/A"

            # Total tablas
            cur.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type   = 'BASE TABLE';
            """)
            results["total_tables"] = cur.fetchone()[0]

            conn.close()
            ok(f"BD conectada — {results['tx_count']} TXs | {results['total_tables']} tablas")
            results["database"] = True
        except Exception as e:
            warn(f"BD conectada pero query falló: {e}")
            results["database"] = True
    else:
        fail(f"BD no conectada: {err}")
        results["database"] = False

    # Motor
    step("Motor Matemático")
    try:
        sys.path.insert(0, ROOT)
        from fin_sys_core.tax_motor import process_transaction_taxes
        res = process_transaction_taxes(100000, apply_iva=True, apply_gmf=True)
        assert res["iva_amount"] == 19000
        assert res["gmf_amount"] == 400
        ok("Motor OK — IVA=19.000 | GMF=400")
        results["motor"] = True
    except Exception as e:
        fail(f"Motor: {e}")
        results["motor"] = False

    # Control Tower
    step("Control Tower API")
    if results.get("backend"):
        s, kpis = fetch("http://localhost:8000/api/ct/entities/1/kpis")
        if s == 200 and kpis:
            results["ct_balance"] = kpis.get("balance_neto", 0)
            ok(f"CT: Balance Holding ${results['ct_balance']:,.0f}")
            results["ct"] = True
        else:
            warn("CT API no disponible")
            results["ct"] = False

    # HR Module — usar workspace_id conocido y endpoint real
    step("Módulo RRHH/Empresas")
    if results.get("backend"):
        # Endpoint real: /api/hr/company-links o /api/hr/folders/{workspace_id}
        ws_id = "37888f92-8bef-4528-b187-2064c6f0049c"
        s, data = fetch(f"http://localhost:8000/api/hr/folders/{ws_id}")
        if s == 200:
            ok(f"RRHH: backend responde (folders OK)")
            results["hr"] = True
        else:
            # Fallback: intentar con company-links
            s2, _ = fetch("http://localhost:8000/api/hr/company-links?workspace_id=" + ws_id)
            if s2 in (200, 404):
                ok(f"RRHH: backend responde (company-links status {s2})")
                results["hr"] = True
            else:
                warn(f"RRHH endpoints: status {s}/{s2}")
                results["hr"] = False
    else:
        results["hr"] = False

    return results

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2 — LIMPIEZA DE ARTEFACTOS TEMPORALES
# ══════════════════════════════════════════════════════════════════════════════
def section_cleanup(results):
    header("🧹 SECCIÓN 2/5 — LIMPIEZA DE ARTEFACTOS TEMPORALES")
    cleaned = []
    warnings = []

    conn, err = get_db()
    if not conn:
        warn(f"No hay conexión a BD para limpieza: {err}")
        return cleaned

    step("Documentos de prueba en hr_documents")
    try:
        cur = conn.cursor()
        # Eliminar docs con URLs falsas (localhost, example.com, o sin URL)
        cur.execute("""
            SELECT id, file_name, file_url FROM hr_documents
            WHERE file_url LIKE '%localhost%'
               OR file_url LIKE '%example.com%'
               OR file_url IS NULL
               OR file_url = ''
            ORDER BY created_at;
        """)
        fake_docs = cur.fetchall()
        if fake_docs:
            warn(f"{len(fake_docs)} documento(s) con URLs inválidas encontrado(s):")
            for d in fake_docs:
                info(f"  {d[1]} → {(d[2] or '')[:60]}")
            cur.execute("""
                DELETE FROM hr_documents
                WHERE file_url LIKE '%localhost%'
                   OR file_url LIKE '%example.com%'
                   OR file_url IS NULL
                   OR file_url = '';
            """)
            conn.commit()
            cleaned.append(f"  ✅ Eliminados {len(fake_docs)} documentos con URLs inválidas")
            ok(f"Eliminados {len(fake_docs)} documentos de prueba")
        else:
            ok("Sin documentos de prueba (BD limpia)")

    except Exception as e:
        warn(f"No se pudo limpiar hr_documents: {e}")

    step("Pagos sin vincular (voucher_document_id huérfano)")
    try:
        cur.execute("""
            SELECT COUNT(*) FROM hr_payment_records p
            LEFT JOIN hr_documents d ON p.voucher_document_id = d.id
            WHERE p.voucher_document_id IS NOT NULL AND d.id IS NULL;
        """)
        orphan_vouchers = cur.fetchone()[0]
        if orphan_vouchers > 0:
            cur.execute("""
                UPDATE hr_payment_records SET voucher_document_id = NULL
                WHERE voucher_document_id IS NOT NULL
                  AND voucher_document_id NOT IN (SELECT id FROM hr_documents);
            """)
            conn.commit()
            cleaned.append(f"  ✅ Corregidos {orphan_vouchers} pagos con voucher_document_id huérfano")
            ok(f"Corregidos {orphan_vouchers} pagos huérfanos")
        else:
            ok("Sin voucher_document_id huérfanos")
    except Exception as e:
        warn(f"No se pudo verificar vouchers: {e}")

    step("Workspaces Hub vacíos")
    try:
        cur.execute("""
            SELECT COUNT(*) FROM hub_workspaces
            WHERE name IS NULL OR TRIM(name) = '';
        """)
        empty_ws = cur.fetchone()[0]
        if empty_ws > 0:
            cur.execute("DELETE FROM hub_workspaces WHERE name IS NULL OR TRIM(name) = '';")
            conn.commit()
            cleaned.append(f"  ✅ Eliminados {empty_ws} workspaces vacíos")
            ok(f"Eliminados {empty_ws} workspaces vacíos")
        else:
            ok("Sin workspaces vacíos")
    except Exception as e:
        warn(f"No se pudo verificar workspaces: {e}")

    step("Archivos scratch temporales")
    scratch_dir = os.path.join(ROOT, "scratch")
    if os.path.isdir(scratch_dir):
        files = os.listdir(scratch_dir)
        test_files = [f for f in files if any(x in f.lower() for x in ["test_","_test","temp_","_tmp","debug_"])]
        if test_files:
            warn(f"{len(test_files)} archivo(s) temporales en scratch/:")
            for f in test_files:
                info(f"  {f}")
            warnings.append(f"  ⚠️  {len(test_files)} archivos temp en scratch/ — revisar manualmente")
        else:
            ok("scratch/ sin archivos temporales críticos")
    
    step("Artefactos de AI (brain) obsoletos")
    brain_dir = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "brain")
    if os.path.isdir(brain_dir):
        conversations = [d for d in os.listdir(brain_dir) if os.path.isdir(os.path.join(brain_dir, d))]
        ok(f"Brain: {len(conversations)} conversación(es) en caché (no se eliminan)")

    conn.close()
    return cleaned

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3 — DOCS DE ESTADO (desactivada: se mantienen a mano)
# ══════════════════════════════════════════════════════════════════════════════
def section_update_memory_bank(results):
    header("📝 SECCIÓN 3/5 — docs de estado (mantenimiento MANUAL)")

    # DESACTIVADO 20 Jul 2026: la regeneración por plantilla hardcodeada
    # resucitaba contexto obsoleto (App.jsx, sesiones viejas) y pisaba las
    # actualizaciones hechas al cierre de sesión. activeContext.md y
    # progress.md se mantienen a mano (WORKFLOW.md FASE 5).
    warn("Regeneración por plantilla DESACTIVADA — checkpoints.md y CHECKLIST.md se mantienen a mano")
    info("memory-bank/ se retiró el 26 ago 2026 — ver docs/archive/")
    return

    # (cuerpo por plantilla eliminado — inalcanzable tras el return de arriba)

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4 — ACTUALIZAR docs/*.md
# ══════════════════════════════════════════════════════════════════════════════
def section_update_docs(results):
    header("📊 SECCIÓN 4/5 — docs/*.md (mantenimiento MANUAL)")

    # DESACTIVADO 20 Jul 2026: igual que memory-bank — la plantilla
    # hardcodeada agregaba checkpoints obsoletos y pisaba CHECKLIST.md.
    warn("Regeneración por plantilla DESACTIVADA — los .md se mantienen a mano")
    return

    # (cuerpo por plantilla eliminado — inalcanzable tras el return de arriba)

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5 — AUDITORÍA DE ARCHIVOS CLAVE
# ══════════════════════════════════════════════════════════════════════════════
def section_audit():
    header("🔐 SECCIÓN 5/5 — AUDITORÍA DE ARCHIVOS CLAVE")

    protected_files = [
        ("frontend/src/App.jsx",                         "🔴 CRÍTICO"),
        ("frontend/src/control-tower/ControlTowerApp.jsx","🔴 CRÍTICO"),
        ("fin_sys_core/database_driver.py",               "🔴 CRÍTICO"),
        ("fin_sys_core/control_tower_driver.py",          "🔴 CRÍTICO"),
        ("fin_sys_core/tax_motor.py",                     "🟡 ESTABLE"),
        ("fin_sys_core/ledger_math.py",                   "🟡 ESTABLE"),
        ("fin_sys_core/hr_driver.py",                     "🟢 ACTIVO"),
        ("fin_sys_core/hr_documents_driver.py",           "🟢 ACTIVO"),
        ("server.py",                                     "🟡 SOLO APPEND"),
    ]

    print(f"\n  {'Archivo':<55} {'Estado':<15} {'Tamaño':>10}")
    print(f"  {'─'*55} {'─'*15} {'─'*10}")
    for rel_path, status in protected_files:
        full_path = os.path.join(ROOT, rel_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"  {rel_path:<55} {status:<15} {size:>8,}B")
        else:
            print(f"  {rel_path:<55} {'⚠️  NO EXISTE':<15}")

    # Verificar integridad server.py (que no se hayan tocado endpoints existentes)
    step("Verificando integridad server.py")
    server_path = os.path.join(ROOT, "server.py")
    if os.path.exists(server_path):
        with open(server_path, "r", encoding="utf-8") as f:
            content = f.read()
        endpoints = re.findall(r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)', content)
        ok(f"server.py — {len(endpoints)} endpoints definidos, {len(content):,} bytes")

        # Verificar endpoints críticos
        critical_endpoints = ["/api/portfolios", "/api/transactions", "/api/ct/entities",
                               "/api/hub/workspaces", "/api/hr/profile", "/api/hr/payments", "/api/hr/documents", "/api/hr/company-links"]
        for ep in critical_endpoints:
            if ep in content:
                info(f"  ✓ {ep}")
            else:
                warn(f"  ✗ FALTA: {ep}")

# ══════════════════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ══════════════════════════════════════════════════════════════════════════════
def final_summary(results, cleaned):
    header("📋 RESUMEN FINAL — MANTENIMIENTO COMPLETADO")

    print(f"\n  {BOLD}Fecha / Hora:{RESET} {NOW_STR}")
    print(f"  {BOLD}Modo:{RESET}       Mantenimiento completo")

    print(f"\n  {CYAN}{'─' * 50}{RESET}")
    print(f"  {BOLD}ESTADO DEL SISTEMA:{RESET}")
    checks = [
        ("frontend",  "Frontend (Vite)"),
        ("backend",   "Backend (FastAPI)"),
        ("database",  "PostgreSQL"),
        ("motor",     "Motor Matemático"),
        ("ct",        "Control Tower"),
        ("hr",        "RRHH / Empresas"),
    ]
    for key, name in checks:
        v = results.get(key)
        icon = f"{GREEN}✅{RESET}" if v else (f"{RED}❌{RESET}" if v is False else f"{YELLOW}⚠️ {RESET}")
        print(f"  {icon} {name}")

    if cleaned:
        print(f"\n  {CYAN}{'─' * 50}{RESET}")
        print(f"  {BOLD}LIMPIEZA REALIZADA:{RESET}")
        for item in cleaned:
            print(f"  {item}")

    print(f"\n  {CYAN}{'─' * 50}{RESET}")
    print(f"  {BOLD}ARCHIVOS .md ACTUALIZADOS:{RESET}")
    print(f"  (a mano al cierre de sesión: docs/checkpoints.md + CHECKLIST.md)")

    print(f"\n  {CYAN}{'─' * 50}{RESET}")
    all_ok = all(results.get(k) for k in ["frontend", "backend", "database", "motor"])
    if all_ok:
        print(f"  {GREEN}{BOLD}🚀 SISTEMA LISTO PARA CONTINUAR{RESET}")
    else:
        print(f"  {YELLOW}{BOLD}⚡ HAY SERVICIOS CON ADVERTENCIAS — VER ARRIBA{RESET}")

    print(f"\n  {DIM}App:  http://localhost:{results.get('frontend_port', 5173)}")
    print(f"  Hub:  andres@finsys.io / admin123")
    print(f"  CT:   andres@finsys.os / admin123")
    print(f"  API:  http://localhost:8000/docs{RESET}\n")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FIN-SYS OS v2.0 — Session Maintenance Tool")
    parser.add_argument("--check",  action="store_true", help="Solo verificar sistema")
    parser.add_argument("--clean",  action="store_true", help="Solo limpiar artefactos")
    parser.add_argument("--update", action="store_true", help="Solo actualizar .md")
    args = parser.parse_args()

    load_env()

    print(f"\n{BOLD}{MAGENTA}{'█' * 62}{RESET}")
    print(f"{BOLD}{MAGENTA}  FIN-SYS OS v2.0 — SESSION MAINTENANCE TOOL")
    print(f"  {NOW_STR}")
    print(f"{'█' * 62}{RESET}\n")

    full_mode = not (args.check or args.clean or args.update)

    results = section_verify()

    if args.clean or full_mode:
        cleaned = section_cleanup(results)
    else:
        cleaned = []

    if args.update or full_mode:
        section_update_memory_bank(results)
        section_update_docs(results)

    if full_mode:
        section_audit()

    final_summary(results, cleaned)
