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

@router.get("/api/cartera/summary")
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

@router.get("/api/cartera/{ledger_id}/payments")
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
            from shared.helpers import emit_journal_entry
            emit_journal_entry(
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
            from shared.helpers import emit_journal_entry
            coa_cat = "__CXC_CREATE__" if body["type"] == "CXC" else "__CXP_CREATE__"
            emit_journal_entry(
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
            except: pass
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
        return {"status": "ELIMINADO", "id": ledger_id}
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            try: release_db_connection(conn)
            except: pass
        raise HTTPException(status_code=500, detail=str(e))
