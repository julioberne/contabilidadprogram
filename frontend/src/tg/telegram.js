/* ============================================================
   tg/telegram.js — Envoltorio mínimo del SDK de Telegram Web Apps.
   Fuera de Telegram (navegador normal, tests) todo es inofensivo.
   ============================================================ */

export function tg() {
  return (typeof window !== 'undefined' && window.Telegram && window.Telegram.WebApp) || null;
}

/** Avisa a Telegram que la página cargó y pide pantalla completa. */
export function tgReady() {
  const w = tg();
  if (!w) return;
  try { w.ready(); } catch { /* sin SDK */ }
  try { w.expand(); } catch { /* sin SDK */ }
}

/** Cierra la Mini App; fuera de Telegram intenta cerrar la pestaña. */
export function tgClose() {
  const w = tg();
  if (w) {
    try { w.close(); return; } catch { /* sigue abajo */ }
  }
  try { window.close(); } catch { /* nada */ }
}

/** Parámetro de la URL con la que el bot abrió la Mini App (?draft=N). */
export function tgParam(nombre) {
  try {
    return new URLSearchParams(window.location.search).get(nombre);
  } catch {
    return null;
  }
}
