# -*- coding: utf-8 -*-
"""coa_admin_driver.py — CRUD del plan de cuentas y de las posting rules
para el módulo Contadores (B3, 2026-09-15).

Zero-Impact: database_driver.py (rojo) no se toca; este driver usa el pool
directamente. Toda escritura invalida shared.rules_cache (el asiento
automático cachea reglas/códigos 60 s).

Reglas de negocio:
  COA  · code inmutable (crear otra cuenta + borrar la vieja)
       · no se borra una cuenta con hijos, con movimientos en el diario o
         referenciada por una posting rule activa
       · no se puede quitar is_group a una cuenta con hijos
  Reglas · transaction_type ∈ TX_TYPES · category no vacía · débito ≠ crédito
       · las cuentas deben existir (COA del portafolio, o de cualquiera si la
         regla es global) y NO ser de grupo · __BANK__ permitido
       · única por (category, transaction_type, portafolio) — uq_posting_rules_cat_type
"""
from typing import Any, Dict, List, Optional

from psycopg2 import errors as pg_errors
from psycopg2.extras import RealDictCursor

from fin_sys_core.db_pool import get_conn, put_conn

ACCOUNT_TYPES = ("ACTIVO", "PASIVO", "PATRIMONIO", "INGRESO", "GASTO")
TX_TYPES = ("INGRESO", "GASTO", "TRANSFERENCIA", "CXC", "CXP")
PLACEHOLDERS = ("__BANK__",)


class CoaError(Exception):
    def __init__(self, mensaje: str, status: int = 400):
        super().__init__(mensaje)
        self.status = status


def _invalidar():
    try:
        from shared import rules_cache
        rules_cache.invalidate()
    except Exception:
        pass


def _f(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: (float(v) if hasattr(v, "quantize") else (v.isoformat() if hasattr(v, "isoformat") else v))
            for k, v in d.items()}


# ── Plan de cuentas ──────────────────────────────────────────────────────────

def listar_coa(portfolio_id: int) -> List[Dict[str, Any]]:
    """Filas planas con parent_code, nº de hijos y nº de movimientos
    (líneas del diario con ese código para el portafolio o sin portafolio)."""
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT c.id, c.code, c.name, c.account_type, c.parent_id, c.is_group, c.description,
                   p.code AS parent_code,
                   (SELECT COUNT(*) FROM chart_of_accounts h WHERE h.parent_id = c.id) AS hijos,
                   (SELECT COUNT(*) FROM kernel_journal_entries j
                     WHERE j.cuenta_codigo = c.code
                       AND (j.portfolio_id = c.portfolio_id OR j.portfolio_id IS NULL)) AS movimientos,
                   (SELECT COUNT(*) FROM posting_rules r
                     WHERE r.is_active AND (r.debit_account_code = c.code OR r.credit_account_code = c.code)
                       AND (r.portfolio_id IS NULL OR r.portfolio_id = c.portfolio_id)) AS reglas
            FROM chart_of_accounts c
            LEFT JOIN chart_of_accounts p ON p.id = c.parent_id
            WHERE c.portfolio_id = %s
            ORDER BY c.code
        """, (int(portfolio_id),))
        return [_f(dict(r)) for r in cur.fetchall()]
    finally:
        put_conn(conn)


def _validar_tipo(t: str) -> str:
    t = (t or "").strip().upper()
    if t not in ACCOUNT_TYPES:
        raise CoaError(f"account_type inválido: {t!r}. Válidos: {', '.join(ACCOUNT_TYPES)}")
    return t


def crear_cuenta(portfolio_id: int, code: str, name: str, account_type: str,
                 is_group: bool = False, parent_code: Optional[str] = None,
                 description: Optional[str] = None) -> Dict[str, Any]:
    code = (code or "").strip()
    name = (name or "").strip()
    if not code or not name:
        raise CoaError("code y name son obligatorios")
    tipo = _validar_tipo(account_type)
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        parent_id = None
        if parent_code:
            cur.execute("SELECT id, is_group FROM chart_of_accounts WHERE portfolio_id = %s AND code = %s",
                        (int(portfolio_id), parent_code.strip()))
            p = cur.fetchone()
            if not p:
                raise CoaError(f"La cuenta padre {parent_code} no existe en este portafolio")
            if not p["is_group"]:
                raise CoaError(f"La cuenta padre {parent_code} no es de grupo")
            parent_id = p["id"]
        try:
            cur.execute("""
                INSERT INTO chart_of_accounts (portfolio_id, code, name, account_type, is_group, parent_id, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, code, name, account_type, parent_id, is_group, description
            """, (int(portfolio_id), code, name[:150], tipo, bool(is_group), parent_id, description))
        except pg_errors.UniqueViolation:
            conn.rollback()
            raise CoaError(f"Ya existe la cuenta {code} en este portafolio", 409)
        fila = dict(cur.fetchone())
        conn.commit()
        _invalidar()
        return _f(fila)
    except CoaError:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def actualizar_cuenta(cuenta_id: int, **campos) -> Dict[str, Any]:
    permitidos = {"name", "account_type", "is_group", "description", "parent_code"}
    datos = {k: v for k, v in campos.items() if k in permitidos and v is not None}
    if "code" in campos and campos["code"] is not None:
        raise CoaError("El código es inmutable: crea otra cuenta y elimina la anterior")
    if not datos:
        raise CoaError("Nada que actualizar")
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM chart_of_accounts WHERE id = %s", (int(cuenta_id),))
        actual = cur.fetchone()
        if not actual:
            raise CoaError("Cuenta no encontrada", 404)
        sets, params = [], []
        if "name" in datos:
            sets.append("name = %s"); params.append(str(datos["name"]).strip()[:150])
        if "account_type" in datos:
            sets.append("account_type = %s"); params.append(_validar_tipo(datos["account_type"]))
        if "description" in datos:
            sets.append("description = %s"); params.append(datos["description"])
        if "is_group" in datos:
            if not datos["is_group"]:
                cur.execute("SELECT COUNT(*) AS n FROM chart_of_accounts WHERE parent_id = %s", (int(cuenta_id),))
                if cur.fetchone()["n"]:
                    raise CoaError("No se puede quitar 'grupo' a una cuenta con subcuentas", 409)
            sets.append("is_group = %s"); params.append(bool(datos["is_group"]))
        if "parent_code" in datos:
            if datos["parent_code"] == "":
                sets.append("parent_id = NULL")
            else:
                cur.execute("SELECT id, is_group FROM chart_of_accounts WHERE portfolio_id = %s AND code = %s",
                            (actual["portfolio_id"], str(datos["parent_code"]).strip()))
                p = cur.fetchone()
                if not p or not p["is_group"]:
                    raise CoaError("La cuenta padre no existe o no es de grupo")
                if p["id"] == int(cuenta_id):
                    raise CoaError("Una cuenta no puede ser su propio padre")
                sets.append("parent_id = %s"); params.append(p["id"])
        params.append(int(cuenta_id))
        cur.execute(f"""UPDATE chart_of_accounts SET {', '.join(sets)} WHERE id = %s
                        RETURNING id, code, name, account_type, parent_id, is_group, description""", params)
        fila = dict(cur.fetchone())
        conn.commit()
        _invalidar()
        return _f(fila)
    except CoaError:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def eliminar_cuenta(cuenta_id: int) -> Dict[str, Any]:
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, code, portfolio_id FROM chart_of_accounts WHERE id = %s", (int(cuenta_id),))
        c = cur.fetchone()
        if not c:
            raise CoaError("Cuenta no encontrada", 404)
        cur.execute("SELECT COUNT(*) AS n FROM chart_of_accounts WHERE parent_id = %s", (int(cuenta_id),))
        if cur.fetchone()["n"]:
            raise CoaError(f"La cuenta {c['code']} tiene subcuentas: elimínalas o muévelas primero", 409)
        cur.execute("""SELECT COUNT(*) AS n FROM kernel_journal_entries
                       WHERE cuenta_codigo = %s AND (portfolio_id = %s OR portfolio_id IS NULL)""",
                    (c["code"], c["portfolio_id"]))
        n_mov = cur.fetchone()["n"]
        if n_mov:
            raise CoaError(f"La cuenta {c['code']} tiene {n_mov} movimiento(s) en el diario: no se puede eliminar", 409)
        cur.execute("""SELECT COUNT(*) AS n FROM posting_rules
                       WHERE is_active AND (debit_account_code = %s OR credit_account_code = %s)
                         AND (portfolio_id IS NULL OR portfolio_id = %s)""",
                    (c["code"], c["code"], c["portfolio_id"]))
        if cur.fetchone()["n"]:
            raise CoaError(f"La cuenta {c['code']} está referenciada por una posting rule activa", 409)
        cur.execute("DELETE FROM chart_of_accounts WHERE id = %s", (int(cuenta_id),))
        conn.commit()
        _invalidar()
        return {"status": "ok", "id": int(cuenta_id), "code": c["code"]}
    except CoaError:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def copiar_coa(from_portfolio_id: int, to_portfolio_id: int) -> Dict[str, Any]:
    """Copia el plan de cuentas de un portafolio a otro (solo códigos que no
    existan en el destino), preservando la jerarquía."""
    if int(from_portfolio_id) == int(to_portfolio_id):
        raise CoaError("Origen y destino son el mismo portafolio")
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""SELECT c.code, c.name, c.account_type, c.is_group, c.description, p.code AS parent_code
                       FROM chart_of_accounts c LEFT JOIN chart_of_accounts p ON p.id = c.parent_id
                       WHERE c.portfolio_id = %s ORDER BY length(c.code), c.code""", (int(from_portfolio_id),))
        origen = [dict(r) for r in cur.fetchall()]
        if not origen:
            raise CoaError("El portafolio de origen no tiene plan de cuentas")
        creadas = 0
        for c in origen:   # de códigos cortos a largos: los padres van primero
            parent_id = None
            if c["parent_code"]:
                cur.execute("SELECT id FROM chart_of_accounts WHERE portfolio_id = %s AND code = %s",
                            (int(to_portfolio_id), c["parent_code"]))
                p = cur.fetchone()
                parent_id = p["id"] if p else None
            cur.execute("""INSERT INTO chart_of_accounts (portfolio_id, code, name, account_type, is_group, parent_id, description)
                           VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (portfolio_id, code) DO NOTHING""",
                        (int(to_portfolio_id), c["code"], c["name"], c["account_type"], c["is_group"], parent_id, c["description"]))
            creadas += cur.rowcount
        conn.commit()
        _invalidar()
        return {"status": "ok", "creadas": creadas, "origen": len(origen)}
    except CoaError:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


# ── Posting rules ────────────────────────────────────────────────────────────

def listar_reglas(portfolio_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Globales + las del portafolio, con nombres de cuenta resueltos."""
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT r.id, r.rule_name, r.category, r.transaction_type, r.debit_account_code,
                   r.credit_account_code, r.description, r.is_active, r.portfolio_id, r.created_at,
                   p.name AS portfolio_name,
                   (SELECT name FROM chart_of_accounts d WHERE d.code = r.debit_account_code
                     ORDER BY (d.portfolio_id = r.portfolio_id) DESC NULLS LAST LIMIT 1) AS debit_name,
                   (SELECT name FROM chart_of_accounts c WHERE c.code = r.credit_account_code
                     ORDER BY (c.portfolio_id = r.portfolio_id) DESC NULLS LAST LIMIT 1) AS credit_name
            FROM posting_rules r LEFT JOIN portfolios p ON p.id = r.portfolio_id
            WHERE r.portfolio_id IS NULL OR %(pid)s::int IS NULL OR r.portfolio_id = %(pid)s
            ORDER BY r.transaction_type, r.category, r.portfolio_id NULLS LAST
        """, {"pid": int(portfolio_id) if portfolio_id is not None else None})
        return [_f(dict(r)) for r in cur.fetchall()]
    finally:
        put_conn(conn)


def _validar_regla(cur, category, tx_type, debit, credit, portfolio_id):
    category = (category or "").strip()
    tx_type = (tx_type or "").strip().upper()
    debit = (debit or "").strip()
    credit = (credit or "").strip()
    if not category:
        raise CoaError("category es obligatoria")
    if tx_type not in TX_TYPES:
        raise CoaError(f"transaction_type inválido: {tx_type!r}. Válidos: {', '.join(TX_TYPES)}")
    if not debit or not credit:
        raise CoaError("Cuentas débito y crédito son obligatorias")
    if debit == credit:
        raise CoaError("La cuenta débito y la crédito no pueden ser la misma")
    for code in (debit, credit):
        if code in PLACEHOLDERS:
            continue
        # Mismo criterio que el kernel (validar_cuentas_existen): un código es
        # válido si está en el COA (del portafolio, o de cualquiera si la regla
        # es global) O si ya lo usa una posting rule activa — el PUC sembrado
        # es parcial respecto a las reglas y no hay que bloquear su edición.
        if portfolio_id is not None:
            cur.execute("""SELECT bool_and(is_group) AS is_group FROM chart_of_accounts
                           WHERE code = %s AND (portfolio_id = %s OR portfolio_id IS NULL)
                           HAVING COUNT(*) > 0""", (code, int(portfolio_id)))
        else:
            cur.execute("SELECT bool_and(is_group) AS is_group FROM chart_of_accounts WHERE code = %s HAVING COUNT(*) > 0",
                        (code,))
        r = cur.fetchone()
        if r:
            if r["is_group"]:
                raise CoaError(f"La cuenta {code} es de grupo: no se asienta en grupos")
            continue
        cur.execute("""SELECT 1 FROM posting_rules WHERE is_active
                       AND (debit_account_code = %s OR credit_account_code = %s) LIMIT 1""", (code, code))
        if not cur.fetchone():
            raise CoaError(f"La cuenta {code} no existe en el plan de cuentas ni en ninguna regla activa")
    return category, tx_type, debit, credit


def crear_regla(rule_name: str, category: str, transaction_type: str, debit_account_code: str,
                credit_account_code: str, description: Optional[str] = None,
                portfolio_id: Optional[int] = None, is_active: bool = True) -> Dict[str, Any]:
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        category, tx_type, debit, credit = _validar_regla(
            cur, category, transaction_type, debit_account_code, credit_account_code, portfolio_id)
        try:
            cur.execute("""
                INSERT INTO posting_rules (rule_name, category, transaction_type, debit_account_code,
                                           credit_account_code, description, is_active, portfolio_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, rule_name, category, transaction_type, debit_account_code,
                          credit_account_code, description, is_active, portfolio_id
            """, ((rule_name or category).strip()[:100], category, tx_type, debit, credit,
                  description, bool(is_active), int(portfolio_id) if portfolio_id is not None else None))
        except pg_errors.UniqueViolation:
            conn.rollback()
            raise CoaError(f"Ya existe una regla para ({category}, {tx_type}) en ese ámbito", 409)
        fila = dict(cur.fetchone())
        conn.commit()
        _invalidar()
        return _f(fila)
    except CoaError:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def actualizar_regla(rule_id: int, **campos) -> Dict[str, Any]:
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM posting_rules WHERE id = %s", (int(rule_id),))
        actual = cur.fetchone()
        if not actual:
            raise CoaError("Regla no encontrada", 404)
        nuevo = {k: actual[k] for k in ("rule_name", "category", "transaction_type", "debit_account_code",
                                        "credit_account_code", "description", "is_active", "portfolio_id")}
        for k, v in campos.items():
            if k in nuevo and v is not None:
                nuevo[k] = v
        category, tx_type, debit, credit = _validar_regla(
            cur, nuevo["category"], nuevo["transaction_type"], nuevo["debit_account_code"],
            nuevo["credit_account_code"], nuevo["portfolio_id"])
        try:
            cur.execute("""
                UPDATE posting_rules SET rule_name = %s, category = %s, transaction_type = %s,
                       debit_account_code = %s, credit_account_code = %s, description = %s,
                       is_active = %s, portfolio_id = %s
                WHERE id = %s
                RETURNING id, rule_name, category, transaction_type, debit_account_code,
                          credit_account_code, description, is_active, portfolio_id
            """, ((nuevo["rule_name"] or category).strip()[:100], category, tx_type, debit, credit,
                  nuevo["description"], bool(nuevo["is_active"]),
                  int(nuevo["portfolio_id"]) if nuevo["portfolio_id"] is not None else None, int(rule_id)))
        except pg_errors.UniqueViolation:
            conn.rollback()
            raise CoaError(f"Ya existe otra regla para ({category}, {tx_type}) en ese ámbito", 409)
        fila = dict(cur.fetchone())
        conn.commit()
        _invalidar()
        return _f(fila)
    except CoaError:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def eliminar_regla(rule_id: int) -> Dict[str, Any]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM posting_rules WHERE id = %s RETURNING id", (int(rule_id),))
        r = cur.fetchone()
        if not r:
            raise CoaError("Regla no encontrada", 404)
        conn.commit()
        _invalidar()
        return {"status": "ok", "id": int(rule_id)}
    except CoaError:
        conn.rollback()
        raise
    finally:
        put_conn(conn)
