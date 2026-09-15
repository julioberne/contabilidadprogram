/* ============================================================
   api.js — Cliente del módulo Análisis. Mismo patrón que
   useContadoresApi: todas las llamadas llevan Authorization y
   lanzan Error(detail) honesto si el backend responde con error.
   ============================================================ */
import { API } from '../config';
import { authHeaders } from '../shell/authHeaders.js';

async function llamar(method, path, body) {
  const r = await fetch(`${API}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data;
  try { data = await r.json(); } catch { data = null; }
  if (!r.ok) {
    const detail = data?.detail;
    const msg = typeof detail === 'string' ? detail
      : Array.isArray(detail) ? detail.map(d => d.msg || JSON.stringify(d)).join('; ')
      : r.status === 401 ? 'Sesión expirada: inicia sesión de nuevo.'
      : `Error ${r.status}`;
    const err = new Error(msg); err.status = r.status; throw err;
  }
  return data;
}

export const api = {
  get: (path) => llamar('GET', path),
  post: (path, body) => llamar('POST', path, body ?? {}),
};
