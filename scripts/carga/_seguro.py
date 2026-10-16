# -*- coding: utf-8 -*-
"""Guarda del laboratorio de carga: jamás contra la BD compartida (Supabase).

La base de FIN-SYS es la MISMA en local y en producción (CLAUDE.md §6). Todo
script de scripts/carga/ llama a `exigir_local()` antes de conectarse.
"""
LOCALES = {"localhost", "127.0.0.1", "::1"}


def exigir_local(host: str, puerto) -> None:
    h = (host or "").strip().lower()
    if h not in LOCALES or "supabase" in h:
        raise SystemExit(
            f"⛔ Laboratorio de carga: el host '{host}' no es local. Solo se permite "
            "localhost (Postgres de scripts/carga/docker-compose.carga.yml). "
            "La BD de Supabase es la de producción.")
    if str(puerto) in ("5432", "6543"):
        raise SystemExit(
            f"⛔ Puerto {puerto}: es el de Supabase. El laboratorio usa 55432 (Postgres) "
            "o 56432 (PgBouncer).")
