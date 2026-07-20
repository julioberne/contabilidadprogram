# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Bootstrap del Servidor
------------------------------------------
Este archivo SOLO hace bootstrap: carga .env, configura app, CORS,
registra routers y define el evento startup.
Todos los endpoints están en routers/*.py
"""

import sys
import os

# --- Cargador de Variables de Entorno Pura Python ---
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line_strip = line.strip()
            if line_strip and not line_strip.startswith("#") and "=" in line_strip:
                key, val = line_strip.split("=", 1)
                os.environ[key.strip()] = val.strip()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Agregar subdirectorio fin_sys_core a la ruta de búsqueda de Python
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fin_sys_core"))

# Directorio de uploads
os.makedirs("uploads", exist_ok=True)

app = FastAPI(
    title="FIN-SYS OS v2.0 API Server",
    description="Backend modular e inteligente para el MVP de contabilidad retro-brutalista.",
    version="2.0"
)

# CORS dinámico: lee CORS_ORIGINS del entorno, fallback a * en desarrollo
_cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=bool(os.environ.get("CORS_ORIGINS")),  # True solo si hay origins explícitos
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ==============================================================================
# 🔌 Registrar Routers (1 archivo por dominio)
# ==============================================================================

from routers.portfolios import router as portfolios_router
from routers.transactions import router as transactions_router
from routers.profile_accounts import router as profile_accounts_router
from routers.coa import router as coa_contab_router
from routers.dashboard_data import router as dashboard_data_router
from routers.tags_taxes import router as tags_taxes_router
from routers.control_tower import router as ct_router
from routers.hub import router as hub_router
from routers.hr import router as hr_router
from routers.cartera import router as cartera_router
from routers.zero_coa import router as zero_coa_router
from routers.org import router as org_router
from routers.inventory import router as inventory_router
from routers.module_flags import router as flags_router

app.include_router(portfolios_router)
app.include_router(transactions_router)
app.include_router(profile_accounts_router)
app.include_router(coa_contab_router)
app.include_router(dashboard_data_router)
app.include_router(tags_taxes_router)
app.include_router(ct_router)
app.include_router(hub_router)
app.include_router(hr_router)
app.include_router(cartera_router)
app.include_router(zero_coa_router)
app.include_router(org_router)
app.include_router(inventory_router)
app.include_router(flags_router)


# ==============================================================================
# 🚀 Evento de Startup
# ==============================================================================

@app.on_event("startup")
def startup_event():
    """Ejecutado al iniciar el servidor para sincronizar las tablas de Postgres."""
    print("🔄 Sincronizando esquema de base de datos PostgreSQL...")
    try:
        from database_driver import init_db
        from control_tower_driver import init_control_tower_db
        init_db()
        init_control_tower_db()
    except Exception as e:
        print(f"⚠️ [ADVERTENCIA] No se pudo conectar a PostgreSQL en el puerto 5432: {e}")
        print("Asegúrate de que PostgreSQL esté activo antes de realizar peticiones de base de datos.")

    # ── Zero-COA: Registrar listener de partida doble ──
    try:
        from kernel.kernel_event_bus import on, off
        from kernel.kernel_accounting import registrar_asiento, init_journal_entries_table
        init_journal_entries_table()
        # Reset primero para evitar duplicados en hot-reload
        off('fin.transaccion.registrada')
        on('fin.transaccion.registrada', registrar_asiento)
        print("✅ Zero-COA: listener de partida doble registrado")
    except Exception as e:
        print(f"⚠️ Zero-COA init: {e}")


# ==============================================================================
# 🏥 Health check (para Docker healthcheck + monitoreo)
# ==============================================================================
# IMPORTANTE: debe declararse ANTES del catch-all del frontend. FastAPI resuelve
# las rutas por orden de registro, y "/{full_path:path}" captura cualquier GET
# —incluido /api/health— si se registra primero.

@app.get("/api/health", tags=["system"])
def health_check():
    """Endpoint ligero para verificar que el backend está vivo."""
    try:
        from fin_sys_core.database_driver import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
    return {
        "status": "ok",
        "db": db_status,
        "version": "2.0"
    }


# ==============================================================================
# 📦 Producción: Servir frontend build (solo si frontend/dist existe)
# ==============================================================================
# Va al FINAL a propósito: el catch-all sólo debe actuar sobre rutas que ningún
# endpoint previo reclamó.

import pathlib
_frontend_dist = pathlib.Path(__file__).parent / "frontend" / "dist"
if _frontend_dist.exists():
    from fastapi.responses import FileResponse
    # Servir assets estáticos del frontend build
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="frontend-assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        """Catch-all: sirve index.html para rutas SPA del frontend."""
        file_path = _frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_frontend_dist / "index.html"))


if __name__ == "__main__":
    import uvicorn
    # Iniciar servidor local en el puerto 8000
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)

