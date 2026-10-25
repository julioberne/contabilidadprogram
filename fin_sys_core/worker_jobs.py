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


@manejador("entrega_zip")
def entrega_zip(datos: Dict[str, Any], op: Dict[str, Any]) -> Dict[str, Any]:
    """H5.3: el 📦 compendio de entrega (ZIP con índice y folio). Antes, dentro de
    POST /api/accounting-files/entrega con una conexión del pool abierta mientras
    se armaba el ZIP en memoria. Mismo resultado que la ruta síncrona."""
    import accounting_files_driver as drv
    import entrega_driver
    pedido = {k: datos.get(k) for k in ("ids", "nombre", "nota", "folder_id")}
    try:
        return entrega_driver.crear(pedido, datos.get("usuario"))
    except (ValueError, drv.Conflicto, drv.NoEncontrado) as e:
        raise ErrorDefinitivo(str(e)) from e


@manejador("bot_mensaje")
def bot_mensaje(datos: Dict[str, Any], op: Dict[str, Any]) -> Dict[str, Any]:
    """H5.4: un mensaje pesado del bot (voz, IA, /analisis) que el poller encoló
    para seguir atendiendo a los demás chats. Se procesa EXACTAMENTE como lo haría
    el poller (bot_driver.handle_message + entregar_respuesta): la lógica del bot
    y la Regla 6b no cambian. Un reintento no duplica: handle_message descarta el
    mensaje repetido por su update_id. Si falla en el último intento, el usuario
    recibe el mismo «⚠ Error interno» de siempre."""
    import bot_driver
    import bot_telegram
    bot_telegram.enviar_accion(datos["chat_id"])
    try:
        reply = bot_driver.handle_message(datos)
    except Exception as e:
        if int(op.get("intentos") or 1) < int(op.get("max_intentos") or 1):
            raise                                   # BD caída, etc.: que reintente
        reply = f"⚠ Error interno del bot: {e}"
    bot_telegram.entregar_respuesta(datos, reply, bot_driver)
    return {"respondido": bool(reply), "chat_id": datos.get("chat_id"), "tipo": datos.get("kind")}


@manejador("diario_csv")
def diario_csv(datos: Dict[str, Any], op: Dict[str, Any]) -> Dict[str, Any]:
    """H5.3: el CSV del Libro Diario de más de 2.000 filas, sin el tope de 5.000
    del navegador; queda en el organizador con folio propio."""
    from fin_sys_core import diario_csv as csv_mod
    try:
        return csv_mod.generar(datos.get("filtros") or {}, datos.get("orden") or "fecha_desc",
                               datos.get("usuario"), folder_id=datos.get("folder_id"))
    except ValueError as e:
        raise ErrorDefinitivo(str(e)) from e
