# -*- coding: utf-8 -*-
"""
compendio_cache.py — Caché del ⬇ PDF y 💾 HTML offline de los compendios + tope de
generaciones simultáneas (escalabilidad, 06-oct). Archivo NUEVO (Zero-Impact).

La foto de un compendio es inmutable: su PDF/HTML solo cambia si cambia la lista de
comprobantes (se agregó o borró uno) o la fecha de vencimiento (va en la portada). La
clave lleva esas tres cosas, así que nunca se sirve algo viejo.

- En DISCO (tmp del contenedor): lo comparten los workers de gunicorn. TTL 1 h y tope
  300 MB (COMPENDIO_CACHE_SEG / COMPENDIO_CACHE_MB); se poda al guardar.
- Semáforo por worker: máximo COMPENDIO_GENERACIONES (2) armándose a la vez. Si no hay
  turno en 60 s → Ocupado (el router responde 503 "intenta en un minuto"): un pico de
  descargas nunca deja sin hilos al resto de la app.
- Sin disco o sin permisos, se sirve igual (solo que sin caché).
"""
import hashlib
import json
import os
import tempfile
import threading
import time
from typing import Callable, Dict, List, Optional

DIR = os.path.join(tempfile.gettempdir(), "finsys-compendios")
TTL = int(os.getenv("COMPENDIO_CACHE_SEG", "3600"))
TOPE_BYTES = int(float(os.getenv("COMPENDIO_CACHE_MB", "300")) * 1024 * 1024)
ESPERA_SEG = 60
_TURNOS = threading.BoundedSemaphore(max(1, int(os.getenv("COMPENDIO_GENERACIONES", "2"))))


class Ocupado(Exception):
    """Todos los turnos de generación están ocupados."""


def clave(cid: int, formato: str, urls: Dict[int, List[str]], expira_en: Optional[str]) -> str:
    base = json.dumps({"c": cid, "f": formato, "e": expira_en,
                       "u": {str(k): list(v) for k, v in sorted(urls.items())}}, sort_keys=True)
    return hashlib.sha256(base.encode()).hexdigest()[:32]


def _ruta(k: str, formato: str) -> str:
    return os.path.join(DIR, f"{k}.{formato}")


def leer(k: str, formato: str) -> Optional[bytes]:
    p = _ruta(k, formato)
    try:
        if time.time() - os.path.getmtime(p) <= TTL:
            with open(p, "rb") as fh:
                return fh.read()
    except OSError:
        pass
    return None


def _podar() -> None:
    ahora, vivos = time.time(), []
    for nombre in os.listdir(DIR):
        p = os.path.join(DIR, nombre)
        try:
            st = os.stat(p)
        except OSError:
            continue
        viejo = ahora - st.st_mtime > (600 if nombre.endswith(".tmp") else TTL)
        if viejo:
            try:
                os.remove(p)
            except OSError:
                pass
        else:
            vivos.append((st.st_mtime, st.st_size, p))
    total = sum(v[1] for v in vivos)
    for _m, tam, p in sorted(vivos):                      # primero los más viejos
        if total <= TOPE_BYTES:
            break
        try:
            os.remove(p)
            total -= tam
        except OSError:
            pass


def guardar(k: str, formato: str, contenido: bytes) -> None:
    try:
        os.makedirs(DIR, exist_ok=True)
        tmp = f"{_ruta(k, formato)}.{os.getpid()}.{threading.get_ident()}.tmp"
        with open(tmp, "wb") as fh:
            fh.write(contenido)
        os.replace(tmp, _ruta(k, formato))                # atómico: otro worker nunca lee medio archivo
        _podar()
    except OSError:
        pass


def obtener(k: str, formato: str, generar: Callable[[], bytes]) -> bytes:
    """Del disco si está; si no, lo arma (con turno) y lo guarda."""
    hit = leer(k, formato)
    if hit is not None:
        return hit
    if not _TURNOS.acquire(timeout=ESPERA_SEG):
        raise Ocupado()
    try:
        hit = leer(k, formato)                             # otro hilo pudo armarlo mientras esperábamos
        if hit is not None:
            return hit
        contenido = generar()
        guardar(k, formato, contenido)
        return contenido
    finally:
        _TURNOS.release()
