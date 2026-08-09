# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Bot IA (Módulo 09).

Vinculación web↔chat (código de un solo uso) + API de la bandeja de borradores.
Todos los endpoints exigen sesión (require_auth): el bot de Telegram NO entra
por aquí (usa long-polling y accede al dominio directamente). El webhook de
WhatsApp llegará en la Etapa D con verificación de firma X-Hub-Signature-256.
"""
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException

from routers.auth_guard import require_auth

router = APIRouter(tags=["Bot IA"])

# Alfabeto sin caracteres ambiguos (0/O, 1/I)
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _uid(user: dict) -> int:
    try:
        return int(user.get("uid") or 0)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Sesión sin uid válido.")


@router.post("/api/bot/link-code")
def create_link_code(user: dict = Depends(require_auth)):
    """Genera un código de vinculación de un solo uso (10 minutos)."""
    try:
        from db_pool import get_conn, put_conn
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        conn = get_conn()
        try:
            cur = conn.cursor()
            # Limpieza oportunista de códigos viejos
            cur.execute("DELETE FROM bot_link_codes WHERE expires_at < NOW() - INTERVAL '1 day'")
            cur.execute("""
                INSERT INTO bot_link_codes (code_hash, hub_user_id, expires_at)
                VALUES (%s, %s, NOW() + INTERVAL '10 minutes')
            """, (code_hash, _uid(user)))
            conn.commit()
            cur.close()
        finally:
            put_conn(conn)
        return {
            "code": code,
            "expira_en_minutos": 10,
            "instrucciones": f"Escríbele al bot de Telegram: /vincular {code}",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/bot/links")
def list_links(user: dict = Depends(require_auth)):
    """Chats vinculados del usuario actual."""
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, channel, chat_id, default_portfolio, status, created_at
                FROM bot_chat_links WHERE hub_user_id = %s ORDER BY id
            """, (_uid(user),))
            rows = cur.fetchall()
            cur.close()
        finally:
            put_conn(conn)
        return [{"id": r[0], "channel": r[1], "chat_id": r[2],
                 "default_portfolio": r[3], "status": r[4],
                 "created_at": str(r[5])} for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/bot/drafts")
def list_drafts(status: str = "BORRADOR", user: dict = Depends(require_auth)):
    """Bandeja: borradores del usuario actual, por estado."""
    if status not in ("BORRADOR", "PROCESANDO", "CONFIRMADO", "ERROR", "DESCARTADO", "TODOS"):
        raise HTTPException(status_code=422, detail="status inválido")
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            filtro = "" if status == "TODOS" else "AND status = %(status)s"
            cur.execute(f"""
                SELECT id, status, channel, portfolio_name, payload, raw_text,
                       media_path, error, confirmed_transaction_id, created_at
                FROM transaction_drafts
                WHERE user_id = %(uid)s {filtro}
                ORDER BY id DESC LIMIT 100
            """, {"uid": _uid(user), "status": status})
            rows = cur.fetchall()
            cur.close()
        finally:
            put_conn(conn)
        return [{
            "id": r[0], "status": r[1], "channel": r[2], "portfolio_name": r[3],
            "payload": r[4], "raw_text": r[5], "media_path": r[6], "error": r[7],
            "confirmed_transaction_id": r[8], "created_at": str(r[9]),
        } for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/bot/drafts/{draft_id}/confirm")
def confirm_draft_endpoint(draft_id: int, user: dict = Depends(require_auth)):
    """Confirma un borrador desde la web — mismo camino determinista del chat."""
    try:
        from bot_driver import confirmar_draft
        return {"result": confirmar_draft(draft_id, hub_user_id=_uid(user))}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/bot/drafts/{draft_id}/discard")
def discard_draft_endpoint(draft_id: int, user: dict = Depends(require_auth)):
    try:
        from bot_driver import descartar_draft
        return {"result": descartar_draft(draft_id, hub_user_id=_uid(user))}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
