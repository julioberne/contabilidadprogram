# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Constructor de borradores (fuente única de inferencia).

Toma la propuesta cruda del LLM (ai_engine.structure_text_only) y la convierte
en un borrador utilizable, aplicando reglas DETERMINISTAS contra los datos
reales de esta instalación:

  · portafolio validado contra portfolios (sin tildes/mayúsculas)
  · método de pago cruzado con user_accounts — lo que el usuario DIJO manda
    sobre lo que el LLM propuso (su prompt usa una lista genérica ajena a
    las cuentas de este FinSys)
  · account_id resuelto desde el método de pago
  · categoría y tercero con defaults coherentes según el tipo
  · inferred_fields / missing_fields calculados en un solo lugar

Lo usan por igual el Bot IA (fin_sys_core/bot_driver.py) y la Ingestión por
Voz de la web (routers/transactions.py) — misma inteligencia en ambos canales.
"""
import unicodedata
from datetime import date

TIPOS_VALIDOS = ("INGRESO", "GASTO", "TRANSFERENCIA")


def norm(s: str) -> str:
    """minúsculas sin tildes — para comparar 'Crédito' con 'credito'."""
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def fmt_money(v) -> str:
    try:
        return "$" + f"{float(v):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "$?"


# ══════════════════════════════════════════════════════════════════════════════
# Funciones puras (testeables sin BD)
# ══════════════════════════════════════════════════════════════════════════════

def build_payload(parsed: dict, portfolio_name: str):
    """Propuesta del LLM → payload del borrador. → (payload, inferred_fields)

    Todo default queda marcado como inferido: el humano lo ve antes de confirmar.
    """
    inferred = [str(f) for f in (parsed.get("inferred_fields") or [])]

    amount = parsed.get("amount")
    try:
        amount = float(amount) if amount is not None else None
    except (ValueError, TypeError):
        amount = None

    tipo = parsed.get("type") or "GASTO"
    if tipo not in TIPOS_VALIDOS:
        tipo = "GASTO"

    categoria = parsed.get("category")
    if not categoria:
        # Antes la web ponía "Ventas" incluso en un GASTO — default por tipo
        categoria = "Otros Gastos" if tipo == "GASTO" else "Ventas"
        inferred.append("category")

    metodo = parsed.get("payment_method")
    if not metodo:
        metodo = "Efectivo"
        inferred.append("payment_method")

    tp = parsed.get("third_party") or {}
    if not (tp.get("name") or "").strip():
        # Mismo default que el formulario web cuando no hay tercero
        tp = {"identification_type": "NIT", "identification_number": "999999999",
              "name": "Sin especificar"}
        inferred.append("third_party")
    else:
        tp = {
            "identification_type": tp.get("identification_type") or "NIT",
            "identification_number": (tp.get("identification_number") or "").strip() or "999999999",
            "name": (tp.get("name") or "").strip(),
        }
        if tp["identification_type"] not in ("NIT", "CC"):
            tp["identification_type"] = "NIT"

    payload = {
        "portfolio_name": portfolio_name,
        "type": tipo,
        "amount": amount,
        "concept": (parsed.get("concept") or "").strip(),
        "payment_method": metodo,
        "category": categoria,
        "third_party": tp,
        "transaction_date": date.today().isoformat(),
        # Los impuestos JAMÁS se auto-aplican: una categoría inferida por el LLM
        # no es autorización humana para gravar (caso real: "correas de perro"
        # → Infraestructura → +19% sin que el usuario lo pidiera). El IVA/GMF
        # se activan explícitamente en el formulario web o en la bandeja.
        "apply_iva": False,
        "apply_gmf": False,
        "is_recurring": bool(parsed.get("is_recurring", False)),
    }
    return payload, sorted(set(inferred))


def compute_missing(payload: dict):
    """Campos sin los cuales el borrador NO se puede confirmar."""
    missing = []
    if not payload.get("amount") or payload["amount"] <= 0:
        missing.append("monto")
    if not (payload.get("concept") or "").strip():
        missing.append("concepto")
    return missing


# ══════════════════════════════════════════════════════════════════════════════
# Resolvedores contra los datos reales (requieren cursor)
# ══════════════════════════════════════════════════════════════════════════════

def resolver_portafolio(cur, preferido):
    """→ (nombre_real, fue_corregido). (None, False) si no hay portafolios."""
    cur.execute("SELECT name FROM portfolios ORDER BY id")
    nombres = [r[0] for r in cur.fetchall()]
    if not nombres:
        return None, False
    if preferido in nombres:
        return preferido, False
    objetivo = norm(preferido)
    for n in nombres:
        if norm(n) == objetivo:
            return n, False
    return nombres[0], True     # el más antiguo = el principal


def resolver_metodo_pago(cur, texto, sugerido):
    """Cruza lo que el usuario DIJO contra user_accounts.

    → (metodo, explicito). explicito=True cuando el nombre de una cuenta real
    aparece en el texto del usuario: eso manda sobre la propuesta del LLM.
    """
    cur.execute("SELECT name FROM user_accounts ORDER BY id")
    cuentas = [r[0] for r in cur.fetchall()]
    if not cuentas:
        return sugerido, False

    t = norm(texto)
    # 1. Nombre completo de la cuenta mencionado en el texto
    for nombre in cuentas:
        if norm(nombre) in t:
            return nombre, True
    # 2. Palabra distintiva (>3 letras): "Bancolombia" de "Bancolombia Ahorros"
    for nombre in cuentas:
        for palabra in norm(nombre).split():
            if len(palabra) > 3 and palabra in t:
                return nombre, True
    # 3. La propuesta del LLM, si coincide con una cuenta real
    s = norm(sugerido)
    for nombre in cuentas:
        if norm(nombre) == s:
            return nombre, False
    for nombre in cuentas:
        if s and (s in norm(nombre) or norm(nombre) in s):
            return nombre, False
    return sugerido, False


def resolver_cuenta(cur, payment_method):
    """Mapea payment_method → user_accounts.id. → (account_id, error|None)."""
    cur.execute("SELECT id, name FROM user_accounts ORDER BY id")
    cuentas = cur.fetchall()
    if not cuentas:
        return None, "No hay cuentas creadas en FIN-SYS. Crea una en la web primero."
    pm = norm(payment_method)
    if not pm:
        return None, "El borrador no tiene método de pago."
    exactas = [c for c in cuentas if norm(c[1]) == pm]
    if len(exactas) == 1:
        return exactas[0][0], None
    parciales = [c for c in cuentas if pm in norm(c[1]) or norm(c[1]) in pm]
    if len(parciales) == 1:
        return parciales[0][0], None
    nombres = ", ".join(c[1] for c in cuentas)
    if len(parciales) > 1:
        return None, (f"El método de pago '{payment_method}' es ambiguo entre tus cuentas. "
                      f"Cuentas: {nombres}.")
    return None, (f"No encontré una cuenta que coincida con '{payment_method}'. "
                  f"Cuentas disponibles: {nombres}.")


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline completo — el punto de entrada que comparten bot y web
# ══════════════════════════════════════════════════════════════════════════════

def build_draft(cur, parsed: dict, texto: str, portafolio_preferido: str):
    """Propuesta del LLM + texto original → borrador completo y resuelto.

    → {payload, inferred_fields, missing_fields, account_id, account_error,
       portfolio_corregido}
    """
    portafolio, port_corregido = resolver_portafolio(cur, portafolio_preferido)
    if portafolio is None:
        return None

    payload, inferred = build_payload(parsed, portafolio)
    if port_corregido:
        inferred.append("portfolio_name")

    metodo, metodo_explicito = resolver_metodo_pago(cur, texto, payload["payment_method"])
    payload["payment_method"] = metodo
    if metodo_explicito:
        inferred = [f for f in inferred if f != "payment_method"]
    elif "payment_method" not in inferred:
        inferred.append("payment_method")

    account_id, account_error = resolver_cuenta(cur, metodo)
    payload["account_id"] = account_id

    inferred = sorted(set(inferred))
    missing = compute_missing(payload)
    payload["inferred_fields"] = inferred
    payload["missing_fields"] = missing

    return {
        "payload": payload,
        "inferred_fields": inferred,
        "missing_fields": missing,
        "account_id": account_id,
        "account_error": account_error,
        "portfolio_corregido": port_corregido,
    }
