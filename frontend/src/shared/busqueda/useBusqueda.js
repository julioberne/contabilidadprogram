/* ============================================================
   useBusqueda.js — Búsqueda remota única (estándar de consultas,
   hito H3, reglas F1–F3). Un solo comportamiento para todos los
   selectores: debounce de 200 ms, cancela la petición anterior
   (AbortController), ignora respuestas viejas y pide al servidor
   solo el top-N (/api/buscar/<recurso>). Nunca el catálogo entero.

     const { items, mas, cargando, error } = useBusqueda('terceros', q, { minimo: 2 });
   ============================================================ */
import { useEffect, useRef, useState } from 'react';
import { API } from '../../config';

export const DEBOUNCE_MS = 200;

/** URL de búsqueda (pura: se prueba sin red). */
export function urlBusqueda(recurso, q, { limite = 8, ids, ident } = {}) {
  const p = new URLSearchParams();
  if (ids && ids.length) p.set('ids', ids.join(','));
  else if (ident) p.set('ident', ident);
  else if (q) p.set('q', q);
  p.set('limite', String(limite));
  return `${API}/buscar/${recurso}?${p}`;
}

/** Una consulta puntual (resolver fichas por id o documento). */
export async function buscarUna(recurso, opciones, signal) {
  const r = await fetch(urlBusqueda(recurso, '', opciones), { signal });
  if (r.status === 401) { const e = new Error('sesión'); e.status = 401; throw e; }
  if (!r.ok) throw new Error(`Error ${r.status} buscando ${recurso}`);
  return r.json();
}

/**
 * @param {string} recurso   'terceros' | 'cuentas' | 'etiquetas'
 * @param {string} q         texto del usuario
 * @param {{minimo?: number, limite?: number, debounceMs?: number, version?: any, onNoAutorizado?: Function}} opciones
 *   minimo: con menos caracteres no se busca (items vacíos); 0 = top de usados.
 *   version: cámbiala para repetir la búsqueda (p. ej. tras crear o editar).
 */
export function useBusqueda(recurso, q, { minimo = 2, limite = 8, debounceMs = DEBOUNCE_MS, version = 0, onNoAutorizado } = {}) {
  const [estado, setEstado] = useState({ items: [], mas: false, cargando: false, error: '' });
  const ultima = useRef(0);
  const texto = (q || '').trim();
  const activa = texto.length >= minimo;

  useEffect(() => {
    if (!activa) {
      setEstado({ items: [], mas: false, cargando: false, error: '' });   // eslint-disable-line react-hooks/set-state-in-effect
      return undefined;
    }
    const id = ++ultima.current;
    const ctl = new AbortController();
    setEstado((e) => ({ ...e, cargando: true, error: '' }));
    const t = setTimeout(async () => {
      try {
        const r = await fetch(urlBusqueda(recurso, texto, { limite }), { signal: ctl.signal });
        if (r.status === 401) { onNoAutorizado?.(); return; }
        const d = await r.json().catch(() => ({}));
        if (id !== ultima.current) return;                    // llegó tarde: ya hay otra búsqueda
        if (!r.ok) { setEstado({ items: [], mas: false, cargando: false, error: d.detail || `Error ${r.status}` }); return; }
        setEstado({ items: d.items || [], mas: !!d.mas, cargando: false, error: '' });
      } catch (e) {
        if (e.name !== 'AbortError' && id === ultima.current) {
          setEstado({ items: [], mas: false, cargando: false, error: 'Sin conexión con el servidor.' });
        }
      }
    }, debounceMs);
    return () => { clearTimeout(t); ctl.abort(); };
  }, [recurso, texto, activa, limite, debounceMs, version]); // eslint-disable-line react-hooks/exhaustive-deps

  return estado;
}

export default useBusqueda;
