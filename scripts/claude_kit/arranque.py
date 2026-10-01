"""Hook SessionStart del kit de sesión de FIN-SYS (ver docs/guia-trabajo-claude.md).

Al iniciar una sesión, y después de /clear o de compactar, inyecta en el contexto:
- los frentes activos (docs/frentes/*.md) con su próximo paso,
- el resumen del tablero que deja el agente de mantenimiento (scratch/tablero.md),
- un aviso si el worktree nació de `main` vacía.

Solo actúa dentro de este proyecto; en cualquier otra carpeta no imprime nada.
Usa solo la biblioteca estándar. Nunca falla hacia afuera: ante un error, calla.
"""
import json
import os
import re
import sys
import time

PROYECTO = "contabilidadprogram"
MAX_FRENTES = 8
MAX_LINEAS_TABLERO = 14


def raiz_principal(cwd):
    """Checkout principal: la ruta hasta la carpeta del proyecto (los worktrees viven dentro)."""
    partes = re.split(r"[\\/]", cwd)
    for i, p in enumerate(partes):
        if p.lower() == PROYECTO:
            return os.sep.join(partes[: i + 1])
    return None


def leer(ruta, limite=200_000):
    with open(ruta, encoding="utf-8", errors="replace") as fh:
        return fh.read(limite)


def resumen_frente(ruta):
    texto = leer(ruta)
    nombre = os.path.splitext(os.path.basename(ruta))[0]
    m = re.search(r"Estado:\s*([A-ZÁÉÍÓÚ ]+?)(?:\s*·|\s*$)", texto, re.M)
    estado = (m.group(1).strip() if m else "SIN ESTADO").upper()
    proximo = ""
    m = re.search(r"##\s*Pr[oó]ximo paso[^\n]*\n(.*?)(?:\n##|\Z)", texto, re.S)
    if m:
        for linea in m.group(1).splitlines():
            linea = linea.strip().lstrip("-*0123456789. ").strip()
            if linea:
                proximo = linea[:160]
                break
    dias = (time.time() - os.path.getmtime(ruta)) / 86400
    return nombre, estado, proximo, dias


def bloque_frentes(cwd, raiz):
    carpeta = os.path.join(cwd, "docs", "frentes")
    if not os.path.isdir(carpeta) and raiz:
        carpeta = os.path.join(raiz, "docs", "frentes")
    if not os.path.isdir(carpeta):
        return []
    filas = []
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.endswith(".md") or nombre.lower() == "readme.md" or nombre.startswith("_"):
            continue
        n, estado, proximo, dias = resumen_frente(os.path.join(carpeta, nombre))
        if estado.startswith("CERRADO"):
            continue
        viejo = f" (sin tocar hace {dias:.0f} días)" if dias >= 5 else ""
        filas.append(f"- {n}: {estado}{viejo}" + (f" → próximo: {proximo}" if proximo else ""))
    if not filas:
        return ["Frentes activos: ninguno (docs/frentes/ solo tiene la plantilla)."]
    return ["Frentes activos (lee SOLO el de tu tarea):"] + filas[:MAX_FRENTES]


def bloque_tablero(raiz):
    if not raiz:
        return []
    ruta = os.path.join(raiz, "scratch", "tablero.md")
    if not os.path.isfile(ruta):
        return ["Tablero de mantenimiento: aún no existe (lo crea la tarea programada diaria)."]
    dias = (time.time() - os.path.getmtime(ruta)) / 86400
    lineas = [l.rstrip() for l in leer(ruta, 20_000).splitlines()]
    # Solo la sección RESUMEN (hasta el siguiente encabezado ##).
    resumen, dentro = [], False
    for l in lineas:
        if l.lower().startswith("## resumen"):
            dentro = True
            continue
        if dentro and l.startswith("## "):
            break
        if dentro and l.strip():
            resumen.append(l)
    if not resumen:
        resumen = [l for l in lineas if l.strip()][:MAX_LINEAS_TABLERO]
    aviso = f" (ATENCIÓN: tiene {dias:.0f} días)" if dias >= 2 else ""
    return [f"Tablero de mantenimiento{aviso} — detalle en {ruta}:"] + resumen[:MAX_LINEAS_TABLERO]


def aviso_worktree(cwd):
    if os.path.isfile(os.path.join(cwd, "CLAUDE.md")) or os.path.isfile(os.path.join(cwd, "server.py")):
        return []
    if re.search(r"[\\/]\.claude[\\/]worktrees[\\/]", cwd):
        return ["AVISO: este worktree no tiene el código (nació de `main`, que está vacía). "
                "Antes de nada: `git reset --hard master` (CLAUDE.md §1)."]
    return []


def main():
    try:
        datos = json.load(sys.stdin)
    except ValueError:
        datos = {}
    cwd = datos.get("cwd") or os.getcwd()
    if PROYECTO not in cwd.lower():
        return
    raiz = raiz_principal(cwd)
    origen = datos.get("source", "startup")
    partes = [f"[Kit de sesión FIN-SYS · evento: {origen}]"]
    partes += aviso_worktree(cwd)
    partes += bloque_frentes(cwd, raiz)
    partes += bloque_tablero(raiz)
    if origen in ("clear", "compact"):
        partes.append("Contexto recién limpiado: retoma desde el frente de la tarea; no releas lo ya cerrado.")
    salida = {"hookSpecificOutput": {"hookEventName": "SessionStart",
                                     "additionalContext": "\n".join(partes)}}
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(salida, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # un hook roto no debe estorbar la sesión
        pass
