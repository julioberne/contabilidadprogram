# -*- coding: utf-8 -*-
"""
routers/compendios.py — 🤝 Compendio para el cliente (spec 13.6).
Archivo NUEVO (Zero-Impact). Registrado en server.py ANTES del catch-all SPA.

Privado (owner/admin/contador, como el organizador 13.5):
  POST  /api/compendios/preflight     revisión sin crear nada
  POST  /api/compendios               foto + folio + link /c/<código>
  GET   /api/compendios               carpeta 🔗 Compendios (estado, visitas, link si está vigente)
  PATCH /api/compendios/{id}          {ampliar_dias} o {revocar: true}
  GET   /api/compendios/{id}/seguimiento   📈 KPIs, qué revisó por TX y línea de tiempo (13.6-c)
  GET   /api/compendios/actividad          lo último que hicieron los clientes (todos los compendios)

Público (SIN sesión: el código del link es la llave):
  GET   /c/{token}                                    la página del cliente (anota "abrió")
  GET   /api/publico/compendio/{token}/soporte/{i}/{j} comprobante leído por el servidor (anota "vio")
  POST  /api/publico/compendio/{token}/evento          sendBeacon del visor: abrió la TX i
La 1.ª apertura de cada compendio avisa por Telegram en segundo plano (compendio_aviso).
Vencido, revocado o inexistente → la misma página 404 "ya no disponible".
Cabeceras: noindex, no-referrer, no-store, nosniff y CSP con nonce (§4.7).
"""
import os
import time
from collections import deque
from typing import Deque, Dict, List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from routers.auth_guard import require_contador

router = APIRouter(tags=["Compendio para el cliente"])


def _drv():
    import compendio_driver
    return compendio_driver


def _visor():
    import compendio_visor
    return compendio_visor


def _fallo(e: Exception):
    """Traduce los errores del driver a HTTP. Nunca devuelve: siempre lanza."""
    drv = _drv()
    if isinstance(e, HTTPException):
        raise e
    if isinstance(e, drv.Conflicto):
        raise HTTPException(status_code=409, detail=str(e))
    if isinstance(e, (drv.NoEncontrado, drv.NoDisponible)):
        raise HTTPException(status_code=404, detail=str(e) or "No encontrado.")
    if isinstance(e, ValueError):
        raise HTTPException(status_code=400, detail=str(e))
    if drv.es_tabla_faltante(e):
        raise HTTPException(status_code=503, detail="Falta una tabla de los compendios (o la del 📈 seguimiento): "
                                                    "corre scripts/migrate_compendios.py.")
    raise HTTPException(status_code=503, detail=f"El compendio falló: {e}")


# ── Modelos ──────────────────────────────────────────────────

class CompendioIn(BaseModel):
    tx_ids: List[int]
    nombre: Optional[str] = None
    nota: Optional[str] = None
    vigencia_dias: int = 15
    identificacion: bool = True
    ubicaciones: bool = True


class CompendioCambio(BaseModel):
    ampliar_dias: Optional[int] = None
    revocar: bool = False


# ── Privado ──────────────────────────────────────────────────

@router.post("/api/compendios/preflight")
def prevuelo(body: CompendioIn, _u: dict = Depends(require_contador)):
    try:
        return _drv().prevuelo(body.model_dump())
    except Exception as e:
        _fallo(e)


@router.post("/api/compendios", status_code=201)
def crear(body: CompendioIn, user: dict = Depends(require_contador)):
    try:
        return _drv().crear(body.model_dump(), user)
    except Exception as e:
        _fallo(e)


@router.get("/api/compendios")
def listar(_u: dict = Depends(require_contador)):
    try:
        return _drv().listar()
    except Exception as e:
        _fallo(e)


@router.patch("/api/compendios/{cid}")
def actualizar(cid: int, body: CompendioCambio = Body(...), user: dict = Depends(require_contador)):
    try:
        return _drv().actualizar(cid, body.model_dump(), user)
    except Exception as e:
        _fallo(e)


@router.get("/api/compendios/actividad")
def actividad(limite: int = 10, _u: dict = Depends(require_contador)):
    try:
        return _drv().actividad(limite)
    except Exception as e:
        if _drv().es_tabla_faltante(e):
            return []            # la tabla de eventos llega con la migración: sin ella, sin actividad
        _fallo(e)


@router.get("/api/compendios/{cid}/seguimiento")
def seguimiento(cid: int, _u: dict = Depends(require_contador)):
    try:
        return _drv().seguimiento(cid)
    except Exception as e:
        _fallo(e)


# ── Público: límite de ritmo por IP (en memoria, sin guardar la IP) ──

_VENTANA = 60.0
_RITMO: Dict[str, Deque[float]] = {}


def _limite() -> int:
    try:
        return max(10, int(os.getenv("COMPENDIO_RITMO_POR_MIN", "120")))
    except ValueError:
        return 120


def _ip(request: Request) -> str:
    reenviada = request.headers.get("x-forwarded-for", "")
    return (reenviada.split(",")[0].strip() if reenviada else "") or (request.client.host if request.client else "?")


def _ritmo_ok(request: Request) -> bool:
    ahora = time.monotonic()
    marcas = _RITMO.setdefault(_ip(request), deque())
    while marcas and ahora - marcas[0] > _VENTANA:
        marcas.popleft()
    if len(marcas) >= _limite():
        return False
    marcas.append(ahora)
    if len(_RITMO) > 5000:                      # que el mapa no crezca sin fin
        for k in [k for k, v in _RITMO.items() if not v or ahora - v[-1] > _VENTANA]:
            _RITMO.pop(k, None)
    return True


BASE = {"X-Robots-Tag": "noindex, nofollow", "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff"}
CSP_SIMPLE = "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'"


def _no_disponible(codigo: int = 404) -> HTMLResponse:
    return HTMLResponse(_visor().PAGINA_NO_DISPONIBLE, status_code=codigo,
                        headers={**BASE, "Cache-Control": "no-store", "Content-Security-Policy": CSP_SIMPLE})


def _demasiadas() -> HTMLResponse:
    return HTMLResponse("Demasiadas solicitudes. Intenta en un minuto.", status_code=429,
                        headers={**BASE, "Retry-After": "60", "Cache-Control": "no-store",
                                 "Content-Security-Policy": CSP_SIMPLE})


def _anotar_seguro(cid, tipo: str, request: Request, i: Optional[int] = None, j: Optional[int] = None) -> dict:
    """El seguimiento nunca tumba lo que ve el cliente: si falla (p. ej. falta la migración), se sigue."""
    if cid is None:
        return {}
    try:
        return _drv().anotar(cid, tipo, _ip(request), request.headers.get("user-agent", ""), i, j)
    except Exception as e:
        print(f"⚠️ [compendios] no se anotó '{tipo}' del compendio {cid}: {e}")
        return {}


def _tarea_aviso(r: dict):
    """1.ª apertura → aviso por Telegram DESPUÉS de responder (el cliente no espera)."""
    if not r.get("primera"):
        return None
    import compendio_aviso
    if not compendio_aviso.activo():
        return None
    return BackgroundTask(compendio_aviso.avisar_primera_apertura,
                          r.get("folio") or "", r.get("nombre") or "", r.get("dispositivo") or "")


@router.get("/c/{token}", include_in_schema=False)
def ver(token: str, request: Request):
    if not _ritmo_ok(request):
        return _demasiadas()
    drv = _drv()
    try:
        datos = drv.abrir(token)
    except drv.NoDisponible:
        return _no_disponible()
    except Exception as e:
        if drv.es_tabla_faltante(e):
            return _no_disponible()
        return HTMLResponse("El compendio no se pudo abrir. Intenta más tarde.", status_code=503,
                            headers={**BASE, "Cache-Control": "no-store", "Content-Security-Policy": CSP_SIMPLE})
    cid = datos.pop("_id", None)
    # ?previa=1: Andrés lo abre desde ⇩ Exportación (↗ ABRIR) → no es el cliente: ni se anota ni avisa.
    previa = request.query_params.get("previa") == "1"
    anotado = {} if previa else _anotar_seguro(cid, "abrio", request)
    datos["base"] = f"/api/publico/compendio/{token}"
    datos["previa"] = previa
    html, nonce = _visor().pagina(datos)
    return HTMLResponse(html, headers={**BASE, "Cache-Control": "no-store",
                                       "Content-Security-Policy": _visor().csp(nonce)},
                        background=_tarea_aviso(anotado))


class EventoIn(BaseModel):
    tipo: str
    i: Optional[int] = None


@router.post("/api/publico/compendio/{token}/evento", include_in_schema=False)
def evento(token: str, request: Request, body: EventoIn = Body(...)):
    if not _ritmo_ok(request):
        return Response(status_code=429, headers={**BASE, "Retry-After": "60"})
    drv = _drv()
    try:
        drv.evento_publico(token, body.tipo, body.i, _ip(request), request.headers.get("user-agent", ""))
    except drv.NoDisponible:
        return Response(status_code=404, headers=BASE)
    except Exception as e:
        print(f"⚠️ [compendios] evento no anotado: {e}")
    return Response(status_code=204, headers={**BASE, "Cache-Control": "no-store"})


def _traer(url: str, maximo: int) -> Optional[bytes]:
    """Descarga del bucket propio, sin seguir redirecciones y con tope de tamaño."""
    import httpx
    with httpx.Client(timeout=20.0, follow_redirects=False) as cli:
        with cli.stream("GET", url) as r:
            if r.status_code != 200:
                return None
            partes, total = [], 0
            for trozo in r.iter_bytes():
                total += len(trozo)
                if total > maximo:
                    return None
                partes.append(trozo)
    return b"".join(partes)


@router.get("/api/publico/compendio/{token}/soporte/{i}/{j}", include_in_schema=False)
def ver_soporte(token: str, i: int, j: int, request: Request):
    if not _ritmo_ok(request):
        return _demasiadas()
    drv = _drv()
    try:
        s = drv.soporte(token, i, j)
        contenido = _traer(s["url"], drv.max_bytes_soporte())
    except drv.NoDisponible:
        return _no_disponible()
    except Exception:
        return _no_disponible(502)
    if contenido is None:
        return _no_disponible(502)
    cid = s.pop("_id", None)
    if request.query_params.get("previa") != "1":
        _anotar_seguro(cid, "comprobante", request, i, j)
    modo ="attachment" if s["tipo"] == drv.TIPO_OTRO else "inline"
    ascii_ = "".join(ch if 32 <= ord(ch) < 127 and ch not in '"\\' else "_" for ch in s["nombre"]) or "comprobante"
    cabeceras = {**BASE, "Cache-Control": "private, max-age=300",
                 "Content-Disposition": f"{modo}; filename=\"{ascii_}\"; filename*=UTF-8''{quote(s['nombre'])}",
                 # El PDF se incrusta en la propia página: solo ella puede enmarcarlo.
                 "Content-Security-Policy": ("frame-ancestors 'self'" if s["tipo"] == drv.TIPO_PDF
                                             else "default-src 'none'; frame-ancestors 'self'")}
    return Response(content=contenido, media_type=s["mime"], headers=cabeceras)
