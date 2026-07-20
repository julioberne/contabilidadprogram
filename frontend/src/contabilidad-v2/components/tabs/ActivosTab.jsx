// ActivosTab.jsx — Extracted from ContextPanel.jsx
import React from 'react';
import InventoryPanel from '../InventoryPanel';

export default function ActivosTab({
  assetForm,
  panelAssets,
  editingId, setEditingId,
  editData, setEditData,
  deleteItem, fetchAssets,
  activePortfolio,
  activeCompany,
  SectionLabel,
}) {
  return (
    <>
      <div className="border border-black p-2 bg-brutalBg space-y-1.5">
        <SectionLabel text="Vincular recurso/activo a transacción" />
        <div className="flex items-center gap-2 mb-1">
          <label className="flex items-center gap-1 cursor-pointer">
            <input type="checkbox" checked={assetForm.enabled || false} onChange={e => assetForm.setEnabled?.(e.target.checked)} className="accent-black" />
            <span className="text-[10px] font-bold uppercase font-mono">Establecer Recurso</span>
          </label>
        </div>
        {assetForm.enabled && (
          <div className="space-y-1.5">
            <input type="text" value={assetForm.name || ''} onChange={e => assetForm.setName?.(e.target.value)} placeholder="Nombre del recurso" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
            <div className="grid grid-cols-3 gap-1">
              <div>
                <label className="text-[8px] font-bold uppercase block mb-0.5">Stock</label>
                <input type="number" min="1" defaultValue="1" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
              </div>
              <div>
                <label className="text-[8px] font-bold uppercase block mb-0.5">Valor</label>
                <input type="number" value={assetForm.value || ''} onChange={e => assetForm.setValue?.(e.target.value)} placeholder="$" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
              </div>
              <div>
                <label className="text-[8px] font-bold uppercase block mb-0.5">Tag</label>
                <input type="text" value={assetForm.tag || ''} onChange={e => assetForm.setTag?.(e.target.value)} placeholder="Etiqueta" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
              </div>
            </div>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input type="checkbox" checked={assetForm.passive || false} onChange={e => assetForm.setPassive?.(e.target.checked)} className="accent-black" />
              <span className="text-[10px] font-mono">♻ Genera ingreso pasivo</span>
            </label>
          </div>
        )}
      </div>
      {/* --- BD: assets --- */}
      <SectionLabel text={`assets · ${panelAssets.length} registros`} />
      <table className="w-full text-[10px] font-mono border border-black">
        <thead className="bg-black text-white uppercase"><tr>
          <th className="p-1 border-r border-black text-left">Nombre</th>
          <th className="p-1 border-r border-black text-right">Valor</th>
          <th className="p-1 border-r border-black">Tag</th>
          <th className="p-1">Acc.</th>
        </tr></thead>
        <tbody className="divide-y divide-gray-200">
          {panelAssets.map(a => (
            <tr key={a.id} className="hover:bg-brutalBg">
              <td className="p-1 border-r border-black font-bold">{a.name}</td>
              <td className="p-1 border-r border-black text-right">${Number(a.purchase_value||0).toLocaleString()}</td>
              <td className="p-1 border-r border-black">{a.custom_tag||'—'}</td>
              <td className="p-1 text-center whitespace-nowrap">
                <button onClick={()=>{setEditingId(a.id);setEditData({name:a.name,purchase_value:a.purchase_value,custom_tag:a.custom_tag});}} className="text-[9px] text-gray-400 hover:text-black font-bold">✎</button>
                <button onClick={()=>deleteItem('assets',a.id,fetchAssets)} className="text-[9px] text-gray-300 hover:text-red-500 font-bold ml-1">🗑</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {panelAssets.length===0 && <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-2">Sin recursos</p>}

      {/* ── Inventario Completo (Fase 4) ── */}
      <div className="border-t-2 border-black mt-2 pt-2">
        <InventoryPanel
          activePortfolio={activePortfolio}
          activeCompany={activeCompany}
          onDataChanged={() => fetchAssets()}
        />
      </div>
    </>
  );
}
