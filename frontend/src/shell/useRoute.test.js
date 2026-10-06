import { describe, it, expect, beforeEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { pathToView, viewToPath, useQueryParam } from './useRoute.js';

describe('routing', () => {
  it('mapea la raíz a home', () => {
    expect(pathToView('/')).toBe('home');
    expect(viewToPath('home')).toBe('/');
  });

  it('mapea módulos del registry', () => {
    expect(pathToView('/contabilidad')).toBe('contabilidad');
    expect(pathToView('/tower')).toBe('tower');
    expect(viewToPath('contabilidad')).toBe('/contabilidad');
  });

  it('mapea la vista de shell module-settings a /modulos', () => {
    expect(viewToPath('module-settings')).toBe('/modulos');
    expect(pathToView('/modulos')).toBe('module-settings');
  });

  it('cae a home ante paths desconocidos', () => {
    expect(pathToView('/no-existe')).toBe('home');
    expect(pathToView('/contabilidad/sub/ruta')).toBe('contabilidad');
  });

  it('es reversible para todo módulo del registry', () => {
    ['contabilidad', 'rrhh', 'tower', 'tesoreria'].forEach(id => {
      expect(pathToView(viewToPath(id))).toBe(id);
    });
  });
});

describe('useQueryParam (deep-link de sub-vistas RRHH)', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/rrhh');
  });

  it('lee el valor inicial del query string', () => {
    window.history.replaceState(null, '', '/rrhh?view=members');
    const { result } = renderHook(() => useQueryParam('view', 'tasks'));
    expect(result.current[0]).toBe('members');
  });

  it('cae al fallback cuando el param no está', () => {
    const { result } = renderHook(() => useQueryParam('view', 'tasks'));
    expect(result.current[0]).toBe('tasks');
  });

  it('set() escribe el param en la URL', () => {
    const { result } = renderHook(() => useQueryParam('view', 'tasks'));
    act(() => result.current[1]('members'));
    expect(result.current[0]).toBe('members');
    expect(window.location.search).toContain('view=members');
  });

  it('set(fallback) limpia el param de la URL', () => {
    window.history.replaceState(null, '', '/rrhh?view=members');
    const { result } = renderHook(() => useQueryParam('view', 'tasks'));
    act(() => result.current[1]('tasks'));
    expect(window.location.search).not.toContain('view=');
  });

  it('dos params conviven sin pisarse (view + member)', () => {
    const { result: view }   = renderHook(() => useQueryParam('view', 'tasks'));
    act(() => view.current[1]('members'));
    const { result: member } = renderHook(() => useQueryParam('member', ''));
    act(() => member.current[1]('abc-123'));
    expect(window.location.search).toContain('view=members');
    expect(window.location.search).toContain('member=abc-123');
  });
});
