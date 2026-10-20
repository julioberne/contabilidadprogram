# -*- coding: utf-8 -*-
"""diario_csv.py — CSV grande del Libro Diario, armado por el worker (H5.3).

Hasta 2.000 filas el navegador arma el CSV al instante (como siempre). Más
allá, el pedido va a la cola: el worker recorre lo filtrado de a páginas con
el CURSOR del Diario (cada página cuesta lo mismo), arma el CSV con las MISMAS
columnas que aCsv (frontend/.../diario/diarioFiltros.js) y lo deja en el
organizador con folio propio. Sin el tope de 5.000 del navegador; el único tope
es el del organizador (ANALYTICS_EXPORT_MAX_MB): si el CSV no cabe, va
comprimido en un ZIP, y si tampoco cabe, se pide acotar los filtros.

Orden: el cursor existe solo por fecha; con otro orden pedido, el CSV grande
sale por fecha descendente y el resultado lo dice (`orden_usado`).
"""
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime
from typing import Any, Dict, Iterable, Iterator, Optional

PAGINA = 1000
# Si el CSV sin comprimir pasa de esto, ni comprimido cabría en el organizador.
FACTOR_COMPRESION = 8

COLUMNAS = [
    ("id", "ID"), ("transaction_date", "Fecha"), ("type", "Tipo"), ("concept", "Concepto"),
    ("net_value", "Valor neto"), ("amount", "Valor bruto"), ("transaction_currency", "Moneda"),
    ("category", "Cuenta COA"), ("third_party_name", "Tercero"), ("identification_number", "NIT/CC"),
    ("account_name", "Cuenta"), ("dest_account_name", "Cuenta destino"), ("tags", "Etiquetas"),
    ("note", "Nota"), ("portfolio_name", "Empresa"),
]
_NUMERICAS = ("net_value", "amount")
_RE_ESCAPAR = re.compile(r'[;"\n]')


def _celda(v: Any) -> str:
    """Como `esc` de aCsv: listas con " | ", comillas si hay ; " o salto de línea."""
    s = " | ".join(str(x) for x in v) if isinstance(v, (list, tuple)) else ("" if v is None else str(v))
    return f'"{s.replace(chr(34), chr(34) * 2)}"' if _RE_ESCAPAR.search(s) else s


def _numero(v: Any) -> str:
    """Como `num` de aCsv: coma decimal; 50000.0 → "50000" (igual que String() en JS)."""
    if v is None or v == "":
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).replace(".", ",", 1)


def fila_csv(t: Dict[str, Any]) -> str:
    return ";".join(_numero(t.get(k)) if k in _NUMERICAS else _celda(t.get(k)) for k, _ in COLUMNAS)


def armar_csv(filas: Iterable[Dict[str, Any]], tope_bytes: Optional[int] = None) -> Dict[str, Any]:
    """→ {"contenido": bytes UTF-8 con BOM, "n"}. Corta con ValueError si pasa de tope_bytes."""
    partes = ["﻿" + ";".join(etq for _, etq in COLUMNAS)]
    peso, n = len(partes[0]), 0
    for t in filas:
        linea = fila_csv(t)
        partes.append(linea)
        n += 1
        peso += len(linea) + 1
        if tope_bytes and peso > tope_bytes:
            raise ValueError("El CSV es demasiado grande para el organizador: acota los filtros "
                             "(fechas, empresa o tipo) y vuelve a exportar.")
    return {"contenido": "\n".join(partes).encode("utf-8"), "n": n}


def orden_para_csv(orden: str) -> str:
    from fin_sys_core.diario_query import ORDENES_CURSOR
    return orden if orden in ORDENES_CURSOR else "fecha_desc"


def recorrer(filtros: Dict[str, Any], orden: str, buscar=None) -> Iterator[Dict[str, Any]]:
    """Todas las filas filtradas, de a PAGINA, siguiendo el cursor del Diario."""
    if buscar is None:
        from fin_sys_core.diario_query import buscar_movimientos as buscar
    despues = None
    while True:
        r = buscar(filtros, orden=orden, limit=PAGINA, totales=False, despues=despues)
        yield from r["transactions"]
        sig = r.get("siguiente")
        if not sig:
            return
        despues = (sig["fecha"], sig["id"])


def _nombre_seguro(s: str, maximo: int = 80) -> str:
    return re.sub(r"[^\w\-. ]+", "", s, flags=re.UNICODE).strip().replace(" ", "-")[:maximo] or "diario"


def generar(filtros: Dict[str, Any], orden: str, usuario: Optional[Dict[str, Any]] = None, *,
            folder_id: Optional[int] = None, buscar=None, guardar=None) -> Dict[str, Any]:
    """Arma el CSV de lo filtrado y lo guarda en el organizador. → el archivo creado."""
    from fin_sys_core.accounting_files_driver import MAX_BYTES
    orden_usado = orden_para_csv(orden)
    csv = armar_csv(recorrer(filtros, orden_usado, buscar), tope_bytes=MAX_BYTES * FACTOR_COMPRESION)
    empresas = ", ".join(filtros.get("empresas") or []) or "todas las empresas"
    hoy = datetime.now().date().isoformat()
    nombre = f"Libro Diario — {empresas} — {csv['n']} movimientos ({hoy})"[:120]
    base = f"libro-diario-{_nombre_seguro(empresas)}-{hoy}"
    contenido, extension, mime = csv["contenido"], "csv", "text/csv"
    if len(contenido) > MAX_BYTES:            # no cabe: va comprimido
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{base}.csv", contenido)
        contenido, extension, mime = buf.getvalue(), "zip", "application/zip"
        if len(contenido) > MAX_BYTES:
            raise ValueError("Ni comprimido cabe en el organizador: acota los filtros y vuelve a exportar.")
    archivo = (guardar or _guardar)(contenido, nombre, f"{base}.{extension}", mime, usuario, folder_id, {
        "modo": "diario_csv", "filtros": filtros, "orden": orden, "orden_usado": orden_usado,
        "n": csv["n"], "desde": filtros.get("desde"), "hasta": filtros.get("hasta")})
    return {**archivo, "n": csv["n"], "orden_usado": orden_usado, "comprimido": extension == "zip"}


def _guardar(contenido: bytes, nombre: str, nombre_archivo: str, mime: str,
             usuario: Optional[Dict[str, Any]], folder_id: Optional[int], receta: Dict[str, Any]) -> Dict[str, Any]:
    """Archivo GENERADO en el organizador (misma inserción que el 📦 de entrega)."""
    from fin_sys_core.accounting_files_driver import (
        TIPO_LIBRE, _conexion, _entero, _id_tipo, _iso, _quien, _validar_destino, purgar, siguiente_folio,
    )
    from fin_sys_core.entrega_driver import SQL_INSERT
    folder_id = _entero(folder_id, "folder_id")
    sha = hashlib.sha256(contenido).hexdigest()
    with _conexion(None) as c:
        cur = c.cursor()
        _validar_destino(cur, folder_id, None)
        folio = siguiente_folio(cur, datetime.now().year)
        nombre_archivo = f"{folio}_{nombre_archivo}"[:200]
        purgados = purgar(cur)
        sello = {"modo": "diario_csv", "n": receta.get("n"), "orden_usado": receta.get("orden_usado")}
        cur.execute(SQL_INSERT, (folio, nombre, nombre_archivo, _id_tipo(cur, TIPO_LIBRE), "diario_csv",
                                 json.dumps(receta, ensure_ascii=False, default=str), None,
                                 receta.get("desde") or None, receta.get("hasta") or None, folder_id,
                                 contenido, mime, len(contenido), sha, [],
                                 json.dumps(sello, ensure_ascii=False, default=str), _quien(usuario)))
        nuevo_id, creado_en = cur.fetchone()
        cur.close()
    return {"id": int(nuevo_id), "folio": folio, "nombre": nombre, "nombre_archivo": nombre_archivo,
            "tamano_bytes": len(contenido), "sha256": sha, "creado_en": _iso(creado_en), "purgados": purgados}
