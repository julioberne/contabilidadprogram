/* Vista 🗓 de cierres 13.5-d — lógica pura (CA-135-13). */
import { describe, it, expect } from 'vitest';
import { celda, mesAbierto, folioCorto, resumenFila } from './cierres.js';

const DATOS = {
  anio: 2026,
  celdas: {
    cierre_mes: { 1: { id: 4, folio: 'EXP-2026-0004', estado: 'VIGENTE' }, 8: { id: 9, folio: 'EXP-2026-0009', estado: 'CAMBIO' } },
    banco: {},
  },
};

describe('vista de cierres', () => {
  const hoy = new Date(2026, 9, 6);   // 6 de octubre
  it('lee la celda del paquete y mes', () => {
    expect(celda(DATOS, 'cierre_mes', 1).folio).toBe('EXP-2026-0004');
    expect(celda(DATOS, 'cierre_mes', 2)).toBeNull();
    expect(celda(DATOS, 'nada', 1)).toBeNull();
    expect(celda(null, 'cierre_mes', 1)).toBeNull();
  });
  it('un mes que no ha terminado no se puede cerrar', () => {
    expect(mesAbierto(2026, 10, hoy)).toBe(false);   // octubre en curso: se puede exportar lo corrido
    expect(mesAbierto(2026, 11, hoy)).toBe(true);
    expect(mesAbierto(2027, 1, hoy)).toBe(true);
    expect(mesAbierto(2025, 12, hoy)).toBe(false);
  });
  it('folio corto y resumen de la fila', () => {
    expect(folioCorto('EXP-2026-0009')).toBe('0009');
    expect(resumenFila(DATOS, 'cierre_mes', 2026, hoy)).toEqual({ cerrados: 2, cambiaron: 1, posibles: 10 });
    expect(resumenFila(DATOS, 'banco', 2026, hoy)).toEqual({ cerrados: 0, cambiaron: 0, posibles: 10 });
  });
});
