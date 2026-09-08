# -*- coding: utf-8 -*-
"""Migración 2026-09-08 — Evidencias al Supabase Storage (caso PAGO MURDO).

La BD es compartida local↔prod pero /uploads era el disco de cada entorno:
un comprobante subido en local daba 404 en prod. Este script sube al bucket
`hr-docs/evidence/` cada evidencia referenciada por transactions que EXISTA
en el disco donde corre, y actualiza evidence_file_path a la URL pública
(compartida por todos los entornos).

- Idempotente: ignora las que ya empiezan por http.
- Best-effort: si el bucket rechaza un MIME (ej. audio), lo reporta y sigue.
- Corre donde estén los archivos: en el PC de Andrés rescata lo subido en
  local; dentro del contenedor de prod rescataría lo del volumen.
"""
import mimetypes
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(RAIZ, ".env"))

import httpx  # noqa: E402

from fin_sys_core.db_pool import get_conn, put_conn  # noqa: E402

SUPABASE_URL = "https://sciorfjvdqxvcwgvnmbv.supabase.co"
# Llave ANON pública (la misma que ya usa el frontend en supabaseClient.js)
ANON = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNjaW9yZmp2ZHF4dmN3Z3ZubWJ2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA0Mzk2NjYsImV4cCI6MjA5NjAxNTY2Nn0."
        "yO9F0gVl3DqCrrrvY-UAMcTuz_s-KsYYTXooDIBIyLk")
BUCKET = "hr-docs"
PREFIJO = "evidence"

# mimetypes en Windows depende del registro y no conoce .webp — mapa explícito
MIME_EXPLICITO = {
    ".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".gif": "image/gif", ".pdf": "application/pdf",
    ".ogg": "audio/ogg", ".webm": "video/webm",
}


def subir(nombre_archivo: str, contenido: bytes, mime: str) -> str:
    """Sube al bucket y devuelve la URL pública. Lanza si el bucket rechaza."""
    destino = f"{PREFIJO}/{nombre_archivo}"
    r = httpx.post(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{destino}",
        headers={"apikey": ANON, "Authorization": f"Bearer {ANON}",
                 "Content-Type": mime, "x-upsert": "true"},
        content=contenido, timeout=60,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"{r.status_code}: {r.text[:120]}")
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{destino}"


def main():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, evidence_file_path FROM transactions
            WHERE evidence_file_path IS NOT NULL
              AND evidence_file_path <> ''
              AND evidence_file_path NOT LIKE 'http%'
            ORDER BY id
        """)
        filas = cur.fetchall()
        print(f"Evidencias locales referenciadas en la BD: {len(filas)}")
        migradas, sin_archivo, rechazadas = 0, [], []
        for tx_id, ruta in filas:
            nombre = os.path.basename(ruta.replace("\\", "/"))
            local = os.path.join(RAIZ, "uploads", nombre)
            if not os.path.exists(local):
                sin_archivo.append((tx_id, nombre))
                continue
            ext = os.path.splitext(nombre)[1].lower()
            mime = MIME_EXPLICITO.get(ext) or mimetypes.guess_type(nombre)[0] \
                or "application/octet-stream"
            try:
                with open(local, "rb") as f:
                    contenido = f.read()
                try:
                    url = subir(nombre, contenido, mime)
                except RuntimeError as e:
                    # Lista blanca del bucket sin ese MIME (ej. webp): si es
                    # imagen, convertir a PNG y reintentar.
                    if "invalid_mime_type" not in str(e) or not mime.startswith("image/"):
                        raise
                    import io
                    from PIL import Image
                    buf = io.BytesIO()
                    Image.open(io.BytesIO(contenido)).convert("RGB").save(buf, "PNG")
                    nombre = os.path.splitext(nombre)[0] + ".png"
                    url = subir(nombre, buf.getvalue(), "image/png")
                    print(f"  ↻ TX {tx_id}: convertida a PNG ({mime} no permitido)")
            except Exception as e:
                rechazadas.append((tx_id, nombre, str(e)))
                continue
            cur.execute("UPDATE transactions SET evidence_file_path = %s WHERE id = %s",
                        (url, tx_id))
            conn.commit()
            migradas += 1
            print(f"  ✅ TX {tx_id}: {nombre} → {url}")
        print(f"\nMigradas: {migradas}")
        if sin_archivo:
            print(f"Sin archivo en ESTE disco (subidas en otro entorno): {sin_archivo}")
        if rechazadas:
            print(f"Rechazadas por el bucket (MIME no permitido u otro): {rechazadas}")
    finally:
        put_conn(conn)


if __name__ == "__main__":
    main()
