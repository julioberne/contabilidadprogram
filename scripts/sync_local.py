# -*- coding: utf-8 -*-
"""sync_local.py — Poner el entorno LOCAL al día con master/producción.

Nace del 11-sep-2026: localhost:8000 sirvió un frontend/dist congelado de
días atrás y "los cambios no se veían" (y una pestaña vieja pedía chunks ya
inexistentes). Producción se construye sola en cada deploy; lo local NO —
este script cierra esa brecha en un solo paso:

  1) git fetch + merge --ff-only origin/master   → código al día
  2) npm run build en frontend/                  → dist al día para :8000

El backend local (uvicorn --reload) se recarga solo al ver el código nuevo.
Tras correrlo: Ctrl+Shift+R en la pestaña del navegador para soltar la caché.

Uso (desde la raíz del proyecto):
  .venv\\Scripts\\python.exe scripts\\sync_local.py
"""
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def correr(cmd, cwd=RAIZ, shell=False):
    mostrado = cmd if isinstance(cmd, str) else " ".join(cmd)
    print(f"\n$ {mostrado}")
    r = subprocess.run(cmd, cwd=str(cwd), shell=shell)
    if r.returncode != 0:
        sys.exit(f"\n✖ Falló: {mostrado} — revisa el mensaje de arriba (¿cambios locales sin commit?).")


correr(["git", "fetch", "origin"])
correr(["git", "merge", "--ff-only", "origin/master"])
correr("npm run build", cwd=RAIZ / "frontend", shell=True)
print("\n✔ Local al día con origin/master: código + build de :8000.")
print("  Último paso manual: Ctrl+Shift+R en la pestaña del navegador.")
