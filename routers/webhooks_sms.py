# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: webhook de SMS bancarios (Bot IA, etapa 09.F).

Archivo NUEVO (Zero-Impact). Registrado en server.py ANTES del catch-all SPA.

  POST   /api/webhooks/sms              ← la app del teléfono (MacroDroid) — token X-SMS-Token
  POST   /api/webhooks/sms/token        ← crea un token (sesión); el token plano se devuelve UNA vez
  GET    /api/webhooks/sms/tokens       ← tokens del usuario (sesión)
  DELETE /api/webhooks/sms/tokens/{id}  ← revoca (sesión)

El webhook NO parsea ni habla con Telegram: valida, encola en bot_messages
(channel='sms') y responde 202 en milisegundos. El tick del poller
(fin_sys_core/bot_sms.procesar_pendientes) hace el resto (D-09F-01).
Seguridad (R-09F-01): token por usuario (hash sha256 en sms_ingest_tokens,
comparación en tiempo constante), allowlist de remitentes por token, cuerpo
≤ 4 KB, ≥ 60 SMS/min → 429. El teléfono debe apuntar a HTTPS (R-09F-11).
Spec: docs/specs/09-bot-ia/09.F-sms-bancolombia.md
"""
import json
import secrets
from typing import List, Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from routers.auth_guard import require_auth

router = APIRouter(tags=["Bot IA · SMS"])

MAX_BODY_BYTES = 4096
MAX_SMS_POR_MINUTO = 60


class TokenInput(BaseModel):
    label: Optional[str] = None
    remitentes: Optional[List[str]] = None      # default: ['85540'] (Bancolombia)


def _uid(user: dict) -> str:
    uid = (user.get("uid") or "").strip()
    if not uid:
        raise HTTPException(status_code=401, detail="Sesión sin uid válido.")
    return uid


def _leer_cuerpo(request: Request, body: bytes) -> dict:
    """JSON o form-urlencoded (el form es lo cómodo desde MacroDroid: no hay
    que escapar comillas ni saltos del SMS)."""
    ctype = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if ctype == "application/json":
        try:
            datos = json.loads(body.decode("utf-8", "replace") or "{}")
        except ValueError:
            raise HTTPException(status_code=400, detail="JSON inválido.")
        if not isinstance(datos, dict):
            raise HTTPException(status_code=400, detail="Se esperaba un objeto JSON.")
        return datos
    if ctype == "application/x-www-form-urlencoded":
        return {k: v[0] for k, v in parse_qs(body.decode("utf-8", "replace"),
                                             keep_blank_values=True).items()}
    raise HTTPException(status_code=415,
                        detail="Content-Type debe ser application/json o application/x-www-form-urlencoded.")


@router.post("/api/webhooks/sms", status_code=202)
async def recibir_sms(request: Request):
    """Encola un SMS. Respuestas: 202 {status: ACEPTADO|DUPLICADO} · 401 token ·
    403 remitente · 413 tamaño · 415 tipo · 422 sin texto · 429 tasa."""
    token = (request.headers.get("x-sms-token") or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Falta el header X-SMS-Token.")
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail=f"Cuerpo mayor a {MAX_BODY_BYTES} bytes.")
    datos = _leer_cuerpo(request, body)

    from bot_sms import encolar_sms, resolver_identidad, solo_digitos
    remitente = solo_digitos(datos.get("from") or datos.get("sms_number") or "")
    texto = str(datos.get("text") or datos.get("sms_message") or "").strip()
    sent_stamp = str(datos.get("sentStamp") or datos.get("sent_stamp") or "").strip() or None
    if not texto:
        raise HTTPException(status_code=422, detail="text vacío.")

    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        identidad = resolver_identidad(cur, token)
        if identidad is None:
            conn.rollback()
            raise HTTPException(status_code=401, detail="Token inválido o revocado.")
        if remitente not in identidad["allowlist"]:
            conn.commit()                       # last_seen_at sí se registra
            raise HTTPException(status_code=403,
                                detail=f"Remitente '{remitente}' no permitido para este token.")
        cur.execute("""
            SELECT COUNT(*) FROM bot_messages
             WHERE channel = 'sms' AND direction = 'IN'
               AND created_at > NOW() - INTERVAL '1 minute'
        """)
        if int(cur.fetchone()[0]) >= MAX_SMS_POR_MINUTO:
            conn.rollback()
            raise HTTPException(status_code=429, detail="Demasiados SMS por minuto.")
        msg_id, duplicado = encolar_sms(cur, identidad, remitente, texto, sent_stamp)
        conn.commit()
        cur.close()
    except HTTPException:
        raise
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        put_conn(conn)

    if duplicado:
        return {"status": "DUPLICADO"}
    return {"status": "ACEPTADO", "id": msg_id,
            "chat_vinculado": bool(identidad.get("chat_link_id"))}


# ── Gestión de tokens (sesión web) ───────────────────────────────────────────

@router.post("/api/webhooks/sms/token", status_code=201)
def crear_token(body: TokenInput = None, user: dict = Depends(require_auth)):
    """Crea un token para un teléfono. El token plano se devuelve UNA sola vez."""
    from bot_sms import hash_token, solo_digitos
    body = body or TokenInput()
    remitentes = [solo_digitos(r) for r in (body.remitentes or []) if solo_digitos(r)] or ["85540"]
    token = secrets.token_urlsafe(32)
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sms_ingest_tokens (hub_user_id, token_hash, label, sender_allowlist)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (_uid(user), hash_token(token), (body.label or "").strip()[:80] or None, remitentes))
            token_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
        finally:
            put_conn(conn)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "id": token_id, "token": token, "label": body.label, "remitentes": remitentes,
        "instrucciones": ("En MacroDroid: trigger 'SMS recibido' del remitente → acción "
                          "'HTTP Request' POST a https://<tu-dominio>/api/webhooks/sms con el "
                          "header X-SMS-Token y el cuerpo form-urlencoded from={sms_number}, "
                          "text={sms_message}. Guarda el token: no se vuelve a mostrar."),
    }


@router.get("/api/webhooks/sms/tokens")
def listar_tokens(user: dict = Depends(require_auth)):
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, label, sender_allowlist, created_at, last_seen_at, revoked_at
                  FROM sms_ingest_tokens WHERE hub_user_id = %s ORDER BY id
            """, (_uid(user),))
            rows = cur.fetchall()
            cur.close()
        finally:
            put_conn(conn)
        return [{"id": r[0], "label": r[1], "remitentes": list(r[2] or []),
                 "created_at": str(r[3]), "last_seen_at": str(r[4]) if r[4] else None,
                 "revoked_at": str(r[5]) if r[5] else None} for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/webhooks/sms/tokens/{token_id}")
def revocar_token(token_id: int, user: dict = Depends(require_auth)):
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE sms_ingest_tokens SET revoked_at = NOW()
                 WHERE id = %s AND hub_user_id = %s AND revoked_at IS NULL
            """, (token_id, _uid(user)))
            n = cur.rowcount
            conn.commit()
            cur.close()
        finally:
            put_conn(conn)
        if not n:
            raise HTTPException(status_code=404, detail="Token no encontrado o ya revocado.")
        return {"status": "REVOCADO", "id": token_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
