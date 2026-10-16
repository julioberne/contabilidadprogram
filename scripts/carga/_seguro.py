# -*- coding: utf-8 -*-
"""Guarda del laboratorio de carga: jamás contra la BD compartida (Supabase de producción).

La base de FIN-SYS es la MISMA en local y en producción (CLAUDE.md §6). Todo
script de scripts/carga/ llama a `exigir_no_produccion()` antes de conectarse.

Destinos permitidos:
1. Postgres local (localhost, puertos 55432/56432 del docker-compose.carga.yml).
2. Un proyecto de Supabase APARTE para pruebas de volumen ("finsys-lab"): se
   reconoce por su usuario del pooler `postgres.<ref-del-proyecto>`, que tiene
   que ser distinto al de producción (el host del pooler puede ser el mismo).
   Sus datos van en un archivo propio (p. ej. scratch/lab.env) con LAB_DB_HOST,
   LAB_DB_PORT, LAB_DB_USER, LAB_DB_PASSWORD y LAB_DB_NAME.
"""
import os

LOCALES = {"localhost", "127.0.0.1", "::1"}
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PRINCIPAL = r"C:\Users\andre\OneDrive\Escritorio\programas\contabilidadprogram"


def _leer_env(ruta):
    datos = {}
    try:
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    k, v = linea.split("=", 1)
                    datos[k.strip()] = v.strip()
    except OSError:
        pass
    return datos


def usuario_produccion():
    """DB_USER de producción: del entorno o del .env del repo / checkout principal."""
    if os.environ.get("DB_USER") and "supabase" in (os.environ.get("DB_HOST") or ""):
        return os.environ["DB_USER"]
    for ruta in (os.path.join(RAIZ, ".env"), os.path.join(_PRINCIPAL, ".env")):
        env = _leer_env(ruta)
        if env.get("DB_USER"):
            return env["DB_USER"]
    return None


def exigir_local(host: str, puerto) -> None:
    h = (host or "").strip().lower()
    if h not in LOCALES or "supabase" in h:
        raise SystemExit(
            f"⛔ Laboratorio de carga: el host '{host}' no es local. Solo se permite "
            "localhost (Postgres de scripts/carga/docker-compose.carga.yml) o un proyecto "
            "Supabase APARTE con --lab-env. La BD de producción, nunca.")
    if str(puerto) in ("5432", "6543"):
        raise SystemExit(
            f"⛔ Puerto {puerto}: es el de Supabase. El laboratorio local usa 55432 (Postgres) "
            "o 56432 (PgBouncer).")


def exigir_no_produccion(host: str, puerto, usuario: str = "", prod_usuario: str = None) -> None:
    h = (host or "").strip().lower()
    if h in LOCALES:
        exigir_local(host, puerto)
        return
    prod = prod_usuario if prod_usuario is not None else usuario_produccion()
    u = (usuario or "").strip()
    if not prod:
        raise SystemExit("⛔ No pude leer el DB_USER de producción para compararlo: no corro contra un host remoto.")
    if not u or u == prod:
        raise SystemExit(f"⛔ El usuario '{u or '(vacío)'}' es el de PRODUCCIÓN. Usa el proyecto Supabase de laboratorio.")
    if "supabase" in h and "." not in u:
        raise SystemExit("⛔ En el pooler de Supabase el usuario debe ser 'postgres.<ref-del-proyecto>' "
                         "para saber a qué proyecto apunta.")


def leer_lab_env(ruta: str) -> dict:
    """Destino de un proyecto Supabase de laboratorio desde su archivo propio."""
    env = _leer_env(ruta)
    faltan = [k for k in ("LAB_DB_HOST", "LAB_DB_PORT", "LAB_DB_USER", "LAB_DB_PASSWORD") if not env.get(k)]
    if faltan:
        raise SystemExit(f"⛔ {ruta}: faltan {', '.join(faltan)}")
    destino = {"host": env["LAB_DB_HOST"], "puerto": env["LAB_DB_PORT"], "usuario": env["LAB_DB_USER"],
               "clave": env["LAB_DB_PASSWORD"], "db": env.get("LAB_DB_NAME", "postgres")}
    exigir_no_produccion(destino["host"], destino["puerto"], destino["usuario"])
    return destino
