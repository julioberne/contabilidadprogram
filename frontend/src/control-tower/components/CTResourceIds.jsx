// CTResourceIds.jsx — Inventario de IDs / Recursos clasificados
import React, { useState } from 'react';

const CATEGORIES = ['FISCAL', 'LEGAL', 'BANCARIO', 'COMERCIAL', 'OTRO'];
const CATEGORY_COLORS = {
  FISCAL: 'text-amber-400 border-amber-400/40',
  LEGAL: 'text-blue-400 border-blue-400/40',
  BANCARIO: 'text-green-400 border-green-400/40',
  COMERCIAL: 'text-purple-400 border-purple-400/40',
  OTRO: 'text-white/60 border-white/20',
};

const today = new Date().toISOString().split('T')[0];
const isExpired = (d) => d && d < today;
const isExpiringSoon = (d) => {
  if (!d) return false;
  const diff = (new Date(d) - new Date()) / (1000 * 60 * 60 * 24);
  return diff >= 0 && diff <= 30;
};

export default function CTResourceIds({ resources, onCreateResource, onDeleteResource, activeEntity, onClose }) {
  const [filterCat, setFilterCat] = useState('ALL');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ label: '', value: '', category: 'FISCAL', expires_at: '', notes: '' });

  const filtered = filterCat === 'ALL' ? resources : resources.filter(r => r.category === filterCat);

  const handleCreate = async () => {
    if (!form.label.trim() || !form.value.trim()) { alert('Etiqueta y valor son obligatorios.'); return; }
    await onCreateResource({ ...form, expires_at: form.expires_at || null });
    setForm({ label: '', value: '', category: 'FISCAL', expires_at: '', notes: '' });
    setShowForm(false);
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-[100]">
      <div className="bg-black border-4 border-amber-400 w-full max-w-2xl shadow-[8px_8px_0px_#fbbf24] font-mono flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b-2 border-amber-400 flex-shrink-0">
          <div>
            <p className="text-amber-400/60 text-[10px] uppercase font-bold">
              {activeEntity?.name || 'Entidad'}
            </p>
            <h3 className="text-amber-400 font-black uppercase">🪪 INVENTARIO DE IDENTIFICADORES</h3>
          </div>
          <button onClick={onClose} className="text-amber-400 hover:text-white font-black text-xl">✕</button>
        </div>

        {/* Filter + Add */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-amber-400/30 flex-shrink-0 flex-wrap gap-2">
          <div className="flex gap-1 flex-wrap">
            {['ALL', ...CATEGORIES].map(c => (
              <button key={c}
                onClick={() => setFilterCat(c)}
                className={`px-2 py-1 text-[9px] font-black uppercase transition-colors ${
                  filterCat === c ? 'bg-amber-400 text-black' : 'border border-amber-400/30 text-amber-400/60 hover:border-amber-400'
                }`}>
                {c === 'ALL' ? 'TODOS' : c}
              </button>
            ))}
          </div>
          <button onClick={() => setShowForm(p => !p)}
            className="bg-amber-400 text-black text-[9px] font-black px-3 py-1.5 uppercase hover:bg-amber-300">
            + AGREGAR ID
          </button>
        </div>

        {/* Add Form */}
        {showForm && (
          <div className="px-5 py-4 border-b border-amber-400/30 flex-shrink-0 bg-amber-400/5">
            <p className="text-amber-400 text-[10px] font-black uppercase mb-3">+ NUEVO IDENTIFICADOR</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">ETIQUETA *</label>
                <input value={form.label}
                  onChange={e => setForm(p => ({ ...p, label: e.target.value }))}
                  placeholder="Ej: NIT, RUT, Contrato..."
                  className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-sm font-mono outline-none focus:border-amber-400" />
              </div>
              <div>
                <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">VALOR *</label>
                <input value={form.value}
                  onChange={e => setForm(p => ({ ...p, value: e.target.value }))}
                  placeholder="Ej: 901.234.567-1"
                  className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-sm font-mono outline-none focus:border-amber-400" />
              </div>
              <div>
                <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">CATEGORÍA</label>
                <select value={form.category}
                  onChange={e => setForm(p => ({ ...p, category: e.target.value }))}
                  className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-xs font-mono outline-none">
                  {CATEGORIES.map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">VENCE (opcional)</label>
                <input type="date" value={form.expires_at}
                  onChange={e => setForm(p => ({ ...p, expires_at: e.target.value }))}
                  className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-xs font-mono outline-none" />
              </div>
              <div className="col-span-2">
                <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">NOTAS</label>
                <input value={form.notes}
                  onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
                  placeholder="Observaciones adicionales..."
                  className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-sm font-mono outline-none focus:border-amber-400" />
              </div>
            </div>
            <div className="flex gap-2 mt-3">
              <button onClick={() => setShowForm(false)}
                className="flex-1 border-2 border-amber-400/40 text-amber-400/60 py-2 text-xs font-black uppercase hover:border-amber-400">
                CANCELAR
              </button>
              <button onClick={handleCreate}
                className="flex-1 bg-amber-400 text-black py-2 text-xs font-black uppercase hover:bg-amber-300">
                ✓ GUARDAR ID
              </button>
            </div>
          </div>
        )}

        {/* Table */}
        <div className="flex-1 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="text-center py-10">
              <p className="text-4xl text-amber-400/30 mb-3">🪪</p>
              <p className="text-amber-400/60 text-xs font-bold uppercase">Sin IDs registrados</p>
              <p className="text-white/20 text-[10px] mt-1">Agrega NIT, RUT, contratos y licencias</p>
            </div>
          ) : (
            <table className="w-full text-left">
              <thead className="bg-black sticky top-0">
                <tr className="border-b-2 border-amber-400/30">
                  <th className="px-4 py-2 text-[9px] text-amber-400/60 uppercase font-bold">CATEGORÍA</th>
                  <th className="px-4 py-2 text-[9px] text-amber-400/60 uppercase font-bold">ETIQUETA</th>
                  <th className="px-4 py-2 text-[9px] text-amber-400/60 uppercase font-bold">VALOR</th>
                  <th className="px-4 py-2 text-[9px] text-amber-400/60 uppercase font-bold">VENCIMIENTO</th>
                  <th className="px-4 py-2 text-[9px] text-amber-400/60 uppercase font-bold">ACCIÓN</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(r => {
                  const catStyle = CATEGORY_COLORS[r.category] || CATEGORY_COLORS.OTRO;
                  const expired = isExpired(r.expires_at);
                  const expiringSoon = isExpiringSoon(r.expires_at);
                  return (
                    <tr key={r.id} className={`border-b border-amber-400/10 hover:bg-amber-400/5 transition-colors ${expired ? 'opacity-50' : ''}`}>
                      <td className="px-4 py-2">
                        <span className={`text-[9px] font-black uppercase border px-1.5 py-0.5 ${catStyle}`}>
                          {r.category}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-white text-xs font-black uppercase">{r.label}</td>
                      <td className="px-4 py-2 text-amber-400 text-xs font-mono">{r.value}</td>
                      <td className="px-4 py-2">
                        {r.expires_at ? (
                          <span className={`text-[10px] font-bold ${
                            expired ? 'text-red-400' : expiringSoon ? 'text-amber-400' : 'text-white/40'
                          }`}>
                            {expired ? '⚠ VENCIDO' : expiringSoon ? '⏰ ' : ''}
                            {r.expires_at}
                          </span>
                        ) : (
                          <span className="text-white/20 text-[10px]">—</span>
                        )}
                      </td>
                      <td className="px-4 py-2">
                        <button
                          onClick={() => onDeleteResource(r.id)}
                          className="text-red-400/60 hover:text-red-400 text-[10px] font-bold uppercase transition-colors">
                          BORRAR
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <div className="border-t-2 border-amber-400/20 px-5 py-2 flex-shrink-0">
          <p className="text-amber-400/30 text-[9px] font-mono uppercase">
            TOTAL: {resources.length} REGISTROS // ENTITY: {activeEntity?.name || 'N/A'}
          </p>
        </div>
      </div>
    </div>
  );
}
