/* Organizador contable 13.5-b — lógica pura. */
import { describe, expect, it } from 'vitest';
import {
  RAIZ, arbolPlano, armarArbol, carpetasAutomaticas, descendientes, diasParaVencer, estadoVigencia, etiquetaPeriodo,
  fechaHora, formatoBytes, iconoArchivo, migas, nombreDescarga, parametrosLista,
  periodoSugerido, puedeBorrar, queryString, rutaCarpeta, subcarpetas, validarSubida,
} from './organizador.js';

const ARBOL = [
  { portfolio_id: null, empresa: 'Consolidado', anio: 2026, mes: 9, n: 1 },
  { portfolio_id: 2, empresa: 'Pegasus', anio: 2026, mes: 8, n: 2 },
  { portfolio_id: 2, empresa: 'Pegasus', anio: 2026, mes: 9, n: 3 },
  { portfolio_id: 2, empresa: 'Pegasus', anio: 2025, mes: 12, n: 1 },
  { portfolio_id: 2, empresa: 'Pegasus', anio: null, mes: null, n: 4 },
  { portfolio_id: 1, empresa: 'Finanzas Julian', anio: 2026, mes: 9, n: 5 },
];
const CARPETAS = [
  { id: 1, nombre: 'Auditoría', parent_id: null },
  { id: 2, nombre: '2026', parent_id: 1 },
  { id: 3, nombre: 'Banco', parent_id: 2 },
  { id: 4, nombre: 'Para el banco', parent_id: null },
];

describe('formatos', () => {
  it('bytes con coma decimal', () => {
    expect(formatoBytes(0)).toBe('0 B');
    expect(formatoBytes(820)).toBe('820 B');
    expect(formatoBytes(2048)).toBe('2 KB');
    expect(formatoBytes(3276800)).toBe('3,1 MB');
    expect(formatoBytes(150 * 1024)).toBe('150 KB');
  });

  it('icono por MIME', () => {
    expect(iconoArchivo('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')).toEqual({ icono: '📗', ext: 'XLSX' });
    expect(iconoArchivo('application/pdf').ext).toBe('PDF');
    expect(iconoArchivo('image/jpeg').ext).toBe('JPG');
    expect(iconoArchivo('', 'raro.docx').ext).toBe('DOCX');
  });

  it('período igual que el backend', () => {
    expect(etiquetaPeriodo('2026-09-01', '2026-09-30')).toBe('sep 2026');
    expect(etiquetaPeriodo('2026-02-01', '2026-02-28')).toBe('feb 2026');
    expect(etiquetaPeriodo('2026-01-01', '2026-12-31')).toBe('año 2026');
    expect(etiquetaPeriodo('2026-07-01', '2026-09-30')).toBe('T3 2026');
    expect(etiquetaPeriodo('2026-09-05', '2026-09-20')).toBe('05/09/2026 – 20/09/2026');
    expect(etiquetaPeriodo(null, '2026-09-30')).toBe('hasta 30/09/2026');
    expect(etiquetaPeriodo(null, null)).toBe('sin período');
  });

  it('fecha y hora', () => {
    expect(fechaHora('2026-10-05T09:30:12')).toBe('05/10/2026 09:30');
    expect(fechaHora('2026-10-05')).toBe('05/10/2026');
    expect(fechaHora(null)).toBe('');
    // La BD responde UTC: se muestra la hora de Colombia (y el día correcto cerca de medianoche).
    expect(fechaHora('2026-10-05T23:35:33+00:00')).toBe('05/10/2026 18:35');
    expect(fechaHora('2026-10-06T02:10:00Z')).toBe('05/10/2026 21:10');
    expect(fechaHora('2026-10-05T18:35:00-05:00')).toBe('05/10/2026 18:35');
  });

  it('nombre de la descarga', () => {
    expect(nombreDescarga("attachment; filename=\"EXP_Cierre a_o.xlsx\"; filename*=UTF-8''EXP_Cierre%20a%C3%B1o.xlsx")).toBe('EXP_Cierre año.xlsx');
    expect(nombreDescarga('attachment; filename="x.pdf"')).toBe('x.pdf');
    expect(nombreDescarga('', 'respaldo.xlsx')).toBe('respaldo.xlsx');
  });
});

describe('árbol automático Empresa → Año → Mes', () => {
  const empresas = armarArbol(ARBOL);

  it('agrupa, ordena y deja el consolidado al final', () => {
    expect(empresas.map((e) => [e.pid, e.n])).toEqual([[1, 5], [2, 10], [0, 1]]);
    const pegasus = empresas[1];
    expect(pegasus.sinPeriodo).toBe(4);
    expect(pegasus.anios.map((a) => [a.anio, a.n])).toEqual([[2026, 5], [2025, 1]]);
    expect(pegasus.anios[0].meses.map((m) => m.mes)).toEqual([9, 8]);
  });

  it('carpetas automáticas de cada nivel', () => {
    expect(carpetasAutomaticas(RAIZ, empresas).map((c) => c.etiqueta)).toEqual(['Finanzas Julian', 'Pegasus', 'Consolidado']);
    expect(carpetasAutomaticas({ nivel: 'empresa', pid: 2 }, empresas).map((c) => c.etiqueta)).toEqual(['2026', '2025']);
    const meses = carpetasAutomaticas({ nivel: 'anio', pid: 2, anio: 2026 }, empresas);
    expect(meses.map((c) => [c.etiqueta, c.n])).toEqual([['09 septiembre', 3], ['08 agosto', 2]]);
    expect(meses[0].ubicacion).toEqual({ nivel: 'mes', pid: 2, anio: 2026, mes: 9 });
    expect(carpetasAutomaticas({ nivel: 'mes', pid: 2, anio: 2026, mes: 9 }, empresas)).toEqual([]);
  });

  it('migas de la ubicación', () => {
    const m = migas({ ubicacion: { nivel: 'mes', pid: 2, anio: 2026, mes: 9 }, empresas });
    expect(m.map((x) => x.etiqueta)).toEqual(['Archivo', 'Pegasus', '2026', '09 septiembre']);
    expect(m[1].ubicacion).toEqual({ nivel: 'empresa', pid: 2 });
    expect(migas({ ubicacion: { nivel: 'carpeta', id: 3 }, carpetas: CARPETAS }).map((x) => x.etiqueta))
      .toEqual(['Archivo', '📁 Auditoría', '📁 2026', '📁 Banco']);
    expect(migas({ filtro: { tipo: 7 }, tipos: [{ id: 7, nombre: 'Soportes', icono: '📎' }] })[1].etiqueta).toBe('📎 Soportes');
    expect(migas({ filtro: { cambiaron: true } })[1].etiqueta).toBe('⚠ Cambiaron');
    expect(migas({ q: 'EXP-2026', ubicacion: { nivel: 'empresa', pid: 2 }, empresas })[1].etiqueta).toBe('🔍 «EXP-2026»');
  });
});

describe('parámetros de la lista', () => {
  it('la búsqueda manda sobre todo; luego el filtro; luego la ubicación', () => {
    expect(parametrosLista({ ubicacion: { nivel: 'mes', pid: 2, anio: 2026, mes: 9 }, q: ' folio ' })).toEqual({ q: 'folio' });
    expect(parametrosLista({ ubicacion: { nivel: 'mes', pid: 2, anio: 2026, mes: 9 }, filtro: { fijado: true } })).toEqual({ fijado: true });
    expect(parametrosLista({ ubicacion: { nivel: 'mes', pid: 2, anio: 2026, mes: 9 } })).toEqual({ portfolio_id: 2, anio: 2026, mes: 9 });
    expect(parametrosLista({ ubicacion: { nivel: 'empresa', pid: 0 } })).toEqual({ portfolio_id: 0 });
    expect(parametrosLista({ ubicacion: { nivel: 'carpeta', id: 4 } })).toEqual({ folder_id: 4 });
    expect(parametrosLista({})).toEqual({});
  });

  it('query string sin vacíos', () => {
    expect(queryString({ portfolio_id: 0, anio: 2026, q: '', fijado: false, cambiaron: true, x: null }))
      .toBe('?portfolio_id=0&anio=2026&cambiaron=true');
    expect(queryString({})).toBe('');
    expect(queryString({ q: 'a&b' })).toBe('?q=a%26b');
  });
});

describe('carpetas propias', () => {
  it('ruta, hijas y descendientes', () => {
    expect(rutaCarpeta(CARPETAS, 3).map((c) => c.id)).toEqual([1, 2, 3]);
    expect(rutaCarpeta([{ id: 1, parent_id: 2 }, { id: 2, parent_id: 1 }], 1).length).toBe(2);   // ciclo no cuelga
    expect(subcarpetas(CARPETAS, null).map((c) => c.id)).toEqual([1, 4]);
    expect(subcarpetas(CARPETAS, 1).map((c) => c.id)).toEqual([2]);
    expect([...descendientes(CARPETAS, 1)].sort()).toEqual([1, 2, 3]);
  });

  it('árbol plano en orden de lectura con su nivel', () => {
    expect(arbolPlano(CARPETAS).map((c) => [c.nombre, c.nivel]))
      .toEqual([['Auditoría', 0], ['2026', 1], ['Banco', 2], ['Para el banco', 0]]);
  });
});

describe('vigencia, subida y permisos', () => {
  it('insignia de vigencia', () => {
    expect(estadoVigencia({ vigencia: { estado: 'VIGENTE', detalles: [] } }).texto).toBe('VIGENTE');
    expect(estadoVigencia({ vigencia: { estado: 'CAMBIO', detalles: ['+3 TX(s)'] } }).detalles).toEqual(['+3 TX(s)']);
    expect(estadoVigencia({ vigencia: null })).toBeNull();
    expect(estadoVigencia({ vigencia: { estado: 'SIN_HUELLA' } })).toBeNull();
  });

  it('días para vencer: solo los cercanos y nunca un fijado', () => {
    const hoy = new Date(2026, 9, 5);
    expect(diasParaVencer({ vence_el: '2026-10-15' }, hoy)).toBe(10);
    expect(diasParaVencer({ vence_el: '2026-12-30' }, hoy)).toBeNull();
    expect(diasParaVencer({ vence_el: '2026-10-01' }, hoy)).toBe(0);
    expect(diasParaVencer({ vence_el: '2026-10-15', fijado: true }, hoy)).toBeNull();
    expect(diasParaVencer({ vence_el: null }, hoy)).toBeNull();
  });

  it('período sugerido para subir', () => {
    const hoy = new Date(2026, 9, 5);
    expect(periodoSugerido({ nivel: 'mes', pid: 2, anio: 2026, mes: 8 }, hoy)).toEqual({ anio: 2026, mes: 8 });
    expect(periodoSugerido({ nivel: 'anio', pid: 2, anio: 2025 }, hoy)).toEqual({ anio: 2025, mes: '' });
    expect(periodoSugerido(RAIZ, hoy)).toEqual({ anio: 2026, mes: 10 });
  });

  it('valida extensión, tamaño y vacío', () => {
    expect(validarSubida({ name: 'extracto.PDF', size: 100 })).toBeNull();
    expect(validarSubida({ name: 'x.docx', size: 100 })).toMatch(/solo PDF/);
    expect(validarSubida({ name: 'x.pdf', size: 11 * 1024 * 1024 }, 10)).toMatch(/tope es 10 MB/);
    expect(validarSubida({ name: 'x.csv', size: 0 })).toMatch(/vacío/);
  });

  it('borrar es solo de owner/admin', () => {
    expect(puedeBorrar({ role: 'OWNER' })).toBe(true);
    expect(puedeBorrar({ role: 'admin' })).toBe(true);
    expect(puedeBorrar({ role: 'contador' })).toBe(false);
    expect(puedeBorrar(null)).toBe(false);
  });
});
