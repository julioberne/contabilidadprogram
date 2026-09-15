# -*- coding: utf-8 -*-
"""kernel_journal_workflow.py — Flujo del contador sobre el libro diario (B2).

Transiciones de estado de un asiento (todas las líneas de un entry_group_id
comparten estado; SOLO este módulo y kernel_accounting lo mutan):

    BORRADOR ──contabilizar──▶ CONTABILIZADO ──anular──▶ ANULADO (+ espejo)
        └──────rechazar──────▶ RECHAZADO

Además: editar líneas de un BORRADOR (revalida partida doble, cuentas y
periodo), bandeja agrupada con la TX de origen, y asientos manuales.
Zero-Impact: archivo nuevo; kernel_accounting solo aporta sus funciones.
"""
import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor, execute_values

from fin_sys_core.db_pool import get_conn, put_conn
from kernel.kernel_accounting import (
    PartidaDobleError, CuentaNoExisteError, _monto, derivar_tipo_puc,
    validar_cuentas_existen, registrar_asiento, _anular_grupo,
)
from kernel.kernel_periods import assert_periodo_abierto, PeriodoCerradoError  # noqa: F401

logger = logging.getLogger("kernel.workflow")

TRANSICIONES = {
    "BORRADOR": {"CONTABILIZADO", "RECHAZADO"},
    "CONTABILIZADO": {"ANULADO"},
}


class EstadoAsientoError(Exception):
    """Transición inválida (409) o asiento inexistente (404)."""

    def __init__(self, mensaje: str, status: int = 409):
        super().__init__(mensaje)
        self.status = status


def _json_safe(v):
    if isinstance(v, Decimal):
        return float(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def _fila(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _json_safe(v) for k, v in d.items()}


# ── Lectura ──────────────────────────────────────────────────────────────────

_SELECT_GRUPOS = """
    WITH g AS (
        SELECT entry_group_id,
               MIN(fecha) AS fecha, MIN(estado) AS estado,
               MIN(portfolio_id) AS portfolio_id, MIN(tx_id) AS tx_id,
               MIN(modulo_origen) AS modulo_origen, MIN(referencia) AS referencia,
               MIN(descripcion) AS descripcion,
               SUM(debito) AS total_debito, SUM(credito) AS total_credito,
               MIN(created_by) AS created_by, MIN(posted_by) AS posted_by,
               MIN(posted_at) AS posted_at, MIN(revisado_por) AS revisado_por,
               MIN(revisado_en) AS revisado_en, MIN(motivo) AS motivo,
               MIN(reversa_de) AS reversa_de, MIN(anulado_por) AS anulado_por,
               MIN(created_at) AS created_at, COUNT(*) AS n_lineas, MIN(id) AS min_id
        FROM kernel_journal_entries
        {where}
        GROUP BY entry_group_id
    )
    SELECT g.*, p.name AS portfolio_name,
           t.type AS tx_type, t.amount AS tx_amount, t.net_value AS tx_net_value,
           t.concept AS tx_concept, t.category AS tx_category,
           t.transaction_date AS tx_fecha, t.payment_method AS tx_payment_method,
           tp.name AS tx_tercero, a.name AS tx_cuenta,
           COUNT(*) OVER() AS total
    FROM g
    LEFT JOIN portfolios p ON p.id = g.portfolio_id
    LEFT JOIN transactions t ON t.id = g.tx_id
    LEFT JOIN third_parties tp ON tp.id = t.third_party_id
    LEFT JOIN user_accounts a ON a.id = t.account_id
    ORDER BY g.fecha DESC, g.min_id DESC
    LIMIT %(limit)s OFFSET %(offset)s
"""


def _lineas_de(cur, grupos: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    if not grupos:
        return {}
    cur.execute("""
        SELECT id, entry_group_id, linea, cuenta_codigo, cuenta_nombre, cuenta_tipo,
               debito, credito
        FROM kernel_journal_entries
        WHERE entry_group_id = ANY(%s)
        ORDER BY entry_group_id, linea, id
    """, (grupos,))
    por_grupo: Dict[str, List[Dict[str, Any]]] = {}
    for r in cur.fetchall():
        por_grupo.setdefault(r["entry_group_id"], []).append(_fila(dict(r)))
    return por_grupo


def obtener_asientos_agrupados(estado: Optional[str] = "BORRADOR", portfolio_id: Optional[int] = None,
                               fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None,
                               modulo_origen: Optional[str] = None, q: Optional[str] = None,
                               sin_portafolio: bool = False, tx_id: Optional[int] = None,
                               limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """Bandeja: un ítem por asiento (grupo) con sus líneas y la TX de origen.
    estado: un estado | 'TODOS'. → {items, total}"""
    cond, params = [], {"limit": int(limit), "offset": int(offset)}
    if estado and str(estado).upper() != "TODOS":
        cond.append("estado = %(estado)s"); params["estado"] = str(estado).upper()
    if portfolio_id is not None:
        cond.append("portfolio_id = %(pid)s"); params["pid"] = int(portfolio_id)
    if sin_portafolio:
        cond.append("portfolio_id IS NULL")
    if fecha_desde:
        cond.append("fecha >= %(desde)s"); params["desde"] = fecha_desde
    if fecha_hasta:
        cond.append("fecha <= %(hasta)s"); params["hasta"] = fecha_hasta
    if modulo_origen:
        cond.append("modulo_origen = %(modulo)s"); params["modulo"] = modulo_origen
    if tx_id is not None:
        cond.append("tx_id = %(txid)s"); params["txid"] = int(tx_id)
    if q:
        cond.append("(referencia ILIKE %(q)s OR descripcion ILIKE %(q)s OR entry_group_id ILIKE %(q)s)")
        params["q"] = f"%{q}%"
    where = ("WHERE " + " AND ".join(cond)) if cond else ""
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(_SELECT_GRUPOS.format(where=where), params)
        filas = [dict(r) for r in cur.fetchall()]
        total = int(filas[0]["total"]) if filas else 0
        lineas = _lineas_de(cur, [f["entry_group_id"] for f in filas])
        cur.close()
    finally:
        put_conn(conn)
    items = []
    for f in filas:
        f.pop("total", None); f.pop("min_id", None)
        item = _fila(f)
        item["cuadra"] = abs(float(f["total_debito"] or 0) - float(f["total_credito"] or 0)) < 0.005
        item["lineas"] = lineas.get(f["entry_group_id"], [])
        tx = {k[3:]: item.pop(k) for k in list(item) if k.startswith("tx_") and k != "tx_id"}
        item["tx"] = tx if any(v is not None for v in tx.values()) else None
        items.append(item)
    return {"items": items, "total": total, "limit": int(limit), "offset": int(offset)}


def obtener_asiento(entry_group_id: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(_SELECT_GRUPOS.format(where="WHERE entry_group_id = %(g)s"),
                    {"g": entry_group_id, "limit": 1, "offset": 0})
        r = cur.fetchone()
        if not r:
            return None
        f = dict(r); f.pop("total", None); f.pop("min_id", None)
        lineas = _lineas_de(cur, [entry_group_id])
        cur.close()
    finally:
        put_conn(conn)
    item = _fila(f)
    item["cuadra"] = abs(float(f["total_debito"] or 0) - float(f["total_credito"] or 0)) < 0.005
    item["lineas"] = lineas.get(entry_group_id, [])
    tx = {k[3:]: item.pop(k) for k in list(item) if k.startswith("tx_") and k != "tx_id"}
    item["tx"] = tx if any(v is not None for v in tx.values()) else None
    return item


# ── Transiciones ─────────────────────────────────────────────────────────────

def _cabecera_bloqueada(cur, entry_group_id: str) -> Dict[str, Any]:
    cur.execute("""
        SELECT entry_group_id, MIN(estado) AS estado, MIN(portfolio_id) AS portfolio_id,
               MIN(fecha) AS fecha, MIN(tx_id) AS tx_id, MIN(modulo_origen) AS modulo_origen,
               MIN(referencia) AS referencia, MIN(descripcion) AS descripcion,
               MIN(created_by) AS created_by, MIN(anulado_por) AS anulado_por,
               SUM(debito) AS total_debito, SUM(credito) AS total_credito
        FROM kernel_journal_entries WHERE entry_group_id = %s
        GROUP BY entry_group_id
    """, (entry_group_id,))
    r = cur.fetchone()
    if not r:
        raise EstadoAsientoError(f"Asiento {entry_group_id} no existe", 404)
    # bloqueo de filas para la transición
    cur.execute("SELECT id FROM kernel_journal_entries WHERE entry_group_id = %s FOR UPDATE", (entry_group_id,))
    return r


def _exigir(estado_actual: str, destino: str, grupo: str) -> None:
    if destino not in TRANSICIONES.get(estado_actual, set()):
        raise EstadoAsientoError(
            f"El asiento {grupo} está {estado_actual}: no puede pasar a {destino}.")


def contabilizar_asiento(entry_group_id: str, usuario: str, conn=None) -> Dict[str, Any]:
    propia = conn is None
    if propia:
        conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cab = _cabecera_bloqueada(cur, entry_group_id)
        _exigir(cab["estado"], "CONTABILIZADO", entry_group_id)
        if _monto(cab["total_debito"]) != _monto(cab["total_credito"]):
            raise PartidaDobleError(
                f"El asiento {entry_group_id} no cuadra: Db={cab['total_debito']} ≠ Cr={cab['total_credito']}")
        assert_periodo_abierto(cab["portfolio_id"], cab["fecha"], conn=conn)
        cur.execute("""
            UPDATE kernel_journal_entries
               SET estado = 'CONTABILIZADO', posted_by = %s, posted_at = NOW()
             WHERE entry_group_id = %s
        """, (usuario, entry_group_id))
        n = cur.rowcount
        if propia:
            conn.commit()
        cur.close()
        logger.info(f"✅ {entry_group_id} CONTABILIZADO por {usuario} ({n} líneas)")
        return {"status": "ok", "entry_group_id": entry_group_id, "estado": "CONTABILIZADO", "lineas": n}
    except Exception:
        if propia:
            conn.rollback()
        raise
    finally:
        if propia:
            put_conn(conn)


def rechazar_asiento(entry_group_id: str, usuario: str, motivo: str) -> Dict[str, Any]:
    if not (motivo or "").strip():
        raise ValueError("El motivo del rechazo es obligatorio.")
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cab = _cabecera_bloqueada(cur, entry_group_id)
        _exigir(cab["estado"], "RECHAZADO", entry_group_id)
        cur.execute("""
            UPDATE kernel_journal_entries
               SET estado = 'RECHAZADO', motivo = %s, revisado_por = %s, revisado_en = NOW()
             WHERE entry_group_id = %s
        """, (motivo.strip(), usuario, entry_group_id))
        n = cur.rowcount
        conn.commit()
        cur.close()
        return {"status": "ok", "entry_group_id": entry_group_id, "estado": "RECHAZADO", "lineas": n}
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def anular_asiento(entry_group_id: str, usuario: str, motivo: str,
                   fecha: Optional[str] = None, conn=None) -> Dict[str, Any]:
    """CONTABILIZADO → espejo CONTABILIZADO (fecha hoy o `fecha`) + ANULADO.
    Un BORRADOR se RECHAZA. Idempotente."""
    if not (motivo or "").strip():
        raise ValueError("El motivo de la anulación es obligatorio.")
    propia = conn is None
    if propia:
        conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT MIN(estado), MIN(anulado_por), MIN(portfolio_id) FROM kernel_journal_entries
            WHERE entry_group_id = %s
        """, (entry_group_id,))
        r = cur.fetchone()
        if not r or r[0] is None:
            raise EstadoAsientoError(f"Asiento {entry_group_id} no existe", 404)
        estado, anulado_por, pid = r
        if estado == "CONTABILIZADO":
            assert_periodo_abierto(pid, fecha or str(date.today()), conn=conn)
        res = _anular_grupo(cur, entry_group_id, estado, anulado_por,
                            motivo=motivo.strip(), usuario=usuario, fecha=fecha)
        if propia:
            conn.commit()
        cur.close()
        return res
    except Exception:
        if propia:
            conn.rollback()
        raise
    finally:
        if propia:
            put_conn(conn)


# ── Edición de borradores y asientos manuales ────────────────────────────────

def _normalizar_lineas(lineas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    salida = []
    for l in lineas or []:
        codigo = str(l.get("cuenta_codigo") or "").strip()
        deb = _monto(l.get("debito") or 0)
        cre = _monto(l.get("credito") or 0)
        if not codigo:
            raise CuentaNoExisteError("Línea con cuenta_codigo vacío")
        if deb < 0 or cre < 0:
            raise PartidaDobleError("Los montos no pueden ser negativos")
        if deb == 0 and cre == 0:
            continue   # línea vacía: se ignora
        if deb > 0 and cre > 0:
            raise PartidaDobleError(f"La línea de {codigo} tiene débito y crédito a la vez")
        salida.append({"cuenta_codigo": codigo, "cuenta_nombre": (l.get("cuenta_nombre") or "")[:150],
                       "cuenta_tipo": l.get("cuenta_tipo") or derivar_tipo_puc(codigo),
                       "debito": deb, "credito": cre})
    if len(salida) < 2:
        raise PartidaDobleError("Un asiento necesita al menos dos líneas con monto")
    td = sum((l["debito"] for l in salida), Decimal("0"))
    tc = sum((l["credito"] for l in salida), Decimal("0"))
    if td != tc:
        raise PartidaDobleError(f"Partida doble no cuadra: Débitos={td:,.2f} ≠ Créditos={tc:,.2f}")
    return salida


def editar_lineas_borrador(entry_group_id: str, lineas: List[Dict[str, Any]], usuario: str,
                           fecha: Optional[str] = None, descripcion: Optional[str] = None,
                           portfolio_id: Optional[int] = None) -> Dict[str, Any]:
    """Solo BORRADOR. Reemplaza las líneas (renumeradas 1..n) conservando
    grupo, referencia, módulo, tx_id y creador. Revalida todo."""
    nuevas = _normalizar_lineas(lineas)
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cab = _cabecera_bloqueada(cur, entry_group_id)
        if cab["estado"] != "BORRADOR":
            raise EstadoAsientoError(f"Solo se editan borradores; {entry_group_id} está {cab['estado']}.")
        validar_cuentas_existen(cur, [l["cuenta_codigo"] for l in nuevas])
        fecha_final = fecha or cab["fecha"]
        pid_final = portfolio_id if portfolio_id is not None else cab["portfolio_id"]
        assert_periodo_abierto(pid_final, fecha_final, conn=conn)
        desc_final = descripcion if descripcion is not None else cab["descripcion"]
        cur.execute("DELETE FROM kernel_journal_entries WHERE entry_group_id = %s", (entry_group_id,))
        filas = [(entry_group_id, fecha_final, l["cuenta_codigo"], l["cuenta_nombre"], l["cuenta_tipo"],
                  l["debito"], l["credito"], cab["modulo_origen"], cab["referencia"], desc_final, i,
                  "BORRADOR", pid_final, cab["tx_id"], cab["created_by"], usuario)
                 for i, l in enumerate(nuevas, start=1)]
        execute_values(cur, """
            INSERT INTO kernel_journal_entries
                (entry_group_id, fecha, cuenta_codigo, cuenta_nombre, cuenta_tipo,
                 debito, credito, modulo_origen, referencia, descripcion, linea,
                 estado, portfolio_id, tx_id, created_by, revisado_por)
            VALUES %s
        """, filas)
        conn.commit()
        cur.close()
        return {"status": "ok", "entry_group_id": entry_group_id, "lineas": len(filas),
                "estado": "BORRADOR"}
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def crear_asiento_manual(portfolio_id: Optional[int], fecha: str, descripcion: str,
                         lineas: List[Dict[str, Any]], usuario: str,
                         contabilizar: bool = False) -> Dict[str, Any]:
    nuevas = _normalizar_lineas(lineas)
    evento = {
        "fecha": fecha or str(date.today()),
        "modulo_origen": "contadores",
        "referencia": f"MAN-{uuid.uuid4().hex[:8].upper()}",
        "descripcion": (descripcion or "").strip() or "Asiento manual",
        "asientos": [{"cuenta_codigo": l["cuenta_codigo"], "cuenta_nombre": l["cuenta_nombre"],
                      "cuenta_tipo": l["cuenta_tipo"], "debito": l["debito"], "credito": l["credito"]}
                     for l in nuevas],
        "portfolio_id": portfolio_id,
        "created_by": usuario,
        "omitir_dedupe": True,
    }
    return registrar_asiento(evento, estado="CONTABILIZADO" if contabilizar else "BORRADOR")
