/* ============================================================
   ListView.jsx — Vista de lista de tareas (tabla sorteable)
   ============================================================ */
import { useState } from 'react';

const PRIORITY_COLORS = { low: '#10B981', medium: '#0EA5E9', high: '#F59E0B', urgent: '#EF4444' };
const PRIORITY_LABELS = { low: 'BAJA', medium: 'MEDIA', high: 'ALTA', urgent: 'URGENTE' };

export default function ListView({ tasks, statuses, members, onStatusChange, onTaskClick }) {
  const [sortBy, setSortBy]   = useState('created_at');
  const [filterStatus, setFilter] = useState('all');

  const statusMap = Object.fromEntries(statuses.map(s => [s.id, s]));

  const filtered = tasks
    .filter(t => filterStatus === 'all' || t.status === filterStatus)
    .sort((a, b) => {
      if (sortBy === 'due_date') return (a.due_date || 'z').localeCompare(b.due_date || 'z');
      if (sortBy === 'priority') {
        const order = { urgent: 0, high: 1, medium: 2, low: 3 };
        return (order[a.priority] || 2) - (order[b.priority] || 2);
      }
      return 0;
    });

  return (
    <div style={styles.root}>
      {/* Filtros */}
      <div style={styles.filters}>
        <select value={filterStatus} onChange={e => setFilter(e.target.value)} style={styles.select}>
          <option value="all">Todos los estados</option>
          {statuses.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
        <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={styles.select}>
          <option value="created_at">Orden: Creación</option>
          <option value="due_date">Orden: Vencimiento</option>
          <option value="priority">Orden: Prioridad</option>
        </select>
        <span style={styles.count}>{filtered.length} tareas</span>
      </div>

      {/* Tabla */}
      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr style={styles.thead}>
              <th style={{ ...styles.th, width: '36px' }} />
              <th style={{ ...styles.th, textAlign: 'left' }}>TAREA</th>
              <th style={styles.th}>ESTADO</th>
              <th style={styles.th}>PRIORIDAD</th>
              <th style={styles.th}>ASIGNADOS</th>
              <th style={styles.th}>VENCE</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(task => {
              const status = statusMap[task.status];
              const overdue = task.due_date && new Date(task.due_date) < new Date() && task.status !== 'done';
              return (
                <tr key={task.id} style={styles.row} onClick={() => onTaskClick(task)}>
                  {/* Priority bar */}
                  <td style={{ ...styles.td, padding: 0 }}>
                    <div style={{ width: '4px', height: '100%', minHeight: '40px', background: PRIORITY_COLORS[task.priority] }} />
                  </td>
                  {/* Title */}
                  <td style={{ ...styles.td, textAlign: 'left' }}>
                    <span style={styles.taskTitle}>{task.title}</span>
                    {task.description && (
                      <span style={styles.taskDesc}> — {task.description.slice(0, 50)}{task.description.length > 50 ? '…' : ''}</span>
                    )}
                  </td>
                  {/* Status */}
                  <td style={styles.td}>
                    <span style={{ ...styles.statusBadge, color: status?.color, borderColor: status?.color }}>
                      {status?.label || task.status}
                    </span>
                  </td>
                  {/* Priority */}
                  <td style={styles.td}>
                    <span style={{ color: PRIORITY_COLORS[task.priority], fontSize: '10px', letterSpacing: '1px' }}>
                      {PRIORITY_LABELS[task.priority]}
                    </span>
                  </td>
                  {/* Assignees */}
                  <td style={styles.td}>
                    <div style={styles.avatars}>
                      {(task.assignees || []).slice(0, 3).map((a, i) => (
                        <div key={a.id} style={{
                          ...styles.avatar, background: a.color || '#0EA5E9',
                          zIndex: 10 - i, marginLeft: i > 0 ? '-6px' : 0,
                        }} title={a.name}>
                          {a.name?.slice(0, 2).toUpperCase()}
                        </div>
                      ))}
                    </div>
                  </td>
                  {/* Due date */}
                  <td style={{ ...styles.td, color: overdue ? '#ef4444' : '#64748b' }}>
                    {task.due_date
                      ? new Date(task.due_date).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' })
                      : '—'}
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} style={{ ...styles.td, textAlign: 'center', color: '#64748b', padding: '32px' }}>
                  Sin tareas en esta vista
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const C = { bg: '#0a0a0a', row: '#111', border: '#1e1e1e', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  root: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  filters: {
    display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 20px',
    borderBottom: `1px solid ${C.border}`, flexShrink: 0,
  },
  select: {
    background: '#1a1a1a', border: `2px solid #333`, color: C.text,
    padding: '6px 10px', fontSize: '11px', fontFamily: '"IBM Plex Mono", monospace',
    cursor: 'pointer', outline: 'none',
  },
  count: { color: C.dim, fontSize: '11px', fontFamily: '"IBM Plex Mono", monospace', marginLeft: 'auto' },
  tableWrap: { flex: 1, overflowY: 'auto', padding: '0 20px 20px' },
  table: { width: '100%', borderCollapse: 'collapse' },
  thead: { position: 'sticky', top: 0, background: C.bg },
  th: {
    color: C.dim, fontSize: '10px', letterSpacing: '2px', padding: '12px 12px',
    fontFamily: '"IBM Plex Mono", monospace', fontWeight: 600, borderBottom: `2px solid ${C.border}`,
    textAlign: 'center',
  },
  row: {
    borderBottom: `1px solid ${C.border}`, cursor: 'pointer',
    transition: 'background .1s',
  },
  td: {
    padding: '12px', color: C.text, fontSize: '12px',
    fontFamily: '"IBM Plex Mono", monospace', verticalAlign: 'middle', textAlign: 'center',
  },
  taskTitle: { fontWeight: 600 },
  taskDesc: { color: C.dim, fontWeight: 400 },
  statusBadge: {
    border: '1px solid', padding: '2px 8px', fontSize: '10px',
    letterSpacing: '1px', whiteSpace: 'nowrap',
  },
  avatars: { display: 'flex', alignItems: 'center', justifyContent: 'center' },
  avatar: {
    width: '22px', height: '22px', borderRadius: '50%',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#000', fontSize: '8px', fontWeight: 700, border: `2px solid ${C.bg}`,
    fontFamily: '"IBM Plex Mono", monospace',
  },
};
