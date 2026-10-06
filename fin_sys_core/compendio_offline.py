# -*- coding: utf-8 -*-
"""
compendio_offline.py — 💾 HTML offline del Compendio para el cliente (spec 13.6, etapa 13.6-e).
Archivo NUEVO (Zero-Impact). El MISMO visor del link (compendio_visor), con todo
adentro: los datos de la foto y los comprobantes como data: (fotos con Pillow, lado
mayor 1280 px, JPEG q65). Un solo archivo que se manda por WhatsApp o correo y abre
sin internet. No vence ni se revoca (por eso lo baja solo quien tiene el link vigente).

Presupuesto COMPENDIO_MAX_MB (25, el tope de un correo) contando el +33 % del base64:
lo que no cabe queda "omitido por tamaño: véalo en el link".
"""
import base64
import copy
import io
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

MAX_LADO_PX = 1280
CALIDAD_JPEG = 65


def _foto(datos: bytes) -> Optional[bytes]:
    try:
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(datos))).convert("RGB")
        im.thumbnail((MAX_LADO_PX, MAX_LADO_PX))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=CALIDAD_JPEG, optimize=True)
        return buf.getvalue()
    except Exception:
        return None


def generar(snapshot: Dict[str, Any], urls_por_tx: Dict[int, List[str]], traer: Callable[[str], Optional[bytes]],
            describir: Callable[[str], Dict[str, Any]], expira_en=None) -> bytes:
    from fin_sys_core import compendio_pdf, compendio_visor
    bajados = compendio_pdf._bajar(snapshot, urls_por_tx, traer, describir, tipos=("imagen", "pdf", "audio", "otro"))
    presupuesto = compendio_pdf.max_bytes() - 400_000          # el visor y los datos
    datos = copy.deepcopy(snapshot)
    for t in datos.get("txs", []):
        sops = []
        for j, _url in enumerate(urls_por_tx.get(t["id"]) or []):
            b = bajados[(t["i"], j)]
            d = b["descr"]
            s = {"j": j, "nombre": d["nombre"], "tipo": d["tipo"], "servible": False}
            contenido, mime = b["datos"], d["mime"]
            if d["servible"] and contenido and d["tipo"] == "imagen":
                contenido, mime = _foto(contenido), "image/jpeg"
            if not d["servible"]:
                pass
            elif not contenido:
                s["nota"] = "no se pudo leer al generar esta copia"
            elif len(contenido) * 4 // 3 > presupuesto:
                s["nota"] = "omitido por tamaño: véalo en el link"
            else:
                presupuesto -= len(contenido) * 4 // 3
                s.update(servible=True, data=f"data:{mime};base64,{base64.b64encode(contenido).decode()}")
            sops.append(s)
        t["soportes"] = sops
    datos.update(offline=True, base="", previa=False, expira_en=None,
                 generado=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    html, _nonce = compendio_visor.pagina(datos, offline=True)
    return html.encode("utf-8")
