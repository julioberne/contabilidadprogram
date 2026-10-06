import { describe, it, expect, beforeEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import {
  pathToView, viewToPath, useQueryParam, useRoute, usePathname, avisarRuta, EVENTO_RUTA,
} from './useRoute.js';
import { getNavGroups } from '../registry/moduleRegistry.js';

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

describe('sub-rutas del menú lateral (∑ Análisis → 📦 Exportación)', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/contabilidad');
    localStorage.removeItem('finsys_session');
  });

  it('navigate(view, {path}) abre la sub-ruta y avisa el cambio', () => {
    const avisos = [];
    const oir = (e) => avisos.push(e.detail.path);
    window.addEventListener(EVENTO_RUTA, oir);
    const { result } = renderHook(() => useRoute());
    act(() => result.current[1]('analisis', { path: '/analisis/exportacion' }));
    window.removeEventListener(EVENTO_RUTA, oir);
    expect(result.current[0]).toBe('analisis');
    expect(window.location.pathname).toBe('/analisis/exportacion');
    expect(avisos).toEqual(['/analisis/exportacion']);
  });

  it('ignora una sub-ruta que pertenece a otro módulo', () => {
    const { result } = renderHook(() => useRoute());
    act(() => result.current[1]('analisis', { path: '/contabilidad/19-x' }));
    expect(window.location.pathname).toBe('/analisis');
  });

  it('usePathname sigue los avisos de EVENTO_RUTA (pushState no dispara popstate)', () => {
    const { result } = renderHook(() => usePathname());
    act(() => {
      window.history.replaceState(null, '', '/analisis/exportacion');
      avisarRuta('test');
    });
    expect(result.current).toBe('/analisis/exportacion');
  });

  it('el registry cuelga 📦 Exportación de ∑ Análisis solo para owner/admin/contador', () => {
    const sub = () => getNavGroups().flatMap(g => g.items).find(i => i.id === 'analisis').sub;
    expect(sub()).toEqual([]);   // sin sesión = member
    localStorage.setItem('finsys_session', JSON.stringify({ hubRole: 'contador' }));
    expect(sub().map(s => s.path)).toEqual(['/analisis/exportacion']);
    expect(pathToView('/analisis/exportacion')).toBe('analisis');
  });
});
