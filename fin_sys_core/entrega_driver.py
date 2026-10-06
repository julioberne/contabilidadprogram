# -*- coding: utf-8 -*-
"""
entrega_driver.py — 📦 Compendio de entrega en ZIP (spec 13.5 §11, pedido de Andrés 06-oct).
Archivo NUEVO (Zero-Impact). Lo usa routers/accounting_files.py.

Varios archivos del organizador (libros, relaciones, documentos subidos) → UN ZIP con:
  00 - INDICE.csv   una fila por archivo: folio, origen, tipo, empresa, período, tamaño,
                    SHA-256, quién y cuándo, y su vigencia al empaquetar (✅ / ⚠ cambió)
  LEEME.txt         folio del compendio, nombre, nota, fecha y cómo verificar la integridad
  NN - folio - nombre.ext   los archivos tal cual (byte a byte; se verifica su SHA-256)
El ZIP se archiva como un GENERADO más (folio EXP-AAAA-NNNN de la misma secuencia, paquete
'entrega'). No se regenera: para otra entrega se arma otro con los archivos de hoy.
"""
import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fin_sys_core.accounting_files_driver import (
    MAX_BYTES, MAX_MB, ORIGEN_GENERADO, TIPO_LIBRE, NoEncontrado, _conexion, _entero, _filas, _id_tipo, _iso,
    _quien, _texto, _validar_destino, _vigencias, purgar, siguiente_folio,
)

PAQUETE_ENTREGA = "entrega"
MIME_ZIP = "application/zip"
MAX_ARCHIVOS = 50

_COLS = ("id", "origen", "folio", "nombre", "nombre_archivo", "mime_type", "archivo", "sha256", "tamano_bytes",
         "portfolio_id", "empresa", "periodo_desde", "periodo_hasta", "tipo", "creado_por", "creado_en",
         "receta", "huella_datos", "paquete")
SQL_LEER = """
    SELECT f.id, f.origen, f.folio, f.nombre, f.nombre_archivo, f.mime_type, f.archivo, f.sha256, f.tamano_bytes,
           f.portfolio_id, p.name, f.periodo_desde, f.periodo_hasta, t.nombre, f.creado_por, f.creado_en,
           f.receta, f.huella_datos, f.paquete
      FROM accounting_files f
      LEFT JOIN portfolios p ON p.id = f.portfolio_id
      LEFT JOIN accounting_doc_types t ON t.id = f.tipo_documental_id
     WHERE f.id = ANY(%s)
"""


def _ids(v) -> List[int]:
    if not isinstance(v, (list, tuple)) or not v:
        raise ValueError("Elige al menos un archivo para la entrega.")
    out: List[int] = []
    for x in v:
        n = _entero(x, "ids", opcional=False)
        if n not in out:
            out.append(n)
    if len(out) > MAX_ARCHIVOS:
        raise ValueError(f"Máximo {MAX_ARCHIVOS} archivos por entrega ({len(out)} elegidos).")
    return out


def _seguro(s: str, maximo: int = 90) -> str:
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", str(s or "")).strip(" .")[:maximo] or "archivo"


def _extension(f: Dict[str, Any]) -> str:
    n = str(f.get("nombre_archivo") or "")
    return ("." + n.rsplit(".", 1)[-1].lower()) if "." in n else ""


def _dia(v) -> str:
    if isinstance(v, datetime):
        v = v.date()
    return v.strftime("%d/%m/%Y") if isinstance(v, date) else ""


def armar_zip(filas: List[Dict[str, Any]], folio: str, nombre: str, nota: Optional[str],
              vigencias: Dict[int, Dict[str, Any]], ahora: datetime) -> Dict[str, Any]:
    """Pura: → {contenido, advertencias, indice}. Los archivos van byte a byte y se verifica su huella."""
    buf = io.BytesIO()
    indice, advertencias = [], []
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for k, f in enumerate(filas, start=1):
            datos = bytes(f["archivo"] or b"")
            sha = hashlib.sha256(datos).hexdigest()
            integro = not f.get("sha256") or sha == f["sha256"]
            if not integro:
                advertencias.append(f"{f.get('folio') or f['nombre']}: su huella no coincide con la registrada.")
            ruta = f"{k:02d} - {_seguro(f.get('folio') or 'SUBIDO', 20)} - {_seguro(f['nombre'])}{_extension(f)}"
            z.writestr(ruta, datos)
            v = vigencias.get(f["id"], {}).get("estado")
            vig = {"VIGENTE": "Vigente", "CAMBIO": "Los libros cambiaron después"}.get(v, "No aplica" if
                                                                                        f["origen"] != ORIGEN_GENERADO else "Sin huella")
            if v == "CAMBIO":
                advertencias.append(f"{f.get('folio')}: los libros cambiaron después de exportarlo (conviene regenerarlo).")
            periodo = (f"{_dia(f.get('periodo_desde'))} a {_dia(f.get('periodo_hasta'))}"
                       if f.get("periodo_hasta") else "")
            indice.append({"N.º": k, "Archivo en el ZIP": ruta, "Folio": f.get("folio") or "",
                           "Origen": "Generado por FIN-SYS" if f["origen"] == ORIGEN_GENERADO else "Subido",
                           "Tipo": f.get("tipo") or "", "Empresa": f.get("empresa") or "Consolidado",
                           "Período": periodo, "Tamaño (bytes)": len(datos), "SHA-256": sha,
                           "Integridad": "OK" if integro else "NO COINCIDE",
                           "Vigencia al empaquetar": vig, "Creado por": f.get("creado_por") or "",
                           "Creado el": _dia(f.get("creado_en"))})
        csv_buf = io.StringIO()
        w = csv.DictWriter(csv_buf, fieldnames=list(indice[0].keys()), delimiter=";")   # ; = Excel en español
        w.writeheader()
        w.writerows(indice)
        z.writestr("00 - INDICE.csv", "﻿" + csv_buf.getvalue())                   # BOM: tildes bien en Excel
        leeme = [f"Compendio de entrega {folio}", nombre, f"Armado el {_dia(ahora)} con FIN-SYS.",
                 f"{len(filas)} archivo(s). El índice (00 - INDICE.csv) trae folio, período y SHA-256 de cada uno.",
                 "Para verificar que un archivo no cambió, calcule su SHA-256 y compárelo con el del índice."]
        if nota:
            leeme += ["", "Nota:", nota]
        if advertencias:
            leeme += ["", "Advertencias:"] + [f"- {a}" for a in advertencias]
        z.writestr("LEEME.txt", "\r\n".join(leeme))
    return {"contenido": buf.getvalue(), "advertencias": advertencias, "indice": indice}


SQL_INSERT = """
    INSERT INTO accounting_files
        (origen, folio, nombre, nombre_archivo, tipo_documental_id, paquete, receta,
         portfolio_id, periodo_desde, periodo_hasta, folder_id, archivo, mime_type,
         tamano_bytes, sha256, hojas, sello, huella_datos, creado_por, reemplaza_a)
    VALUES ('GENERADO', %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s::jsonb, NULL, %s, NULL)
    RETURNING id, creado_en
"""


def crear(datos: Dict[str, Any], usuario: Optional[Dict[str, Any]] = None, conn=None) -> Dict[str, Any]:
    ids = _ids(datos.get("ids"))
    nota = _texto(datos.get("nota"), "nota", 1000)
    nombre_in = _texto(datos.get("nombre"), "nombre", 120)
    folder_id = _entero(datos.get("folder_id"), "folder_id")
    with _conexion(conn) as c:
        cur = c.cursor()
        _validar_destino(cur, folder_id, None)
        cur.execute(SQL_LEER, (ids,))
        por_id = {f["id"]: f for f in _filas(cur, _COLS)}
        faltan = [i for i in ids if i not in por_id]
        if faltan:
            raise NoEncontrado("No existen: " + ", ".join(f"#{i}" for i in faltan) + ".")
        filas = [por_id[i] for i in ids]
        if any(f.get("paquete") == PAQUETE_ENTREGA for f in filas):
            raise ValueError("Un compendio de entrega no puede ir dentro de otro: elige los archivos sueltos.")
        vig = _vigencias(cur, filas)
        ahora = datetime.now()
        folio = siguiente_folio(cur, ahora.year)
        nombre = nombre_in or f"Entrega de {len(filas)} archivo(s) — {ahora.date().isoformat()}"
        z = armar_zip(filas, folio, nombre, nota, vig, ahora)
        contenido = z["contenido"]
        if len(contenido) > MAX_BYTES:
            raise ValueError(f"El ZIP pesa {len(contenido) / 1048576:.1f} MB y el tope es {MAX_MB:g} MB: "
                             "arma dos entregas más pequeñas.")
        pids = sorted({f["portfolio_id"] for f in filas if f.get("portfolio_id") is not None})
        unico = pids[0] if len(pids) == 1 and all(f.get("portfolio_id") for f in filas) else None
        desdes = [f["periodo_desde"] for f in filas if f.get("periodo_desde")]
        hastas = [f["periodo_hasta"] for f in filas if f.get("periodo_hasta")]
        sha = hashlib.sha256(contenido).hexdigest()
        nombre_archivo = f"{folio}_{_seguro(nombre, 80)}.zip"
        sello = {"modo": PAQUETE_ENTREGA, "n_archivos": len(filas), "advertencias": z["advertencias"],
                 "archivos": [{"folio": f.get("folio"), "nombre": f["nombre"], "sha256": r["SHA-256"]}
                              for f, r in zip(filas, z["indice"])]}
        purgados = purgar(cur)
        cur.execute(SQL_INSERT, (folio, nombre, nombre_archivo, _id_tipo(cur, TIPO_LIBRE), PAQUETE_ENTREGA,
                                 json.dumps({"modo": PAQUETE_ENTREGA, "ids": ids, "nota": nota}, ensure_ascii=False),
                                 unico, min(desdes) if desdes else None, max(hastas) if hastas else None, folder_id,
                                 contenido, MIME_ZIP, len(contenido), sha, [],
                                 json.dumps(sello, ensure_ascii=False, default=str), _quien(usuario)))
        nuevo_id, creado_en = cur.fetchone()
        cur.close()
    return {"id": int(nuevo_id), "folio": folio, "nombre": nombre, "nombre_archivo": nombre_archivo,
            "paquete": PAQUETE_ENTREGA, "n": len(filas), "tamano_bytes": len(contenido), "sha256": sha,
            "advertencias": z["advertencias"], "creado_en": _iso(creado_en), "purgados": purgados}
