/* Nueva exportación 13.5-c — períodos y paquetes (lógica pura). */
import { describe, it, expect } from 'vitest';
import { rangoRelativo, atajoDe, rangoMes } from './periodos.js';
import {
  paqueteDeHojas, hojasDePaquete, recetaPeriodo, validarPeriodo, recetaTransacciones,
  filtrarTransacciones, distintos, totalesPorMoneda, PERSONALIZADO,
} from './paquetes.js';

const d = (s) => { const [a, m, dd] = s.split('-').map(Number); return new Date(a, m - 1, dd); };

describe('períodos relativos', () => {
  it('mes anterior, también el 1 de enero', () => {
    expect(rangoRelativo('mes_anterior', d('2026-10-06'))).toEqual({ desde: '2026-09-01', hasta: '2026-09-30' });
    expect(rangoRelativo('mes_anterior', d('2026-01-01'))).toEqual({ desde: '2025-12-01', hasta: '2025-12-31' });
    expect(rangoRelativo('mes_anterior', d('2024-03-15'))).toEqual({ desde: '2024-02-01', hasta: '2024-02-29' });
  });
  it('bimestre del IVA anterior (ene-feb … nov-dic)', () => {
    expect(rangoRelativo('bimestre_anterior', d('2026-10-06'))).toEqual({ desde: '2026-07-01', hasta: '2026-08-31' });
    expect(rangoRelativo('bimestre_anterior', d('2026-09-01'))).toEqual({ desde: '2026-07-01', hasta: '2026-08-31' });
    expect(rangoRelativo('bimestre_anterior', d('2026-02-10'))).toEqual({ desde: '2025-11-01', hasta: '2025-12-31' });
  });
  it('trimestre anterior y años', () => {
    expect(rangoRelativo('trimestre_anterior', d('2026-10-06'))).toEqual({ desde: '2026-07-01', hasta: '2026-09-30' });
    expect(rangoRelativo('trimestre_anterior', d('2026-02-01'))).toEqual({ desde: '2025-10-01', hasta: '2025-12-31' });
    expect(rangoRelativo('anio_corrido', d('2026-10-06'))).toEqual({ desde: '2026-01-01', hasta: '2026-10-06' });
    expect(rangoRelativo('anio_anterior', d('2026-10-06'))).toEqual({ desde: '2025-01-01', hasta: '2025-12-31' });
    expect(rangoRelativo('mes_actual', d('2026-10-06'))).toEqual({ desde: '2026-10-01', hasta: '2026-10-06' });
  });
  it('reconoce el atajo de un rango y arma el rango de un mes', () => {
    expect(atajoDe('2026-09-01', '2026-09-30', d('2026-10-06'))).toBe('mes_anterior');
    expect(atajoDe('2026-09-02', '2026-09-30', d('2026-10-06'))).toBeNull();
    expect(rangoMes(2026, 2)).toEqual({ desde: '2026-02-01', hasta: '2026-02-28' });
    expect(() => rangoRelativo('nada')).toThrow();
  });
});

const PRE = [
  { clave: 'cierre_mes', hojas: ['diario', 'mayor', 'balance_prueba', 'estado_resultados', 'balance_general'] },
  { clave: 'banco', hojas: ['estado_resultados', 'balance_general'] },
];

describe('paquetes y receta', () => {
  it('hojas exactas → paquete; cualquier otra combinación → personalizado', () => {
    expect(paqueteDeHojas(PRE, ['balance_general', 'estado_resultados'])).toBe('banco');
    expect(paqueteDeHojas(PRE, ['caratula', 'estado_resultados', 'balance_general'])).toBe('banco');
    expect(paqueteDeHojas(PRE, ['estado_resultados'])).toBe(PERSONALIZADO);
    expect(hojasDePaquete(PRE, 'banco')).toEqual(['estado_resultados', 'balance_general']);
  });
  const base = { desde: '2026-09-01', hasta: '2026-09-30', hojas: ['diario'], empresas: [], nivelPuc: '',
    tipos: [], moneda: '', terceros: [], categorias: '', cuentasPuc: '', nombre: '', paquete: '', atajo: '' };
  it('receta de período: consolidado, una empresa o varias, y solo los filtros usados', () => {
    expect(recetaPeriodo(base)).toEqual({ receta: { modo: 'periodo', desde: '2026-09-01', hasta: '2026-09-30', hojas: ['diario'] }, paquete: PERSONALIZADO });
    expect(recetaPeriodo({ ...base, empresas: [3] }).receta.portfolio_id).toBe(3);
    expect(recetaPeriodo({ ...base, empresas: [3, 5] }).receta.portfolios).toEqual([3, 5]);
    const r = recetaPeriodo({ ...base, paquete: 'cierre_mes', atajo: 'mes_anterior', nivelPuc: 'cuenta',
      tipos: ['GASTO'], categorias: 'Arriendo, Servicios ', cuentasPuc: '5135,', nombre: ' Para el banco ' });
    expect(r.paquete).toBe('cierre_mes');
    expect(r.receta).toMatchObject({ nivel_puc: 'cuenta', relativo: 'mes_anterior', nombre: 'Para el banco',
      filtros: { tipos: ['GASTO'], categorias: ['Arriendo', 'Servicios'], cuentas_puc: ['5135'] } });
  });
  it('valida el formulario', () => {
    expect(validarPeriodo(base)).toBeNull();
    expect(validarPeriodo({ ...base, hasta: '' })).toMatch(/fecha final/);
    expect(validarPeriodo({ ...base, desde: '2026-10-01' })).toMatch(/posterior/);
    expect(validarPeriodo({ ...base, hojas: [] })).toMatch(/libro/);
  });
  it('relación de transacciones', () => {
    expect(recetaTransacciones([4, 9], ' Para auditoría ')).toEqual({ receta: { modo: 'transacciones', tx_ids: [4, 9], nombre: 'Para auditoría' }, paquete: null });
  });
});

const TXS = [
  { id: 1, transaction_date: '2026-09-03', concept: 'Pago arriendo oficina', category: 'Arriendo', type: 'GASTO', portfolio_name: 'Pegasus', third_party_id: 7, third_party_name: 'Inmobiliaria', amount: 1000, transaction_currency: 'COP' },
  { id: 2, transaction_date: '2026-09-20', concept: 'Venta servicio', category: 'Ventas', type: 'INGRESO', portfolio_name: 'Blu', third_party_id: 8, third_party_name: 'Cliente Ñandú', amount: 5000, transaction_currency: 'COP' },
  { id: 3, transaction_date: '2026-10-01', concept: 'Licencia', category: 'Software', type: 'GASTO', portfolio_name: 'Pegasus', third_party_id: 9, third_party_name: 'Proveedor', amount: 20, transaction_currency: 'USD' },
];

describe('selector de transacciones', () => {
  it('filtra por fecha, empresa, tipo, categoría, tercero y texto (sin tildes ni mayúsculas)', () => {
    expect(filtrarTransacciones(TXS, { desde: '2026-09-01', hasta: '2026-09-30' }).map((t) => t.id)).toEqual([1, 2]);
    expect(filtrarTransacciones(TXS, { empresa: 'Pegasus', tipo: 'GASTO' }).map((t) => t.id)).toEqual([1, 3]);
    expect(filtrarTransacciones(TXS, { categoria: 'Ventas' }).map((t) => t.id)).toEqual([2]);
    expect(filtrarTransacciones(TXS, { tercero: 9 }).map((t) => t.id)).toEqual([3]);
    expect(filtrarTransacciones(TXS, { q: 'nandu' }).map((t) => t.id)).toEqual([2]);
    expect(filtrarTransacciones(TXS, { q: 'pago oficina' }).map((t) => t.id)).toEqual([1]);
    expect(filtrarTransacciones(TXS, {}).length).toBe(3);
  });
  it('desplegables y totales sin mezclar monedas', () => {
    expect(distintos(TXS, 'portfolio_name')).toEqual(['Blu', 'Pegasus']);
    expect(totalesPorMoneda(TXS)).toEqual({ COP: 6000, USD: 20 });
  });
});
