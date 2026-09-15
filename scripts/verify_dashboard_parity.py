# -*- coding: utf-8 -*-
"""
Paridad dashboard legacy vs rápido (plan cimientos A2, 2026-09-15)
==================================================================
Compara, para cada portafolio y para "todos", la respuesta de la ruta
legacy de GET /api/dashboard-data (9 sentencias, cálculo en Python) contra
la ruta rápida (1 sentencia, fin_sys_core/dashboard_query.py), y lo mismo
para GET /api/accounts.

    python scripts/verify_dashboard_parity.py            # in-process
    python scripts/verify_dashboard_parity.py --http http://127.0.0.1:8000 http://127.0.0.1:8001
        (compara dos servidores: p. ej. uno con DASHBOARD_FAST=0 y otro =1;
         acepta --token <bearer> si los GET exigen sesión)

Sale con código 1 si hay diferencias. Tolerancia numérica: 0.01.
"""
import json
import os
import sys
from decimal import Decimal

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_ROOT)
sys.path.insert(0, _ROOT)
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            ls = line.strip()
            if ls and not ls.startswith("#") and "=" in ls:
                k, v = ls.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

TOL = 0.01
IGNORAR_CLAVES = set()   # coa se compara desde A0 (ambas rutas leen chart_of_accounts)


def _num(x):
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float, Decimal)):
        return float(x)
    return None


def _norm(x):
    """Serializa como lo haría FastAPI (fechas → str, Decimal → float)."""
    return json.loads(json.dumps(x, default=lambda o: float(o) if isinstance(o, Decimal) else str(o)))


def diff(a, b, ruta="", out=None):
    out = out if out is not None else []
    na, nb = _num(a), _num(b)
    if na is not None and nb is not None:
        if abs(na - nb) > TOL:
            out.append(f"{ruta}: {a} != {b}")
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        ka, kb = set(a), set(b)
        for k in sorted(ka ^ kb):
            out.append(f"{ruta}: clave solo en {'legacy' if k in ka else 'fast'}: {k}")
        for k in sorted(ka & kb):
            if k in IGNORAR_CLAVES:
                continue
            diff(a[k], b[k], f"{ruta}.{k}", out)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{ruta}: longitud {len(a)} != {len(b)}")
        # Listas de dicts con id → emparejar por id; si no, por posición
        if a and b and all(isinstance(x, dict) and "id" in x for x in a + b):
            ma = {x["id"]: x for x in a}
            mb = {x["id"]: x for x in b}
            for k in sorted(set(ma) ^ set(mb)):
                out.append(f"{ruta}: id solo en {'legacy' if k in ma else 'fast'}: {k}")
            for k in sorted(set(ma) & set(mb)):
                diff(ma[k], mb[k], f"{ruta}[id={k}]", out)
            # y el orden
            if [x["id"] for x in a] != [x["id"] for x in b]:
                out.append(f"{ruta}: orden distinto")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diff(x, y, f"{ruta}[{i}]", out)
        return out
    if (a in (None, "")) and (b in (None, "")):
        return out
    if a != b:
        out.append(f"{ruta}: {a!r} != {b!r}")
    return out


def casos():
    from fin_sys_core.database_driver import obtener_portafolios
    nombres = [p["name"] for p in obtener_portafolios()]
    return [None] + nombres


def in_process():
    import routers.dashboard_data as dd
    from routers.profile_accounts import list_accounts
    from fin_sys_core.dashboard_query import obtener_cuentas_con_delta

    total = 0
    for portfolio in casos():
        for offset in (0, 50):
            os.environ["DASHBOARD_FAST"] = "0"
            legacy = _norm(dd.get_dashboard_data(portfolio, 50, offset))
            rapido = _norm(dd._dashboard_fast(portfolio, 50, offset))
            d = diff(legacy, rapido, "dashboard")
            etiqueta = f"dashboard portfolio={portfolio!r} offset={offset}"
            print(f"{'✅' if not d else '❌'} {etiqueta}: {len(d)} diferencias")
            for linea in d[:20]:
                print("    ", linea)
            total += len(d)
        os.environ["DASHBOARD_FAST"] = "0"
        legacy = _norm(list_accounts(portfolio))
        rapido = _norm(obtener_cuentas_con_delta(portfolio))
        d = diff(legacy, rapido, "accounts")
        print(f"{'✅' if not d else '❌'} accounts portfolio={portfolio!r}: {len(d)} diferencias")
        for linea in d[:20]:
            print("    ", linea)
        total += len(d)
    return total


def http(a, b, token=None):
    import urllib.request
    import urllib.parse

    def get(base, path):
        req = urllib.request.Request(base + path)
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))

    total = 0
    for portfolio in casos():
        q = "?portfolio=" + urllib.parse.quote(portfolio) if portfolio else "?"
        for path in (f"/api/dashboard-data{q}&limit=50&offset=0", f"/api/accounts{q}"):
            d = diff(get(a, path), get(b, path), path)
            print(f"{'✅' if not d else '❌'} {path}: {len(d)} diferencias")
            for linea in d[:20]:
                print("    ", linea)
            total += len(d)
    return total


if __name__ == "__main__":
    args = sys.argv[1:]
    token = None
    if "--token" in args:
        i = args.index("--token")
        token = args[i + 1]
        del args[i:i + 2]
    if "--http" in args:
        i = args.index("--http")
        n = http(args[i + 1], args[i + 2], token)
    else:
        n = in_process()
    print(f"\n{'PARIDAD OK' if n == 0 else f'{n} DIFERENCIAS'}")
    sys.exit(0 if n == 0 else 1)
