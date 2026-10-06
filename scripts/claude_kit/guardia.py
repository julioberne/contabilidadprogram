"""Hook PreToolUse del kit de sesión de FIN-SYS: la «guardia» (docs/guia-trabajo-claude.md §9).

Convierte en bloqueos reales las reglas de CLAUDE.md §6 que antes eran solo texto:
- deny: `git push` y `scripts\\publicar.*` (los corre Andrés), `session_maintenance.py` sin
  `--check`, `bot_telegram.py` (token compartido con producción), scripts de migración, SQL de
  escritura ejecutado contra la BD, leer o tocar `.env`, la API de Dokploy fuera de
  `scratch/deploy_prod.py`.
- ask: editar `fin_sys_core/database_driver.py` o `control_tower_driver.py` (permiso explícito).
Cada decisión queda en `scratch/guardia.log` del checkout principal.

Límites (propios de los hooks): actúa por llamada de herramienta, así que un .py escrito y luego
ejecutado puede esquivarla; si este script falla, la acción sigue (falla abierta). Solo actúa
dentro de contabilidadprogram. Usa solo la biblioteca estándar.
"""
import json
import os
import re
import sys
import time

PROYECTO = "contabilidadprogram"

MOTIVOS = {
    "push": "El push lo hace Andrés con scripts\\publicar.cmd en su terminal. Deja el trabajo commiteado y avísale.",
    "publicar": "scripts\\publicar.cmd (push + CI + deploy) lo corre Andrés, no Claude.",
    "mantenimiento": "session_maintenance.py solo con --check: sin argumentos borra en la BD compartida con producción.",
    "bot": "No lances el poller en local: el token de Telegram es el mismo de producción (chocaría con 409).",
    "migracion": "Las migraciones escriben en la BD de producción: prepárale el comando a Andrés para que la corra él.",
    "sql": "SQL de escritura contra la BD (es la de producción): pásale el SQL a Andrés en vez de ejecutarlo.",
    "env": ".env tiene los secretos de producción: no se lee ni se toca (usa .env.production.example para los nombres).",
    "dokploy": "El deploy solo se hace con scratch\\deploy_prod.py (o publicar.cmd de Andrés), no llamando a la API de Dokploy.",
    "driver": "Este archivo necesita permiso explícito de Andrés antes de editarlo (CLAUDE.md §6).",
}

SEPARADORES = re.compile(r"&&|\|\||[;|\n]")
SQL_ESCRITURA = re.compile(
    r"\b(INSERT\s+INTO|UPDATE\s+[\w.\"]+\s+SET|DELETE\s+FROM|DROP\s+(TABLE|SCHEMA|DATABASE|INDEX|VIEW|FUNCTION)"
    r"|TRUNCATE\b|ALTER\s+TABLE|CREATE\s+(TABLE|SCHEMA))", re.I)
EJECUTOR_SQL = re.compile(r"\bpsql\b|psycopg|\.execute(many)?\s*\(", re.I)
HTTP = re.compile(r"\bcurl(\.exe)?\b|Invoke-(RestMethod|WebRequest)|\birm\b|\biwr\b|requests\.|httpx\.|urllib", re.I)
DOKPLOY = re.compile(r"dokploy|:3000/api|compose\.deploy", re.I)
ENV_NOMBRE = re.compile(r"^\.env(\.(local|production|development|prod|dev))?$", re.I)
SOLO_MIRAR = {"ls", "dir", "test", "test-path", "git", "stat", "where", "which"}
DRIVERS = ("fin_sys_core/database_driver.py", "fin_sys_core/control_tower_driver.py")


def _tokens(segmento):
    return [t for t in re.split(r"\s+", segmento.replace('"', " ").replace("'", " ").strip()) if t]


def _base(token):
    return token.replace("\\", "/").rstrip("/").split("/")[-1]


HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?")


def _sin_heredocs(comando):
    """Quita el cuerpo de los heredocs (`<<'EOF' ... EOF`) y here-strings de PowerShell (@' ... '@):
    ahí van mensajes de commit y documentos, que mencionan cosas sin ejecutarlas."""
    salida, fin = [], None
    for linea in comando.splitlines():
        if fin is not None:
            if linea.strip() == fin:
                fin = None
            continue
        salida.append(linea)
        m = HEREDOC.search(linea)
        if m:
            fin = m.group(1)
        elif re.search(r"@['\"]\s*$", linea):
            fin = "'@" if linea.rstrip().endswith("@'") else '"@'
    return "\n".join(salida)


def _es_git_push(toks):
    for i, t in enumerate(toks):
        if _base(t).lower() not in ("git", "git.exe"):
            continue
        if not all(_base(p).lower() in LANZADORES or p.startswith("-") for p in toks[:i]):
            continue  # "git" dentro de un texto (p. ej. un mensaje de commit), no en posición de comando
        j = i + 1
        while j < len(toks) and toks[j].startswith("-"):
            j += 2 if toks[j] in ("-C", "-c", "--git-dir", "--work-tree") else 1
        if j < len(toks) and toks[j].lower() == "push":
            return True
    return False


LANZADORES = {"python", "python.exe", "python3", "py", "py.exe", "&", "cmd", "cmd.exe", "/c", "call", "start",
              "powershell", "powershell.exe", "pwsh", "uv", "run"}


def _ejecuta(toks, patron):
    """True si el segmento EJECUTA un script cuyo nombre cumple `patron`: en posición de comando
    (primera palabra) o detrás solo de lanzadores y opciones (`python -u x.py`, `& "x.cmd"`, `cmd /c x.cmd`).
    Mencionarlo como argumento (`grep -n publicar.cmd`) no cuenta."""
    for i, t in enumerate(toks):
        if re.fullmatch(patron, _base(t), re.I):
            return all(_base(p).lower() in LANZADORES or p.startswith("-") for p in toks[:i])
    return False


def _ejecuta_modulo(toks, modulo):
    """`python -m paquete.modulo`."""
    return any(toks[i] == "-m" and toks[i + 1] == modulo for i in range(len(toks) - 1))


def decidir_comando(comando):
    if not comando:
        return None
    if HTTP.search(comando) and DOKPLOY.search(comando) and "deploy_prod.py" not in comando:
        return "deny", MOTIVOS["dokploy"]
    for linea in comando.splitlines():  # el SQL sí se busca también dentro de los heredocs (python - <<'PY')
        if SQL_ESCRITURA.search(linea) and EJECUTOR_SQL.search(linea):
            return "deny", MOTIVOS["sql"]
    for segmento in SEPARADORES.split(_sin_heredocs(comando)):
        toks = _tokens(segmento)
        if not toks:
            continue
        if _es_git_push(toks):
            return "deny", MOTIVOS["push"]
        if _ejecuta(toks, r"publicar\.(cmd|py)"):
            return "deny", MOTIVOS["publicar"]
        if _ejecuta(toks, r"session_maintenance\.py") and "--check" not in toks:
            return "deny", MOTIVOS["mantenimiento"]
        if _ejecuta(toks, r"bot_telegram\.py") or _ejecuta_modulo(toks, "fin_sys_core.bot_telegram"):
            return "deny", MOTIVOS["bot"]
        if _ejecuta(toks, r"migrate_\w+\.py"):
            return "deny", MOTIVOS["migracion"]
        if _base(toks[0]).lower() not in SOLO_MIRAR and any(ENV_NOMBRE.match(_base(t)) for t in toks):
            return "deny", MOTIVOS["env"]
    return None


def decidir(datos):
    """('deny'|'ask', motivo) o None para dejar pasar. Función pura: la usan los tests."""
    cwd = (datos.get("cwd") or "").lower()
    if PROYECTO not in cwd:
        return None
    herramienta = datos.get("tool_name", "")
    entrada = datos.get("tool_input") or {}
    if herramienta in ("Bash", "PowerShell"):
        return decidir_comando(entrada.get("command", ""))
    ruta = (entrada.get("file_path") or entrada.get("notebook_path") or "").replace("\\", "/")
    if not ruta:
        return None
    if ENV_NOMBRE.match(ruta.rsplit("/", 1)[-1]):
        return "deny", MOTIVOS["env"]
    if herramienta in ("Edit", "Write", "MultiEdit", "NotebookEdit") and ruta.lower().endswith(DRIVERS):
        return "ask", MOTIVOS["driver"]
    return None


def _registrar(cwd, datos, decision, motivo):
    partes = re.split(r"[\\/]", cwd)
    try:
        raiz = os.sep.join(partes[: [p.lower() for p in partes].index(PROYECTO) + 1])
    except ValueError:
        return
    entrada = datos.get("tool_input") or {}
    que = (entrada.get("command") or entrada.get("file_path") or "").replace("\n", " ")[:200]
    linea = f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{decision}\t{datos.get('tool_name')}\t{que}\t{motivo}\n"
    try:
        os.makedirs(os.path.join(raiz, "scratch"), exist_ok=True)
        with open(os.path.join(raiz, "scratch", "guardia.log"), "a", encoding="utf-8") as fh:
            fh.write(linea)
    except OSError:
        pass


def main():
    datos = json.load(sys.stdin)
    resultado = decidir(datos)
    if not resultado:
        return
    decision, motivo = resultado
    _registrar(datos.get("cwd") or "", datos, decision, motivo)
    salida = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                     "permissionDecisionReason": f"[guardia FIN-SYS] {motivo}"}}
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(salida, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # falla abierta: un hook roto no debe trabar la sesión
        pass
