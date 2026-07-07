/* ============================================================
   HtmlPreview.jsx — Extracted from DocumentsTab.jsx
   Carga el HTML del comprobante y lo muestra en un iframe sandboxed
   ============================================================ */
import { useState, useEffect } from 'react';

const FF = '"IBM Plex Mono", monospace';

// ── HtmlPreview ────────────────────────────────────────────────────────────────
// Carga el HTML del comprobante y lo muestra en un iframe sandboxed
export default function HtmlPreview({ url, fileName, onDownload }) {
  const [srcdoc, setSrcdoc]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    setLoading(true); setError(null); setSrcdoc(null);

    // Data URL (data:text/html;base64,...) — decodificar sin fetch
    if (url?.startsWith('data:')) {
      try {
        const comma = url.indexOf(',');
        const b64   = url.slice(comma + 1);
        const decoded = decodeURIComponent(escape(atob(b64)));
        setSrcdoc(decoded);
        setLoading(false);
      } catch (e) {
        setError('No se pudo decodificar: ' + e.message);
        setLoading(false);
      }
      return;
    }

    // URL normal — fetch
    fetch(url)
      .then(r => {
        if (!r.ok) throw new Error(`Error ${r.status}: ${r.statusText}`);
        return r.text();
      })
      .then(html => { setSrcdoc(html); setLoading(false); })
      .catch(e  => { setError(e.message); setLoading(false); });
  }, [url]);

  if (loading) return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', width:'100%', height:'300px', color:'#64748b', fontFamily:FF, fontSize:'11px', gap:'8px' }}>
      <span style={{ animation:'spin 1s linear infinite', display:'inline-block' }}>◈</span> Cargando comprobante...
    </div>
  );

  if (error) return (
    <div style={{ textAlign:'center' }}>
      <div style={{ fontSize:'40px', marginBottom:'12px' }}>⚠</div>
      <div style={{ color:'#94a3b8', fontFamily:FF, fontSize:'12px', marginBottom:'8px' }}>No se pudo cargar la vista previa</div>
      <div style={{ color:'#475569', fontFamily:FF, fontSize:'10px', marginBottom:'16px' }}>{error}</div>
      <button onClick={() => onDownload(url, fileName)}
        style={{ background:'#0EA5E9', border:'none', color:'#fff', padding:'8px 20px', cursor:'pointer', fontFamily:FF, fontSize:'11px', letterSpacing:'1px' }}>
        ↓ DESCARGAR COMPROBANTE
      </button>
    </div>
  );

  return (
    <iframe
      srcDoc={srcdoc}
      sandbox="allow-same-origin"
      style={{ width:'100%', height:'75vh', border:'none', background:'#fff' }}
      title={fileName}
    />
  );
}
