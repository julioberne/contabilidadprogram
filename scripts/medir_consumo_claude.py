"""Mide en qué se van los tokens de las sesiones de Claude Code de este repo.

Solo lectura: recorre las transcripciones .jsonl de las sesiones principales
(no las de subagentes) en ~/.claude/projects/*contabilidadprogram* y resume:
contexto pico por sesión, tokens releídos de caché, peso de los resultados de
herramientas y archivos más releídos. Sirve para comparar antes/después de
aplicar docs/guia-trabajo-claude.md.

Uso:  .venv\\Scripts\\python.exe scripts\\medir_consumo_claude.py [--dias 30] [--top 12]
"""
import argparse
import glob
import json
import os
import time
from collections import Counter

BASE = os.path.expanduser("~/.claude/projects")
PATRON = "*contabilidadprogram*"


def medir_sesion(ruta, peso_tool, llamadas_tool, agentes, lecturas):
    s = dict(pico=0, turnos=0, comp=0, salida=0, cread=0, cwrite=0, tope200=0)
    id_a_tool = {}
    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            try:
                ev = json.loads(linea)
            except ValueError:
                continue
            tipo = ev.get("type")
            if (tipo == "system" and "compact" in str(ev.get("subtype", ""))) or ev.get("isCompactSummary"):
                s["comp"] += 1
            msg = ev.get("message") or {}
            contenido = msg.get("content") if isinstance(msg.get("content"), list) else []
            if tipo == "assistant":
                u = msg.get("usage") or {}
                ctx = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                       + u.get("cache_creation_input_tokens", 0))
                if ctx:
                    s["turnos"] += 1
                    s["pico"] = max(s["pico"], ctx)
                    s["salida"] += u.get("output_tokens", 0)
                    s["cread"] += u.get("cache_read_input_tokens", 0)
                    s["cwrite"] += u.get("cache_creation_input_tokens", 0)
                    s["tope200"] += min(ctx, 200_000)
                for c in contenido:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        nombre = c.get("name", "?")
                        id_a_tool[c.get("id")] = nombre
                        llamadas_tool[nombre] += 1
                        entrada = c.get("input") or {}
                        if nombre == "Agent":
                            agentes[f"{entrada.get('subagent_type') or 'general'} / modelo={entrada.get('model') or 'definición'}"] += 1
                        elif nombre == "Read":
                            p = str(entrada.get("file_path", "")).replace("\\", "/")
                            lecturas[p.split("contabilidadprogram/")[-1]] += 1
            elif tipo == "user":
                for c in contenido:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        cont = c.get("content")
                        n = len(cont) if isinstance(cont, str) else len(json.dumps(cont, ensure_ascii=False))
                        peso_tool[id_a_tool.get(c.get("tool_use_id"), "?")] += n
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dias", type=int, default=30)
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()

    limite = time.time() - args.dias * 86400
    peso_tool, llamadas_tool, agentes, lecturas = Counter(), Counter(), Counter(), Counter()
    sesiones = []
    for ruta in glob.glob(os.path.join(BASE, PATRON, "*.jsonl")):
        if os.path.getmtime(ruta) < limite:
            continue
        s = medir_sesion(ruta, peso_tool, llamadas_tool, agentes, lecturas)
        if s["turnos"]:
            s["id"] = os.path.basename(ruta)[:8]
            s["fecha"] = time.strftime("%m-%d", time.localtime(os.path.getmtime(ruta)))
            sesiones.append(s)

    if not sesiones:
        print(f"Sin sesiones en los últimos {args.dias} días.")
        return
    picos = sorted(s["pico"] for s in sesiones)
    total_cread = sum(s["cread"] for s in sesiones)
    total_turnos = sum(s["turnos"] for s in sesiones)
    grandes = sum(s["cread"] for s in sesiones if s["pico"] > 700_000)
    print(f"Sesiones con actividad en {args.dias} días: {len(sesiones)}")
    print(f"Contexto pico: mediana {picos[len(picos) // 2]:,} | máximo {picos[-1]:,}")
    for umbral in (200_000, 400_000, 700_000):
        print(f"  sesiones que pasaron {umbral:,}: {sum(p > umbral for p in picos)}")
    print(f"Contexto medio por turno: {total_cread / total_turnos:,.0f}")
    print(f"Tokens releídos de caché: {total_cread / 1e6:,.0f} M "
          f"(sesiones >700k aportan {100 * grandes / max(total_cread, 1):.0f}%)")
    print(f"  con tope de 200k por turno serían como máximo: {sum(s['tope200'] for s in sesiones) / 1e6:,.0f} M")
    print(f"Tokens escritos en caché: {sum(s['cwrite'] for s in sesiones) / 1e6:,.0f} M | "
          f"salida: {sum(s['salida'] for s in sesiones) / 1e6:,.1f} M")
    print(f"Sesiones con compactación: {sum(1 for s in sesiones if s['comp'])}")

    print(f"\nTop {args.top} sesiones por contexto pico:")
    for s in sorted(sesiones, key=lambda x: x["pico"], reverse=True)[:args.top]:
        print(f"  {s['fecha']} {s['id']}  pico={s['pico']:>9,}  turnos={s['turnos']:>5}  "
              f"releído={s['cread'] / 1e6:>7,.0f} M  compactaciones={s['comp']}")

    total_peso = sum(peso_tool.values()) or 1
    print("\nPeso de resultados de herramientas (caracteres):")
    for nombre, n in peso_tool.most_common(args.top):
        print(f"  {nombre:<42} {n:>12,}  {100 * n / total_peso:5.1f}%  llamadas={llamadas_tool[nombre]}")
    print("\nSubagentes lanzados:")
    for k, v in agentes.most_common():
        print(f"  {v:>4}  {k}")
    print("\nArchivos más releídos:")
    for k, v in lecturas.most_common(args.top):
        print(f"  {v:>4}  {k}")


if __name__ == "__main__":
    main()
