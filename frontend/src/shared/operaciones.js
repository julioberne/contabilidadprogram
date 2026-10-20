/* ============================================================
   operaciones.js — Seguir un trabajo de la cola (estándar H5).

   Una ruta que encola responde 202 con { operacion, en_cola: true }.
   esperarOperacion(id) consulta GET /api/operaciones/{id} con pausas
   crecientes (1,5 s → 5 s) hasta que queda HECHA (devuelve su
   resultado) o FALLIDA (lanza Error con el motivo). Un 503/429
   pasajero no corta la espera: se reintenta.
   ============================================================ */
import { API } from '../config';
import { authHeaders } from '../shell/authHeaders.js';

const dormir = (ms) => new Promise((ok) => setTimeout(ok, ms));

export async function esperarOperacion(id, {
  cadaMs = 1500, maxMs = 10 * 60 * 1000, onEstado, signal, pedir = fetch, esperar = dormir,
} = {}) {
  const fin = Date.now() + maxMs;
  let pausa = cadaMs;
  for (;;) {
    if (signal?.aborted) throw new DOMException('Cancelado', 'AbortError');
    const r = await pedir(`${API}/operaciones/${id}`, { headers: { ...authHeaders() }, signal });
    if (r.ok) {
      const op = await r.json();
      onEstado?.(op);
      if (op.estado === 'HECHA') return op.resultado;
      if (op.estado === 'FALLIDA') throw new Error(op.error || 'La operación falló.');
    } else if (r.status !== 503 && r.status !== 429) {
      throw new Error(r.status === 404 ? 'La operación ya no existe.' : `Error ${r.status} al consultar la operación.`);
    }
    if (Date.now() > fin) {
      throw new Error('Sigue en preparación: quedará en el organizador cuando termine.');
    }
    await esperar(pausa);
    pausa = Math.min(5000, Math.round(pausa * 1.3));
  }
}

export default esperarOperacion;
