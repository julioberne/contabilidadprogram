/* ============================================================
   HistorialTab.jsx — Historial de Pagos de Nómina
   Módulo 08c — pestaña independiente junto a Documentos
   Muestra: todos los pagos, totales, generación de comprobantes
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import { API_HR } from '../../../../config';

const API = API_HR;
const FF  = '"IBM Plex Mono", monospace';
const C   = { bg:'#0a0a0a', card:'#0f0f0f', border:'#1e1e1e', text:'#e2e8f0', dim:'#64748b', accent:'#0EA5E9', green:'#10B981', red:'#EF4444' };

const fmt = n => {
  if (n == null) return '—';
  return `$${Number(n).toLocaleString('es-CO')}`;
};
const fmtDate = d => d ? new Date(d).toLocaleDateString('es-CO', { day:'2-digit', month:'short', year:'numeric' }) : '—';

export default function HistorialTab({ member, workspace, currentUser }) {
  const canEdit = currentUser?.role === 'owner' || currentUser?.role === 'admin' || currentUser?.is_superuser;

  const [records, setRecords]     = useState([]);
  const [loading, setLoading]     = useState(false);
  const [error,   setError]       = useState(null);
  const [genId,   setGenId]       = useState(null);  // id del record generando comprobante

  const load = useCallback(() => {
    if (!member?.id || !workspace?.id) return;
    setLoading(true);
    setError(null);
    fetch(`${API}/payments/${member.id}?workspace_id=${workspace.id}`)
      .then(r => r.json())
      .then(d => setRecords(Array.isArray(d) ? d : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [member?.id, workspace?.id]);

  useEffect(() => { load(); }, [load]);

  // ── Totales ─────────────────────────────────────────────────
  const totals = records.reduce((acc, r) => {
    acc.base      += Number(r.base_amount      || 0);
    acc.devengado += Number(r.devengado_total  || 0);
    acc.deduccion += Number(r.deduccion_empleado || 0);
    acc.neto      += Number(r.neto_a_pagar     || 0);
    acc.empresa   += Number(r.costo_empleador  || 0);
    return acc;
  }, { base: 0, devengado: 0, deduccion: 0, neto: 0, empresa: 0 });
  const handleGenVoucher = async (rec) => {
    setGenId(rec.id);
    try {
      const html     = buildVoucherHTML(rec, member);
      const safeName = (rec.period_label || rec.id).replace(/[\s/]/g, '_');
      const fileName = `Comprobante_${member.name?.replace(/\s/g,'_') || member.id}_${safeName}.html`;

      // Convertir HTML a base64 data URL — evita subir a Storage (bucket restringe MIME types)
      const b64     = btoa(unescape(encodeURIComponent(html)));
      const dataUrl = `data:text/html;base64,${b64}`;

      // Guardar metadata en hr_documents via backend
      const metaRes = await fetch(
        `${API}/documents/${member.id}?workspace_id=${workspace.id}`,
        {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            file_name:   fileName,
            file_url:    dataUrl,
            file_size:   html.length,
            mime_type:   'text/html',
            category:    'nomina',
            folder_id:   null,
            description: `Comprobante de pago — ${rec.period_label || rec.id}`,
            uploaded_by: member.id,
          }),
        }
      );
      if (!metaRes.ok) throw new Error(`Error guardando: ${metaRes.status}`);
      const docRecord = await metaRes.json();
      const docId     = docRecord?.id;

      // Vincular al registro de pago
      if (docId) {
        await fetch(`${API}/payments/${member.id}/${rec.id}/voucher?doc_id=${docId}`, { method: 'PUT' });
        load();
      }
      alert(`✓ Comprobante generado. Ve a Documentos › Desprendibles para verlo.`);
    } catch (e) {
      alert('Error generando comprobante: ' + e.message);
      console.error('[Voucher]', e);
    } finally {
      setGenId(null);
    }
  };


  if (!member) return null;

  return (
    <div style={S.root}>
      {/* ── HEADER ── */}
      <div style={S.topbar}>
        <div>
          <div style={S.title}>◉ HISTORIAL DE PAGOS</div>
          <div style={S.sub}>{records.length} registros · {member.name}</div>
        </div>
        <div style={{ display:'flex', gap:'8px', alignItems:'center' }}>
          {records.length > 0 && (
            <div style={S.totalBadge}>
              TOTAL NETO: <span style={{ color: C.green }}>{fmt(totals.neto)}</span>
            </div>
          )}
        </div>
      </div>

      {/* ── RESUMEN TOTALES ── */}
      {records.length > 0 && (
        <div style={S.summaryBar}>
          {[
            { label:'BASE TOTAL',      val: totals.base,      col: C.dim },
            { label:'DEVENGADO TOTAL', val: totals.devengado, col: C.text },
            { label:'DEDUCCIONES',     val: totals.deduccion, col: C.red },
            { label:'NETO TOTAL',      val: totals.neto,      col: C.green },
            { label:'COSTO EMPRESA',   val: totals.empresa,   col: '#F59E0B' },
          ].map(({ label, val, col }) => (
            <div key={label} style={S.summaryCard}>
              <div style={{ color: C.dim, fontSize:'8px', letterSpacing:'1px' }}>{label}</div>
              <div style={{ color: col, fontSize:'15px', fontWeight:700, marginTop:'3px' }}>{fmt(val)}</div>
            </div>
          ))}
        </div>
      )}

      {/* ── TABLA ── */}
      <div style={S.tableWrap}>
        {loading && <div style={S.loading}>CARGANDO HISTORIAL...</div>}
        {error   && <div style={S.err}>Error: {error}</div>}

        {!loading && records.length === 0 && (
          <div style={S.empty}>
            <div style={{ fontSize:'32px' }}>◉</div>
            <div style={{ color:C.dim, fontSize:'12px' }}>Sin registros de pago todavía</div>
            <div style={{ color:'#1a1a1a', fontSize:'10px' }}>Los pagos registrados en Salario aparecerán aquí</div>
          </div>
        )}

        {records.length > 0 && (
          <table style={S.table}>
            <thead>
              <tr style={S.thead}>
                <th style={S.th}>PERÍODO</th>
                <th style={{ ...S.th, textAlign:'right' }}>SALARIO BASE</th>
                <th style={{ ...S.th, textAlign:'right' }}>DEVENGADO</th>
                <th style={{ ...S.th, textAlign:'right' }}>DEDUCCIONES</th>
                <th style={{ ...S.th, textAlign:'right', color: C.green }}>NETO A PAGAR</th>
                <th style={{ ...S.th, textAlign:'right', color:'#F59E0B' }}>COSTO EMPRESA</th>
                <th style={S.th}>FECHA PAGO</th>
                <th style={S.th}>COMPROBANTE</th>
              </tr>
            </thead>
            <tbody>
              {records.map((rec, i) => (
                <tr key={rec.id} style={{ ...S.trow, background: i%2===0 ? C.card : C.bg }}>
                  <td style={{ ...S.td, color: C.accent, fontWeight:700 }}>{rec.period_label || `${rec.period_month}/${rec.period_year}`}</td>
                  <td style={{ ...S.td, textAlign:'right', color:C.dim }}>{fmt(rec.base_amount)}</td>
                  <td style={{ ...S.td, textAlign:'right' }}>{fmt(rec.devengado_total)}</td>
                  <td style={{ ...S.td, textAlign:'right', color: C.red }}>{rec.deduccion_empleado ? `-${fmt(rec.deduccion_empleado).slice(1)}` : '—'}</td>
                  <td style={{ ...S.td, textAlign:'right', color: C.green, fontWeight:700 }}>{fmt(rec.neto_a_pagar)}</td>
                  <td style={{ ...S.td, textAlign:'right', color:'#F59E0B' }}>{fmt(rec.costo_empleador)}</td>
                  <td style={{ ...S.td, color:C.dim }}>{fmtDate(rec.payment_date || rec.created_at)}</td>
                  <td style={{ ...S.td }}>
                    {rec.voucher_document_id
                      ? <span style={{ color: C.green, fontSize:'10px' }}>✓ Generado</span>
                      : canEdit
                        ? (
                          <button style={S.genBtn} onClick={() => handleGenVoucher(rec)} disabled={genId === rec.id}>
                            {genId === rec.id ? '...' : '◈ Generar'}
                          </button>
                        )
                        : <span style={{ color:'#1a1a1a', fontSize:'10px' }}>—</span>
                    }
                  </td>
                </tr>
              ))}
              {/* Fila totales */}
              <tr style={{ ...S.trow, background:'#0a1a0a', borderTop:`2px solid ${C.green}` }}>
                <td style={{ ...S.td, color: C.dim, fontWeight:700 }}>TOTALES ({records.length})</td>
                <td style={{ ...S.td, textAlign:'right', color:C.dim, fontWeight:700 }}>{fmt(totals.base)}</td>
                <td style={{ ...S.td, textAlign:'right', fontWeight:700 }}>{fmt(totals.devengado)}</td>
                <td style={{ ...S.td, textAlign:'right', color: C.red, fontWeight:700 }}>-{fmt(totals.deduccion).slice(1)}</td>
                <td style={{ ...S.td, textAlign:'right', color: C.green, fontWeight:700, fontSize:'14px' }}>{fmt(totals.neto)}</td>
                <td style={{ ...S.td, textAlign:'right', color:'#F59E0B', fontWeight:700 }}>{fmt(totals.empresa)}</td>
                <td colSpan={2} />
              </tr>
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ── Builder HTML comprobante ───────────────────────────────────────────────────
function buildVoucherHTML(rec, member) {
  const fmt2 = n => n != null ? `$${Number(n).toLocaleString('es-CO')}` : '$0';
  return `<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8">
<title>Comprobante de Pago — ${rec.period_label}</title>
<style>
  body { font-family: 'IBM Plex Mono', monospace; background:#0a0a0a; color:#e2e8f0; margin:0; padding:32px; }
  .box { max-width:720px; margin:auto; border:2px solid #1e1e1e; padding:32px; }
  .header { border-bottom:2px solid #0EA5E9; padding-bottom:16px; margin-bottom:24px; }
  .title { color:#0EA5E9; font-size:20px; font-weight:700; letter-spacing:4px; }
  .meta { color:#64748b; font-size:11px; margin-top:6px; }
  .row { display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #1a1a1a; font-size:13px; }
  .label { color:#64748b; }
  .val { text-align:right; }
  .neto { background:#0a1a0a; border:1px solid #10B981; padding:20px; text-align:center; margin:24px 0; }
  .neto-label { color:#64748b; font-size:11px; }
  .neto-val { color:#10B981; font-size:28px; font-weight:700; margin-top:6px; }
  .footer { color:#334155; font-size:10px; margin-top:24px; text-align:center; border-top:1px solid #1a1a1a; padding-top:12px; }
</style></head>
<body><div class="box">
  <div class="header">
    <div class="title">◈ COMPROBANTE DE PAGO</div>
    <div class="meta">FIN-SYS OS v2.0 · ${new Date().toLocaleDateString('es-CO')}</div>
  </div>
  <div class="row"><span class="label">EMPLEADO</span><span class="val">${member?.name || '—'}</span></div>
  <div class="row"><span class="label">PERÍODO</span><span class="val">${rec.period_label || `${rec.period_month}/${rec.period_year}`}</span></div>
  <div class="row"><span class="label">SALARIO BASE</span><span class="val">${fmt2(rec.base_amount)}</span></div>
  <div class="row"><span class="label">TOTAL DEVENGADO</span><span class="val">${fmt2(rec.devengado_total)}</span></div>
  <div class="row"><span class="label" style="color:#EF4444">DEDUCCIONES EMPLEADO</span><span class="val" style="color:#EF4444">-${fmt2(rec.deduccion_empleado).slice(1)}</span></div>
  <div class="neto">
    <div class="neto-label">NETO A PAGAR</div>
    <div class="neto-val">${fmt2(rec.neto_a_pagar)}</div>
  </div>
  <div class="row"><span class="label" style="color:#F59E0B">COSTO TOTAL EMPRESA</span><span class="val" style="color:#F59E0B">${fmt2(rec.costo_empleador)}</span></div>
  <div class="footer">Documento generado automáticamente · FIN-SYS OS · No requiere firma física</div>
</div></body></html>`;
}

// ── Estilos ────────────────────────────────────────────────────────────────────
const S = {
  root:        { display:'flex', flexDirection:'column', flex:1, overflow:'hidden', fontFamily:FF, background:C.bg },
  topbar:      { display:'flex', alignItems:'center', justifyContent:'space-between', padding:'12px 16px', borderBottom:`2px solid ${C.border}`, flexShrink:0, gap:'12px', flexWrap:'wrap' },
  title:       { color:C.accent, fontSize:'12px', fontWeight:700, letterSpacing:'2px' },
  sub:         { color:C.dim, fontSize:'10px', marginTop:'2px' },
  totalBadge:  { background:'#0a1a0a', border:`1px solid ${C.green}`, color:C.dim, fontSize:'11px', padding:'6px 14px', fontFamily:FF, letterSpacing:'0.5px' },
  summaryBar:  { display:'flex', gap:'0', borderBottom:`1px solid ${C.border}`, flexShrink:0, overflowX:'auto' },
  summaryCard: { flex:1, minWidth:'130px', padding:'12px 16px', borderRight:`1px solid ${C.border}` },
  tableWrap:   { flex:1, overflowY:'auto' },
  loading:     { color:C.dim, fontSize:'11px', padding:'24px 16px' },
  err:         { color:C.red, fontSize:'11px', padding:'12px 16px', background:'#1a0a0a', margin:'12px 16px' },
  empty:       { display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', flex:1, gap:'10px', padding:'60px 20px', color:C.dim },
  table:       { width:'100%', borderCollapse:'collapse', fontSize:'11px', fontFamily:FF },
  thead:       { position:'sticky', top:0, background:'#0d0d0d', zIndex:1 },
  th:          { color:C.dim, fontSize:'9px', letterSpacing:'1px', padding:'8px 12px', textAlign:'left', borderBottom:`1px solid ${C.border}`, fontWeight:700 },
  trow:        { borderBottom:`1px solid ${C.border}` },
  td:          { padding:'9px 12px', color:C.text },
  genBtn:      { background:'transparent', border:`1px solid #1e3a5f`, color:'#2a6a9f', padding:'3px 10px', cursor:'pointer', fontSize:'9px', fontFamily:FF, letterSpacing:'0.5px' },
};
