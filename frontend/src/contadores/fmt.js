/* fmt.js — formato de dinero y fechas del módulo Contadores (es-CO). */
export const fmt = (v) => v == null || v === '' ? '—'
  : `$${Number(v).toLocaleString('es-CO', Number.isInteger(Number(v))
      ? { maximumFractionDigits: 0 } : { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const fmtFecha = (v) => (v ? String(v).slice(0, 10) : '—');

export const hoy = () => new Date().toISOString().slice(0, 10);

export const ESTADO_STYLE = {
  BORRADOR: 'bg-brutalAmber text-black',
  CONTABILIZADO: 'bg-brutalGreen text-black',
  RECHAZADO: 'bg-gray-200 text-gray-600',
  ANULADO: 'bg-brutalCrimson text-white line-through',
};
