/* ============================================================
   vistas.js — Vistas del módulo Análisis (funciones puras).

   - VISTAS_PREDEFINIDAS: 4 configuraciones de <perspective-viewer>
     listas para restore().
   - Vistas propias v1 en localStorage (luego tabla analysis_views).
     El storage se inyecta para poder testearlas con vitest.
   ============================================================ */

export const CLAVE_VISTAS = 'finsys_analisis_vistas_v1';

// bucket("fecha",'M') agrupa la fecha por mes dentro del motor WASM.
const EXPR_MES = { 'Mes': `bucket("fecha", 'M')` };

export const VISTAS_PREDEFINIDAS = [
  {
    nombre: 'Gastos por empresa y mes',
    config: {
      plugin: 'Datagrid',
      group_by: ['empresa'],
      split_by: ['Mes'],
      columns: ['neto'],
      aggregates: { neto: 'sum' },
      filter: [['tipo', '==', 'GASTO']],
      expressions: EXPR_MES,
      settings: false,
    },
  },
  {
    nombre: 'Terceros top (gasto)',
    config: {
      plugin: 'Y Bar',
      group_by: ['tercero'],
      columns: ['neto'],
      aggregates: { neto: 'sum' },
      sort: [['neto', 'desc']],
      filter: [['tipo', '==', 'GASTO']],
      settings: false,
    },
  },
  {
    nombre: 'Flujo mensual (ingresos vs gastos)',
    config: {
      plugin: 'Y Bar',
      group_by: ['Mes'],
      split_by: ['tipo'],
      columns: ['neto'],
      aggregates: { neto: 'sum' },
      expressions: EXPR_MES,
      settings: false,
    },
  },
  {
    nombre: 'Balance dinámico',
    config: {
      plugin: 'Datagrid',
      group_by: ['empresa', 'categoria'],
      split_by: ['tipo'],
      columns: ['neto'],
      aggregates: { neto: 'sum' },
      settings: false,
    },
  },
];

/** Vistas guardadas por el usuario: { nombre: config }. Jamás revienta. */
export function cargarVistasGuardadas(storage = window.localStorage) {
  try {
    const crudo = JSON.parse(storage.getItem(CLAVE_VISTAS));
    if (!crudo || typeof crudo !== 'object' || Array.isArray(crudo)) return {};
    return Object.fromEntries(
      Object.entries(crudo).filter(([n, c]) => n && c && typeof c === 'object')
    );
  } catch {
    return {};
  }
}

/** Guarda/actualiza una vista propia. Devuelve el mapa actualizado. */
export function guardarVista(nombre, config, storage = window.localStorage) {
  const limpio = String(nombre || '').trim();
  if (!limpio) throw new Error('La vista necesita un nombre.');
  if (!config || typeof config !== 'object') throw new Error('No hay configuración que guardar.');
  const vistas = cargarVistasGuardadas(storage);
  vistas[limpio] = config;
  storage.setItem(CLAVE_VISTAS, JSON.stringify(vistas));
  return vistas;
}

/** Borra una vista propia. Devuelve el mapa actualizado. */
export function borrarVista(nombre, storage = window.localStorage) {
  const vistas = cargarVistasGuardadas(storage);
  delete vistas[nombre];
  storage.setItem(CLAVE_VISTAS, JSON.stringify(vistas));
  return vistas;
}
