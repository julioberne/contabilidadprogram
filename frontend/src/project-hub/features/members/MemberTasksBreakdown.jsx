/* ============================================================
   MemberTasksBreakdown.jsx — Detalle de tareas de una persona
   Lista real agrupada por estado (vencidas / en progreso / hechas),
   cada tarea con su proyecto y empresa, y resumen desplegable.
   Alimentado por GET /api/hub/users/{id}/tasks?workspace_id=
   ============================================================ */
import { useState, useEffect } from 'react';
import { API_HUB } from '../../../config';

const STATUS_LABEL = {
  todo: 'POR HACER', in_progress: 'EN PROGRESO', review: 'EN REVISIÓN', done: 'HECHA',
};
const PRIORITY_COLOR = { low: '#64748b', medium: '#0EA5E9', high: '#F59E0B', urgent: '#EF4444' };

const fmtDate = (d) => d
  ? new Date(d).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })
  : '—';

export default function MemberTasksBreakdown({ member, workspace }) {
  const [tasks,   setTasks]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');
  const [openId,  setOpenId]  = useState(null);

  useEffect(() => {
    if (!member?.id || !workspace?.id) return;
    let alive = true;
    setLoading(true); setError('');
    fetch(`${API_HUB}/users/${member.id}/tasks?workspace_id=${workspace.id}`)
      .then(r => { if (!r.ok) throw new Error(`Error ${r.status}`); return r.json(); })
      .then(data => { if (alive) setTasks(Array.isArray(data) ? data : []); })
      .catch(e => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [member?.id, workspace?.id]);

  if (loading) return <p style={S.dim}>Cargando tareas…</p>;
  if (error)   return <p style={{ ...S.dim, color: '#EF4444' }}>No se pudieron cargar las tareas: {error}</p>;
  if (tasks.length === 0) return <p style={S.dim}>Sin tareas asignadas todavía.</p>;

  const overdue    = tasks.filter(t => t.is_overdue);
  const inProgress = tasks.filter(t => !t.is_overdue && t.status !== 'done');
  const done       = tasks.filter(t => !t.is_overdue && t.status === 'done');

  const groups = [
    { key: 'overdue', label: 'VENCIDAS',    color: '#EF4444', items: overdue },
    { key: 'prog',    label: 'EN PROGRESO', color: '#0EA5E9', items: inProgress },
    { key: 'done',    label: 'COMPLETADAS', color: '#10B981', items: done },
  ];

  return (
    <div>
      <div style={S.sectionHeader}>
        <span style={S.sectionLabel}>DESGLOSE DE TAREAS</span>
        <span style={S.count}>{tasks.length} en total</span>
      </div>

      {groups.map(g => g.items.length === 0 ? null : (
        <div key={g.key} style={S.group}>
          <div style={S.groupHead}>
            <span style={{ ...S.dot, background: g.color }} />
            <span style={{ ...S.groupLabel, color: g.color }}>{g.label}</span>
            <span style={S.groupCount}>{g.items.length}</span>
          </div>

          {g.items.map(t => {
            const open = openId === t.id;
            return (
              <div key={t.id} style={S.task}>
                <button style={S.taskRow} onClick={() => setOpenId(open ? null : t.id)}>
                  <span style={{ ...S.prio, background: PRIORITY_COLOR[t.priority] || '#64748b' }} />
                  <span style={S.title}>{t.title}</span>
                  <span style={S.tags}>
                    {t.project_name && <span style={S.tag}>◈ {t.project_name}</span>}
                    {t.entity_name  && <span style={S.tagCompany}>▦ {t.entity_name}</span>}
                  </span>
                  <span style={S.chevron}>{open ? '▾' : '▸'}</span>
                </button>

                {open && (
                  <div style={S.detail}>
                    {t.description
                      ? <p style={S.desc}>{t.description}</p>
                      : <p style={{ ...S.desc, fontStyle: 'italic', color: '#475569' }}>Sin descripción.</p>}
                    <div style={S.detailMeta}>
                      <span style={S.metaChip}>Estado: <b style={{ color: '#e2e8f0' }}>{STATUS_LABEL[t.status] || t.status}</b></span>
                      <span style={S.metaChip}>Vence: <b style={{ color: t.is_overdue ? '#EF4444' : '#e2e8f0' }}>{fmtDate(t.due_date)}</b></span>
                      {t.completed_at && <span style={S.metaChip}>Completada: <b style={{ color: '#10B981' }}>{fmtDate(t.completed_at)}</b></span>}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

const S = {
  dim:        { color: '#64748b', fontSize: '12px', padding: '8px 0' },
  sectionHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' },
  sectionLabel:  { color: '#64748b', fontSize: '10px', letterSpacing: '2px' },
  count:      { color: '#64748b', fontSize: '11px' },
  group:      { marginBottom: '16px' },
  groupHead:  { display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' },
  dot:        { width: '8px', height: '8px', flexShrink: 0 },
  groupLabel: { fontSize: '10px', letterSpacing: '1.5px', fontWeight: 700 },
  groupCount: { color: '#64748b', fontSize: '10px' },
  task:       { borderLeft: '1px solid #1e1e1e', marginLeft: '3px' },
  taskRow:    { width: '100%', display: 'flex', alignItems: 'center', gap: '10px', background: 'transparent', border: 'none', borderBottom: '1px solid #141414', padding: '9px 8px', cursor: 'pointer', textAlign: 'left', fontFamily: '"IBM Plex Mono", monospace' },
  prio:       { width: '4px', height: '16px', flexShrink: 0 },
  title:      { color: '#e2e8f0', fontSize: '12px', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  tags:       { display: 'flex', gap: '6px', flexShrink: 0, maxWidth: '50%', overflow: 'hidden' },
  tag:        { color: '#64748b', fontSize: '10px', border: '1px solid #1e1e1e', padding: '1px 6px', whiteSpace: 'nowrap' },
  tagCompany: { color: '#8B5CF6', fontSize: '10px', border: '1px solid #2a2140', padding: '1px 6px', whiteSpace: 'nowrap' },
  chevron:    { color: '#64748b', fontSize: '11px', flexShrink: 0, width: '12px' },
  detail:     { padding: '8px 8px 14px 22px', background: '#0d0d0d' },
  desc:       { color: '#94a3b8', fontSize: '12px', lineHeight: 1.6, margin: '0 0 10px' },
  detailMeta: { display: 'flex', gap: '14px', flexWrap: 'wrap' },
  metaChip:   { color: '#64748b', fontSize: '11px' },
};
