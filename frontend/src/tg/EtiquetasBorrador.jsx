/* ============================================================
   EtiquetasBorrador.jsx — 🏷️ Etiquetas del borrador en la Mini App
   (24-oct-2026). En el chat los botones tienen espacio limitado;
   aquí se ven como fichas, se buscan por nombre (servidor, top-N:
   estándar H3 — nunca el catálogo entero) y se crean si no existen.
   Se guardan con el mismo PUT de la bandeja (`avisar_chat`): el bot
   reenvía el resumen y, al confirmar, van a la transacción.
   ============================================================ */
import { useEffect, useMemo, useState } from 'react';
import { API } from '../config';
import { useBusqueda } from '../shared/busqueda/useBusqueda.js';

const norm = (s) => (s || '').toString().trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, ' ');

export default function EtiquetasBorrador({ draft, onGuardado, logout }) {
  const puestas = useMemo(() => (draft.payload?.tags || []).map(String), [draft.payload?.tags]);
  const [seleccion, setSeleccion] = useState(puestas);
  const [q, setQ] = useState('');
  const [version, setVersion] = useState(0);
  const [estado, setEstado] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const { items, mas, cargando } = useBusqueda('etiquetas', q, {
    minimo: 0, limite: 30, version, onNoAutorizado: logout,
  });

  // Lo que manda es el borrador más reciente (p. ej. tras guardar concepto o tercero)
  useEffect(() => { setSeleccion(puestas); }, [draft.id, puestas]);

  const nombres = items.map(t => String(t.name).trim());
  const otras = nombres.filter(n => !seleccion.includes(n));
  const yaExiste = q.trim() && [...nombres, ...seleccion].some(n => norm(n) === norm(q));
  const cambio = seleccion.length !== puestas.length || seleccion.some(n => !puestas.includes(n));

  const alternar = (nombre) => setSeleccion(s => (s.includes(nombre) ? s.filter(n => n !== nombre) : [...s, nombre]));

  const crear = async () => {
    const nombre = q.trim().replace(/\s+/g, ' ');
    setOcupado(true); setEstado('');
    try {
      const r = await fetch(`${API}/tags`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: nombre }),
      });
      const cuerpo = await r.json().catch(() => ({}));
      if (r.status === 401) { logout(); return; }
      if (!r.ok) { setEstado(`No se pudo crear «${nombre}»: ${cuerpo.detail || r.status}`); return; }
      const creada = String(cuerpo.name || nombre).trim();
      setSeleccion(s => (s.includes(creada) ? s : [...s, creada]));
      setQ(''); setVersion(v => v + 1);
      setEstado(`Creada «${creada}» y marcada. Toca «Guardar etiquetas» para ponerla en el borrador.`);
    } catch {
      setEstado('Sin conexión con el servidor.');
    } finally {
      setOcupado(false);
    }
  };

  const guardar = async () => {
    setOcupado(true); setEstado('');
    try {
      const r = await fetch(`${API}/bot/drafts/${draft.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags: seleccion, avisar_chat: true }),
      });
      const cuerpo = await r.json().catch(() => ({}));
      if (r.status === 401) { logout(); return; }
      if (!r.ok) { setEstado(`No se pudo guardar: ${cuerpo.detail || r.status}`); return; }
      onGuardado(cuerpo);
      setEstado('Etiquetas guardadas. El bot te manda el resumen actualizado al chat.');
    } catch {
      setEstado('Sin conexión con el servidor.');
    } finally {
      setOcupado(false);
    }
  };

  const ficha = (nombre, marcada) => (
    <button key={nombre} type="button" disabled={!draft.editable} onClick={() => alternar(nombre)}
      aria-pressed={marcada} aria-label={`${marcada ? 'Quitar' : 'Poner'} etiqueta ${nombre}`}
      className={`border-2 border-black px-2 py-0.5 text-[11px] disabled:opacity-60 ${marcada ? 'bg-black text-white' : 'bg-white hover:bg-brutalGreen'}`}>
      {marcada ? '✓ ' : ''}{nombre}
    </button>
  );

  return (
    <div className="border-2 border-black p-2 bg-white font-mono text-xs space-y-1.5" aria-label="Etiquetas del borrador">
      <div className="text-[10px] uppercase text-gray-500">🏷️ Etiquetas</div>
      {seleccion.length > 0 && <div className="flex flex-wrap gap-1">{seleccion.map(n => ficha(n, true))}</div>}
      {draft.editable && (
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="🔎 Buscar o crear etiqueta"
          aria-label="Buscar etiqueta" className="w-full border-2 border-black px-2 py-1.5 text-sm outline-none focus:border-brutalGreen bg-white" />
      )}
      {draft.editable && (
        <div className="flex flex-wrap gap-1">
          {otras.map(n => ficha(n, false))}
          {!cargando && q.trim() && otras.length === 0 && !yaExiste && (
            <span className="text-gray-500">Ninguna etiqueta contiene «{q.trim()}».</span>
          )}
        </div>
      )}
      {draft.editable && mas && <div className="text-[10px] text-gray-500">Hay más: escribe para buscar.</div>}
      {draft.editable && q.trim() && !yaExiste && (
        <button type="button" onClick={crear} disabled={ocupado}
          className="border-2 border-black px-2 py-1 text-[11px] font-bold uppercase bg-white hover:bg-black hover:text-white disabled:opacity-50">
          ➕ Crear «{q.trim()}»
        </button>
      )}
      {draft.editable && (
        <button type="button" onClick={guardar} disabled={!cambio || ocupado}
          className="w-full border-2 border-black bg-brutalGreen px-2 py-1.5 text-xs font-bold uppercase hover:bg-black hover:text-white disabled:opacity-40">
          {ocupado ? 'Guardando…' : 'Guardar etiquetas'}
        </button>
      )}
      {estado && <div role="status" className="text-[11px]">{estado}</div>}
    </div>
  );
}
