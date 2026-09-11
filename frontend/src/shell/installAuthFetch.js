/* ============================================================
   installAuthFetch.js — Inyección global del token de sesión.

   La remediación 2026-09-11 protegió TODOS los endpoints mutadores
   del backend con Depends(require_admin/require_auth). Decenas de
   componentes hacen fetch() directo a la API sin headers de auth
   (EvidenceModal, ContextPanel, cartera, CT, hub, HR…): en lugar de
   tocar cada llamada, este wrapper envuelve window.fetch UNA sola
   vez y añade Authorization: Bearer <token> a toda petición dirigida
   a la API propia. Solo a la API propia: nunca a hosts externos
   (p. ej. status.supabase.com).

   Se importa primero en main.jsx. Un Authorization explícito de la
   llamada siempre gana sobre el inyectado.
   ============================================================ */
import API_BASE from '../config';
import { authHeaders } from './authHeaders';

const nativeFetch = window.fetch.bind(window);

function esApiPropia(url) {
  if (typeof url !== 'string' || !url) return false;
  // API_BASE es '/api' (default) o VITE_API_URL absoluto en despliegues
  return url.startsWith(API_BASE) || url.startsWith('/api/') || url === '/api';
}

window.fetch = function (input, init) {
  try {
    const url = typeof input === 'string'
      ? input
      : (input instanceof URL ? input.href : (input && input.url) || '');
    if (esApiPropia(url)) {
      const auth = authHeaders();
      if (auth.Authorization) {
        const base = (init && init.headers)
          || (typeof input === 'object' && input && input.headers)
          || {};
        const headers = new Headers(base);
        if (!headers.has('Authorization')) {
          headers.set('Authorization', auth.Authorization);
        }
        init = { ...(init || {}), headers };
      }
    }
  } catch {
    // El wrapper jamás debe tumbar una petición: ante cualquier duda,
    // se delega al fetch nativo tal cual.
  }
  return nativeFetch(input, init);
};
