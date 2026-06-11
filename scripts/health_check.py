"""
FIN-SYS OS v2.0 — Health Check Script
Verifica el estado de todos los servicios: Backend, Frontend, DB, Motor Matemático y Control Tower.
Ejecutar desde la raíz del proyecto: python scripts/health_check.py
"""

import urllib.request
import urllib.error
import json
import sys
import os

# ─── Cargar variables de entorno ──────────────────────────────────────────────
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line_strip = line.strip()
            if line_strip and not line_strip.startswith("#") and "=" in line_strip:
                key, val = line_strip.split("=", 1)
                os.environ[key.strip()] = val.strip()

print("=" * 55)
print("  FIN-SYS OS v2.0 — HEALTH CHECK")
print("=" * 55)
all_ok = True

# ─── 1. Frontend (Vite) ───────────────────────────────────────────────────────
try:
    urllib.request.urlopen("http://localhost:5173", timeout=3)
    print("✅ [1/5] Frontend (React/Vite)    → :5173 OK")
except Exception:
    print("❌ [1/5] Frontend (React/Vite)    → :5173 CAÍDO")
    print("         Reiniciar: cd frontend && npm run dev")
    all_ok = False

# ─── 2. Backend (FastAPI) ─────────────────────────────────────────────────────
try:
    urllib.request.urlopen("http://localhost:8000/docs", timeout=3)
    print("✅ [2/5] Backend (FastAPI)         → :8000 OK")
except Exception:
    print("❌ [2/5] Backend (FastAPI)         → :8000 CAÍDO")
    print("         Reiniciar: python server.py")
    all_ok = False

# ─── 3. PostgreSQL / Supabase ─────────────────────────────────────────────────
try:
    import psycopg2
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        port=os.getenv("DB_PORT", "5432"),
        connect_timeout=5
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM transactions;")
    tx_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM entities;")
    entity_count = cur.fetchone()[0]
    conn.close()
    print(f"✅ [3/5] PostgreSQL (Supabase)     → Conectado | TXs: {tx_count} | Entidades: {entity_count}")
except Exception as e:
    print(f"❌ [3/5] PostgreSQL (Supabase)     → {str(e)[:60]}")
    print("         Verificar .env: DB_HOST, DB_USER, DB_PASSWORD")
    all_ok = False

# ─── 4. Motor Matemático ──────────────────────────────────────────────────────
try:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from fin_sys_core.tax_motor import process_transaction_taxes
    res = process_transaction_taxes(100000, apply_iva=True, apply_gmf=True)
    assert res["iva_amount"] == 19000, f"IVA inesperado: {res['iva_amount']}"
    assert res["gmf_amount"] == 400,   f"GMF inesperado: {res['gmf_amount']}"
    print("✅ [4/5] Motor Matemático          → IVA=19.000 | GMF=400 ✓")
except AssertionError as e:
    print(f"❌ [4/5] Motor Matemático          → Falla lógica: {e}")
    all_ok = False
except Exception as e:
    print(f"❌ [4/5] Motor Matemático          → ERROR: {e}")
    all_ok = False

# ─── 5. Control Tower API ─────────────────────────────────────────────────────
try:
    req = urllib.request.urlopen("http://localhost:8000/api/ct/entities", timeout=5)
    data = json.loads(req.read().decode())
    entity_count_api = len(data) if isinstance(data, list) else "?"
    req2 = urllib.request.urlopen("http://localhost:8000/api/ct/entities/1/kpis", timeout=5)
    kpis = json.loads(req2.read().decode())
    balance = kpis.get("balance_neto", 0)
    print(f"✅ [5/5] Control Tower API         → Entidades raíz: {entity_count_api} | Balance Holding: ${balance:,.0f}")
except urllib.error.URLError:
    print("❌ [5/5] Control Tower API         → Backend caído (ver check #2)")
    all_ok = False
except Exception as e:
    print(f"❌ [5/5] Control Tower API         → ERROR: {e}")
    all_ok = False

# ─── Resultado Final ──────────────────────────────────────────────────────────
print("=" * 55)
if all_ok:
    print("🚀 TODO EN ORDEN. Sistema listo para continuar.")
    print("   App principal: http://localhost:5173")
    print("   Control Tower: http://localhost:5173 → ⬡ CONTROL TOWER")
    print("   Login CT demo: andres@finsys.os / admin123")
    sys.exit(0)
else:
    print("⚠️  ALGUNOS SERVICIOS ESTÁN CAÍDOS. Revisar arriba.")
    sys.exit(1)
