# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Cartera (CXC / CXP)"""
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(tags=["Cartera"])


# ══════════════════════════════════════════════════════════════════════════════
# CARTERA (CXC / CXP)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/api/cartera")
def list_cartera(portfolio: Optional[str] = None):
    from fin_sys_core.database_driver import listar_cartera
    return listar_cartera(portfolio)

@router.put("/api/cartera/{ledger_id}/status")
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

@router.put("/api/cartera/{ledger_id}")
def update_cartera_entry(ledger_id: int, body: dict):
    """Edita una cuenta CXC/CXP existente: monto original, fechas, frecuencia,
    plazo. Si cambia el monto, el saldo se recalcula contra lo ya abonado."""
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    CAMPOS = {"original_amount", "due_date", "start_date", "payment_frequency", "term"}
    data = {k: v for k, v in (body or {}).items() if k in CAMPOS and v not in (None, "")}
    if not data:
        raise HTTPException(status_code=400, detail="Nada que editar.")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT original_amount, status FROM cxp_cxc_ledger WHERE id=%s;", (ledger_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        sets, params = [], []
        for k in ("due_date", "start_date", "term"):
            if k in data:
                sets.append(f"{k} = %s"); params.append(data[k])
        if "payment_frequency" in data:
            sets.append("payment_frequency = %s"); params.append(int(data["payment_frequency"]))
        nuevo_saldo = None
        if "original_amount" in data:
            nuevo = float(data["original_amount"])
            if nuevo <= 0:
                raise HTTPException(status_code=400, detail="Monto inválido.")
            # El saldo se deriva SIEMPRE de monto - abonado (fuente de verdad:
            # el historial de abonos, que no se toca aquí)
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM cartera_payments WHERE ledger_id=%s;", (ledger_id,))
            abonado = float(cur.fetchone()[0])
            nuevo_saldo = max(0.0, nuevo - abonado)
            sets.append("original_amount = %s"); params.append(nuevo)
            sets.append("remaining_balance = %s"); params.append(nuevo_saldo)
            nuevo_status = "PAGADO" if nuevo_saldo == 0 else ("PENDIENTE" if row[1] == "PAGADO" else row[1])
            sets.append("status = %s"); params.append(nuevo_status)
        params.append(ledger_id)
        cur.execute(f"UPDATE cxp_cxc_ledger SET {', '.join(sets)} WHERE id = %s;", params)
        conn.commit()
        cur.close()
        release_db_connection(conn)
        conn = None
        return {"status": "OK", "remaining_balance": nuevo_saldo}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn is not None:
            try: release_db_connection(conn)
            except Exception: pass


@router.delete("/api/cartera/payments/{payment_id}")
def delete_cartera_payment(payment_id: int):
    """Elimina un abono para corregirlo: borra la partida, sus líneas de asiento
    en el kernel (referencia PAY-{id}) y recalcula saldo y estado de la cuenta."""
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM cartera_payments WHERE id = %s RETURNING ledger_id, amount;", (payment_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Abono no encontrado")
        ledger_id = row[0]
        # La partida contable del abono desaparece COMPLETA con él (2 líneas de
        # partida doble con referencia PAY-{id}) — libros coherentes con cartera.
        cur.execute("DELETE FROM kernel_journal_entries WHERE referencia = %s;", (f"PAY-{payment_id}",))
        asientos_borrados = cur.rowcount
        # Saldo SIEMPRE derivado: original - abonos restantes
        cur.execute("""
            UPDATE cxp_cxc_ledger l
               SET remaining_balance = GREATEST(0, l.original_amount - COALESCE(
                       (SELECT SUM(p.amount) FROM cartera_payments p WHERE p.ledger_id = l.id), 0)),
                   status = CASE
                       WHEN l.original_amount - COALESCE(
                           (SELECT SUM(p.amount) FROM cartera_payments p WHERE p.ledger_id = l.id), 0) <= 0
                       THEN 'PAGADO'
                       WHEN l.status = 'PAGADO' THEN 'PENDIENTE'
                       ELSE l.status END
             WHERE l.id = %s
            RETURNING remaining_balance, status;
        """, (ledger_id,))
        saldo, status = cur.fetchone()
        conn.commit()
        cur.close()
        release_db_connection(conn)
        conn = None
        return {"status": "OK", "ledger_id": ledger_id, "new_balance": float(saldo),
                "new_status": status, "journal_lines_removed": asientos_borrados}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn is not None:
            try: release_db_connection(conn)
            except Exception: pass


@router.put("/api/cartera/{ledger_id}/plan")
def update_cartera_plan(ledger_id: int, body: dict):
    """Define o edita el plan de pagos de una cuenta existente (Fase 1).
    body: {min_payment, interest_rate, interest_period}. null/0 = quitar."""
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    min_payment = float(body["min_payment"]) if body.get("min_payment") else None
    interest_rate = float(body["interest_rate"]) if body.get("interest_rate") else None
    interest_period = (body.get("interest_period") or "MENSUAL").upper()
    if interest_period not in ("MENSUAL", "ANUAL"):
        interest_period = "MENSUAL"
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE cxp_cxc_ledger
               SET min_payment = %s, interest_rate = %s, interest_period = %s
             WHERE id = %s RETURNING id;
        """, (min_payment, interest_rate, interest_period, ledger_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        conn.commit()
        cur.close()
        release_db_connection(conn)
        conn = None
        return {"status": "OK", "min_payment": min_payment,
                "interest_rate": interest_rate, "interest_period": interest_period}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn is not None:
            try: release_db_connection(conn)
            except Exception: pass


@router.get("/api/cartera/summary")
def get_cartera_summary():
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # cartera_payments se crea en init_db() al arrancar (ya no DDL por request)
        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE type='CXC') as total_cxc,
                COUNT(*) FILTER (WHERE type='CXP') as total_cxp,
                COALESCE(SUM(original_amount) FILTER (WHERE type='CXC'), 0) as monto_cxc,
                COALESCE(SUM(original_amount) FILTER (WHERE type='CXP'), 0) as monto_cxp,
                COALESCE(SUM(remaining_balance) FILTER (WHERE type='CXC'), 0) as pendiente_cxc,
                COALESCE(SUM(remaining_balance) FILTER (WHERE type='CXP'), 0) as pendiente_cxp,
                COUNT(*) FILTER (WHERE status='PAGADO') as pagados,
                COUNT(*) FILTER (WHERE status='VENCIDO') as vencidos,
                COALESCE(SUM(remaining_balance) FILTER (
                    WHERE status NOT IN ('PAGADO', 'CANCELADO') AND due_date < CURRENT_DATE
                ), 0) as vencido_monto,
                COALESCE(SUM(remaining_balance) FILTER (
                    WHERE status NOT IN ('PAGADO', 'CANCELADO')
                    AND due_date >= CURRENT_DATE AND due_date <= CURRENT_DATE + INTERVAL '7 days'
                ), 0) as proximo_monto
            FROM cxp_cxc_ledger;
        """)
        row = cur.fetchone()
        cur.close()
        release_db_connection(conn)
        return {
            # Conteos (uso interno / futuros paneles)
            "total_cxc": row[0], "total_cxp": row[1],
            "monto_cxc": float(row[2]), "monto_cxp": float(row[3]),
            "pendiente_cxc": float(row[4]), "pendiente_cxp": float(row[5]),
            "pagados": row[6], "vencidos": row[7],
            # Montos — consumidos por CarteraKpiBar.jsx (cxc/cxp = saldo pendiente,
            # no el conteo; antes el frontend leía estos nombres de un shape que
            # nunca existía y siempre daba NaN)
            "cxc_total": float(row[4]), "cxp_total": float(row[5]),
            "vencido_total": float(row[8]), "proximo_total": float(row[9]),
        }
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except Exception: pass
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/cartera/{ledger_id}/payments")
def get_cartera_payments(ledger_id: int):
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, amount, payment_date, note, balance_after, created_at,
                   interest_part, principal_part
            FROM cartera_payments WHERE ledger_id = %s
            ORDER BY created_at DESC;
        """, (ledger_id,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        for r in rows:
            for k in ['payment_date','created_at']:
                if k in r and r[k]: r[k] = str(r[k])
            for k in ['amount','balance_after','interest_part','principal_part']:
                if k in r and r[k] is not None: r[k] = float(r[k])
        cur.close()
        release_db_connection(conn)
        return rows
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except Exception: pass
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/cartera/{ledger_id}/payment")
def register_cartera_payment(ledger_id: int, body: dict):
    from fin_sys_core.database_driver import get_db_connection, release_db_connection
    amount = float(body.get("amount", 0))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Monto inválido")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT remaining_balance, status, interest_rate, interest_period, start_date
            FROM cxp_cxc_ledger WHERE id = %s;
        """, (ledger_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        # Interés simple sobre saldo desde el último abono (o el inicio):
        # el abono cubre PRIMERO el interés devengado y el resto amortiza capital.
        cur.execute("""
            SELECT MAX(payment_date) FROM cartera_payments WHERE ledger_id = %s;
        """, (ledger_id,))
        last_pay = cur.fetchone()[0]
        from fin_sys_core.cartera_plan import dividir_abono
        interest_part, principal_part, new_balance = dividir_abono(
            amount, float(row[0]), row[2], row[3], last_pay or row[4])
        new_status = "PAGADO" if new_balance == 0 else row[1]
        cur.execute("""
            INSERT INTO cartera_payments (ledger_id, amount, payment_date, note, balance_after,
                                          interest_part, principal_part)
            VALUES (%s, %s, COALESCE(%s, CURRENT_DATE), %s, %s, %s, %s) RETURNING id;
        """, (ledger_id, amount, body.get("payment_date") or None,
              body.get("note") or None, new_balance, interest_part, principal_part))
        pid = cur.fetchone()[0]
        cur.execute("UPDATE cxp_cxc_ledger SET remaining_balance=%s, status=%s WHERE id=%s;",
                    (new_balance, new_status, ledger_id))
        conn.commit()
        # Zero-COA: Emitir asiento de pago al kernel
        try:
            from shared.helpers import emit_journal_entry
            emit_journal_entry(
                category="__CXC_PAYMENT__", tx_type="CXC",
                amount=amount, referencia=f"PAY-{pid}",
                descripcion=f"Abono cartera #{ledger_id}"
            )
        except Exception as emit_err:
            print(f"⚠️ [CARTERA] Fallo emitiendo asiento de abono PAY-{pid}: {emit_err}")
        cur.close()
        release_db_connection(conn)
        conn = None
        return {"status": "OK", "payment_id": pid, "new_balance": new_balance,
                "new_status": new_status, "interest_part": interest_part,
                "principal_part": principal_part}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Libera también cuando la salida fue una HTTPException (p.ej. 404)
        if conn is not None:
            try:
                release_db_connection(conn)
            except Exception:
                pass

@router.post("/api/cartera")
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
        # Plan de pagos (Fase 1 — opcional): cuota mínima por corte e interés
        # simple sobre saldo. NULL = cuenta clásica, comportamiento intacto.
        min_payment = float(body["min_payment"]) if body.get("min_payment") else None
        interest_rate = float(body["interest_rate"]) if body.get("interest_rate") else None
        interest_period = (body.get("interest_period") or "MENSUAL").upper()
        if interest_period not in ("MENSUAL", "ANUAL"):
            interest_period = "MENSUAL"
        cur.execute("""
            INSERT INTO cxp_cxc_ledger
                (third_party_id, type, original_amount, remaining_balance, due_date, term, status,
                 start_date, payment_frequency, min_payment, interest_rate, interest_period)
            VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_DATE), %s, %s, %s, %s) RETURNING id;
        """, (body["third_party_id"], body["type"], amount, remaining,
              body["due_date"], body["term"],
              "PAGADO" if remaining == 0 else "PENDIENTE",
              start_date, payment_freq, min_payment, interest_rate, interest_period))
        lid = cur.fetchone()[0]
        if partial > 0:
            # El abono inicial es del día cero: sin interés devengado, todo a capital
            cur.execute("""
                INSERT INTO cartera_payments (ledger_id, amount, payment_date, note, balance_after,
                                              interest_part, principal_part)
                VALUES (%s, %s, CURRENT_DATE, 'Abono inicial', %s, 0, %s);
            """, (lid, partial, remaining, partial))
        conn.commit()
        # Zero-COA: Emitir asiento de creación CXC/CXP al kernel
        try:
            from shared.helpers import emit_journal_entry
            coa_cat = "__CXC_CREATE__" if body["type"] == "CXC" else "__CXP_CREATE__"
            emit_journal_entry(
                category=coa_cat, tx_type=body["type"],
                amount=amount,
                referencia=f"{body['type']}-{lid}",
                descripcion=f"Crear {body['type']} #{lid}"
            )
        except Exception as emit_err:
            print(f"⚠️ [CARTERA] Fallo emitiendo asiento {body['type']}-{lid}: {emit_err}")
        cur.close()
        release_db_connection(conn)
        conn = None
        return {"status": "CREADO", "id": lid, "remaining_balance": remaining}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn is not None:
            try: release_db_connection(conn)
            except Exception: pass


# ── POST /api/third-parties — Crear tercero standalone ──
@router.post("/api/third-parties")
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
            INSERT INTO third_parties (name, identification_type, identification_number,
                                       email, phone, website, address, maps_link)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """, (name, body.get("identification_type", "NIT"),
              body.get("identification_number", ""),
              body.get("email", ""), body.get("phone", ""),
              body.get("website", ""), body.get("address", ""),
              body.get("maps_link", "")))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        release_db_connection(conn)
        return {"id": new_id, "name": name, "status": "CREADO"}
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except Exception: pass
        raise HTTPException(status_code=500, detail=str(e))


# ── PUT /api/third-parties/{tp_id} ──
@router.put("/api/third-parties/{tp_id}")
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
@router.get("/api/cartera/alerts")
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
            except Exception: pass
        raise HTTPException(status_code=500, detail=str(e))


# ── DELETE /api/cartera/{id} ──
@router.delete("/api/cartera/{ledger_id}")
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
        conn = None
        return {"status": "ELIMINADO", "id": ledger_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Libera también cuando la salida fue una HTTPException (p.ej. 404 con
        # el DELETE de payments ya ejecutado): el finally garantiza rollback
        # implícito al devolver la conexión sin commit
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                release_db_connection(conn)
            except Exception:
                pass
