"""Chequeo diario determinista para el agente de mantenimiento de FIN-SYS (tarea mantenimiento-finsys).

Junta en un solo comando —un solo permiso— todo lo que no necesita criterio: git y producción,
salud (solo lectura), tests puros del CI, medición de consumo, frentes, specs, memoria y documentos
viejos. Escribe scratch/tablero.md y agrega una fila a scratch/medicion-historial.csv del checkout
principal. Nunca escribe en la BD ni en archivos versionados.

Uso:
  python chequeo_diario.py                     corre todo y escribe el tablero
  python chequeo_diario.py --sesiones "TEXTO"  completa la sección Sesiones del tablero de hoy;
                                               TEXTO = "resumen ;; sesión 1 ;; sesión 2 ..."
La carpeta del proyecto se puede cambiar con la variable de entorno FINSYS_RAIZ.
"""
import argparse
import csv
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

RAIZ = os.environ.get("FINSYS_RAIZ", r"C:\Users\andre\OneDrive\Escritorio\programas\contabilidadprogram")
MEMORIA = os.path.expanduser(r"~/.claude/projects/C--Users-andre-OneDrive-Escritorio-programas-contabilidadprogram/memory")
PROD = "https://finsys-andres.duckdns.org/api/health"
BASE_CONTEXTO = 370_000
TABLERO = os.path.join(RAIZ, "scratch", "tablero.md")
HISTORIAL = os.path.join(RAIZ, "scratch", "medicion-historial.csv")
PENDIENTE_SESIONES = "- Sesiones y cuota: (pendiente: las agrega el agente con --sesiones)"


def correr(cmd, timeout=300, cwd=RAIZ):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, f"{type(e).__name__}: {e}"


def python_proyecto():
    p = os.path.join(RAIZ, ".venv", "Scripts", "python.exe")
    return p if os.path.isfile(p) else sys.executable


def git(*args, timeout=60):
    return correr(["git", "-C", RAIZ, *args], timeout=timeout)


def seccion_git():
    git("fetch", "-q", "origin", timeout=120)
    lineas, resumen = [], []
    _, cuenta = git("rev-list", "--left-right", "--count", "master...origin/master")
    try:
        adelante, atras = (int(x) for x in cuenta.split()[:2])
    except ValueError:
        adelante = atras = None
    if adelante is not None:
        lineas.append(f"- master local vs origin/master: +{adelante} / −{atras}")
        if adelante or atras:
            resumen.append(f"master local +{adelante}/−{atras} vs origin")
    _, ramas = git("for-each-ref", "--format=%(refname:short)", "refs/heads/claude/")
    sin_integrar = []
    for rama in ramas.split():
        _, n = git("rev-list", "--count", f"origin/master..{rama}")
        if n.strip().isdigit() and int(n) > 0:
            _, solo_inicial = git("log", "--format=%s", f"origin/master..{rama}")
            if solo_inicial.strip() != "Initial commit":
                sin_integrar.append(f"{rama} ({int(n)})")
    lineas.append(f"- Ramas claude/* con trabajo fuera de origin/master: {', '.join(sin_integrar[:8]) or 'ninguna'}")
    if sin_integrar:
        resumen.append(f"{len(sin_integrar)} rama(s) sin integrar")
    _, estado = git("status", "--porcelain")
    sucios = [l[3:] for l in estado.splitlines() if l.strip()]
    lineas.append(f"- Sin commitear en el checkout principal: {len(sucios)}" + (f" ({', '.join(sucios[:5])})" if sucios else ""))
    try:
        with urllib.request.urlopen(PROD, timeout=15) as r:
            cuerpo = r.read(2000).decode("utf-8", "replace")
            prod = f"{r.status}"
            try:
                d = json.loads(cuerpo)
                prod += " · " + ", ".join(f"{k}={d[k]}" for k in ("status", "db", "database") if k in d)
            except ValueError:
                pass
    except Exception as e:  # noqa: BLE001 - cualquier fallo de red es un dato para el tablero
        prod = f"FALLA ({type(e).__name__}: {str(e)[:80]})"
    lineas.append(f"- Producción {PROD}: {prod}")
    return lineas, resumen, prod


ANSI = re.compile(r"\x1b\[[0-9;]*m")
SECRETO = re.compile(r"password|contrase|clave|token|secret|admin123|@\S+\s*/", re.I)


def resumir_health(salida):
    """(ok, total, problemas) de los chequeos [n/7] de health_check.py, sin colores de terminal."""
    chequeos = [ANSI.sub("", l).strip() for l in salida.splitlines() if re.search(r"\[\d+/\d+\]", l)]
    ok = sum("✅" in l for l in chequeos)
    otros = [ANSI.sub("", l).strip() for l in salida.splitlines() if re.search(r"[❌⚠]", l)]
    problemas = [l for l in dict.fromkeys(otros) if not SECRETO.search(l)]
    return ok, len(chequeos), problemas


def resumir_mantenimiento(salida):
    """Solo líneas de aviso (❌/⚠) de session_maintenance --check; nunca líneas con credenciales."""
    lineas = [ANSI.sub("", l).strip() for l in salida.splitlines() if re.search(r"[❌⚠]", l)]
    return [l for l in lineas if not SECRETO.search(l)]


def seccion_salud():
    lineas, py = [], python_proyecto()
    rc, out = correr([py, os.path.join("scripts", "health_check.py")], timeout=180)
    ok, total, problemas = resumir_health(out)
    lineas.append(f"- health_check.py (solo lee): {ok}/{total} ✅ · código {rc} (frontend/backend locales caídos es normal sin sesión abierta)")
    lineas += [f"  - {l[:140]}" for l in problemas[:6]]
    rc, out = correr([py, os.path.join("scripts", "session_maintenance.py"), "--check"], timeout=180)
    avisos = resumir_mantenimiento(out)
    lineas.append(f"- session_maintenance.py --check: código {rc} · " + ("; ".join(avisos)[:200] if avisos else "sin avisos"))
    ci = os.path.join(RAIZ, ".github", "workflows", "ci.yml")
    modulos = []
    if os.path.isfile(ci):
        m = re.search(r"python -m unittest ([^\n]+?)(?: -v)?\s*$", open(ci, encoding="utf-8").read(), re.M)
        modulos = m.group(1).split() if m else []
    tests = "sin lista de tests en ci.yml"
    if modulos:
        rc, out = correr([py, "-m", "unittest", *modulos], timeout=900)
        ran = re.search(r"Ran (\d+) tests?", out)
        fallos = re.findall(r"^(?:FAIL|ERROR): (\S+ \([^)]*\))", out, re.M)
        tests = f"{ran.group(1) if ran else '?'} tests · {'OK' if rc == 0 else 'FALLAN ' + str(len(fallos))}"
        lineas.append(f"- Tests puros del CI: {tests}")
        lineas += [f"  - {f}" for f in fallos[:8]]
    salud = f"health {ok}/{total} · {tests}"
    return lineas, salud


def seccion_medicion():
    script = os.path.join(RAIZ, "scripts", "medir_consumo_claude.py")
    if not os.path.isfile(script):
        return ["- medir_consumo_claude.py no existe en el checkout principal"], "sin medición"
    _, out = correr([sys.executable, script, "--dias", "7"], timeout=600)
    def num(patron):
        m = re.search(patron, out)
        return int(m.group(1).replace(",", "").replace(".", "")) if m else None
    sesiones = num(r"Sesiones con actividad en \d+ días: ([\d,.]+)")
    medio = num(r"Contexto medio por turno: ([\d,.]+)")
    releido = num(r"Tokens releídos de caché: ([\d,.]+) M")
    grandes = num(r"sesiones que pasaron 700,000: (\d+)")
    hoy = time.strftime("%Y-%m-%d")
    filas = []
    if os.path.isfile(HISTORIAL):
        with open(HISTORIAL, encoding="utf-8") as fh:
            filas = list(csv.DictReader(fh))
    anterior = next((f for f in reversed(filas) if f.get("fecha") != hoy), None)
    if medio is not None and not any(f.get("fecha") == hoy for f in filas):
        nuevo = not os.path.isfile(HISTORIAL)
        with open(HISTORIAL, "a", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            if nuevo:
                w.writerow(["fecha", "sesiones", "contexto_medio_turno", "releido_M", "sesiones_mas_700k"])
            w.writerow([hoy, sesiones, medio, releido, grandes])
    previo = f"{int(anterior['contexto_medio_turno']) // 1000}k" if anterior and anterior.get("contexto_medio_turno", "").isdigit() else "—"
    tendencia = (f"contexto medio por turno {medio // 1000 if medio else '?'}k (7 días; base {BASE_CONTEXTO // 1000}k; "
                 f"anterior {previo})")
    lineas = [f"- {tendencia}", f"- Sesiones: {sesiones} · releído: {releido} M · sesiones >700k: {grandes}"]
    return lineas, tendencia


def campo(texto, patron):
    m = re.search(patron, texto, re.M)
    return m.group(1).strip() if m else ""


def seccion_frentes():
    lineas, activos = [], []
    for ruta in sorted(glob.glob(os.path.join(RAIZ, "docs", "frentes", "*.md"))):
        nombre = os.path.basename(ruta)[:-3]
        if nombre.lower() == "readme":
            continue
        texto = open(ruta, encoding="utf-8", errors="replace").read()
        estado = campo(texto, r"Estado:\s*([A-ZÁÉÍÓÚ ]+?)(?:\s*·|$)") or "SIN ESTADO"
        fecha = campo(texto, r"Actualizado:\s*([0-9-]{10})")
        m = re.search(r"##\s*Pr[oó]ximo paso[^\n]*\n(.*?)(?:\n##|\Z)", texto, re.S)
        proximo = ""
        if m:
            proximo = next((l.strip().lstrip("-*0123456789. ") for l in m.group(1).splitlines() if l.strip()), "")
        dias = (time.time() - os.path.getmtime(ruta)) / 86400
        alerta = " ¿abandonado?" if dias >= 5 and not estado.startswith("CERRADO") else ""
        lineas.append(f"- {nombre}: {estado} (actualizado {fecha or '?'}){alerta} → {proximo[:140]}")
        if not estado.startswith("CERRADO"):
            activos.append(nombre)
    return lineas or ["- (no hay frentes)"], activos


def seccion_specs():
    lineas = []
    limite = time.time() - 14 * 86400
    for ruta in sorted(glob.glob(os.path.join(RAIZ, "docs", "specs", "**", "*.md"), recursive=True)):
        if os.path.getmtime(ruta) < limite:
            continue
        texto = open(ruta, encoding="utf-8", errors="replace").read()
        estado = campo(texto, r"\*\*Estado:\*\*\s*([^\n]+)")
        pendientes = len(re.findall(r"^\s*- \[ \]", texto, re.M))
        if estado or pendientes:
            rel = os.path.relpath(ruta, os.path.join(RAIZ, "docs", "specs")).replace("\\", "/")
            lineas.append(f"- {rel}: {estado[:110]}" + (f" · casillas sin marcar: {pendientes}" if pendientes else ""))
    return lineas or ["- (sin specs tocadas en 14 días)"]


def seccion_propuestas():
    lineas = []
    indice = os.path.join(MEMORIA, "MEMORY.md")
    if os.path.isfile(indice):
        largas = [l for l in open(indice, encoding="utf-8").read().splitlines() if l.startswith("- [") and len(l) > 250]
        if largas:
            nombres = [re.match(r"- \[([^\]]+)\]", l).group(1) for l in largas[:3]]
            lineas.append(f"- Memoria: {len(largas)} entradas del índice con más de 250 caracteres (p. ej. {', '.join(nombres)}) → acortar")
    hace = time.time() - 45 * 86400
    viejos = []
    for ruta in glob.glob(os.path.join(RAIZ, "*.md")) + glob.glob(os.path.join(RAIZ, "docs", "*.md")):
        rel = os.path.relpath(ruta, RAIZ).replace("\\", "/")
        _, fecha = git("log", "-1", "--format=%ct", "--", rel)
        if fecha.strip().isdigit() and int(fecha) < hace:
            viejos.append(f"{rel} ({os.path.getsize(ruta) // 1024} KB)")
    if viejos:
        lineas.append(f"- Docs sin commits en 45 días: {', '.join(viejos[:8])} → revisar o archivar")
    return lineas or ["- (nada)"]


def escribir_tablero():
    git_l, git_r, prod = seccion_git()
    salud_l, salud = seccion_salud()
    med_l, tendencia = seccion_medicion()
    fren_l, activos = seccion_frentes()
    specs_l = seccion_specs()
    prop_l = seccion_propuestas()
    propuestas = 0 if prop_l == ["- (nada)"] else len(prop_l)
    resumen = [
        PENDIENTE_SESIONES,
        f"- Git: {'; '.join(git_r) or 'al día'} · producción {prod.split(' ')[0]}",
        f"- Salud: {salud}",
        f"- Frentes activos: {', '.join(activos) or 'ninguno'}",
        f"- Tendencia: {tendencia}",
        f"- Propuestas que esperan OK de Andrés: {propuestas} (ver abajo)",
    ]
    partes = [f"# Tablero FIN-SYS — {time.strftime('%Y-%m-%d %H:%M')}", "## Resumen", *resumen,
              "## Sesiones", "- (pendiente: las agrega el agente con --sesiones)",
              "## Git y producción", *git_l, "## Frentes", *fren_l, "## Specs (tocadas en 14 días)", *specs_l,
              "## Salud", *salud_l, "## Medición", *med_l, "## Propuestas (no aplicadas)", *prop_l]
    os.makedirs(os.path.dirname(TABLERO), exist_ok=True)
    with open(TABLERO, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(partes) + "\n")
    return "\n".join(partes)


def agregar_sesiones(texto):
    if not os.path.isfile(TABLERO):
        return "No hay tablero: corre primero el chequeo sin --sesiones."
    items = [t.strip() for t in texto.split(";;") if t.strip()]
    if not items:
        return "Texto vacío."
    contenido = open(TABLERO, encoding="utf-8").read()
    contenido = contenido.replace(PENDIENTE_SESIONES, f"- Sesiones y cuota: {items[0]}", 1)
    cuerpo = "\n".join(f"- {t}" for t in (items[1:] or ["(ninguna activa)"]))
    contenido = re.sub(r"## Sesiones\n.*?(?=\n## )", f"## Sesiones\n{cuerpo}", contenido, count=1, flags=re.S)
    with open(TABLERO, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(contenido)
    return f"Sesiones agregadas al tablero ({len(items) - 1} líneas): {TABLERO}"


def main():
    ap = argparse.ArgumentParser(description="Chequeo diario de FIN-SYS para el agente de mantenimiento.")
    ap.add_argument("--sesiones", help='"resumen ;; sesión 1 ;; sesión 2 ..."')
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    print(agregar_sesiones(args.sesiones) if args.sesiones else escribir_tablero())


if __name__ == "__main__":
    main()
