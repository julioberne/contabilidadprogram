/* ============================================================
   DiarioTab.jsx — Libro diario del contador (todos los estados) +
   asiento manual. Reutiliza la bandeja con estado TODOS.
   ============================================================ */
import { useState } from 'react';
import BandejaTab from './BandejaTab.jsx';
import LineasEditor, { lineasValidas, lineasPayload } from '../components/LineasEditor.jsx';
import { api } from '../useContadoresApi.js';
import { hoy } from '../fmt.js';

export default function DiarioTab({ portfolioId, portfolios, cuentas, onCambio }) {
  const [nuevo, setNuevo] = useState(false);
  const [form, setForm] = useState({ fecha: hoy(), descripcion: '', contabilizar: false, portfolio_id: portfolioId, lineas: [] });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [version, setVersion] = useState(0);
  const btn = 'border border-black px-1.5 py-0.5 text-[10px] font-bold hover:bg-black hover:text-white disabled:opacity-40';
  const inp = 'border border-black px-1 py-0.5 text-[10px] font-mono bg-white';

  const crear = async () => {
    if (!lineasValidas(form.lineas)) return;
    setBusy(true); setMsg('');
    try {
      const d = await api.post('/contadores/asientos', {
        portfolio_id: form.portfolio_id ?? null, fecha: form.fecha, descripcion: form.descripcion,
        lineas: lineasPayload(form.lineas), contabilizar: form.contabilizar,
      });
      setMsg(`✔ Asiento ${d.resultado.entry_group_id} creado (${d.resultado.estado}).`);
      setForm({ fecha: hoy(), descripcion: '', contabilizar: false, portfolio_id: portfolioId, lineas: [] });
      setNuevo(false);
      setVersion((v) => v + 1);
      onCambio?.();
    } catch (e) { setMsg(`✖ ${e.message}`); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-2">
      <div className="bg-white border-2 border-black p-2 shadow-brutal space-y-1">
        <div className="flex items-center gap-2">
          <button className={`${btn} ${nuevo ? 'bg-black text-white' : ''}`} onClick={() => setNuevo(!nuevo)}>+ ASIENTO MANUAL</button>
          {msg && <span className="text-[10px] font-bold">{msg}</span>}
        </div>
        {nuevo && (
          <div className="space-y-1 border-t border-black pt-1">
            <div className="flex flex-wrap gap-2 items-center text-[10px]">
              <label>Fecha <input type="date" className={inp} value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} /></label>
              <label>Portafolio
                <select className={`${inp} ml-1`} value={form.portfolio_id ?? ''} onChange={(e) => setForm({ ...form, portfolio_id: e.target.value === '' ? null : Number(e.target.value) })}>
                  <option value="">(sin portafolio)</option>
                  {(portfolios || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </label>
              <input className={`${inp} flex-1`} placeholder="descripción" value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} />
              <label className="flex items-center gap-1"><input type="checkbox" checked={form.contabilizar} onChange={(e) => setForm({ ...form, contabilizar: e.target.checked })} /> contabilizar directo</label>
            </div>
            <LineasEditor lineas={form.lineas} cuentas={cuentas} listId="coa-manual" onChange={(l) => setForm({ ...form, lineas: l })} />
            <button className={`${btn} bg-brutalGreen`} disabled={busy || !lineasValidas(form.lineas)} onClick={crear}>{busy ? '…' : 'CREAR ASIENTO'}</button>
          </div>
        )}
      </div>
      <BandejaTab key={version} portfolioId={portfolioId} cuentas={cuentas} estadoInicial="TODOS" onCambio={onCambio} />
    </div>
  );
}
