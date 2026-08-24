# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 — Auth Guard: tokens de sesión firmados (HMAC)
---------------------------------------------------------------
Archivo NUEVO (Zero-Impact). Sin dependencias externas ni tablas nuevas.

Flujo:
  1. POST /api/hub/users/login emite un token firmado (create_session_token).
  2. El frontend lo envía como  Authorization: Bearer <token>.
  3. Los endpoints protegidos lo exigen vía Depends(require_auth/require_admin).

El secreto se toma de SESSION_SECRET (recomendado en producción). Si no está,
se deriva de DB_PASSWORD para que los tokens sobrevivan reinicios sin tocar .env.
"""
import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Depends, Header, HTTPException

# TTL de la sesión: 7 días. Con 12h la sesión moría a media jornada y los
# botones admin (⚠️ Reiniciar / ⚡ Semillar) fallaban con 401 sin que fuera
# obvio por qué (caso real 2026-08-10).
TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60


def _secret() -> bytes:
    explicit = os.getenv("SESSION_SECRET")
    if explicit:
        return explicit.encode()
    # Derivado estable (no aleatorio por boot) para no invalidar sesiones en
    # cada reinicio. Configurar SESSION_SECRET en producción es lo recomendado.
    seed = f"finsys-session::{os.getenv('DB_PASSWORD', 'dev')}"
    return hashlib.sha256(seed.encode()).digest()


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64d(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def create_session_token(user: dict) -> str:
    """Genera un token firmado con los datos mínimos de sesión."""
    payload = {
        "uid":  str(user.get("id", "")),
        "name": user.get("name", ""),
        "role": (user.get("role") or "member").lower(),
        "su":   bool(user.get("is_superuser")),
        "exp":  int(time.time()) + TOKEN_TTL_SECONDS,
    }
    raw = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64e(hmac.new(_secret(), raw.encode(), hashlib.sha256).digest())
    return f"{raw}.{sig}"


def decode_session_token(token: str) -> dict | None:
    """Valida firma y expiración. Devuelve el payload o None."""
    try:
        raw, sig = token.split(".", 1)
        expected = _b64e(hmac.new(_secret(), raw.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_b64d(raw))
        if int(payload.get("exp", 0)) < time.time():
            return None
        return payload
    except Exception:
        return None


def require_auth(authorization: str = Header(None)) -> dict:
    """Dependencia FastAPI: exige un Bearer token válido."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Autenticación requerida. Inicia sesión de nuevo.")
    payload = decode_session_token(authorization[7:].strip())
    if not payload:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada. Inicia sesión de nuevo.")
    return payload


def require_admin(user: dict = Depends(require_auth)) -> dict:
    """Dependencia FastAPI: exige rol owner/admin o superusuario."""
    if not (user.get("su") or user.get("role") in ("owner", "admin")):
        raise HTTPException(status_code=403, detail="Se requiere rol administrador.")
    return user
