/* ============================================================
   CompanyMapTab.jsx — Mapa de Empresas (ADMIN only)
   Módulo 08c — Zero-Impact — nuevo componente independiente
   ============================================================
   Vista matriz: filas = entidades CT, columnas = empleados vinculados
   ADMIN puede asignar / desvincular desde aquí
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import { API_HR, API_CT } from '../../../config';

const API = API_HR;
const CT  = API_CT;

const LEVEL_INDENT = { 1: 0, 2: 16, 3: 32, 4: 48 };
const LEVEL_COLORS = { 1: '#0EA5E9', 2: '#10B981', 3: '#8B5CF6', 4: '#F59E0B' };
const LEVEL_LABELS = { 1: 'HOLDING', 2: 'EMPRESA', 3: 'SUBSIDIARIA', 4: 'PROYECTO' };

// CT API devuelve 'type' como string, no 'level' como número
const TYPE_TO_LEVEL = { HOLDING: 1, EMPRESA: 2, SUBSIDIARIA: 3, SUB_EMPRESA: 3, PROYECTO: 4 };

// Aplanar el árbol anidado que devuelve el CT endpoint
function flattenEntities(list, acc = []) {
  if (!Array.isArray(list)) return acc;
  list.forEach(e => {
    const level = TYPE_TO_LEVEL[e.type] || 2;
    acc.push({ ...e, level });
    if (Array.isArray(e.children) && e.children.length) flattenEntities(e.children, acc);
  });
  return acc;
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function CompanyMapTab({ workspace, currentUser, members }) {
  const canEdit = currentUser?.role === 'owner' || currentUser?.role === 'admin' || currentUser?.is_superuser;

  const [entities,  setEntities]  = useState([]);   // todas las entidades CT
  const [allLinks,  setAllLinks]  = useState([]);   // todos los vínculos empleado-empresa
  const [loading,   setLoading]   = useState(false);
  const [search,    setSearch]    = useState('');

  // Modal crear entidad nueva
  const [newEntityModal, setNewEntityModal] = useState(false);
  const [newEntityForm, setNewEntityForm] = useState({ name: '', level: 2, parent_id: '', description: '' });
  const [savingEntity, setSavingEntity] = useState(false);


  const load = useCallback(() => {
    if (!workspace?.id) return;
    setLoading(true);
    Promise.all([
      fetch(`${CT}/entities`).then(r => r.json()).catch(() => []),
      fetch(`${API}/company-links?workspace_id=${workspace.id}`).then(r => r.json()).catch(() => []),
    ]).then(([raw, links]) => {
      // CT devuelve estructura anidada con 'value' wrapper o array directo
      const rawList = Array.isArray(raw) ? raw : (Array.isArray(raw?.value) ? raw.value : []);
      setEntities(flattenEntities(rawList));
      setAllLinks(Array.isArray(links) ? links : []);
    }).finally(() => setLoading(false));
  }, [workspace?.id]);

  useEffect(() => { load(); }, [load]);

  // Construir mapa: entityId → [{ user_id, entity_name, role_in_company, id }]
  const buildMap = () => {
    const map = {};
    allLinks.forEach(link => {
      const key = String(link.entity_id);
      if (!map[key]) map[key] = [];
      map[key].push(link);
    });
    return map;
  };
  const linkMap = buildMap();

  // Miembros sin ninguna empresa
  const assignedUserIds = new Set(allLinks.map(l => l.user_id));
  const unassigned = (members || []).filter(m => !assignedUserIds.has(m.id));

  // Filtro de búsqueda sobre entidades y empleados
  const filteredEntities = search
    ? entities.filter(e =>
        e.name.toLowerCase().includes(search.toLowerCase()) ||
        (linkMap[String(e.id)] || []).some(l =>
          getMemberName(l.user_id, members).toLowerCase().includes(search.toLowerCase())
        )
      )
    : entities;

  // Modal de asignación rápida
  const [assignModal, setAssignModal] = useState(null);
  const [assignForm,  setAssignForm]  = useState({ user_id: '', role_in_company: '', start_date: '' });
  const [assigning,   setAssigning]   = useState(false);

  const handleCreateEntity = async (e) => {
    e.preventDefault();
    if (!newEntityForm.name.trim()) return;
    setSavingEntity(true);
    try {
      const typeStr = LEVEL_LABELS[newEntityForm.level]; // e.g. 2 → 'EMPRESA'
      const res = await fetch(`${CT}/entities`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name:      newEntityForm.name.trim(),
          type:      typeStr,
          parent_id: newEntityForm.parent_id ? Number(newEntityForm.parent_id) : null,
          industry:  newEntityForm.description || '',
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert('Error al crear: ' + (err.detail || res.statusText));
        return;
      }
      setNewEntityModal(false);
      setNewEntityForm({ name: '', level: 2, parent_id: '', description: '' });
      load();
    } finally { setSavingEntity(false); }
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    if (!assignForm.user_id || !assignModal) return;
    setAssigning(true);
    try {
      await fetch(`${API}/companies/${assignForm.user_id}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entity_id:       assignModal.entityId,
          entity_name:     assignModal.entityName,
          role_in_company: assignForm.role_in_company || null,
          start_date:      assignForm.start_date || null,
        }),
      });
      setAssignModal(null);
      setAssignForm({ user_id: '', role_in_company: '', start_date: '' });
      load();
    } finally { setAssigning(false); }
  };


  const handleUnlink = async (userId, linkId) => {
    if (!confirm('¿Desvincular este trabajador de la empresa?')) return;
    await fetch(`${API}/companies/${userId}/${linkId}`, { method: 'DELETE' });
    load();
  };

  return (
    <div style={S.root}>
      {/* ── HEADER ────────────────────────────────────────── */}
      <div style={S.topbar}>
        <div style={{ color: C.dim, fontSize: '11px' }}>
          {entities.length} entidades · {allLinks.length} vínculos activos · {unassigned.length} sin asignar
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={S.searchWrap}>
            <span style={{ color: '#64748b', fontSize: '11px', padding: '0 6px' }}>⌕</span>
            <input style={S.searchInp} placeholder="Buscar empresa o empleado..."
              value={search} onChange={e => setSearch(e.target.value)} />
            {search && <button style={S.clearBtn} onClick={() => setSearch('')}>✕</button>}
          </div>
          {canEdit && (
            <button style={S.newBtn} onClick={() => setNewEntityModal(true)}>+ NUEVA ENTIDAD</button>
          )}
        </div>
      </div>

      {/* ── LEYENDA ───────────────────────────────────────────────── */}
      <div style={S.legend}>
        {Object.entries(LEVEL_LABELS).map(([lv, label]) => (
          <span key={lv} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', background: LEVEL_COLORS[lv] }} />
            <span style={{ color: LEVEL_COLORS[lv], fontSize: '9px', fontFamily: FF }}>{label}</span>
          </span>
        ))}
        <span style={{ color: '#1a1a1a', fontSize: '9px' }}>|</span>
        <span style={{ color: '#334155', fontSize: '9px', fontFamily: FF }}>
          {canEdit ? 'ADMIN: click en empresa para asignar · ✕ para desvincular' : 'Solo lectura'}
        </span>
      </div>

      {loading && <div style={S.loading}>CARGANDO MAPA...</div>}

      {/* ── TABLA MATRIZ ─────────────────────────────────────────── */}
      <div style={S.matrixWrap}>
        {filteredEntities.map(entity => {
          const links    = linkMap[String(entity.id)] || [];
          const lv       = entity.level || 1;
          const color    = LEVEL_COLORS[lv] || '#64748b';
          const indent   = LEVEL_INDENT[lv] || 0;

          return (
            <div key={entity.id} style={{ ...S.row, paddingLeft: `${indent + 14}px` }}>
              {/* Entidad */}
              <div style={{ ...S.entityCell, borderLeftColor: color }}>
                <span style={{ ...S.levelTag, background: `${color}20`, color }}>
                  {LEVEL_LABELS[lv] || 'NIVEL ' + lv}
                </span>
                <span style={S.entityName}>{entity.name}</span>
                {canEdit && (
                  <button style={S.assignBtn}
                    onClick={() => { setAssignModal({ entityId: entity.id, entityName: entity.name }); setAssignForm({ user_id: '', role_in_company: '', start_date: '' }); }}
                    title="Asignar empleado a esta empresa">
                    + Asignar
                  </button>
                )}
              </div>

              {/* Empleados vinculados */}
              <div style={S.employeesCell}>
                {links.length === 0 && (
                  <span style={S.noEmployees}>Sin empleados asignados</span>
                )}
                {links.map(link => {
                  const mName = getMemberName(link.user_id, members);
                  const initials = mName.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
                  return (
                    <div key={link.id} style={S.empChip}>
                      <span style={S.empAvatar}>{initials}</span>
                      <div style={S.empInfo}>
                        <span style={S.empName}>{mName}</span>
                        {link.role_in_company && <span style={S.empRole}>{link.role_in_company}</span>}
                      </div>
                      {canEdit && (
                        <button style={S.unlinkBtn} title="Desvincular"
                          onClick={() => handleUnlink(link.user_id, link.id)}>✕</button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        {/* Fila: Sin empresa asignada */}
        {unassigned.length > 0 && (
          <div style={{ ...S.row, borderColor: '#1a1a1a' }}>
            <div style={{ ...S.entityCell, borderLeftColor: '#334155' }}>
              <span style={{ ...S.levelTag, background: '#1a1a1a', color: '#64748b' }}>SIN ASIGNAR</span>
              <span style={{ ...S.entityName, color: '#334155' }}>Sin empresa vinculada</span>
            </div>
            <div style={S.employeesCell}>
              {unassigned.map(m => {
                const initials = (m.name || 'NN').split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
                return (
                  <div key={m.id} style={{ ...S.empChip, opacity: .5 }}>
                    <span style={{ ...S.empAvatar, background: '#1a2a1a' }}>{initials}</span>
                    <span style={S.empName}>{m.name || m.email}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* ══ MODAL ASIGNACIÓN RÁPIDA ══════════════════════════════════ */}
      {assignModal && (
        <div style={M.overlay}>
          <div style={M.box}>
            <div style={M.hdr}>
              <div>
                <div style={M.htitle}>ASIGNAR EMPLEADO</div>
                <div style={{ color: '#0EA5E9', fontSize: '11px', fontFamily: FF, marginTop: '2px' }}>
                  ◈ {assignModal.entityName}
                </div>
              </div>
              <button style={M.xbtn} onClick={() => setAssignModal(null)}>✕</button>
            </div>
            <form onSubmit={handleAssign} style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '14px 16px' }}>
              <div style={F.wrap}>
                <label style={F.label}>EMPLEADO</label>
                <select style={F.inp} value={assignForm.user_id} required
                  onChange={e => setAssignForm(f => ({ ...f, user_id: e.target.value }))}>
                  <option value="">Seleccionar trabajador...</option>
                  {(members || []).map(m => (
                    <option key={m.id} value={m.id}>{m.name || m.email}</option>
                  ))}
                </select>
              </div>
              <div style={F.wrap}>
                <label style={F.label}>ROL EN ESTA EMPRESA</label>
                <input style={F.inp} placeholder="Ej: Gerente Financiero"
                  value={assignForm.role_in_company}
                  onChange={e => setAssignForm(f => ({ ...f, role_in_company: e.target.value }))} />
              </div>
              <div style={F.wrap}>
                <label style={F.label}>FECHA DE INICIO</label>
                <input style={F.inp} type="date" value={assignForm.start_date}
                  onChange={e => setAssignForm(f => ({ ...f, start_date: e.target.value }))} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button type="button" style={M.btnCancel} onClick={() => setAssignModal(null)}>Cancelar</button>
                <button type="submit" style={M.btnOk} disabled={assigning}>
                  {assigning ? 'Asignando...' : '◈ VINCULAR'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ══ MODAL NUEVA ENTIDAD ════════════════════════════════ */}
      {newEntityModal && (
        <div style={M.overlay}>
          <div style={M.box}>
            <div style={M.hdr}>
              <div>
                <div style={M.htitle}>+ NUEVA ENTIDAD</div>
                <div style={{ color: C.dim, fontSize: '10px', marginTop: '3px', fontFamily: FF }}>Crear empresa, subsidiaria o proyecto</div>
              </div>
              <button style={M.xbtn} onClick={() => setNewEntityModal(false)}>✕</button>
            </div>
            <form onSubmit={handleCreateEntity} style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '14px 16px' }}>
              <div style={F.wrap}>
                <label style={F.label}>TIPO DE ENTIDAD</label>
                <div style={{ display: 'flex', gap: '6px' }}>
                  {Object.entries(LEVEL_LABELS).map(([lv, lbl]) => (
                    <button type="button" key={lv}
                      style={{ ...M.lvlBtn, ...(String(newEntityForm.level)===lv ? { background: `${LEVEL_COLORS[lv]}22`, borderColor: LEVEL_COLORS[lv], color: LEVEL_COLORS[lv] } : {}) }}
                      onClick={() => setNewEntityForm(f => ({ ...f, level: Number(lv), parent_id: '' }))}>
                      <span style={{ width: '7px', height: '7px', background: LEVEL_COLORS[lv], display: 'inline-block', marginRight: '5px', flexShrink: 0 }} />
                      {lbl}
                    </button>
                  ))}
                </div>
              </div>
              <div style={F.wrap}>
                <label style={F.label}>NOMBRE</label>
                <input style={F.inp} placeholder="Ej: Subsidiaria Sur" required
                  value={newEntityForm.name}
                  onChange={e => setNewEntityForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              {newEntityForm.level > 1 && (
                <div style={F.wrap}>
                  <label style={F.label}>EMPRESA PADRE (opcional)</label>
                  {/* custom list — el select nativo es invisible en fondo oscuro */}
                  <div style={{ border: '1px solid #2a2a2a', background: '#111', maxHeight: '160px', overflowY: 'auto' }}>
                    <div
                      style={{ ...F.optRow, background: !newEntityForm.parent_id ? '#1a2a3a' : 'transparent', color: !newEntityForm.parent_id ? '#0EA5E9' : '#64748b' }}
                      onClick={() => setNewEntityForm(f => ({ ...f, parent_id: '' }))}>
                      ◈ Sin empresa padre
                    </div>
                    {entities
                      .filter(e => Number(e.level) < Number(newEntityForm.level))
                      .map(e => {
                        const lv = Number(e.level);
                        const col = LEVEL_COLORS[lv] || '#64748b';
                        const selected = String(newEntityForm.parent_id) === String(e.id);
                        return (
                          <div key={e.id}
                            style={{ ...F.optRow, background: selected ? `${col}22` : 'transparent', color: selected ? col : '#e2e8f0', borderLeft: selected ? `3px solid ${col}` : '3px solid transparent' }}
                            onClick={() => setNewEntityForm(f => ({ ...f, parent_id: String(e.id) }))}>
                            <span style={{ width: '7px', height: '7px', background: col, display: 'inline-block', marginRight: '8px', flexShrink: 0 }} />
                            {e.name}
                            <span style={{ color: col, fontSize: '9px', marginLeft: '6px' }}>{LEVEL_LABELS[lv]}</span>
                          </div>
                        );
                      })}
                  </div>
                  {newEntityForm.parent_id && (
                    <div style={{ color: '#10B981', fontSize: '10px', marginTop: '4px' }}>
                      ✓ Padre: {entities.find(e => String(e.id) === String(newEntityForm.parent_id))?.name}
                    </div>
                  )}
                </div>
              )}
              <div style={F.wrap}>
                <label style={F.label}>DESCRIPCIÓN (opcional)</label>
                <input style={F.inp} placeholder="Breve descripción..."
                  value={newEntityForm.description}
                  onChange={e => setNewEntityForm(f => ({ ...f, description: e.target.value }))} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button type="button" style={M.btnCancel} onClick={() => setNewEntityModal(false)}>Cancelar</button>
                <button type="submit" style={M.btnOk} disabled={savingEntity}>
                  {savingEntity ? 'Creando...' : '+ CREAR ENTIDAD'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function getMemberName(userId, members) {
  const m = (members || []).find(m => m.id === userId);
  return m?.name || m?.email || userId?.slice(0, 8) || '?';
}

// ── Estilos ───────────────────────────────────────────────────────────────────
const FF = '"IBM Plex Mono", monospace';
const C  = { bg: '#0a0a0a', border: '#1e1e1e', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const S = {
  root:         { display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', fontFamily: FF, background: C.bg },
  topbar:       { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', borderBottom: `2px solid ${C.border}`, gap: '12px', flexWrap: 'wrap', flexShrink: 0 },
  newBtn:       { background: C.accent, border: 'none', color: '#000', padding: '6px 14px', cursor: 'pointer', fontSize: '10px', fontWeight: 700, fontFamily: FF, letterSpacing: '0.5px', flexShrink: 0 },
  searchWrap:   { display: 'flex', alignItems: 'center', background: '#111', border: `1px solid #222`, height: '30px' },
  searchInp:    { background: 'transparent', border: 'none', color: C.text, fontSize: '11px', fontFamily: FF, outline: 'none', padding: '0 4px', width: '220px' },
  clearBtn:     { background: 'transparent', border: 'none', color: C.dim, cursor: 'pointer', padding: '0 6px', fontSize: '11px' },
  legend:       { display: 'flex', gap: '16px', padding: '8px 16px', background: '#0a0a0a', borderBottom: `1px solid ${C.border}`, flexWrap: 'wrap', alignItems: 'center', flexShrink: 0 },
  loading:      { color: C.dim, fontSize: '11px', padding: '20px 16px' },
  matrixWrap:   { flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0' },
  row:          { display: 'flex', borderBottom: `1px solid ${C.border}`, minHeight: '52px' },
  entityCell:   { minWidth: '240px', maxWidth: '300px', borderLeft: '3px solid #64748b', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: '4px', justifyContent: 'center', background: '#0a0a0a', flexShrink: 0 },
  levelTag:     { display: 'inline-block', fontSize: '8px', padding: '1px 5px', letterSpacing: '1px', fontWeight: 700, alignSelf: 'flex-start' },
  entityName:   { color: C.text, fontSize: '12px', fontWeight: 600 },
  assignBtn:    { background: 'transparent', border: `1px dashed #1e3a5f`, color: '#2a5a8f', padding: '2px 8px', cursor: 'pointer', fontSize: '9px', fontFamily: FF, marginTop: '2px', alignSelf: 'flex-start' },
  employeesCell:{ flex: 1, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '6px', padding: '8px 12px' },
  noEmployees:  { color: '#1e2a2a', fontSize: '10px', fontStyle: 'italic' },
  empChip:      { display: 'flex', alignItems: 'center', gap: '6px', background: '#0f1a1a', border: `1px solid #1a2a2a`, padding: '4px 10px 4px 6px', position: 'relative' },
  empAvatar:    { width: '24px', height: '24px', background: '#1a2a3a', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '9px', color: C.accent, fontWeight: 700, flexShrink: 0 },
  empInfo:      { display: 'flex', flexDirection: 'column', gap: '1px' },
  empName:      { color: C.text, fontSize: '11px' },
  empRole:      { color: C.dim, fontSize: '9px' },
  unlinkBtn:    { background: 'transparent', border: 'none', color: '#333', cursor: 'pointer', fontSize: '10px', padding: '0 2px', marginLeft: '4px' },
};

const M = {
  overlay:   { position: 'fixed', inset: 0, background: 'rgba(0,0,0,.88)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  box:       { background: '#111', border: `2px solid #222`, width: '100%', maxWidth: '480px', fontFamily: FF },
  hdr:       { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '14px 16px', borderBottom: '1px solid #1a1a1a' },
  htitle:    { color: C.accent, fontSize: '12px', fontWeight: 700, letterSpacing: '2px' },
  xbtn:      { background: 'transparent', border: 'none', color: C.dim, cursor: 'pointer', fontSize: '18px' },
  btnCancel: { background: 'transparent', border: '1px solid #333', color: C.dim, padding: '7px 14px', cursor: 'pointer', fontSize: '11px', fontFamily: FF },
  btnOk:     { background: C.accent, border: 'none', color: '#000', padding: '7px 18px', cursor: 'pointer', fontSize: '11px', fontWeight: 700, fontFamily: FF },
  lvlBtn:    { display: 'flex', alignItems: 'center', background: '#0f0f0f', border: '1px solid #2a2a2a', color: '#64748b', padding: '5px 10px', cursor: 'pointer', fontSize: '9px', fontFamily: FF, letterSpacing: '0.5px' },
};

const F = {
  wrap:   { display: 'flex', flexDirection: 'column', gap: '4px' },
  label:  { color: C.dim, fontSize: '9px', letterSpacing: '2px', fontWeight: 700 },
  inp:    { background: '#1a1a1a', border: `1px solid #2a2a2a`, color: C.text, padding: '8px 10px', fontSize: '12px', fontFamily: FF, outline: 'none', width: '100%', boxSizing: 'border-box' },
  optRow: { display: 'flex', alignItems: 'center', padding: '8px 12px', cursor: 'pointer', fontSize: '11px', fontFamily: FF, borderBottom: '1px solid #1a1a1a', transition: 'background .1s', userSelect: 'none' },
};

