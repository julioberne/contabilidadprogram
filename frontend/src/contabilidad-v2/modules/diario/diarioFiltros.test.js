/* Búsqueda y filtros del Libro Diario (16-oct-2026): lógica pura. */
import { describe, it, expect } from 'vitest';
import {
  FILTROS_VACIOS, aCsv, aParametros, agregarEtiqueta, chipsActivos, codigoPuc,
  desdeParametros, filtroDeGrupo, filtrosActivos, rangoRapido,
} from './diarioFiltros.js';

const F = (extra = {}) => ({ ...FILTROS_VACIOS, ...extra });

describe('rangos rápidos', () => {
  const hoy = new Date(2026, 9, 16); // jueves 16-oct-2026
  it('calcula hoy, semana (lunes-domingo), mes, mes anterior, trimestre y año', () => {
    expect(rangoRapido('hoy', hoy)).toEqual({ desde: '2026-10-16', hasta: '2026-10-16' });
    expect(rangoRapido('semana', hoy)).toEqual({ desde: '2026-10-12', hasta: '2026-10-18' });
    expect(rangoRapido('mes', hoy)).toEqual({ desde: '2026-10-01', hasta: '2026-10-31' });
    expect(rangoRapido('mes_anterior', hoy)).toEqual({ desde: '2026-09-01', hasta: '2026-09-30' });
    expect(rangoRapido('trimestre', hoy)).toEqual({ desde: '2026-10-01', hasta: '2026-12-31' });
    expect(rangoRapido('anio_anterior', hoy)).toEqual({ desde: '2025-01-01', hasta: '2025-12-31' });
  });
  it('mes anterior en enero cae en diciembre del año pasado', () => {
    expect(rangoRapido('mes_anterior', new Date(2026, 0, 10))).toEqual({ desde: '2025-12-01', hasta: '2025-12-31' });
  });
});

describe('filtros ↔ parámetros', () => {
  it('sin filtros no hay nada activo ni parámetros', () => {
    expect(filtrosActivos(F())).toBe(false);
    expect(aParametros(F()).toString()).toBe('');
  });
  it('ida y vuelta conserva filtros, orden y agrupación', () => {
    const f = F({ q: 'cafe', tipos: ['GASTO'], terceros: [272, 5], etiquetas: ['Bonaire obra'],
      desde: '2026-10-01', hasta: '2026-10-31', rango: 'mes', banderas: ['duplicados'], empresas: '*' });
    const p = aParametros(f, { orden: 'monto_desc', agrupar: 'tercero' });
    const r = desdeParametros(`?${p}`);
    expect(r.filtros).toEqual(f);
    expect(r.orden).toBe('monto_desc');
    expect(r.agrupar).toBe('tercero');
    expect(filtrosActivos(r.filtros)).toBe(true);
  });
  it('solo el nombre del rango no cuenta como filtro', () => {
    expect(filtrosActivos(F({ rango: 'mes' }))).toBe(false);
  });
  it('ignora parámetros ajenos (ej. ?tab=) y ids no numéricos', () => {
    const r = desdeParametros('?tab=cuentas&terceros=3,x&orden=fecha_desc');
    expect(r.filtros.terceros).toEqual([3]);
    expect(r.filtros).not.toHaveProperty('tab');
  });
});

describe('chips', () => {
  it('cada chip quita SOLO su filtro', () => {
    const f = F({ q: 'x', terceros: [1, 2], monto_min: '100' });
    const chips = chipsActivos(f, { terceros: [{ id: 1, name: 'Tatiana' }] });
    expect(chips.map((c) => c.texto)).toEqual(['🔍 "x"', '👤 Tatiana', '👤 #2', '💲 $100 – …']);
    const sinTatiana = chips[1].quitar(f);
    expect(sinTatiana.terceros).toEqual([2]);
    expect(sinTatiana.q).toBe('x');
  });
});

describe('utilidades', () => {
  it('CSV con ; BOM, comillas y decimales con coma', () => {
    const csv = aCsv([{ id: 1, concept: 'Pago; "urgente"', net_value: 1500.5, tags: ['A', 'B'] }]);
    expect(csv.startsWith('﻿ID;Fecha')).toBe(true);
    expect(csv).toContain('"Pago; ""urgente"""');
    expect(csv).toContain('1500,5');
    expect(csv).toContain('A | B');
  });
  it('código PUC de la categoría', () => {
    expect(codigoPuc('5105 - Gastos de personal')).toBe('5105');
    expect(codigoPuc('Otros Gastos')).toBeNull();
    expect(codigoPuc(null)).toBeNull();
  });
  it('agregar etiqueta sin repetir (ignora mayúsculas) y devuelve el mismo arreglo si ya está', () => {
    const t = ['Obra'];
    expect(agregarEtiqueta(t, 'obra')).toBe(t);
    expect(agregarEtiqueta(t, 'Mercado')).toEqual(['Obra', 'Mercado']);
    expect(agregarEtiqueta(null, 'X')).toEqual(['X']);
  });
});

describe('clic en un grupo → filtro', () => {
  it('tercero, mes, etiqueta y "(sin …)"', () => {
    expect(filtroDeGrupo('tercero', { clave: 'Tatiana', ref: 272 }, F()).terceros).toEqual([272]);
    const mes = filtroDeGrupo('mes', { clave: '2026-02' }, F());
    expect([mes.desde, mes.hasta]).toEqual(['2026-02-01', '2026-02-28']);
    expect(filtroDeGrupo('etiqueta', { clave: 'Bonaire obra' }, F()).etiquetas).toEqual(['Bonaire obra']);
    expect(filtroDeGrupo('tercero', { clave: '(sin tercero)' }, F()).banderas).toEqual(['sin_tercero']);
    expect(filtroDeGrupo('tipo', { clave: 'GASTO' }, F({ tipos: ['GASTO'] }))).toBeNull();
  });
});
