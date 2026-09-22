# -*- coding: utf-8 -*-
"""storage_media.py — Subida de media del bot a Supabase Storage (Etapa E).

La BD es compartida local↔prod pero /uploads era el disco de cada entorno
(caso PAGO MURDO, 2026-09-08). La media nueva del bot (fotos de comprobantes,
notas de voz) va al bucket `hr-docs/evidence/` — el mismo que usa el
formulario web — y la URL pública queda en el borrador/transacción.

La llave ANON es pública por diseño (es la misma que viaja en el bundle del
frontend); el bucket controla qué MIME acepta. Overrides por env por si el
proyecto Supabase cambia.
"""
import os
import uuid

import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://sciorfjvdqxvcwgvnmbv.supabase.co").rstrip("/")
SUPABASE_ANON = os.getenv(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNjaW9yZmp2ZHF4dmN3Z3ZubWJ2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA0Mzk2NjYsImV4cCI6MjA5NjAxNTY2Nn0."
    "yO9F0gVl3DqCrrrvY-UAMcTuz_s-KsYYTXooDIBIyLk",
)
BUCKET = os.getenv("EVIDENCE_BUCKET", "hr-docs")
PREFIJO = os.getenv("EVIDENCE_PREFIX", "evidence")

# 20MB: tope de descarga del Bot API de Telegram; nadie legítimo lo supera.
MAX_BYTES = 20 * 1024 * 1024


def subir_evidencia(nombre: str, contenido: bytes, mime: str) -> str | None:
    """Sube bytes al bucket. → URL pública, o None si falla (el caller decide
    su fallback — nunca se rompe el flujo del bot por la media)."""
    if not contenido or len(contenido) > MAX_BYTES:
        return None
    seguro = "".join(c if c.isalnum() or c in "._-" else "_" for c in (nombre or "archivo"))[-60:]
    destino = f"{PREFIJO}/{uuid.uuid4().hex[:8]}_{seguro}"
    try:
        r = httpx.post(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{destino}",
            headers={"apikey": SUPABASE_ANON,
                     "Authorization": f"Bearer {SUPABASE_ANON}",
                     "Content-Type": mime or "application/octet-stream"},
            content=contenido, timeout=60,
        )
        if r.status_code in (200, 201):
            return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{destino}"
        print(f"⚠️ [storage_media] Bucket rechazó {seguro} ({mime}): "
              f"{r.status_code} {r.text[:120]}")
    except Exception as e:
        print(f"⚠️ [storage_media] Subida falló ({seguro}): {e}")
    return None


def eliminar_evidencia(url: str) -> bool:
    """Borra un objeto del bucket a partir de su URL pública (retención de
    borradores, etapa 09.F). Best-effort: si la policy del bucket no permite
    DELETE con la llave anon, deja log y devuelve False — nada se rompe.
    URLs ajenas al bucket (rutas /uploads locales) se ignoran."""
    marca = f"/storage/v1/object/public/{BUCKET}/"
    if not url or marca not in url:
        return False
    destino = url.split(marca, 1)[1].split("?", 1)[0]
    if not destino:
        return False
    try:
        r = httpx.delete(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{destino}",
            headers={"apikey": SUPABASE_ANON, "Authorization": f"Bearer {SUPABASE_ANON}"},
            timeout=30,
        )
        if r.status_code in (200, 204):
            return True
        print(f"⚠️ [storage_media] No se pudo borrar {destino}: {r.status_code} {r.text[:120]}")
    except Exception as e:
        print(f"⚠️ [storage_media] Borrado falló ({destino}): {e}")
    return False
