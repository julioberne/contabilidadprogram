# -*- coding: utf-8 -*-
"""
kernel_event_bus.py — Bus de Eventos Interno (K5)
==================================================
Sistema pub/sub en memoria para desacoplar módulos del ERP.

REGLA DE ORO:
  Un módulo NUNCA llama directamente a otro módulo.
  Solo emite eventos al bus, y el bus los distribuye a los suscriptores.

Ejemplo:
  # RRHH paga nómina:
  from kernel.kernel_event_bus import emit
  emit('hr.nomina.pagada', {
      'fecha': '2026-06-30',
      'modulo_origen': 'hr',
      'referencia': 'NOM-2026-06',
      'asientos': [
          {'cuenta_id': 5105, 'debito': 5000000, 'credito': 0},
          {'cuenta_id': 1105, 'debito': 0,       'credito': 5000000},
      ]
  })

  # Kernel contable escucha automáticamente:
  from kernel.kernel_event_bus import on
  on('hr.nomina.pagada', kernel_accounting.registrar_asiento)
"""

import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger("kernel.event_bus")

# ── Registro de listeners ─────────────────────────────────────────────────────
_listeners: Dict[str, List[Callable]] = {}

# ── Historial de eventos (últimos N para debugging) ───────────────────────────
_event_history: List[Dict[str, Any]] = []
_MAX_HISTORY = 100


def on(event_type: str, handler: Callable):
    """
    Suscribe un handler a un tipo de evento.
    
    Args:
        event_type: Nombre del evento (ej: 'hr.nomina.pagada', 'fin.tx.registrada')
        handler: Función que recibe el payload del evento
    
    Convención de nombres:
        {modulo}.{recurso}.{accion}
        Ejemplos: 'fin.transaccion.registrada', 'hr.nomina.pagada', 'sales.factura.emitida'
    """
    _listeners.setdefault(event_type, []).append(handler)
    logger.info(f"📡 Listener registrado: {event_type} → {handler.__name__}")


def off(event_type: str, handler: Callable = None):
    """
    Desuscribe un handler. Si handler es None, elimina TODOS los listeners del evento.
    """
    if handler is None:
        _listeners.pop(event_type, None)
    elif event_type in _listeners:
        _listeners[event_type] = [h for h in _listeners[event_type] if h != handler]


def emit(event_type: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Emite un evento al bus. Todos los handlers suscritos se ejecutan sincrónicamente.
    
    Args:
        event_type: Nombre del evento
        payload: Datos del evento (dict)
    
    Returns:
        Lista de resultados de cada handler ejecutado
    
    Raises:
        No lanza excepciones — los errores de handlers se capturan y loguean.
        Un handler que falla NO impide que los demás se ejecuten.
    """
    handlers = _listeners.get(event_type, [])
    results = []
    
    # Registrar en historial
    event_record = {
        "type": event_type,
        "payload_keys": list(payload.keys()),
        "handlers_count": len(handlers),
        "modulo_origen": payload.get("modulo_origen", "unknown"),
    }
    _event_history.append(event_record)
    if len(_event_history) > _MAX_HISTORY:
        _event_history.pop(0)
    
    if not handlers:
        logger.debug(f"📡 Evento '{event_type}' emitido sin listeners")
        return results
    
    logger.info(f"📡 Evento '{event_type}' → {len(handlers)} handler(s)")
    
    for handler in handlers:
        try:
            result = handler(payload)
            results.append({"handler": handler.__name__, "status": "ok", "result": result})
        except Exception as e:
            logger.error(f"❌ Error en handler '{handler.__name__}' para evento '{event_type}': {e}")
            results.append({"handler": handler.__name__, "status": "error", "error": str(e)})
    
    return results


def list_listeners() -> Dict[str, List[str]]:
    """Retorna los eventos registrados y sus handlers (para debugging/health checks)."""
    return {
        event_type: [h.__name__ for h in handlers]
        for event_type, handlers in _listeners.items()
    }


def get_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Retorna los últimos N eventos emitidos (para debugging)."""
    return _event_history[-limit:]


def reset():
    """Limpia todos los listeners y el historial. Solo para tests."""
    _listeners.clear()
    _event_history.clear()
