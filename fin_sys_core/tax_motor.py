# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 - Motor de Impuestos (tax_motor.py)
--------------------------------------------------
Este módulo maneja de forma determinista el cálculo de los impuestos y tasas
aditivas o deductivas asociadas a cada transacción financiera.
"""

from typing import List, Dict, Any, Optional

# Tasa del IVA estándar en Colombia (19%)
IVA_STANDARD_RATE = 0.19

# Tasa del Gravamen a los Movimientos Financieros (4x1000)
GMF_RATE = 0.004


def calculate_iva(base_amount: float) -> float:
    """
    Calcula el valor del IVA aditivo estándar (19%).
    Ejemplo: Para un servicio de $100.00, el IVA aditivo es $19.00.
    """
    if base_amount is None or base_amount <= 0:
        return 0.0
    return round(base_amount * IVA_STANDARD_RATE, 2)


def calculate_gmf(amount: float) -> float:
    """
    Calcula el valor del GMF (4 por mil = 0.004) aplicado a transacciones financieras.
    Ejemplo: Para un retiro bancario o egreso de $1,000.00, el GMF es $4.00.
    """
    if amount is None or amount <= 0:
        return 0.0
    return round(amount * GMF_RATE, 2)


def process_transaction_taxes(
    base_amount: float,
    apply_iva: bool = False,
    apply_gmf: bool = False,
    custom_taxes: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, float]:
    """
    Procesa el conjunto de impuestos aplicados a una transacción y calcula el impacto neto.
    
    Parámetros:
    - base_amount: El importe bruto o subtotal de la transacción.
    - apply_iva: Booleano para activar el cobro del 19% de IVA (Aditivo).
    - apply_gmf: Booleano para activar la tasa del 4x1000 (Deductivo en egresos o adicional).
    - custom_taxes: Lista de diccionarios con impuestos personalizados:
        [
          {"name": "Retencion", "rate": 0.04, "type": "DEDUCTIVE"},
          {"name": "Tasa Local", "amount": 500.0, "type": "ADDITIVE"}
        ]
        
    Devuelve un diccionario con los montos de cada impuesto e 'impacto_neto'.
    """
    if base_amount is None or base_amount <= 0:
        return {
            "base_amount": 0.0,
            "iva_amount": 0.0,
            "gmf_amount": 0.0,
            "custom_taxes_total": 0.0,
            "net_value": 0.0
        }

    iva_amount = calculate_iva(base_amount) if apply_iva else 0.0
    gmf_amount = calculate_gmf(base_amount) if apply_gmf else 0.0
    
    additive_custom = 0.0
    deductive_custom = 0.0
    
    if custom_taxes:
        for tax in custom_taxes:
            tax_type = tax.get("type", "ADDITIVE").upper()
            
            # El impuesto personalizado puede venir como una tasa (%) o un monto fijo
            if "rate" in tax:
                tax_val = round(base_amount * tax["rate"], 2)
            else:
                tax_val = round(tax.get("amount", 0.0), 2)
                
            if tax_type == "ADDITIVE":
                additive_custom += tax_val
            elif tax_type == "DEDUCTIVE":
                deductive_custom += tax_val

    # Matemáticas de impacto neto:
    # Neto = Base + IVA (Aditivo) + Tasas Aditivas Personalizadas - GMF (Deductivo) - Tasas Deductivas Personalizadas
    # Nota: El GMF (4x1000) actúa como un egreso deducible que incrementa el gasto del banco 
    # o disminuye el valor neto percibido según el tipo de transacción.
    
    net_value = base_amount + iva_amount + additive_custom - gmf_amount - deductive_custom
    
    return {
        "base_amount": round(base_amount, 2),
        "iva_amount": round(iva_amount, 2),
        "gmf_amount": round(gmf_amount, 2),
        "custom_taxes_total": round(additive_custom - deductive_custom, 2),
        "net_value": round(net_value, 2)
    }
