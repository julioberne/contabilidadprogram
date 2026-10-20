# -*- coding: utf-8 -*-
"""worker_jobs.py — Manejadores de los trabajos de la cola (estándar H5).

Cada manejador recibe (datos, op) y devuelve el resultado que verá el usuario
en /api/operaciones/{id}. Debe poder correr dos veces sin daño: pgmq entrega
al menos una vez. Los errores del pedido (dato inválido, no existe) se lanzan
como ErrorDefinitivo para no reintentar en vano.
"""
from typing import Any, Dict

from fin_sys_core.worker import ErrorDefinitivo, manejador


@manejador("prueba_eco")
def prueba_eco(datos: Dict[str, Any], op: Dict[str, Any]) -> Dict[str, Any]:
    """Solo para tests (cola trabajos_prueba): devuelve lo que recibe, o falla
    si se le pide (`fallar`: "definitivo" | "transitorio")."""
    modo = datos.get("fallar")
    if modo == "definitivo":
        raise ErrorDefinitivo("pedido inválido (prueba)")
    if modo == "transitorio":
        raise RuntimeError("falla pasajera (prueba)")
    return {"eco": datos.get("eco"), "intento": op.get("intentos")}


@manejador("exportacion_xlsx")
def exportacion_xlsx(datos: Dict[str, Any], op: Dict[str, Any]) -> Dict[str, Any]:
    """H5.2: la exportación .xlsx archivada (antes, dentro de POST /api/analytics/export,
    ocupando un hilo y una conexión del pool de la API mientras se armaba el libro).
    El resultado es el mismo dict que devolvía la ruta síncrona."""
    import accounting_files_driver as drv
    try:
        return drv.generar(datos.get("receta"), datos.get("usuario"), paquete=datos.get("paquete"),
                           folder_id=datos.get("folder_id"),
                           tipo_documental_id=datos.get("tipo_documental_id"))
    except (ValueError, drv.Conflicto, drv.NoEncontrado) as e:
        raise ErrorDefinitivo(str(e)) from e
