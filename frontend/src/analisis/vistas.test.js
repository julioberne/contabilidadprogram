/* Vistas del módulo Análisis — puras, con storage inyectado. */
import { describe, expect, it } from 'vitest';
import {
  CLAVE_VISTAS, VISTAS_PREDEFINIDAS,
  borrarVista, cargarVistasGuardadas, guardarVista,
} from './vistas.js';

function fakeStorage(inicial = {}) {
  const mapa = new Map(Object.entries(inicial));
  return {
    getItem: (k) => (mapa.has(k) ? mapa.get(k) : null),
    setItem: (k, v) => mapa.set(k, String(v)),
  };
}

describe('vistas predefinidas', () => {
  it('trae las 4 del plan con configuración restaurable', () => {
    expect(VISTAS_PREDEFINIDAS).toHaveLength(4);
    for (const v of VISTAS_PREDEFINIDAS) {
      expect(v.nombre).toBeTruthy();
      expect(v.config.plugin).toBeTruthy();
      expect(Array.isArray(v.config.columns)).toBe(true);
    }
  });

  it('las vistas por mes agrupan la fecha con bucket (motor WASM, no la IA)', () => {
    const conMes = VISTAS_PREDEFINIDAS.filter((v) => (v.config.group_by || []).includes('Mes')
      || (v.config.split_by || []).includes('Mes'));
    expect(conMes.length).toBeGreaterThanOrEqual(2);
    for (const v of conMes) expect(v.config.expressions.Mes).toContain('bucket');
  });
});

describe('vistas guardadas (localStorage v1)', () => {
  it('guarda, recarga y borra', () => {
    const st = fakeStorage();
    guardarVista('  Mi vista  ', { plugin: 'Datagrid' }, st);
    expect(cargarVistasGuardadas(st)).toEqual({ 'Mi vista': { plugin: 'Datagrid' } });
    guardarVista('Mi vista', { plugin: 'Y Bar' }, st);   // actualiza sin duplicar
    expect(cargarVistasGuardadas(st)['Mi vista'].plugin).toBe('Y Bar');
    borrarVista('Mi vista', st);
    expect(cargarVistasGuardadas(st)).toEqual({});
  });

  it('exige nombre y configuración', () => {
    const st = fakeStorage();
    expect(() => guardarVista('   ', { plugin: 'X' }, st)).toThrow('nombre');
    expect(() => guardarVista('Vista', null, st)).toThrow('configuración');
  });

  it('storage corrupto jamás revienta la carga', () => {
    expect(cargarVistasGuardadas(fakeStorage({ [CLAVE_VISTAS]: '{{{' }))).toEqual({});
    expect(cargarVistasGuardadas(fakeStorage({ [CLAVE_VISTAS]: '[1,2]' }))).toEqual({});
    expect(cargarVistasGuardadas(fakeStorage({ [CLAVE_VISTAS]: '{"a":null,"b":{"plugin":"X"}}' })))
      .toEqual({ b: { plugin: 'X' } });
  });
});
