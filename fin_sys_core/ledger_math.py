# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 - Matemáticas del Libro Diario y Caja Viva (ledger_math.py)
--------------------------------------------------------------------------
Este módulo calcula agregaciones financieras en tiempo real y valida límites
de capital aislado para bolsillos virtuales ("Pockets").
"""

from typing import List, Dict, Any


class ExcedeLimitePocketError(Exception):
    """Excepción lanzada cuando una transacción de gasto supera el presupuesto de un Pocket."""
    pass


def calculate_caja_viva(
    transactions: List[Dict[str, Any]],
    accounts: Optional[List[Dict[str, Any]]] = None,
    capital_inicial_cop: float = 5000000.0,
    capital_inicial_usd: float = 1000.0
) -> Dict[str, Any]:
    """
    Calcula los saldos consolidados en tiempo real para las tarjetas de la Caja Viva,
    separando COP y USD, e incluye alertas del estado patrimonial y de insolvencia de cuentas.
    """
    total_ingresos_cop = 0.0
    total_gastos_cop = 0.0
    total_ingresos_usd = 0.0
    total_gastos_usd = 0.0
    
    for tx in transactions:
        tx_type = tx.get("type", "").upper()
        # Ignorar transferencias para el cálculo de ingresos y gastos consolidados
        if tx_type == "TRANSFERENCIA":
            continue
            
        net_value = tx.get("net_value")
        if net_value is None:
            net_value = 0.0
        else:
            try:
                net_value = float(net_value)
            except (ValueError, TypeError):
                net_value = 0.0
                
        currency = tx.get("transaction_currency", "COP")
        if currency == "USD":
            if tx_type == "INGRESO":
                total_ingresos_usd += net_value
            elif tx_type == "GASTO":
                total_gastos_usd += net_value
        else: # Por defecto COP
            if tx_type == "INGRESO":
                total_ingresos_cop += net_value
            elif tx_type == "GASTO":
                total_gastos_cop += net_value
            
    balance_neto_cop = total_ingresos_cop - total_gastos_cop
    patrimonio_cop = capital_inicial_cop + balance_neto_cop
    
    balance_neto_usd = total_ingresos_usd - total_gastos_usd
    patrimonio_usd = capital_inicial_usd + balance_neto_usd
    
    alerts = []
    status = "NOMINAL"
    
    # Alertas agregadas
    if balance_neto_cop < 0:
        alerts.append("⚠️ [DÉFICIT COP] El balance neto actual en COP es negativo.")
        status = "ALERTA_DEFICIT"
    if balance_neto_usd < 0:
        alerts.append("⚠️ [DÉFICIT USD] El balance neto actual en USD es negativo.")
        status = "ALERTA_DEFICIT"
        
    if patrimonio_cop < 0:
        alerts.append("🚨 [INSOLVENCIA COP] ¡El patrimonio neto en COP es menor a cero!")
        status = "INSOLVENTE"
    if patrimonio_usd < 0:
        alerts.append("🚨 [INSOLVENCIA USD] ¡El patrimonio neto en USD es menor a cero!")
        status = "INSOLVENTE"
        
    # Verificar insolvencia por cuenta individual
    if accounts:
        for acc in accounts:
            curr_bal = float(acc.get("current_balance") or 0.0)
            name = acc.get("name", "Cuenta")
            currency = acc.get("currency", "COP")
            acc_type = acc.get("type", "")
            
            if acc_type == "Crédito":
                # Alerta si excede un límite de crédito de -2,000,000 COP o -500 USD
                limit = -2000000.0 if currency == "COP" else -500.0
                if curr_bal < limit:
                    alerts.append(f"🚨 [LÍMITE EXCEDIDO] La cuenta de crédito '{name}' ha superado su límite con un saldo de {curr_bal:,.2f} {currency}.")
                    status = "INSOLVENTE"
            else:
                # Alerta si cualquier cuenta de ahorros/efectivo tiene saldo negativo
                if curr_bal < 0:
                    alerts.append(f"🚨 [SALDO NEGATIVO] La cuenta '{name}' está sobregirada con un saldo de {curr_bal:,.2f} {currency}.")
                    status = "INSOLVENTE"
        
    return {
        "total_ingresos_cop": round(total_ingresos_cop, 2),
        "total_gastos_cop": round(total_gastos_cop, 2),
        "balance_neto_cop": round(balance_neto_cop, 2),
        "capital_inicial_cop": round(capital_inicial_cop, 2),
        "patrimonio_cop": round(patrimonio_cop, 2),
        
        "total_ingresos_usd": round(total_ingresos_usd, 2),
        "total_gastos_usd": round(total_gastos_usd, 2),
        "balance_neto_usd": round(balance_neto_usd, 2),
        "capital_inicial_usd": round(capital_inicial_usd, 2),
        "patrimonio_usd": round(patrimonio_usd, 2),
        
        # Retrocompatibilidad
        "total_ingresos": round(total_ingresos_cop + total_ingresos_usd * 4000.0, 2),
        "total_gastos": round(total_gastos_cop + total_gastos_usd * 4000.0, 2),
        "balance_neto": round(balance_neto_cop + balance_neto_usd * 4000.0, 2),
        "capital_inicial": round(capital_inicial_cop + capital_inicial_usd * 4000.0, 2),
        "patrimonio": round(patrimonio_cop + patrimonio_usd * 4000.0, 2),
        
        "status": status,
        "alerts": alerts
    }


def validate_pocket_budget(
    pocket_balance: float,
    transaction_expense: float,
    pocket_name: str
) -> bool:
    """
    Valida si un gasto propuesto excede el saldo restante en un bolsillo ("Pocket").
    Lanza una excepción descriptiva si se viola la regla de aislamiento de capital.
    """
    if transaction_expense <= 0:
        return True
        
    if transaction_expense > pocket_balance:
        raise ExcedeLimitePocketError(
            f"❌ [EXCEDE LIMITE DE INVERSIÓN] La transacción por ${transaction_expense:.2f} "
            f"excede el saldo restante de ${pocket_balance:.2f} en el bolsillo '{pocket_name}'."
        )
        
    return True
