/* ============================================================
   FolderCard.jsx — Extracted from DocumentsTab.jsx
   FolderCard + NewFolderCard components
   ============================================================ */
import { useState } from 'react';
import { FC } from './styles';

// ── FolderCard ─────────────────────────────────────────────────────────────────
export function FolderCard({ folder, docCount, canEdit, onOpen, onEdit, onDelete }) {
  const [h, setH] = useState(false);
  return (
    <div style={{ ...FC.card, ...(h?FC.cardH:{}) }} onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)}>
      <div style={FC.inner} onClick={onOpen}>
        <span style={{ fontSize:'26px', color: folder.color||'#64748b', lineHeight:1, flexShrink:0 }}>▣</span>
        <div style={{ flex:1, minWidth:0 }}>
          <div style={FC.name}>{folder.name}</div>
          <div style={FC.meta}>{docCount} archivo{docCount!==1?'s':''} · clic para entrar</div>
        </div>
      </div>
      {canEdit && h && (
        <div style={FC.acts}>
          <button style={FC.actBtn} title="Editar carpeta" onClick={e=>{e.stopPropagation();onEdit();}}>✎</button>
          <button style={{...FC.actBtn,color:'#ef4444'}} title="Eliminar carpeta" onClick={e=>{e.stopPropagation();onDelete();}}>✕</button>
        </div>
      )}
    </div>
  );
}

// ── NewFolderCard ──────────────────────────────────────────────────────────────
export function NewFolderCard({ value, onChange, onCreate, onCancel }) {
  return (
    <div style={{ ...FC.card, border:`1px dashed ${value.color}` }}>
      <div style={{ padding:'10px', display:'flex', flexDirection:'column', gap:'8px' }}>
        <input autoFocus style={FC.inp} placeholder="Nombre de la carpeta..."
          value={value.name} onChange={e=>onChange({...value,name:e.target.value})}
          onKeyDown={e=>{if(e.key==='Enter')onCreate();if(e.key==='Escape')onCancel();}} />
        <div style={{display:'flex',gap:'5px',flexWrap:'wrap'}}>
          {['#0EA5E9','#10B981','#F59E0B','#EF4444','#8B5CF6','#F97316','#64748b'].map(c=>(
            <button key={c} style={{width:'18px',height:'18px',background:c,border:value.color===c?'2px solid #fff':'2px solid transparent',cursor:'pointer'}}
              onClick={()=>onChange({...value,color:c})} />
          ))}
        </div>
        <div style={{display:'flex',gap:'6px'}}>
          <button style={FC.btnCreate} onClick={onCreate}>✓ Crear</button>
          <button style={{...FC.btnCreate,background:'transparent',border:'1px solid #333',color:'#94a3b8'}} onClick={onCancel}>✕</button>
        </div>
      </div>
    </div>
  );
}
