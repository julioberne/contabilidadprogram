# -*- coding: utf-8 -*-
"""
compendio_visor.py — Arma la página del Compendio para el cliente (spec 13.6).
Archivo NUEVO (Zero-Impact). Un solo visor (templates/compendio_visor.html +
compendio_visor.js) para el link /c/<código> y, más adelante, el HTML offline.

Los datos van en <script type="application/json"> con <, > y & escapados: un
concepto como "</script><script>…" se ve como texto, nunca se ejecuta. El JS
del visor lleva el nonce de la CSP (sin 'unsafe-inline' para scripts).
"""
import html
import json
import os
import re
import secrets
from typing import Any, Dict, Tuple

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
_MARCA = re.compile(r"__(TITULO|NONCE|JS|DATOS|META)__")


def _leer(nombre: str) -> str:
    with open(os.path.join(_DIR, nombre), encoding="utf-8") as fh:
        return fh.read()


def datos_seguros(datos: Dict[str, Any]) -> str:
    return (json.dumps(datos, ensure_ascii=False)
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def csp(nonce: str) -> str:
    return ("default-src 'none'; "
            f"script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; "
            "img-src 'self' data: blob:; media-src 'self' data: blob:; frame-src 'self' blob:; "
            "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")   # 'self': aviso 13.6-c


def csp_offline(nonce: str) -> str:
    """El HTML offline no tiene cabeceras: la CSP va en un <meta>. Todo está adentro (data:)."""
    return ("default-src 'none'; "
            f"script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; "
            "img-src data: blob:; media-src data: blob:; frame-src blob:; base-uri 'none'; form-action 'none'")


def pagina(datos: Dict[str, Any], offline: bool = False) -> Tuple[str, str]:
    """→ (html, nonce). En el link, el nonce va en la cabecera CSP; offline, en un <meta>."""
    nonce = secrets.token_urlsafe(16)
    titulo = html.escape(f"{datos.get('nombre') or 'Compendio'} · {datos.get('folio') or ''}".strip(" ·"))
    # Sin html.escape: volvería &#x27; las comillas simples de la CSP ('nonce-…'). No lleva comillas dobles.
    meta = (f'<meta http-equiv="Content-Security-Policy" content="{csp_offline(nonce)}">' if offline else "")
    valores = {"TITULO": titulo, "NONCE": nonce, "JS": _leer("compendio_visor.js"), "DATOS": datos_seguros(datos),
               "META": meta}
    # Una sola pasada sobre la PLANTILLA: lo insertado (p. ej. un nombre "__DATOS__") no se vuelve a leer.
    return _MARCA.sub(lambda m: valores[m.group(1)], _leer("compendio_visor.html")), nonce


PAGINA_NO_DISPONIBLE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Enlace no disponible</title>
<style>body{margin:0;background:#FCF9F2;font-family:"Roboto Mono",ui-monospace,monospace;color:#000}
div{max-width:460px;margin:15vh auto;padding:16px;background:#fff;border:2px solid #000;box-shadow:4px 4px 0 #000}
h1{font-size:16px;text-transform:uppercase;margin:0 0 8px}p{font-size:13px;margin:0}</style></head>
<body><div><h1>⛔ Este enlace ya no está disponible</h1>
<p>Venció o fue revocado. Pídele a quien te lo envió un enlace nuevo.</p></div></body></html>"""
