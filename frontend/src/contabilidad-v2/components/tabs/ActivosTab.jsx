// ActivosTab.jsx — Extracted from ContextPanel.jsx
import React from 'react';
import InventoryPanel from '../InventoryPanel';
import NumInput from '../../../shared/NumInput';

export default function ActivosTab({
  assetForm,
  panelAssets,
  editingId, setEditingId,
  editData, setEditData,
  deleteItem, fetchAssets, createItem, updateItem,
  activePortfolio,
  activeCompany,
  SectionLabel,
}) {
  // ➕ Recurso directo, vinculado a la EMPRESA activa (pedido 2026-09-06)
  const [nuevo, setNuevo] = React.useState({ name: '', purchase_value: '', custom_tag: '', is_passive_income_generator: false });
  const [guardando, setGuardando] = React.useState(false);
  const guardarRecurso = async () => {
    if (!nuevo.name.trim()) return;
    setGuardando(true);
    try {
      await createItem('assets', {
        name: nuevo.name.trim(),
        purchase_value: parseFloat(nuevo.purchase_value) || 0,
        custom_tag: nuevo.custom_tag.trim() || null,
        is_passive_income_generator: nuevo.is_passive_income_generator,
        entity_id: activeCompany?.id || null,
        portfolio: activePortfolio || null,
      }, fetchAssets);
      setNuevo({ name: '', purchase_value: '', custom_tag: '', is_passive_income_generator: false });
    } catch (e) { alert(e.message || 'No se pudo guardar el recurso.'); }
    finally { setGuardando(false); }
  };
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
                <NumInput value={assetForm.value || ''} onChange={e => assetForm.setValue?.(e.target.value)} placeholder="$" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
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
      {/* ➕ Recurso directo en la empresa activa */}
      <div className="border border-black p-2 bg-white space-y-1.5">
        <SectionLabel text={`Nuevo recurso → ${activeCompany?.name || activePortfolio || 'sin empresa activa'}`} />
        <input type="text" value={nuevo.name} onChange={e => setNuevo(n => ({ ...n, name: e.target.value }))}
          placeholder="Nombre del recurso (ej: Camioneta, Impresora 3D…)"
          className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
        <div className="grid grid-cols-2 gap-1">
          <NumInput value={nuevo.purchase_value} onChange={e => setNuevo(n => ({ ...n, purchase_value: e.target.value }))}
            placeholder="$ Valor" className="border border-black px-2 py-1 text-[10px] font-mono outline-none text-right" />
          <input type="text" value={nuevo.custom_tag} onChange={e => setNuevo(n => ({ ...n, custom_tag: e.target.value }))}
            placeholder="Etiqueta / Tag" className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1 cursor-pointer text-[10px] font-mono">
            <input type="checkbox" checked={nuevo.is_passive_income_generator}
              onChange={e => setNuevo(n => ({ ...n, is_passive_income_generator: e.target.checked }))} className="accent-black" />
            ♻ Genera ingreso pasivo
          </label>
          <span className="flex-1" />
          <button onClick={guardarRecurso} disabled={guardando || !nuevo.name.trim()}
            className="bg-black text-white border border-black px-3 py-1 text-[9px] font-bold uppercase hover:bg-brutalGreen hover:text-black disabled:opacity-40">
            {guardando ? 'Guardando…' : '💾 Guardar recurso'}
          </button>
        </div>
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
            editingId === a.id ? (
              <tr key={a.id} className="bg-yellow-50">
                <td className="p-1 border-r border-black">
                  <input value={editData.name || ''} onChange={e => setEditData(d => ({ ...d, name: e.target.value }))}
                    className="w-full border border-black px-1 text-[10px] font-mono outline-none" />
                </td>
                <td className="p-1 border-r border-black">
                  <NumInput value={editData.purchase_value ?? ''} onChange={e => setEditData(d => ({ ...d, purchase_value: e.target.value }))}
                    className="w-full border border-black px-1 text-[10px] font-mono outline-none text-right" />
                </td>
                <td className="p-1 border-r border-black">
                  <input value={editData.custom_tag || ''} onChange={e => setEditData(d => ({ ...d, custom_tag: e.target.value }))}
                    className="w-full border border-black px-1 text-[10px] font-mono outline-none" />
                </td>
                <td className="p-1 text-center whitespace-nowrap">
                  <button onClick={()=>updateItem('assets',a.id,{name:editData.name,purchase_value:parseFloat(editData.purchase_value)||0,custom_tag:editData.custom_tag},fetchAssets)}
                    className="text-[10px] hover:text-brutalGreen font-bold" title="Guardar">💾</button>
                  <button onClick={()=>setEditingId(null)} className="text-[10px] hover:text-red-600 font-bold ml-1" title="Cancelar">✕</button>
                </td>
              </tr>
            ) : (
            <tr key={a.id} className="hover:bg-brutalBg">
              <td className="p-1 border-r border-black">
                <div className="font-bold">{a.name}</div>
                <div className="text-[8px] text-gray-500"
                     title={a.entity_name ? 'Vinculado a esta empresa' : 'Legado: pertenece al portafolio, sin empresa asignada'}>
                  {a.entity_name ? `🏢 ${a.entity_name}` : `📁 ${a.portfolio_name || 'sin vínculo'}`}
                  {a.is_passive_income_generator ? ' · ♻' : ''}
                </div>
              </td>
              <td className="p-1 border-r border-black text-right">${Number(a.purchase_value||0).toLocaleString('es-CO')}</td>
              <td className="p-1 border-r border-black">{a.custom_tag||'—'}</td>
              <td className="p-1 text-center whitespace-nowrap">
                <button onClick={()=>{setEditingId(a.id);setEditData({name:a.name,purchase_value:a.purchase_value,custom_tag:a.custom_tag});}} className="text-[9px] text-gray-400 hover:text-black font-bold" title="Editar">✎</button>
                <button onClick={()=>deleteItem('assets',a.id,fetchAssets)} className="text-[9px] text-gray-300 hover:text-red-500 font-bold ml-1" title="Eliminar">🗑</button>
              </td>
            </tr>
            )
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
