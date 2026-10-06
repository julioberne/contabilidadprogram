/* ============================================================
   paquetes.js — Lógica pura de "Nueva exportación" (13.5-c).
   Paquete ↔ hojas (espejo de paquete_efectivo del backend), receta
   para el motor 13.4 y filtros del selector de transacciones.
   Los paquetes vienen de GET /api/analytics/export/paquetes.
   ============================================================ */

export const PERSONALIZADO = 'personalizado';
export const MAX_TX = 5000;                       // = MAX_TX_IDS del motor
export const TIPOS_TX = ['INGRESO', 'GASTO', 'TRANSFERENCIA'];
export const NIVELES_PUC = [
  ['', 'Todos los niveles'], ['clase', 'Clase (1 dígito)'], ['grupo', 'Grupo (2)'],
  ['cuenta', 'Cuenta (4)'], ['subcuenta', 'Subcuenta (6)'],
];

/** Hojas del modo período, agrupadas como las piensa un contador. La carátula va siempre. */
export const GRUPOS_HOJAS = [
  { titulo: 'Libros oficiales', hojas: [['diario', 'Libro diario'], ['mayor', 'Mayor']] },
  { titulo: 'Estados financieros', hojas: [['balance_prueba', 'Balance de prueba'],
    ['estado_resultados', 'Estado de resultados'], ['balance_general', 'Balance general']] },
  { titulo: 'Auxiliares y soportes', hojas: [['movimientos', 'Movimientos'],
    ['auxiliar_tercero', 'Auxiliar por tercero'], ['cartera', 'Cartera por edades'], ['impuestos', 'Impuestos']] },
];
export const HOJAS = GRUPOS_HOJAS.flatMap((g) => g.hojas.map(([h]) => h));

/** Período que propone cada paquete al elegirlo. */
export const ATAJO_DE_PAQUETE = { cierre_mes: 'mes_anterior', iva_bimestral: 'bimestre_anterior', completo: 'anio_corrido' };

const mismas = (a, b) => a.length === b.length && a.every((x) => b.includes(x));

/** Hojas elegidas → clave del paquete que calza exacto, o 'personalizado'. */
export function paqueteDeHojas(predefinidos, hojas) {
  const elegidas = (hojas || []).filter((h) => h !== 'caratula');
  const hit = (predefinidos || []).find((p) => mismas(p.hojas.filter((h) => h !== 'caratula'), elegidas));
  return hit ? hit.clave : PERSONALIZADO;
}

/** Hojas de un paquete predefinido (sin carátula, que el motor agrega). */
export function hojasDePaquete(predefinidos, clave) {
  const p = (predefinidos || []).find((x) => x.clave === clave);
  return p ? p.hojas.filter((h) => h !== 'caratula') : [];
}

/** Lista desde un arreglo o desde texto separado por comas. */
const lista = (v) => (Array.isArray(v) ? v : String(v || '').split(','))
  .map((s) => String(s).trim()).filter(Boolean);

/** Formulario del modo período → { receta, paquete } para preflight/generar. */
export function recetaPeriodo(f) {
  const receta = { modo: 'periodo', desde: f.desde || undefined, hasta: f.hasta, hojas: [...f.hojas] };
  if (f.empresas.length === 1) receta.portfolio_id = f.empresas[0];
  else if (f.empresas.length > 1) receta.portfolios = [...f.empresas];
  if (f.nivelPuc) receta.nivel_puc = f.nivelPuc;
  const filtros = {};
  if (f.tipos.length) filtros.tipos = [...f.tipos];
  if (f.moneda) filtros.moneda = f.moneda;
  if (f.terceros.length) filtros.terceros = [...f.terceros];
  if (lista(f.categorias).length) filtros.categorias = lista(f.categorias);
  if (lista(f.cuentasPuc).length) filtros.cuentas_puc = lista(f.cuentasPuc);
  if (Object.keys(filtros).length) receta.filtros = filtros;
  if (f.nombre?.trim()) receta.nombre = f.nombre.trim();
  if (f.atajo) receta.relativo = f.atajo;
  // 06-oct: comparativo, certificación (Ley 222 art. 37) y folio inicial.
  if (f.comparativo) receta.comparativo = f.comparativo;
  if (f.certificar) {
    const c = Object.fromEntries(Object.entries(f.cert || {}).filter(([, v]) => String(v || '').trim())
      .map(([k, v]) => [k, String(v).trim()]));
    receta.certificacion = Object.keys(c).length ? c : true;     // {} sería "no certificar" para el motor
  }
  if (String(f.folioInicial ?? '').trim()) receta.folio_inicial = Number(f.folioInicial);
  return { receta, paquete: f.paquete || PERSONALIZADO };
}

export const COMPARATIVOS = [['', 'Sin comparativo'], ['periodo_anterior', 'Vs. período anterior'], ['anio_anterior', 'Vs. año anterior']];
export const CAMPOS_CERTIFICACION = [
  ['representante', 'Representante legal'], ['documento_representante', 'C.C. del representante'],
  ['contador', 'Contador público'], ['tarjeta_profesional', 'T.P. del contador'],
];

/** Error legible del formulario de período, o null. */
export function validarPeriodo(f) {
  if (!f.hasta) return 'Falta la fecha final del período.';
  if (f.desde && f.desde > f.hasta) return 'La fecha inicial es posterior a la final.';
  if (!f.hojas.length) return 'Elige al menos un libro.';
  const folio = String(f.folioInicial ?? '').trim();
  if (folio && !(/^\d+$/.test(folio) && Number(folio) >= 1 && Number(folio) <= 999999)) {
    return 'El folio inicial es un número entero de 1 a 999999.';
  }
  return null;
}

/** Receta de una relación de transacciones elegidas. */
export function recetaTransacciones(ids, nombre) {
  const receta = { modo: 'transacciones', tx_ids: [...ids] };
  if (nombre?.trim()) receta.nombre = nombre.trim();
  return { receta, paquete: null };
}

const sinTildes = (s) => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

/** Filtro del selector: q busca en concepto, tercero, categoría, cuenta, nota e id. */
export function filtrarTransacciones(txs, f = {}) {
  const q = sinTildes(f.q).trim();
  return (txs || []).filter((t) => {
    const fecha = String(t.transaction_date || '').slice(0, 10);
    if (f.desde && fecha < f.desde) return false;
    if (f.hasta && fecha > f.hasta) return false;
    if (f.empresa && t.portfolio_name !== f.empresa) return false;
    if (f.tipo && t.type !== f.tipo) return false;
    if (f.categoria && t.category !== f.categoria) return false;
    if (f.tercero && String(t.third_party_id) !== String(f.tercero)) return false;
    if (q) {
      const texto = sinTildes([t.id, t.concept, t.third_party_name, t.category, t.account_name, t.note,
        t.identification_number].join(' '));
      if (!q.split(/\s+/).every((p) => texto.includes(p))) return false;
    }
    return true;
  });
}

/** Valores distintos (ordenados) de un campo, para los desplegables del selector. */
export function distintos(txs, campo) {
  return [...new Set((txs || []).map((t) => t[campo]).filter((v) => v != null && v !== ''))]
    .sort((a, b) => String(a).localeCompare(String(b), 'es'));
}

/** Σ por moneda de un conjunto de transacciones (USD jamás se suma al COP, R-13-06). */
export function totalesPorMoneda(txs) {
  const out = {};
  (txs || []).forEach((t) => {
    const m = t.transaction_currency || 'COP';
    out[m] = (out[m] || 0) + Number(t.amount || 0);
  });
  return out;
}
