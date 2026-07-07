// ImpuestosTab.jsx — Extracted from ContextPanel.jsx
import React from 'react';

export default function ImpuestosTab({
  taxes,
  panelTaxes,
  editingId, setEditingId,
  editData, setEditData,
  deleteItem, fetchTaxes,
  newTaxName, setNewTaxName,
  newTaxRate, setNewTaxRate,
  newTaxType, setNewTaxType,
  API_BASE,
  SectionLabel,
}) {
  return (
    <>
      <div className="border border-black p-2 bg-brutalBg space-y-1.5">
        <SectionLabel text="Vincular impuesto a transacción" />
        <label className="flex items-center gap-1 cursor-pointer mb-1">
          <input type="checkbox" checked={taxes.enabled || false} onChange={e => taxes.setEnabled?.(e.target.checked)} className="accent-black" />
          <span className="text-[10px] font-bold uppercase font-mono">Aplicar Impuesto</span>
        </label>
        {taxes.enabled && (
          <div className="grid grid-cols-2 gap-1">
            <select value={taxes.type || 'IVA_19'} onChange={e => taxes.setType?.(e.target.value)} className="border border-black px-2 py-1 text-[10px] font-mono">
              <option value="IVA_19">IVA 19%</option>
              <option value="IVA_5">IVA 5%</option>
              <option value="RETEFUENTE">ReteFuente</option>
              <option value="RETEICA">ReteICA</option>
              <option value="GMF">GMF (4x1000)</option>
              <option value="CUSTOM">Custom</option>
            </select>
            {taxes.type === 'CUSTOM' && (
              <input type="number" step="0.01" value={taxes.customRate || ''} onChange={e => taxes.setCustomRate?.(e.target.value)} placeholder="% Tasa" className="border border-black px-2 py-1 text-[10px] font-mono outline-none text-right" />
            )}
          </div>
        )}
      </div>
      {/* --- BD: custom_taxes_templates --- */}
      <SectionLabel text={`custom_taxes_templates · ${panelTaxes.length} registros`} />
      <table className="w-full text-[10px] font-mono border border-black">
        <thead className="bg-black text-white uppercase"><tr>
          <th className="p-1 border-r border-black text-left">Nombre</th>
          <th className="p-1 border-r border-black text-right">Tasa</th>
          <th className="p-1 border-r border-black">Tipo</th>
          <th className="p-1">Acc.</th>
        </tr></thead>
        <tbody className="divide-y divide-gray-200">
          {panelTaxes.map(t => (
            <tr key={t.id} className="hover:bg-brutalBg">
              <td className="p-1 border-r border-black font-bold">{t.name}</td>
              <td className="p-1 border-r border-black text-right">{Number(t.rate).toFixed(2)}%</td>
              <td className="p-1 border-r border-black text-center"><span className={`px-1 py-0.5 text-[7px] font-bold border ${t.type==='ADDITIVE'?'bg-green-50 border-green-400':'bg-red-50 border-red-400'}`}>{t.type==='ADDITIVE'?'+ADD':'−DED'}</span></td>
              <td className="p-1 text-center whitespace-nowrap">
                <button onClick={()=>{setEditingId(t.id);setEditData({name:t.name,rate:t.rate,type:t.type});}} className="text-[9px] text-gray-400 hover:text-black font-bold">✎</button>
                <button onClick={()=>deleteItem('custom-taxes',t.id,fetchTaxes)} className="text-[9px] text-gray-300 hover:text-red-500 font-bold ml-1">🗑</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {panelTaxes.length===0 && <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-2">Sin tasas</p>}
      <div className="grid grid-cols-4 gap-1 border-t border-black pt-1.5">
        <input type="text" value={newTaxName} onChange={e=>setNewTaxName(e.target.value)} placeholder="Nombre" className="bg-brutalBg border border-black px-1 py-1 text-[10px] font-mono outline-none" />
        <input type="number" step="0.01" value={newTaxRate} onChange={e=>setNewTaxRate(e.target.value)} placeholder="%" className="bg-brutalBg border border-black px-1 py-1 text-[10px] font-mono outline-none text-right" />
        <select value={newTaxType} onChange={e=>setNewTaxType(e.target.value)} className="bg-brutalBg border border-black px-1 py-1 text-[10px] font-mono"><option value="ADDITIVE">ADITIVO</option><option value="DEDUCTIVE">DED</option></select>
        <button onClick={()=>{if(newTaxName.trim()&&newTaxRate){fetch(`${API_BASE}/custom-taxes`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:newTaxName.trim(),rate:parseFloat(newTaxRate),type:newTaxType})}).then(()=>{setNewTaxName('');setNewTaxRate('');fetchTaxes()});}}} className="bg-black text-white border border-black px-1 py-1 text-[8px] font-bold hover:bg-brutalGreen hover:text-black">+</button>
      </div>
    </>
  );
}
