# -*- coding: utf-8 -*-
"""mock_policy.py — Política central de datos simulados (DT-28).

Incidente 2026-09-07: durante un corte de red con Supabase, los drivers
sirvieron datos MOCK como si fueran reales (el selector mostró empresas
inventadas y el frontend llegó a operar sobre ellas). Regla nueva:

    Un fallo de BD produce ERROR VISIBLE, no datos falsos.

Los mocks quedan reservados para desarrollo deliberado sin BD, activado con
el MISMO flag del fail-fast de arranque:

    FINSYS_ALLOW_MOCK=1

Uso en los drivers (solo en los except de fallback — el modo simulación
explícito IS_POSTGRES_ACTIVE no pasa por aquí):

    except Exception as e:
        return mock_o_error(e, "obtener_cuentas", MOCK_USER_ACCOUNTS)
"""
import os


def mock_permitido() -> bool:
    """True solo si el operador pidió explícitamente correr sin BD."""
    return os.getenv("FINSYS_ALLOW_MOCK") == "1"


def mock_o_error(e, contexto: str, valor_mock):
    """Devuelve el mock SOLO bajo FINSYS_ALLOW_MOCK=1; si no, propaga.

    El error propagado conserva la causa original para que el endpoint
    responda 500 con el motivo real en vez de un 200 con mentiras.
    """
    if not mock_permitido():
        raise ConnectionError(f"BD no disponible en {contexto}: {e}") from e
    print(f"⚠️ [MOCK] {contexto} sirviendo datos simulados (FINSYS_ALLOW_MOCK=1): {e}")
    return valor_mock
