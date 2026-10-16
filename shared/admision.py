# -*- coding: utf-8 -*-
"""admision.py — Control de admisión por usuario y por clase de carga.

Estándar de consultas, hito H1 (reglas P4, P7, P8 y P12): cuotas por usuario
(token bucket) y tope de consultas pesadas simultáneas, al estilo de los
limitadores de Stripe y del descarte de carga de la Builders' Library de AWS.

Arranca en modo **"registrar"** (marcha blanca): NO rechaza nada, solo deja en
el log `[admision] habría rechazado …` para medir con tráfico real antes de
activar. Modos (variable FINSYS_ADMISION):

    registrar  (por defecto) → nunca bloquea; registra lo que habría rechazado
    activo                   → responde 429 + Retry-After al exceder la cuota
    apagado                  → el middleware no hace nada

Reglas fijas:
- Falla ABIERTO: cualquier error interno deja pasar la petición.
- El health y las escrituras contables nunca se rechazan aquí (crítico).
- Todo es en memoria POR WORKER: con 2 workers, cada uno cuenta lo suyo.
"""
import hashlib
import os
import threading
import time
from typing import Dict, Optional, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse

# ── Clases de carga ──────────────────────────────────────────────────────────
CRITICA, INTERACTIVA, INFORME = "critica", "interactiva", "informe"

# Prefijos de rutas pesadas (recorren muchas filas o arman archivos).
_PREFIJOS_INFORME = (
    "/api/analytics/dataset", "/api/contadores/reportes", "/api/org/consolidated",
    "/api/compendios", "/api/exports", "/api/exportacion", "/api/transactions/export",
)

# Cuotas (P7). Valores de partida: se ajustan con lo que registre la marcha blanca.
LECTURA_TASA, LECTURA_RAFAGA = 10.0, 30.0      # GET interactivos por usuario
INFORME_SIMULTANEOS_USUARIO = 2                 # pesadas a la vez por usuario
INFORME_SIMULTANEOS_WORKER = 4                  # pesadas a la vez por worker (bulkhead)
RETRY_AFTER_S = 2

_LOG_CADA_S = 10.0                              # no inundar el log en un pico


def modo() -> str:
    m = (os.environ.get("FINSYS_ADMISION") or "registrar").strip().lower()
    return m if m in ("registrar", "activo", "apagado") else "registrar"


def clasificar(metodo: str, ruta: str, query: str = "") -> str:
    """Clase de carga de una petición (P4)."""
    if ruta.startswith("/api/health"):
        return CRITICA
    if metodo != "GET":
        # Escrituras: altas contables, ✅ del bot, ediciones. Una escritura ya
        # aceptada nunca se descarta (P8).
        return CRITICA
    if ruta.startswith(_PREFIJOS_INFORME):
        return INFORME
    if ruta.startswith("/api/diario/movimientos") and ("agrupar=" in query or "limit=5000" in query):
        return INFORME
    return INTERACTIVA


def clave_usuario(request: Request) -> str:
    """Identidad barata para las cuotas: hash del token (sin validarlo; la
    autenticación la hace auth_guard) o, sin token, la IP del cliente."""
    auth = request.headers.get("authorization") or ""
    if auth:
        return "t:" + hashlib.sha256(auth.encode()).hexdigest()[:16]
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return "ip:" + (ip or (request.client.host if request.client else "?"))


class _Cubeta:
    """Token bucket: `tasa` fichas por segundo, hasta `rafaga`."""
    __slots__ = ("fichas", "t")

    def __init__(self, rafaga: float):
        self.fichas, self.t = rafaga, time.monotonic()

    def tomar(self, tasa: float, rafaga: float) -> bool:
        ahora = time.monotonic()
        self.fichas = min(rafaga, self.fichas + (ahora - self.t) * tasa)
        self.t = ahora
        if self.fichas >= 1.0:
            self.fichas -= 1.0
            return True
        return False


class Admision:
    """Estado del limitador de UN worker. Seguro entre hilos."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cubetas: Dict[str, _Cubeta] = {}
        self._informes_usuario: Dict[str, int] = {}
        self._informes_worker = 0
        self._ultimo_log: Dict[str, float] = {}
        self.contadores = {"admitidas": 0, "habria_rechazado": 0, "rechazadas": 0}

    # Devuelve (admitir, motivo_si_excede)
    def entrar(self, clase: str, usuario: str) -> Tuple[bool, Optional[str]]:
        if clase == CRITICA:
            return True, None
        with self._lock:
            if clase == INTERACTIVA:
                cub = self._cubetas.get(usuario)
                if cub is None:
                    if len(self._cubetas) > 10000:      # tope de memoria
                        self._cubetas.clear()
                    cub = self._cubetas[usuario] = _Cubeta(LECTURA_RAFAGA)
                if not cub.tomar(LECTURA_TASA, LECTURA_RAFAGA):
                    return False, f"más de {LECTURA_TASA:g} lecturas/s (ráfaga {LECTURA_RAFAGA:g})"
                return True, None
            # INFORME: tope por usuario y por worker
            n_usr = self._informes_usuario.get(usuario, 0)
            if n_usr >= INFORME_SIMULTANEOS_USUARIO:
                return False, f"{n_usr} consultas pesadas en curso del mismo usuario"
            if self._informes_worker >= INFORME_SIMULTANEOS_WORKER:
                return False, f"{self._informes_worker} consultas pesadas en curso en este worker"
            self._informes_usuario[usuario] = n_usr + 1
            self._informes_worker += 1
            return True, None

    def salir(self, clase: str, usuario: str) -> None:
        if clase != INFORME:
            return
        with self._lock:
            n = self._informes_usuario.get(usuario, 0) - 1
            if n > 0:
                self._informes_usuario[usuario] = n
            else:
                self._informes_usuario.pop(usuario, None)
            self._informes_worker = max(0, self._informes_worker - 1)

    def debe_loguear(self, clave: str) -> bool:
        ahora = time.monotonic()
        with self._lock:
            if ahora - self._ultimo_log.get(clave, 0.0) < _LOG_CADA_S:
                return False
            self._ultimo_log[clave] = ahora
            return True


ESTADO = Admision()


def install_admission_middleware(app, estado: Admision = ESTADO):
    @app.middleware("http")
    async def _admision(request: Request, call_next):
        m = modo()
        ruta = request.url.path
        if m == "apagado" or not ruta.startswith("/api/"):
            return await call_next(request)
        try:
            clase = clasificar(request.method, ruta, request.url.query or "")
            usuario = clave_usuario(request)
            admitir, motivo = estado.entrar(clase, usuario)
        except Exception:
            return await call_next(request)               # falla abierto

        if not admitir:
            # En modo registrar la petición pasa, pero un INFORME no tomó cupo:
            # no hay que liberarlo al salir.
            tomo_cupo = False
            if m == "activo":
                estado.contadores["rechazadas"] += 1
                if estado.debe_loguear(f"r:{usuario}:{clase}"):
                    print(f"[admision] 429 {request.method} {ruta} ({clase}, {usuario[:10]}): {motivo}")
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Demasiadas consultas seguidas. Intenta de nuevo en unos segundos.",
                             "motivo": motivo},
                    headers={"Retry-After": str(RETRY_AFTER_S)},
                )
            estado.contadores["habria_rechazado"] += 1
            if estado.debe_loguear(f"h:{usuario}:{clase}"):
                print(f"[admision] habría rechazado {request.method} {ruta} ({clase}, {usuario[:10]}): {motivo}")
        else:
            tomo_cupo = True
            estado.contadores["admitidas"] += 1

        try:
            return await call_next(request)
        finally:
            if tomo_cupo:
                estado.salir(clase, usuario)

    return app


def resumen() -> dict:
    """Para /api/health/profundo: modo, cuotas y contadores de este worker."""
    return {
        "modo": modo(),
        "cuotas": {"lectura_por_s": LECTURA_TASA, "rafaga": LECTURA_RAFAGA,
                   "informes_por_usuario": INFORME_SIMULTANEOS_USUARIO,
                   "informes_por_worker": INFORME_SIMULTANEOS_WORKER},
        "contadores": dict(ESTADO.contadores),
        "informes_en_curso": ESTADO._informes_worker,
    }


# ── Pool saturado → 503 + Retry-After (estándar de consultas, H2 / P2) ───────
_DETALLE_SATURADO = ("El servidor está atendiendo muchas consultas a la vez. "
                     "Intenta de nuevo en unos segundos.")


def install_saturation_middleware(app):
    """Si durante la petición get_conn() rechazó por pool saturado, la respuesta
    se convierte en 503 + Retry-After — AUNQUE el endpoint haya dicho 200.
    Motivo (laboratorio, 16-oct-2026): varios drivers se tragan el error y
    devuelven [] o datos de ejemplo con 200 (p. ej. /api/portfolios inventaba
    "Negocio A/B"); con saturación esos datos están incompletos o son falsos.
    El 503 le dice al cliente que es transitorio y el wrapper de fetch reintenta."""
    from fin_sys_core.db_pool import saturacion_ctx

    @app.middleware("http")
    async def _saturacion(request: Request, call_next):
        marca = {"saturado": False}
        token = saturacion_ctx.set(marca)
        try:
            response = await call_next(request)
        finally:
            saturacion_ctx.reset(token)
        if marca["saturado"]:
            ESTADO.contadores["saturado_503"] = ESTADO.contadores.get("saturado_503", 0) + 1
            return JSONResponse(status_code=503, content={"detail": _DETALLE_SATURADO},
                                headers={"Retry-After": str(RETRY_AFTER_S)})
        return response

    return app
