# -*- coding: utf-8 -*-
"""Carga ACOTADA y SOLO LECTURA contra un backend real (laboratorio, criterios 1, 2, 3 y 5).

La BD es la de producción, así que esta carga tiene freno de mano:
- Solo GET (nunca POST/PUT/DELETE): no escribe nada.
- Tope duro de 20 usuarios virtuales y 60 s por escalón.
- Freno automático: se detiene si el p95 pasa de 1,5 s, si los errores pasan
  del 2 % o si el pool del worker pasa del 70 % (/api/health/profundo).
- Por defecto solo fuera de horario (21:00–07:00 hora local); --ahora lo salta.

Mide por endpoint: p50/p95/p99, códigos HTTP, KB por respuesta (detecta
"descarga el catálogo entero") y el goodput (respuestas OK por segundo).

    python scripts/laboratorio/carga_acotada.py                       # backend local :8003
    python scripts/laboratorio/carga_acotada.py --url https://finsys-andres.duckdns.org  (necesita LAB_TOKEN)
"""
import argparse
import json
import os
import random
import statistics
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)

TOPE_USUARIOS = 20
TOPE_SEGUNDOS = 60
FRENO_P95_MS = 1500
FRENO_ERRORES = 0.02
FRENO_POOL = 0.70
HORARIO_LIBRE = (21, 7)          # 21:00 → 07:00

# (nombre, peso, plantilla de ruta). {e} = empresa, {t} = un tercero, {q} = búsqueda
ESCENARIOS = [
    ("diario_busqueda", 30, "/api/diario/movimientos?portfolio={e}&q={q}"),
    ("diario_filtros", 15, "/api/diario/movimientos?portfolio={e}&tipos=GASTO&terceros={t}&orden=monto_desc"),
    ("diario_grupos", 8, "/api/diario/movimientos?portfolio={e}&agrupar=tercero&limit=0"),
    ("diario_opciones", 8, "/api/diario/opciones?portfolio={e}"),
    ("panel", 12, "/api/dashboard-data?portfolio={e}&limit=50&offset=0"),
    ("panel_saldos", 6, "/api/dashboard-data/balance?portfolio={e}"),
    # 16-oct (tras H3): la web y la Mini App ya buscan en el servidor; el catálogo
    # completo solo lo piden los widgets de colegio, y queda para la proyección.
    ("buscar_terceros", 8, "/api/buscar/terceros?q={q}&limite=8"),
    ("buscar_terceros_vacio", 3, "/api/buscar/terceros?limite=8"),
    ("terceros_catalogo", 2, "/api/third-parties"),
    ("etiquetas", 4, "/api/tags"),
    ("portafolios", 4, "/api/portfolios"),
    ("rrhh_resumen", 3, "/api/hr/employees/summary"),
    ("compendios", 2, "/api/compendios"),
    ("libro_mayor", 3, "/api/contadores/reportes/balance-prueba"),
    ("analisis_dataset", 2, "/api/analytics/dataset"),
]
INTERACTIVOS = ("diario_busqueda", "diario_filtros", "diario_opciones", "panel", "panel_saldos",
                "etiquetas", "portafolios", "buscar_terceros", "buscar_terceros_vacio", "rrhh_resumen")
BUSQUEDAS = ["pago", "café", "nómina", "arriendo", "venta", "transporte", "$50.000", "ecci", "obra", "efectivo"]


def en_horario_libre(ahora: Optional[datetime] = None) -> bool:
    h = (ahora or datetime.now()).hour
    ini, fin = HORARIO_LIBRE
    return h >= ini or h < fin


def acotar(usuarios: List[int], segundos: int):
    """Aplica los topes duros (no negociables por argumento)."""
    return [max(1, min(u, TOPE_USUARIOS)) for u in usuarios], max(5, min(segundos, TOPE_SEGUNDOS))


def percentil(valores: List[float], p: float) -> float:
    if not valores:
        return 0.0
    v = sorted(valores)
    return v[min(len(v) - 1, int(round(p / 100.0 * (len(v) - 1))))]


def pausas_globales(ventana: List[tuple], lenta_ms: float = 3000, juntas_s: float = 1.5) -> List[dict]:
    """Varias peticiones LENTAS que terminan casi a la vez = la BD o la red se
    detuvieron para todo el proceso (no es culpa de un endpoint). Pura.
    ventana: [(t_fin, ms, código, nombre)]."""
    lentas = sorted((x for x in ventana if x[1] >= lenta_ms), key=lambda x: x[0])
    grupos, actual = [], []
    for x in lentas:
        if actual and x[0] - actual[-1][0] > juntas_s:
            grupos.append(actual)
            actual = []
        actual.append(x)
    if actual:
        grupos.append(actual)
    return [{"n": len(g), "ms_medio": round(sum(x[1] for x in g) / len(g)),
             "endpoints": sorted({x[3] for x in g})}
            for g in grupos if len(g) >= 2 and len({x[3] for x in g}) >= 2]


def debe_frenar(latencias: List[float], codigos: List[int], pool_uso: Optional[float]) -> Optional[str]:
    """Motivo para detener la carga, o None. Pura (se prueba en tests)."""
    if len(latencias) >= 20 and percentil(latencias, 95) > FRENO_P95_MS:
        return f"p95 {percentil(latencias, 95):.0f} ms > {FRENO_P95_MS} ms"
    if len(codigos) >= 20:
        errores = sum(1 for c in codigos if c >= 500 or c < 0)
        if errores / len(codigos) > FRENO_ERRORES:
            return f"errores {100.0 * errores / len(codigos):.1f} % > {100 * FRENO_ERRORES:.0f} %"
    if pool_uso is not None and pool_uso > FRENO_POOL:
        return f"pool al {100 * pool_uso:.0f} % > {100 * FRENO_POOL:.0f} %"
    return None


class Registro:
    def __init__(self):
        self.lock = threading.Lock()
        self.por_nombre: Dict[str, Dict[str, list]] = {}
        self.ventana: List[tuple] = []          # (t, ms, código) para el freno

    def anotar(self, nombre, ms, codigo, bytes_):
        with self.lock:
            d = self.por_nombre.setdefault(nombre, {"ms": [], "codigos": [], "bytes": []})
            d["ms"].append(ms)
            d["codigos"].append(codigo)
            d["bytes"].append(bytes_)
            self.ventana.append((time.time(), ms, codigo, nombre))

    def ultimos(self, segundos=5):
        lim = time.time() - segundos
        with self.lock:
            v = [x for x in self.ventana if x[0] >= lim]
        return [x[1] for x in v], [x[2] for x in v]

    def todo(self):
        with self.lock:
            return list(self.ventana)


def _get(base, ruta, token, timeout=30):
    req = urllib.request.Request(base + ruta, headers={"Authorization": f"Bearer {token}"}, method="GET")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            cuerpo = r.read()
            return (time.perf_counter() - t0) * 1000, r.status, len(cuerpo), cuerpo
    except urllib.error.HTTPError as e:
        return (time.perf_counter() - t0) * 1000, e.code, 0, b""
    except Exception:
        return (time.perf_counter() - t0) * 1000, -1, 0, b""


def token_local() -> str:
    """Solo para un backend LOCAL que usa el mismo .env (mismo secreto de sesión)."""
    from routers.auth_guard import create_session_token
    return create_session_token({"id": "laboratorio", "name": "Laboratorio", "role": "admin", "is_superuser": True})


def pool_uso(base) -> Optional[float]:
    try:
        with urllib.request.urlopen(base + "/api/health/profundo", timeout=5) as r:
            p = json.load(r).get("pool") or {}
        maxc = p.get("maxconn") or 0
        return (p.get("used") or 0) / maxc if maxc else None
    except Exception:
        return None


def contexto(base, token):
    _, c, _, cuerpo = _get(base, "/api/portfolios", token)
    if c != 200:
        raise SystemExit(f"⛔ /api/portfolios respondió {c}: ¿token válido para ese backend?")
    empresas = [p["name"] for p in json.loads(cuerpo)]
    terceros = {}
    for e in empresas[:5]:
        _, c, _, cuerpo = _get(base, f"/api/diario/opciones?portfolio={urllib.parse.quote(e)}", token)
        if c == 200:
            terceros[e] = [t["id"] for t in json.loads(cuerpo).get("terceros", [])][:200]
    return empresas, terceros


def correr(base, token, usuarios_escalones, segundos, pausa_ms, empresas, terceros):
    nombres, pesos = zip(*[(n, w) for n, w, _ in ESCENARIOS])
    plantillas = {n: r for n, _, r in ESCENARIOS}
    escalones, frenado = [], None
    for usuarios in usuarios_escalones:
        reg, fin, parar = Registro(), time.time() + segundos, threading.Event()

        def usuario():
            e = random.choice(empresas)
            ts = terceros.get(e) or [0]
            while time.time() < fin and not parar.is_set():
                n = random.choices(nombres, pesos)[0]
                ruta = plantillas[n].format(e=urllib.parse.quote(e), t=random.choice(ts),
                                            q=urllib.parse.quote(random.choice(BUSQUEDAS)))
                ms, codigo, b, _ = _get(base, ruta, token)
                reg.anotar(n, ms, codigo, b)
                time.sleep(pausa_ms / 1000.0 * random.uniform(0.5, 1.5))

        hilos = [threading.Thread(target=usuario, daemon=True) for _ in range(usuarios)]
        t0 = time.time()
        [h.start() for h in hilos]
        while any(h.is_alive() for h in hilos):
            time.sleep(3)
            lat, cods = reg.ultimos(5)
            motivo = debe_frenar(lat, cods, pool_uso(base))
            if motivo:
                frenado = f"{usuarios} usuarios: {motivo}"
                parar.set()
        [h.join() for h in hilos]
        escalones.append(resumir(usuarios, time.time() - t0, reg))
        if frenado:
            break
    return escalones, frenado


def resumir(usuarios, duracion, reg: Registro) -> dict:
    por = {}
    total = ok = 0
    for n, d in reg.por_nombre.items():
        total += len(d["ms"])
        ok += sum(1 for c in d["codigos"] if 200 <= c < 300)
        por[n] = {"n": len(d["ms"]), "p50_ms": round(statistics.median(d["ms"]), 1),
                  "p95_ms": round(percentil(d["ms"], 95), 1), "p99_ms": round(percentil(d["ms"], 99), 1),
                  "kb_medio": round(statistics.mean(d["bytes"]) / 1024, 1) if d["bytes"] else 0,
                  "codigos": {str(c): d["codigos"].count(c) for c in set(d["codigos"])}}
    interactivos = [ms for n, d in reg.por_nombre.items() if n in INTERACTIVOS for ms in d["ms"]]
    return {"usuarios": usuarios, "segundos": round(duracion, 1), "peticiones": total,
            "p95_interactivo_ms": round(percentil(interactivos, 95), 1), "n_interactivo": len(interactivos),
            "pausas_globales": pausas_globales(reg.todo()),
            "goodput_ok_s": round(ok / max(duracion, 0.001), 2),
            "ok_pct": round(100.0 * ok / max(total, 1), 1), "endpoints": por}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8003")
    ap.add_argument("--escalones", default="1,3,5,10")
    ap.add_argument("--segundos", type=int, default=20)
    ap.add_argument("--pausa-ms", type=int, default=800, help="tiempo de pensar entre acciones")
    ap.add_argument("--ahora", action="store_true", help="correr aunque sea horario laboral")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if not args.ahora and not en_horario_libre():
        raise SystemExit("⛔ Horario laboral: la BD es la de producción. Corre entre 21:00 y 07:00 o usa --ahora.")
    base = args.url.rstrip("/")
    local = base.startswith(("http://127.0.0.1", "http://localhost"))
    token = os.environ.get("LAB_TOKEN") or (token_local() if local else None)
    if not token:
        raise SystemExit("⛔ Para un backend remoto define LAB_TOKEN (token de una sesión tuya).")
    usuarios, segundos = acotar([int(x) for x in args.escalones.split(",")], args.segundos)
    empresas, terceros = contexto(base, token)
    escalones, frenado = correr(base, token, usuarios, segundos, args.pausa_ms, empresas, terceros)
    resultado = {"url": base, "fecha": datetime.now().isoformat(timespec="seconds"),
                 "escalones": escalones, "frenado": frenado,
                 "topes": {"usuarios": TOPE_USUARIOS, "segundos": TOPE_SEGUNDOS, "p95_ms": FRENO_P95_MS,
                           "errores": FRENO_ERRORES, "pool": FRENO_POOL}}
    if args.json:
        print(json.dumps(resultado, ensure_ascii=False))
        return 0
    for e in escalones:
        print(f"\n── {e['usuarios']} usuarios · {e['segundos']}s · {e['peticiones']} peticiones · "
              f"goodput {e['goodput_ok_s']} OK/s · {e['ok_pct']} % OK")
        for n, d in sorted(e["endpoints"].items()):
            print(f"   {n:20} n={d['n']:4} p50={d['p50_ms']:7} p95={d['p95_ms']:7} KB={d['kb_medio']:8} {d['codigos']}")
    if frenado:
        print(f"\n🛑 Freno automático: {frenado}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
