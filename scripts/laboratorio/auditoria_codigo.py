# -*- coding: utf-8 -*-
"""Auditoría estática de escalabilidad (laboratorio de rendimiento, criterio 6).

Busca en el código los patrones que el estándar de consultas
(docs/estandar-consultas-escalables.md) marca como "no escala": descargas
completas, catálogos enteros al navegador, listas sin tope, GET sin sesión,
montos en float, sondeos periódicos, DDL en la app, búsquedas sin índice…

Funciona como TRINQUETE: `linea_base.json` guarda cuántas veces aparece cada
regla en cada archivo HOY. El CI falla solo si aparece una ocurrencia NUEVA
(o un archivo nuevo con el patrón); bajar el conteo siempre está permitido y
se consolida con --actualizar-linea-base.

    python scripts/laboratorio/auditoria_codigo.py              # informe + trinquete
    python scripts/laboratorio/auditoria_codigo.py --json       # para laboratorio.py
    python scripts/laboratorio/auditoria_codigo.py --actualizar-linea-base
"""
import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LINEA_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "linea_base.json")

DIRS_PY = ("fin_sys_core", "routers", "kernel", "shared")
DIRS_JS = ("frontend/src",)
EXCLUIR = ("node_modules", "dist", ".test.", "test_", "__pycache__", "/tests/", "\\tests\\")


@dataclass(frozen=True)
class Regla:
    id: str
    titulo: str
    gravedad: str           # ALTA | MEDIA
    lenguaje: str           # py | js
    patron: str
    regla_estandar: str     # regla del estándar que lo corrige
    ayuda: str


REGLAS: Tuple[Regla, ...] = (
    Regla("descarga-todas-tx", "Descarga TODAS las transacciones", "ALTA", "py",
          r"obtener_transacciones\(\s*(None)?\s*\)", "B1/B2 · H6",
          "Usar una consulta acotada por empresa, rango y página (fin_sys_core/consultas/)."),
    Regla("catalogo-terceros-completo", "Catálogo de terceros completo al navegador", "ALTA", "js",
          r"""\$\{API\}/third-parties[`'"]\s*[,)]""", "F1/F2 · H3",
          "Usar <BuscadorRemoto> contra /api/buscar/terceros (top-N + 'escribe más')."),
    Regla("dataset-analisis-completo", "Dataset de Análisis sin acotar", "ALTA", "js",
          r"analytics/dataset", "B1 · H6",
          "Dataset por empresa y rango, con tope, generado en la cola y en Arrow."),
    Regla("sondeo-periodico", "Sondeo periódico (setInterval)", "MEDIA", "js",
          r"setInterval\(", "P9 · H7",
          "Versión por empresa + ETag/304, o refrescar solo tras una mutación."),
    Regla("filtro-en-navegador", "Filtro de lista en el navegador", "MEDIA", "js",
          r"\.toLowerCase\(\)\s*\.includes\(", "F1 · H3",
          "Aceptable solo en listas acotadas (<2.000); si crece, búsqueda remota."),
    Regla("monto-float", "Monto convertido a float", "MEDIA", "py",
          r"float\([^)\n]*\b(net_value|amount|monto|saldo|valor)\b", "B9",
          "Montos como Decimal/NUMERIC de punta a punta; string en el JSON."),
    Regla("busqueda-contiene", "Búsqueda 'contiene' (LIKE '%…%')", "MEDIA", "py",
          r"(I?LIKE\s+'%%|I?LIKE\s+%\(|\"%\"\s*\+|f\"%\{)", "B6 · plan B",
          "Requiere índice trigram (pg_trgm) y mínimo 3 caracteres."),
    Regla("paginacion-offset", "Paginación con OFFSET", "MEDIA", "py",
          r"\bOFFSET\s+%", "B3",
          "Paginación por cursor (keyset) con índice (empresa, fecha, id)."),
    Regla("ddl-en-app", "DDL dentro del código de la app", "MEDIA", "py",
          r"(ALTER\s+TABLE|CREATE\s+(UNIQUE\s+)?INDEX|CREATE\s+TABLE)", "P14",
          "El esquema va en migraciones (las corre Andrés); FINSYS_DDL_ARRANQUE=0."),
    Regla("get-sin-sesion", "GET sin sesión (sin Depends(require_*))", "ALTA", "py",
          r"__GET_SIN_SESION__", "B5 · H9",
          "Agregar _u: dict = Depends(require_auth) o declararla pública a propósito."),
)

# GET públicos a propósito (antes del login, health, enlaces públicos firmados).
GET_PUBLICOS = {
    "/api/module-flags", "/api/health", "/api/health/vida", "/api/health/profundo",
}
PREFIJOS_PUBLICOS = ("/api/publico/", "/c/", "/api/tg/", "/api/webhooks/")


def _archivos(dirs, extensiones):
    for d in dirs:
        base = os.path.join(RAIZ, d)
        for raiz, _, nombres in os.walk(base):
            for n in nombres:
                ruta = os.path.join(raiz, n)
                rel = os.path.relpath(ruta, RAIZ).replace("\\", "/")
                if n.endswith(extensiones) and not any(x in "/" + rel for x in EXCLUIR):
                    yield rel, ruta


def _gets_sin_sesion(texto: str) -> List[Tuple[int, str]]:
    """Rutas @router.get / @app.get cuya firma no tiene Depends(require_…)."""
    hallazgos = []
    for m in re.finditer(r'@(?:router|app)\.get\(\s*["\']([^"\']+)["\'][^)]*\)\s*\n\s*(?:async\s+)?def\s+\w+\((.*?)\)\s*(?:->[^:]+)?:',
                         texto, flags=re.S):
        ruta, firma = m.group(1), m.group(2)
        if "Depends(require_" in firma or "Depends(_require" in firma:
            continue
        if ruta in GET_PUBLICOS or ruta.startswith(PREFIJOS_PUBLICOS) or not ruta.startswith("/api/"):
            continue
        linea = texto.count("\n", 0, m.start()) + 1
        hallazgos.append((linea, f"GET {ruta}"))
    return hallazgos


def auditar() -> Dict[str, Dict[str, List[Tuple[int, str]]]]:
    """{regla_id: {archivo: [(línea, fragmento), …]}}"""
    resultado: Dict[str, Dict[str, List[Tuple[int, str]]]] = {r.id: {} for r in REGLAS}
    fuentes = {"py": list(_archivos(DIRS_PY, (".py",))) + [("server.py", os.path.join(RAIZ, "server.py"))],
               "js": list(_archivos(DIRS_JS, (".js", ".jsx")))}
    for lang, archivos in fuentes.items():
        for rel, ruta in archivos:
            try:
                with open(ruta, encoding="utf-8") as f:
                    texto = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            for r in REGLAS:
                if r.lenguaje != lang:
                    continue
                if r.id == "get-sin-sesion":
                    hall = _gets_sin_sesion(texto)
                else:
                    hall = [(texto.count("\n", 0, m.start()) + 1,
                             texto[m.start():m.start() + 80].split("\n")[0].strip())
                            for m in re.finditer(r.patron, texto, flags=re.I)]
                if hall:
                    resultado[r.id][rel] = hall
    return resultado


def conteos(resultado) -> Dict[str, Dict[str, int]]:
    return {rid: {f: len(h) for f, h in archivos.items()} for rid, archivos in resultado.items()}


def comparar(actual: Dict[str, Dict[str, int]], base: Dict[str, Dict[str, int]]) -> List[dict]:
    """Ocurrencias NUEVAS frente a la línea base (lo que hace fallar el trinquete)."""
    nuevas = []
    for rid, archivos in actual.items():
        for f, n in archivos.items():
            previo = base.get(rid, {}).get(f, 0)
            if n > previo:
                nuevas.append({"regla": rid, "archivo": f, "antes": previo, "ahora": n})
    return nuevas


def leer_linea_base(ruta: str = LINEA_BASE) -> Optional[Dict[str, Dict[str, int]]]:
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f).get("conteos")
    except (OSError, ValueError):
        return None


def resumen(resultado, base=None) -> dict:
    c = conteos(resultado)
    por_regla = []
    for r in REGLAS:
        total = sum(c[r.id].values())
        por_regla.append({"id": r.id, "titulo": r.titulo, "gravedad": r.gravedad, "total": total,
                          "archivos": len(c[r.id]), "regla_estandar": r.regla_estandar, "ayuda": r.ayuda,
                          "ejemplos": [f"{f}:{h[0][0]}" for f, h in list(resultado[r.id].items())[:4]]})
    return {"por_regla": por_regla,
            "nuevas": comparar(c, base) if base is not None else None,
            "total_alta": sum(x["total"] for x in por_regla if x["gravedad"] == "ALTA"),
            "total_media": sum(x["total"] for x in por_regla if x["gravedad"] == "MEDIA")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--actualizar-linea-base", action="store_true")
    args = ap.parse_args(argv)

    res = auditar()
    if args.actualizar_linea_base:
        with open(LINEA_BASE, "w", encoding="utf-8") as f:
            json.dump({"nota": "Generado por auditoria_codigo.py --actualizar-linea-base. "
                               "Bajar conteos está bien; subirlos lo bloquea el CI.",
                       "conteos": conteos(res)}, f, ensure_ascii=False, indent=1, sort_keys=True)
        print(f"✅ Línea base actualizada: {LINEA_BASE}")
        return 0

    base = leer_linea_base()
    r = resumen(res, base)
    if args.json:
        print(json.dumps(r, ensure_ascii=False))
    else:
        print("Auditoría de escalabilidad (patrones que no escalan)")
        for x in r["por_regla"]:
            if x["total"]:
                print(f"  [{x['gravedad']:5}] {x['titulo']:45} {x['total']:4} en {x['archivos']:3} archivos "
                      f"→ {x['regla_estandar']}  ej. {', '.join(x['ejemplos'][:2])}")
        if base is None:
            print("  (sin línea base: corre --actualizar-linea-base)")
    if r["nuevas"]:
        print("\n❌ Trinquete: patrones NUEVOS que no escalan (no estaban en la línea base):")
        for n in r["nuevas"]:
            ayuda = next(x["ayuda"] for x in r["por_regla"] if x["id"] == n["regla"])
            print(f"   {n['regla']}: {n['archivo']} ({n['antes']} → {n['ahora']}). {ayuda}")
        return 1
    if not args.json and base is not None:
        print("\n✅ Trinquete: ningún patrón nuevo frente a la línea base.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
