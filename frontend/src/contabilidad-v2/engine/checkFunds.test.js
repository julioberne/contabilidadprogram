import { describe, it, expect } from 'vitest';
import { checkFunds, esCuentaCredito } from './checkFunds.js';

const cop = { id: 1, name: 'Efectivo', type: 'Efectivo', currency: 'COP', current_balance: 100000 };
const usd = { id: 2, name: 'Binance', type: 'Crypto', currency: 'USD', current_balance: 50 };
const credito = { id: 3, name: 'Davivienda', type: 'Crédito', currency: 'COP', current_balance: -200000 };
const accounts = [cop, usd, credito];

const base = { accounts, selectedAccountId: '1', formType: 'GASTO', txCurrency: 'COP', trmValue: '4000' };

describe('checkFunds', () => {
  it('no advierte si hay saldo suficiente', () => {
    expect(checkFunds({ ...base, amount: '50000' })).toBeNull();
  });

  it('advierte cuando el gasto excede el saldo', () => {
    const r = checkFunds({ ...base, amount: '150000' });
    expect(r).not.toBeNull();
    expect(r.saldoResultante).toBe(-50000);
    expect(r.account.name).toBe('Efectivo');
  });

  it('no advierte en INGRESO', () => {
    expect(checkFunds({ ...base, formType: 'INGRESO', amount: '999999' })).toBeNull();
  });

  it('exime a las cuentas de crédito', () => {
    expect(checkFunds({ ...base, selectedAccountId: '3', amount: '999999' })).toBeNull();
    expect(esCuentaCredito(credito)).toBe(true);
  });

  it('no advierte si no hay cuenta seleccionada', () => {
    expect(checkFunds({ ...base, selectedAccountId: '', amount: '999999' })).toBeNull();
  });

  it('convierte USD→COP con la TRM (gasto en USD sobre cuenta COP)', () => {
    // 30 USD * 4000 = 120.000 COP > 100.000 de saldo
    const r = checkFunds({ ...base, txCurrency: 'USD', amount: '30' });
    expect(r).not.toBeNull();
    expect(r.egreso).toBe(120000);
    expect(r.saldoResultante).toBe(-20000);
  });

  it('convierte COP→USD con la TRM (gasto en COP sobre cuenta USD)', () => {
    // 240.000 COP / 4000 = 60 USD > 50 de saldo
    const r = checkFunds({ ...base, selectedAccountId: '2', amount: '240000' });
    expect(r).not.toBeNull();
    expect(r.egreso).toBe(60);
    expect(r.saldoResultante).toBe(-10);
  });

  it('TRANSFERENCIA descuenta amount tal cual, como el backend', () => {
    const r = checkFunds({ ...base, formType: 'TRANSFERENCIA', txCurrency: 'USD', amount: '150000' });
    expect(r.egreso).toBe(150000);  // sin conversión: espeja calcular_delta_cuenta
  });

  it('ignora montos inválidos', () => {
    expect(checkFunds({ ...base, amount: '' })).toBeNull();
    expect(checkFunds({ ...base, amount: '-500' })).toBeNull();
  });

  it('saldo exacto a cero no advierte', () => {
    expect(checkFunds({ ...base, amount: '100000' })).toBeNull();
  });
});
