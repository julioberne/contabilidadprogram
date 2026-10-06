"""Hook PostToolUse del kit de sesión de FIN-SYS: «lint-al-editar» (docs/guia-trabajo-claude.md §9).

Después de cada Edit/Write de un .py, .js, .jsx o .mjs del proyecto, corre `scripts/lint_critico.py`
sobre ese archivo. Si encuentra errores graves (sintaxis, nombres no definidos, claves duplicadas,
reglas de hooks...), se los devuelve a Claude con exit 2 para que los corrija en el acto.
En silencio si todo está bien, si el archivo no aplica o si no hay linter disponible.

Usa el Python del .venv del checkout principal (donde está ruff). Solo actúa dentro de
contabilidadprogram. Usa solo la biblioteca estándar y nunca falla hacia afuera.
"""
import json
import os
import re
import subprocess
import sys

PROYECTO = "contabilidadprogram"
EXTENSIONES = (".py", ".js", ".jsx", ".mjs")
MAX_LINEAS = 20


def raiz_principal(ruta):
    partes = re.split(r"[\\/]", ruta)
    bajas = [p.lower() for p in partes]
    return os.sep.join(partes[: bajas.index(PROYECTO) + 1]) if PROYECTO in bajas else None


def raiz_repo(archivo):
    """Sube desde el archivo hasta la carpeta que tiene scripts/lint_critico.py (worktree o principal)."""
    d = os.path.dirname(os.path.abspath(archivo))
    while True:
        if os.path.isfile(os.path.join(d, "scripts", "lint_critico.py")):
            return d
        padre = os.path.dirname(d)
        if padre == d:
            return None
        d = padre


def main():
    datos = json.load(sys.stdin)
    archivo = (datos.get("tool_input") or {}).get("file_path") or ""
    if PROYECTO not in archivo.lower() or not archivo.lower().endswith(EXTENSIONES) or not os.path.isfile(archivo):
        return 0
    repo = raiz_repo(archivo)
    principal = raiz_principal(archivo)
    if not repo or not principal:
        return 0
    python = os.path.join(principal, ".venv", "Scripts", "python.exe")
    if not os.path.isfile(python):
        python = sys.executable
    r = subprocess.run([python, os.path.join(repo, "scripts", "lint_critico.py"), archivo],
                       cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=80)
    if r.returncode != 1:
        return 0
    lineas = [l for l in r.stdout.splitlines() if l.strip()][:MAX_LINEAS]
    sys.stderr.reconfigure(encoding="utf-8")
    print(f"[lint-al-editar] Errores graves en {os.path.basename(archivo)} (rompen en ejecución); corrígelos antes de seguir:",
          file=sys.stderr)
    print("\n".join(lineas), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # un hook roto no debe trabar la sesión
        sys.exit(0)
