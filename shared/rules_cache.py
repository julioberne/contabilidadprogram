# -*- coding: utf-8 -*-
"""rules_cache.py — caché en memoria (por proceso, TTL 60 s) de lo que el
asiento automático consulta en CADA transacción (plan cimientos A3).

Antes, registrar una TX pagaba 3-4 viajes a la BD solo para resolver la
posting rule, el nombre de la cuenta bancaria (__BANK__) y validar que los
códigos existen. Estas tablas cambian muy poco: se cachean 60 s y el CRUD de
reglas/COA del módulo Contadores llama invalidate() al escribir.

Resolución de regla = la misma de shared/helpers.emit_journal_entry:
  1. (category, transaction_type) activa, ORDER BY portfolio_id NULLS LAST
  2. si no hay, ('__FALLBACK__', transaction_type)
"""
import threading
import time
from typing import Dict, List, Optional, Set, Tuple

from fin_sys_core.db_pool import get_conn, put_conn

TTL_S = 60.0
_lock = threading.Lock()
_cache: Dict[str, Tuple[float, object]] = {}   # nombre → (expira_en, valor)


def invalidate(nombre: Optional[str] = None) -> None:
    """Borra la caché (toda o una clave). Llamar tras escribir posting_rules,
    chart_of_accounts o user_accounts."""
    with _lock:
        if nombre is None:
            _cache.clear()
        else:
            _cache.pop(nombre, None)


def _get(nombre: str, cargar):
    ahora = time.monotonic()
    with _lock:
        hit = _cache.get(nombre)
        if hit and hit[0] > ahora:
            return hit[1]
    valor = cargar()
    with _lock:
        _cache[nombre] = (time.monotonic() + TTL_S, valor)
    return valor


def _query(sql: str, params=()) -> List[tuple]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        filas = cur.fetchall()
        cur.close()
        return filas
    finally:
        put_conn(conn)


# ── posting_rules ────────────────────────────────────────────────────────────

def _cargar_reglas() -> List[tuple]:
    # (category, transaction_type, debit, credit, rule_name, portfolio_id, id)
    return _query("""
        SELECT category, transaction_type, debit_account_code, credit_account_code,
               rule_name, portfolio_id, id
        FROM posting_rules WHERE is_active = TRUE
        ORDER BY portfolio_id NULLS LAST, id
    """)


def get_rule(category: str, tx_type: str) -> Optional[Tuple[str, str, str]]:
    """→ (debit_code, credit_code, rule_name) o None. Misma prioridad que el
    SQL original (exacta con portfolio_id más bajo primero; luego global;
    luego __FALLBACK__ del mismo tipo)."""
    reglas = _get("posting_rules", _cargar_reglas)
    for cat, tipo, deb, cre, nombre, _pid, _id in reglas:
        if cat == category and tipo == tx_type:
            return deb, cre, nombre
    for cat, tipo, deb, cre, nombre, _pid, _id in reglas:
        if cat == "__FALLBACK__" and tipo == tx_type:
            return deb, cre, nombre
    return None


# ── user_accounts (para __BANK__) ─────────────────────────────────────────────

BANK_ACCOUNT_MAP = {
    "Efectivo": "110505",
    "Caja Menor": "110510",
}
DEFAULT_BANK_CODE = "111005"


def _cargar_cuentas() -> Dict[int, str]:
    return {r[0]: r[1] for r in _query("SELECT id, name FROM user_accounts")}


def resolve_bank_code(account_id) -> str:
    """Igual que shared.helpers.resolve_bank_code, sin viaje a la BD."""
    if not account_id:
        return DEFAULT_BANK_CODE
    try:
        nombre = _get("user_accounts", _cargar_cuentas).get(int(account_id))
    except Exception:
        return DEFAULT_BANK_CODE
    return BANK_ACCOUNT_MAP.get(nombre, DEFAULT_BANK_CODE)


# ── códigos válidos (COA ∪ posting_rules) ────────────────────────────────────

def _cargar_codigos() -> Set[str]:
    filas = _query("""
        SELECT DISTINCT code FROM chart_of_accounts
        UNION SELECT DISTINCT debit_account_code FROM posting_rules WHERE is_active
        UNION SELECT DISTINCT credit_account_code FROM posting_rules WHERE is_active
    """)
    return {r[0] for r in filas if r[0]}


def get_valid_codes() -> Set[str]:
    return _get("valid_codes", _cargar_codigos)


def codigos_conocidos(codigos) -> bool:
    """True si TODOS los códigos están en la caché (evita el SELECT de
    validación). False = consultar la BD (puede ser un código recién creado)."""
    try:
        validos = get_valid_codes()
    except Exception:
        return False
    return all(c in validos for c in codigos)
