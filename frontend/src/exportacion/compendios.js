/* ============================================================
   compendios.js — Lógica pura del 🤝 Compendio para el cliente
   (spec 13.6): datos para /api/compendios, validación, link
   completo, texto de WhatsApp y estado legible de cada compendio.
   ============================================================ */

export const VIGENCIAS = [7, 15, 30, 90];
export const MAX_COMPENDIO = 1000;                // = MAX_TX del driver
export const MAX_NOTA = 1000;
export const COMPENDIO_INICIAL = { nota: '', vigencia: 15, identificacion: true, ubicaciones: true };

/** Cuerpo de POST /api/compendios(/preflight). */
export function datosCompendio(ids, nombre, c) {
  const d = {
    tx_ids: [...ids], vigencia_dias: c.vigencia,
    identificacion: !!c.identificacion, ubicaciones: !!c.ubicaciones,
  };
  if (nombre?.trim()) d.nombre = nombre.trim();
  if (c.nota?.trim()) d.nota = c.nota.trim();
  return d;
}

/** Error legible del formulario del compendio, o null. */
export function validarCompendio(n, c) {
  if (!n) return 'Marca al menos una transacción.';
  if (n > MAX_COMPENDIO) return `Máximo ${MAX_COMPENDIO} transacciones por compendio (${n} marcadas).`;
  if (!VIGENCIAS.includes(c.vigencia)) return 'Elige cuánto dura el link.';
  if ((c.nota || '').length > MAX_NOTA) return `La nota admite máximo ${MAX_NOTA} caracteres.`;
  return null;
}

/** "2026-10-21T14:00:00+00:00" → "21/10/2026". */
export function fechaCorta(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

/** Ruta del backend (/c/…) → link completo con el dominio donde se está usando la app. */
export function linkCompleto(ruta, origen) {
  return ruta ? `${String(origen || '').replace(/\/$/, '')}${ruta}` : null;
}

export function textoWhatsApp({ nombre, folio, link, expira_en: expira }) {
  return `${nombre} (${folio})\nComprobantes y detalle: ${link}\nVálido hasta el ${fechaCorta(expira)}.`;
}

/** wa.me abre WhatsApp con el texto listo: FIN-SYS no envía nada por su cuenta. */
export function urlWhatsApp(texto) {
  return `https://wa.me/?text=${encodeURIComponent(texto)}`;
}

export const ESTADOS = {
  vigente: { texto: 'VIGENTE', clase: 'bg-brutalGreen' },
  vencido: { texto: 'VENCIDO', clase: 'bg-brutalNeutral' },
  revocado: { texto: 'REVOCADO', clase: 'bg-brutalCrimson text-white' },
};

/** "hace 5 min" · "hace 3 h" · "hace 2 días" (para la última visita). */
export function haceCuanto(iso, ahora = new Date()) {
  if (!iso) return null;
  const min = Math.max(0, Math.round((ahora - new Date(iso)) / 60000));
  if (min < 1) return 'hace un momento';
  if (min < 60) return `hace ${min} min`;
  const h = Math.round(min / 60);
  if (h < 24) return `hace ${h} h`;
  const d = Math.round(h / 24);
  return `hace ${d} día${d === 1 ? '' : 's'}`;
}
