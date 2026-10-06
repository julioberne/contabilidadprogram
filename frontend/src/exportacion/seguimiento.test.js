/* 📈 Seguimiento del cliente 13.6-c — lógica pura. */
import { describe, it, expect } from 'vitest';
import { textoEvento, horaCorta, tardanza } from './seguimiento.js';

describe('seguimiento del cliente', () => {
  it('cuenta qué hizo el cliente', () => {
    expect(textoEvento({ tipo: 'abrio' })).toBe('abrió el compendio');
    expect(textoEvento({ tipo: 'tx', concepto: 'Pago gym' })).toBe('abrió "Pago gym"');
    expect(textoEvento({ tipo: 'comprobante', j: 0, concepto: 'Taxi' })).toBe('vio el comprobante 1 de "Taxi"');
    expect(textoEvento({ tipo: 'tx', concepto: null })).toBe('abrió una transacción');
  });

  it('hora corta: hoy solo la hora, otro día con la fecha', () => {
    const ahora = new Date(2026, 9, 6, 15, 0);
    expect(horaCorta(new Date(2026, 9, 6, 14, 32).toISOString(), ahora)).toBe('14:32');
    expect(horaCorta(new Date(2026, 9, 5, 9, 5).toISOString(), ahora)).toMatch(/05\/10.*09:05/);
    expect(horaCorta(null, ahora)).toBe('—');
  });

  it('cuánto tardó en abrirlo', () => {
    expect(tardanza(null)).toBeNull();
    expect(tardanza(0.4)).toBe('menos de 1 h después de crearlo');
    expect(tardanza(2)).toBe('2 h después de crearlo');
    expect(tardanza(72)).toBe('3 días después de crearlo');
  });
});
