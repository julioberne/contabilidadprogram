/* Casillas del Libro Diario (13.5, CA-135-08) — lógica pura. */
import { describe, it, expect } from 'vitest';
import { alternarId, marcarVarias, seleccionadas, estadoCabecera, resumenSeleccion, estaMarcada,
  resumenFiltro, porMonedaDeTotales } from './seleccion.js';

const TXS = [
  { id: 1, type: 'INGRESO', net_value: 1000, transaction_currency: 'COP' },
  { id: 2, type: 'GASTO', net_value: 300, transaction_currency: 'COP' },
  { id: 3, type: 'GASTO', net_value: 20, transaction_currency: 'USD' },
  { id: 4, type: 'TRANSFERENCIA', net_value: 500 },
];

describe('selección del Libro Diario', () => {
  it('alterna y marca en bloque sin mutar el Set original', () => {
    const a = new Set([1]);
    expect([...alternarId(a, 2)]).toEqual([1, 2]);
    expect([...alternarId(a, 1)]).toEqual([]);
    expect([...a]).toEqual([1]);
    expect([...marcarVarias(a, TXS, true)].sort()).toEqual([1, 2, 3, 4]);
    expect([...marcarVarias(new Set([1, 2, 9]), TXS, false)]).toEqual([9]);
  });

  it('exporta solo lo marcado que está cargado (un id de otra empresa no cuenta)', () => {
    const sel = new Set([3, 1, 99]);
    expect(seleccionadas(sel, TXS).map((t) => t.id)).toEqual([1, 3]);
    expect(estadoCabecera(sel, TXS)).toBe('algunas');
    expect(estadoCabecera(new Set([99]), TXS)).toBe('ninguna');
    expect(estadoCabecera(new Set([1, 2, 3, 4]), TXS)).toBe('todas');
    expect(estadoCabecera(new Set(), [])).toBe('ninguna');
  });

  it('totales con valor neto, por moneda; transferencias cuentan pero no suman', () => {
    expect(resumenSeleccion(TXS)).toEqual({
      n: 4,
      porMoneda: { COP: { ingresos: 1000, gastos: 300 }, USD: { ingresos: 0, gastos: 20 } },
    });
    expect(resumenSeleccion([])).toEqual({ n: 0, porMoneda: {} });
  });
});

describe('«Marcar todo» por filtro (H8.3)', () => {
  const FILTRO = { query: 'portfolio=A', n: 500, porMoneda: { COP: { ingresos: 5000, gastos: 900 } } };

  it('todo está marcado salvo lo desmarcado a mano', () => {
    const sel = new Set([2]);
    expect(estaMarcada(sel, FILTRO, 1)).toBe(true);
    expect(estaMarcada(sel, FILTRO, 2)).toBe(false);
    expect(estaMarcada(sel, null, 2)).toBe(true);
    expect(estaMarcada(sel, null, 1)).toBe(false);
  });

  it('la cabecera refleja las excepciones', () => {
    expect(estadoCabecera(new Set(), TXS, FILTRO)).toBe('todas');
    expect(estadoCabecera(new Set([1]), TXS, FILTRO)).toBe('algunas');
    expect(estadoCabecera(new Set([1, 2, 3, 4]), TXS, FILTRO)).toBe('ninguna');
  });

  it('el resumen es lo del servidor menos las filas desmarcadas', () => {
    expect(resumenFiltro(FILTRO, [])).toEqual({ n: 500, porMoneda: FILTRO.porMoneda });
    expect(resumenFiltro(FILTRO, [TXS[0], TXS[1]])).toEqual({
      n: 498, porMoneda: { COP: { ingresos: 4000, gastos: 600 } },
    });
  });

  it('los totales del servidor toman la misma forma; USD solo si hay', () => {
    expect(porMonedaDeTotales({ ingresos_cop: 10, gastos_cop: 4, ingresos_usd: 0, gastos_usd: 0 }))
      .toEqual({ COP: { ingresos: 10, gastos: 4 } });
    expect(porMonedaDeTotales({ ingresos_cop: 10, gastos_cop: 4, ingresos_usd: 0, gastos_usd: 2 }))
      .toEqual({ COP: { ingresos: 10, gastos: 4 }, USD: { ingresos: 0, gastos: 2 } });
  });
});
