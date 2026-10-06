"""Lint de errores graves: los que rompen en ejecución, no los de estilo.

- Python: ruff con E9, F63, F7 y F82 (sintaxis, comparaciones inválidas, `return`/`break`
  fuera de lugar, nombres no definidos).
- JavaScript/JSX: eslint con la config de frontend/, quedándose solo con reglas que detectan
  fallos reales (variables no definidas, claves duplicadas, código inalcanzable, reglas de los
  hooks de React...) y con los errores de parseo. Los archivos de test se omiten: vitest ya los
  ejecuta y usan globales de Node.

Lo usan el CI y el hook `lint-al-editar` del kit de sesión (scripts/claude_kit/). El lint
completo de estilo sigue siendo `npm run lint` y ruff con sus reglas por defecto.

Uso:  python scripts/lint_critico.py [--py] [--js] [rutas...]
      Sin --py/--js revisa ambos; sin rutas, todo el backend y frontend/src.
      Sale con 1 si encuentra errores graves y con 0 si no.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUFF_SELECT = "E9,F63,F7,F82"
DIRS_PY = ["fin_sys_core", "routers", "kernel", "shared", "scripts", "tests", "server.py"]
EXT_JS = (".js", ".jsx", ".mjs")
REGLAS_JS = {
    "no-undef", "no-dupe-keys", "no-dupe-args", "no-dupe-class-members", "no-duplicate-case",
    "no-unreachable", "no-const-assign", "no-func-assign", "no-import-assign", "no-class-assign",
    "no-redeclare", "no-self-assign", "valid-typeof", "no-unsafe-negation", "no-obj-calls",
    "react-hooks/rules-of-hooks",
}


def es_test_js(ruta):
    ruta = ruta.replace("\\", "/")
    return "/__tests__/" in ruta or bool(re.search(r"\.(test|spec)\.[cm]?jsx?$", ruta))


def lint_py(rutas):
    """Lista de errores 'ruta:línea:col: CÓDIGO mensaje', o None si ruff no está instalado."""
    objetivos = rutas or [d for d in DIRS_PY if os.path.exists(os.path.join(RAIZ, d))]
    if not objetivos:
        return []
    r = subprocess.run([sys.executable, "-m", "ruff", "check", "--select", RUFF_SELECT,
                        "--output-format", "concise", "--no-cache", *objetivos],
                       cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if "No module named ruff" in r.stderr:
        return None
    return [l for l in r.stdout.splitlines() if re.match(r"^.+:\d+:\d+: ", l)]


def _eslint():
    front = os.path.join(RAIZ, "frontend")
    js = os.path.join(front, "node_modules", "eslint", "bin", "eslint.js")
    node = shutil.which("node")
    return (front, [node, js]) if node and os.path.isfile(js) else (front, None)


def filtrar_eslint(resultados, front):
    """Del JSON de eslint, deja solo errores graves fuera de los tests."""
    errores = []
    for archivo in resultados:
        ruta = os.path.relpath(archivo.get("filePath", ""), os.path.dirname(front)).replace("\\", "/")
        if es_test_js(ruta):
            continue
        for m in archivo.get("messages", []):
            if m.get("severity") != 2:
                continue
            regla = m.get("ruleId")
            if regla in REGLAS_JS or (regla is None and m.get("fatal")):
                errores.append(f"{ruta}:{m.get('line')}:{m.get('column')}: {regla or 'parseo'} {m.get('message')}")
    return errores


def lint_js(rutas):
    """Lista de errores graves de eslint, o None si eslint no está instalado en frontend/."""
    front, cmd = _eslint()
    if cmd is None:
        return None
    if rutas:
        objetivos = [os.path.abspath(r) for r in rutas if r.endswith(EXT_JS) and not es_test_js(r)]
        if not objetivos:
            return []
    else:
        objetivos = ["src"]
    r = subprocess.run([*cmd, "-f", "json", "--no-warn-ignored", *objetivos], cwd=front,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        datos = json.loads(r.stdout or "[]")
    except ValueError:
        return [f"eslint no pudo correr: {(r.stderr or r.stdout).strip()[:300]}"]
    return filtrar_eslint(datos, front)


def main():
    ap = argparse.ArgumentParser(description="Lint de errores graves (Python y JS/JSX).")
    ap.add_argument("--py", action="store_true", help="solo Python")
    ap.add_argument("--js", action="store_true", help="solo JavaScript/JSX")
    ap.add_argument("rutas", nargs="*")
    args = ap.parse_args()
    ambos = not (args.py or args.js)
    rutas_py = [r for r in args.rutas if r.endswith(".py")]
    rutas_js = [r for r in args.rutas if r.endswith(EXT_JS)]
    hay_errores = False

    if (args.py or ambos) and (rutas_py or not args.rutas):
        errores = lint_py(rutas_py)
        if errores is None:
            print("aviso: ruff no está instalado; Python sin revisar (pip install ruff)", file=sys.stderr)
        elif errores:
            hay_errores = True
            print("\n".join(errores))
    if (args.js or ambos) and (rutas_js or not args.rutas):
        errores = lint_js(rutas_js)
        if errores is None:
            print("aviso: eslint no está instalado en frontend/; JS sin revisar (npm install)", file=sys.stderr)
        elif errores:
            hay_errores = True
            print("\n".join(errores))
    if not hay_errores:
        print("lint crítico: sin errores graves")
    return 1 if hay_errores else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
