/* ============================================================
   AccionesLote.jsx — Editar varias transacciones marcadas a la
   vez: agregar una etiqueta o cambiar la cuenta COA. Usa el PUT
   /transactions/{id} de siempre (admin), una por una, y reporta
   cuántas salieron bien.
   ============================================================ */
import React from 'react';
import { API } from '../../../config';
import { agregarEtiqueta } from './diarioFiltros.js';

const boton = 'border-2 border-black px-2 py-0.5 text-[10px] font-bold uppercase hover:bg-black hover:text-white disabled:opacity-40';

export default function AccionesLote({ txs, coaFlatAccounts, onHecho }) {
  const [modo, setModo] = React.useState('');
  const [valor, setValor] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg] = React.useState('');
  if (!txs.length) return null;

  const aplicar = async () => {
    if (!valor.trim()) return;
    const cambios = txs.map((t) => [t, modo === 'etiqueta' ? { tags: agregarEtiqueta(t.tags, valor) } : { category: valor }])
      // agregarEtiqueta devuelve el MISMO arreglo si ya la tenía
      .filter(([t, c]) => (modo === 'etiqueta' ? c.tags !== t.tags : t.category !== valor));
    if (!cambios.length) { setMsg('Nada que cambiar: todas ya lo tenían.'); return; }
    if (!window.confirm(`¿Aplicar a ${cambios.length} transacción(es)?`)) return;
    setBusy(true); setMsg('');
    let ok = 0; const fallos = [];
    for (const [t, cuerpo] of cambios) {
      try {
        const r = await fetch(`${API}/transactions/${t.id}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo),
        });
        if (r.ok) ok += 1;
        else { const d = await r.json().catch(() => ({})); fallos.push(`#${t.id}: ${d.detail || r.status}`); }
      } catch { fallos.push(`#${t.id}: sin conexión`); }
    }
    setBusy(false);
    setMsg(`✅ ${ok} actualizada(s)${fallos.length ? ` · ❌ ${fallos.length}: ${fallos.slice(0, 3).join(' · ')}` : ''}`);
    if (ok) { setModo(''); setValor(''); onHecho?.(); }
  };

  return (
    <div className="mt-1 border-2 border-black bg-white px-2 py-1 flex flex-wrap items-center gap-1 text-[10px]"
      role="region" aria-label="Editar en lote">
      <span className="font-bold uppercase">✎ Editar {txs.length} marcada{txs.length === 1 ? '' : 's'}:</span>
      <button type="button" className={`${boton} ${modo === 'etiqueta' ? 'bg-black text-white' : 'bg-white'}`}
        onClick={() => { setModo(modo === 'etiqueta' ? '' : 'etiqueta'); setValor(''); setMsg(''); }}>🏷 Agregar etiqueta</button>
      <button type="button" className={`${boton} ${modo === 'categoria' ? 'bg-black text-white' : 'bg-white'}`}
        onClick={() => { setModo(modo === 'categoria' ? '' : 'categoria'); setValor(''); setMsg(''); }}>📂 Cambiar cuenta COA</button>
      {modo === 'etiqueta' && (
        <input autoFocus value={valor} onChange={(e) => setValor(e.target.value)} placeholder="Etiqueta (ej. Bonaire obra)"
          onKeyDown={(e) => { if (e.key === 'Enter') aplicar(); }}
          className="border-2 border-black px-1.5 py-0.5 font-mono" aria-label="Etiqueta a agregar" />
      )}
      {modo === 'categoria' && (
        <select autoFocus value={valor} onChange={(e) => setValor(e.target.value)} aria-label="Cuenta COA nueva"
          className="border-2 border-black px-1.5 py-0.5 font-mono max-w-[260px]">
          <option value="">Elige la cuenta…</option>
          {(coaFlatAccounts || []).map((a) => <option key={a.id} value={`${a.code} - ${a.name}`}>{a.code} - {a.name}</option>)}
        </select>
      )}
      {modo && <button type="button" disabled={busy || !valor.trim()} onClick={aplicar} className={`${boton} bg-brutalAmber`}>
        {busy ? 'Aplicando…' : 'Aplicar'}</button>}
      {msg && <span className="font-mono">{msg}</span>}
    </div>
  );
}
