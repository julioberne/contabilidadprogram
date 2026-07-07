// TercerosTab.jsx — Extracted from ContextPanel.jsx
import React from 'react';

export default function TercerosTab({
  search, setSearch,
  tercero,
  allThirdParties,
  editingId, setEditingId,
  editData, setEditData,
  updateItem, deleteItem, refreshTP,
  SectionLabel,
}) {
  return (
    <>
      {/* --- Form: Identificación de Tercero --- */}
      <div className="border border-black p-2 bg-brutalBg space-y-1.5">
        <SectionLabel text="Vincular tercero a transacción" />
        <input type="text" value={search} onChange={e => { setSearch(e.target.value); }}
          placeholder="🔍 Buscar tercero existente..."
          className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen" />
        {search.length >= 2 && (
          <div className="border border-black bg-white max-h-24 overflow-y-auto">
            {allThirdParties.filter(tp => (tp.name||'').toLowerCase().includes(search.toLowerCase()) || (tp.identification_number||'').includes(search)).slice(0,5).map(tp => (
              <div key={tp.id} onClick={() => {
                if (tercero.setName) tercero.setName(tp.name || '');
                if (tercero.setIdType) tercero.setIdType(tp.identification_type || 'NIT');
                if (tercero.setIdNumber) tercero.setIdNumber(tp.identification_number || '');
                if (tercero.setEmail) tercero.setEmail(tp.email || '');
                if (tercero.setPhone) tercero.setPhone(tp.phone || '');
                if (tercero.setAddress) tercero.setAddress(tp.address || '');
                setSearch('');
              }} className="px-2 py-1 text-[10px] font-mono hover:bg-brutalGreen cursor-pointer border-b border-gray-100">
                <span className="font-bold">{tp.name}</span> <span className="text-gray-400">· {tp.identification_type} {tp.identification_number}</span>
              </div>
            ))}
          </div>
        )}
        <div className="text-[8px] text-gray-300 uppercase font-mono border-t border-dashed border-gray-200 pt-1">O crear nuevo:</div>
        <div className="grid grid-cols-2 gap-1">
          <input type="text" value={tercero.name || ''} onChange={e => tercero.setName?.(e.target.value)} placeholder="Nombre / Razón Social" className="col-span-2 border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen" />
          <select value={tercero.idType || 'NIT'} onChange={e => tercero.setIdType?.(e.target.value)} className="border border-black px-1 py-1 text-[10px] font-mono">
            <option value="NIT">NIT</option><option value="CC">CC</option><option value="CE">CE</option><option value="PP">Pasaporte</option>
          </select>
          <input type="text" value={tercero.idNumber || ''} onChange={e => tercero.setIdNumber?.(e.target.value)} placeholder="Número" className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
          <input type="email" value={tercero.email || ''} onChange={e => tercero.setEmail?.(e.target.value)} placeholder="Email" className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
          <input type="tel" value={tercero.phone || ''} onChange={e => tercero.setPhone?.(e.target.value)} placeholder="Teléfono" className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
          <input type="text" value={tercero.address || ''} onChange={e => tercero.setAddress?.(e.target.value)} placeholder="Dirección" className="col-span-2 border border-black px-2 py-1 text-[10px] font-mono outline-none" />
        </div>
      </div>
      {/* --- BD: third_parties --- */}
      <SectionLabel text={`third_parties · ${allThirdParties.length} registros`} />
      <table className="w-full text-[10px] font-mono border border-black">
        <thead className="bg-black text-white uppercase"><tr>
          <th className="p-1 border-r border-black text-left">Nombre</th>
          <th className="p-1 border-r border-black">Tipo</th>
          <th className="p-1 border-r border-black">NIT/CC</th>
          <th className="p-1 border-r border-black">Email</th>
          <th className="p-1">Acc.</th>
        </tr></thead>
        <tbody className="divide-y divide-gray-200">
          {allThirdParties.map(tp => (
            <tr key={tp.id} className="hover:bg-brutalBg">
              {editingId === tp.id ? (<>
                <td className="p-0.5 border-r border-black"><input type="text" value={editData.name||''} onChange={e=>setEditData({...editData,name:e.target.value})} className="w-full border border-black px-1 py-0.5 text-[10px] font-mono outline-none" /></td>
                <td className="p-0.5 border-r border-black"><select value={editData.identification_type||'NIT'} onChange={e=>setEditData({...editData,identification_type:e.target.value})} className="border border-black px-0.5 py-0.5 text-[10px] font-mono"><option>NIT</option><option>CC</option></select></td>
                <td className="p-0.5 border-r border-black"><input type="text" value={editData.identification_number||''} onChange={e=>setEditData({...editData,identification_number:e.target.value})} className="w-full border border-black px-1 py-0.5 text-[10px] font-mono outline-none" /></td>
                <td className="p-0.5 border-r border-black"><input type="text" value={editData.email||''} onChange={e=>setEditData({...editData,email:e.target.value})} className="w-full border border-black px-1 py-0.5 text-[10px] font-mono outline-none" /></td>
                <td className="p-0.5 text-center">
                  <button onClick={()=>updateItem('third-parties',tp.id,editData,refreshTP)} className="bg-brutalGreen border border-black px-1 py-0.5 text-[8px] font-bold mr-0.5">✓</button>
                  <button onClick={()=>setEditingId(null)} className="bg-gray-200 border border-black px-1 py-0.5 text-[8px] font-bold">✕</button>
                </td>
              </>) : (<>
                <td className="p-1 border-r border-black font-bold truncate max-w-[100px]">{tp.name}</td>
                <td className="p-1 border-r border-black text-center text-[8px]">{tp.identification_type}</td>
                <td className="p-1 border-r border-black">{tp.identification_number}</td>
                <td className="p-1 border-r border-black text-gray-400 truncate max-w-[80px]">{tp.email||'—'}</td>
                <td className="p-1 text-center whitespace-nowrap">
                  <button onClick={()=>{setEditingId(tp.id);setEditData({...tp});}} className="text-[9px] text-gray-400 hover:text-black font-bold">✎</button>
                  <button onClick={()=>deleteItem('third-parties',tp.id,refreshTP)} className="text-[9px] text-gray-300 hover:text-red-500 font-bold ml-1">🗑</button>
                </td>
              </>)}
            </tr>
          ))}
        </tbody>
      </table>
      {allThirdParties.length===0 && <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-2">Sin terceros</p>}
    </>
  );
}
