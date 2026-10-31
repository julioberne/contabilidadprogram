/* ============================================================
   seleccion.js — Casillas del Libro Diario (spec 13.5 §4.3,
   CA-135-08/09). Lógica pura: la selección es un Set de ids de
   TX; lo que se exporta es la selección ∩ las filas cargadas
   (lo que se ve es lo que se exporta). Totales con el valor neto,
   como la carátula de la Relación, y por moneda: USD jamás se
   suma al COP (R-13-06).

   «Marcar todo» (estándar H8.3): `filtro` = { query, n, porMoneda }.
   Mientras exista, lo marcado es TODO lo que cumple ese filtro y
   el Set guarda las excepciones desmarcadas a mano. Marcar no
   baja filas: se piden al exportar o editar en lote.
   ============================================================ */

export const MAX_SELECCION = 20000;       // LIMITE_SELECCION del servidor

/** ¿Esta fila está marcada? */
export function estaMarcada(sel, filtro, id) {
  return filtro ? !sel.has(id) : sel.has(id);
}

/** Marca o desmarca un id (devuelve un Set nuevo). */
export function alternarId(sel, id) {
  const s = new Set(sel);
  if (s.has(id)) s.delete(id); else s.add(id);
  return s;
}

/** Marca (o desmarca) de una vez todas las TXs dadas. */
export function marcarVarias(sel, txs, marcar) {
  const s = new Set(sel);
  (txs || []).forEach((t) => (marcar ? s.add(t.id) : s.delete(t.id)));
  return s;
}

/** TXs cargadas que están marcadas, en el orden del Libro Diario. */
export function seleccionadas(sel, txs) {
  return (txs || []).filter((t) => sel.has(t.id));
}

/** Estado de la casilla "todas las visibles": 'todas' | 'algunas' | 'ninguna'. */
export function estadoCabecera(sel, txs, filtro = null) {
  const n = (txs || []).filter((t) => estaMarcada(sel, filtro, t.id)).length;
  if (!n) return 'ninguna';
  return n === (txs || []).length ? 'todas' : 'algunas';
}

/** { n, porMoneda: { COP: { ingresos, gastos } } } de las TXs marcadas (valor neto). */
export function resumenSeleccion(txs) {
  const porMoneda = {};
  (txs || []).forEach((t) => {
    if (t.type !== 'INGRESO' && t.type !== 'GASTO') return;     // transferencias: cuentan, no suman
    const m = t.transaction_currency || 'COP';
    const acc = porMoneda[m] || (porMoneda[m] = { ingresos: 0, gastos: 0 });
    acc[t.type === 'INGRESO' ? 'ingresos' : 'gastos'] += Number(t.net_value ?? t.amount ?? 0);
  });
  return { n: (txs || []).length, porMoneda };
}

/** Totales del servidor (/api/diario/movimientos) → la forma de `porMoneda`. */
export function porMonedaDeTotales(t) {
  const porMoneda = { COP: { ingresos: Number(t?.ingresos_cop || 0), gastos: Number(t?.gastos_cop || 0) } };
  if (t?.ingresos_usd || t?.gastos_usd) {
    porMoneda.USD = { ingresos: Number(t.ingresos_usd || 0), gastos: Number(t.gastos_usd || 0) };
  }
  return porMoneda;
}

/** { n, porMoneda } de «Marcar todo»: lo del servidor menos las filas desmarcadas. */
export function resumenFiltro(filtro, desmarcadas) {
  const menos = resumenSeleccion(desmarcadas).porMoneda;
  const porMoneda = {};
  Object.entries(filtro.porMoneda).forEach(([m, t]) => {
    porMoneda[m] = { ingresos: t.ingresos - (menos[m]?.ingresos || 0), gastos: t.gastos - (menos[m]?.gastos || 0) };
  });
  return { n: filtro.n - desmarcadas.length, porMoneda };
}
