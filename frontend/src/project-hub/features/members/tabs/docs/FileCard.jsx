/* ============================================================
   FileCard.jsx — Extracted from DocumentsTab.jsx
   FileCard (grid view) + FileRow (list view) components
   ============================================================ */
import { useState } from 'react';
import { FILE_ICONS, FILE_EXT, catLabel, catColor, fmtSize, fmtDate, downloadFile } from './constants';
import { FC, FR } from './styles';

// ── FileCard (grid) ────────────────────────────────────────────────────────────
export function FileCard({ doc, canEdit, onPreview, onDelete, catLabelFn, catColorFn }) {
  const [h, setH] = useState(false);
  const isImg     = doc.mime_type?.startsWith('image/');
  const isVoucher = doc.mime_type === 'application/octet-stream' || doc.mime_type === 'text/html';
  const labelFn = catLabelFn || catLabel;
  const colorFn = catColorFn || catColor;
  const cc = colorFn(doc.category);
  return (
    <div style={{...FC.file,...(h?FC.fileH:{})}} onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)}>
      <div style={FC.thumb} onClick={onPreview}>
        {isImg ? (
          <img src={doc.file_url} alt={doc.file_name}
            style={{width:'100%',height:'100%',objectFit:'cover',cursor:'pointer'}}
            onError={e => { e.target.style.display='none'; e.target.nextSibling.style.display='flex'; }}
          />
        ) : null}
        <div style={{...FC.ico,...(isImg?{display:'none'}:{}),
          ...(isVoucher ? { flexDirection:'column', gap:'4px' } : {})
        }}>
          {isVoucher ? (
            <>
              <span style={{ fontSize:'26px', lineHeight:1 }}>🧾</span>
              <span style={{ fontSize:'8px', color:'#84CC16', letterSpacing:'1px', fontFamily:'"IBM Plex Mono",monospace' }}>COMPROBANTE</span>
            </>
          ) : FILE_ICONS[doc.mime_type] || '📄'}
        </div>
        <div style={FC.extTag}>{FILE_EXT[doc.mime_type]||'FILE'}</div>
      </div>
      <div style={FC.info}>
        <div style={FC.fname} title={doc.file_name}>{doc.file_name}</div>
        <div style={{...FC.ctag,background:`${cc}22`,color:cc}}>{labelFn(doc.category)}</div>
        <div style={FC.fmeta}>{fmtSize(doc.file_size)} · {fmtDate(doc.created_at)}</div>
      </div>
      {h && (
        <div style={FC.hover}>
          <button style={FC.hBtn} onClick={onPreview} title="Ver">👁</button>
          <button style={FC.hBtn} onClick={() => downloadFile(doc.file_url, doc.file_name)} title="Descargar">↓</button>
          {canEdit && <button style={{...FC.hBtn,color:'#ef4444'}} onClick={onDelete} title="Eliminar">✕</button>}
        </div>
      )}
    </div>
  );
}

// ── FileRow (list) ─────────────────────────────────────────────────────────────
export function FileRow({ doc, canEdit, onPreview, onDelete, catLabelFn, catColorFn }) {
  const [h, setH] = useState(false);
  const labelFn = catLabelFn || catLabel;
  const colorFn = catColorFn || catColor;
  const cc = colorFn(doc.category);
  const isVoucher = doc.mime_type === 'application/octet-stream' || doc.mime_type === 'text/html';
  return (
    <div style={{...FR.row,...(h?FR.rowH:{})}} onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)}>
      <span style={{fontSize:'18px',flexShrink:0,width:'28px'}}>{isVoucher ? '🧾' : FILE_ICONS[doc.mime_type]||'📄'}</span>
      <span style={FR.ext}>{FILE_EXT[doc.mime_type]||'FILE'}</span>
      <span style={FR.name}>{doc.file_name}</span>
      <span style={{...FR.cat,background:`${cc}22`,color:cc}}>{labelFn(doc.category)}</span>
      <span style={FR.size}>{fmtSize(doc.file_size)}</span>
      <span style={FR.date}>{fmtDate(doc.created_at)}</span>
      <div style={FR.acts}>
        <button style={FR.act} onClick={onPreview} title="Ver">👁</button>
        <button style={FR.act} onClick={() => downloadFile(doc.file_url, doc.file_name)} title="Descargar">↓</button>
        {canEdit && <button style={{...FR.act,color:'#ef4444'}} onClick={onDelete} title="Eliminar">✕</button>}
      </div>
    </div>
  );
}
