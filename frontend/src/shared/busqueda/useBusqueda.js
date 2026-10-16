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
export function urlBusqueda(recurso, q, { limite = 8, ids, ident, nombre, despues, orden, conTotal } = {}) {
  const p = new URLSearchParams();
  if (ids && ids.length) p.set('ids', ids.join(','));
  else if (ident) p.set('ident', ident);
  else if (nombre) p.set('nombre', nombre);
  else if (q) p.set('q', q);
  p.set('limite', String(limite));
  if (despues) { p.set('despues_nombre', despues.nombre); p.set('despues_id', String(despues.id)); }
  if (orden) p.set('orden', orden);
  if (conTotal) p.set('con_total', 'true');
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

/**
 * Tercero que coincide EXACTAMENTE por documento (o, sin documento, por nombre):
 * el semáforo "reutiliza / crea" del registro. undefined = consultando.
 */
export function useTerceroExacto({ ident, nombre, excluir = '999999999', debounceMs = 300 }) {
  const [res, setRes] = useState({ clave: '', tercero: null });
  const doc = (ident || '').trim();
  const nom = doc ? '' : (nombre || '').trim();
  const clave = doc ? `i:${doc}` : (nom ? `n:${nom.toLowerCase()}` : '');

  useEffect(() => {
    if (!clave) return undefined;
    const ctl = new AbortController();
    const t = setTimeout(async () => {
      try {
        const d = await buscarUna('terceros', doc ? { ident: doc, limite: 1 } : { nombre: nom, limite: 1 }, ctl.signal);
        const f = (d.items || []).find((x) => String(x.identification_number) !== excluir) || null;
        setRes({ clave, tercero: f });
      } catch (e) {
        if (e.name !== 'AbortError') setRes({ clave, tercero: null });
      }
    }, debounceMs);
    return () => { clearTimeout(t); ctl.abort(); };
  }, [clave]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!clave) return null;
  return res.clave === clave ? res.tercero : undefined;
}

/** Listado paginado (panel de gestión): páginas de `tamano`, "cargar más" y total. */
export function usePaginaTerceros(q, { tamano = 50, version = 0 } = {}) {
  const [estado, setEstado] = useState({ items: [], total: 0, siguiente: null, cargando: false, error: '' });
  const texto = (q || '').trim();
  const pedir = async (despues, signal) => {
    const r = await fetch(urlBusqueda('terceros', texto, { limite: tamano, despues, orden: 'nombre', conTotal: true }), { signal });
    if (!r.ok) throw new Error(`Error ${r.status}`);
    return r.json();
  };
  useEffect(() => {
    const ctl = new AbortController();
    setEstado((e) => ({ ...e, cargando: true, error: '' }));   // eslint-disable-line react-hooks/set-state-in-effect
    const t = setTimeout(() => {
      pedir(null, ctl.signal)
        .then((d) => setEstado({ items: d.items || [], total: d.total || 0, siguiente: d.siguiente || null, cargando: false, error: '' }))
        .catch((e) => { if (e.name !== 'AbortError') setEstado({ items: [], total: 0, siguiente: null, cargando: false, error: e.message }); });
    }, texto ? DEBOUNCE_MS : 0);
    return () => { clearTimeout(t); ctl.abort(); };
  }, [texto, tamano, version]); // eslint-disable-line react-hooks/exhaustive-deps

  const cargarMas = async () => {
    setEstado((e) => ({ ...e, cargando: true }));
    try {
      if (!estado.siguiente) { setEstado((e) => ({ ...e, cargando: false })); return; }
      const d = await pedir(estado.siguiente);
      setEstado((e) => ({ ...e, items: [...e.items, ...(d.items || [])], total: d.total || e.total,
                          siguiente: d.siguiente || null, cargando: false }));
    } catch (err) {
      setEstado((e) => ({ ...e, cargando: false, error: err.message }));
    }
  };
  return { ...estado, cargarMas, hayMas: !!estado.siguiente };
}

export default useBusqueda;
