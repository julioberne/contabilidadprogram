# -*- coding: utf-8 -*-
"""
incremental_balance.py — Actualización Incremental de Saldos O(1)
================================================================
Reemplaza la recalculación completa (O(N)) por actualizaciones
atómicas que solo modifican las cuentas afectadas por la transacción.

ANTES: Leer TODAS las transacciones → recalcular en Python → UPDATE todas las cuentas
AHORA: Calcular delta → UPDATE solo la(s) cuenta(s) afectada(s)

Estándar H8 (30-oct-2026): el delta es Decimal al centavo (lo que se suma es
exactamente lo que se revierte) y las cuentas se bloquean en orden ascendente
de id, para que A→B y B→A simultáneos nunca se interbloqueen. El llamador deja
los saldos para el final de su transacción: lo que dura el UPDATE hasta el
commit es lo que la cuenta queda bloqueada.

La función `recalcular_saldos_cuentas()` original se mantiene en database_driver.py
como herramienta de reconciliación manual (no se llama automáticamente).
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any

CENTAVO = Decimal("0.01")


def _decimal(valor) -> Decimal:
    """NUMERIC o float → Decimal (vía str: no arrastra el binario del float)."""
    return Decimal(str(valor))


def _al_centavo(valor: Decimal) -> Decimal:
    """Como numeric(15,2): la mitad se aleja de cero."""
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def calcular_delta_cuenta(tx_data: Dict[str, Any], account_currency: str) -> Decimal:
    """
    Calcula cuánto debe cambiar el saldo de la cuenta ORIGEN para esta transacción.

    Retorna:
        Decimal positivo = saldo sube (INGRESO)
        Decimal negativo = saldo baja (GASTO / TRANSFERENCIA salida)
    """
    tx_type = tx_data.get("type", "").upper()
    net_val = _decimal(tx_data.get("net_value") or 0)
    amount = _decimal(tx_data.get("amount") or 0)
    trm = _decimal(tx_data.get("trm") or 1)
    tx_curr = tx_data.get("transaction_currency", "COP")

    # Valor en la moneda de la cuenta
    val_in_acc = net_val
    if tx_curr != account_currency:
        if tx_curr == "USD" and account_currency == "COP":
            val_in_acc = net_val * trm
        elif tx_curr == "COP" and account_currency == "USD":
            val_in_acc = net_val / trm if trm > 0 else Decimal(0)

    if tx_type == "INGRESO":
        return _al_centavo(val_in_acc)
    elif tx_type == "GASTO":
        return -_al_centavo(val_in_acc)
    elif tx_type == "TRANSFERENCIA":
        return -_al_centavo(amount)  # Transferencia usa amount, no net_value

    return Decimal(0)


def calcular_delta_destino(tx_data: Dict[str, Any],
                           source_account_currency: str,
                           dest_account_currency: str) -> Decimal:
    """
    Calcula cuánto debe cambiar el saldo de la cuenta DESTINO en una TRANSFERENCIA.
    Solo aplica para TRANSFERENCIA con dest_account_id.

    Retorna:
        Decimal positivo (la cuenta destino siempre recibe)
    """
    tx_type = tx_data.get("type", "").upper()
    if tx_type != "TRANSFERENCIA":
        return Decimal(0)

    amount = _decimal(tx_data.get("amount") or 0)
    trm = _decimal(tx_data.get("trm") or 1)

    val_in_dest = amount
    if source_account_currency != dest_account_currency:
        if source_account_currency == "USD" and dest_account_currency == "COP":
            val_in_dest = amount * trm
        elif source_account_currency == "COP" and dest_account_currency == "USD":
            val_in_dest = amount / trm if trm > 0 else Decimal(0)

    return _al_centavo(val_in_dest)


def _deltas_de(cur, tx_data: Dict[str, Any]) -> Dict[int, Decimal]:
    """{cuenta: delta} de una transacción: el origen y, en traslados, el destino."""
    acc_id = tx_data.get("account_id")
    dest_id = tx_data.get("dest_account_id")
    if not acc_id:
        return {}  # Sin cuenta asignada, no hay saldo que actualizar

    es_traslado = bool(dest_id) and tx_data.get("type", "").upper() == "TRANSFERENCIA"
    ids = [int(acc_id), int(dest_id)] if es_traslado else [int(acc_id)]
    cur.execute("SELECT id, currency FROM user_accounts WHERE id = ANY(%s);", (ids,))
    monedas = dict(cur.fetchall())
    if int(acc_id) not in monedas:
        return {}

    deltas = {int(acc_id): calcular_delta_cuenta(tx_data, monedas[int(acc_id)])}
    if es_traslado and int(dest_id) in monedas:
        delta_dest = calcular_delta_destino(tx_data, monedas[int(acc_id)], monedas[int(dest_id)])
        deltas[int(dest_id)] = deltas.get(int(dest_id), Decimal(0)) + delta_dest
    return deltas


def _mover_saldos(cur, deltas: Dict[int, Decimal]) -> None:
    """Aplica los deltas en orden ascendente de id (sin interbloqueo A↔B)."""
    for cuenta_id in sorted(deltas):
        if deltas[cuenta_id] != 0:
            cur.execute("""
                UPDATE user_accounts
                SET current_balance = current_balance + %s
                WHERE id = %s;
            """, (deltas[cuenta_id], cuenta_id))


def aplicar_delta_incremental(conn, tx_data: Dict[str, Any]):
    """
    Aplica la actualización incremental de saldos directamente en la BD.
    Solo toca las cuentas involucradas en la transacción (1 o 2 UPDATEs max).

    Args:
        conn: conexión psycopg2 activa (dentro de una transacción)
        tx_data: datos de la transacción recién registrada
    """
    cur = conn.cursor()
    _mover_saldos(cur, _deltas_de(cur, tx_data))
    cur.close()


def revertir_delta_incremental(conn, tx_data: Dict[str, Any]):
    """
    Revierte el efecto de una transacción sobre los saldos.
    Útil para eliminar transacciones.
    Funciona aplicando el delta inverso.
    """
    cur = conn.cursor()
    _mover_saldos(cur, {cuenta: -delta for cuenta, delta in _deltas_de(cur, tx_data).items()})
    cur.close()


def reemplazar_delta_incremental(conn, viejo: Dict[str, Any], nuevo: Dict[str, Any]):
    """
    Edición: quita el efecto de `viejo` y pone el de `nuevo` en un solo paso,
    cuenta por cuenta y en orden de id (dos pasos separados bloquean en desorden).
    """
    cur = conn.cursor()
    deltas = {cuenta: -delta for cuenta, delta in _deltas_de(cur, viejo).items()}
    for cuenta, delta in _deltas_de(cur, nuevo).items():
        deltas[cuenta] = deltas.get(cuenta, Decimal(0)) + delta
    _mover_saldos(cur, deltas)
    cur.close()
