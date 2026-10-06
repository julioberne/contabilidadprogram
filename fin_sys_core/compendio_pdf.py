# -*- coding: utf-8 -*-
"""
compendio_pdf.py — ⬇ PDF del Compendio para el cliente (spec 13.6 §4.4, etapa 13.6-d).
Archivo NUEVO (Zero-Impact). Sale de la MISMA foto que el link (R-136-06): mismas
cifras, mismo folio. Se genera bajo demanda y no se guarda (D-136-03).

  portada  → nombre, folio, empresas, rango, nota y totales por moneda (USD aparte)
  índice   → una fila por transacción, con enlace a su página
  1 página por TX (o más si sus fotos no caben) → datos, 📍 enlace a Google Maps y
             las fotos de sus comprobantes (Pillow: lado mayor 1600 px, JPEG q70)
  los comprobantes que YA son PDF se anexan justo después de su TX (pypdf), con
  marcadores: Portada · Índice · cada TX · cada PDF anexo.

`traer(url) -> bytes | None` se inyecta (el router descarga del bucket propio; los
tests usan uno falso). Los comprobantes se bajan en paralelo y con presupuesto de
tamaño: si el PDF pasaría de COMPENDIO_MAX_MB, el resto queda como "véalo en el link".
"""
import io
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

MAX_LADO_PX = 1600
CALIDAD_JPEG = 70
_REEMPLAZOS = {"—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "...", "•": "-",
               "→": "->", "✔": "OK", "✘": "X", "▲": "+", "▼": "-", "∑": "Total", "€": "EUR", " ": " "}


def max_bytes() -> int:
    try:
        return int(float(os.getenv("COMPENDIO_MAX_MB", "25")) * 1024 * 1024)
    except ValueError:
        return 25 * 1024 * 1024


def _t(s) -> str:
    """Las fuentes base del PDF son latin-1: tildes y ñ sí; emojis y símbolos raros no (se quitan)."""
    s = str(s if s is not None else "")
    for a, b in _REEMPLAZOS.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "ignore").decode("latin-1")


def plata(v, moneda: str = "COP") -> str:
    n = float(v or 0)
    txt = f"{abs(n):,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")
    if txt.endswith(",00"):
        txt = txt[:-3]
    signo = "-" if n < 0 else ""
    return f"{signo}${txt}" if moneda == "COP" else f"{signo}{moneda} {txt}"


def _dia(iso) -> str:
    if not iso:
        return "-"
    if isinstance(iso, (date, datetime)):
        iso = iso.isoformat()
    p = str(iso)[:10].split("-")
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 else str(iso)


def _jpeg(datos: bytes) -> Optional[tuple]:
    """Foto → (bytes JPEG comprimido, ancho_px, alto_px), o None si no es una imagen legible."""
    try:
        from PIL import Image, ImageOps
        im = Image.open(io.BytesIO(datos))
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((MAX_LADO_PX, MAX_LADO_PX))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=CALIDAD_JPEG, optimize=True)
        return buf.getvalue(), im.size[0], im.size[1]
    except Exception:
        return None


def _paginas_pdf(datos: bytes) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(datos)).pages)
    except Exception:
        return 0


def _bajar(snapshot: Dict[str, Any], urls_por_tx: Dict[int, List[str]], traer: Callable[[str], Optional[bytes]],
           describir: Callable[[str], Dict[str, Any]], tipos=("imagen", "pdf")) -> Dict[tuple, Dict[str, Any]]:
    """(i, j) → {descr, datos}. Solo los servibles de `tipos`; en paralelo (también lo usa el HTML offline)."""
    tareas = {}
    for t in snapshot.get("txs", []):
        for j, url in enumerate(urls_por_tx.get(t["id"]) or []):
            d = describir(url)
            tareas[(t["i"], j)] = {"descr": d, "url": url, "datos": None}
    pedir = [(k, v["url"]) for k, v in tareas.items() if v["descr"]["servible"] and v["descr"]["tipo"] in tipos]

    def uno(par):
        k, url = par
        try:
            return k, traer(url)
        except Exception:
            return k, None
    if pedir:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for k, datos in ex.map(uno, pedir):
                tareas[k]["datos"] = datos
    return tareas


def generar(snapshot: Dict[str, Any], urls_por_tx: Dict[int, List[str]], traer: Callable[[str], Optional[bytes]],
            describir: Callable[[str], Dict[str, Any]], expira_en=None) -> bytes:
    from fpdf import FPDF
    from pypdf import PdfReader, PdfWriter

    folio = snapshot.get("folio") or ""
    txs = snapshot.get("txs", [])
    bajados = _bajar(snapshot, urls_por_tx, traer, describir)
    presupuesto = max_bytes() - 300_000          # margen para el texto y la estructura del PDF

    class Pdf(FPDF):
        def footer(self):
            self.set_y(-10)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(90)
            self.cell(0, 5, _t(f"Folio {folio} · Generado con FIN-SYS"), align="C")
            self.set_text_color(0)

    pdf = Pdf(format="A4", unit="mm")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(True, margin=15)
    pdf.set_title(_t(f"{snapshot.get('nombre') or 'Compendio'} - {folio}"))
    pdf.set_creator("FIN-SYS")

    # ── Portada ────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 9, _t(snapshot.get("nombre") or "Compendio"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    empresas = " - ".join(e["nombre"] + (f" (NIT {e['nit']})" if e.get("nit") else "") for e in snapshot.get("empresas", []))
    rango = snapshot.get("rango") or {}
    lineas = [f"Folio: {folio}", empresas and f"Empresa: {empresas}",
              rango.get("desde") and f"Fechas: {_dia(rango['desde'])} a {_dia(rango['hasta'])}",
              f"Transacciones: {snapshot.get('n', len(txs))}",
              snapshot.get("creado_en") and f"Generado: {_dia(snapshot['creado_en'])}",
              expira_en and f"Enlace válido hasta: {_dia(expira_en)}"]
    for ln in filter(None, lineas):
        pdf.cell(0, 6, _t(ln), new_x="LMARGIN", new_y="NEXT")
    if snapshot.get("nota"):
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 10)
        pdf.multi_cell(0, 5, _t(snapshot["nota"]), border="L", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "TOTALES", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for m, tot in (snapshot.get("totales") or {}).items():
        pdf.cell(0, 6, _t(f"{m}: Ingresos {plata(tot['ingresos'], m)} · Gastos {plata(tot['gastos'], m)} · "
                          f"Neto {plata(tot['neto'], m)} ({tot['n']} TX)"), new_x="LMARGIN", new_y="NEXT")
    if len(snapshot.get("totales") or {}) > 1:
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, "Cada moneda se totaliza aparte: nunca se suman entre si.", new_x="LMARGIN", new_y="NEXT")

    # ── Índice (con enlaces a cada transacción) ───────────────────────
    enlaces = [pdf.add_link() for _ in txs]
    pdf.add_page()
    pag_indice = pdf.page_no()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "INDICE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for k, t in enumerate(txs):
        n_sop = len(urls_por_tx.get(t["id"]) or [])
        pdf.set_text_color(0, 0, 160)
        pdf.cell(22, 5.5, _t(_dia(t.get("fecha"))), link=enlaces[k])
        pdf.cell(110, 5.5, _t((t.get("concepto") or "(sin concepto)")[:70]), link=enlaces[k])
        pdf.cell(35, 5.5, _t(plata(t.get("neto"), t.get("moneda") or "COP")), align="R", link=enlaces[k])
        pdf.set_text_color(0)
        pdf.cell(0, 5.5, _t(f"{n_sop} comp." if n_sop else "-"), new_x="LMARGIN", new_y="NEXT")

    # ── Una página por transacción ─────────────────────────────────────
    inicio, fin, anexos = {}, {}, {}
    for k, t in enumerate(txs):
        pdf.add_page()
        inicio[k] = pdf.page_no()
        pdf.set_link(enlaces[k], page=pdf.page_no())
        pdf.set_font("Helvetica", "B", 13)
        pdf.multi_cell(0, 7, _t(f"{_dia(t.get('fecha'))} · {t.get('concepto') or '(sin concepto)'}"),
                       new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        datos = [("Tipo", t.get("tipo")), ("Empresa", t.get("empresa")), ("Tercero", t.get("tercero")),
                 ("Identificación", t.get("identificacion")), ("Categoría", t.get("categoria")),
                 ("Cuenta", t.get("cuenta")),
                 ("Valor bruto", t.get("bruto") and plata(t["bruto"], t.get("moneda") or "COP")),
                 ("IVA", t.get("iva") and plata(t["iva"], t.get("moneda") or "COP")),
                 ("GMF", t.get("gmf") and plata(t["gmf"], t.get("moneda") or "COP")),
                 ("Valor neto", plata(t.get("neto"), t.get("moneda") or "COP")), ("Referencia", f"#{t.get('id')}")]
        for etiqueta, valor in datos:
            if valor:
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(32, 5.5, _t(etiqueta))
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5.5, _t(valor), new_x="LMARGIN", new_y="NEXT")
        if t.get("maps"):
            pdf.set_text_color(0, 0, 160)
            pdf.set_font("Helvetica", "U", 9)
            pdf.cell(0, 6, "Ver ubicación en Google Maps", link=t["maps"], new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0)
            pdf.set_font("Helvetica", "", 9)
        pdf.ln(2)
        sops = [(j, bajados[(t["i"], j)]) for j in range(len(urls_por_tx.get(t["id"]) or []))]
        if not sops:
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 6, "Esta transacción no tiene comprobantes.", new_x="LMARGIN", new_y="NEXT")
        for j, s in sops:
            titulo = f"Comprobante {j + 1}"
            d, datos_b = s["descr"], s["datos"]
            pdf.set_font("Helvetica", "B", 9)
            if not d["servible"]:
                pdf.cell(0, 6, _t(f"{titulo}: no disponible."), new_x="LMARGIN", new_y="NEXT")
            elif d["tipo"] == "audio":
                pdf.cell(0, 6, _t(f"{titulo}: nota de voz (escúchela en el enlace)."), new_x="LMARGIN", new_y="NEXT")
            elif d["tipo"] == "otro":
                pdf.cell(0, 6, _t(f"{titulo}: {d['nombre']} (descárguelo en el enlace)."), new_x="LMARGIN", new_y="NEXT")
            elif not datos_b:
                pdf.cell(0, 6, _t(f"{titulo}: no se pudo leer en este momento."), new_x="LMARGIN", new_y="NEXT")
            elif d["tipo"] == "pdf":
                n = _paginas_pdf(datos_b)
                if not n:
                    pdf.cell(0, 6, _t(f"{titulo}: el PDF está dañado."), new_x="LMARGIN", new_y="NEXT")
                elif len(datos_b) > presupuesto:
                    pdf.cell(0, 6, _t(f"{titulo}: omitido por tamaño (véalo en el enlace)."), new_x="LMARGIN", new_y="NEXT")
                else:
                    presupuesto -= len(datos_b)
                    anexos.setdefault(k, []).append((titulo, datos_b, n))
                    pdf.cell(0, 6, _t(f"{titulo}: PDF de {n} página(s), anexo a continuación."),
                             new_x="LMARGIN", new_y="NEXT")
            else:
                foto = _jpeg(datos_b)
                if not foto:
                    pdf.cell(0, 6, _t(f"{titulo}: la imagen no se pudo leer."), new_x="LMARGIN", new_y="NEXT")
                    continue
                jpg, wpx, hpx = foto
                if len(jpg) > presupuesto:
                    pdf.cell(0, 6, _t(f"{titulo}: omitido por tamaño (véalo en el enlace)."), new_x="LMARGIN", new_y="NEXT")
                    continue
                presupuesto -= len(jpg)
                pdf.cell(0, 6, _t(titulo), new_x="LMARGIN", new_y="NEXT")
                w = pdf.epw
                h = w * hpx / wpx
                if h > pdf.eph * 0.85:
                    h = pdf.eph * 0.85
                    w = h * wpx / hpx
                if pdf.get_y() + h > pdf.h - pdf.b_margin:
                    pdf.add_page()
                pdf.image(io.BytesIO(jpg), x=pdf.l_margin + (pdf.epw - w) / 2, y=pdf.get_y(), w=w, h=h)
                pdf.set_y(pdf.get_y() + h + 3)
        fin[k] = pdf.page_no()

    base = bytes(pdf.output())

    # ── Anexar los PDF y armar los marcadores ──────────────────────────
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(base)))
    for k in sorted(anexos, reverse=True):                    # de atrás hacia adelante: las posiciones no se corren
        pos = fin[k]                                           # 0-based: justo después de la última página de la TX
        for _titulo, datos_b, _n in reversed(anexos[k]):
            writer.merge(position=pos, fileobj=PdfReader(io.BytesIO(datos_b)))

    def corrimiento(pagina_fpdf: int) -> int:                  # páginas anexas antes de esta página
        return sum(n for kk, lst in anexos.items() if fin[kk] < pagina_fpdf for _t_, _d, n in lst)

    writer.add_outline_item("Portada", 0)
    writer.add_outline_item("Indice", pag_indice - 1)
    for k, t in enumerate(txs):
        padre = writer.add_outline_item(_t(f"{_dia(t.get('fecha'))} {t.get('concepto') or ''}")[:80],
                                        inicio[k] - 1 + corrimiento(inicio[k]))
        pos = fin[k] + corrimiento(fin[k])
        for titulo, _d, n in anexos.get(k, []):
            writer.add_outline_item(_t(f"{titulo} (PDF)"), pos, parent=padre)
            pos += n
    writer.add_metadata({"/Title": _t(f"{snapshot.get('nombre') or 'Compendio'} - {folio}"), "/Producer": "FIN-SYS"})
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def nombre_archivo(snapshot: Dict[str, Any], extension: str) -> str:
    base = re.sub(r"[^\w\s.-]", "", f"{snapshot.get('folio') or 'compendio'} {snapshot.get('nombre') or ''}").strip()
    limpio = re.sub(r"\s+", " ", base)[:90]          # (Python 3.11: nada de \ dentro de un f-string)
    return f"{limpio}.{extension}"
