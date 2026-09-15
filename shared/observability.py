# -*- coding: utf-8 -*-
"""Observabilidad mínima del backend (2026-09-15).

Hasta hoy nadie medía cuánto tardaba cada request en el servidor: la
lentitud se percibía desde el navegador (que mezcla red + servidor) y no
había forma de saber si los ~0.6 s del dashboard eran Supabase, Python o
la distancia Colombia→VPS. Este middleware:

  - escribe la cabecera `Server-Timing: app;dur=<ms>` (visible en DevTools →
    Network → Timing) para separar tiempo de servidor del de red;
  - imprime una línea `[req] METHOD /ruta STATUS ms` por request a /api
    (gunicorn ya loguea el acceso, pero sin milisegundos).

Sin dependencias nuevas y sin tocar los routers.
"""
import time

from starlette.requests import Request


def install_timing_middleware(app, prefix: str = "/api", log: bool = True):
    @app.middleware("http")
    async def _timing(request: Request, call_next):
        inicio = time.perf_counter()
        response = await call_next(request)
        ms = (time.perf_counter() - inicio) * 1000.0
        try:
            response.headers["Server-Timing"] = f"app;dur={ms:.1f}"
        except Exception:
            pass
        if log and request.url.path.startswith(prefix):
            print(f"[req] {request.method} {request.url.path} "
                  f"{response.status_code} {ms:.0f}ms")
        return response

    return app
