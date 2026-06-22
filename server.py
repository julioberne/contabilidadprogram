# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 - Servidor FastAPI Web Server (server.py)
---------------------------------------------------------
Este script levanta el servidor REST en localhost, exponiendo las APIs del
Módulo 01 (Registro) y Módulo 02 (Libro Diario) y conectando el núcleo matemático.
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

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# Agregar subdirectorio fin_sys_core a la ruta de búsqueda de Python
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fin_sys_core"))

from database_driver import (
    init_db, registrar_transaccion, obtener_transacciones,
    obtener_perfil_usuario, actualizar_perfil_usuario,
    obtener_cuentas, crear_cuenta, reset_db,
    obtener_coa_tree, cargar_plantilla_coa,
    obtener_portafolios, crear_portafolio, obtener_terceros
)
from tax_motor import process_transaction_taxes
from ledger_math import calculate_caja_viva, validate_pocket_budget, ExcedeLimitePocketError
from ai_engine import parse_audio_to_transaction, transcribe_audio_only, structure_text_only
from control_tower_driver import (
    init_control_tower_db, obtener_entidades_arbol, crear_entidad,
    actualizar_estado_entidad, eliminar_entidad,
    obtener_workspace_users, registrar_workspace_user, login_workspace_user,
    obtener_resource_ids, crear_resource_id, eliminar_resource_id,
    obtener_aprobaciones, crear_aprobacion, resolver_aprobacion,
    obtener_miembros_entidad, invitar_miembro, obtener_kpis_entidad
)

app = FastAPI(
    title="FIN-SYS OS v2.0 API Server",
    description="Backend modular e inteligente para el MVP de contabilidad retro-brutalista.",
    version="2.0"
)

# Configurar middleware de CORS para comunicación fluida con el frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permitir todos los orígenes en desarrollo local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import shutil
os.makedirs("uploads", exist_ok=True)
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ==============================================================================
# 📋 Esquemas de Validación de Datos (Pydantic Models)
# ==============================================================================

class PortfolioInput(BaseModel):
    name: str
    industry_type: str = "ESTANDAR"
    sub_industry_type: str = ""

class ThirdPartyInput(BaseModel):
    identification_type: str = Field(..., pattern="^(NIT|CC)$")
    identification_number: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None


class ProfileInput(BaseModel):
    name: str
    email: str
    role: str
    avatar_style: str


class AccountInput(BaseModel):
    name: str
    type: str
    currency: str = "COP"
    initial_balance: float = 0.0


class CxcCxpInput(BaseModel):
    type: str = Field(..., pattern="^(CXC|CXP)$")
    due_date: str
    term: str = Field("Corto", pattern="^(Corto|Mediano|Largo)$")


class AssetInput(BaseModel):
    name: str
    purchase_value: float
    custom_tag: Optional[str] = None
    establish_as_asset: bool = False
    is_passive_income_generator: bool = False
    recurrence_interval_days: Optional[int] = 30
    recurrence_amount: Optional[float] = 0.0


class TransactionInput(BaseModel):
    portfolio_name: str
    type: str = Field(..., pattern="^(INGRESO|GASTO|TRANSFERENCIA)$")
    amount: float = Field(..., gt=0.0)
    concept: str
    payment_method: str
    category: str
    third_party: ThirdPartyInput
    transaction_date: str
    apply_iva: bool = False
    apply_gmf: bool = False
    custom_taxes: Optional[List[Dict[str, Any]]] = None
    
    # Georreferenciación opcional
    geo_latitude: Optional[float] = None
    geo_longitude: Optional[float] = None
    geo_maps_link: Optional[str] = None
    
    # Módulo de Cuentas
    account_id: Optional[int] = None
    dest_account_id: Optional[int] = None
    trm: Optional[float] = 1.0
    transaction_currency: Optional[str] = "COP"
    
    # [NEW] Campos por cobrar/pagar y activos
    cxc_cxp: Optional[CxcCxpInput] = None
    asset: Optional[AssetInput] = None
    evidence_file_path: Optional[str] = None
    is_recurring: Optional[bool] = False
    recurrence_interval: Optional[str] = "MENSUAL"
    recurrence_days: Optional[int] = 30
    recurrence_max_reps: Optional[int] = None
    recurrence_start_date: Optional[str] = None
    recurrence_end_date: Optional[str] = None


class StructureRequest(BaseModel):
    transcript: str
    portfolio_name: str = "Negocio A"


class TransactionUpdateInput(BaseModel):
    type: Optional[str] = None
    amount: Optional[float] = None
    concept: Optional[str] = None
    transaction_date: Optional[str] = None
    payment_method: Optional[str] = None
    category: Optional[str] = None
    net_value: Optional[float] = None
    third_party_name: Optional[str] = None
    identification_number: Optional[str] = None
    
    # Módulo de Cuentas
    account_id: Optional[int] = None
    dest_account_id: Optional[int] = None
    trm: Optional[float] = None
    transaction_currency: Optional[str] = None
    is_recurring: Optional[bool] = None
    recurrence_interval: Optional[str] = None
    recurrence_days: Optional[int] = None
    recurrence_max_reps: Optional[int] = None
    recurrence_start_date: Optional[str] = None
    recurrence_end_date: Optional[str] = None


# ==============================================================================
# 🔌 Endpoints de la API
# ==============================================================================

@app.on_event("startup")
def startup_event():
    """Ejecutado al iniciar el servidor para sincronizar las tablas de Postgres."""
    print("🔄 Sincronizando esquema de base de datos PostgreSQL...")
    try:
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


@app.get("/api/portfolios")
def get_portfolios():
    try:
        ports = obtener_portafolios()
        if not ports:
            # Fallback a iniciales por defecto si está vacío
            ports = [
                {"id": 1, "name": "Negocio A", "industry_type": "ESTANDAR"},
                {"id": 2, "name": "Negocio B", "industry_type": "ESTANDAR"},
                {"id": 3, "name": "Finanzas Personales", "industry_type": "ESTANDAR"}
            ]
        return ports
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolios", status_code=201)
def create_portfolio_endpoint(port_input: PortfolioInput):
    try:
        new_id = crear_portafolio(port_input.name, port_input.industry_type, port_input.sub_industry_type)
        if not new_id:
             raise HTTPException(status_code=500, detail="Error al crear el portafolio")
        return {"status": "CREADO", "portfolio_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolios/balance")
def get_caja_viva_balance(portfolio: Optional[str] = None):
    """
    Obtiene los agregados acumulados de la Caja Viva en tiempo real.
    Suma el total de ingresos, gastos, balance neto y patrimonio con alertas.
    """
    try:
        txs = obtener_transacciones(portfolio)
        accounts = obtener_cuentas()
        totals = calculate_caja_viva(txs, accounts)
        return {
            "status": totals["status"],
            "total_ingresos": totals["total_ingresos"],
            "total_gastos": totals["total_gastos"],
            "balance_neto": totals["balance_neto"],
            "capital_inicial": totals.get("capital_inicial", 5000000.0),
            "patrimonio": totals.get("patrimonio", 5000000.0),
            
            # Nuevos agregados separados
            "total_ingresos_cop": totals["total_ingresos_cop"],
            "total_gastos_cop": totals["total_gastos_cop"],
            "balance_neto_cop": totals["balance_neto_cop"],
            "patrimonio_cop": totals["patrimonio_cop"],
            
            "total_ingresos_usd": totals["total_ingresos_usd"],
            "total_gastos_usd": totals["total_gastos_usd"],
            "balance_neto_usd": totals["balance_neto_usd"],
            "patrimonio_usd": totals["patrimonio_usd"],
            
            "alerts": totals.get("alerts", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/transactions")
def list_transactions(portfolio: Optional[str] = None):
    """
    Obtiene el historial de transacciones ordenado para el Libro Diario (Módulo 02).
    Soporta filtrado dinámico por la pestaña del portafolio.
    """
    try:
        txs = obtener_transacciones(portfolio)
        return txs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transactions", status_code=201)
def create_manual_transaction(tx_input: TransactionInput):
    """
    Registra manualmente una transacción aplicando impuestos y validación de pockets.
    """
    try:
        # 1. Ejecutar las matemáticas del motor de impuestos (IVA, GMF, Tasas)
        tax_results = process_transaction_taxes(
            base_amount=tx_input.amount,
            apply_iva=tx_input.apply_iva,
            apply_gmf=tx_input.apply_gmf,
            custom_taxes=tx_input.custom_taxes
        )

        # 2. Construir el paquete completo de datos
        tx_data = {
            "portfolio_name": tx_input.portfolio_name,
            "type": tx_input.type,
            "amount": tx_input.amount,
            "concept": tx_input.concept,
            "payment_method": tx_input.payment_method,
            "category": tx_input.category,
            "transaction_date": tx_input.transaction_date,
            "third_party": {
                "identification_type": tx_input.third_party.identification_type,
                "identification_number": tx_input.third_party.identification_number,
                "name": tx_input.third_party.name,
                "email": tx_input.third_party.email,
                "phone": tx_input.third_party.phone,
                "website": tx_input.third_party.website
            },
            # Resultados matemáticos exactos
            "tax_iva_percentage": 19.0 if tx_input.apply_iva else 0.0,
            "tax_iva_amount": tax_results["iva_amount"],
            "tax_gmf_percentage": 0.40 if tx_input.apply_gmf else 0.0,
            "tax_gmf_amount": tax_results["gmf_amount"],
            "custom_tax_amount": tax_results["custom_taxes_total"],
            "net_value": tax_results["net_value"],
            # Georreferenciación
            "geo_latitude": tx_input.geo_latitude,
            "geo_longitude": tx_input.geo_longitude,
            "geo_maps_link": tx_input.geo_maps_link,
            
            # Módulo de Cuentas
            "account_id": tx_input.account_id,
            "dest_account_id": tx_input.dest_account_id,
            "trm": tx_input.trm,
            "transaction_currency": tx_input.transaction_currency,
            
            # [NEW] Campos por cobrar/pagar y activos
            "cxc_cxp": tx_input.cxc_cxp.dict() if tx_input.cxc_cxp else None,
            "asset": tx_input.asset.dict() if tx_input.asset else None,
            "evidence_file_path": tx_input.evidence_file_path,
            "is_recurring": tx_input.is_recurring,
            "recurrence_interval": tx_input.recurrence_interval,
            "recurrence_days": tx_input.recurrence_days,
            "recurrence_max_reps": tx_input.recurrence_max_reps,
            "recurrence_start_date": tx_input.recurrence_start_date,
            "recurrence_end_date": tx_input.recurrence_end_date
        }

        # 3. Guardar en la base de datos PostgreSQL
        transaction_id = registrar_transaccion(tx_data)

        # 4. Zero-COA: Emitir asiento contable al kernel (non-blocking)
        try:
            _emit_journal_entry(
                category=tx_input.category or "",
                tx_type=tx_input.type,
                amount=float(tax_results["net_value"]),
                account_id=tx_input.account_id,
                referencia=f"TX-{transaction_id}",
                descripcion=tx_input.concept or "",
                fecha=tx_input.transaction_date
            )
        except Exception:
            pass  # Non-blocking: Zero-COA failure must not break transactions

        return {
            "status": "EXITOSO",
            "transaction_id": transaction_id,
            "net_value": tax_results["net_value"],
            "concept": tx_input.concept
        }
    except ExcedeLimitePocketError as e:
        # Error controlado de sobregasto de bolsillo
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-evidence")
def upload_evidence_endpoint(file: UploadFile = File(...)):
    """
    Sube un archivo de evidencia (comprobante) a la carpeta de uploads local.
    """
    try:
        os.makedirs("uploads", exist_ok=True)
        file_path = os.path.join("uploads", file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "status": "EXITOSO",
            "file_path": f"/uploads/{file.filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transactions/voice")
def upload_voice_transaction(
    audio_file: UploadFile = File(...),
    portfolio_name: str = Form("Negocio A")
):
    """
    Recibe el archivo binario de audio del micrófono en localhost,
    lo pasa a la API de Gemini Multimodal para su transcripción y parseo RAG
    y devuelve la propuesta de transacción en estado BORRADOR para confirmación interactiva.
    """
    try:
        # 1. Guardar temporalmente el archivo recibido de audio
        upload_dir = "./uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, audio_file.filename)
        with open(file_path, "wb") as f:
            f.write(audio_file.file.read())
            
        # 2. Llamar al motor inteligente de Gemini + RAG
        parsed_tx = parse_audio_to_transaction(file_path, portfolio_name)
        
        # 3. Calcular impuestos estándar (IVA/GMF) de forma determinista basados en lo extraído
        base_amount = parsed_tx.get("amount")
        if base_amount is None:
            base_amount = 0.0
        else:
            try:
                base_amount = float(base_amount)
            except (ValueError, TypeError):
                base_amount = 0.0
        
        # Inferencia simple de IVA: si se extrae o deduce que aplica
        apply_iva = parsed_tx.get("category") in ["Servicios", "Infraestructura"]
        
        tax_results = process_transaction_taxes(
            base_amount=base_amount,
            apply_iva=apply_iva,
            apply_gmf=False
        )
        
        # 4. Devolver la respuesta en estado BORRADOR (para confirmación en la UI)
        return {
            "status": "BORRADOR",
            "raw_transcript": parsed_tx.get("raw_transcript", ""),
            "parsed_data": {
                "portfolio_name": portfolio_name,
                "type": parsed_tx.get("type", "GASTO"),
                "amount": base_amount,
                "concept": parsed_tx.get("concept", ""),
                "payment_method": parsed_tx.get("payment_method") or "Efectivo",
                "category": parsed_tx.get("category") or "Ventas",
                "third_party": parsed_tx.get("third_party") or {
                    "identification_type": "NIT",
                    "identification_number": "",
                    "name": ""
                },
                "is_recurring": parsed_tx.get("is_recurring", False)
            },
            "calculation_results": {
                "tax_iva_amount": tax_results["iva_amount"],
                "tax_gmf_amount": tax_results["gmf_amount"],
                "net_value": tax_results["net_value"]
            },
            "suggested_tags": parsed_tx.get("suggested_tags", []),
            "inferred_fields": parsed_tx.get("inferred_fields", [])
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transactions/transcribe")
def upload_voice_transcribe_only(
    audio_file: UploadFile = File(...)
):
    """
    Recibe el archivo binario de audio del micrófono en localhost,
    lo pasa a la API de Whisper (vía Groq) o Gemini como fallback para obtener
    la transcripción textual únicamente.
    """
    try:
        # 1. Guardar temporalmente el archivo recibido de audio
        upload_dir = "./uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, audio_file.filename)
        with open(file_path, "wb") as f:
            f.write(audio_file.file.read())
            
        # 2. Llamar a la transcripción
        transcript = transcribe_audio_only(file_path)
        
        return {
            "transcript": transcript
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transactions/structure")
def structure_voice_transcript(
    req: StructureRequest
):
    """
    Toma un texto transcrito (que puede haber sido editado por el usuario),
    lo pasa a la API de Llama 3.3/Gemini para su parseo RAG
    y devuelve la propuesta de transacción en estado BORRADOR para confirmación interactiva.
    """
    try:
        portfolio_name = req.portfolio_name
        transcript = req.transcript
        
        # 1. Llamar al motor inteligente de estructuración
        parsed_tx = structure_text_only(transcript, portfolio_name)
        
        # 2. Calcular impuestos estándar (IVA/GMF) de forma determinista basados en lo extraído
        base_amount = parsed_tx.get("amount")
        if base_amount is None:
            base_amount = 0.0
        else:
            try:
                base_amount = float(base_amount)
            except (ValueError, TypeError):
                base_amount = 0.0
        
        # Inferencia simple de IVA: si se extrae o deduce que aplica
        apply_iva = parsed_tx.get("category") in ["Servicios", "Infraestructura"]
        
        tax_results = process_transaction_taxes(
            base_amount=base_amount,
            apply_iva=apply_iva,
            apply_gmf=False
        )
        
        # 3. Devolver la respuesta en estado BORRADOR (para confirmación en la UI)
        return {
            "status": "BORRADOR",
            "raw_transcript": transcript,
            "parsed_data": {
                "portfolio_name": portfolio_name,
                "type": parsed_tx.get("type", "GASTO"),
                "amount": base_amount,
                "concept": parsed_tx.get("concept", ""),
                "payment_method": parsed_tx.get("payment_method") or "Efectivo",
                "category": parsed_tx.get("category") or "Ventas",
                "third_party": parsed_tx.get("third_party") or {
                    "identification_type": "NIT",
                    "identification_number": "",
                    "name": ""
                },
                "is_recurring": parsed_tx.get("is_recurring", False)
            },
            "calculation_results": {
                "tax_iva_amount": tax_results["iva_amount"],
                "tax_gmf_amount": tax_results["gmf_amount"],
                "net_value": tax_results["net_value"]
            },
            "suggested_tags": parsed_tx.get("suggested_tags", []),
            "inferred_fields": parsed_tx.get("inferred_fields", [])
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/transactions/{tx_id}")
def update_transaction_endpoint(tx_id: int, tx_update: TransactionUpdateInput):
    """
    Permite actualizar campos individuales de una transacción existente (Edición tipo Excel).
    """
    try:
        from database_driver import actualizar_transaccion
        update_dict = tx_update.dict(exclude_unset=True)
        
        # Si se modifica el amount, recalculamos net_value e impuestos por conveniencia
        if "amount" in update_dict and "net_value" not in update_dict:
            apply_iva = update_dict.get("category") in ["Servicios", "Infraestructura"]
            tax_results = process_transaction_taxes(
                base_amount=update_dict["amount"],
                apply_iva=apply_iva,
                apply_gmf=False
            )
            update_dict["net_value"] = tax_results["net_value"]
            update_dict["tax_iva_amount"] = tax_results["iva_amount"]
            update_dict["tax_gmf_amount"] = tax_results["gmf_amount"]
            
        success = actualizar_transaccion(tx_id, update_dict)
        if not success:
            raise HTTPException(status_code=404, detail="Transacción no encontrada.")
        return {"status": "ACTUALIZADO", "transaction_id": tx_id}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transactions/seed_synthetic")
def seed_synthetic_data(portfolio: str = "Negocio A"):
    """
    Genera un conjunto de datos sintéticos (Ingresos y Egresos)
    para simular un entorno financiero real e inducir una alerta de insolvencia.
    """
    try:
        from database_driver import registrar_transaccion
        
        synthetic_txs = [
            {
                "portfolio_name": portfolio,
                "type": "INGRESO",
                "amount": 2500000.0,
                "concept": "VENTA MAYORISTA DE MERCANCÍA",
                "payment_method": "Banco M",
                "category": "Ventas",
                "transaction_date": "2026-06-01",
                "third_party": {
                    "identification_type": "NIT",
                    "identification_number": "800111222-9",
                    "name": "DISTRIBUIDORA ANDINA SAS"
                },
                "tax_iva_percentage": 0.0,
                "tax_iva_amount": 0.0,
                "tax_gmf_percentage": 0.0,
                "tax_gmf_amount": 0.0,
                "custom_tax_amount": 0.0,
                "net_value": 2500000.0
            },
            {
                "portfolio_name": portfolio,
                "type": "GASTO",
                "amount": 1500000.0,
                "concept": "PAGO DE ARRENDAMIENTO OFICINA CENTRAL",
                "payment_method": "Transferencia",
                "category": "Infraestructura",
                "transaction_date": "2026-06-02",
                "third_party": {
                    "identification_type": "NIT",
                    "identification_number": "900555666-3",
                    "name": "INMOBILIARIA DEL ESTE"
                },
                "tax_iva_percentage": 19.0,
                "tax_iva_amount": 285000.0,
                "tax_gmf_percentage": 0.0,
                "tax_gmf_amount": 0.0,
                "custom_tax_amount": 0.0,
                "net_value": 1785000.0
            },
            {
                "portfolio_name": portfolio,
                "type": "GASTO",
                "amount": 7000000.0,
                "concept": "COMPRA DE MAQUINARIA NASDAQ-100 IMPORTACIÓN",
                "payment_method": "Tarjeta C",
                "category": "Infraestructura",
                "transaction_date": "2026-06-03",
                "third_party": {
                    "identification_type": "CC",
                    "identification_number": "1007888999",
                    "name": "GLOBAL TRADING INC"
                },
                "tax_iva_percentage": 0.0,
                "tax_iva_amount": 0.0,
                "tax_gmf_percentage": 0.0,
                "tax_gmf_amount": 0.0,
                "custom_tax_amount": 0.0,
                "net_value": 7000000.0
            }
        ]
        
        ids = []
        for tx in synthetic_txs:
            tx_id = registrar_transaccion(tx)
            ids.append(tx_id)
            
        return {
            "status": "COMPLETO",
            "message": "Datos sintéticos creados con éxito. Se indujo un estado de insolvencia para probar alertas.",
            "ids": ids
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transactions/reset")
def reset_database_endpoint():
    """
    Reinicia completamente la base de datos a su estado por defecto
    (borra transacciones y terceros, y restablece las cuentas iniciales).
    """
    try:
        success = reset_db()
        if not success:
            raise HTTPException(status_code=500, detail="No se pudo reiniciar la base de datos.")
        return {
            "status": "COMPLETO",
            "message": "Base de datos y balances de cuentas reiniciados exitosamente."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/profile")

def get_profile():
    try:
        return obtener_perfil_usuario()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/profile")
def update_profile(profile: ProfileInput):
    try:
        success = actualizar_perfil_usuario(profile.dict())
        if not success:
            raise HTTPException(status_code=500, detail="No se pudo actualizar el perfil.")
        return {"status": "ACTUALIZADO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounts")
def list_accounts():
    try:
        return obtener_cuentas()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounts", status_code=201)
def add_account(acc: AccountInput):
    try:
        new_id = crear_cuenta(acc.dict())
        return {"status": "CREADO", "account_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/coa")
def get_coa_tree(portfolio: str):
    """Obtiene el árbol del catálogo de cuentas"""
    try:
        tree = obtener_coa_tree(portfolio)
        return {"status": "OK", "data": tree}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CoaTemplateInput(BaseModel):
    portfolio_name: str
    template_name: str

@app.post("/api/coa/template")
def load_coa_template(payload: CoaTemplateInput):
    """Carga una plantilla COA para un portafolio"""
    try:
        success = cargar_plantilla_coa(payload.portfolio_name, payload.template_name)
        if not success:
            raise HTTPException(status_code=500, detail="No se pudo cargar la plantilla COA. Verifica la base de datos.")
        return {"status": "CARGADO", "message": f"Plantilla {payload.template_name} cargada con éxito."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CoaAccountInput(BaseModel):
    portfolio_name: str
    code: str
    name: str
    type: str
    is_group: bool
    parent_code: Optional[str] = None

@app.post("/api/coa/account")
def add_coa_account(payload: CoaAccountInput):
    """Agrega una cuenta personalizada al COA"""
    from database_driver import agregar_cuenta_coa
    try:
        acc_data = {
            "code": payload.code,
            "name": payload.name,
            "type": payload.type,
            "is_group": payload.is_group,
            "parent_code": payload.parent_code
        }
        success = agregar_cuenta_coa(payload.portfolio_name, acc_data)
        if not success:
            raise HTTPException(status_code=500, detail="Error guardando cuenta.")
        return {"status": "CREADO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Iniciar servidor local en el puerto 8000
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)


@app.get("/api/third-parties")
def get_third_parties():
    try:
        return obtener_terceros()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# 🏢 CONTROL TOWER ENDPOINTS — /api/ct/*
# ==============================================================================

# --- Pydantic Models para Control Tower ---
class EntityInput(BaseModel):
    name: str
    type: str = "EMPRESA"
    parent_id: Optional[int] = None
    portfolio_id: Optional[int] = None
    industry: Optional[str] = ""
    sub_industry: Optional[str] = ""
    status: Optional[str] = "AL DIA"

class CTUserRegisterInput(BaseModel):
    name: str
    email: str
    password: str
    role_label: str = "Colaborador"
    permissions: Optional[Dict[str, Any]] = None
    parent_user_id: Optional[int] = None

class CTLoginInput(BaseModel):
    email: str
    password: str

class ResourceIdInput(BaseModel):
    entity_id: int
    label: str
    value: str
    category: str = "FISCAL"
    expires_at: Optional[str] = None
    notes: Optional[str] = None

class ApprovalInput(BaseModel):
    entity_id: int
    transaction_id: Optional[int] = None
    requested_by: Optional[int] = None
    description: Optional[str] = None
    amount: Optional[float] = None

class ResolveApprovalInput(BaseModel):
    status: str  # APROBADO | RECHAZADO
    reviewer_id: int
    notes: Optional[str] = ""

class MemberInviteInput(BaseModel):
    user_id: int
    role_label: str = "Colaborador"
    permissions: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None

class CTQuickTransactionInput(BaseModel):
    entity_id: int
    portfolio_name: str
    type: str  # INGRESO | GASTO
    amount: float
    concept: str
    category: str
    payment_method: str
    third_party_name: str
    third_party_id_number: str
    third_party_id_type: str = "NIT"


# --- Entidades ---
@app.get("/api/ct/entities")
def ct_get_entities():
    try:
        return obtener_entidades_arbol()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ct/entities", status_code=201)
def ct_create_entity(data: EntityInput):
    try:
        new_id = crear_entidad(data.dict())
        return {"status": "CREADO", "entity_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/ct/entities/{entity_id}/status")
def ct_update_entity_status(entity_id: int, status: str):
    try:
        actualizar_estado_entidad(entity_id, status)
        return {"status": "ACTUALIZADO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/ct/entities/{entity_id}")
def ct_delete_entity(entity_id: int):
    try:
        eliminar_entidad(entity_id)
        return {"status": "ELIMINADO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ct/entities/{entity_id}/kpis")
def ct_get_entity_kpis(entity_id: int):
    try:
        return obtener_kpis_entidad(entity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Usuarios del Workspace ---
@app.get("/api/ct/users")
def ct_get_users():
    try:
        return obtener_workspace_users()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ct/users/register", status_code=201)
def ct_register_user(data: CTUserRegisterInput):
    try:
        user = registrar_workspace_user(data.dict())
        return {"status": "REGISTRADO", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ct/users/login")
def ct_login_user(data: CTLoginInput):
    try:
        user = login_workspace_user(data.email, data.password)
        if not user:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        return {"status": "OK", "user": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Resource IDs ---
@app.get("/api/ct/entities/{entity_id}/resources")
def ct_get_resources(entity_id: int):
    try:
        return obtener_resource_ids(entity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ct/resources", status_code=201)
def ct_create_resource(data: ResourceIdInput):
    try:
        new_id = crear_resource_id(data.dict())
        return {"status": "CREADO", "resource_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/ct/resources/{rid}")
def ct_delete_resource(rid: int):
    try:
        eliminar_resource_id(rid)
        return {"status": "ELIMINADO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Aprobaciones ---
@app.get("/api/ct/approvals")
def ct_get_approvals(entity_id: Optional[int] = None):
    try:
        return obtener_aprobaciones(entity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ct/approvals", status_code=201)
def ct_create_approval(data: ApprovalInput):
    try:
        new_id = crear_aprobacion(data.dict())
        return {"status": "CREADO", "approval_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/ct/approvals/{approval_id}/resolve")
def ct_resolve_approval(approval_id: int, data: ResolveApprovalInput):
    try:
        resolver_aprobacion(approval_id, data.status, data.reviewer_id, data.notes)
        return {"status": "RESUELTO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Miembros por entidad ---
@app.get("/api/ct/entities/{entity_id}/members")
def ct_get_members(entity_id: int):
    try:
        return obtener_miembros_entidad(entity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ct/entities/{entity_id}/members", status_code=201)
def ct_invite_member(entity_id: int, data: MemberInviteInput):
    try:
        perms = data.permissions or {"ledger": True, "reports": True}
        new_id = invitar_miembro(entity_id, data.user_id, data.role_label, perms, data.expires_at)
        return {"status": "INVITADO", "member_id": new_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Transacción Rápida desde Control Tower ---
@app.post("/api/ct/quick-transaction", status_code=201)
def ct_quick_transaction(data: CTQuickTransactionInput):
    """Registra una transacción rápida desde el panel lateral del Control Tower."""
    try:
        from tax_motor import process_transaction_taxes
        tax_results = process_transaction_taxes(
            base_amount=data.amount, apply_iva=False, apply_gmf=False
        )
        tx_data = {
            "portfolio_name": data.portfolio_name,
            "type": data.type,
            "amount": data.amount,
            "concept": data.concept,
            "payment_method": data.payment_method,
            "category": data.category,
            "transaction_date": __import__('datetime').date.today().isoformat(),
            "third_party": {
                "identification_type": data.third_party_id_type,
                "identification_number": data.third_party_id_number,
                "name": data.third_party_name,
            },
            "tax_iva_percentage": 0.0, "tax_iva_amount": 0.0,
            "tax_gmf_percentage": 0.0, "tax_gmf_amount": 0.0,
            "custom_tax_amount": 0.0,
            "net_value": tax_results["net_value"],
        }
        from database_driver import registrar_transaccion
        tx_id = registrar_transaccion(tx_data)
        return {"status": "EXITOSO", "transaction_id": tx_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# ██╗  ██╗██╗   ██╗██████╗     ███████╗███╗   ██╗██████╗ ██████╗  ██████╗ ██╗███╗   ██╗████████╗███████╗
# ██║  ██║██║   ██║██╔══██╗    ██╔════╝████╗  ██║██╔══██╗██╔══██╗██╔═══██╗██║████╗  ██║╚══██╔══╝██╔════╝
# ███████║██║   ██║██████╔╝    █████╗  ██╔██╗ ██║██║  ██║██████╔╝██║   ██║██║██╔██╗ ██║   ██║   ███████╗
# ██╔══██║██║   ██║██╔══██╗    ██╔══╝  ██║╚██╗██║██║  ██║██╔═══╝ ██║   ██║██║██║╚██╗██║   ██║   ╚════██║
# ██║  ██║╚██████╔╝██████╔╝    ███████╗██║ ╚████║██████╔╝██║     ╚██████╔╝██║██║ ╚████║   ██║   ███████║
# ==============================================================================
# MODULO 08: PROJECT HUB — Endpoints /api/hub/*
# Todos los endpoints del Hub son NUEVOS y van al final (Zero-Impact Policy)
# NO se modifica ningún endpoint existente de los módulos 01-07
# ==============================================================================

from pydantic import BaseModel as _HubBase
from typing import Optional as _Opt, List as _List
import sys as _sys

# Modelos Pydantic del Hub
class HubWorkspaceCreate(_HubBase):
    name: str
    nit: _Opt[str] = None
    logo_url: _Opt[str] = None

class HubUserRegister(_HubBase):
    email: str
    password: str
    name: str
    cedula: _Opt[str] = None
    description: _Opt[str] = None
    workspace_id: _Opt[str] = None
    role: str = "member"

class HubUserLogin(_HubBase):
    email: str
    password: str

class HubEntityCreate(_HubBase):
    workspace_id: str
    name: str
    entity_type: str = "CUSTOM"
    parent_id: _Opt[str] = None
    description: _Opt[str] = None
    color: str = "#0EA5E9"

class HubProjectCreate(_HubBase):
    workspace_id: str
    name: str
    entity_id: _Opt[str] = None
    description: _Opt[str] = None
    color: str = "#0EA5E9"
    created_by: _Opt[str] = None

class HubTaskCreate(_HubBase):
    workspace_id: str
    project_id: str
    title: str
    description: _Opt[str] = None
    priority: str = "medium"
    due_date: _Opt[str] = None
    created_by: _Opt[str] = None
    assignee_ids: _List[str] = []

class HubTaskUpdate(_HubBase):
    title: _Opt[str] = None
    description: _Opt[str] = None
    status: _Opt[str] = None
    priority: _Opt[str] = None
    due_date: _Opt[str] = None
    position: _Opt[int] = None
    assignee_ids: _Opt[_List[str]] = None

class HubNoteCreate(_HubBase):
    workspace_id: str
    user_id: str
    title: str = "Sin titulo"
    project_id: _Opt[str] = None

class HubNoteUpdate(_HubBase):
    title: _Opt[str] = None
    content: _Opt[list] = None
    is_private: _Opt[bool] = None

class HubEventCreate(_HubBase):
    workspace_id: str
    title: str
    start_time: str
    end_time: str
    description: _Opt[str] = None
    all_day: bool = False
    color: _Opt[str] = None
    created_by: _Opt[str] = None
    project_id: _Opt[str] = None
    attendee_ids: _List[str] = []

class HubEventUpdate(_HubBase):
    title: _Opt[str] = None
    description: _Opt[str] = None
    start_time: _Opt[str] = None
    end_time: _Opt[str] = None
    all_day: _Opt[bool] = None
    color: _Opt[str] = None
    attendee_ids: _Opt[_List[str]] = None

class HubMemberAdd(_HubBase):
    workspace_id: str
    user_id: str
    role: str = "member"


# ── WORKSPACES ────────────────────────────────────────────────────────────────

@app.post("/api/hub/workspaces")
def hub_create_workspace(data: HubWorkspaceCreate):
    try:
        from fin_sys_core.hub_driver import create_workspace
        ws = create_workspace(name=data.name, nit=data.nit, logo_url=data.logo_url)
        return {"status": "ok", "workspace": ws}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hub/workspaces")
def hub_get_workspaces(user_id: str = None, all: bool = False):
    try:
        from fin_sys_core.hub_driver import get_workspaces_for_user, get_all_workspaces
        if all:
            return get_all_workspaces()
        if user_id:
            return get_workspaces_for_user(user_id)
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── USERS ─────────────────────────────────────────────────────────────────────

@app.post("/api/hub/users/register")
def hub_register(data: HubUserRegister):
    try:
        from fin_sys_core.hub_driver import register_user
        user = register_user(
            email=data.email, password=data.password, name=data.name,
            cedula=data.cedula, description=data.description,
            workspace_id=data.workspace_id, role=data.role
        )
        return {"status": "ok", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hub/users/login")
def hub_login(data: HubUserLogin):
    try:
        from fin_sys_core.hub_driver import login_user
        user = login_user(email=data.email, password=data.password)
        if not user:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        return {"status": "ok", "user": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hub/users")
def hub_get_members(workspace_id: str):
    try:
        from fin_sys_core.hub_driver import get_workspace_members
        return get_workspace_members(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hub/users/add-member")
def hub_add_member(data: HubMemberAdd):
    try:
        from fin_sys_core.hub_driver import add_member_to_workspace
        result = add_member_to_workspace(data.workspace_id, data.user_id, data.role)
        return {"status": "ok", "member": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── ENTITIES ──────────────────────────────────────────────────────────────────

@app.get("/api/hub/entities")
def hub_get_entities(workspace_id: str):
    try:
        from fin_sys_core.hub_driver import get_entity_tree
        return get_entity_tree(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hub/entities")
def hub_create_entity(data: HubEntityCreate):
    try:
        from fin_sys_core.hub_driver import create_entity
        entity = create_entity(
            workspace_id=data.workspace_id, name=data.name,
            entity_type=data.entity_type, parent_id=data.parent_id,
            description=data.description, color=data.color
        )
        return {"status": "ok", "entity": entity}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/hub/entities/{entity_id}")
def hub_delete_entity(entity_id: str):
    try:
        from fin_sys_core.hub_driver import delete_entity
        ok = delete_entity(entity_id)
        return {"status": "ok" if ok else "not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── PROJECTS ──────────────────────────────────────────────────────────────────

@app.get("/api/hub/projects")
def hub_get_projects(workspace_id: str, entity_id: str = None):
    try:
        from fin_sys_core.hub_driver import get_projects
        return get_projects(workspace_id, entity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hub/projects")
def hub_create_project(data: HubProjectCreate):
    try:
        from fin_sys_core.hub_driver import create_project
        project = create_project(
            workspace_id=data.workspace_id, name=data.name,
            entity_id=data.entity_id, description=data.description,
            color=data.color, created_by=data.created_by
        )
        return {"status": "ok", "project": project}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── TASKS ─────────────────────────────────────────────────────────────────────

@app.get("/api/hub/tasks")
def hub_get_tasks(project_id: str, status: str = None):
    try:
        from fin_sys_core.hub_driver import get_tasks
        return get_tasks(project_id, status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hub/tasks")
def hub_create_task(data: HubTaskCreate):
    try:
        from fin_sys_core.hub_driver import create_task
        task = create_task(
            workspace_id=data.workspace_id, project_id=data.project_id,
            title=data.title, description=data.description,
            priority=data.priority, due_date=data.due_date,
            created_by=data.created_by, assignee_ids=data.assignee_ids
        )
        return {"status": "ok", "task": task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/hub/tasks/{task_id}")
def hub_update_task(task_id: str, data: HubTaskUpdate):
    try:
        from fin_sys_core.hub_driver import update_task
        task = update_task(
            task_id,
            **{k: v for k, v in data.dict().items() if v is not None}
        )
        return {"status": "ok", "task": task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/hub/tasks/{task_id}")
def hub_delete_task(task_id: str):
    try:
        from fin_sys_core.hub_driver import delete_task
        ok = delete_task(task_id)
        return {"status": "ok" if ok else "not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── NOTES ─────────────────────────────────────────────────────────────────────

@app.get("/api/hub/notes")
def hub_get_notes(workspace_id: str, user_id: str):
    try:
        from fin_sys_core.hub_driver import get_notes
        return get_notes(workspace_id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hub/notes")
def hub_create_note(data: HubNoteCreate):
    try:
        from fin_sys_core.hub_driver import create_note
        note = create_note(
            workspace_id=data.workspace_id, user_id=data.user_id,
            title=data.title, project_id=data.project_id
        )
        return {"status": "ok", "note": note}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/hub/notes/{note_id}")
def hub_update_note(note_id: str, data: HubNoteUpdate):
    try:
        from fin_sys_core.hub_driver import update_note
        note = update_note(
            note_id, title=data.title,
            content=data.content, is_private=data.is_private
        )
        return {"status": "ok", "note": note}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── EVENTS / CALENDAR ─────────────────────────────────────────────────────────

@app.get("/api/hub/events")
def hub_get_events(workspace_id: str):
    try:
        from fin_sys_core.hub_driver import get_events
        return get_events(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hub/events")
def hub_create_event(data: HubEventCreate):
    try:
        from fin_sys_core.hub_driver import create_event
        event = create_event(
            workspace_id=data.workspace_id, title=data.title,
            start_time=data.start_time, end_time=data.end_time,
            description=data.description, all_day=data.all_day,
            color=data.color, created_by=data.created_by,
            project_id=data.project_id, attendee_ids=data.attendee_ids
        )
        return {"status": "ok", "event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/hub/events/{event_id}")
def hub_update_event(event_id: str, data: HubEventUpdate):
    try:
        from fin_sys_core.hub_driver import update_event
        event = update_event(
            event_id,
            **{k: v for k, v in data.dict().items() if v is not None}
        )
        return {"status": "ok", "event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── METRICS ───────────────────────────────────────────────────────────────────

@app.get("/api/hub/metrics")
def hub_get_metrics(workspace_id: str):
    try:
        from fin_sys_core.hub_driver import get_user_metrics
        return get_user_metrics(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS RESTAURADOS — Cartera, HR, Tags, Dashboard, Health, Zero-COA
# ══════════════════════════════════════════════════════════════════════════════


# ── GET /health — Health check sin BD ──
@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0"}


# ── POST /api/reconcile-balances ──
@app.post("/api/reconcile-balances")
def reconcile_balances():
    try:
        from fin_sys_core.database_driver import get_db_connection, release_db_connection, recalcular_saldos_cuentas
        conn = get_db_connection()
        recalcular_saldos_cuentas(conn)
        conn.commit()
        release_db_connection(conn)
        return {"status": "OK", "message": "Saldos reconciliados"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/dashboard-data ──
@app.get("/api/dashboard-data")
def get_dashboard_data(portfolio: Optional[str] = None, limit: int = 50, offset: int = 0):
    try:
        from fin_sys_core.database_driver import obtener_transacciones, obtener_cuentas, obtener_portafolios, obtener_perfil_usuario
        from fin_sys_core.ledger_math import calculate_caja_viva
        txs = obtener_transacciones(portfolio)
        accounts = obtener_cuentas()
        totals = calculate_caja_viva(txs, accounts)
        
        # Paginación de transacciones
        paginated_txs = txs[offset:offset + limit] if txs else []
        
        result = {
            # KPIs (balance)
            "status": totals["status"],
            "total_ingresos": totals["total_ingresos"],
            "total_gastos": totals["total_gastos"],
            "balance_neto": totals["balance_neto"],
            "capital_inicial": totals.get("capital_inicial", 5000000.0),
            "patrimonio": totals.get("patrimonio", 5000000.0),
            "total_ingresos_cop": totals["total_ingresos_cop"],
            "total_gastos_cop": totals["total_gastos_cop"],
            "balance_neto_cop": totals["balance_neto_cop"],
            "patrimonio_cop": totals["patrimonio_cop"],
            "total_ingresos_usd": totals["total_ingresos_usd"],
            "total_gastos_usd": totals["total_gastos_usd"],
            "balance_neto_usd": totals["balance_neto_usd"],
            "patrimonio_usd": totals["patrimonio_usd"],
            "alerts": totals.get("alerts", []),
            # SOL-04A: datos consolidados para el frontend
            "transactions": paginated_txs,
            "total_tx_count": len(txs),
            "accounts": accounts,
            "portfolios": obtener_portafolios(),
            "balance": totals,
        }
        
        # Perfil
        try:
            result["profile"] = obtener_perfil_usuario()
        except:
            result["profile"] = None
        
        # COA
        try:
            from fin_sys_core.database_driver import get_db_connection, release_db_connection
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, code, name, parent_id, is_group, naturaleza, nivel
                FROM coa_accounts
                WHERE portfolio_name = %s
                ORDER BY code;
            """, (portfolio or "Negocio A",))
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            cur.close()
            release_db_connection(conn)
            if rows:
                result["coa"] = {"status": "OK", "data": _build_coa_tree(rows)}
            else:
                result["coa"] = {"status": "EMPTY", "data": []}
        except Exception:
            result["coa"] = None
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _build_coa_tree(flat_rows):
    """Construye árbol COA a partir de filas planas."""
    by_id = {r["id"]: {**r, "children": []} for r in flat_rows}
    tree = []
    for r in flat_rows:
        node = by_id[r["id"]]
        if r.get("parent_id") and r["parent_id"] in by_id:
            by_id[r["parent_id"]]["children"].append(node)
        else:
            tree.append(node)
    return tree


# ── POST /api/cache/invalidate ──
@app.post("/api/cache/invalidate")
def invalidate_cache():
    return {"status": "OK", "message": "Cache invalidado"}


# ── Tags ──
@app.get("/api/tags")
def list_tags():
    try:
        from fin_sys_core.database_driver import listar_tags
        return listar_tags()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tags", status_code=201)
def create_tag(body: dict):
    try:
        from fin_sys_core.database_driver import crear_tag
        return crear_tag(body.get("name", ""), body.get("color", "#000000"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Custom Taxes ──
@app.get("/api/custom-taxes")
def list_custom_taxes():
    try:
        from fin_sys_core.database_driver import listar_custom_taxes
        return listar_custom_taxes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/custom-taxes", status_code=201)
def create_custom_tax(body: dict):
    try:
        from fin_sys_core.database_driver import crear_custom_tax
        return crear_custom_tax(body.get("name", ""), float(body.get("rate", 0)), body.get("tax_type", "ADDITIVE"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# CARTERA (CXC / CXP)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/cartera")
def list_cartera(portfolio: Optional[str] = None):
    from fin_sys_core.database_driver import listar_cartera
    return listar_cartera(portfolio)

@app.put("/api/cartera/{ledger_id}/status")
def update_cartera_status(ledger_id: int, body: dict):
    from fin_sys_core.database_driver import actualizar_cartera_status
    try:
        updated = actualizar_cartera_status(
            ledger_id, body.get("status", ""),
            remaining_balance=body.get("remaining_balance")
        )
        return {"status": "OK", "updated": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cartera/summary")
def get_cartera_summary():
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Ensure cartera_payments table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cartera_payments (
                id SERIAL PRIMARY KEY,
                ledger_id INTEGER NOT NULL REFERENCES cxp_cxc_ledger(id) ON DELETE CASCADE,
                amount DECIMAL(15,2) NOT NULL,
                payment_date DATE DEFAULT CURRENT_DATE,
                note TEXT,
                balance_after DECIMAL(15,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE type='CXC') as total_cxc,
                COUNT(*) FILTER (WHERE type='CXP') as total_cxp,
                COALESCE(SUM(original_amount) FILTER (WHERE type='CXC'), 0) as monto_cxc,
                COALESCE(SUM(original_amount) FILTER (WHERE type='CXP'), 0) as monto_cxp,
                COALESCE(SUM(remaining_balance) FILTER (WHERE type='CXC'), 0) as pendiente_cxc,
                COALESCE(SUM(remaining_balance) FILTER (WHERE type='CXP'), 0) as pendiente_cxp,
                COUNT(*) FILTER (WHERE status='PAGADO') as pagados,
                COUNT(*) FILTER (WHERE status='VENCIDO') as vencidos
            FROM cxp_cxc_ledger;
        """)
        row = cur.fetchone()
        cur.close()
        release_db_connection(conn)
        return {
            "total_cxc": row[0], "total_cxp": row[1],
            "monto_cxc": float(row[2]), "monto_cxp": float(row[3]),
            "pendiente_cxc": float(row[4]), "pendiente_cxp": float(row[5]),
            "pagados": row[6], "vencidos": row[7]
        }
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except: pass
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cartera/{ledger_id}/payments")
def get_cartera_payments(ledger_id: int):
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, amount, payment_date, note, balance_after, created_at
            FROM cartera_payments WHERE ledger_id = %s
            ORDER BY created_at DESC;
        """, (ledger_id,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        for r in rows:
            for k in ['payment_date','created_at']:
                if k in r and r[k]: r[k] = str(r[k])
            for k in ['amount','balance_after']:
                if k in r and r[k] is not None: r[k] = float(r[k])
        cur.close()
        release_db_connection(conn)
        return rows
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except: pass
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cartera/{ledger_id}/payment")
def register_cartera_payment(ledger_id: int, body: dict):
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    amount = float(body.get("amount", 0))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Monto inválido")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT remaining_balance, status FROM cxp_cxc_ledger WHERE id = %s;", (ledger_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        new_balance = max(0, float(row[0]) - amount)
        new_status = "PAGADO" if new_balance == 0 else row[1]
        cur.execute("""
            INSERT INTO cartera_payments (ledger_id, amount, payment_date, note, balance_after)
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
        """, (ledger_id, amount, body.get("payment_date") or None,
              body.get("note") or None, new_balance))
        pid = cur.fetchone()[0]
        cur.execute("UPDATE cxp_cxc_ledger SET remaining_balance=%s, status=%s WHERE id=%s;",
                    (new_balance, new_status, ledger_id))
        conn.commit()
        # Zero-COA: Emitir asiento de pago al kernel
        try:
            _emit_journal_entry(
                category="__CXC_PAYMENT__", tx_type="CXC",
                amount=amount, referencia=f"PAY-{pid}",
                descripcion=f"Abono cartera #{ledger_id}"
            )
        except: pass
        cur.close()
        release_db_connection(conn)
        return {"status": "OK", "payment_id": pid, "new_balance": new_balance, "new_status": new_status}
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except: pass
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cartera")
def create_cartera_entry(body: dict):
    """Crea una cuenta CXC/CXP standalone."""
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    for f in ["third_party_id", "type", "original_amount", "due_date", "term"]:
        if f not in body:
            raise HTTPException(status_code=400, detail=f"Campo requerido: {f}")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        amount = float(body["original_amount"])
        partial = float(body.get("partial_payment", 0))
        remaining = max(0, amount - partial)
        start_date = body.get("start_date") or None
        payment_freq = int(body.get("payment_frequency", 30))
        cur.execute("""
            INSERT INTO cxp_cxc_ledger
                (third_party_id, type, original_amount, remaining_balance, due_date, term, status, start_date, payment_frequency)
            VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_DATE), %s) RETURNING id;
        """, (body["third_party_id"], body["type"], amount, remaining,
              body["due_date"], body["term"],
              "PAGADO" if remaining == 0 else "PENDIENTE",
              start_date, payment_freq))
        lid = cur.fetchone()[0]
        if partial > 0:
            cur.execute("""
                INSERT INTO cartera_payments (ledger_id, amount, payment_date, note, balance_after)
                VALUES (%s, %s, CURRENT_DATE, 'Abono inicial', %s);
            """, (lid, partial, remaining))
        conn.commit()
        # Zero-COA: Emitir asiento de creación CXC/CXP al kernel
        try:
            coa_cat = "__CXC_CREATE__" if body["type"] == "CXC" else "__CXP_CREATE__"
            _emit_journal_entry(
                category=coa_cat, tx_type=body["type"],
                amount=amount,
                referencia=f"{body['type']}-{lid}",
                descripcion=f"Crear {body['type']} #{lid}"
            )
        except: pass
        cur.close()
        release_db_connection(conn)
        return {"status": "CREADO", "id": lid, "remaining_balance": remaining}
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except: pass
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /api/third-parties — Crear tercero standalone ──
@app.post("/api/third-parties")
def create_third_party(body: dict):
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nombre requerido")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO third_parties (name, identification_type, identification_number, email, phone, website)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        """, (name, body.get("identification_type", "NIT"),
              body.get("identification_number", ""),
              body.get("email", ""), body.get("phone", ""),
              body.get("website", "")))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        release_db_connection(conn)
        return {"id": new_id, "name": name, "status": "CREADO"}
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except: pass
        raise HTTPException(status_code=500, detail=str(e))


# ── PUT /api/third-parties/{tp_id} ──
@app.put("/api/third-parties/{tp_id}")
def update_third_party(tp_id: int, body: dict):
    from fin_sys_core.database_driver import actualizar_tercero
    try:
        result = actualizar_tercero(
            tp_id, name=body.get("name"),
            identification_type=body.get("identification_type"),
            identification_number=body.get("identification_number"),
            email=body.get("email"), phone=body.get("phone"),
            website=body.get("website")
        )
        return {"status": "OK", "updated": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/cartera/alerts ──
@app.get("/api/cartera/alerts")
def get_cartera_alerts():
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Update vencidos
        cur.execute("""
            UPDATE cxp_cxc_ledger SET status = 'VENCIDO'
            WHERE due_date < CURRENT_DATE AND status NOT IN ('PAGADO', 'VENCIDO', 'CANCELADO');
        """)
        conn.commit()
        cur.execute("""
            SELECT l.id, l.type, l.original_amount, l.remaining_balance, l.due_date, l.status,
                   tp.name as third_party_name,
                   (l.due_date - CURRENT_DATE) as days_until_due
            FROM cxp_cxc_ledger l
            LEFT JOIN third_parties tp ON tp.id = l.third_party_id
            WHERE l.status NOT IN ('PAGADO', 'CANCELADO')
            AND l.due_date <= CURRENT_DATE + INTERVAL '30 days'
            ORDER BY l.due_date ASC;
        """)
        cols = [d[0] for d in cur.description]
        alerts = []
        for r in cur.fetchall():
            row = dict(zip(cols, r))
            for k in ['original_amount','remaining_balance']:
                if row.get(k) is not None: row[k] = float(row[k])
            if row.get('due_date'): row['due_date'] = str(row['due_date'])
            if row.get('days_until_due') is not None: row['days_until_due'] = int(row['days_until_due'])
            alerts.append(row)
        cur.close()
        release_db_connection(conn)
        return {"alerts": alerts}
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except: pass
        raise HTTPException(status_code=500, detail=str(e))


# ── DELETE /api/cartera/{id} ──
@app.delete("/api/cartera/{ledger_id}")
def delete_cartera_entry(ledger_id: int):
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM cartera_payments WHERE ledger_id = %s;", (ledger_id,))
        cur.execute("DELETE FROM cxp_cxc_ledger WHERE id = %s RETURNING id;", (ledger_id,))
        deleted = cur.fetchone()
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Cuenta {ledger_id} no encontrada")
        conn.commit()
        cur.close()
        release_db_connection(conn)
        return {"status": "ELIMINADO", "id": ledger_id}
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except: pass
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# HR ENDPOINTS (Módulo 08c)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/hr/profile/{user_id}")
def hr_get_profile(user_id: str, workspace_id: str = "default"):
    try:
        from fin_sys_core.hr_driver import get_hr_profile
        return get_hr_profile(user_id, workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/hr/profile/{user_id}")
def hr_update_profile(user_id: str, body: dict):
    try:
        from fin_sys_core.hr_driver import update_hr_profile
        ws = body.pop("workspace_id", "default")
        return update_hr_profile(user_id, ws, body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hr/salary/{user_id}")
def hr_get_salary(user_id: str, workspace_id: str = "default"):
    try:
        from fin_sys_core.hr_driver import get_hr_salary
        return get_hr_salary(user_id, workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/hr/salary/{user_id}")
def hr_update_salary(user_id: str, body: dict):
    try:
        from fin_sys_core.hr_driver import update_hr_salary
        ws = body.pop("workspace_id", "default")
        return update_hr_salary(user_id, ws, body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hr/companies/{user_id}")
def hr_get_companies(user_id: str):
    try:
        from fin_sys_core.hr_driver import get_employee_companies
        return get_employee_companies(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/companies/{user_id}")
def hr_add_company(user_id: str, body: dict):
    try:
        from fin_sys_core.hr_driver import add_employee_company
        return add_employee_company(
            user_id, body.get("entity_id"), body.get("entity_name", ""),
            body.get("workspace_id", "default"), body.get("role", "Empleado"),
            body.get("start_date")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hr/folders/{workspace_id}")
def hr_get_folders(workspace_id: str):
    try:
        from fin_sys_core.hr_documents_driver import get_folders
        return get_folders(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/folders/{workspace_id}")
def hr_create_folder(workspace_id: str, body: dict):
    try:
        from fin_sys_core.hr_documents_driver import create_folder
        return create_folder(workspace_id, body.get("name", ""), body.get("parent_id"), body.get("color"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hr/documents/{user_id}")
def hr_get_documents(user_id: str, workspace_id: str = "default", folder_id: Optional[str] = None):
    try:
        from fin_sys_core.hr_documents_driver import get_documents
        return get_documents(user_id, workspace_id, folder_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/documents/{user_id}")
def hr_save_document(user_id: str, body: dict):
    try:
        from fin_sys_core.hr_documents_driver import save_document_metadata
        ws = body.get("workspace_id", "default")
        return save_document_metadata(
            user_id, ws, body.get("name", ""), body.get("doc_type", ""),
            body.get("file_data"), body.get("file_name"), body.get("mime_type"),
            body.get("folder_id"), body.get("notes"), body.get("category_id")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/salary/calculate")
def hr_calculate_salary(body: dict):
    """Endpoint huérfano — mantener hasta limpieza técnica."""
    return {"status": "NOT_IMPLEMENTED", "message": "Cálculo ocurre localmente en SalaryTab.jsx"}

@app.post("/api/hr/storage/sign-upload")
def hr_sign_upload(body: dict):
    """Endpoint huérfano — sustituido por data URL base64."""
    return {"status": "NOT_IMPLEMENTED", "message": "Bucket bloquea MIME, usando base64"}

@app.get("/api/hr/categories/{workspace_id}")
def hr_get_categories(workspace_id: str):
    try:
        from fin_sys_core.hr_driver import get_doc_categories
        return get_doc_categories(workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/categories/{workspace_id}")
def hr_add_category(workspace_id: str, body: dict):
    try:
        from fin_sys_core.hr_driver import add_doc_category
        return add_doc_category(workspace_id, body.get("name", ""), body.get("color", "#666"), body.get("sort_order", 0))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hr/payments/{user_id}")
def hr_get_payments(user_id: str, workspace_id: str = "default"):
    try:
        from fin_sys_core.hr_driver import get_payment_records
        return get_payment_records(user_id, workspace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/payments/{user_id}")
def hr_add_payment(user_id: str, body: dict):
    try:
        from fin_sys_core.hr_driver import add_payment_record
        ws = body.pop("workspace_id", "default")
        return add_payment_record(user_id, ws, body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# ZERO-COA — Kernel Integration (Posting Rules + Journal Entries)
# ══════════════════════════════════════════════════════════════════════════════

BANK_ACCOUNT_MAP = {
    "Efectivo": "110505",
    "Caja Menor": "110510",
}

def _resolve_bank_code(account_id: int = None) -> str:
    """Resuelve un account_id a su código PUC. Default: 111005 (Bancos)."""
    if not account_id:
        return "111005"
    try:
        from fin_sys_core.database_driver import get_db_connection, release_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM user_accounts WHERE id = %s;", (account_id,))
        row = cur.fetchone()
        cur.close()
        release_db_connection(conn)
        if row:
            return BANK_ACCOUNT_MAP.get(row[0], "111005")
        return "111005"
    except:
        return "111005"


def _emit_journal_entry(category, tx_type, amount, account_id=None, referencia="", descripcion="", fecha=None):
    """
    Busca la posting_rule por (category, tx_type), resuelve __BANK__,
    y emite el evento al kernel para generar el asiento de partida doble.
    Nunca bloquea la operación original si falla.
    """
    import logging
    logger = logging.getLogger("zero_coa")
    try:
        from kernel.kernel_event_bus import emit
        from fin_sys_core.database_driver import get_db_connection, release_db_connection
        from datetime import date
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT debit_account_code, credit_account_code, rule_name
            FROM posting_rules
            WHERE category = %s AND transaction_type = %s AND is_active = TRUE
            ORDER BY portfolio_id NULLS LAST LIMIT 1;
        """, (category, tx_type))
        rule = cur.fetchone()
        # Fallback: si no hay match exacto, usar regla genérica
        if not rule:
            cur.execute("""
                SELECT debit_account_code, credit_account_code, rule_name
                FROM posting_rules
                WHERE category = '__FALLBACK__' AND transaction_type = %s AND is_active = TRUE
                LIMIT 1;
            """, (tx_type,))
            rule = cur.fetchone()
        cur.close()
        release_db_connection(conn)
        if not rule:
            return None
        debit_code, credit_code, rule_name = rule
        bank_code = _resolve_bank_code(account_id)
        if debit_code == "__BANK__":
            debit_code = bank_code
        if credit_code == "__BANK__":
            credit_code = bank_code
        result = emit('fin.transaccion.registrada', {
            'fecha': fecha or str(date.today()),
            'modulo_origen': 'zero_coa',
            'referencia': referencia,
            'descripcion': f"[{rule_name}] {descripcion}",
            'asientos': [
                {'cuenta_codigo': debit_code, 'debito': amount, 'credito': 0,
                 'cuenta_nombre': rule_name, 'cuenta_tipo': ''},
                {'cuenta_codigo': credit_code, 'debito': 0, 'credito': amount,
                 'cuenta_nombre': rule_name, 'cuenta_tipo': ''},
            ]
        })
        logger.info(f"✅ Zero-COA: {rule_name} | ${amount:,.0f} | Db={debit_code} Cr={credit_code}")
        return result
    except Exception as e:
        logger.warning(f"⚠️ Zero-COA emit failed: {e}")
        return None


# ── GET /api/journal-entries ──
@app.get("/api/journal-entries")
def get_journal_entries(
    fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None,
    modulo_origen: Optional[str] = None, limit: int = 100, offset: int = 0
):
    try:
        from kernel.kernel_accounting import obtener_asientos
        entries = obtener_asientos(
            fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
            modulo_origen=modulo_origen, limit=limit, offset=offset
        )
        for e in entries:
            for k in ['fecha', 'created_at']:
                if k in e and e[k]: e[k] = str(e[k])
            for k in ['debito', 'credito']:
                if k in e and e[k] is not None: e[k] = float(e[k])
        return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/financial-summary ──
@app.get("/api/financial-summary")
def get_financial_summary(fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None):
    try:
        from kernel.kernel_accounting import obtener_resumen_financiero
        return obtener_resumen_financiero(fecha_desde, fecha_hasta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/posting-rules ──
@app.get("/api/posting-rules")
def list_posting_rules():
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, rule_name, category, transaction_type,
                   debit_account_code, credit_account_code, description, is_active
            FROM posting_rules ORDER BY transaction_type, category;
        """)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
        release_db_connection(conn)
        return rows
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except: pass
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /api/posting-rules/preview ──
@app.get("/api/posting-rules/preview")
def preview_posting_rule(category: str, tx_type: str, amount: float = 0, account_id: int = None):
    """Retorna el preview del asiento contable sin emitirlo."""
    try:
        from fin_sys_core.database_driver import get_db_connection, release_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT debit_account_code, credit_account_code, rule_name, description
            FROM posting_rules
            WHERE category = %s AND transaction_type = %s AND is_active = TRUE
            ORDER BY portfolio_id NULLS LAST LIMIT 1;
        """, (category, tx_type))
        rule = cur.fetchone()
        # Fallback genérico
        if not rule:
            cur.execute("""
                SELECT debit_account_code, credit_account_code, rule_name, description
                FROM posting_rules
                WHERE category = '__FALLBACK__' AND transaction_type = %s AND is_active = TRUE
                LIMIT 1;
            """, (tx_type,))
            rule = cur.fetchone()
        cur.close()
        release_db_connection(conn)
        if not rule:
            return {"found": False}
        debit_code, credit_code, rule_name, desc = rule
        bank_code = _resolve_bank_code(account_id)
        if debit_code == "__BANK__":
            debit_code = bank_code
        if credit_code == "__BANK__":
            credit_code = bank_code
        return {
            "found": True, "rule_name": rule_name, "description": desc,
            "debit": {"cuenta_codigo": debit_code, "monto": amount},
            "credit": {"cuenta_codigo": credit_code, "monto": amount},
            "balanced": True
        }
    except:
        return {"found": False}
