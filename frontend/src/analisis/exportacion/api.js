/* ============================================================
   api.js — Cliente del organizador contable 📦 (13.5).
   Mismo patrón que ../api.js (Authorization + Error(detail) honesto),
   más PATCH/DELETE, subida multipart y descargas como blob: los
   archivos jamás tienen URL pública (R-135-05).
   ============================================================ */
import { API } from '../../config';
import { authHeaders } from '../../shell/authHeaders.js';
import { nombreDescarga } from './organizador.js';

async function error(r) {
  let data = null;
  try { data = await r.json(); } catch { /* sin cuerpo */ }
  const detail = data?.detail;
  const msg = typeof detail === 'string' ? detail
    : Array.isArray(detail) ? detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
    : r.status === 401 ? 'Sesión expirada: inicia sesión de nuevo.'
    : r.status === 413 ? 'El archivo supera el tope de tamaño.'
    : `Error ${r.status}`;
  const err = new Error(msg); err.status = r.status;
  return err;
}

async function llamar(method, path, body) {
  const r = await fetch(`${API}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) throw await error(r);
  try { return await r.json(); } catch { return null; }
}

async function blob(path) {
  const r = await fetch(`${API}${path}`, { headers: { ...authHeaders() } });
  if (!r.ok) throw await error(r);
  return { blob: await r.blob(), disposition: r.headers.get('Content-Disposition') };
}

export const api = {
  get: (path) => llamar('GET', path),
  post: (path, body) => llamar('POST', path, body ?? {}),
  patch: (path, body) => llamar('PATCH', path, body ?? {}),
  del: (path) => llamar('DELETE', path),

  /** Multipart: el navegador pone el boundary (no se manda Content-Type). */
  async subir(formData) {
    const r = await fetch(`${API}/accounting-files/upload`, {
      method: 'POST', headers: { ...authHeaders() }, body: formData,
    });
    if (!r.ok) throw await error(r);
    return r.json();
  },

  /** Binario de la vista previa (PDF/imagen) → URL de objeto local. Revocar al cerrar. */
  async urlVistaPrevia(id) {
    const { blob: b } = await blob(`/accounting-files/${id}/preview`);
    return URL.createObjectURL(b);
  },

  /** Descarga el archivo exacto con su nombre (cuenta la descarga en el backend). */
  async descargar(id, respaldo = 'archivo') {
    const { blob: b, disposition } = await blob(`/accounting-files/${id}/download`);
    const url = URL.createObjectURL(b);
    const a = document.createElement('a');
    a.href = url;
    a.download = nombreDescarga(disposition, respaldo);
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  },
};
