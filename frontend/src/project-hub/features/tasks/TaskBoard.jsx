/* ============================================================
   TaskBoard.jsx — Vista principal de tareas
   Kanban + Lista, toggle entre vistas
   ============================================================ */
import { useState, useEffect } from 'react';
import KanbanView from './KanbanView';
import ListView   from './ListView';
import TaskModal  from './TaskModal';

const STATUSES = [
  { id: 'todo',        label: 'POR HACER',    color: '#64748b' },
  { id: 'in_progress', label: 'EN PROGRESO',  color: '#0EA5E9' },
  { id: 'review',      label: 'EN REVISIÓN',  color: '#F59E0B' },
  { id: 'done',        label: 'COMPLETADO',   color: '#10B981' },
];

export default function TaskBoard({ project, workspace, user }) {
  const [view, setView]         = useState('kanban'); // 'kanban' | 'list'
  const [tasks, setTasks]       = useState([]);
  const [members, setMembers]   = useState([]);
  const [loading, setLoading]   = useState(false);
  const [modal, setModal]       = useState(null); // null | 'new' | task-object

  const API = 'http://localhost:8000/api/hub';

  const loadTasks = async () => {
    if (!project) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/tasks?project_id=${project.id}`);
      setTasks(await r.json());
    } finally { setLoading(false); }
  };

  const loadMembers = async () => {
    if (!workspace) return;
    const r = await fetch(`${API}/users?workspace_id=${workspace.id}`);
    setMembers(await r.json());
  };

  useEffect(() => { loadTasks(); loadMembers(); }, [project?.id]);

  const handleStatusChange = async (taskId, newStatus) => {
    setTasks(ts => ts.map(t => t.id === taskId ? { ...t, status: newStatus } : t));
    await fetch(`${API}/tasks/${taskId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    });
  };

  const handleSaveTask = async (formData) => {
    if (modal === 'new') {
      const r = await fetch(`${API}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...formData, workspace_id: workspace.id, project_id: project.id, created_by: user?.id }),
      });
      const { task } = await r.json();
      setTasks(ts => [...ts, { ...task, assignees: [] }]);
    } else {
      const r = await fetch(`${API}/tasks/${modal.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const { task } = await r.json();
      setTasks(ts => ts.map(t => t.id === task.id ? { ...t, ...task } : t));
    }
    setModal(null);
  };

  const handleDeleteTask = async (taskId) => {
    await fetch(`${API}/tasks/${taskId}`, { method: 'DELETE' });
    setTasks(ts => ts.filter(t => t.id !== taskId));
    setModal(null);
  };

  if (!project) return (
    <div style={styles.empty}>
      <p style={styles.emptyText}>◈ Selecciona un proyecto en el panel izquierdo</p>
    </div>
  );

  return (
    <div style={styles.root}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.projectInfo}>
          <div style={{ ...styles.projectDot, background: project.color || '#0EA5E9' }} />
          <h2 style={styles.projectTitle}>{project.name}</h2>
          <span style={styles.taskCount}>{tasks.length} tareas</span>
        </div>
        <div style={styles.actions}>
          {/* Toggle vista */}
          <div style={styles.toggle}>
            <button style={{ ...styles.toggleBtn, ...(view === 'kanban' ? styles.toggleActive : {}) }}
              onClick={() => setView('kanban')}>⬛ KANBAN</button>
            <button style={{ ...styles.toggleBtn, ...(view === 'list' ? styles.toggleActive : {}) }}
              onClick={() => setView('list')}>☰ LISTA</button>
          </div>
          <button style={styles.newBtn} onClick={() => setModal('new')}>
            + NUEVA TAREA
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div style={styles.statsBar}>
        {STATUSES.map(s => {
          const count = tasks.filter(t => t.status === s.id).length;
          return (
            <div key={s.id} style={styles.stat}>
              <span style={{ ...styles.statDot, background: s.color }} />
              <span style={styles.statLabel}>{s.label}</span>
              <span style={{ ...styles.statCount, color: s.color }}>{count}</span>
            </div>
          );
        })}
      </div>

      {/* Board */}
      {loading ? (
        <div style={styles.loading}>CARGANDO TAREAS...</div>
      ) : view === 'kanban' ? (
        <KanbanView
          tasks={tasks} statuses={STATUSES} members={members}
          onStatusChange={handleStatusChange}
          onTaskClick={setModal}
          onNewTask={() => setModal('new')}
        />
      ) : (
        <ListView
          tasks={tasks} statuses={STATUSES} members={members}
          onStatusChange={handleStatusChange}
          onTaskClick={setModal}
        />
      )}

      {/* Modal */}
      {modal !== null && (
        <TaskModal
          task={modal === 'new' ? null : modal}
          members={members}
          onSave={handleSaveTask}
          onDelete={handleDeleteTask}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  );
}

const C = { bg: '#0a0a0a', panel: '#111', border: '#0EA5E9', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  root: { display: 'flex', flexDirection: 'column', height: '100%', background: C.bg },
  empty: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  emptyText: { color: C.dim, fontSize: '14px', fontFamily: '"IBM Plex Mono", monospace' },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '16px 20px', borderBottom: `2px solid #222`, flexShrink: 0,
  },
  projectInfo: { display: 'flex', alignItems: 'center', gap: '12px' },
  projectDot: { width: '12px', height: '12px' },
  projectTitle: { color: C.text, fontSize: '16px', fontWeight: 700, margin: 0, fontFamily: '"IBM Plex Mono", monospace' },
  taskCount: { color: C.dim, fontSize: '11px', fontFamily: '"IBM Plex Mono", monospace' },
  actions: { display: 'flex', alignItems: 'center', gap: '12px' },
  toggle: { display: 'flex', border: `2px solid #333`, overflow: 'hidden' },
  toggleBtn: {
    background: 'transparent', border: 'none', color: C.dim, padding: '6px 12px',
    cursor: 'pointer', fontSize: '11px', fontFamily: '"IBM Plex Mono", monospace',
    letterSpacing: '1px',
  },
  toggleActive: { background: C.accent, color: '#000', fontWeight: 700 },
  newBtn: {
    background: C.accent, border: 'none', color: '#000', padding: '8px 16px',
    cursor: 'pointer', fontSize: '12px', fontWeight: 700, letterSpacing: '1px',
    fontFamily: '"IBM Plex Mono", monospace', boxShadow: `2px 2px 0 #0369a1`,
  },
  statsBar: {
    display: 'flex', gap: '24px', padding: '10px 20px',
    borderBottom: `1px solid #1a1a1a`, flexShrink: 0,
  },
  stat: { display: 'flex', alignItems: 'center', gap: '6px' },
  statDot: { width: '8px', height: '8px' },
  statLabel: { color: C.dim, fontSize: '10px', letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace' },
  statCount: { fontSize: '12px', fontWeight: 700, fontFamily: '"IBM Plex Mono", monospace' },
  loading: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.dim, fontFamily: '"IBM Plex Mono", monospace' },
};
