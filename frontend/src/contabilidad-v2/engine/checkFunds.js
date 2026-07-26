/* ============================================================
   checkFunds.js — Chequeo de disponible antes de registrar.

   Espeja la semántica de fin_sys_core/incremental_balance.py
   (calcular_delta_cuenta) para anticipar en qué queda el saldo.

   ESTIMACIÓN, no verdad contable: el net_value real lo calcula
   el tax_motor en el backend, así que con IVA/GMF el egreso real
   puede ser algo mayor. Sirve para advertir, no para bloquear.
   ============================================================ */

/** Las cuentas de crédito viven en negativo por diseño. */
export function esCuentaCredito(acc) {
  const t = String(acc?.type || '').toLowerCase();
  return t.startsWith('cred') || t.startsWith('créd');
}

/** Convierte un valor de txCurrency a la moneda de la cuenta. */
function enMonedaCuenta(valor, txCurrency, accountCurrency, trm) {
  if (txCurrency === accountCurrency) return valor;
  if (txCurrency === 'USD' && accountCurrency === 'COP') return valor * trm;
  if (txCurrency === 'COP' && accountCurrency === 'USD') return trm > 0 ? valor / trm : 0;
  return valor;
}

/**
 * @returns {null | {account, saldoActual, egreso, saldoResultante}}
 *   null  → no hay nada que advertir (ingreso, sin cuenta, o queda en positivo)
 *   objeto → la operación deja la cuenta en negativo
 */
export function checkFunds({ accounts, selectedAccountId, formType, amount, txCurrency, trmValue }) {
  const tipo = String(formType || '').toUpperCase();
  if (tipo !== 'GASTO' && tipo !== 'TRANSFERENCIA') return null;

  const account = (accounts || []).find(a => String(a.id) === String(selectedAccountId));
  if (!account) return null;                       // sin cuenta asignada no hay saldo que controlar
  if (esCuentaCredito(account)) return null;       // el cupo lo controla el límite de crédito

  const monto = parseFloat(amount);
  if (!Number.isFinite(monto) || monto <= 0) return null;

  const accCurrency = account.currency || 'COP';
  const trm = parseFloat(trmValue) || 1.0;

  // TRANSFERENCIA descuenta amount tal cual (igual que el backend);
  // GASTO descuenta el valor convertido a la moneda de la cuenta.
  const egreso = tipo === 'TRANSFERENCIA'
    ? monto
    : enMonedaCuenta(monto, txCurrency || 'COP', accCurrency, trm);

  const saldoActual = Number(account.current_balance || 0);
  const saldoResultante = saldoActual - egreso;

  if (saldoResultante >= 0) return null;

  return { account, saldoActual, egreso, saldoResultante };
}

/** Texto del diálogo de confirmación. */
export function mensajeSobregiro({ account, saldoActual, egreso, saldoResultante }) {
  const cur = account.currency || 'COP';
  const f = (n) => `${cur === 'COP' ? '$' : ''}${Number(n).toLocaleString('es-CO', { maximumFractionDigits: 2 })} ${cur}`;
  return [
    `⚠ FONDOS INSUFICIENTES EN "${account.name}"`,
    '',
    `Saldo actual:      ${f(saldoActual)}`,
    `Esta operación:   -${f(egreso)}`,
    `Saldo resultante:  ${f(saldoResultante)}`,
    '',
    'La cuenta quedará sobregirada. El monto real puede variar por IVA/GMF.',
    '',
    '¿Registrar de todas formas?',
  ].join('\n');
}
