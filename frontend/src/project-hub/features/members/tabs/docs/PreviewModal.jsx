/* ============================================================
   PreviewModal.jsx — Extracted from DocumentsTab.jsx
   Preview modal for documents (images, PDFs, HTML, fallback)
   ============================================================ */
import { fmtSize, downloadFile } from './constants';
import { FF, M } from './styles';
import HtmlPreview from './HtmlPreview';

export default function PreviewModal({ preview, catLabel, catColor, onClose }) {
  return (
    <div style={M.overlay} onClick={onClose}>
      <div style={{ ...M.box, maxWidth:'960px', maxHeight:'92vh', overflow:'hidden' }} onClick={e => e.stopPropagation()}>
        <div style={M.hdr}>
          <div style={{ display:'flex', flexDirection:'column', gap:'2px', overflow:'hidden', flex:1 }}>
            <span style={M.htitle}>{preview.file_name}</span>
            <span style={{ color: catColor(preview.category), fontSize:'10px', fontFamily:FF }}>◈ {catLabel(preview.category)} · {fmtSize(preview.file_size)}</span>
          </div>
          <div style={{ display:'flex', gap:'6px', flexShrink:0 }}>
            <button
              style={{ ...M.btnOk, padding:'6px 14px', fontSize:'12px', cursor:'pointer' }}
              onClick={() => downloadFile(preview.file_url, preview.file_name)}
            >↓ Descargar</button>
            <button style={M.xbtn} onClick={onClose}>✕</button>
          </div>
        </div>
        <div style={{ flex:1, overflow:'auto', display:'flex', alignItems:'center', justifyContent:'center', minHeight:'300px', padding:'16px' }}>
          {preview.mime_type?.startsWith('image/') ? (
            <img src={preview.file_url} alt={preview.file_name}
              style={{ maxWidth:'100%', maxHeight:'75vh', objectFit:'contain' }} />
          ) : preview.mime_type === 'application/pdf' ? (
            <iframe src={preview.file_url} style={{ width:'100%', height:'75vh', border:'none' }} title={preview.file_name} />
          ) : (preview.mime_type === 'text/html' || preview.mime_type === 'application/octet-stream') ? (
            <HtmlPreview url={preview.file_url} fileName={preview.file_name} onDownload={downloadFile} />
          ) : (
            <div style={{ textAlign:'center' }}>
              <div style={{ fontSize:'56px', marginBottom:'16px' }}>📄</div>
              <div style={{ color:'#94a3b8', fontFamily:FF, fontSize:'13px', marginBottom:'20px' }}>Vista previa no disponible para este tipo</div>
              <button onClick={() => downloadFile(preview.file_url, preview.file_name)}
                style={{ ...M.btnOk, border:'none', cursor:'pointer', padding:'10px 24px' }}>↓ DESCARGAR</button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
