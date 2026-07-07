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

// ── Extracted modules ──────────────────────────────────────────────────────────
import {
  API, MAX_MB, MAX_B,
  publicUrl, downloadFile,
  DEFAULT_CATEGORIES, FOLDER_COLORS, FILE_ICONS, FILE_EXT,
  catLabelFrom, catColorFrom,
  fmtSize, fmtDate,
} from './docs/constants';
import { C, FF, S, M, FC, FR } from './docs/styles';
import { FolderCard, NewFolderCard } from './docs/FolderCard';
import { FileCard, FileRow } from './docs/FileCard';
import HtmlPreview from './docs/HtmlPreview';
import UploadModal from './docs/UploadModal';
import PreviewModal from './docs/PreviewModal';
import CategoryConfigModal from './docs/CategoryConfigModal';

// ── Componente principal ───────────────────────────────────────────────────────
export default function DocumentsTab({ member, workspace, currentUser }) {
  const canEdit = currentUser?.role === 'owner' || currentUser?.role === 'admin' || currentUser?.is_superuser;
  const fileRef = useRef(null);

  // CATEGORÍAS DINÁMICAS
  const [categories, setCategories] = useState(DEFAULT_CATEGORIES);
  const [showCatConfig, setShowCatConfig] = useState(false);
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
              ? <div style={S.fileGrid}>{docsHere.map(d => <FileCard key={d.id} doc={d} canEdit={canEdit} catLabelFn={catLabel} catColorFn={catColor} onPreview={() => setPreview(d)} onDelete={() => handleDelete(d)} />)}</div>
              : <div style={S.fileList}>{docsHere.map(d => <FileRow  key={d.id} doc={d} canEdit={canEdit} catLabelFn={catLabel} catColorFn={catColor} onPreview={() => setPreview(d)} onDelete={() => handleDelete(d)} />)}</div>
          )}
        </div>
      </div>

      {/* ══ MODAL UPLOAD ═════════════════════════════════════════ */}
      {showUpload && (
        <UploadModal
          pendingFiles={pendingFiles} uploading={uploading} uploadPct={uploadPct} uploadError={uploadError}
          uploadCat={uploadCat} setUploadCat={setUploadCat}
          uploadFolder={uploadFolder} setUploadFolder={setUploadFolder}
          allFolders={allFolders} categories={categories}
          onUpload={handleUpload}
          onClose={() => { setShowUpload(false); setPendingFiles([]); }}
        />
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
        <PreviewModal
          preview={preview}
          catLabel={catLabel}
          catColor={catColor}
          onClose={() => setPreview(null)}
        />
      )}

      {/* ══ MODAL CONFIGURAR CATEGORÍAS ═════════════════════════ */}
      {showCatConfig && (
        <CategoryConfigModal
          categories={categories}
          workspaceId={workspace.id}
          onClose={() => setShowCatConfig(false)}
          onReload={loadCategories}
        />
      )}
    </div>
  );
}
