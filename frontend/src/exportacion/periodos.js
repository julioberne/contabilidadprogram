/* ============================================================
   periodos.js — Atajos de período de "Nueva exportación" (13.5-c).
   Lógica pura con vitest. Fechas locales (hora de Colombia en el
   navegador del usuario), siempre AAAA-MM-DD.
   Los bimestres son los del IVA (formulario 300): ene-feb, mar-abr,
   may-jun, jul-ago, sep-oct, nov-dic.
   ============================================================ */

export const ATAJOS = [
  { clave: 'mes_actual', etiqueta: 'Este mes' },
  { clave: 'mes_anterior', etiqueta: 'Mes anterior' },
  { clave: 'bimestre_anterior', etiqueta: 'Bimestre IVA anterior' },
  { clave: 'trimestre_anterior', etiqueta: 'Trimestre anterior' },
  { clave: 'anio_corrido', etiqueta: 'Año corrido' },
  { clave: 'anio_anterior', etiqueta: 'Año anterior' },
];

const dos = (n) => String(n).padStart(2, '0');
export const iso = (d) => `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
const ultimoDia = (anio, mes0) => new Date(anio, mes0 + 1, 0);

/** Bloque de `meses` meses completo anterior al que contiene `hoy` (mes0 0-based). */
function bloqueAnterior(hoy, meses) {
  const indice = Math.floor(hoy.getMonth() / meses) - 1;          // puede ser -1 → año anterior
  const anio = hoy.getFullYear() + (indice < 0 ? -1 : 0);
  const inicio = ((indice + 12 / meses) % (12 / meses)) * meses;
  return { desde: iso(new Date(anio, inicio, 1)), hasta: iso(ultimoDia(anio, inicio + meses - 1)) };
}

/** Atajo → { desde, hasta } en AAAA-MM-DD. */
export function rangoRelativo(clave, hoy = new Date()) {
  const a = hoy.getFullYear();
  const m = hoy.getMonth();
  switch (clave) {
    case 'mes_actual': return { desde: iso(new Date(a, m, 1)), hasta: iso(hoy) };
    case 'mes_anterior': return bloqueAnterior(hoy, 1);
    case 'bimestre_anterior': return bloqueAnterior(hoy, 2);
    case 'trimestre_anterior': return bloqueAnterior(hoy, 3);
    case 'anio_corrido': return { desde: iso(new Date(a, 0, 1)), hasta: iso(hoy) };
    case 'anio_anterior': return { desde: `${a - 1}-01-01`, hasta: `${a - 1}-12-31` };
    default: throw new Error(`Atajo de período desconocido: ${clave}`);
  }
}

/** ¿Qué atajo produce exactamente este rango hoy? (para resaltarlo) — o null. */
export function atajoDe(desde, hasta, hoy = new Date()) {
  const hit = ATAJOS.find(({ clave }) => {
    const r = rangoRelativo(clave, hoy);
    return r.desde === desde && r.hasta === hasta;
  });
  return hit ? hit.clave : null;
}

/** Rango de un mes del organizador (anio, mes 1-12). */
export function rangoMes(anio, mes) {
  return { desde: `${anio}-${dos(mes)}-01`, hasta: iso(ultimoDia(Number(anio), Number(mes) - 1)) };
}
