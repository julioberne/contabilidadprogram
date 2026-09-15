# -*- coding: utf-8 -*-
"""Paquete de tests. Carga el .env del repo ANTES de que cualquier test
importe fin_sys_core: db_pool lee DB_HOST/DB_PORT al importarse, y en una
suite combinada el primer módulo que lo importa fijaba "localhost" para
todos los demás (2026-09-15). Sin .env no pasa nada (CI: tests puros)."""
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV = os.path.join(_ROOT, ".env")
if os.path.exists(_ENV):
    with open(_ENV, encoding="utf-8") as _f:
        for _line in _f:
            _ls = _line.strip()
            if _ls and not _ls.startswith("#") and "=" in _ls:
                _k, _v = _ls.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
