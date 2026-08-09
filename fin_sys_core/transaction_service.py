# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Servicio de dominio: creación de transacciones.

Extraído de routers/transactions.py (create_manual_transaction) para que la
web y el Bot IA (Módulo 09) compartan EXACTAMENTE el mismo pipeline oficial:
impuestos → registrar_transaccion → asiento Zero-COA.

La lógica es un espejo del endpoint original (refactor puro, cero cambios):
el router conserva HTTPException y el formato HTTP; este módulo solo hace
dominio y deja subir las excepciones (ExcedeLimitePocketError incluida).
"""


def create_transaction(tx_input) -> dict:
    """Registra una transacción oficial y emite su asiento contable.

    tx_input: instancia de routers.schemas.TransactionInput (ya validada por
    Pydantic — el llamador es responsable de construirla, lo que garantiza el
    contrato tanto desde la web como desde el bot).

    Devuelve el dict de resultado {status, transaction_id, net_value, concept,
    journal}. Lanza ExcedeLimitePocketError (límite de pocket) o cualquier
    error de persistencia hacia el llamador.
    """
    from database_driver import registrar_transaccion
    from tax_motor import process_transaction_taxes

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

    # 4. Zero-COA: Emitir asiento contable al kernel.
    # No bloquea la TX, pero el resultado se reporta (antes: except: pass
    # → el diario podía desincronizarse en silencio).
    from shared.helpers import emit_journal_entry
    journal = {"status": "error", "error": "sin ejecutar"}
    try:
        journal = emit_journal_entry(
            category=tx_input.category or "",
            tx_type=tx_input.type,
            amount=float(tax_results["net_value"]),
            account_id=tx_input.account_id,
            referencia=f"TX-{transaction_id}",
            descripcion=tx_input.concept or "",
            fecha=tx_input.transaction_date
        ) or {"status": "error", "error": "emit devolvió None"}
    except Exception as e:
        journal = {"status": "error", "error": str(e)}
    if journal.get("status") not in ("ok", "skipped_duplicate"):
        print(f"❌ [ZERO-COA] TX-{transaction_id} SIN asiento contable: {journal}")

    return {
        "status": "EXITOSO",
        "transaction_id": transaction_id,
        "net_value": tax_results["net_value"],
        "concept": tx_input.concept,
        "journal": journal.get("status"),
    }
