/* ============================================================
   useDiarioFiltrado.js — Filas, totales y grupos del Libro
   Diario desde /api/diario/movimientos (filtros en el servidor).

   - Cambia un filtro → página 1 de nuevo (la petición vieja se
     aborta para que una respuesta lenta no pise a la nueva).
   - `senal` cambia cuando el resto del módulo mutó datos (nueva
     TX, edición, borrado): se recarga conservando lo ya cargado.
   - parchar/quitar actualizan una fila sin viajar al servidor.
   - Estándar H4: «cargar más» pide solo la página (totales=false)
     y, en orden por fecha, sigue desde la última fila vista
     (`siguiente` del servidor): la página 100 cuesta lo que la 1.
   ============================================================ */
import { useCallback, useEffect, useRef, useState } from 'react';
import { API } from '../../../config';
import { aParametros } from './diarioFiltros.js';

const PAGINA = 50;
export const MAX_TODO = 5000;

async function pedir(params, signal) {
  const r = await fetch(`${API}/diario/movimientos?${params}`, { signal });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.detail || `Error ${r.status} al filtrar el Diario`);
  return d;
}

export function useDiarioFiltrado({ portfolio, filtros, orden, agrupar, senal }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [totales, setTotales] = useState(null);
  const [grupos, setGrupos] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [cargandoMas, setCargandoMas] = useState(false);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');
  const abortRef = useRef(null);
  const cargadasRef = useRef(0);
  const siguienteRef = useRef(null);       // cursor {fecha, id} de la próxima página

  const base = useCallback(() => {
    const p = aParametros(filtros, { orden, agrupar });
    p.delete('rango');                      // solo es la etiqueta del chip
    if (portfolio) p.set('portfolio', portfolio);
    return p;
  }, [portfolio, filtros, orden, agrupar]);
  const clave = base().toString();

  const cargar = useCallback(async (limite) => {
    abortRef.current?.abort();
    const ctl = new AbortController();
    abortRef.current = ctl;
    setCargando(true); setError('');
    try {
      const p = base(); p.set('limit', String(limite)); p.set('offset', '0');
      const d = await pedir(p, ctl.signal);
      setRows(d.transactions || []); cargadasRef.current = (d.transactions || []).length;
      siguienteRef.current = d.siguiente || null;
      setTotal(d.total || 0); setTotales(d.totales || null); setGrupos(d.grupos || null);
      setAviso(d.aviso || '');
    } catch (e) {
      if (e.name !== 'AbortError') setError(e.message);
    } finally {
      if (abortRef.current === ctl) setCargando(false);
    }
  }, [base]);

  // Filtro nuevo → desde la primera página.
  useEffect(() => { cargar(PAGINA); }, [clave]); // eslint-disable-line react-hooks/exhaustive-deps

  // Mutación en otra parte del módulo → misma cantidad de filas, datos frescos.
  const primera = useRef(true);
  useEffect(() => {
    if (primera.current) { primera.current = false; return; }
    cargar(Math.max(PAGINA, cargadasRef.current));
  }, [senal]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => abortRef.current?.abort(), []);

  const cargarMas = useCallback(async () => {
    setCargandoMas(true);
    try {
      const p = base(); p.delete('agrupar');
      p.set('limit', String(PAGINA)); p.set('totales', 'false');
      const sig = siguienteRef.current;
      if (sig) { p.set('despues_fecha', sig.fecha); p.set('despues_id', String(sig.id)); }
      else p.set('offset', String(cargadasRef.current));
      const d = await pedir(p);
      siguienteRef.current = d.siguiente || null;
      setRows((prev) => {
        const vistos = new Set(prev.map((t) => t.id));
        const nuevas = [...prev, ...(d.transactions || []).filter((t) => !vistos.has(t.id))];
        cargadasRef.current = nuevas.length;
        return nuevas;
      });
    } catch (e) { setError(e.message); }
    finally { setCargandoMas(false); }
  }, [base]);

  /** TODO lo filtrado (hasta MAX_TODO filas), sin tocar la tabla. */
  const traerTodo = useCallback(async () => {
    const p = base(); p.delete('agrupar');
    p.set('limit', String(MAX_TODO)); p.set('offset', '0'); p.set('totales', 'false');
    const d = await pedir(p);
    return d.transactions || [];
  }, [base]);

  const parchar = useCallback((txId, tx) => {
    setRows((prev) => prev.map((t) => (t.id === txId ? { ...t, ...tx } : t)));
  }, []);
  const quitar = useCallback((txId) => {
    setRows((prev) => prev.filter((t) => t.id !== txId));
    setTotal((n) => Math.max(0, n - 1));
  }, []);

  return { rows, total, totales, grupos, cargando, cargandoMas, error, aviso,
    cargarMas, traerTodo, recargar: () => cargar(Math.max(PAGINA, cargadasRef.current)), parchar, quitar };
}

export default useDiarioFiltrado;
