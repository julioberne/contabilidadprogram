/* ============================================================
   cierres.js — Vista 🗓 de cierres (spec 13.5-d, CA-135-13):
   paquete × mes con el último folio de cada uno y su vigencia.
   Lógica pura (la matriz la arma GET /api/accounting-files/cierres).
   ============================================================ */

export const ESTADO_CIERRE = {
  VIGENTE: { icono: '✅', clase: 'bg-brutalGreen', ayuda: 'Vigente: los libros no cambiaron desde que se exportó' },
  CAMBIO: { icono: '⚠', clase: 'bg-brutalAmber', ayuda: 'Los libros cambiaron después de exportarlo: conviene regenerar' },
  SIN_HUELLA: { icono: '•', clase: 'bg-brutalNeutral', ayuda: 'Sin huella para comparar' },
};

/** Celda del paquete en el mes (1–12) o null si ese mes no tiene exportación. */
export function celda(datos, clave, mes) {
  return datos?.celdas?.[clave]?.[String(mes)] || null;
}

/** ¿El mes aún no termina? (no se puede cerrar: no se ofrece "—" → nueva exportación). */
export function mesAbierto(anio, mes, hoy = new Date()) {
  return anio > hoy.getFullYear() || (anio === hoy.getFullYear() && mes > hoy.getMonth() + 1);
}

/** Folio corto para la celda: "EXP-2026-0007" → "0007". */
export function folioCorto(folio) {
  const m = String(folio || '').match(/(\d+)$/);
  return m ? m[1] : String(folio || '');
}

/** Resumen de la fila: cuántos meses cerrados (hasta hoy) y cuántos con ⚠. */
export function resumenFila(datos, clave, anio, hoy = new Date()) {
  let cerrados = 0;
  let cambiaron = 0;
  let posibles = 0;
  for (let mes = 1; mes <= 12; mes += 1) {
    if (mesAbierto(anio, mes, hoy)) continue;
    posibles += 1;
    const c = celda(datos, clave, mes);
    if (c) { cerrados += 1; if (c.estado === 'CAMBIO') cambiaron += 1; }
  }
  return { cerrados, cambiaron, posibles };
}
