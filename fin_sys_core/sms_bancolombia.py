# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Etapa 09.F: parser de las alertas SMS de Bancolombia.

Módulo PURO (sin BD, sin red, sin LLM). Regla 6b: una tabla de familias con
una expresión regular cada una; lo que no cae en ninguna familia devuelve
None y el llamador lo conserva como "no reconocido" — jamás se descarta y
jamás se adivina.

Muestras reales (remitente 85540, 21-sep-2026; el año llegó con 2 y con 4
dígitos el MISMO día, por eso las regex aceptan ambos):

    Bancolombia: Transferiste $11,900.00 desde tu cuenta *3037 a la cuenta
    *3193301184 el 21/09/26 a las 20:00. ¿Dudas? Llamanos al 018000931987.
    Estamos cerca.

Familias sin muestra real (Compraste / Retiraste / Recibiste / Pagaste) NO se
inventan: se agregan a FAMILIAS cuando Andrés envíe un SMS de cada una.
Spec: docs/specs/09-bot-ia/09.F-sms-bancolombia.md (R-09F-03, R-09F-04).
"""
import re
from datetime import date

REMITENTE_DEFAULT = "85540"

# ── Piezas reutilizables ─────────────────────────────────────────────────────
_MONEDA = r"(?P<moneda>\$|COP|USD)?\s?"
# "11,900.00" · "4,530,000" · "1.234,56" · "2,50" · "12345.67"
_MONTO = r"(?P<monto>\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
_FECHA = r"(?P<fecha>\d{1,2}/\d{1,2}/\d{2}(?:\d{2})?)"
_HORA = r"(?:\s+a\s+las\s+(?P<hora>\d{1,2}:\d{2}))?"

RE_TRANSFERISTE = re.compile(
    r"(?:Bancolombia:?\s*)?Transferiste\s+" + _MONEDA + _MONTO
    + r"\s+desde\s+tu\s+cuenta\s+\*?(?P<origen>\d{2,6})"
    + r"\s+a\s+la\s+cuenta\s+\*?(?P<destino>\d{4,20})"
    + r"\s+el\s+" + _FECHA + _HORA,
    re.IGNORECASE,
)


# ── Normalizadores deterministas ─────────────────────────────────────────────

def normalizar_monto(texto):
    """'11,900.00' → 11900.0 · '4,530,000' → 4530000.0 · '1.234,56' → 1234.56
    · '2,50' → 2.5. Con ambos separadores, el que aparece ÚLTIMO es el decimal;
    con uno solo, es de miles si se repite o si el último grupo tiene 3 dígitos.
    → float o None."""
    s = (texto or "").strip().replace(" ", "")
    if not s:
        return None
    tiene_coma, tiene_punto = "," in s, "." in s
    if tiene_coma and tiene_punto:
        decimal = "," if s.rfind(",") > s.rfind(".") else "."
        miles = "." if decimal == "," else ","
        s = s.replace(miles, "").replace(decimal, ".")
    elif tiene_coma or tiene_punto:
        sep = "," if tiene_coma else "."
        partes = s.split(sep)
        if len(partes) > 2 or len(partes[-1]) == 3:
            s = s.replace(sep, "")          # separador de miles
        else:
            s = s.replace(sep, ".")         # separador decimal
    try:
        return float(s)
    except ValueError:
        return None


def normalizar_fecha(texto):
    """'21/09/26' → '2026-09-21' · '21/09/2026' → '2026-09-21' · inválida → None."""
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})\s*", texto or "")
    if not m:
        return None
    d, mes, anio = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if anio < 100:
        anio += 2000
    try:
        return date(anio, mes, d).isoformat()
    except ValueError:
        return None


def es_celular(destino) -> bool:
    """Celular colombiano: 10 dígitos que empiezan por 3 (Nequi / Transfiya /
    Daviplata). Cualquier otra cosa es un número de cuenta."""
    return bool(re.fullmatch(r"3\d{9}", destino or ""))


def last4(numero) -> str:
    return (numero or "")[-4:]


# ── Builders por familia ─────────────────────────────────────────────────────

def _build_transferencia(nombre, m, texto):
    destino = m.group("destino")
    return {
        "familia": nombre,
        "tipo_sugerido": "GASTO",           # transferencia a un tercero = salida
        "amount": normalizar_monto(m.group("monto")),
        "currency": "USD" if (m.group("moneda") or "").upper() == "USD" else "COP",
        "origen_last4": last4(m.group("origen")),
        "destino": destino,
        "destino_last4": last4(destino),
        "destino_es_celular": es_celular(destino),
        "fecha": normalizar_fecha(m.group("fecha")),
        "hora": m.group("hora"),
        "raw": texto,
    }


# (nombre, regex compilada, builder(nombre, match, texto) -> dict)
# Se evalúan en orden; la primera que hace search() gana.
FAMILIAS = (
    ("transferencia_enviada", RE_TRANSFERISTE, _build_transferencia),
    # ("compra_tarjeta",   RE_COMPRASTE,  _build_compra),    # pendiente de muestra real
    # ("retiro",           RE_RETIRASTE,  _build_retiro),    # pendiente de muestra real
    # ("transferencia_recibida", RE_RECIBISTE, _build_recibida),  # pendiente de muestra real
)


def parsear(texto):
    """SMS → dict de la familia reconocida, o None ("no reconocido").
    Nunca lanza: un texto raro simplemente no casa con ninguna familia."""
    t = (texto or "").strip()
    if not t:
        return None
    for nombre, rx, builder in FAMILIAS:
        m = rx.search(t)
        if m:
            return builder(nombre, m, t)
    return None
