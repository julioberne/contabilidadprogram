/* ============================================================
   diarioFiltros.js — Lógica pura de la búsqueda y filtros del
   Libro Diario (16-oct-2026). Sin React: filtros ↔ query string
   (URL compartible y petición al servidor), rangos rápidos de
   fecha, chips de filtros activos y CSV de lo filtrado.
   El filtrado de verdad lo hace /api/diario/movimientos.
   ============================================================ */

export const FILTROS_VACIOS = Object.freeze({
  q: '', tipos: [], desde: '', hasta: '', rango: '',
  terceros: [], cuentas: [], categorias: [], etiquetas: [],
  monto_min: '', monto_max: '', moneda: '', cartera: '', cartera_estado: '',
  banderas: [], empresas: '',          // '' = empresa activa · '*' = todas · 'A,B' = esas
});

export const ORDENES = [
  ['fecha_desc', 'Fecha ↓ (recientes)'], ['fecha_asc', 'Fecha ↑ (antiguas)'],
  ['monto_desc', 'Monto ↓ (mayor a menor)'], ['monto_asc', 'Monto ↑ (menor a mayor)'],
  ['tercero_asc', 'Tercero A-Z'], ['concepto_asc', 'Concepto A-Z'],
];

export const AGRUPACIONES = [
  ['', 'Sin agrupar'], ['tercero', 'Por tercero'], ['categoria', 'Por cuenta COA'],
  ['mes', 'Por mes'], ['cuenta', 'Por medio de pago'], ['etiqueta', 'Por etiqueta / proyecto'],
  ['tipo', 'Por tipo'], ['empresa', 'Por empresa'],
];

export const TIPOS = [['INGRESO', 'Ingresos'], ['GASTO', 'Gastos'], ['TRANSFERENCIA', 'Transferencias']];

export const BANDERAS = [
  ['sin_tercero', 'Sin tercero o sin NIT'], ['sin_evidencia', 'Sin evidencia'], ['con_evidencia', 'Con evidencia'],
  ['sin_categoria', 'Sin cuenta COA'], ['sin_etiqueta', 'Sin etiqueta'], ['con_nota', 'Con nota'],
  ['recurrentes', 'Recurrentes'], ['con_impuestos', 'Con IVA/GMF'], ['con_ubicacion', 'Con ubicación'],
  ['duplicados', '⚠ Posibles duplicados'],
];

export const RANGOS = [
  ['hoy', 'Hoy'], ['semana', 'Esta semana'], ['mes', 'Este mes'], ['mes_anterior', 'Mes anterior'],
  ['trimestre', 'Este trimestre'], ['anio', 'Este año'], ['anio_anterior', 'Año anterior'],
];

const LISTAS = ['tipos', 'terceros', 'cuentas', 'categorias', 'etiquetas', 'banderas'];
const TEXTOS = ['q', 'desde', 'hasta', 'rango', 'monto_min', 'monto_max', 'moneda', 'cartera', 'cartera_estado', 'empresas'];

const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/** Rango rápido → { desde, hasta } (semana = lunes a domingo). */
export function rangoRapido(clave, hoy = new Date()) {
  const y = hoy.getFullYear(); const m = hoy.getMonth();
  switch (clave) {
    case 'hoy': return { desde: iso(hoy), hasta: iso(hoy) };
    case 'semana': {
      const lunes = new Date(y, m, hoy.getDate() - ((hoy.getDay() + 6) % 7));
      return { desde: iso(lunes), hasta: iso(new Date(y, m, lunes.getDate() + 6)) };
    }
    case 'mes': return { desde: iso(new Date(y, m, 1)), hasta: iso(new Date(y, m + 1, 0)) };
    case 'mes_anterior': return { desde: iso(new Date(y, m - 1, 1)), hasta: iso(new Date(y, m, 0)) };
    case 'trimestre': {
      const t = Math.floor(m / 3) * 3;
      return { desde: iso(new Date(y, t, 1)), hasta: iso(new Date(y, t + 3, 0)) };
    }
    case 'anio': return { desde: `${y}-01-01`, hasta: `${y}-12-31` };
    case 'anio_anterior': return { desde: `${y - 1}-01-01`, hasta: `${y - 1}-12-31` };
    default: return { desde: '', hasta: '' };
  }
}

/** ¿Hay algún filtro que cambie el resultado frente al Diario completo? */
export function filtrosActivos(f) {
  return LISTAS.some((k) => (f[k] || []).length > 0)
    || TEXTOS.some((k) => k !== 'rango' && String(f[k] || '').trim() !== '');
}

/** Filtros + orden + agrupación → URLSearchParams (sirve para la URL y la API). */
export function aParametros(f, { orden = 'fecha_desc', agrupar = '' } = {}) {
  const p = new URLSearchParams();
  for (const k of TEXTOS) { const v = String(f[k] || '').trim(); if (v) p.set(k, v); }
  for (const k of LISTAS) { if ((f[k] || []).length) p.set(k, f[k].join(',')); }
  if (orden && orden !== 'fecha_desc') p.set('orden', orden);
  if (agrupar) p.set('agrupar', agrupar);
  return p;
}

/** query string → { filtros, orden, agrupar } (lo desconocido se ignora). */
export function desdeParametros(search) {
  const p = new URLSearchParams(search || '');
  const filtros = { ...FILTROS_VACIOS };
  for (const k of TEXTOS) if (p.get(k)) filtros[k] = p.get(k);
  for (const k of LISTAS) if (p.get(k)) filtros[k] = p.get(k).split(',').filter(Boolean);
  // Los ids de tercero/cuenta viajan como texto; se comparan como número.
  filtros.terceros = filtros.terceros.map(Number).filter(Number.isFinite);
  filtros.cuentas = filtros.cuentas.map(Number).filter(Number.isFinite);
  return { filtros, orden: p.get('orden') || 'fecha_desc', agrupar: p.get('agrupar') || '' };
}

/** Claves de la URL que pertenecen al Diario (para no pisar otras, p. ej. ?tab=). */
export const CLAVES_URL = [...TEXTOS, ...LISTAS, 'orden', 'agrupar'];

const fmt = (v) => `$${Number(v || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 })}`;

/** Chips de filtros activos: [{ id, texto, quitar: filtros → filtros }]. */
export function chipsActivos(f, opciones = {}) {
  const nombre = (lista, id, campo = 'name') => (opciones[lista] || []).find((o) => o.id === id)?.[campo] ?? `#${id}`;
  const sin = (k, v) => (x) => ({ ...x, [k]: x[k].filter((y) => y !== v) });
  const chips = [];
  if (f.q) chips.push({ id: 'q', texto: `🔍 "${f.q}"`, quitar: (x) => ({ ...x, q: '' }) });
  for (const t of f.tipos) chips.push({ id: `t-${t}`, texto: TIPOS.find(([k]) => k === t)?.[1] || t, quitar: sin('tipos', t) });
  if (f.desde || f.hasta) {
    const r = RANGOS.find(([k]) => k === f.rango)?.[1];
    chips.push({ id: 'fecha', texto: `📅 ${r || `${f.desde || '…'} → ${f.hasta || '…'}`}`,
      quitar: (x) => ({ ...x, desde: '', hasta: '', rango: '' }) });
  }
  for (const id of f.terceros) chips.push({ id: `tp-${id}`, texto: `👤 ${nombre('terceros', id)}`, quitar: sin('terceros', id) });
  for (const id of f.cuentas) chips.push({ id: `c-${id}`, texto: `🏦 ${nombre('cuentas', id)}`, quitar: sin('cuentas', id) });
  for (const c of f.categorias) chips.push({ id: `cat-${c}`, texto: `📂 ${c}`, quitar: sin('categorias', c) });
  for (const e of f.etiquetas) chips.push({ id: `e-${e}`, texto: `🏷 ${e}`, quitar: sin('etiquetas', e) });
  if (f.monto_min || f.monto_max) {
    chips.push({ id: 'monto', texto: `💲 ${f.monto_min ? fmt(f.monto_min) : '…'} – ${f.monto_max ? fmt(f.monto_max) : '…'}`,
      quitar: (x) => ({ ...x, monto_min: '', monto_max: '' }) });
  }
  if (f.moneda) chips.push({ id: 'moneda', texto: `💱 ${f.moneda}`, quitar: (x) => ({ ...x, moneda: '' }) });
  if (f.cartera) {
    const t = f.cartera === 'NINGUNA' ? 'Sin cartera' : `${f.cartera}${f.cartera_estado ? ` · ${f.cartera_estado}` : ''}`;
    chips.push({ id: 'cartera', texto: `📄 ${t}`, quitar: (x) => ({ ...x, cartera: '', cartera_estado: '' }) });
  }
  for (const b of f.banderas) chips.push({ id: `b-${b}`, texto: BANDERAS.find(([k]) => k === b)?.[1] || b, quitar: sin('banderas', b) });
  if (f.empresas) {
    chips.push({ id: 'empresas', texto: `🏢 ${f.empresas === '*' ? 'Todas las empresas' : f.empresas.split(',').join(', ')}`,
      quitar: (x) => ({ ...x, empresas: '' }) });
  }
  return chips;
}

/** Filas → CSV (separador ; y BOM para que Excel en español lo abra bien). */
export function aCsv(txs) {
  const cols = [
    ['id', 'ID'], ['transaction_date', 'Fecha'], ['type', 'Tipo'], ['concept', 'Concepto'],
    ['net_value', 'Valor neto'], ['amount', 'Valor bruto'], ['transaction_currency', 'Moneda'],
    ['category', 'Cuenta COA'], ['third_party_name', 'Tercero'], ['identification_number', 'NIT/CC'],
    ['account_name', 'Cuenta'], ['dest_account_name', 'Cuenta destino'], ['tags', 'Etiquetas'],
    ['note', 'Nota'], ['portfolio_name', 'Empresa'],
  ];
  const esc = (v) => {
    const s = Array.isArray(v) ? v.join(' | ') : String(v ?? '');
    return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const num = (v) => (v === null || v === undefined || v === '' ? '' : String(v).replace('.', ','));
  const filas = (txs || []).map((t) => cols.map(([k]) => (
    k === 'net_value' || k === 'amount' ? num(t[k]) : esc(t[k])
  )).join(';'));
  return `\uFEFF${cols.map(([, l]) => l).join(';')}\n${filas.join('\n')}`;
}

/** Código PUC al inicio de la categoría ("5105 - Gastos…" → "5105"), o null. */
export function codigoPuc(categoria) {
  const m = /^\s*(\d{4,10})\b/.exec(categoria || '');
  return m ? m[1] : null;
}

/** Etiquetas nuevas de una TX al etiquetar en lote (sin repetir, respeta mayúsculas existentes). */
export function agregarEtiqueta(tags, nueva) {
  const actual = Array.isArray(tags) ? tags : [];
  const n = (nueva || '').trim();
  if (!n || actual.some((t) => t.toLowerCase() === n.toLowerCase())) return actual;
  return [...actual, n];
}

const SIN_GRUPO = { '(sin tercero)': 'sin_tercero', '(sin categoría)': 'sin_categoria', '(sin etiqueta)': 'sin_etiqueta' };

/** Grupo → filtros con ese grupo aplicado (o null si no se puede filtrar por él). */
export function filtroDeGrupo(agrupar, g, filtros) {
  const bandera = SIN_GRUPO[g.clave];
  if (bandera) return filtros.banderas.includes(bandera) ? null : { ...filtros, banderas: [...filtros.banderas, bandera] };
  const agrega = (k, v) => (filtros[k].includes(v) ? null : { ...filtros, [k]: [...filtros[k], v] });
  switch (agrupar) {
    case 'tercero': return g.ref != null ? agrega('terceros', g.ref) : null;
    case 'cuenta': return g.ref != null ? agrega('cuentas', g.ref) : null;
    case 'categoria': return agrega('categorias', g.clave);
    case 'etiqueta': return agrega('etiquetas', g.clave);
    case 'tipo': return agrega('tipos', g.clave);
    case 'empresa': return { ...filtros, empresas: g.clave };
    case 'mes': {
      const [y, m] = g.clave.split('-').map(Number);
      const fin = new Date(y, m, 0).getDate();
      return { ...filtros, rango: '', desde: `${g.clave}-01`, hasta: `${g.clave}-${String(fin).padStart(2, '0')}` };
    }
    default: return null;
  }
}
