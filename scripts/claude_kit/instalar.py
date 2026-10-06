"""Instala el kit de sesión de FIN-SYS a nivel de usuario (~/.claude), para que llegue a
todas las sesiones de este PC aunque el worktree nazca de `main` vacía.

Qué copia (la fuente versionada es este repo):
  scripts/claude_kit/{arranque,medidor,guardia,lint_al_editar,chequeo_diario}.py → ~/.claude/hooks/finsys/
  .claude/agents/*.md                          → ~/.claude/agents/
  .claude/skills/cerrar-hito/SKILL.md          → ~/.claude/skills/cerrar-hito/
y registra en ~/.claude/settings.json (con copia de respaldo; no toca otras claves):
  - hooks SessionStart (arranque), UserPromptSubmit (medidor), PreToolUse (guardia) y
    PostToolUse (lint_al_editar);
  - un único permiso: ejecutar chequeo_diario.py (solo lee y escribe el tablero), para que la
    tarea programada del agente de mantenimiento no se detenga esperando aprobación.

Los hooks solo actúan cuando la sesión está dentro de `contabilidadprogram`.

Uso (desde la raíz del repo):
  python scripts/claude_kit/instalar.py             instala o actualiza
  python scripts/claude_kit/instalar.py --check     muestra diferencias, no escribe
  python scripts/claude_kit/instalar.py --desinstalar
La tarea programada del agente de mantenimiento (scripts/claude_kit/mantenimiento.md)
se crea desde una sesión de Claude; ver docs/guia-trabajo-claude.md.
"""
import argparse
import json
import os
import shutil
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOME = os.path.join(os.path.expanduser("~"), ".claude")
DIR_HOOKS = os.path.join(HOME, "hooks", "finsys")
SETTINGS = os.path.join(HOME, "settings.json")
MARCA = "hooks/finsys/"  # identifica nuestras entradas en settings.json

SCRIPTS = ["arranque.py", "medidor.py", "guardia.py", "lint_al_editar.py", "chequeo_diario.py"]
COPIAS = [(os.path.join(REPO, "scripts", "claude_kit", s), os.path.join(DIR_HOOKS, s)) for s in SCRIPTS] + [
    (os.path.join(REPO, ".claude", "skills", "cerrar-hito", "SKILL.md"),
     os.path.join(HOME, "skills", "cerrar-hito", "SKILL.md")),
]
for nombre in sorted(os.listdir(os.path.join(REPO, ".claude", "agents"))):
    if nombre.endswith(".md"):
        COPIAS.append((os.path.join(REPO, ".claude", "agents", nombre), os.path.join(HOME, "agents", nombre)))


def comando(script):
    ruta = os.path.join(DIR_HOOKS, script).replace("\\", "/")
    return f'python "{ruta}"'


HOOKS = {
    "SessionStart": {"matcher": "startup|clear|compact",
                     "hooks": [{"type": "command", "command": comando("arranque.py"), "timeout": 15}]},
    "UserPromptSubmit": {"hooks": [{"type": "command", "command": comando("medidor.py"), "timeout": 10}]},
    "PreToolUse": {"matcher": "Bash|PowerShell|Edit|Write|MultiEdit|NotebookEdit|Read",
                   "hooks": [{"type": "command", "command": comando("guardia.py"), "timeout": 10}]},
    "PostToolUse": {"matcher": "Edit|Write|MultiEdit",
                    "hooks": [{"type": "command", "command": comando("lint_al_editar.py"), "timeout": 90}]},
}
PERMISO_CHEQUEO = f"Bash({comando('chequeo_diario.py')}*)"


def mismo_contenido(a, b):
    """Compara ignorando el fin de línea: git en Windows deja CRLF en el repo y la copia puede tener LF."""
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read().replace(b"\r\n", b"\n") == fb.read().replace(b"\r\n", b"\n")


def es_nuestra(entrada):
    return any(MARCA in str(h.get("command", "")).replace("\\", "/") for h in entrada.get("hooks", []))


def leer_settings():
    if not os.path.exists(SETTINGS):
        return {}
    with open(SETTINGS, encoding="utf-8") as fh:
        return json.load(fh)


def settings_con_hooks(cfg, instalar):
    nuevo = json.loads(json.dumps(cfg))
    hooks = nuevo.setdefault("hooks", {})
    for evento in list(hooks):
        hooks[evento] = [e for e in hooks[evento] if not es_nuestra(e)]
    if instalar:
        for evento, entrada in HOOKS.items():
            hooks.setdefault(evento, []).append(entrada)
    for evento in [e for e, lista in hooks.items() if not lista]:
        del hooks[evento]
    if not hooks:
        del nuevo["hooks"]
    permisos = nuevo.setdefault("permissions", {})
    allow = [r for r in permisos.get("allow", []) if r != PERMISO_CHEQUEO]
    if instalar:
        allow.append(PERMISO_CHEQUEO)
    permisos["allow"] = allow
    return nuevo


def guardar_settings(cfg):
    if os.path.exists(SETTINGS):
        respaldo = f"{SETTINGS}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(SETTINGS, respaldo)
        print(f"  respaldo: {respaldo}")
    with open(SETTINGS, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def main():
    ap = argparse.ArgumentParser(description="Instala el kit de sesión de FIN-SYS en ~/.claude")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="solo mostrar diferencias")
    g.add_argument("--desinstalar", action="store_true")
    args = ap.parse_args()

    cfg = leer_settings()
    if args.check:
        for src, dst in COPIAS:
            estado = "falta" if not os.path.exists(dst) else ("igual" if mismo_contenido(src, dst) else "DISTINTO")
            print(f"  {estado:<8} {dst}")
        al_dia = settings_con_hooks(cfg, True) == cfg
        print(f"  hooks en settings.json: {'al día' if al_dia else 'FALTAN o difieren'}")
        return

    if args.desinstalar:
        for _, dst in COPIAS:
            if os.path.exists(dst) and (MARCA in dst.replace("\\", "/") or "cerrar-hito" in dst):
                os.remove(dst)
                print(f"  borrado {dst}")
        guardar_settings(settings_con_hooks(cfg, False))
        print("Hooks quitados de settings.json. Los subagentes de ~/.claude/agents/ se dejan (bórralos a mano si quieres).")
        return

    for src, dst in COPIAS:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  copiado {os.path.relpath(src, REPO)} → {dst}")
    nuevo = settings_con_hooks(cfg, True)
    if nuevo != cfg:
        guardar_settings(nuevo)
        print("  hooks registrados en settings.json")
    else:
        print("  settings.json ya estaba al día")
    print("Listo. Las sesiones nuevas (o reiniciadas) cargan el kit.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
