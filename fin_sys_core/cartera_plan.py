# -*- coding: utf-8 -*-
"""Plan de pagos de cartera (Fase 1 — modo préstamo).

Todo DERIVADO de los datos: nada de schedulers ni estado extra. Reglas:

- La cuota mínima se exige POR CORTE (payment_frequency días desde start_date):
  al cumplirse k cortes, el deudor debe llevar abonado ≥ k × cuota mínima.
  Si lleva menos y aún hay saldo → EN MORA (independiente de VENCIDO, que es
  la fecha final due_date).
- Interés simple sobre saldo: tasa % prorrateada por día (MENSUAL/30, ANUAL/365)
  desde el último abono (o el inicio). Cada abono se aplica PRIMERO a interés
  devengado y luego a capital — regla estándar de préstamos.
"""
from datetime import date, timedelta
from typing import Any, Dict, Optional


def tasa_diaria(rate, period) -> float:
    if not rate:
        return 0.0
    base = 30.0 if (period or "MENSUAL").upper() == "MENSUAL" else 365.0
    return float(rate) / 100.0 / base


def interes_devengado(saldo, rate, period, desde: Optional[date], hoy: Optional[date] = None):
    """Interés simple acumulado desde `desde` hasta `hoy`. → (monto, días)."""
    hoy = hoy or date.today()
    if not rate or not desde or float(saldo or 0) <= 0:
        return 0.0, 0
    dias = max(0, (hoy - desde).days)
    return round(float(saldo) * tasa_diaria(rate, period) * dias, 2), dias


def proximo_corte_de(start: Optional[date], freq: int, hoy: Optional[date] = None) -> Optional[str]:
    """Próxima fecha de corte esperada según start_date + frecuencia."""
    hoy = hoy or date.today()
    if not start or not freq or freq <= 0:
        return None
    cortes = max(0, (hoy - start).days // freq)
    return str(start + timedelta(days=(cortes + 1) * freq))


def plan_info(row: Dict[str, Any], abonado_total: float,
              last_event_date: Optional[date], hoy: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """Anotación derivada del plan para una fila del ledger.

    → None cuando la cuenta no tiene plan (sin cuota mínima ni interés):
    las cuentas viejas siguen exactamente igual que antes.
    """
    mp = float(row.get("min_payment") or 0)
    rate = float(row.get("interest_rate") or 0)
    if mp <= 0 and rate <= 0:
        return None

    hoy = hoy or date.today()
    saldo = float(row.get("remaining_balance") or 0)
    freq = int(row.get("payment_frequency") or 30)
    start = row.get("start_date")

    info: Dict[str, Any] = {}
    cortes = 0
    if start and freq > 0:
        cortes = max(0, (hoy - start).days // freq)
        info["proximo_corte"] = str(start + timedelta(days=(cortes + 1) * freq))
        info["cortes_cumplidos"] = cortes

    if mp > 0:
        exigido = round(cortes * mp, 2)
        abonado = round(float(abonado_total or 0), 2)
        info["cuota_minima"] = mp
        info["cuota_exigida"] = exigido
        info["abonado_total"] = abonado
        # medio centavo de tolerancia por redondeos de NUMERIC
        info["en_mora"] = saldo > 0 and (abonado + 0.005) < exigido
        # Calculadora de mora (pedido 04-sep): CUÁNTO se debe de atraso y a
        # cuántas cuotas equivale — lo que hay que pagar para quedar al día.
        if info["en_mora"]:
            mora = round(exigido - abonado, 2)
            info["mora_monto"] = mora
            info["cuotas_atrasadas"] = int(-(-mora // mp))   # ceil sin math

    if rate > 0:
        desde = last_event_date or start
        monto, dias = interes_devengado(saldo, rate, row.get("interest_period"), desde, hoy)
        info["interest_rate"] = rate
        info["interest_period"] = (row.get("interest_period") or "MENSUAL").upper()
        info["interes_devengado"] = monto
        info["interes_dias"] = dias

    return info


def dividir_abono(amount: float, saldo: float, rate, period,
                  last_event_date: Optional[date], hoy: Optional[date] = None):
    """Divide un abono en (interés, capital, saldo_nuevo).

    Sin tasa → todo a capital (comportamiento histórico intacto).
    El interés devengado se cobra primero; lo que sobre amortiza capital.
    """
    amount = float(amount)
    saldo = float(saldo)
    if not rate:
        principal = min(amount, saldo)
        return 0.0, round(principal, 2), round(max(0.0, saldo - amount), 2)
    interes, _dias = interes_devengado(saldo, rate, period, last_event_date, hoy)
    interest_part = round(min(amount, interes), 2)
    principal_part = round(min(amount - interest_part, saldo), 2)
    return interest_part, principal_part, round(max(0.0, saldo - principal_part), 2)
