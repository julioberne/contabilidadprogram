/* ============================================================
   UploadModal.jsx — Extracted from DocumentsTab.jsx
   Upload modal with category picker and folder destination
   ============================================================ */
import { FILE_ICONS, fmtSize } from './constants';
import { C, M } from './styles';

export default function UploadModal({
  pendingFiles, uploading, uploadPct, uploadError,
  uploadCat, setUploadCat,
  uploadFolder, setUploadFolder,
  allFolders, categories,
  onUpload, onClose,
}) {
  return (
    <div style={M.overlay}>
      <div style={M.box}>
        <div style={M.hdr}>
          <span style={M.htitle}>↑ SUBIR {pendingFiles.length} ARCHIVO{pendingFiles.length!==1?'S':''}</span>
          {!uploading && <button style={M.xbtn} onClick={onClose}>✕</button>}
        </div>
        <div style={{ padding:'0 0 4px', maxHeight:'120px', overflowY:'auto' }}>
          {pendingFiles.map((f,i) => (
            <div key={i} style={M.fileRow}>
              <span style={{ fontSize:'16px' }}>{FILE_ICONS[f.type]||'📄'}</span>
              <span style={M.fname}>{f.name}</span>
              <span style={M.fsize}>{fmtSize(f.size)}</span>
            </div>
          ))}
        </div>

        {/* Categoría — prominente */}
        <div style={M.field}>
          <label style={M.flabel}>◈ CATEGORÍA DEL DOCUMENTO</label>
          <div style={M.catGrid}>
            {categories.map(c => (
              <button key={c.id}
                style={{ ...M.catPill, ...(uploadCat===c.id ? { background:`${c.color}33`, borderColor:c.color, color:c.color } : {}) }}
                onClick={() => setUploadCat(c.id)}>
                <span style={{ width:'6px', height:'6px', background:c.color, display:'inline-block', flexShrink:0 }} />
                {c.label}
              </button>
            ))}
          </div>
        </div>

        {/* Carpeta destino */}
        <div style={M.field}>
          <label style={M.flabel}>◉ CARPETA DESTINO</label>
          <select style={M.sel} value={uploadFolder||''} onChange={e => setUploadFolder(e.target.value||null)}>
            <option value="">◈ Raíz (sin carpeta)</option>
            {allFolders.map(f => <option key={f.id} value={f.id}>{f.parent_id ? '  └─ ' : '▣ '}{f.name}</option>)}
          </select>
        </div>

        {uploadError && <div style={M.err}>{uploadError}</div>}
        {uploading && (
          <div style={{ margin:'0 16px 12px', height:'3px', background:'#1a1a1a', position:'relative' }}>
            <div style={{ height:'100%', background:C.accent, width:`${uploadPct}%`, transition:'width .3s' }} />
          </div>
        )}
        <div style={M.foot}>
          {!uploading && <button style={M.btnCancel} onClick={onClose}>Cancelar</button>}
          <button style={M.btnOk} onClick={onUpload} disabled={uploading}>
            {uploading ? `${uploadPct}% subiendo...` : `↑ CONFIRMAR SUBIDA`}
          </button>
        </div>
      </div>
    </div>
  );
}
