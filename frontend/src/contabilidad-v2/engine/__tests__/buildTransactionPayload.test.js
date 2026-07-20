/* ============================================================
   buildTransactionPayload.test.js — Seguro del port v1 → v2.
   Los payloads esperados están derivados A MANO de la lógica
   de handleRegister en hooks/useTransactionForm.js (v1).
   Si un test falla, el port rompió la paridad con v1.
   ============================================================ */
import { describe, it, expect } from 'vitest';
import { buildTransactionPayload, deriveAccountState } from '../buildTransactionPayload.js';

const ACCOUNTS = [
  { id: 1, name: 'Banco M', currency: 'COP' },
  { id: 2, name: 'Cash USD', currency: 'USD' },
];

/** Estado base: los defaults de useTransactionForm (v1) */
function baseState(overrides = {}) {
  return {
    activePortfolio: 'Negocio A',
    accounts: ACCOUNTS,
    formType: 'GASTO',
    amount: '100000',
    concept: 'Compra insumos',
    date: '2026-07-19',
    geoMapsLink: '',
    paymentMethod: 'Efectivo',
    category: 'Ventas',
    selectedAccountId: '',
    selectedDestAccountId: '',
    trmValue: '1.0',
    txCurrency: 'COP',
    thirdPartyType: 'NIT',
    thirdPartyNumber: '',
    thirdPartyName: '',
    thirdPartyEmail: '',
    thirdPartyPhone: '',
    thirdPartyWebsite: '',
    applyIva: false,
    applyGmf: false,
    applyPropina: false,
    isRecurring: false,
    recurrenceInterval: 'MENSUAL',
    recurrenceDays: 30,
    recurrenceMaxReps: '',
    recurrenceStartDate: '2026-07-19',
    recurrenceEndDate: '',
    cxcCxpEnabled: false,
    cxcCxpType: 'CXC',
    cxcCxpDueDate: '',
    cxcCxpTerm: 'Corto',
    cxcCxpValue: '',
    assetEnabled: false,
    assetName: '',
    assetValue: '',
    assetTag: '',
    assetVincularImporte: false,
    assetEstablecerActivo: false,
    assetRecurrente: false,
    evidenceFilePath: '',
    selectedTags: [],
    customTaxesList: [],
    ...overrides,
  };
}

describe('deriveAccountState (semántica v1)', () => {
  it('GASTO: cross-currency cuando txCurrency difiere de la cuenta origen', () => {
    const r = deriveAccountState({
      accounts: ACCOUNTS, selectedAccountId: '1', selectedDestAccountId: '',
      formType: 'GASTO', txCurrency: 'USD',
    });
    expect(r.sourceAcc.name).toBe('Banco M');
    expect(r.isCrossCurrency).toBe(true);
  });

  it('TRANSFERENCIA: cross-currency cuando origen y destino difieren en divisa', () => {
    const r = deriveAccountState({
      accounts: ACCOUNTS, selectedAccountId: '1', selectedDestAccountId: '2',
      formType: 'TRANSFERENCIA', txCurrency: 'COP',
    });
    expect(r.isCrossCurrency).toBe(true);
  });

  it('sin cuenta seleccionada no es cross-currency (falsy)', () => {
    const r = deriveAccountState({
      accounts: ACCOUNTS, selectedAccountId: '', selectedDestAccountId: '',
      formType: 'GASTO', txCurrency: 'USD',
    });
    expect(r.sourceAcc).toBeUndefined();
    expect(r.isCrossCurrency).toBeFalsy();
  });
});

describe('buildTransactionPayload — paridad con handleRegister v1', () => {
  it('GASTO completo: IVA+GMF+propina+tasa custom+recurrencia+cartera+activo+tags', () => {
    const payload = buildTransactionPayload(baseState({
      selectedAccountId: '1',
      category: '5105 - Gastos de personal',
      thirdPartyNumber: '900123456-1',
      thirdPartyName: 'Proveedor SAS',
      thirdPartyEmail: 'prov@sas.co',
      applyIva: true,
      applyGmf: true,
      applyPropina: true,
      customTaxesList: [
        { name: 'ReteICA', rate: 1.104, type: 'DEDUCTIVE', checked: true },
        { name: 'NoAplica', rate: 5, type: 'ADDITIVE', checked: false },
      ],
      isRecurring: true,
      recurrenceInterval: 'PERSONALIZADO',
      recurrenceDays: '15',
      recurrenceMaxReps: '6',
      recurrenceEndDate: '2026-12-31',
      cxcCxpEnabled: true,
      cxcCxpType: 'CXP',
      cxcCxpDueDate: '2026-08-19',
      cxcCxpValue: '50000',
      assetEnabled: true,
      assetEstablecerActivo: true,
      assetVincularImporte: true,
      assetName: 'Impresora industrial',
      assetTag: 'equipos',
      assetRecurrente: true,
      evidenceFilePath: 'uploads/factura.png',
      geoMapsLink: 'https://maps.google.com/x',
      selectedTags: ['operativo', 'q3'],
    }));

    expect(payload).toEqual({
      portfolio_name: 'Negocio A',
      type: 'GASTO',
      amount: 100000,
      concept: 'Compra insumos',
      payment_method: 'Banco M',          // sourceAcc.name pisa a paymentMethod
      category: '5105 - Gastos de personal',
      third_party: {
        identification_type: 'NIT',
        identification_number: '900123456-1',
        name: 'Proveedor SAS',
        email: 'prov@sas.co',
        phone: null,
        website: null,
      },
      transaction_date: '2026-07-19',
      apply_iva: true,
      apply_gmf: true,
      account_id: 1,
      dest_account_id: null,               // solo aplica a TRANSFERENCIA
      trm: 1.0,                            // COP→COP: no cross-currency
      transaction_currency: 'COP',
      is_recurring: true,
      recurrence_interval: 'PERSONALIZADO',
      recurrence_days: 15,
      recurrence_max_reps: 6,
      recurrence_start_date: '2026-07-19',
      recurrence_end_date: '2026-12-31',
      custom_taxes: [
        { name: 'Propina (10%)', rate: 0.10, type: 'ADDITIVE' },
        // rate/100 con la aritmética flotante de JS, igual que v1
        { name: 'ReteICA', rate: 1.104 / 100, type: 'DEDUCTIVE' },
      ],
      cxc_cxp: {
        type: 'CXP',
        due_date: '2026-08-19',
        term: 'Corto',
        partial_value: 50000,
      },
      asset: {
        name: 'Impresora industrial',
        purchase_value: 100000,            // vincularImporte → amount
        custom_tag: 'equipos',
        establish_as_asset: true,
        is_passive_income_generator: true,
        recurrence_interval_days: 30,
        recurrence_amount: 100000,
      },
      evidence_file_path: 'uploads/factura.png',
      geo_maps_link: 'https://maps.google.com/x',
      tags: ['operativo', 'q3'],
    });
  });

  it('TRANSFERENCIA cross-currency: aplica TRM y dest_account_id', () => {
    const payload = buildTransactionPayload(baseState({
      formType: 'TRANSFERENCIA',
      amount: '400000',
      concept: 'Traslado a cuenta USD',
      selectedAccountId: '1',
      selectedDestAccountId: '2',
      trmValue: '4000',
    }));

    expect(payload.type).toBe('TRANSFERENCIA');
    expect(payload.account_id).toBe(1);
    expect(payload.dest_account_id).toBe(2);
    expect(payload.trm).toBe(4000);              // cross-currency → parseFloat(trmValue)
    expect(payload.payment_method).toBe('Banco M');
  });

  it('INGRESO en divisa distinta a la cuenta: cross-currency con TRM', () => {
    const payload = buildTransactionPayload(baseState({
      formType: 'INGRESO',
      selectedAccountId: '1',                     // COP
      txCurrency: 'USD',
      trmValue: '3950.5',
    }));
    expect(payload.trm).toBe(3950.5);
    expect(payload.dest_account_id).toBeNull();
  });

  it('defaults v1: tercero genérico, nulls, y trm=1.0 sin cuenta', () => {
    const payload = buildTransactionPayload(baseState());

    expect(payload.third_party).toEqual({
      identification_type: 'NIT',
      identification_number: '999999999',        // fallback v1
      name: 'Sin especificar',                   // fallback v1
      email: null,
      phone: null,
      website: null,
    });
    expect(payload.payment_method).toBe('Efectivo');  // sin sourceAcc → paymentMethod
    expect(payload.account_id).toBeNull();
    expect(payload.trm).toBe(1.0);
    expect(payload.custom_taxes).toBeNull();
    expect(payload.cxc_cxp).toBeNull();
    expect(payload.asset).toBeNull();
    expect(payload.tags).toBeNull();
    expect(payload.evidence_file_path).toBeNull();
    expect(payload.geo_maps_link).toBeNull();
    expect(payload.is_recurring).toBe(false);
    expect(payload.recurrence_interval).toBeNull();
    expect(payload.recurrence_days).toBeNull();
  });

  it('activo habilitado SIN establecerActivo no genera asset (regla v1)', () => {
    const payload = buildTransactionPayload(baseState({
      assetEnabled: true,
      assetEstablecerActivo: false,
      assetName: 'No debe aparecer',
    }));
    expect(payload.asset).toBeNull();
  });

  it('recurrencia MENSUAL no manda recurrence_days (solo PERSONALIZADO)', () => {
    const payload = buildTransactionPayload(baseState({
      isRecurring: true,
      recurrenceInterval: 'MENSUAL',
      recurrenceDays: '15',
    }));
    expect(payload.recurrence_interval).toBe('MENSUAL');
    expect(payload.recurrence_days).toBeNull();
    expect(payload.recurrence_start_date).toBe('2026-07-19');
  });
});
