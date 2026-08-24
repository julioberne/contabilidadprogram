# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Transacciones (10 endpoints)
CRUD, evidence upload, voice/transcribe/structure, seed, reset.
Extracted from contabilidad.py — PURE refactor, zero logic changes."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
import os, re, shutil, uuid

from routers.auth_guard import require_admin
from routers.schemas import TransactionInput, TransactionUpdateInput, StructureRequest

router = APIRouter(tags=["Transacciones"])

# Extensiones permitidas por tipo de upload (lowercase, sin punto)
_EVIDENCE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "pdf"}
_AUDIO_EXTS    = {"webm", "wav", "mp3", "m4a", "ogg", "opus", "flac"}


def _safe_upload_name(filename: str, allowed_exts: set) -> str:
    """Devuelve un nombre de archivo seguro para guardar en uploads/.

    - Elimina cualquier componente de ruta (bloquea ../ y rutas absolutas)
    - Restringe los caracteres al set [A-Za-z0-9._-]
    - Valida la extensión contra una whitelist
    - Prefija un token aleatorio para evitar colisiones/sobrescrituras
    """
    base = os.path.basename(filename or "")
    # También cortar separadores de Windows que basename (POSIX) no corta
    base = base.replace("\\", "/").split("/")[-1]
    ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida: .{ext or '(sin extensión)'}. "
                   f"Permitidas: {', '.join(sorted(allowed_exts))}",
        )
    stem = base.rsplit(".", 1)[0]
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem)[:80] or "archivo"
    return f"{uuid.uuid4().hex[:8]}_{stem}.{ext}"


# ==============================================================================
# 🔌 Endpoints de la API — Transacciones
# ==============================================================================

@router.get("/api/transactions")
def list_transactions(portfolio: Optional[str] = None):
    """
    Obtiene el historial de transacciones ordenado para el Libro Diario (Módulo 02).
    Soporta filtrado dinámico por la pestaña del portafolio.
    """
    try:
        from database_driver import obtener_transacciones
        txs = obtener_transacciones(portfolio)
        return txs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/transactions", status_code=201)
def create_manual_transaction(tx_input: TransactionInput):
    """
    Registra manualmente una transacción aplicando impuestos y validación de pockets.
    La lógica vive en fin_sys_core/transaction_service.py (compartida con el Bot IA);
    este endpoint solo traduce excepciones de dominio a HTTP.
    """
    try:
        from transaction_service import create_transaction
        from ledger_math import ExcedeLimitePocketError

        return create_transaction(tx_input)
    except ExcedeLimitePocketError as e:
        # Error controlado de sobregasto de bolsillo
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/upload-evidence")
def upload_evidence_endpoint(file: UploadFile = File(...)):
    """
    Sube un archivo de evidencia (comprobante) a la carpeta de uploads local.
    """
    try:
        os.makedirs("uploads", exist_ok=True)
        safe_name = _safe_upload_name(file.filename, _EVIDENCE_EXTS)
        file_path = os.path.join("uploads", safe_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "status": "EXITOSO",
            "file_path": f"/uploads/{safe_name}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/transactions/{tx_id}")
def update_transaction_endpoint(tx_id: int, tx_update: TransactionUpdateInput):
    """
    Permite actualizar campos individuales de una transacción existente (Edición tipo Excel).
    """
    try:
        from database_driver import actualizar_transaccion
        from tax_motor import process_transaction_taxes
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


def _build_voice_draft(parsed_tx, texto, portfolio_name, raw_transcript=""):
    """Respuesta BORRADOR de los endpoints de voz, con la MISMA inferencia
    que el Bot IA (fin_sys_core/draft_builder): portafolio validado, método de
    pago cruzado con las cuentas reales, account_id resuelto y campos
    inferidos/faltantes calculados en un solo lugar.

    El shape de la respuesta se mantiene (parsed_data / calculation_results /
    inferred_fields) para no romper el frontend; solo se agregan campos.
    """
    from draft_builder import build_draft
    from db_pool import get_conn, put_conn
    from tax_motor import process_transaction_taxes

    conn = get_conn()
    try:
        cur = conn.cursor()
        draft = build_draft(cur, parsed_tx, texto, portfolio_name)
        conn.commit()
    finally:
        put_conn(conn)

    if draft is None:
        raise HTTPException(
            status_code=400,
            detail="No hay portafolios creados. Crea uno antes de usar la ingestión por voz."
        )

    payload = draft["payload"]
    base_amount = payload.get("amount") or 0.0
    tax_results = process_transaction_taxes(
        base_amount=base_amount,
        apply_iva=payload.get("apply_iva", False),
        apply_gmf=False
    )

    return {
        "status": "BORRADOR",
        "raw_transcript": raw_transcript,
        "parsed_data": {
            "portfolio_name": payload["portfolio_name"],
            "type": payload["type"],
            "amount": base_amount,
            "concept": payload["concept"],
            "payment_method": payload["payment_method"],
            "category": payload["category"],
            "third_party": payload["third_party"],
            "transaction_date": payload["transaction_date"],
            "account_id": draft["account_id"],
            "apply_iva": payload.get("apply_iva", False),
            "is_recurring": payload.get("is_recurring", False),
        },
        "calculation_results": {
            "tax_iva_amount": tax_results["iva_amount"],
            "tax_gmf_amount": tax_results["gmf_amount"],
            "net_value": tax_results["net_value"],
        },
        "suggested_tags": parsed_tx.get("suggested_tags", []),
        "inferred_fields": draft["inferred_fields"],
        "missing_fields": draft["missing_fields"],
        "account_error": draft["account_error"],
    }


# ==============================================================================
# 🎙️ Endpoints de Voz & Estructura IA
# ==============================================================================

@router.post("/api/transactions/voice")
def upload_voice_transaction(
    audio_file: UploadFile = File(...),
    portfolio_name: str = Form("Negocio A")
):
    """
    Recibe el audio del micrófono, lo transcribe y estructura con IA, y devuelve
    la propuesta en estado BORRADOR para confirmación en la UI.
    Comparte la inferencia con el Bot IA (fin_sys_core/draft_builder).
    """
    try:
        from ai_engine import parse_audio_to_transaction

        # 1. Guardar temporalmente el archivo recibido de audio
        upload_dir = "./uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, _safe_upload_name(audio_file.filename, _AUDIO_EXTS))
        with open(file_path, "wb") as f:
            f.write(audio_file.file.read())

        # 2. Motor de IA: transcripción + estructuración con RAG
        parsed_tx = parse_audio_to_transaction(file_path, portfolio_name)
        transcript = parsed_tx.get("raw_transcript", "") or ""

        # 3. Inferencia determinista compartida con el bot + impuestos
        return _build_voice_draft(parsed_tx, transcript, portfolio_name, transcript)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/transactions/transcribe")
def upload_voice_transcribe_only(
    audio_file: UploadFile = File(...)
):
    """
    Recibe el archivo binario de audio del micrófono en localhost,
    lo pasa a la API de Whisper (vía Groq) o Gemini como fallback para obtener
    la transcripción textual únicamente.
    """
    try:
        from ai_engine import transcribe_audio_only
        
        # 1. Guardar temporalmente el archivo recibido de audio
        upload_dir = "./uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, _safe_upload_name(audio_file.filename, _AUDIO_EXTS))
        with open(file_path, "wb") as f:
            f.write(audio_file.file.read())

        # 2. Llamar a la transcripción
        transcript = transcribe_audio_only(file_path)
        
        return {
            "transcript": transcript
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/transactions/structure")
def structure_voice_transcript(
    req: StructureRequest
):
    """
    Toma un texto transcrito (posiblemente editado por el usuario), lo estructura
    con IA y devuelve la propuesta en estado BORRADOR.
    Comparte la inferencia con el Bot IA (fin_sys_core/draft_builder): portafolio
    validado, método de pago cruzado con las cuentas reales y account_id resuelto.
    """
    try:
        from ai_engine import structure_text_only

        parsed_tx = structure_text_only(req.transcript, req.portfolio_name)
        return _build_voice_draft(parsed_tx, req.transcript, req.portfolio_name, req.transcript)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# 🔌 Endpoints — Seed Sintético & Reset
# ==============================================================================

@router.post("/api/transactions/seed_synthetic")
def seed_synthetic_data(portfolio: str = "Negocio A", _admin: dict = Depends(require_admin)):
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


@router.post("/api/transactions/reset")
def reset_database_endpoint(_admin: dict = Depends(require_admin)):
    """
    Reinicia el sistema contable a un estado LIMPIO para pruebas de integridad:
    sin transacciones, sin asientos, sin terceros, sin borradores del bot, y
    las cuentas conservan su estructura pero con TODOS los saldos en $0.

    reset_db() (driver estable) trunca y re-siembra las cuentas con dinero de
    fábrica (incluido un -500.000 fantasma en Davivienda); aquí se completa la
    limpieza que el usuario espera del botón ⚠️ Reiniciar.
    """
    try:
        from database_driver import reset_db
        success = reset_db()
        if not success:
            raise HTTPException(status_code=500, detail="No se pudo reiniciar la base de datos.")

        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            # Cuentas en cero: estructura sí, dinero no.
            cur.execute("UPDATE user_accounts SET initial_balance = 0, current_balance = 0")
            conn.commit()
            # Datos del bot (tablas posteriores a reset_db). La vinculación de
            # chats (bot_chat_links) se conserva: es configuración, no datos.
            for tabla in ("transaction_drafts", "bot_messages"):
                try:
                    cur.execute(f"TRUNCATE {tabla} RESTART IDENTITY")
                    conn.commit()
                except Exception:
                    conn.rollback()   # instalación sin las tablas del bot
            cur.close()
        finally:
            put_conn(conn)

        return {
            "status": "COMPLETO",
            "message": "Sistema contable limpio: sin transacciones, asientos, terceros ni "
                       "borradores; cuentas conservadas con saldos en $0."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
