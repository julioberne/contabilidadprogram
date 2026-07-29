/* ============================================================
   TasksOverview.jsx — COMPENDIO de tareas del workspace
   Vista global: quién trabaja en qué tarea, de qué empresa/proyecto
   es y en qué estado. Filtrable por empresa, persona y estado.
   GET /hub/tasks/overview?workspace_id=
   ============================================================ */
import { useState, useEffect, useMemo } from 'react';
import { API_HUB } from '../../../config';

const STATUS = {
  todo:        { label: 'POR HACER',   color: '#64748b' },
  in_progress: { label: 'EN PROGRESO', color: '#0EA5E9' },
  review:      { label: 'EN REVISIÓN', color: '#F59E0B' },
  done:        { label: 'COMPLETADO',  color: '#10B981' },
};
const PRIORITY = {
  low:    { label: 'BAJA',    color: '#10B981' },
  medium: { label: 'MEDIA',   color: '#0EA5E9' },
  high:   { label: 'ALTA',    color: '#F59E0B' },
  urgent: { label: 'URGENTE', color: '#EF4444' },
};

function fmtDate(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }); }
  catch { return '—'; }
}

export default function TasksOverview({ workspace, user }) {
  const [tasks, setTasks]       = useState([]);
  const [entities, setEntities] = useState([]); // roster completo de empresas del workspace
  const [members, setMembers]   = useState([]); // roster completo de personas del workspace
  const [loading, setLoading]   = useState(false);
  const [fEstado, setFEstado]   = useState('all');
  const [fEmpresa, setFEmpresa] = useState('all');
  const [fPersona, setFPersona] = useState('all');

  // Las opciones de EMPRESA/PERSONA vienen del roster real del workspace
  // (entidades y miembros), no solo de lo que ya aparece en tareas — así el
  // filtro muestra empresas/personas aunque todavía no tengan tareas asignadas.
  useEffect(() => {
    if (!workspace) return;
    setLoading(true);
    Promise.all([
      fetch(`${API_HUB}/tasks/overview?workspace_id=${workspace.id}`).then(r => r.json()),
      fetch(`${API_HUB}/entities?workspace_id=${workspace.id}`).then(r => r.json()),
      fetch(`${API_HUB}/users?workspace_id=${workspace.id}`).then(r => r.json()),
    ])
      .then(([tk, ent, usr]) => {
        setTasks(Array.isArray(tk) ? tk : []);
        setEntities(Array.isArray(ent) ? ent : []);
        setMembers(Array.isArray(usr) ? usr : []);
      })
      .catch(() => { setTasks([]); setEntities([]); setMembers([]); })
      .finally(() => setLoading(false));
  }, [workspace?.id]);

  // Opciones de filtro: roster completo, con fallback a lo visto en tareas
  // (por si una tarea referencia una empresa/persona fuera del roster actual).
  const empresas = useMemo(() => {
    const map = new Map(entities.map(e => [e.id, e.name]));
    tasks.forEach(t => { if (t.entity_id && !map.has(t.entity_id)) map.set(t.entity_id, t.entity_name); });
    return [...map.entries()].sort((a, b) => (a[1] || '').localeCompare(b[1] || ''));
  }, [entities, tasks]);

  const personas = useMemo(() => {
    const map = new Map(members.map(m => [m.id, m]));
    tasks.forEach(t => (t.assignees || []).forEach(a => { if (!map.has(a.id)) map.set(a.id, a); }));
    return [...map.values()].sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  }, [members, tasks]);

  const filtered = useMemo(() => tasks.filter(t => {
    if (fEstado !== 'all' && t.status !== fEstado) return false;
    if (fEmpresa !== 'all' && t.entity_id !== fEmpresa) return false;
    if (fPersona !== 'all' && !(t.assignees || []).some(a => a.id === fPersona)) return false;
    return true;
  }), [tasks, fEstado, fEmpresa, fPersona]);

  const counts = useMemo(() => {
    const c = { todo: 0, in_progress: 0, review: 0, done: 0 };
    tasks.forEach(t => { if (c[t.status] != null) c[t.status]++; });
    return c;
  }, [tasks]);

  if (!workspace) return (
    <div style={S.empty}>◈ Selecciona un workspace</div>
  );

  return (
    <div style={S.root}>
      {/* Header */}
      <div style={S.header}>
        <div>
          <h2 style={S.title}>▤ COMPENDIO DE TAREAS</h2>
          <p style={S.sub}>Panorama de {workspace.name} · quién trabaja en qué, para qué empresa y en qué estado</p>
        </div>
        <div style={S.total}>{filtered.length}<span style={S.totalLbl}>tareas</span></div>
      </div>

      {/* Resumen por estado */}
      <div style={S.statsBar}>
        {Object.entries(STATUS).map(([k, s]) => (
          <button key={k}
            style={{ ...S.stat, ...(fEstado === k ? { borderColor: s.color } : {}) }}
            onClick={() => setFEstado(fEstado === k ? 'all' : k)}
            title="Filtrar por este estado">
            <span style={{ ...S.statDot, background: s.color }} />
            <span style={S.statLabel}>{s.label}</span>
            <span style={{ ...S.statCount, color: s.color }}>{counts[k]}</span>
          </button>
        ))}
      </div>

      {/* Filtros */}
      <div style={S.filters}>
        <div style={S.filterGroup}>
          <span style={S.filterLabel}>EMPRESA</span>
          <select style={S.select} value={fEmpresa} onChange={e => setFEmpresa(e.target.value)}>
            <option value="all">Todas</option>
            {empresas.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </select>
        </div>
        <div style={S.filterGroup}>
          <span style={S.filterLabel}>PERSONA</span>
          <select style={S.select} value={fPersona} onChange={e => setFPersona(e.target.value)}>
            <option value="all">Todas</option>
            {personas.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        {(fEstado !== 'all' || fEmpresa !== 'all' || fPersona !== 'all') && (
          <button style={S.clearBtn} onClick={() => { setFEstado('all'); setFEmpresa('all'); setFPersona('all'); }}>
            ✕ LIMPIAR
          </button>
        )}
      </div>

      {/* Tabla */}
      <div style={S.tableWrap}>
        {loading ? (
          <div style={S.msg}>CARGANDO...</div>
        ) : filtered.length === 0 ? (
          <div style={S.msg}>Sin tareas para este filtro.</div>
        ) : (
          <table style={S.table}>
            <thead>
              <tr>
                <th style={S.th}>TAREA</th>
                <th style={S.th}>EMPRESA</th>
                <th style={S.th}>PROYECTO</th>
                <th style={S.th}>ASIGNADOS</th>
                <th style={S.th}>PRIORIDAD</th>
                <th style={S.th}>ESTADO</th>
                <th style={S.th}>VENCE</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(t => {
                const st = STATUS[t.status] || STATUS.todo;
                const pr = PRIORITY[t.priority] || PRIORITY.medium;
                return (
                  <tr key={t.id} style={S.tr}>
                    <td style={{ ...S.td, ...S.tdTitle }}>
                      <span style={{ ...S.projDot, background: t.project_color || '#0EA5E9' }} />
                      {t.title}
                    </td>
                    <td style={S.td}>{t.entity_name || <em style={S.none}>—</em>}</td>
                    <td style={S.td}>{t.project_name || <em style={S.none}>—</em>}</td>
                    <td style={S.td}>
                      <div style={S.avatars}>
                        {(t.assignees || []).length === 0
                          ? <em style={S.none}>sin asignar</em>
                          : t.assignees.map(a => (
                              <span key={a.id} style={{ ...S.avatar, background: a.color || '#0EA5E9' }} title={a.name}>
                                {(a.name || '?').slice(0, 2).toUpperCase()}
                              </span>
                            ))}
                      </div>
                    </td>
                    <td style={S.td}>
                      <span style={{ ...S.tag, color: pr.color, borderColor: pr.color }}>{pr.label}</span>
                    </td>
                    <td style={S.td}>
                      <span style={{ ...S.tag, color: st.color, borderColor: st.color }}>{st.label}</span>
                    </td>
                    <td style={{ ...S.td, color: t.is_overdue ? '#EF4444' : '#94a3b8' }}>
                      {t.is_overdue && '⚠ '}{fmtDate(t.due_date)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

const FF = '"IBM Plex Mono", monospace';
const C = { bg: '#0a0a0a', panel: '#111', accent: '#0EA5E9', text: '#e2e8f0', dim: '#64748b' };
const S = {
  root:   { display: 'flex', flexDirection: 'column', height: '100%', background: C.bg, fontFamily: FF, overflow: 'hidden' },
  empty:  { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.dim, fontFamily: FF },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '16px 20px', borderBottom: '2px solid #222', flexShrink: 0 },
  title:  { color: C.accent, fontSize: 15, margin: 0, letterSpacing: 1.5 },
  sub:    { color: C.dim, fontSize: 11, margin: '4px 0 0' },
  total:  { color: C.text, fontSize: 24, fontWeight: 700, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', lineHeight: 1 },
  totalLbl:{ color: C.dim, fontSize: 9, letterSpacing: 1 },
  statsBar:{ display: 'flex', gap: 8, padding: '12px 20px', borderBottom: '1px solid #1a1a1a', flexShrink: 0, flexWrap: 'wrap' },
  stat:   { display: 'flex', alignItems: 'center', gap: 6, background: '#111', border: '2px solid #222', padding: '6px 12px', cursor: 'pointer', fontFamily: FF },
  statDot:{ width: 8, height: 8, flexShrink: 0 },
  statLabel:{ color: C.dim, fontSize: 10, letterSpacing: 1 },
  statCount:{ fontSize: 13, fontWeight: 700 },
  filters:{ display: 'flex', gap: 16, padding: '12px 20px', alignItems: 'flex-end', flexShrink: 0, flexWrap: 'wrap' },
  filterGroup:{ display: 'flex', flexDirection: 'column', gap: 4 },
  filterLabel:{ color: C.dim, fontSize: 9, letterSpacing: 1 },
  select: { background: '#1a1a1a', border: '2px solid #333', color: C.text, padding: '6px 10px', fontSize: 12, fontFamily: FF, outline: 'none', cursor: 'pointer', minWidth: 160 },
  clearBtn:{ background: 'transparent', border: '1px solid #333', color: C.dim, padding: '7px 12px', cursor: 'pointer', fontSize: 11, fontFamily: FF },
  tableWrap:{ flex: 1, overflow: 'auto', padding: '0 20px 20px' },
  table:  { width: '100%', borderCollapse: 'collapse', fontFamily: FF },
  th:     { textAlign: 'left', color: C.dim, fontSize: 9, letterSpacing: 1.5, fontWeight: 700, padding: '10px 10px', borderBottom: '2px solid #222', position: 'sticky', top: 0, background: C.bg, whiteSpace: 'nowrap' },
  tr:     { borderBottom: '1px solid #161616' },
  td:     { padding: '10px 10px', fontSize: 12, color: C.text, verticalAlign: 'middle' },
  tdTitle:{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 },
  projDot:{ width: 8, height: 8, flexShrink: 0 },
  none:   { color: '#475569', fontStyle: 'normal' },
  avatars:{ display: 'flex', gap: 4, flexWrap: 'wrap' },
  avatar: { width: 22, height: 22, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontSize: 9, fontWeight: 700, fontFamily: FF, flexShrink: 0 },
  tag:    { fontSize: 9, border: '1px solid', padding: '2px 6px', fontWeight: 700, letterSpacing: 0.5, whiteSpace: 'nowrap' },
  msg:    { color: C.dim, fontSize: 13, textAlign: 'center', padding: 40 },
};
