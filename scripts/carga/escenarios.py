# -*- coding: utf-8 -*-
"""Pruebas de carga LOCALES de FIN-SYS (estándar de consultas, hito H1 / P14).

Arranca SU PROPIO backend (uvicorn, puerto 8099) con un entorno limpio que
apunta al PgBouncer del laboratorio (localhost:56432) — nunca carga el .env
principal ni toca Supabase — y lanza escenarios con concurrencia creciente:
búsqueda del Diario con debounce, opciones, panel, terceros y una consulta
pesada (Análisis). Mide p50/p95/p99, códigos HTTP y goodput por escalón,
hasta pasar el punto de quiebre (objetivo: goodput plano cerca del 100 %).

    python scripts\\carga\\escenarios.py --solo-esquema          # crea las tablas (DDL de arranque)
    python scripts\\carga\\generar_holding.py --escala chica
    python scripts\\carga\\escenarios.py --escalones 5,20,60,120 --segundos 20
"""
import argparse
import json
import os
import random
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, AQUI)
from _seguro import exigir_local  # noqa: E402

PUERTO_API = 8099
SECRETO = "laboratorio-de-carga-no-es-produccion"


def entorno_lab(args) -> dict:
    exigir_local(args.db_host, args.db_puerto)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("DB_", "SUPABASE", "TELEGRAM"))}
    env.update(DB_HOST=args.db_host, DB_PORT=str(args.db_puerto), DB_NAME="finsys_carga",
               DB_USER="postgres", DB_PASSWORD="carga", SESSION_SECRET=SECRETO,
               FINSYS_ADMISION=args.admision, DASHBOARD_FAST="1", PYTHONIOENCODING="utf-8")
    return env


def arrancar_backend(args):
    cmd = [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1",
           "--port", str(PUERTO_API), "--workers", str(args.workers)]
    proc = subprocess.Popen(cmd, cwd=RAIZ, env=entorno_lab(args),
                            stdout=subprocess.DEVNULL if not args.ver_logs else None,
                            stderr=subprocess.STDOUT if not args.ver_logs else None)
    for _ in range(120):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PUERTO_API}/api/health/vida", timeout=1)
            return proc
        except Exception:
            time.sleep(1)
    proc.terminate()
    raise SystemExit("⛔ El backend del laboratorio no arrancó en 120 s (usa --ver-logs).")


def token() -> str:
    os.environ["SESSION_SECRET"] = SECRETO
    sys.path.insert(0, RAIZ)
    from routers.auth_guard import create_session_token
    return create_session_token({"id": "carga", "name": "Carga", "role": "admin", "is_superuser": True})


class Medidor:
    def __init__(self):
        self.lock = threading.Lock()
        self.lat = {}
        self.codigos = {}

    def anotar(self, nombre, ms, codigo):
        with self.lock:
            self.lat.setdefault(nombre, []).append(ms)
            self.codigos.setdefault(nombre, {}).setdefault(codigo, 0)
            self.codigos[nombre][codigo] += 1


def pedir(url, tok, medidor, nombre):
    t0 = time.perf_counter()
    codigo = 0
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
            codigo = r.status
    except urllib.error.HTTPError as e:
        codigo = e.code
    except Exception:
        codigo = -1                       # timeout o conexión rechazada
    medidor.anotar(nombre, (time.perf_counter() - t0) * 1000, codigo)


def escenario(base, empresa, terceros):
    """Una acción de un usuario simulado: (nombre, url)."""
    r = random.random()
    q = urllib.parse.quote
    if r < 0.45:
        texto = random.choice(["pago", "café", "nómina", "arriendo", "venta", "tercero 0", "transporte", "$150.000"])
        return "diario_busqueda", f"{base}/api/diario/movimientos?portfolio={q(empresa)}&q={q(texto)}"
    if r < 0.60:
        return "diario_filtros", (f"{base}/api/diario/movimientos?portfolio={q(empresa)}&tipos=GASTO"
                                  f"&terceros={random.choice(terceros)}&orden=monto_desc")
    if r < 0.70:
        return "diario_grupos", f"{base}/api/diario/movimientos?portfolio={q(empresa)}&agrupar=tercero&limit=0"
    if r < 0.80:
        return "diario_opciones", f"{base}/api/diario/opciones?portfolio={q(empresa)}"
    if r < 0.90:
        return "panel", f"{base}/api/dashboard-data?portfolio={q(empresa)}&limit=50&offset=0"
    if r < 0.97:
        return "terceros_catalogo", f"{base}/api/third-parties"
    return "analisis_dataset", f"{base}/api/analytics/dataset"


def correr_escalon(usuarios, segundos, base, tok, empresas, terceros, pausa_ms):
    medidor = Medidor()
    fin = time.time() + segundos

    def usuario():
        empresa = random.choice(empresas)
        while time.time() < fin:
            nombre, url = escenario(base, empresa, terceros)
            pedir(url, tok, medidor, nombre)
            time.sleep(pausa_ms / 1000.0 * random.uniform(0.5, 1.5))   # tiempo de "pensar"

    hilos = [threading.Thread(target=usuario, daemon=True) for _ in range(usuarios)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    return medidor


def pct(valores, p):
    if not valores:
        return 0.0
    v = sorted(valores)
    return v[min(len(v) - 1, int(round(p / 100.0 * (len(v) - 1))))]


def informe(usuarios, segundos, m: Medidor):
    total = sum(len(v) for v in m.lat.values())
    ok = sum(c.get(200, 0) for c in m.codigos.values())
    print(f"\n── {usuarios} usuarios · {segundos}s · {total} peticiones · goodput {ok / segundos:.1f} OK/s "
          f"({100.0 * ok / max(1, total):.0f} % OK)")
    print(f"   {'escenario':20} {'n':>6} {'p50':>7} {'p95':>7} {'p99':>7}  códigos")
    for nombre in sorted(m.lat):
        lat = m.lat[nombre]
        print(f"   {nombre:20} {len(lat):6d} {statistics.median(lat):6.0f}ms {pct(lat, 95):6.0f}ms "
              f"{pct(lat, 99):6.0f}ms  {json.dumps(m.codigos[nombre])}")
    return {"usuarios": usuarios, "total": total, "ok": ok,
            "p95": {n: pct(v, 95) for n, v in m.lat.items()}, "codigos": m.codigos}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db-host", default="localhost")
    ap.add_argument("--db-puerto", default="56432", help="PgBouncer del laboratorio (modo transacción)")
    ap.add_argument("--workers", type=int, default=2, help="como producción (gunicorn 2 workers)")
    ap.add_argument("--escalones", default="5,20,60,120")
    ap.add_argument("--segundos", type=int, default=20)
    ap.add_argument("--pausa-ms", type=int, default=300, help="tiempo de pensar entre acciones")
    ap.add_argument("--admision", default="registrar", choices=["registrar", "activo", "apagado"])
    ap.add_argument("--solo-esquema", action="store_true", help="arranca el backend (DDL) y sale")
    ap.add_argument("--ver-logs", action="store_true")
    ap.add_argument("--salida", default=os.path.join(AQUI, "resultado_carga.json"))
    args = ap.parse_args()

    proc = arrancar_backend(args)
    try:
        if args.solo_esquema:
            print("✅ Esquema creado en la BD del laboratorio (DDL de arranque).")
            return
        base = f"http://127.0.0.1:{PUERTO_API}"
        tok = token()
        req = urllib.request.Request(f"{base}/api/portfolios", headers={"Authorization": f"Bearer {tok}"})
        empresas = [p["name"] for p in json.load(urllib.request.urlopen(req, timeout=30))
                    if p["name"].startswith("CARGA EMPRESA")]
        if not empresas:
            raise SystemExit("⛔ No hay datos: corre antes scripts\\carga\\generar_holding.py")
        req = urllib.request.Request(f"{base}/api/diario/opciones?portfolio={urllib.parse.quote(empresas[0])}",
                                     headers={"Authorization": f"Bearer {tok}"})
        terceros = [t["id"] for t in json.load(urllib.request.urlopen(req, timeout=60))["terceros"][:500]] or [1]
        resultados = []
        for u in [int(x) for x in args.escalones.split(",")]:
            resultados.append(informe(u, args.segundos,
                                      correr_escalon(u, args.segundos, base, tok, empresas, terceros, args.pausa_ms)))
        with open(args.salida, "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=1)
        print(f"\n📄 Resultado en {args.salida}")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
