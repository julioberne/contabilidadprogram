// EtiquetasTab.jsx — Extracted from ContextPanel.jsx
import React from 'react';

export default function EtiquetasTab({
  tagState,
  panelTags,
  editingId, setEditingId,
  editData, setEditData,
  updateItem, deleteItem, fetchTags,
  newTag, setNewTag,
  API_BASE,
  SectionLabel,
}) {
  return (
    <>
      <div className="border border-black p-2 bg-brutalBg space-y-1.5">
        <SectionLabel text="Seleccionar etiquetas para transacción" />
        <input type="text" value={tagState.search || ''} onChange={e => tagState.setSearch?.(e.target.value)}
          placeholder="🔍 Filtrar etiquetas..." className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen" />
        <div className="max-h-24 overflow-y-auto space-y-0.5">
          {panelTags.filter(t => !tagState.search || t.name.toLowerCase().includes((tagState.search||'').toLowerCase())).map(tag => {
            const sel = (tagState.selected || []).includes(tag.name);
            return (
              <div key={tag.id} onClick={() => {
                if (!tagState.setSelected) return;
                tagState.setSelected(prev => sel ? prev.filter(t => t !== tag.name) : [...prev, tag.name]);
              }} className={`flex items-center gap-1.5 px-2 py-1 cursor-pointer border ${sel ? 'border-black bg-brutalGreen' : 'border-gray-200 hover:bg-brutalBg'}`}>
                <span className="text-[10px] font-mono">{sel ? '☑' : '☐'}</span>
                <span className="w-2.5 h-2.5 border border-black" style={{ backgroundColor: tag.color || '#000' }}></span>
                <span className="text-[10px] font-bold uppercase font-mono">{tag.name}</span>
              </div>
            );
          })}
        </div>
        {(tagState.selected||[]).length > 0 && (
          <div className="flex flex-wrap gap-1 border-t border-dashed border-gray-200 pt-1">
            {(tagState.selected||[]).map(t => (
              <span key={t} className="bg-black text-white px-1.5 py-0.5 text-[8px] font-bold uppercase inline-flex items-center gap-1">
                {t} <button onClick={() => tagState.setSelected?.(prev => prev.filter(x => x !== t))} className="text-gray-400 hover:text-red-300">×</button>
              </span>
            ))}
          </div>
        )}
      </div>
      {/* --- BD: tag_definitions --- */}
      <SectionLabel text={`tag_definitions · ${panelTags.length} registros`} />
      <div className="space-y-0.5">
        {panelTags.map(tag => (
          <div key={tag.id} className="flex items-center justify-between border border-gray-200 px-2 py-1 hover:bg-brutalBg group">
            {editingId === tag.id ? (
              <div className="flex items-center gap-1 flex-1">
                <input type="text" value={editData.name||''} onChange={e=>setEditData({...editData,name:e.target.value})} className="flex-1 border border-black px-1 py-0.5 text-[10px] font-mono outline-none" autoFocus />
                <input type="color" value={editData.color||'#000000'} onChange={e=>setEditData({...editData,color:e.target.value})} className="w-5 h-5 border border-black cursor-pointer" />
                <button onClick={()=>updateItem('tags',tag.id,editData,fetchTags)} className="bg-brutalGreen border border-black px-1 py-0.5 text-[8px] font-bold">✓</button>
                <button onClick={()=>setEditingId(null)} className="bg-gray-200 border border-black px-1 py-0.5 text-[8px] font-bold">✕</button>
              </div>
            ) : (<>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 border border-black" style={{backgroundColor:tag.color||'#000'}}></span>
                <span className="text-[10px] font-bold uppercase font-mono">{tag.name}</span>
              </div>
              <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={()=>{setEditingId(tag.id);setEditData({name:tag.name,color:tag.color});}} className="text-[9px] text-gray-400 hover:text-black font-bold">✎</button>
                <button onClick={()=>deleteItem('tags',tag.id,fetchTags)} className="text-[9px] text-gray-300 hover:text-red-500 font-bold">🗑</button>
              </div>
            </>)}
          </div>
        ))}
      </div>
      <div className="flex gap-1 border-t border-black pt-1.5">
        <input type="text" value={newTag} onChange={e=>setNewTag(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&newTag.trim()){fetch(`${API_BASE}/tags`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:newTag.trim()})}).then(()=>{setNewTag('');fetchTags()});}}} placeholder="+ Nueva etiqueta..." className="flex-grow bg-brutalBg border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen" />
        <button onClick={()=>{if(newTag.trim()){fetch(`${API_BASE}/tags`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:newTag.trim()})}).then(()=>{setNewTag('');fetchTags()});}}} className="bg-black text-white border border-black px-2 py-1 text-[8px] font-bold hover:bg-brutalGreen hover:text-black">+</button>
      </div>
    </>
  );
}
