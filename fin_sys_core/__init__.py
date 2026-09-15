# -*- coding: utf-8 -*-
"""fin_sys_core — paquete de drivers. UN solo objeto por módulo (2026-09-15).

Historia: server.py hacía `sys.path.insert(0, "fin_sys_core")` y por eso el
código mezclaba dos formas de importar el mismo archivo:

    from db_pool import get_conn                 # forma corta (21 sitios)
    from fin_sys_core.db_pool import get_conn    # forma paquete (8 sitios)

Python las cargaba como DOS módulos distintos en sys.modules → dos pools de
conexiones por proceso (el doble de conexiones contra Supabase, 1.9 s de
calentamiento del segundo, close_pool cerrando solo uno) y estado duplicado
(IS_POSTGRES_ACTIVE, la caché de reglas, el failover...).

Este __init__ instala un MetaPathFinder AL FRENTE de sys.meta_path: cuando
alguien pide `import db_pool`, el finder devuelve EXACTAMENTE el objeto
`fin_sys_core.db_pool` (lo importa bajo el nombre paquete si hace falta).
Así los ~90 imports existentes siguen funcionando sin reescribirlos y el
test tests/test_single_module_identity.py garantiza la identidad.

Orden inverso (scripts/tests que hacen `import db_pool` ANTES de importar
el paquete): al cargar este __init__ se adoptan bajo el nombre paquete los
módulos cortos ya presentes en sys.modules.
"""
import importlib
import importlib.abc
import importlib.util
import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
_PKG = __name__  # "fin_sys_core"


def _es_modulo_del_paquete(nombre: str) -> bool:
    """¿`nombre` (sin puntos) corresponde a fin_sys_core/<nombre>.py?"""
    return (
        "." not in nombre
        and nombre != _PKG
        and os.path.isfile(os.path.join(_DIR, nombre + ".py"))
    )


class _AliasFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """`import <x>` → el mismo objeto que `fin_sys_core.<x>`."""

    def find_spec(self, fullname, path=None, target=None):
        if not _es_modulo_del_paquete(fullname):
            return None
        return importlib.util.spec_from_loader(fullname, self)

    def create_module(self, spec):
        # Devuelve el módulo YA cargado bajo el nombre paquete (o lo carga).
        # importlib no sobreescribe __name__/__spec__ existentes (override=False),
        # así que el objeto conserva su identidad "fin_sys_core.<x>".
        return importlib.import_module(f"{_PKG}.{spec.name}")

    def exec_module(self, module):
        pass  # ya se ejecutó bajo el nombre paquete


def _adoptar_modulos_cortos_ya_cargados():
    """Orden inverso: `import db_pool` ocurrió antes que `import fin_sys_core`."""
    for nombre, modulo in list(sys.modules.items()):
        if modulo is None or "." in nombre or nombre == _PKG:
            continue
        archivo = getattr(modulo, "__file__", None)
        if not archivo:
            continue
        try:
            if os.path.dirname(os.path.abspath(archivo)) != _DIR:
                continue
        except Exception:
            continue
        sys.modules.setdefault(f"{_PKG}.{nombre}", modulo)


_adoptar_modulos_cortos_ya_cargados()

if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())
