/* ============================================================
   useContadoresApi.js — Cliente del módulo Contadores.
   TODAS las llamadas llevan Authorization (authHeaders) y lanzan
   Error(detail) si el backend responde con error.
   ============================================================ */
import { useCallback, useState } from 'react';
import { API } from '../config';
import { authHeaders } from '../shell/authHeaders';

const hdrs = () => ({ 'Content-Type': 'application/json', ...authHeaders() });

async function llamar(method, path, body) {
  const r = await fetch(`${API}${path}`, {
    method, headers: hdrs(), body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data;
  try { data = await r.json(); } catch { data = null; }
  if (!r.ok) {
    const detail = data?.detail;
    const msg = typeof detail === 'string' ? detail
      : Array.isArray(detail) ? detail.map(d => d.msg || JSON.stringify(d)).join('; ')
      : r.status === 401 ? 'Sesión expirada: inicia sesión de nuevo.'
      : r.status === 403 ? 'Sin permiso (se requiere rol contador o administrador).'
      : `Error ${r.status}`;
    const err = new Error(msg); err.status = r.status; throw err;
  }
  return data;
}

export const api = {
  get: (path) => llamar('GET', path),
  post: (path, body) => llamar('POST', path, body ?? {}),
  put: (path, body) => llamar('PUT', path, body ?? {}),
  del: (path) => llamar('DELETE', path),
};

/** Estado de carga/error compartido para una pestaña. */
export function useContadoresApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const run = useCallback(async (fn) => {
    setLoading(true); setError('');
    try { return await fn(api); }
    catch (e) { setError(e.message || 'Error'); throw e; }
    finally { setLoading(false); }
  }, []);
  return { api, run, loading, error, setError };
}

export default useContadoresApi;
