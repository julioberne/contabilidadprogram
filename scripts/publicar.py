# -*- coding: utf-8 -*-
"""publicar.py — Publicar el trabajo de una sesión en un solo paso.

Nace del 06-oct-2026: con varias sesiones (worktrees) a la vez, "lo de
GitHub", "lo de producción" y "lo de :8000" quedaban desfasados porque el
push, el deploy y el sync eran tres comandos sueltos en tres carpetas.

Se corre desde la carpeta de la sesión (worktree) o desde la principal, con
la rama a publicar en uso:

  1) Revisa: nada sin commitear (salvo .claude/, que es local) y la rama al
     día con origin/master (si otra sesión publicó antes, para).
  2) Muestra los commits y pregunta "¿Publicar? (s/n)" — la aprobación.
  3) git push origin HEAD:master.
  4) Espera el CI de GitHub (gh). Si falla, NO despliega.
  5) Deploy: scratch/deploy_prod.py de la carpeta principal (DT-22 + dispara
     Dokploy) y, mientras Dokploy construye, pone :8000 al día
     (scripts/sync_local.py en la carpeta principal: ff + npm run build).
  6) Espera el deployment de Dokploy y sondea producción (/api/health y que
     el deployment sea el del último commit de master).

No mezcla ramas ajenas, no resuelve conflictos, no toca la BD ni corre
migraciones (eso sigue siendo manual y con OK de Andrés).

Uso (PowerShell, en la carpeta de la sesión):
  scripts\\publicar.cmd                # todo: push + CI + deploy + :8000
  scripts\\publicar.cmd --sin-deploy   # push + CI + :8000 (producción no se toca)
  scripts\\publicar.cmd --solo-sync    # solo :8000 al día con GitHub
  scripts\\publicar.cmd --simular      # revisa y muestra qué haría, sin cambiar nada
"""
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

PROD_URL = "https://finsys-andres.duckdns.org"
COMPOSE_ID = "Rj-fzTPLe3K2JQNoEqMPe"   # compose finsys-app en Dokploy (= scratch/deploy_prod.py)
ESPERA_CI_S = 20 * 60
ESPERA_DEPLOY_S = 20 * 60


def git(*args, cwd=None, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode != 0:
        parar(f"git {' '.join(args)} falló:\n{r.stderr.strip()}")
    return r


def correr(cmd, cwd):
    print(f"\n$ {' '.join(str(c) for c in cmd)}", flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=str(cwd)).returncode


def parar(msg):
    sys.exit(f"\n✖ {msg}")


def paso(msg):
    print(f"\n━━ {msg}", flush=True)


def preguntar(msg):
    try:
        return input(f"\n{msg} (s/n): ").strip().lower() in ("s", "si", "sí", "y")
    except EOFError:
        return False


# ── Dokploy (token en scratch/dokploy.env de la carpeta principal; nunca se copia) ──
def dokploy(principal, ruta):
    cfg = {}
    with open(principal / "scratch" / "dokploy.env", encoding="utf-8-sig") as fh:
        for linea in fh:
            if "=" in linea:
                k, v = linea.strip().split("=", 1)
                cfg[k] = v
    req = urllib.request.Request(f"{cfg['DOKPLOY_URL']}/api/{ruta}", headers={"x-api-key": cfg["DOKPLOY_TOKEN"]})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())


def ultimo_deployment(principal):
    lista = dokploy(principal, f"deployment.allByCompose?composeId={COMPOSE_ID}")
    return max(lista, key=lambda d: d.get("createdAt") or "") if lista else None


# ── CI de GitHub ──
def esperar_ci(sha):
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        print("⚠ No encuentro `gh` (GitHub CLI): no puedo esperar el CI.")
        return preguntar("¿Seguir sin esperar el CI?")
    limite = time.time() + 180
    run = None
    while time.time() < limite:
        r = subprocess.run(["gh", "run", "list", "--commit", sha, "--json", "databaseId,status,conclusion,workflowName"],
                           capture_output=True, text=True, encoding="utf-8")
        runs = json.loads(r.stdout or "[]") if r.returncode == 0 else []
        if runs:
            run = runs[0]
            break
        print("… esperando que GitHub arranque el CI", flush=True)
        time.sleep(10)
    if not run:
        print("⚠ GitHub no mostró un CI para este commit en 3 minutos.")
        return preguntar("¿Seguir sin el CI?")
    if run["status"] == "completed":
        ok = run["conclusion"] == "success"
    else:
        print(f"CI «{run['workflowName']}» en curso (run {run['databaseId']})…", flush=True)
        ok = subprocess.run(["gh", "run", "watch", str(run["databaseId"]), "--exit-status", "--interval", "15"],
                            timeout=ESPERA_CI_S).returncode == 0
    if not ok:
        parar(f"El CI falló: no se despliega. Detalle: gh run view {run['databaseId']} --log-failed")
    print("✔ CI en verde")
    return True


# ── Pasos ──
def sync_local(principal):
    paso("Poniendo :8000 al día (carpeta principal)")
    py = principal / ".venv" / "Scripts" / "python.exe"
    if correr([py, principal / "scripts" / "sync_local.py"], principal) != 0:
        print("⚠ El sync de :8000 no terminó (mira el mensaje de arriba). GitHub y producción no se afectan.")
        return False
    return True


def deploy(principal):
    paso("Desplegando a producción")
    antes = ultimo_deployment(principal)
    antes_ts = (antes or {}).get("createdAt") or ""
    py = principal / ".venv" / "Scripts" / "python.exe"
    if correr([py, principal / "scratch" / "deploy_prod.py"], principal / "scratch") != 0:
        parar("deploy_prod.py falló: producción no se tocó.")
    return antes_ts


def esperar_deploy(principal, antes_ts, asunto_master):
    paso("Esperando a Dokploy")
    limite = time.time() + ESPERA_DEPLOY_S
    visto = None
    while time.time() < limite:
        try:
            d = ultimo_deployment(principal)
        except (urllib.error.URLError, OSError) as e:
            print(f"… Dokploy no respondió ({e}); reintento", flush=True)
            time.sleep(15)
            continue
        if d and (d.get("createdAt") or "") > antes_ts:
            if d.get("status") != visto:
                visto = d.get("status")
                print(f"[{dt.datetime.now():%H:%M:%S}] {visto} — {(d.get('title') or '')[:70]}", flush=True)
            if visto == "done":
                return d
            if visto == "error":
                parar(f"El deploy falló en Dokploy: {d.get('errorMessage') or 'ver panel :3000 → finsys-app → Deployments'}")
        time.sleep(15)
    parar("Dokploy no terminó en 20 minutos: revisa el panel :3000 → finsys-app → Deployments.")


def sondear(deployment, asunto_master):
    paso("Sonda de producción")
    titulo = (deployment.get("title") or "").strip()
    if titulo and asunto_master.startswith(titulo[:40]):
        print(f"✔ Dokploy desplegó el último commit de master: «{asunto_master[:70]}»")
    else:
        print(f"⚠ El deployment dice «{titulo[:70]}» y master es «{asunto_master[:70]}»")
    for intento in range(12):
        try:
            with urllib.request.urlopen(f"{PROD_URL}/api/health", timeout=20) as r:
                salud = json.loads(r.read().decode())
            if salud.get("status") == "ok":
                print(f"✔ {PROD_URL}/api/health → ok (BD {salud.get('db')})")
                return True
        except (urllib.error.URLError, OSError, ValueError):
            pass
        time.sleep(10)
    print("⚠ /api/health no respondió ok en 2 minutos: revisa el panel de Dokploy.")
    return False


def main():
    ap = argparse.ArgumentParser(description="Publicar el trabajo de la sesión: push + CI + deploy + :8000")
    modo = ap.add_mutually_exclusive_group()
    modo.add_argument("--sin-deploy", action="store_true", help="push + CI + :8000, sin tocar producción")
    modo.add_argument("--solo-sync", action="store_true", help="solo poner :8000 al día con GitHub")
    ap.add_argument("--simular", action="store_true", help="revisar y mostrar qué haría, sin cambiar nada")
    a = ap.parse_args()

    aqui = pathlib.Path(git("rev-parse", "--show-toplevel").stdout.strip())
    principal = pathlib.Path(git("rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()).parent
    rama = git("rev-parse", "--abbrev-ref", "HEAD", cwd=aqui).stdout.strip()

    if a.solo_sync:
        if a.simular:
            print(f"Simulación: correría scripts/sync_local.py en {principal}")
            return
        sync_local(principal)
        print("\n✔ Listo. Ctrl+Shift+R en la pestaña de :8000.")
        return

    paso(f"Revisando la sesión  ·  carpeta {aqui}  ·  rama {rama}")
    if rama == "HEAD":
        parar("La carpeta no está en una rama (HEAD suelto): no hay qué publicar.")
    sucio = [l for l in git("status", "--porcelain", cwd=aqui).stdout.splitlines() if l[3:].strip('"').split("/")[0] != ".claude"]
    sin_commit = [l for l in sucio if not l.startswith("??")]
    if sin_commit:
        parar("Hay cambios sin commitear (no se publicarían):\n  " + "\n  ".join(sin_commit)
              + "\nPídele a la sesión que los commitee (o los descarte) y vuelve a correr publicar.")
    nuevos = [l for l in sucio if l.startswith("??")]
    if nuevos:
        print("⚠ Archivos nuevos sin agregar a git (NO se publican):\n  " + "\n  ".join(nuevos))

    git("fetch", "origin", cwd=aqui)
    if git("merge-base", "--is-ancestor", "origin/master", "HEAD", cwd=aqui, check=False).returncode != 0:
        parar("La rama está atrasada: otra sesión publicó en master después.\n"
              "Pídele a esta sesión «actualiza la rama sobre origin/master» y vuelve a correr publicar.")
    commits = git("log", "--oneline", "origin/master..HEAD", cwd=aqui).stdout.strip().splitlines()

    print(f"\nCommits a publicar en master: {len(commits) or 'ninguno (master ya los tiene)'}")
    for c in commits:
        print(f"  {c[:110]}")
    pasos = (["push a master"] if commits else []) + ["esperar el CI"] \
        + ([] if a.sin_deploy else ["deploy a producción + sonda"]) + [":8000 al día"]
    print("Pasos: " + " → ".join(pasos))
    if a.simular:
        print("\nSimulación: no se cambió nada.")
        return
    if not preguntar("¿Publicar?"):
        parar("Cancelado: no se hizo nada.")

    if commits:
        paso("Push a master")
        if correr(["git", "push", "origin", "HEAD:master"], aqui) != 0:
            parar("El push falló (¿otra sesión publicó justo ahora?). Nada más se hizo.")
    git("fetch", "origin", cwd=aqui)
    sha = git("rev-parse", "origin/master", cwd=aqui).stdout.strip()
    asunto = git("log", "-1", "--format=%s", "origin/master", cwd=aqui).stdout.strip()

    paso(f"CI de GitHub para {sha[:7]}")
    esperar_ci(sha)

    sondeo_ok = True
    if not a.sin_deploy:
        antes_ts = deploy(principal)
        sync_ok = sync_local(principal)          # mientras Dokploy construye
        d = esperar_deploy(principal, antes_ts, asunto)
        sondeo_ok = sondear(d, asunto)
    else:
        sync_ok = sync_local(principal)

    paso("Resumen")
    print(f"  GitHub master : {sha[:7]} «{asunto[:70]}»")
    if not a.sin_deploy:
        print(f"  Producción    : {'✔' if sondeo_ok else '⚠'} {PROD_URL}")
    print(f"  Local :8000   : {'✔ al día — Ctrl+Shift+R en la pestaña' if sync_ok else '⚠ sin sincronizar (ver arriba)'}")


if __name__ == "__main__":
    main()
