# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Borrar la ficha de un tercero (👤 Terceros → 🗑).

Archivo NUEVO (Zero-Impact). `database_driver.eliminar_tercero` no sirve para
esto: intenta dejar en NULL `transactions.third_party_id` y
`cxp_cxc_ledger.third_party_id`, que en la BD real son NOT NULL + ON DELETE
RESTRICT, y no protege al genérico. Queda sin usar.

Regla (decisión de Andrés, 30-sep-2026):
  · Un tercero CON HISTORIA no se borra: transacciones, cartera (CXC/CXP),
    movimientos de inventario (el FK los dejaría en NULL en silencio) o
    borradores abiertos del bot que lo nombran (al confirmarse, el tercero
    reaparecería solo). Se responde con el conteo, nada se toca.
  · El genérico «Sin especificar» (999999999) jamás se borra.
  · Sin historia se borra la ficha; sus medios de pago
    (`third_party_accounts`) caen por ON DELETE CASCADE.

Mitad con BD: recibe el cursor del llamador y NO hace commit (igual que
terceros_cuentas.py); el router decide commit o rollback.
"""
import psycopg2.errors

from fin_sys_core.database_driver import TERCERO_GENERICO_NUM

# Un borrador sigue vivo (editable / confirmable) hasta que se confirma o se
# descarta; PROCESANDO es la toma del borrador durante la confirmación.
ESTADOS_BORRADOR_ABIERTO = ("BORRADOR", "PROCESANDO", "ERROR")


# ══════════════════════════════════════════════════════════════════════════════
# Mitad pura
# ══════════════════════════════════════════════════════════════════════════════

def _plural(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def describir_uso(uso) -> str:
    """«18 transacciones, 1 cuenta de cartera y 2 borradores abiertos del bot (#236, #240)»
    ("" si no hay nada)."""
    partes = []
    if uso.get("transacciones"):
        partes.append(_plural(uso["transacciones"], "transacción", "transacciones"))
    if uso.get("cartera"):
        partes.append(_plural(uso["cartera"], "cuenta de cartera (CXC/CXP)",
                              "cuentas de cartera (CXC/CXP)"))
    if uso.get("inventario"):
        partes.append(_plural(uso["inventario"], "movimiento de inventario",
                              "movimientos de inventario"))
    borradores = list(uso.get("borradores") or [])
    if borradores:
        ids = ", ".join(f"#{b}" for b in borradores[:5]) + ("…" if len(borradores) > 5 else "")
        partes.append(_plural(len(borradores), "borrador abierto del bot",
                              "borradores abiertos del bot") + f" ({ids})")
    if not partes:
        return ""
    if len(partes) == 1:
        return partes[0]
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def mensaje_en_uso(nombre, uso) -> str:
    """El texto que ve la persona en el aviso del panel (detail del 409)."""
    solo_borradores = bool(uso.get("borradores")) and not any(
        uso.get(k) for k in ("transacciones", "cartera", "inventario"))
    consejo = ("Corrige o descarta ese borrador en la Bandeja del bot y vuelve a intentar."
               if solo_borradores else
               "Un tercero con historia no se borra: primero reasigna o elimina esos registros.")
    return f"No se puede eliminar a «{nombre}»: tiene {describir_uso(uso)}. {consejo}"


# ══════════════════════════════════════════════════════════════════════════════
# Mitad con BD (cursor del llamador; sin commit)
# ══════════════════════════════════════════════════════════════════════════════

def uso_de_tercero(cur, tp_id, numero) -> dict:
    """Cuánta historia tiene el tercero. → {"transacciones", "cartera",
    "inventario": int, "borradores": [ids abiertos que lo nombran]}.
    Los borradores lo referencian por documento (payload.third_party) y, desde
    la etapa 09.I, también por `id` (así el cruce sobrevive a que el documento
    de la ficha cambie después de asignarla)."""
    cur.execute("""
        SELECT (SELECT COUNT(*) FROM transactions WHERE third_party_id = %(id)s),
               (SELECT COUNT(*) FROM cxp_cxc_ledger WHERE third_party_id = %(id)s),
               (SELECT COUNT(*) FROM inventory_movements WHERE third_party_id = %(id)s),
               (SELECT COALESCE(array_agg(id ORDER BY id), '{}')
                  FROM transaction_drafts
                 WHERE status IN %(abiertos)s
                   AND (payload->'third_party'->>'identification_number' = %(numero)s
                        OR payload->'third_party'->>'id' = %(id_txt)s))
    """, {"id": tp_id, "id_txt": str(tp_id), "numero": str(numero), "abiertos": ESTADOS_BORRADOR_ABIERTO})
    txs, cartera, inventario, borradores = cur.fetchone()
    return {"transacciones": int(txs), "cartera": int(cartera), "inventario": int(inventario),
            "borradores": [int(b) for b in (borradores or [])]}


def eliminar(cur, tp_id) -> dict:
    """Borra la ficha si no tiene historia. No hace commit.
    → {"ok": True, "id", "name", "identification_type", "identification_number"}
    → {"ok": False, "codigo": "no_existe" | "generico" | "en_uso", "error": str, "uso"?: {...}}
    La fila queda bloqueada (FOR UPDATE) hasta que el llamador cierre la
    transacción: un registro nuevo que la referencie espera, así el conteo y
    el DELETE ven lo mismo."""
    cur.execute("""
        SELECT identification_type, identification_number, name
          FROM third_parties WHERE id = %s FOR UPDATE
    """, (tp_id,))
    fila = cur.fetchone()
    if not fila:
        return {"ok": False, "codigo": "no_existe", "error": "Ese tercero no existe."}
    tipo, numero, nombre = fila[0], str(fila[1]).strip(), str(fila[2]).strip()
    if numero == TERCERO_GENERICO_NUM:
        return {"ok": False, "codigo": "generico",
                "error": "«Sin especificar» es el tercero genérico del sistema: no se puede eliminar."}
    uso = uso_de_tercero(cur, tp_id, numero)
    if any(uso.values()):
        return {"ok": False, "codigo": "en_uso", "uso": uso, "error": mensaje_en_uso(nombre, uso)}
    try:
        cur.execute("DELETE FROM third_parties WHERE id = %s", (tp_id,))
    except psycopg2.errors.ForeignKeyViolation:
        # Red de seguridad: los FK RESTRICT de la BD mandan aunque el conteo
        # no hubiera visto el registro. La transacción queda abortada; el
        # llamador hace rollback.
        return {"ok": False, "codigo": "en_uso", "uso": uso,
                "error": f"No se puede eliminar a «{nombre}»: acaba de recibir un registro nuevo."}
    return {"ok": True, "id": tp_id, "name": nombre, "identification_type": tipo,
            "identification_number": numero}
