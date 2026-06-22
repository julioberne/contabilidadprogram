# -*- coding: utf-8 -*-
"""
incremental_balance.py — Actualización Incremental de Saldos O(1)
================================================================
Reemplaza la recalculación completa (O(N)) por actualizaciones
atómicas que solo modifican las cuentas afectadas por la transacción.

ANTES: Leer TODAS las transacciones → recalcular en Python → UPDATE todas las cuentas
AHORA: Calcular delta → UPDATE solo la(s) cuenta(s) afectada(s)

La función `recalcular_saldos_cuentas()` original se mantiene en database_driver.py
como herramienta de reconciliación manual (no se llama automáticamente).
"""

from typing import Dict, Any, Optional


def calcular_delta_cuenta(tx_data: Dict[str, Any], account_currency: str) -> float:
    """
    Calcula cuánto debe cambiar el saldo de la cuenta ORIGEN para esta transacción.
    
    Retorna:
        float positivo = saldo sube (INGRESO)
        float negativo = saldo baja (GASTO / TRANSFERENCIA salida)
    """
    tx_type = tx_data.get("type", "").upper()
    net_val = float(tx_data.get("net_value") or 0.0)
    amount = float(tx_data.get("amount") or 0.0)
    trm = float(tx_data.get("trm") or 1.0)
    tx_curr = tx_data.get("transaction_currency", "COP")
    
    # Valor en la moneda de la cuenta
    val_in_acc = net_val
    if tx_curr != account_currency:
        if tx_curr == "USD" and account_currency == "COP":
            val_in_acc = net_val * trm
        elif tx_curr == "COP" and account_currency == "USD":
            val_in_acc = net_val / trm if trm > 0 else 0.0
    
    if tx_type == "INGRESO":
        return val_in_acc
    elif tx_type == "GASTO":
        return -val_in_acc
    elif tx_type == "TRANSFERENCIA":
        return -amount  # Transferencia usa amount, no net_value
    
    return 0.0


def calcular_delta_destino(tx_data: Dict[str, Any], 
                           source_account_currency: str,
                           dest_account_currency: str) -> float:
    """
    Calcula cuánto debe cambiar el saldo de la cuenta DESTINO en una TRANSFERENCIA.
    Solo aplica para TRANSFERENCIA con dest_account_id.
    
    Retorna:
        float positivo (la cuenta destino siempre recibe)
    """
    tx_type = tx_data.get("type", "").upper()
    if tx_type != "TRANSFERENCIA":
        return 0.0
    
    amount = float(tx_data.get("amount") or 0.0)
    trm = float(tx_data.get("trm") or 1.0)
    
    val_in_dest = amount
    if source_account_currency != dest_account_currency:
        if source_account_currency == "USD" and dest_account_currency == "COP":
            val_in_dest = amount * trm
        elif source_account_currency == "COP" and dest_account_currency == "USD":
            val_in_dest = amount / trm if trm > 0 else 0.0
    
    return val_in_dest


def aplicar_delta_incremental(conn, tx_data: Dict[str, Any]):
    """
    Aplica la actualización incremental de saldos directamente en la BD.
    Solo toca las cuentas involucradas en la transacción (1 o 2 UPDATEs max).
    
    Args:
        conn: conexión psycopg2 activa (dentro de una transacción)
        tx_data: datos de la transacción recién registrada
    """
    cur = conn.cursor()
    acc_id = tx_data.get("account_id")
    dest_id = tx_data.get("dest_account_id")
    
    if not acc_id:
        return  # Sin cuenta asignada, no hay saldo que actualizar
    
    # 1. Obtener la moneda de la cuenta origen
    cur.execute("SELECT currency FROM user_accounts WHERE id = %s;", (acc_id,))
    row = cur.fetchone()
    if not row:
        return
    acc_currency = row[0]
    
    # 2. Calcular y aplicar delta a cuenta origen
    delta = calcular_delta_cuenta(tx_data, acc_currency)
    if delta != 0.0:
        cur.execute("""
            UPDATE user_accounts 
            SET current_balance = current_balance + %s 
            WHERE id = %s;
        """, (delta, acc_id))
    
    # 3. Si es TRANSFERENCIA con destino, actualizar cuenta destino
    if dest_id and tx_data.get("type", "").upper() == "TRANSFERENCIA":
        cur.execute("SELECT currency FROM user_accounts WHERE id = %s;", (dest_id,))
        dest_row = cur.fetchone()
        if dest_row:
            dest_currency = dest_row[0]
            delta_dest = calcular_delta_destino(tx_data, acc_currency, dest_currency)
            if delta_dest != 0.0:
                cur.execute("""
                    UPDATE user_accounts 
                    SET current_balance = current_balance + %s 
                    WHERE id = %s;
                """, (delta_dest, dest_id))
    
    cur.close()


def revertir_delta_incremental(conn, tx_data: Dict[str, Any]):
    """
    Revierte el efecto de una transacción sobre los saldos.
    Útil para eliminar o editar transacciones.
    Funciona aplicando el delta inverso.
    """
    cur = conn.cursor()
    acc_id = tx_data.get("account_id")
    dest_id = tx_data.get("dest_account_id")
    
    if not acc_id:
        return
    
    cur.execute("SELECT currency FROM user_accounts WHERE id = %s;", (acc_id,))
    row = cur.fetchone()
    if not row:
        return
    acc_currency = row[0]
    
    # Delta inverso en cuenta origen
    delta = calcular_delta_cuenta(tx_data, acc_currency)
    if delta != 0.0:
        cur.execute("""
            UPDATE user_accounts 
            SET current_balance = current_balance - %s 
            WHERE id = %s;
        """, (delta, acc_id))
    
    # Delta inverso en cuenta destino (transferencia)
    if dest_id and tx_data.get("type", "").upper() == "TRANSFERENCIA":
        cur.execute("SELECT currency FROM user_accounts WHERE id = %s;", (dest_id,))
        dest_row = cur.fetchone()
        if dest_row:
            dest_currency = dest_row[0]
            delta_dest = calcular_delta_destino(tx_data, acc_currency, dest_currency)
            if delta_dest != 0.0:
                cur.execute("""
                    UPDATE user_accounts 
                    SET current_balance = current_balance - %s 
                    WHERE id = %s;
                """, (delta_dest, dest_id))
    
    cur.close()
