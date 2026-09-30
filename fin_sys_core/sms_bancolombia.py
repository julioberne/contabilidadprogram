# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Etapa 09.F: parser de las alertas SMS de Bancolombia.

Módulo PURO (sin BD, sin red, sin LLM). Regla 6b: una tabla de familias con
una expresión regular cada una; lo que no cae en ninguna familia devuelve
None y el llamador lo conserva como "no reconocido" — jamás se descarta y
jamás se adivina.

Familias con muestra REAL (remitente 85540; el año llega con 2 y con 4
dígitos y los montos en formato 11,900.00 y 7.000,00 según la familia):

  transferencia_enviada (21-sep-2026)
    Bancolombia: Transferiste $11,900.00 desde tu cuenta *3037 a la cuenta
    *3193301184 el 21/09/26 a las 20:00. ¿Dudas? Llamanos al 018000931987.
  compra_tarjeta (23-sep-2026)
    Bancolombia: Compraste $7.000,00 en Didi con tu T.Deb *1775, el
    23/09/2026 a las 10:35. Si tienes dudas, encuentranos aqui: …
  transferencia_recibida (26-sep-2026)
    Bancolombia: Recibiste una transferencia por $1,696,000 de SANDRA JIMENEZ
    en tu cuenta **3037, el 26/09/2026 a las 16:40. Si tienes dudas, …
  pago_qr (26-sep-2026)
    Bancolombia: ANDRES JULIAN DIAZ BERNATE pagaste $30,000.00 por codigo QR
    desde tu cuenta *3037 a la llave 0087671656 el 26/09/2026 a las 17:52.

Familias sin muestra real (Retiraste, pagos PSE, avances…) NO se inventan:
se agregan a FAMILIAS cuando Andrés envíe un SMS de cada una.
Spec: docs/specs/09-bot-ia/09.F-sms-bancolombia.md (R-09F-03, R-09F-04).

Contrato de salida (todas las familias):
  familia, tipo_sugerido (GASTO|INGRESO), tipo_inferido (bool),
  amount, currency, fecha (ISO|None), hora, raw,
  origen_last4   → últimos 4 de MI cuenta o MI tarjeta
  origen_campo   → "last4_cuenta" | "last4_tarjeta" (columna de user_accounts)
  destino        → cuenta / celular / llave de la contraparte (o None)
  destino_last4, destino_es_celular
  contraparte_nombre → comercio o remitente tal como lo escribe el banco (o None)
"""
import re
from datetime import date

REMITENTE_DEFAULT = "85540"

# ── Piezas reutilizables ─────────────────────────────────────────────────────
_PREFIJO = r"(?:Bancolombia:?\s*)?"
_MONEDA = r"(?P<moneda>\$|COP|USD)?\s?"
# "11,900.00" · "4,530,000" · "1.234,56" · "7.000,00" · "2,50" · "12345.67"
_MONTO = r"(?P<monto>\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
_FECHA = r"(?P<fecha>\d{1,2}/\d{1,2}/\d{2}(?:\d{2})?)"
_HORA = r"(?:\s+a\s+las\s+(?P<hora>\d{1,2}:\d{2}))?"

RE_TRANSFERISTE = re.compile(
    _PREFIJO + r"Transferiste\s+" + _MONEDA + _MONTO
    + r"\s+desde\s+tu\s+cuenta\s+\*?(?P<origen>\d{2,6})"
    + r"\s+a\s+la\s+cuenta\s+\*?(?P<destino>\d{4,20})"
    + r"\s+el\s+" + _FECHA + _HORA,
    re.IGNORECASE,
)

RE_COMPRASTE = re.compile(
    _PREFIJO + r"Compraste\s+" + _MONEDA + _MONTO
    + r"\s+en\s+(?P<comercio>.+?)\s+con\s+tu\s+T\.?\s*(?P<tipo_tarjeta>Deb|Cred)[a-zé]*\.?"
    + r"\s*\*?(?P<tarjeta>\d{4})"
    + r",?\s+el\s+" + _FECHA + _HORA,
    re.IGNORECASE,
)

RE_RECIBISTE = re.compile(
    _PREFIJO + r"Recibiste\s+una\s+transferencia\s+por\s+" + _MONEDA + _MONTO
    + r"\s+de\s+(?P<remitente>.+?)\s+en\s+tu\s+cuenta\s+\*{0,3}(?P<cuenta>\d{2,6})"
    + r",?\s+el\s+" + _FECHA + _HORA,
    re.IGNORECASE,
)

# Variante Bre-B (10-ago-2026): "Bancolombia: Andres, recibiste una transferencia
#  de LEIDY DANIELA MOLINA MARTINEZ por $505,000.00 en tu cuenta *3037 conectada
#  a la llave 1007365480 el 10/08/26 a las 19:41." — nombre ANTES del monto.
RE_RECIBISTE_LLAVE = re.compile(
    r"recibiste\s+una\s+transferencia\s+de\s+(?P<remitente>.+?)\s+por\s+" + _MONEDA + _MONTO
    + r"\s+en\s+tu\s+cuenta\s+\*{0,3}(?P<cuenta>\d{2,6})"
    + r"(?:\s+conectada\s+a\s+la\s+llave\s+(?P<llave>\S+?))?"
    + r",?\s+el\s+" + _FECHA + _HORA,
    re.IGNORECASE,
)

# "…: NOMBRE DEL TITULAR pagaste $30,000.00 por codigo QR desde tu cuenta *3037
#  a la llave 0087671656 el …" — la llave Bre-B puede ser celular, cédula,
#  correo o alfanumérica: se captura hasta el siguiente espacio.
RE_PAGO_QR = re.compile(
    r"pagaste\s+" + _MONEDA + _MONTO
    + r"\s+por\s+c[oó]digo\s+QR\s+desde\s+tu\s+cuenta\s+\*?(?P<origen>\d{2,6})"
    + r"\s+a\s+la\s+llave\s+(?P<llave>\S+)"
    + r"\s+el\s+" + _FECHA + _HORA,
    re.IGNORECASE,
)


# ── Normalizadores deterministas ─────────────────────────────────────────────

def normalizar_monto(texto):
    """'11,900.00' → 11900.0 · '4,530,000' → 4530000.0 · '7.000,00' → 7000.0
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
    Daviplata / llave Bre-B de celular). Cualquier otra cosa es cuenta o llave."""
    return bool(re.fullmatch(r"3\d{9}", destino or ""))


def last4(numero) -> str:
    return (numero or "")[-4:]


def _limpiar_nombre(s) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip(" .,")


# ── Builders por familia ─────────────────────────────────────────────────────

def _base(nombre, m, texto, tipo, tipo_inferido):
    return {
        "familia": nombre,
        "tipo_sugerido": tipo,
        "tipo_inferido": tipo_inferido,
        "amount": normalizar_monto(m.group("monto")),
        "currency": "USD" if (m.group("moneda") or "").upper() == "USD" else "COP",
        "fecha": normalizar_fecha(m.group("fecha")),
        "hora": m.group("hora"),
        "raw": texto,
        "origen_last4": None,
        "origen_campo": "last4_cuenta",
        "destino": None,
        "destino_last4": None,
        "destino_es_celular": False,
        "contraparte_nombre": None,
    }


def _build_transferencia(nombre, m, texto):
    # GASTO inferido: si el destino resulta ser otra cuenta MÍA, bot_sms la
    # convierte en TRANSFERENCIA (determinista, por last4_cuenta).
    d = _base(nombre, m, texto, "GASTO", True)
    destino = m.group("destino")
    d.update(origen_last4=last4(m.group("origen")), destino=destino,
             destino_last4=last4(destino), destino_es_celular=es_celular(destino))
    return d


def _build_compra(nombre, m, texto):
    d = _base(nombre, m, texto, "GASTO", False)      # una compra ES un gasto
    es_credito = m.group("tipo_tarjeta").lower().startswith("cred")
    d.update(origen_last4=m.group("tarjeta"), origen_campo="last4_tarjeta",
             contraparte_nombre=_limpiar_nombre(m.group("comercio")),
             tarjeta_tipo="credito" if es_credito else "debito")
    return d


def _build_recibida(nombre, m, texto):
    d = _base(nombre, m, texto, "INGRESO", False)    # "Recibiste" ES un ingreso
    d.update(origen_last4=last4(m.group("cuenta")),   # MI cuenta (la que recibe)
             contraparte_nombre=_limpiar_nombre(m.group("remitente")))
    llave = (m.groupdict().get("llave") or "").rstrip(".,;")
    if llave:
        d["mi_llave"] = llave                         # llave Bre-B de MI cuenta (auditoría)
    return d


def _build_pago_qr(nombre, m, texto):
    d = _base(nombre, m, texto, "GASTO", False)      # "pagaste" ES un gasto
    llave = m.group("llave").rstrip(".,;")
    d.update(origen_last4=last4(m.group("origen")), destino=llave,
             destino_last4=last4(llave), destino_es_celular=es_celular(llave))
    return d


# (nombre, regex compilada, builder(nombre, match, texto) -> dict)
# Se evalúan en orden; la primera que hace search() gana.
FAMILIAS = (
    ("transferencia_enviada", RE_TRANSFERISTE, _build_transferencia),
    ("compra_tarjeta", RE_COMPRASTE, _build_compra),
    ("transferencia_recibida", RE_RECIBISTE, _build_recibida),
    ("transferencia_recibida", RE_RECIBISTE_LLAVE, _build_recibida),
    ("pago_qr", RE_PAGO_QR, _build_pago_qr),
    # ("retiro", RE_RETIRASTE, _build_retiro),    # pendiente de muestra real
)


# ── Red de seguridad para plantillas que cambian (R-09F-13) ─────────────────
# Si NINGUNA familia casa, no se adivina la familia; pero hay dos hechos que
# se pueden leer literalmente de cualquier texto:
#   · ¿trae dinero?  Sin un monto ($ / COP / USD + número) NO es un movimiento
#     (avisos de seguridad, claves, inscripción de cuentas): no genera borrador.
#   · Si trae dinero: el primer monto, la primera fecha dd/mm/aa y los *NNNN
#     enmascarados. El llamador los usa como propuesta marcada "inferido".

_RE_DINERO = re.compile(r"(?P<moneda>\$|\bCOP|\bUSD)\s?" + _MONTO, re.IGNORECASE)
_RE_FECHA_SUELTA = re.compile(r"(?<![\d/])(\d{1,2}/\d{1,2}/\d{2}(?:\d{2})?)(?![\d/])")
_RE_HORA_SUELTA = re.compile(r"a\s+las\s+(\d{1,2}:\d{2})", re.IGNORECASE)
_RE_ENMASCARADO = re.compile(r"\*{1,3}(\d{4})(?!\d)")


def tiene_dinero(texto) -> bool:
    """¿El texto menciona un monto? ($11,900.00 · COP 50.000 · USD1,00)"""
    return bool(_RE_DINERO.search(texto or ""))


def extraer_generico(texto) -> dict:
    """Lectura LITERAL de un SMS de plantilla desconocida. No decide tipo,
    familia ni contraparte. → {amount, currency, fecha, hora, last4_candidatos}"""
    t = texto or ""
    m = _RE_DINERO.search(t)
    fecha = None
    for f in _RE_FECHA_SUELTA.findall(t):
        fecha = normalizar_fecha(f)
        if fecha:
            break
    h = _RE_HORA_SUELTA.search(t)
    vistos = []
    for l4 in _RE_ENMASCARADO.findall(t):
        if l4 not in vistos:
            vistos.append(l4)
    return {
        "amount": normalizar_monto(m.group("monto")) if m else None,
        "currency": "USD" if m and (m.group("moneda") or "").upper() == "USD" else "COP",
        "fecha": fecha,
        "hora": h.group(1) if h else None,
        "last4_candidatos": vistos,
    }


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
