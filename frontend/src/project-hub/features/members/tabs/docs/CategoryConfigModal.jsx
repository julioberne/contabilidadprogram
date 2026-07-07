/* ============================================================
   CategoryConfigModal.jsx — Extracted from DocumentsTab.jsx
   Category config modal + CRUD functions
   ============================================================ */
import { useState } from 'react';
import { API, FOLDER_COLORS } from './constants';
import { C, FF, M } from './styles';

export default function CategoryConfigModal({
  categories, workspaceId,
  onClose, onReload,
}) {
  const [editingCat, setEditingCat] = useState(null); // {id, name, color, sort_order, isNew}

  // ── CRUD categorías ────────────────────────────────────────────────
  async function handleSaveCat() {
    if (!editingCat?.name?.trim()) return;
    if (editingCat.isNew) {
      await fetch(`${API}/categories/${workspaceId}`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ name: editingCat.name.trim(), color: editingCat.color, sort_order: editingCat.sort_order }),
      });
    } else {
      await fetch(`${API}/categories/${workspaceId}/${editingCat.id}`, {
        method:'PUT', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ name: editingCat.name.trim(), color: editingCat.color, sort_order: editingCat.sort_order }),
      });
    }
    setEditingCat(null);
    onReload();
  }

  async function handleDeleteCat(catId) {
    if (!confirm('¿Eliminar esta categoría?')) return;
    await fetch(`${API}/categories/${workspaceId}/${catId}`, { method:'DELETE' });
    onReload();
  }

  return (
    <div style={M.overlay}>
      <div style={{ ...M.box, maxWidth:'520px' }}>
        <div style={M.hdr}>
          <span style={M.htitle}>⚙️ CONFIGURAR CATEGORÍAS</span>
          <button style={M.xbtn} onClick={() => { onClose(); setEditingCat(null); }}>✕</button>
        </div>
        <div style={{ overflowY:'auto', maxHeight:'50vh' }}>
          {categories.map(cat => (
            <div key={cat.id} style={{ display:'flex', alignItems:'center', gap:'8px', padding:'8px 16px', borderBottom:'1px solid #111' }}>
              <span style={{ width:'10px', height:'10px', background:cat.color, flexShrink:0, display:'inline-block' }} />
              {editingCat?.id === cat.id ? (
                <>
                  <input style={{ ...M.inp, flex:1, padding:'4px 6px', fontSize:'11px' }}
                    value={editingCat.name}
                    onChange={e => setEditingCat(c => ({ ...c, name: e.target.value }))}
                    onKeyDown={e => e.key==='Enter' && handleSaveCat()} />
                  <div style={{ display:'flex', gap:'4px' }}>
                    {FOLDER_COLORS.map(col => (
                      <button key={col} onClick={() => setEditingCat(c => ({ ...c, color: col }))}
                        style={{ width:'16px', height:'16px', background:col, border: editingCat.color===col ? '2px solid #fff':'2px solid transparent', cursor:'pointer' }} />
                    ))}
                  </div>
                  <button style={{ ...M.btnOk, padding:'4px 10px', fontSize:'10px' }} onClick={handleSaveCat}>✓</button>
                  <button style={{ ...M.btnCancel, padding:'4px 8px', fontSize:'10px' }} onClick={() => setEditingCat(null)}>✕</button>
                </>
              ) : (
                <>
                  <span style={{ flex:1, color:'#e2e8f0', fontSize:'12px', fontFamily:FF }}>{cat.label}</span>
                  {!cat.is_default && (
                    <span style={{ color:'#334155', fontSize:'9px', marginRight:'4px' }}>PERSONALIZADA</span>
                  )}
                  <button style={{ background:'transparent', border:'none', color:'#94a3b8', cursor:'pointer', fontSize:'12px', padding:'2px 6px' }}
                    onClick={() => setEditingCat({ id: cat.id, name: cat.label, color: cat.color, sort_order: cat.sort_order || 99, isNew: false })}>✎</button>
                  {!cat.is_default && (
                    <button style={{ background:'transparent', border:'none', color:'#ef4444', cursor:'pointer', fontSize:'12px', padding:'2px 6px' }}
                      onClick={() => handleDeleteCat(cat.id)}>✕</button>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
        <div style={{ ...M.field, borderTop:'1px solid #1a1a1a' }}>
          <div style={{ color:C.dim, fontSize:'9px', letterSpacing:'2px', marginBottom:'6px' }}>+ NUEVA CATEGORÍA</div>
          <div style={{ display:'flex', gap:'6px' }}>
            <input style={{ ...M.inp, flex:1, padding:'6px 8px', fontSize:'11px' }} placeholder="Nombre..."
              value={editingCat?.isNew ? editingCat.name : ''}
              onFocus={() => !editingCat?.isNew && setEditingCat({ id: null, name:'', color:'#0EA5E9', sort_order:99, isNew:true })}
              onChange={e => setEditingCat(c => ({ ...c, name: e.target.value }))}
              onKeyDown={e => e.key==='Enter' && editingCat?.isNew && handleSaveCat()} />
            {editingCat?.isNew && (
              <>
                <div style={{ display:'flex', gap:'3px', alignItems:'center' }}>
                  {FOLDER_COLORS.map(col => (
                    <button key={col} onClick={() => setEditingCat(c => ({ ...c, color: col }))}
                      style={{ width:'16px', height:'16px', background:col, border: editingCat.color===col ? '2px solid #fff':'2px solid transparent', cursor:'pointer' }} />
                  ))}
                </div>
                <button style={{ ...M.btnOk, padding:'6px 12px', fontSize:'10px' }} onClick={handleSaveCat}>+ CREAR</button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
