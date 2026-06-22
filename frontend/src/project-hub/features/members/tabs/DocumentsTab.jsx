/* ============================================================
   DocumentsTab.jsx — HR Drive v2 (fixes + UX mejorada)
   ============================================================
   FIX 1: URLs usan /storage/v1/object/public/hr-docs/
   FIX 2: "Todos los archivos" muestra colección GLOBAL
   FIX 3: Bucket público → thumbnails y preview funcionan
   UX+:   search bar, vista lista/grid, indicador de modo
   ============================================================ */
import { useState, useEffect, useRef, useCallback } from 'react';
import { supabase } from '../../../lib/supabaseClient';

const API    = 'http://localhost:8000/api/hr';
const MAX_MB = 50;
const MAX_B  = MAX_MB * 1024 * 1024;
const SB_URL = 'https://sciorfjvdqxvcwgvnmbv.supabase.co';

// Genera URL pública correcta (bucket público)
const publicUrl = (path) => `${SB_URL}/storage/v1/object/public/hr-docs/${path}`;

// Descarga forzada via blob (evita el 404 de open-in-tab en Supabase)
const downloadFile = async (url, fileName) => {
  try {
    let blobUrl;
    if (url?.startsWith('data:')) {
      const comma = url.indexOf(',');
      const b64   = url.slice(comma + 1);
      const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      const blob  = new Blob([bytes], { type: 'text/html' });
      blobUrl = URL.createObjectURL(blob);
    } else {
      const res = await fetch(url);
      if (!res.ok) throw new Error('No se pudo descargar el archivo');
      const blob = await res.blob();
      blobUrl = URL.createObjectURL(blob);
    }
    const a    = document.createElement('a');
    a.href     = blobUrl;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(blobUrl); a.remove(); }, 1000);
  } catch (e) {
    window.open(url, '_blank');
  }
};

// Categorías por defecto (usadas como fallback si no hay BD)
const DEFAULT_CATEGORIES = [
  { id: 'contrato',     label: 'Contrato laboral',    color: '#0EA5E9' },
  { id: 'cedula',       label: 'Cédula / ID',          color: '#10B981' },
  { id: 'hoja_vida',    label: 'Hoja de vida',         color: '#8B5CF6' },
  { id: 'fotos',        label: 'Fotos',                color: '#F59E0B' },
  { id: 'clinico',      label: 'Historial clínico',    color: '#EF4444' },
  { id: 'certificados', label: 'Certificados',         color: '#06B6D4' },
  { id: 'nomina',       label: 'Desprendibles nómina', color: '#84CC16' },
  { id: 'financiero',   label: 'Info financiera',      color: '#F97316' },
  { id: 'paz_salvo',    label: 'Paz y salvos',         color: '#EC4899' },
  { id: 'cartas',       label: 'Cartas / Notas',       color: '#A78BFA' },
  { id: 'general',      label: 'General',              color: '#64748b' },
];
const FOLDER_COLORS = ['#0EA5E9','#10B981','#F59E0B','#EF4444','#8B5CF6','#F97316','#06B6D4','#64748b'];
const FILE_ICONS  = { 'application/pdf':'📄', 'image/jpeg':'🖼','image/jpg':'🖼','image/png':'🖼', 'application/vnd.ms-excel':'📊', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'📊', 'text/html':'📄', 'application/octet-stream':'📄', 'application/msword':'📝', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':'📝' };
const FILE_EXT    = { 'application/pdf':'PDF','image/jpeg':'JPG','image/jpg':'JPG','image/png':'PNG','application/vnd.ms-excel':'XLS','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'XLSX','text/html':'HTML','application/octet-stream':'FILE','application/msword':'DOC','application/vnd.openxmlformats-officedocument.wordprocessingml.document':'DOCX' };

// Estas funciones usan el array dinámico de categorías (reciben el array como parámetro)
const catLabelFrom = (cats, id) => cats.find(c => c.id === id)?.label || id;
const catColorFrom = (cats, id) => cats.find(c => c.id === id)?.color || '#64748b';
// Compatibilidad hacia atrás con funciones sin parámetro (usan DEFAULT)
const catLabel = id => DEFAULT_CATEGORIES.find(c => c.id === id)?.label || id;
const catColor = id => DEFAULT_CATEGORIES.find(c => c.id === id)?.color || '#64748b';
const fmtSize  = b => !b ? '—' : b < 1048576 ? `${(b/1024).toFixed(0)} KB` : `${(b/1048576).toFixed(1)} MB`;
const fmtDate  = s => s ? new Date(s).toLocaleDateString('es-CO',{day:'2-digit',month:'short',year:'numeric'}) : '—';

// ── Componente principal ───────────────────────────────────────────────────────
export default function DocumentsTab({ member, workspace, currentUser }) {
  const canEdit = currentUser?.role === 'owner' || currentUser?.role === 'admin' || currentUser?.is_superuser;
  const fileRef = useRef(null);

  // CATEGORÍAS DINÁMICAS
  const [categories, setCategories] = useState(DEFAULT_CATEGORIES);
  const [showCatConfig, setShowCatConfig] = useState(false);
  const [editingCat,    setEditingCat]    = useState(null); // {id, name, color, sort_order, isNew}
  const catLabel = id => categories.find(c => c.id === id)?.label || catLabelFrom(DEFAULT_CATEGORIES, id);
  const catColor = id => categories.find(c => c.id === id)?.color || catColorFrom(DEFAULT_CATEGORIES, id);

  // ── Navegación
  const [path,       setPath]       = useState([]);
  const [folderId,   setFolderId]   = useState(null);

  // ── Filtros / vista
  const [catFilter,  setCatFilter]  = useState('all');   // 'all' | category id
  const [globalMode, setGlobalMode] = useState(false);   // true = ignorar carpeta actual
  const [viewMode,   setViewMode]   = useState('grid');  // 'grid' | 'list'
  const [search,     setSearch]     = useState('');

  // ── Datos
  const [allFolders, setAllFolders] = useState([]);
  const [allDocs,    setAllDocs]    = useState([]);
  const [loading,    setLoading]    = useState(false);

  // ── Upload
  const [showUpload,   setShowUpload]   = useState(false);
  const [pendingFiles, setPendingFiles] = useState([]);
  const [uploadCat,    setUploadCat]    = useState('general');
  const [uploadFolder, setUploadFolder] = useState(null);
  const [uploading,    setUploading]    = useState(false);
  const [uploadPct,    setUploadPct]    = useState(0);
  const [uploadError,  setUploadError]  = useState('');

  // ── Carpetas
  const [editingFolder, setEditingFolder] = useState(null);
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [newFolder,     setNewFolder]     = useState({ name:'', color:'#0EA5E9' });

  // ── Preview
  const [preview, setPreview] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  // ── Carga de datos ─────────────────────────────────────────────────────────────────
  const loadCategories = useCallback(() => {
    if (!workspace?.id) return;
    fetch(`${API}/categories/${workspace.id}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (Array.isArray(data) && data.length) {
          // Mapear respuesta del servidor
          const fromServer = data.map(c => ({ id: c.id, label: c.name, color: c.color, sort_order: c.sort_order, is_default: c.is_default }));
          // Merge: garantizar que todos los defaults estén presentes aunque no estén en BD
          const serverIds = new Set(fromServer.map(c => c.id));
          const merged = [...fromServer];
          DEFAULT_CATEGORIES.forEach(def => {
            if (!serverIds.has(def.id)) merged.push({ ...def, is_default: true });
          });
          merged.sort((a, b) => (a.sort_order || 99) - (b.sort_order || 99) || a.label.localeCompare(b.label));
          setCategories(merged);
        }
        // Si la respuesta es null o vacía, se mantiene DEFAULT_CATEGORIES
      })
      .catch(() => {});
  }, [workspace?.id]);

  const load = useCallback(() => {
    if (!workspace?.id || !member?.id) return;
    setLoading(true);
    Promise.all([
      fetch(`${API}/folders/${workspace.id}`).then(r => r.json()).catch(() => []),
      fetch(`${API}/documents/${member.id}?workspace_id=${workspace.id}`).then(r => r.json()).catch(() => []),
    ]).then(([folders, docs]) => {
      setAllFolders(Array.isArray(folders) ? folders : []);
      setAllDocs(Array.isArray(docs) ? docs : []);
    }).finally(() => setLoading(false));
  }, [workspace?.id, member?.id]);

  useEffect(() => { load(); loadCategories(); }, [load, loadCategories]);
  useEffect(() => { setUploadFolder(folderId); }, [folderId]);

  // ── Lógica de filtrado ─────────────────────────────────────────────────────
  // Modo global: categoría clickeada en sidebar ó "Todos" → muestra toda la colección
  // Modo carpeta: navega por el árbol de carpetas
  const basePool = globalMode
    ? allDocs                                                      // toda la colección
    : allDocs.filter(d => (d.folder_id || null) === folderId);    // solo carpeta actual

  const searchFiltered = search.trim()
    ? basePool.filter(d => d.file_name.toLowerCase().includes(search.toLowerCase()))
    : basePool;

  const docsHere = catFilter === 'all'
    ? searchFiltered
    : searchFiltered.filter(d => d.category === catFilter);

  // Carpetas hijas de la carpeta actual (solo en modo no-global)
  const childFolders = globalMode ? [] : allFolders.filter(f => (f.parent_id || null) === folderId);

  // Conteos para sidebar
  const catCounts = categories.reduce((acc, c) => {
    acc[c.id] = allDocs.filter(d => d.category === c.id).length;
    return acc;
  }, {});
  const docsInFolder = fid => allDocs.filter(d => (d.folder_id || null) === fid).length;

  // ── Navegación ─────────────────────────────────────────────────────────────
  const openFolder = folder => {
    setPath(p => [...p, { id: folder.id, name: folder.name, color: folder.color }]);
    setFolderId(folder.id);
    setGlobalMode(false);
    setCatFilter('all');
    setSearch('');
  };
  const navigateTo = idx => {
    if (idx < 0) { setPath([]); setFolderId(null); }
    else { const np = path.slice(0, idx + 1); setPath(np); setFolderId(np[idx].id); }
    setGlobalMode(false);
    setCatFilter('all');
  };
  const handleCatClick = (catId) => {
    setCatFilter(catId);
    setGlobalMode(true);   // siempre global al filtrar por categoría
    setSearch('');
  };
  const handleAllClick = () => {
    setCatFilter('all');
    setGlobalMode(true);
    setSearch('');
  };

  // ── Carpeta CRUD ───────────────────────────────────────────────────────────
  const handleCreateFolder = async () => {
    if (!newFolder.name.trim()) return;
    await fetch(`${API}/folders/${workspace.id}`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ name: newFolder.name.trim(), color: newFolder.color, parent_id: folderId, created_by: currentUser?.id }),
    });
    setNewFolder({ name:'', color:'#0EA5E9' });
    setShowNewFolder(false);
    load();
  };
  const handleSaveFolder = async () => {
    if (!editingFolder?.name?.trim()) return;
    await fetch(`${API}/folders/${workspace.id}/${editingFolder.id}`, {
      method: 'PUT', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ name: editingFolder.name, color: editingFolder.color }),
    });
    setEditingFolder(null);
    load();
  };
  const handleDeleteFolder = async fid => {
    if (!confirm('¿Eliminar carpeta y todos sus archivos?')) return;
    await fetch(`${API}/folders/${workspace.id}/${fid}`, { method: 'DELETE' });
    load();
  };

  // ── Upload ─────────────────────────────────────────────────────────────────
  const pickFiles = files => {
    const valid = [];
    for (const f of files) {
      // Aceptar todos los tipos conocidos + octet-stream (comprobantes)
      const isKnown = FILE_ICONS[f.type];
      const isOctet = f.type === 'application/octet-stream' || f.type === 'text/html';
      if (!isKnown && !isOctet) { setUploadError(`Tipo no permitido: ${f.name}`); continue; }
      if (f.size > MAX_B) { setUploadError(`Muy grande: ${f.name} (máx ${MAX_MB}MB)`); continue; }
      valid.push(f);
    }
    if (valid.length) { setPendingFiles(valid); setUploadError(''); setShowUpload(true); }
  };

  const handleUpload = async () => {
    setUploading(true); setUploadError('');
    let done = 0;
    for (const file of pendingFiles) {
      setUploadPct(Math.round(done / pendingFiles.length * 80));
      try {
        const storagePath = `${workspace.id}/${member.id}/${Date.now()}_${file.name}`;
        const { error: sErr } = await supabase.storage.from('hr-docs').upload(storagePath, file, { contentType: file.type, upsert: false });
        if (sErr) throw new Error(sErr.message);

        // URL pública correcta (bucket público)
        const url = publicUrl(storagePath);
        const res = await fetch(`${API}/documents/${member.id}?workspace_id=${workspace.id}`, {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({ file_name: file.name, file_url: url, file_size: file.size, mime_type: file.type, category: uploadCat, folder_id: uploadFolder || null, uploaded_by: currentUser?.id }),
        });
        if (!res.ok) throw new Error('Error guardando metadatos');
        done++;
      } catch (e) { setUploadError(prev => `${prev}\nError: ${file.name} — ${e.message}`); }
    }
    setUploadPct(100);
    setTimeout(() => { setUploading(false); setUploadPct(0); }, 400);
    setPendingFiles([]); setShowUpload(false);
    load();
  };

  const handleDelete = async doc => {
    if (!confirm(`¿Eliminar "${doc.file_name}"?`)) return;
    try {
      const storagePath = doc.file_url.split('/public/hr-docs/')[1];
      if (storagePath) await supabase.storage.from('hr-docs').remove([storagePath]);
    } catch {}
    await fetch(`${API}/documents/${member.id}/${doc.id}`, { method: 'DELETE' });
    load();
  };

  // ── Indicador de contexto ─────────────────────────────────────────────────
  const contextLabel = globalMode
    ? (catFilter === 'all' ? '◈ Toda la colección' : `◈ ${catLabel(catFilter)}`)
    : path.length === 0 ? '◈ Inicio' : null;

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div style={S.root}
      onDragOver={e => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={e => { e.preventDefault(); setDragOver(false); pickFiles(Array.from(e.dataTransfer.files)); }}>

      {/* ── TOP BAR ──────────────────────────────────────────────── */}
      <div style={S.topbar}>
        {/* Breadcrumb / modo */}
        <div style={S.breadcrumb}>
          <button style={S.breadBtn} onClick={() => { navigateTo(-1); setGlobalMode(false); }}>◈ Inicio</button>
          {!globalMode && path.map((seg, i) => (
            <span key={seg.id} style={{ display:'flex', alignItems:'center', gap:'2px' }}>
              <span style={{ color:'#2a2a2a', padding:'0 2px' }}>/</span>
              <button style={{ ...S.breadBtn, color: seg.color || C.dim }} onClick={() => navigateTo(i)}>{seg.name}</button>
            </span>
          ))}
          {globalMode && (
            <span style={{ display:'flex', alignItems:'center', gap:'4px' }}>
              <span style={{ color:'#2a2a2a' }}>/</span>
              <span style={{ color: catFilter === 'all' ? C.accent : catColor(catFilter), fontSize:'12px', fontFamily:FF }}>
                {catFilter === 'all' ? 'Todos los archivos' : catLabel(catFilter)}
              </span>
            </span>
          )}
        </div>

        {/* Controles */}
        <div style={{ display:'flex', gap:'6px', alignItems:'center' }}>
          {/* Search */}
          <div style={S.searchWrap}>
            <span style={{ color:C.dim, fontSize:'11px', paddingLeft:'8px' }}>⌕</span>
            <input style={S.searchInput} placeholder="Buscar archivos..." value={search}
              onChange={e => setSearch(e.target.value)} />
            {search && <button style={S.clearSearch} onClick={() => setSearch('')}>✕</button>}
          </div>
          {/* Vista */}
          <button style={{ ...S.viewBtn, ...(viewMode==='grid'?S.viewBtnActive:{}) }} onClick={() => setViewMode('grid')} title="Vista cuadrícula">⊞</button>
          <button style={{ ...S.viewBtn, ...(viewMode==='list'?S.viewBtnActive:{}) }} onClick={() => setViewMode('list')} title="Vista lista">☰</button>
          {/* Acciones */}
          {canEdit && !globalMode && (
            <button style={S.btnSecondary} onClick={() => { setShowNewFolder(true); setNewFolder({ name:'', color:'#0EA5E9' }); }}>+ Carpeta</button>
          )}
          <button style={S.btnPrimary} onClick={() => fileRef.current?.click()}>↑ SUBIR</button>
          <input ref={fileRef} type="file" multiple style={{ display:'none' }} accept=".pdf,.jpg,.jpeg,.png,.xls,.xlsx"
            onChange={e => pickFiles(Array.from(e.target.files))} />
        </div>
      </div>

      {/* ── BODY ─────────────────────────────────────────────────── */}
      <div style={S.body}>

        {/* Sidebar — CATEGORÍAS */}
        <div style={S.sidebar}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'6px 8px 2px' }}>
            <div style={S.sideTitle}>CATEGORÍAS</div>
            {canEdit && (
              <button onClick={() => setShowCatConfig(true)}
                style={{ background:'transparent', border:'none', color:'#334155', cursor:'pointer', fontSize:'12px', padding:'2px 4px' }}
                title="Configurar categorías">⚙️</button>
            )}
          </div>
          <div style={S.sideHint}>Ver toda la colección por tipo</div>

          <button style={{ ...S.catBtn, ...(globalMode && catFilter==='all' ? S.catBtnActive : {}) }}
            onClick={handleAllClick}>
            <span style={S.catDot(' #0EA5E9')} />
            <span style={S.catLabel}>Todos los archivos</span>
            <span style={{ ...S.catBadge, color:'#64748b' }}>{allDocs.length}</span>
          </button>

          {categories.map(cat => (
            <button key={cat.id}
              style={{ ...S.catBtn, ...(globalMode && catFilter===cat.id ? { ...S.catBtnActive, borderLeft:`2px solid ${cat.color}` } : {}) }}
              onClick={() => handleCatClick(cat.id)}>
              <span style={S.catDot(cat.color)} />
              <span style={S.catLabel}>{cat.label}</span>
              {catCounts[cat.id] > 0 && <span style={{ ...S.catBadge, color:cat.color }}>{catCounts[cat.id]}</span>}
            </button>
          ))}

          {/* Divider */}
          <div style={S.divider} />
          <div style={S.sideTitle}>NAVEGACIÓN</div>
          <div style={S.sideHint}>Doble clic = entrar a carpeta</div>
        </div>

        {/* Contenido Drive */}
        <div style={{ ...S.main, ...(dragOver ? S.mainDrag : {}) }}>

          {/* Stats */}
          <div style={S.statsBar}>
            <span style={S.stats}>
              {!globalMode && childFolders.length > 0 && `${childFolders.length} carpeta${childFolders.length!==1?'s':''}  ·  `}
              {docsHere.length} archivo{docsHere.length!==1?'s':''}
              {search && ` — filtro: "${search}"`}
            </span>
            {dragOver && <span style={{ color:C.accent, fontSize:'11px', fontFamily:FF }}>↓ Suelta aquí para subir</span>}
            {loading && <span style={{ color:C.dim, fontSize:'10px' }}>cargando...</span>}
          </div>

          {/* CARPETAS */}
          {!globalMode && (childFolders.length > 0 || showNewFolder) && (
            <>
              <div style={S.secLabel}>CARPETAS</div>
              <div style={S.folderGrid}>
                {childFolders.map(folder => (
                  <FolderCard key={folder.id} folder={folder}
                    docCount={docsInFolder(folder.id)} canEdit={canEdit}
                    onOpen={() => openFolder(folder)}
                    onEdit={() => setEditingFolder({ ...folder })}
                    onDelete={() => handleDeleteFolder(folder.id)} />
                ))}
                {showNewFolder && (
                  <NewFolderCard value={newFolder} onChange={setNewFolder}
                    onCreate={handleCreateFolder} onCancel={() => setShowNewFolder(false)} />
                )}
              </div>
            </>
          )}

          {/* ARCHIVOS */}
          {docsHere.length > 0 && !globalMode && childFolders.length > 0 && (
            <div style={S.secLabel}>ARCHIVOS EN ESTA CARPETA</div>
          )}

          {docsHere.length === 0 && !loading && childFolders.length === 0 && !showNewFolder && (
            <div style={S.empty}>
              <div style={{ fontSize:'40px', opacity:.15 }}>◈</div>
              <div style={S.emptyMsg}>{canEdit ? 'Vacío — arrastra archivos o haz clic en ↑ SUBIR' : 'Sin archivos aquí'}</div>
              <div style={S.emptyHint}>PDF · JPG · PNG · XLS · XLSX · Máx. {MAX_MB}MB</div>
            </div>
          )}

          {/* Grid o lista */}
          {docsHere.length > 0 && (
            viewMode === 'grid'
              ? <div style={S.fileGrid}>{docsHere.map(d => <FileCard key={d.id} doc={d} canEdit={canEdit} onPreview={() => setPreview(d)} onDelete={() => handleDelete(d)} />)}</div>
              : <div style={S.fileList}>{docsHere.map(d => <FileRow  key={d.id} doc={d} canEdit={canEdit} onPreview={() => setPreview(d)} onDelete={() => handleDelete(d)} />)}</div>
          )}
        </div>
      </div>

      {/* ══ MODAL UPLOAD ═════════════════════════════════════════ */}
      {showUpload && (
        <div style={M.overlay}>
          <div style={M.box}>
            <div style={M.hdr}>
              <span style={M.htitle}>↑ SUBIR {pendingFiles.length} ARCHIVO{pendingFiles.length!==1?'S':''}</span>
              {!uploading && <button style={M.xbtn} onClick={() => { setShowUpload(false); setPendingFiles([]); }}>✕</button>}
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
              {!uploading && <button style={M.btnCancel} onClick={() => { setShowUpload(false); setPendingFiles([]); }}>Cancelar</button>}
              <button style={M.btnOk} onClick={handleUpload} disabled={uploading}>
                {uploading ? `${uploadPct}% subiendo...` : `↑ CONFIRMAR SUBIDA`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══ MODAL EDITAR CARPETA ═══════════════════════════════════ */}
      {editingFolder && (
        <div style={M.overlay}>
          <div style={{ ...M.box, maxWidth:'360px' }}>
            <div style={M.hdr}>
              <span style={M.htitle}>✎ EDITAR CARPETA</span>
              <button style={M.xbtn} onClick={() => setEditingFolder(null)}>✕</button>
            </div>
            <div style={M.field}>
              <label style={M.flabel}>NOMBRE</label>
              <input style={M.inp} value={editingFolder.name} autoFocus
                onChange={e => setEditingFolder(f => ({ ...f, name: e.target.value }))}
                onKeyDown={e => e.key==='Enter' && handleSaveFolder()} />
            </div>
            <div style={M.field}>
              <label style={M.flabel}>COLOR</label>
              <div style={{ display:'flex', gap:'8px', flexWrap:'wrap' }}>
                {FOLDER_COLORS.map(c => (
                  <button key={c} onClick={() => setEditingFolder(f => ({ ...f, color:c }))}
                    style={{ width:'28px', height:'28px', background:c, border: editingFolder.color===c ? '3px solid #fff' : '2px solid transparent', cursor:'pointer' }} />
                ))}
              </div>
            </div>
            <div style={M.field}>
              <label style={M.flabel}>VISTA PREVIA</label>
              <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
                <span style={{ fontSize:'28px', color: editingFolder.color }}>▣</span>
                <span style={{ color:'#e2e8f0', fontFamily:FF, fontSize:'14px' }}>{editingFolder.name || 'Nombre...'}</span>
              </div>
            </div>
            <div style={M.foot}>
              <button style={M.btnCancel} onClick={() => setEditingFolder(null)}>Cancelar</button>
              <button style={M.btnOk} onClick={handleSaveFolder}>✓ GUARDAR</button>
            </div>
          </div>
        </div>
      )}

      {/* ══ MODAL PREVIEW ══════════════════════════════════════════ */}
      {preview && (
        <div style={M.overlay} onClick={() => setPreview(null)}>
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
                <button style={M.xbtn} onClick={() => setPreview(null)}>✕</button>
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
      )}

      {/* ══ MODAL CONFIGURAR CATEGORÍAS ═════════════════════════ */}
      {showCatConfig && (
        <div style={M.overlay}>
          <div style={{ ...M.box, maxWidth:'520px' }}>
            <div style={M.hdr}>
              <span style={M.htitle}>⚙️ CONFIGURAR CATEGORÍAS</span>
              <button style={M.xbtn} onClick={() => { setShowCatConfig(false); setEditingCat(null); }}>✕</button>
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
      )}
    </div>
  );

  // ── CRUD categorías ────────────────────────────────────────────────
  async function handleSaveCat() {
    if (!editingCat?.name?.trim()) return;
    if (editingCat.isNew) {
      await fetch(`${API}/categories/${workspace.id}`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ name: editingCat.name.trim(), color: editingCat.color, sort_order: editingCat.sort_order }),
      });
    } else {
      await fetch(`${API}/categories/${workspace.id}/${editingCat.id}`, {
        method:'PUT', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ name: editingCat.name.trim(), color: editingCat.color, sort_order: editingCat.sort_order }),
      });
    }
    setEditingCat(null);
    loadCategories();
  }

  async function handleDeleteCat(catId) {
    if (!confirm('¿Eliminar esta categoría?')) return;
    await fetch(`${API}/categories/${workspace.id}/${catId}`, { method:'DELETE' });
    loadCategories();
  }
}

// ── HtmlPreview ────────────────────────────────────────────────────────────────
// Carga el HTML del comprobante y lo muestra en un iframe sandboxed
function HtmlPreview({ url, fileName, onDownload }) {
  const [srcdoc, setSrcdoc]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const FF = '"IBM Plex Mono", monospace';

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

// ── FolderCard ─────────────────────────────────────────────────────────────────
function FolderCard({ folder, docCount, canEdit, onOpen, onEdit, onDelete }) {
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
function NewFolderCard({ value, onChange, onCreate, onCancel }) {
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

// ── FileCard (grid) ────────────────────────────────────────────────────────────
function FileCard({ doc, canEdit, onPreview, onDelete }) {
  const [h, setH] = useState(false);
  const isImg     = doc.mime_type?.startsWith('image/');
  const isVoucher = doc.mime_type === 'application/octet-stream' || doc.mime_type === 'text/html';
  const cc = catColor(doc.category);
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
        <div style={{...FC.ctag,background:`${cc}22`,color:cc}}>{catLabel(doc.category)}</div>
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
function FileRow({ doc, canEdit, onPreview, onDelete }) {
  const [h, setH] = useState(false);
  const cc = catColor(doc.category);
  const isVoucher = doc.mime_type === 'application/octet-stream' || doc.mime_type === 'text/html';
  return (
    <div style={{...FR.row,...(h?FR.rowH:{})}} onMouseEnter={()=>setH(true)} onMouseLeave={()=>setH(false)}>
      <span style={{fontSize:'18px',flexShrink:0,width:'28px'}}>{isVoucher ? '🧾' : FILE_ICONS[doc.mime_type]||'📄'}</span>
      <span style={FR.ext}>{FILE_EXT[doc.mime_type]||'FILE'}</span>
      <span style={FR.name}>{doc.file_name}</span>
      <span style={{...FR.cat,background:`${cc}22`,color:cc}}>{catLabel(doc.category)}</span>
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
