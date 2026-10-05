# -*- coding: utf-8 -*-
"""
routers/accounting_files.py — Organizador contable 📦 EXPORTACIÓN (spec 13.5).
Archivo NUEVO (Zero-Impact). Registrado en server.py ANTES del catch-all SPA.

Ver y generar: owner/admin/contador (require_contador). Borrar: solo admin.
Los archivos viven en Postgres y solo salen por /download y /preview con
sesión: nunca una URL pública (R-135-05).

  POST   /api/analytics/export/preflight        pre-vuelo (= lo que dirá la carátula)
  POST   /api/analytics/export                  arma con el motor 13.4, archiva → {id, folio}
  GET    /api/analytics/export/paquetes         predefinidos + guardados
  POST   /api/analytics/export/paquetes         guardar receta
  DELETE /api/analytics/export/paquetes/{id}    (admin)
  GET    /api/accounting-files                  lista (sin bytes) + vigencia en lote
  GET    /api/accounting-files/resumen          cabecera, conteos y árbol empresa → año → mes
  GET    /api/accounting-files/cierres          matriz paquete × mes (vista 🗓)
  POST   /api/accounting-files/upload           subir documento externo (multipart)
  GET    /api/accounting-files/{id}             ficha + vigencia calculada en el momento
  GET    /api/accounting-files/{id}/download    el archivo exacto (cuenta la descarga)
  GET    /api/accounting-files/{id}/preview     xlsx/csv → filas; PDF/imagen → binario
  PATCH  /api/accounting-files/{id}             nombre, nota, fijado, carpeta, tipo
  POST   /api/accounting-files/{id}/regenerar   folio NUEVO con reemplaza_a
  DELETE /api/accounting-files/{id}             (admin)
  GET/POST /api/accounting-folders · PATCH/DELETE /api/accounting-folders/{id} (DELETE admin)
  GET/POST /api/accounting-doc-types · PATCH/DELETE /api/accounting-doc-types/{id} (DELETE admin)
"""
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel

from routers.auth_guard import require_admin, require_contador

router = APIRouter(tags=["Organizador contable"])


def _drv():
    import accounting_files_driver
    return accounting_files_driver


def _fallo(e: Exception):
    """Traduce los errores del driver a HTTP. Nunca devuelve: siempre lanza."""
    drv = _drv()
    if isinstance(e, HTTPException):
        raise e
    if isinstance(e, drv.Conflicto):
        raise HTTPException(status_code=409, detail=str(e))
    if isinstance(e, drv.NoEncontrado):
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, ValueError):
        raise HTTPException(status_code=400, detail=str(e))
    if drv.es_tabla_faltante(e):
        raise HTTPException(status_code=503, detail="El organizador aún no está instalado: "
                                                    "falta correr scripts/migrate_exports.py.")
    raise HTTPException(status_code=503, detail=f"El organizador falló: {e}")


def _descarga(nombre: str, inline: bool = False) -> str:
    ascii_ = "".join(ch if 32 <= ord(ch) < 127 and ch not in '"\\' else "_" for ch in nombre) or "archivo"
    modo = "inline" if inline else "attachment"
    return f"{modo}; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nombre)}"


# ── Modelos ──────────────────────────────────────────────────

class ExportRequest(BaseModel):
    receta: Dict[str, Any]
    paquete: Optional[str] = None
    folder_id: Optional[int] = None
    tipo_documental_id: Optional[int] = None


class PreflightRequest(BaseModel):
    receta: Dict[str, Any]
    paquete: Optional[str] = None


class RegenerarRequest(BaseModel):
    desde: Optional[str] = None
    hasta: Optional[str] = None


class PaqueteRequest(BaseModel):
    nombre: str
    receta: Dict[str, Any]


# ── Nueva exportación ────────────────────────────────────────

@router.post("/api/analytics/export/preflight")
def preflight(req: PreflightRequest, user: dict = Depends(require_contador)):
    try:
        return _drv().prevuelo(req.receta, req.paquete, usuario=user)
    except Exception as e:
        _fallo(e)


@router.post("/api/analytics/export")
def exportar(req: ExportRequest, user: dict = Depends(require_contador)):
    try:
        return _drv().generar(req.receta, user, paquete=req.paquete, folder_id=req.folder_id,
                              tipo_documental_id=req.tipo_documental_id)
    except Exception as e:
        _fallo(e)


@router.get("/api/analytics/export/paquetes")
def paquetes(_user: dict = Depends(require_contador)):
    try:
        return _drv().listar_paquetes()
    except Exception as e:
        _fallo(e)


@router.post("/api/analytics/export/paquetes")
def guardar_paquete(req: PaqueteRequest, user: dict = Depends(require_contador)):
    try:
        return _drv().guardar_paquete(req.nombre, req.receta, user)
    except Exception as e:
        _fallo(e)


@router.delete("/api/analytics/export/paquetes/{paquete_id}")
def borrar_paquete(paquete_id: int, _admin: dict = Depends(require_admin)):
    try:
        return _drv().eliminar_paquete(paquete_id)
    except Exception as e:
        _fallo(e)


# ── Organizador: rutas fijas ANTES de /{file_id} ─────────────

@router.get("/api/accounting-files")
def listar(folder_id: Optional[int] = None, portfolio_id: Optional[int] = None,
           anio: Optional[int] = None, mes: Optional[int] = None, tipo: Optional[int] = None,
           q: Optional[str] = None, fijado: bool = False, cambiaron: bool = False,
           por_vencer: bool = False, origen: Optional[str] = None,
           limit: int = 50, offset: int = 0, _user: dict = Depends(require_contador)):
    try:
        return _drv().listar({"folder_id": folder_id, "portfolio_id": portfolio_id, "anio": anio,
                              "mes": mes, "tipo": tipo, "q": q, "fijado": fijado,
                              "cambiaron": cambiaron, "por_vencer": por_vencer, "origen": origen,
                              "limit": limit, "offset": offset})
    except Exception as e:
        _fallo(e)


@router.get("/api/accounting-files/resumen")
def resumen(_user: dict = Depends(require_contador)):
    try:
        return _drv().resumen()
    except Exception as e:
        _fallo(e)


@router.get("/api/accounting-files/cierres")
def cierres(anio: int, portfolio_id: Optional[int] = None, _user: dict = Depends(require_contador)):
    try:
        return _drv().cierres(portfolio_id or None, anio)
    except Exception as e:
        _fallo(e)


@router.post("/api/accounting-files/upload")
def subir(archivo: UploadFile = File(...), nombre: Optional[str] = Form(None),
          tipo_documental_id: Optional[int] = Form(None), folder_id: Optional[int] = Form(None),
          portfolio_id: Optional[int] = Form(None), anio: Optional[int] = Form(None),
          mes: Optional[int] = Form(None), nota: Optional[str] = Form(None),
          user: dict = Depends(require_contador)):
    drv = _drv()
    contenido = archivo.file.read(drv.MAX_BYTES + 1)
    if len(contenido) > drv.MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"El archivo supera el tope de {drv.MAX_MB:g} MB.")
    try:
        return drv.subir(contenido, archivo.filename or "documento", {
            "nombre": nombre, "tipo_documental_id": tipo_documental_id, "folder_id": folder_id,
            "portfolio_id": portfolio_id, "anio": anio, "mes": mes, "nota": nota}, usuario=user)
    except Exception as e:
        _fallo(e)


# ── Organizador: un archivo ──────────────────────────────────

@router.get("/api/accounting-files/{file_id}")
def ficha(file_id: int, _user: dict = Depends(require_contador)):
    try:
        return _drv().ficha(file_id)
    except Exception as e:
        _fallo(e)


@router.get("/api/accounting-files/{file_id}/download")
def descargar(file_id: int, _user: dict = Depends(require_contador)):
    try:
        a = _drv().descargar(file_id)
    except Exception as e:
        _fallo(e)
    return Response(content=a["contenido"], media_type=a["mime_type"], headers={
        "Content-Disposition": _descarga(a["nombre_archivo"]),
        "X-FinSys-SHA256": a["sha256"],
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    })


@router.get("/api/accounting-files/{file_id}/preview")
def vista_previa(file_id: int, hoja: Optional[str] = None, limite: int = 50,
                 _user: dict = Depends(require_contador)):
    try:
        v = _drv().vista_previa(file_id, hoja, limite)
    except Exception as e:
        _fallo(e)
    if v.get("tipo") != "binario":
        return v
    return Response(content=v["contenido"], media_type=v["mime_type"], headers={
        "Content-Disposition": _descarga(v["nombre_archivo"], inline=True),
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox",
    })


@router.patch("/api/accounting-files/{file_id}")
def actualizar(file_id: int, cambios: Dict[str, Any] = Body(...), _user: dict = Depends(require_contador)):
    try:
        return _drv().actualizar(file_id, cambios)
    except Exception as e:
        _fallo(e)


@router.post("/api/accounting-files/{file_id}/regenerar")
def regenerar(file_id: int, req: Optional[RegenerarRequest] = None, user: dict = Depends(require_contador)):
    try:
        req = req or RegenerarRequest()
        return _drv().regenerar(file_id, user, req.desde, req.hasta)
    except Exception as e:
        _fallo(e)


@router.delete("/api/accounting-files/{file_id}")
def eliminar(file_id: int, _admin: dict = Depends(require_admin)):
    try:
        return _drv().eliminar(file_id)
    except Exception as e:
        _fallo(e)


# ── Carpetas propias ─────────────────────────────────────────

@router.get("/api/accounting-folders")
def carpetas(_user: dict = Depends(require_contador)):
    try:
        return _drv().listar_carpetas()
    except Exception as e:
        _fallo(e)


@router.post("/api/accounting-folders")
def crear_carpeta(datos: Dict[str, Any] = Body(...), user: dict = Depends(require_contador)):
    try:
        return _drv().crear_carpeta(datos, user)
    except Exception as e:
        _fallo(e)


@router.patch("/api/accounting-folders/{folder_id}")
def actualizar_carpeta(folder_id: int, datos: Dict[str, Any] = Body(...),
                       _user: dict = Depends(require_contador)):
    try:
        return _drv().actualizar_carpeta(folder_id, datos)
    except Exception as e:
        _fallo(e)


@router.delete("/api/accounting-folders/{folder_id}")
def eliminar_carpeta(folder_id: int, _admin: dict = Depends(require_admin)):
    try:
        return _drv().eliminar_carpeta(folder_id)
    except Exception as e:
        _fallo(e)


# ── Tipos documentales ───────────────────────────────────────

@router.get("/api/accounting-doc-types")
def tipos(_user: dict = Depends(require_contador)):
    try:
        return _drv().listar_tipos()
    except Exception as e:
        _fallo(e)


@router.post("/api/accounting-doc-types")
def crear_tipo(datos: Dict[str, Any] = Body(...), user: dict = Depends(require_contador)):
    try:
        return _drv().crear_tipo(datos, user)
    except Exception as e:
        _fallo(e)


@router.patch("/api/accounting-doc-types/{tipo_id}")
def actualizar_tipo(tipo_id: int, datos: Dict[str, Any] = Body(...), _user: dict = Depends(require_contador)):
    try:
        return _drv().actualizar_tipo(tipo_id, datos)
    except Exception as e:
        _fallo(e)


@router.delete("/api/accounting-doc-types/{tipo_id}")
def eliminar_tipo(tipo_id: int, _admin: dict = Depends(require_admin)):
    try:
        return _drv().eliminar_tipo(tipo_id)
    except Exception as e:
        _fallo(e)
