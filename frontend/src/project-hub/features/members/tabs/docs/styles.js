/* ============================================================
   styles.js — Extracted from DocumentsTab.jsx
   All style objects: C (colors), FF (font), S, M, FC, FR
   ============================================================ */

// ── Estilos ────────────────────────────────────────────────────────────────────
const C  = { bg:'#0a0a0a', card:'#0f0f0f', border:'#1e1e1e', text:'#e2e8f0', dim:'#64748b', accent:'#0EA5E9' };
const FF = '"IBM Plex Mono", monospace';

const S = {
  root:        { display:'flex', flexDirection:'column', flex:1, overflow:'hidden', fontFamily:FF, background:C.bg },
  topbar:      { display:'flex', alignItems:'center', gap:'8px', padding:'8px 14px', borderBottom:`2px solid ${C.border}`, flexShrink:0, flexWrap:'wrap' },
  breadcrumb:  { display:'flex', alignItems:'center', gap:'2px', flex:1, minWidth:0, flexWrap:'wrap' },
  breadBtn:    { background:'transparent', border:'none', color:C.accent, cursor:'pointer', fontSize:'13px', fontFamily:FF, padding:'2px 6px' },
  searchWrap:  { display:'flex', alignItems:'center', background:'#111', border:`1px solid #2a2a2a`, height:'30px', minWidth:'180px' },
  searchInput: { background:'transparent', border:'none', color:C.text, fontSize:'11px', fontFamily:FF, outline:'none', flex:1, padding:'0 6px' },
  clearSearch: { background:'transparent', border:'none', color:C.dim, cursor:'pointer', padding:'0 6px', fontSize:'11px' },
  viewBtn:     { background:'transparent', border:`1px solid #2a2a2a`, color:C.dim, width:'30px', height:'30px', cursor:'pointer', fontSize:'15px', display:'flex', alignItems:'center', justifyContent:'center' },
  viewBtnActive:{ borderColor:C.accent, color:C.accent },
  btnPrimary:  { background:C.accent, border:'none', color:'#000', padding:'6px 14px', cursor:'pointer', fontSize:'11px', fontWeight:700, letterSpacing:'0.5px', fontFamily:FF, flexShrink:0 },
  btnSecondary:{ background:'transparent', border:`1px solid #2a2a2a`, color:C.dim, padding:'6px 10px', cursor:'pointer', fontSize:'11px', fontFamily:FF, flexShrink:0 },
  body:        { flex:1, display:'flex', overflow:'hidden' },
  sidebar:     { width:'176px', minWidth:'160px', borderRight:`2px solid ${C.border}`, overflowY:'auto', padding:'10px 6px', display:'flex', flexDirection:'column', gap:'1px', background:'#0a0a0a', flexShrink:0 },
  sideTitle:   { color:C.dim, fontSize:'9px', letterSpacing:'2px', padding:'6px 8px 2px', fontWeight:700 },
  sideHint:    { color:'#1e2a3a', fontSize:'9px', padding:'0 8px 6px', lineHeight:1.4, letterSpacing:'0.2px' },
  catBtn:      { display:'flex', alignItems:'center', gap:'6px', width:'100%', background:'transparent', border:'none', borderLeft:'2px solid transparent', padding:'5px 8px', cursor:'pointer', fontSize:'11px', fontFamily:FF, color:'#94a3b8', textAlign:'left' },
  catBtnActive:{ borderLeft:`2px solid ${C.accent}`, background:'rgba(14,165,233,0.07)', color:C.text },
  catDot:      col => ({ width:'7px', height:'7px', background:col, display:'inline-block', flexShrink:0 }),
  catLabel:    { flex:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' },
  catBadge:    { fontSize:'10px', flexShrink:0 },
  divider:     { height:'1px', background:C.border, margin:'8px 0' },
  main:        { flex:1, overflowY:'auto', padding:'14px', display:'flex', flexDirection:'column', gap:'10px', minWidth:0 },
  mainDrag:    { outline:`2px dashed ${C.accent}`, background:'rgba(14,165,233,0.03)' },
  statsBar:    { display:'flex', alignItems:'center', justifyContent:'space-between', flexShrink:0 },
  stats:       { color:C.dim, fontSize:'11px' },
  secLabel:    { color:C.dim, fontSize:'9px', letterSpacing:'2px', fontWeight:700 },
  folderGrid:  { display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(190px,1fr))', gap:'6px' },
  fileGrid:    { display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(155px,1fr))', gap:'6px' },
  fileList:    { display:'flex', flexDirection:'column', gap:'2px' },
  empty:       { display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', flex:1, gap:'8px', padding:'60px 20px' },
  emptyMsg:    { color:C.dim, fontSize:'13px', textAlign:'center', maxWidth:'280px', lineHeight:1.5 },
  emptyHint:   { color:'#1a1a1a', fontSize:'10px', letterSpacing:'0.5px' },
};

const M = {
  overlay:  { position:'fixed', inset:0, background:'rgba(0,0,0,.9)', zIndex:200, display:'flex', alignItems:'center', justifyContent:'center', padding:'20px' },
  box:      { background:'#111', border:`2px solid #222`, width:'100%', maxWidth:'500px', display:'flex', flexDirection:'column', fontFamily:FF, maxHeight:'90vh' },
  hdr:      { display:'flex', justifyContent:'space-between', alignItems:'center', padding:'12px 16px', borderBottom:'1px solid #1a1a1a', flexShrink:0 },
  htitle:   { color:C.accent, fontSize:'12px', fontWeight:700, letterSpacing:'2px', overflow:'hidden', textOverflow:'ellipsis', flex:1 },
  xbtn:     { background:'transparent', border:'none', color:C.dim, cursor:'pointer', fontSize:'18px', flexShrink:0 },
  field:    { padding:'10px 16px', display:'flex', flexDirection:'column', gap:'6px' },
  flabel:   { color:C.dim, fontSize:'9px', letterSpacing:'2px', fontWeight:700 },
  fileRow:  { display:'flex', alignItems:'center', gap:'8px', padding:'5px 16px', background:'#0f0f0f', borderBottom:'1px solid #111' },
  fname:    { flex:1, color:C.text, fontSize:'11px', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' },
  fsize:    { color:C.dim, fontSize:'10px', flexShrink:0 },
  catGrid:  { display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(140px,1fr))', gap:'4px' },
  catPill:  { display:'flex', alignItems:'center', gap:'5px', background:'#0f0f0f', border:'1px solid #2a2a2a', color:'#64748b', padding:'5px 8px', cursor:'pointer', fontSize:'10px', fontFamily:FF, textAlign:'left', letterSpacing:'0.3px' },
  sel:      { background:'#1a1a1a', border:'2px solid #2a2a2a', color:C.text, padding:'8px', fontSize:'12px', fontFamily:FF, outline:'none', width:'100%' },
  inp:      { background:'#1a1a1a', border:'2px solid #2a2a2a', color:C.text, padding:'8px', fontSize:'13px', fontFamily:FF, outline:'none', width:'100%', boxSizing:'border-box' },
  err:      { margin:'0 16px 8px', padding:'8px', background:'#1a0a0a', border:'1px solid #ef4444', color:'#ef4444', fontSize:'11px', whiteSpace:'pre-line' },
  foot:     { display:'flex', justifyContent:'flex-end', gap:'8px', padding:'12px 16px', borderTop:'1px solid #1a1a1a', flexShrink:0 },
  btnCancel:{ background:'transparent', border:'1px solid #333', color:C.dim, padding:'8px 16px', cursor:'pointer', fontSize:'11px', fontFamily:FF },
  btnOk:    { background:C.accent, border:'none', color:'#000', padding:'8px 18px', cursor:'pointer', fontSize:'11px', fontWeight:700, fontFamily:FF, letterSpacing:'0.5px' },
};

const FC = {
  card:     { background:C.card, border:`1px solid #1e1e1e`, position:'relative', transition:'border-color .15s' },
  cardH:    { borderColor:'#2a2a2a' },
  inner:    { display:'flex', alignItems:'center', gap:'10px', padding:'12px', cursor:'pointer' },
  name:     { color:'#e2e8f0', fontSize:'13px', fontFamily:FF, fontWeight:600, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' },
  meta:     { color:'#64748b', fontSize:'10px', marginTop:'2px' },
  acts:     { position:'absolute', top:'4px', right:'4px', display:'flex', gap:'2px', background:'rgba(0,0,0,.7)' },
  actBtn:   { background:'transparent', border:'none', color:'#94a3b8', cursor:'pointer', fontSize:'12px', padding:'3px 6px', fontFamily:FF },
  inp:      { background:'#1a1a1a', border:'1px solid #333', color:'#e2e8f0', padding:'6px 8px', fontSize:'12px', fontFamily:FF, outline:'none', width:'100%', boxSizing:'border-box' },
  btnCreate:{ background:C.accent, border:'none', color:'#000', padding:'5px 10px', cursor:'pointer', fontSize:'11px', fontWeight:700, fontFamily:FF },
  // file card
  file:     { background:C.card, border:`1px solid #1e1e1e`, display:'flex', flexDirection:'column', overflow:'hidden', position:'relative', transition:'border-color .15s' },
  fileH:    { borderColor:'#2a2a2a' },
  thumb:    { height:'95px', background:'#111', display:'flex', alignItems:'center', justifyContent:'center', position:'relative', overflow:'hidden', cursor:'pointer', flexShrink:0 },
  ico:      { fontSize:'32px', opacity:.7, display:'flex', alignItems:'center', justifyContent:'center', width:'100%', height:'100%' },
  extTag:   { position:'absolute', bottom:'4px', right:'4px', background:'rgba(0,0,0,.75)', color:'#94a3b8', fontSize:'8px', padding:'2px 5px', fontFamily:FF, letterSpacing:'1px' },
  info:     { padding:'7px 10px', display:'flex', flexDirection:'column', gap:'3px' },
  fname:    { color:'#e2e8f0', fontSize:'11px', fontFamily:FF, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' },
  ctag:     { fontSize:'9px', padding:'2px 5px', fontFamily:FF, display:'inline-block', alignSelf:'flex-start', letterSpacing:'0.3px' },
  fmeta:    { color:'#334155', fontSize:'9px' },
  hover:    { position:'absolute', top:'4px', right:'4px', display:'flex', background:'rgba(0,0,0,.75)', gap:'0' },
  hBtn:     { background:'transparent', border:'none', color:'#94a3b8', cursor:'pointer', fontSize:'12px', padding:'3px 7px', fontFamily:FF, textDecoration:'none', display:'flex', alignItems:'center' },
};

const FR = {
  row:  { display:'flex', alignItems:'center', gap:'10px', padding:'8px 12px', background:C.card, border:`1px solid ${C.border}`, transition:'background .1s' },
  rowH: { background:'#111' },
  ext:  { color:C.dim, fontSize:'9px', fontFamily:FF, letterSpacing:'1px', flexShrink:0, width:'32px', textAlign:'right' },
  name: { flex:1, color:'#e2e8f0', fontSize:'12px', fontFamily:FF, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' },
  cat:  { fontSize:'9px', padding:'2px 6px', flexShrink:0, fontFamily:FF },
  size: { color:C.dim, fontSize:'10px', flexShrink:0, width:'60px', textAlign:'right' },
  date: { color:'#2a2a2a', fontSize:'10px', flexShrink:0, width:'90px', textAlign:'right' },
  acts: { display:'flex', gap:'0', flexShrink:0 },
  act:  { background:'transparent', border:'none', color:C.dim, cursor:'pointer', fontSize:'12px', padding:'2px 7px', fontFamily:FF, textDecoration:'none', display:'flex', alignItems:'center' },
};

export { C, FF, S, M, FC, FR };
