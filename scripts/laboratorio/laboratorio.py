# -*- coding: utf-8 -*-
"""Laboratorio de rendimiento y escalabilidad de FIN-SYS — orquestador.

Corre los criterios del laboratorio, aplica los umbrales del estándar de
consultas (docs/estandar-consultas-escalables.md) y escribe un informe con
veredicto OK / ALERTA / CRÍTICO por criterio, más el historial para ver la
tendencia entre corridas.

  1. Latencia por endpoint        (carga_acotada.py, opcional --carga)
  2. Capacidad y errores          (carga_acotada.py)
  3. Pool y conexiones            (/api/health/profundo + observatorio)
  4. Base de datos                (observatorio_bd.py, solo lectura)
  5. Carga útil (KB)              (carga_acotada.py)
  6. Auditoría del código         (auditoria_codigo.py, trinquete)
  +  Proyección de capacidad      (proyeccion.py, modelo con supuestos)

Todo es SOLO LECTURA contra la BD compartida con producción.

    python scripts/laboratorio/laboratorio.py                      # auditoría + BD + proyección
    python scripts/laboratorio/laboratorio.py --carga               # + carga acotada (fuera de horario)
    python scripts/laboratorio/laboratorio.py --carga --url https://finsys-andres.duckdns.org  (LAB_TOKEN)
    python scripts/laboratorio/laboratorio.py --sin-bd              # solo auditoría (como en el CI)
"""
import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Optional

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, AQUI)
sys.path.insert(0, RAIZ)

import auditoria_codigo as auditoria  # noqa: E402
import proyeccion  # noqa: E402

DIR_INFORMES = os.path.join(RAIZ, "docs", "laboratorio")
HISTORIAL = os.path.join(DIR_INFORMES, "historial.jsonl")

# Umbrales (estándar de consultas). Interactivo = búsqueda, filtros, panel.
INTERACTIVOS = ("diario_busqueda", "diario_filtros", "diario_opciones", "panel", "panel_saldos",
                "etiquetas", "portafolios")
CATALOGOS = ("terceros_catalogo", "analisis_dataset")
U = {"p95_ok": 300, "p95_alerta": 1000, "errores_ok": 1.0, "errores_alerta": 5.0,
     "pool_ok": 0.70, "conexiones_ok": 0.70, "cache_ok": 99.0,
     "usuarios_500k_ok": 200, "usuarios_500k_alerta": 50, "tabla_grande": 10_000}

OK, ALERTA, CRITICO, SIN_DATO = "OK", "ALERTA", "CRÍTICO", "SIN DATO"


def _peor(*estados):
    for e in (CRITICO, ALERTA, OK):
        if e in estados:
            return e
    return SIN_DATO


def evaluar(d: dict) -> List[dict]:
    """Veredicto por criterio. Pura: recibe todo lo medido y devuelve filas."""
    filas = []
    carga = d.get("carga")
    base_ms = d.get("latencia_base_ms") or 0

    # 1. Latencia
    if carga and carga.get("escalones"):
        ult = carga["escalones"][-1]
        p95s = {n: x["p95_ms"] for n, x in ult["endpoints"].items() if n in INTERACTIVOS and x.get("n", 0) >= 3}
        p95_todo = ult.get("p95_interactivo_ms")
        if p95_todo is not None and ult.get("n_interactivo", 0) >= 5:
            neto = max(0.0, p95_todo - base_ms)
            est = OK if neto <= U["p95_ok"] else (ALERTA if neto <= U["p95_alerta"] else CRITICO)
            peor = f"; el más lento: {max(p95s, key=p95s.get)} ({max(p95s.values()):.0f} ms)" if p95s else ""
            filas.append({"criterio": "1. Latencia interactiva (p95 neto)", "estado": est,
                          "detalle": f"p95 {p95_todo:.0f} ms − red {base_ms:.0f} ms = {neto:.0f} ms con "
                                     f"{ult['usuarios']} usuarios ({ult['n_interactivo']} muestras){peor}",
                          "accion": "Revisar el plan de esa consulta en el observatorio (criterio 4)."})
        else:
            filas.append({"criterio": "1. Latencia interactiva (p95 neto)", "estado": SIN_DATO,
                          "detalle": "pocas muestras (sube --segundos o los escalones)", "accion": ""})
    else:
        filas.append({"criterio": "1. Latencia interactiva (p95 neto)", "estado": SIN_DATO,
                      "detalle": "sin carga (usa --carga)", "accion": ""})

    # 2. Capacidad y errores
    if carga and carga.get("escalones"):
        ult = carga["escalones"][-1]
        err = 100.0 - ult["ok_pct"]
        est = OK if err <= U["errores_ok"] else (ALERTA if err <= U["errores_alerta"] else CRITICO)
        if carga.get("frenado"):
            est = _peor(est, ALERTA)
        pausas = [p for e in carga["escalones"] for p in e.get("pausas_globales", [])]
        if pausas:
            est = _peor(est, ALERTA)
        txt_pausas = ("; PAUSA GLOBAL: " + ", ".join(f"{p['n']} peticiones de {len(p['endpoints'])} endpoints "
                                                       f"~{p['ms_medio'] / 1000:.1f} s a la vez" for p in pausas[:2])) if pausas else ""
        filas.append({"criterio": "2. Capacidad y errores", "estado": est,
                      "detalle": f"goodput {ult['goodput_ok_s']} OK/s con {ult['usuarios']} usuarios; "
                                 f"{err:.1f} % no-OK" + (f"; freno: {carga['frenado']}" if carga.get("frenado") else "") + txt_pausas,
                      "accion": "Si frenó por pool: H2 (pool que espera). Si por p95: índices/forma de consulta."})
    else:
        filas.append({"criterio": "2. Capacidad y errores", "estado": SIN_DATO, "detalle": "sin carga", "accion": ""})

    # 3. Pool y conexiones
    obs = d.get("observatorio") or {}
    lim = obs.get("limites") if isinstance(obs.get("limites"), dict) else {}
    est3, det3 = SIN_DATO, []
    if lim.get("max_connections"):
        uso = lim["conexiones_abiertas"] / lim["max_connections"]
        est3 = OK if uso <= U["conexiones_ok"] else ALERTA
        det3.append(f"{lim['conexiones_abiertas']}/{lim['max_connections']} conexiones ({100 * uso:.0f} %)")
        if lim.get("bloqueos_en_espera"):
            est3 = _peor(est3, ALERTA)
            det3.append(f"{lim['bloqueos_en_espera']} bloqueos en espera")
    pool = d.get("pool") or {}
    if pool.get("maxconn"):
        if pool.get("fallback_en_uso"):
            est3 = _peor(est3, ALERTA)
            det3.append(f"{pool['fallback_en_uso']} conexiones de respaldo en uso")
        det3.append(f"pool del worker {pool.get('used', 0)}/{pool['maxconn']}")
    filas.append({"criterio": "3. Pool y conexiones", "estado": est3, "detalle": "; ".join(det3) or "sin datos",
                  "accion": "Presupuesto en docs/escalamiento.md; H2 para que el pool espere en vez de fallar."})

    # 4. Base de datos
    if obs:
        hallazgos, est4 = [], OK
        for p in (obs.get("estandar") or {}).get("planes", []):
            for s in p.get("seq_scans", []):
                if (s.get("filas") or 0) >= U["tabla_grande"]:
                    est4 = _peor(est4, ALERTA)
                    hallazgos.append(f"{p['consulta']} recorre {s['tabla']} ({s['filas']} filas)")
        for t in obs.get("tablas") or []:
            if isinstance(t, dict) and t.get("filas", 0) >= 1000 and t["recorridos_completos"] > 10 * max(1, t["por_indice"]):
                est4 = _peor(est4, ALERTA)
                hallazgos.append(f"{t['tabla']}: {t['recorridos_completos']} recorridos completos vs "
                                 f"{t['por_indice']} por índice ({t['filas']} filas) → falta un índice")
        cache = obs.get("cache_hit_pct")
        if cache is not None and float(cache) < U["cache_ok"]:
            est4 = _peor(est4, ALERTA)
            hallazgos.append(f"cache hit {cache} %")
        filas.append({"criterio": "4. Base de datos", "estado": est4,
                      "detalle": "; ".join(hallazgos[:4]) or "sin recorridos completos en tablas grandes",
                      "accion": "Índice para la consulta que recorre; ver top de pg_stat_statements."})
    else:
        filas.append({"criterio": "4. Base de datos", "estado": SIN_DATO, "detalle": "sin BD", "accion": ""})

    # 5. Carga útil
    util = d.get("carga_util") or []
    if util:
        excede = [u for u in util if u.get("excede_presupuesto_en")]
        est5 = ALERTA if excede else OK
        filas.append({"criterio": "5. Carga útil (KB por respuesta)", "estado": est5,
                      "detalle": "; ".join(f"{u['endpoint']} supera {proyeccion.PRESUPUESTO_KB_INTERACTIVO} KB "
                                           f"con {u['excede_presupuesto_en']:,} filas (hoy {u['kb_hoy']} KB)"
                                           for u in excede) or "dentro del presupuesto",
                      "accion": "H3 (búsqueda remota top-N) y H6 (dataset acotado)."})
    else:
        filas.append({"criterio": "5. Carga útil (KB por respuesta)", "estado": SIN_DATO, "detalle": "sin carga", "accion": ""})

    # 6. Auditoría
    aud = d.get("auditoria") or {}
    if aud:
        nuevas = aud.get("nuevas") or []
        est6 = CRITICO if nuevas else (ALERTA if aud.get("total_alta") else OK)
        filas.append({"criterio": "6. Auditoría del código (trinquete)", "estado": est6,
                      "detalle": (f"{len(nuevas)} patrones NUEVOS; " if nuevas else "") +
                                 f"{aud.get('total_alta', 0)} de gravedad alta y {aud.get('total_media', 0)} media (deuda conocida)",
                      "accion": "Los nuevos se corrigen antes de publicar; la deuda baja con H3/H6."})

    # + Proyección
    proy = d.get("proyeccion") or {}
    esc = {e["transacciones_por_empresa"]: e for e in proy.get("escalas", [])}
    if 500_000 in esc:
        u = esc[500_000]["usuarios_activos"]
        est = OK if u >= U["usuarios_500k_ok"] else (ALERTA if u >= U["usuarios_500k_alerta"] else CRITICO)
        filas.append({"criterio": "+ Proyección a 500.000 TX/empresa", "estado": est,
                      "detalle": f"~{u} usuarios activos; cuello: {esc[500_000]['consulta_mas_lenta']} "
                                 f"({esc[500_000]['ms_por_consulta'][esc[500_000]['consulta_mas_lenta']]:.0f} ms en BD)",
                      "accion": "Modelo con supuestos (ver informe). Diario plan A+B y H7 bajan el cuello."})
    return filas


def latencia_base(carga) -> float:
    """Red + framework: p50 de la consulta más trivial (portafolios) al menor escalón."""
    if not carga or not carga.get("escalones"):
        return 0.0
    eps = carga["escalones"][0]["endpoints"]
    return float((eps.get("portafolios") or eps.get("etiquetas") or {}).get("p50_ms") or 0.0)


def pool_de(url) -> dict:
    import urllib.request
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/api/health/profundo", timeout=5) as r:
            return json.load(r).get("pool") or {}
    except Exception:
        return {}


def correr(args) -> dict:
    d = {"fecha": datetime.now().isoformat(timespec="seconds"), "url": args.url}
    aud = auditoria.auditar()
    d["auditoria"] = auditoria.resumen(aud, auditoria.leer_linea_base())
    if not args.sin_bd:
        import observatorio_bd
        d["observatorio"] = observatorio_bd.observar()
    if args.carga:
        import carga_acotada as ca
        if not args.ahora and not ca.en_horario_libre():
            raise SystemExit("⛔ Horario laboral: corre la carga entre 21:00 y 07:00 o usa --ahora.")
        base = args.url.rstrip("/")
        local = base.startswith(("http://127.0.0.1", "http://localhost"))
        token = os.environ.get("LAB_TOKEN") or (ca.token_local() if local else None)
        if not token:
            raise SystemExit("⛔ Para un backend remoto define LAB_TOKEN.")
        usuarios, segundos = ca.acotar([int(x) for x in args.escalones.split(",")], args.segundos)
        empresas, terceros = ca.contexto(base, token)
        # Red + framework + 1 viaje a la BD: 5 llamadas seguidas a la consulta más trivial.
        import statistics
        d["latencia_base_ms"] = round(statistics.median(ca._get(base, "/api/portfolios", token)[0] for _ in range(5)), 1)
        escalones, frenado = ca.correr(base, token, usuarios, segundos, args.pausa_ms, empresas, terceros)
        d["carga"] = {"escalones": escalones, "frenado": frenado}
        d["pool"] = pool_de(base)
    # Proyección
    obs = d.get("observatorio") or {}
    est = obs.get("estandar") or {}
    lim = obs.get("limites") if isinstance(obs.get("limites"), dict) else {}
    pool_max = (d.get("pool") or {}).get("maxconn") or int(os.environ.get("DB_POOL_MAX", "10"))
    if est.get("planes"):
        d["proyeccion"] = proyeccion.proyectar(est["planes"], est.get("transacciones_empresa") or 1,
                                               args.workers, pool_max, lim.get("max_connections"))
    if d.get("carga"):
        primero = {}
        for e in d["carga"]["escalones"]:          # KB por endpoint en cualquier escalón
            for n, x in e["endpoints"].items():
                primero.setdefault(n, x)
        tablas = {t["tabla"]: t["filas"] for t in (obs.get("tablas") or []) if isinstance(t, dict)}
        filas_tx = sum(t["filas"] for t in (obs.get("tablas") or []) if isinstance(t, dict) and t["tabla"] == "transactions") or 1
        util = []
        if "analisis_dataset" in primero:
            util += proyeccion.proyectar_carga_util({"analisis_dataset": primero["analisis_dataset"]["kb_medio"]},
                                                    {"analisis_dataset": filas_tx})
        if "terceros_catalogo" in primero:
            util += proyeccion.proyectar_carga_util({"terceros_catalogo": primero["terceros_catalogo"]["kb_medio"]},
                                                    {"terceros_catalogo": tablas.get("third_parties", 1)},
                                                    escalas=(5_000, 50_000, 500_000))
        d["carga_util"] = util
    d["veredicto"] = evaluar(d)
    return d


ICONO = {OK: "🟢", ALERTA: "🟡", CRITICO: "🔴", SIN_DATO: "⚪"}


def informe_md(d: dict, previo: Optional[dict]) -> str:
    v = d["veredicto"]
    global_ = _peor(*[x["estado"] for x in v])
    L = [f"# Laboratorio de rendimiento — {d['fecha'][:16].replace('T', ' ')}", "",
         f"**Veredicto global: {ICONO.get(global_, '')} {global_}** · backend `{d.get('url')}` · "
         "solo lectura contra la BD compartida.", ""]
    if str(d.get("url", "")).startswith(("http://127.0.0.1", "http://localhost")) and d.get("carga"):
        L += ["> ⚠ **Backend local**: un solo worker con recarga y ~180 ms por viaje a la BD (Colombia → "
              "us-east-2). Las latencias de los criterios 1 y 2 **no representan producción**. Para cifras "
              "reales: `--url https://finsys-andres.duckdns.org` con `LAB_TOKEN`, de noche.", ""]
    L += [
         "| Criterio | Estado | Detalle | Qué hacer |", "|---|---|---|---|"]
    for x in v:
        L.append(f"| {x['criterio']} | {ICONO.get(x['estado'], '')} {x['estado']} | {x['detalle']} | {x['accion']} |")
    if previo:
        antes = {x["criterio"]: x["estado"] for x in previo.get("veredicto", [])}
        cambios = [f"{x['criterio']}: {antes[x['criterio']]} → {x['estado']}" for x in v
                   if x["criterio"] in antes and antes[x["criterio"]] != x["estado"]]
        L += ["", f"**Tendencia frente a {previo['fecha'][:16].replace('T', ' ')}:** " +
              ("; ".join(cambios) if cambios else "sin cambios de estado.")]
    carga = d.get("carga")
    if carga:
        L += ["", "## Latencia y capacidad (carga acotada)", "",
              f"Red + framework + 1 viaje a la BD: {d.get('latencia_base_ms', 0):.0f} ms (mediana de 5 llamadas a /api/portfolios). "
              "Desde el PC local esto incluye ~180 ms de red Colombia → Supabase; en producción es ~15 ms.", ""]
        for e in carga["escalones"]:
            L += [f"**{e['usuarios']} usuarios** · {e['peticiones']} peticiones · goodput {e['goodput_ok_s']} OK/s · {e['ok_pct']} % OK", "",
                  "| Endpoint | n | p50 ms | p95 ms | p99 ms | KB | Códigos |", "|---|---|---|---|---|---|---|"]
            for n, x in sorted(e["endpoints"].items()):
                L.append(f"| {n} | {x['n']} | {x['p50_ms']} | {x['p95_ms']} | {x['p99_ms']} | {x['kb_medio']} | {x['codigos']} |")
            L.append("")
        if carga.get("frenado"):
            L.append(f"🛑 Freno automático: {carga['frenado']}")
    obs = d.get("observatorio")
    if obs:
        lim = obs.get("limites") or {}
        L += ["", "## Base de datos (observatorio, solo lectura)", "",
              f"Postgres {lim.get('version')} · max_connections {lim.get('max_connections')} · "
              f"abiertas {lim.get('conexiones_abiertas')} · cache hit {obs.get('cache_hit_pct')} %", "",
              "| Consulta estándar | BD ms | Recorridos completos |", "|---|---|---|"]
        for p in (obs.get("estandar") or {}).get("planes", []):
            seq = ", ".join(f"{s['tabla']}({s['filas']})" for s in p.get("seq_scans", [])) if "error" not in p else p["error"]
            L.append(f"| {p['consulta']} | {p.get('ejecucion_ms', '—')} | {seq or '—'} |")
        L += ["", "| Tabla | Filas | Recorridos completos | Por índice |", "|---|---|---|---|"]
        for t in (obs.get("tablas") or [])[:10]:
            if isinstance(t, dict):
                L.append(f"| {t['tabla']} | {t['filas']} | {t['recorridos_completos']} | {t['por_indice']} |")
        top = obs.get("top_sentencias")
        if isinstance(top, list) and top:
            L += ["", "**Lo que más tiempo total consume (pg_stat_statements):**", "",
                  "| Consulta | Llamadas | Total ms | Media ms |", "|---|---|---|---|"]
            for s in top[:6]:
                L.append(f"| `{str(s['consulta'])[:90].replace('|', '/')}` | {s['llamadas']} | {s['total_ms']} | {s['media_ms']} |")
    proy = d.get("proyeccion")
    if proy:
        L += ["", "## Proyección de capacidad (modelo)", "",
              f"Conexiones útiles: {proy['conexiones_utiles']} · supuestos: {proy['supuestos']}", "",
              "| TX por empresa | Consulta más lenta | ms en BD | Consultas/s | Usuarios activos |", "|---|---|---|---|---|"]
        for e in proy["escalas"]:
            L.append(f"| {e['transacciones_por_empresa']:,} | {e['consulta_mas_lenta']} | "
                     f"{e['ms_por_consulta'][e['consulta_mas_lenta']]} | {e['consultas_por_s']} | {e['usuarios_activos']} |")
        L += ["", "_Es un modelo: con CPU compartida (Supabase Micro) el número real puede ser menor. "
              "Se reemplaza por medición cuando exista la BD de volumen aislada._"]
    if d.get("carga_util"):
        L += ["", "## Carga útil proyectada (catálogos completos)", "", "| Endpoint | KB hoy | Proyección |", "|---|---|---|"]
        for u in d["carga_util"]:
            L.append(f"| {u['endpoint']} | {u['kb_hoy']} | " +
                     ", ".join(f"{n:,} filas → {kb:,.0f} KB" for n, kb in u["kb_proyectado"].items()) + " |")
    aud = d.get("auditoria")
    if aud:
        L += ["", "## Auditoría del código", "", "| Patrón | Gravedad | Total | Ejemplos | Regla |", "|---|---|---|---|---|"]
        for r in aud["por_regla"]:
            if r["total"]:
                L.append(f"| {r['titulo']} | {r['gravedad']} | {r['total']} | {', '.join(r['ejemplos'][:2])} | {r['regla_estandar']} |")
    return "\n".join(L) + "\n"


def ultimo_historial() -> Optional[dict]:
    try:
        with open(HISTORIAL, encoding="utf-8") as f:
            lineas = [x for x in f.read().splitlines() if x.strip()]
        return json.loads(lineas[-1]) if lineas else None
    except (OSError, ValueError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--carga", action="store_true")
    ap.add_argument("--url", default="http://127.0.0.1:8003")
    ap.add_argument("--escalones", default="1,3,5,10")
    ap.add_argument("--segundos", type=int, default=20)
    ap.add_argument("--pausa-ms", type=int, default=800)
    ap.add_argument("--workers", type=int, default=2, help="workers de producción (gunicorn)")
    ap.add_argument("--ahora", action="store_true")
    ap.add_argument("--sin-bd", action="store_true")
    ap.add_argument("--no-guardar", action="store_true")
    args = ap.parse_args(argv)

    d = correr(args)
    previo = ultimo_historial()
    md = informe_md(d, previo)
    if not args.no_guardar:
        os.makedirs(DIR_INFORMES, exist_ok=True)
        nombre = f"informe-{d['fecha'][:16].replace(':', '').replace('T', '-')}.md"
        with open(os.path.join(DIR_INFORMES, nombre), "w", encoding="utf-8") as f:
            f.write(md)
        with open(HISTORIAL, "a", encoding="utf-8") as f:
            f.write(json.dumps({"fecha": d["fecha"], "url": d["url"], "veredicto": d["veredicto"]},
                               ensure_ascii=False) + "\n")
        print(f"📄 docs/laboratorio/{nombre}")
    print(md)
    nuevas = (d.get("auditoria") or {}).get("nuevas")
    return 1 if nuevas else 0


if __name__ == "__main__":
    sys.exit(main())
