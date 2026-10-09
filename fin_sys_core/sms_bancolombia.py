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

  transferencia_llave, pago_boton, retiro_cajero, ahorro_bolsillo (30-sep a
    9-oct-2026): muestras reales junto a cada regex, más abajo.

Familias sin muestra real (pagos PSE, avances…) NO se inventan: se agregan a
FAMILIAS cuando Andrés envíe un SMS de cada una.
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


# Bre-B a una llave CON el nombre del destinatario (8 SMS reales entre el 30-sep
# y el 8-oct-2026, que antes caían en «plantilla nueva»):
#   "Bancolombia: ANDRES, transferiste $70,000.00 a la llave 6550482 desde tu
#    cuenta *3037 a DIDLEXYS MELEANNY VILLASMIL DOMINGUEZ el 08/10/26 a las
#    12:11. Con Bre-b es de una y gratis. …"
RE_TRANSFERISTE_LLAVE = re.compile(
    r"transferiste\s+" + _MONEDA + _MONTO
    + r"\s+a\s+la\s+llave\s+(?P<llave>\S+)"
    + r"\s+desde\s+tu\s+cuenta\s+\*?(?P<origen>\d{2,6})"
    + r"\s+a\s+(?P<nombre>.+?)\s+el\s+" + _FECHA + _HORA,
    re.IGNORECASE,
)

# Pago por Botón Bancolombia (9-oct-2026): fecha sin «el» y hora con segundos.
#   "Bancolombia: Transferiste $12,100.00 por Boton Bancolombia a CAMARA DE
#    COMERCIO DE BOGOTA desde producto *3037. 09/10/2026 11:03:17 ¿Dudas? …"
RE_PAGO_BOTON = re.compile(
    _PREFIJO + r"Transferiste\s+" + _MONEDA + _MONTO
    + r"\s+por\s+Bot[oó]n\s+Bancolombia\s+a\s+(?P<comercio>.+?)"
    + r"\s+desde\s+(?:tu\s+)?producto\s+\*?(?P<origen>\d{2,6})\.?"
    + r"\s+(?:el\s+)?" + _FECHA
    + r"(?:\s+(?:a\s+las\s+)?(?P<hora>\d{1,2}:\d{2})(?::\d{2})?)?",
    re.IGNORECASE,
)

# Retiro en cajero con tarjeta débito (3-oct-2026):
#   "Bancolombia: Retiraste $500.000,00 en CAR_GALERIA de tu T.Deb **5379 el
#    03/10/2026 a las 03:51. Si tienes dudas, …"
RE_RETIRASTE = re.compile(
    _PREFIJO + r"Retiraste\s+" + _MONEDA + _MONTO
    + r"\s+en\s+(?P<lugar>.+?)\s+de\s+tu\s+T\.?\s*(?P<tipo_tarjeta>Deb|Cred)[a-zé]*\.?"
    + r"\s*\*{0,3}(?P<tarjeta>\d{4})"
    + r",?\s+el\s+" + _FECHA + _HORA,
    re.IGNORECASE,
)

# Ahorro a un bolsillo de la misma cuenta (1-oct-2026):
#   "Bancolombia: ANDRES, tu ahorro de $400.000 ya lo tienes en tu bolsillo
#    Personal de tu cuenta de ahorros *3037, el 01/10/2026 a las 07:33. …"
RE_AHORRO_BOLSILLO = re.compile(
    r"tu\s+ahorro\s+de\s+" + _MONEDA + _MONTO
    + r"\s+ya\s+lo\s+tienes\s+en\s+tu\s+bolsillo\s+(?P<bolsillo>.+?)"
    + r"\s+de\s+tu\s+cuenta(?:\s+de\s+ahorros)?\s+\*{0,3}(?P<origen>\d{2,6})"
    + r",?\s+el\s+" + _FECHA + _HORA,
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


def _build_transferencia_llave(nombre, m, texto):
    # Como «Transferiste … a la cuenta»: GASTO inferido. La llave es el medio
    # (ancla fuerte); el nombre del destinatario, el respaldo por igualdad.
    d = _base(nombre, m, texto, "GASTO", True)
    llave = m.group("llave").rstrip(".,;")
    d.update(origen_last4=last4(m.group("origen")), destino=llave,
             destino_last4=last4(llave), destino_es_celular=es_celular(llave),
             contraparte_nombre=_limpiar_nombre(m.group("nombre")))
    return d


def _build_pago_boton(nombre, m, texto):
    d = _base(nombre, m, texto, "GASTO", False)      # pagarle a un comercio ES un gasto
    d.update(origen_last4=last4(m.group("origen")),
             contraparte_nombre=_limpiar_nombre(m.group("comercio")))
    return d


def _build_retiro(nombre, m, texto):
    # Andrés (9-oct-2026): el retiro en cajero se registra como GASTO desde la
    # tarjeta. El cajero NO es un tercero: no se ancla ningún medio.
    d = _base(nombre, m, texto, "GASTO", False)
    es_credito = m.group("tipo_tarjeta").lower().startswith("cred")
    d.update(origen_last4=m.group("tarjeta"), origen_campo="last4_tarjeta",
             lugar=_limpiar_nombre(m.group("lugar")),
             tarjeta_tipo="credito" if es_credito else "debito")
    return d


def _build_ahorro_bolsillo(nombre, m, texto):
    # Andrés (9-oct-2026): traslado entre cuentas propias (cuenta → bolsillo).
    # El bolsillo comparte los 4 dígitos de la cuenta: la cuenta destino NO se
    # resuelve por número; se elige con 💳 Cuenta (nada se adivina).
    d = _base(nombre, m, texto, "TRANSFERENCIA", False)
    d.update(origen_last4=last4(m.group("origen")),
             bolsillo=_limpiar_nombre(m.group("bolsillo")))
    return d


# (nombre, regex compilada, builder(nombre, match, texto) -> dict)
# Se evalúan en orden; la primera que hace search() gana.
FAMILIAS = (
    ("pago_boton", RE_PAGO_BOTON, _build_pago_boton),
    ("transferencia_enviada", RE_TRANSFERISTE, _build_transferencia),
    ("transferencia_llave", RE_TRANSFERISTE_LLAVE, _build_transferencia_llave),
    ("compra_tarjeta", RE_COMPRASTE, _build_compra),
    ("retiro_cajero", RE_RETIRASTE, _build_retiro),
    ("transferencia_recibida", RE_RECIBISTE, _build_recibida),
    ("transferencia_recibida", RE_RECIBISTE_LLAVE, _build_recibida),
    ("pago_qr", RE_PAGO_QR, _build_pago_qr),
    ("ahorro_bolsillo", RE_AHORRO_BOLSILLO, _build_ahorro_bolsillo),
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


_RE_BANCO = re.compile(r"\bbancolombia\b", re.IGNORECASE)


def es_del_banco(texto) -> bool:
    """¿El texto dice que es de Bancolombia? MacroDroid reenvía TODOS los SMS con
    el mismo remitente (85540): sin esto, la publicidad con «$» de otros
    remitentes (Cali Mio, factura Claro) llegaba como «plantilla nueva» y
    creaba borradores basura (#602, #620, #622)."""
    return bool(_RE_BANCO.search(texto or ""))


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
