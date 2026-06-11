/* ============================================================
   HubSidebar.jsx — Sidebar del Project Hub
   Incluye: workspace switcher, árbol de entidades/proyectos,
   navegación principal (Tareas / Notas / Calendario / Miembros)
   ============================================================ */
import { useState, useEffect } from 'react';
import WorkspaceSwitcher from './WorkspaceSwitcher';

const NAV = [
  { id: 'tasks',    icon: '◈', label: 'TAREAS' },
  { id: 'notes',    icon: '◉', label: 'NOTAS' },
  { id: 'calendar', icon: '◷', label: 'CALENDARIO' },
  { id: 'members',  icon: '◎', label: 'EQUIPO' },
  { id: 'settings', icon: '◬', label: 'AJUSTES' },
];

export default function HubSidebar({
  user, workspace, workspaces,
  onSwitchWorkspace, onCreateWorkspace,
  activeView, onChangeView,
  activeProject, onSelectProject,
}) {
  const [entities, setEntities]   = useState([]);
  const [projects, setProjects]   = useState([]);
  const [expanded, setExpanded]   = useState({});
  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');

  // Cargar árbol de entidades
  useEffect(() => {
    if (!workspace) return;
    fetch(`http://localhost:8000/api/hub/entities?workspace_id=${workspace.id}`)
      .then(r => r.json()).then(setEntities).catch(() => {});
    fetch(`http://localhost:8000/api/hub/projects?workspace_id=${workspace.id}`)
      .then(r => r.json()).then(setProjects).catch(() => {});
  }, [workspace]);

  const toggle = (id) => setExpanded(e => ({ ...e, [id]: !e[id] }));

  const createProject = async () => {
    if (!newProjectName.trim()) return;
    const res = await fetch('http://localhost:8000/api/hub/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workspace_id: workspace.id, name: newProjectName.trim(),
        created_by: user?.id,
      }),
    });
    const { project } = await res.json();
    setProjects(p => [...p, project]);
    setNewProjectName(''); setShowNewProject(false);
    onSelectProject(project);
  };

  return (
    <div style={styles.sidebar}>
      {/* Workspace Switcher */}
      <WorkspaceSwitcher
        workspace={workspace} workspaces={workspaces}
        onSwitch={onSwitchWorkspace} onCreate={onCreateWorkspace}
      />

      {/* Navegación principal */}
      <nav style={styles.nav}>
        {NAV.map(n => (
          <button key={n.id}
            style={{ ...styles.navItem, ...(activeView === n.id ? styles.navActive : {}) }}
            onClick={() => onChangeView(n.id)}>
            <span style={styles.navIcon}>{n.icon}</span>
            <span>{n.label}</span>
          </button>
        ))}
      </nav>

      {/* Proyectos */}
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span style={styles.sectionLabel}>PROYECTOS</span>
          <button style={styles.addBtn} onClick={() => setShowNewProject(v => !v)}>+</button>
        </div>

        {showNewProject && (
          <div style={styles.newProject}>
            <input
              placeholder="Nombre del proyecto..."
              value={newProjectName}
              onChange={e => setNewProjectName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && createProject()}
              style={styles.input} autoFocus
            />
            <button onClick={createProject} style={styles.btnCreate}>✓</button>
          </div>
        )}

        <div style={styles.projectList}>
          {projects.map(p => (
            <button key={p.id}
              style={{
                ...styles.projectItem,
                ...(activeProject?.id === p.id ? styles.projectActive : {}),
              }}
              onClick={() => { onSelectProject(p); onChangeView('tasks'); }}>
              <span style={{ ...styles.projectDot, background: p.color || '#0EA5E9' }} />
              <span style={styles.projectName}>{p.name}</span>
            </button>
          ))}
          {projects.length === 0 && (
            <p style={styles.emptyMsg}>Sin proyectos aún</p>
          )}
        </div>
      </div>

      {/* Footer — usuario activo */}
      <div style={styles.footer}>
        <div style={{ ...styles.userAvatar, background: user?.color || '#0EA5E9' }}>
          {user?.name?.slice(0, 2).toUpperCase() || '??'}
        </div>
        <div style={styles.userInfo}>
          <span style={styles.userName}>{user?.name}</span>
          <span style={styles.userRole}>{user?.role?.toUpperCase()}</span>
        </div>
      </div>
    </div>
  );
}

const C = { bg: '#0d0d0d', border: '#0EA5E9', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  sidebar: {
    width: '220px', minWidth: '220px', background: C.bg,
    borderRight: `2px solid ${C.border}`, height: '100%',
    display: 'flex', flexDirection: 'column',
    fontFamily: '"IBM Plex Mono", monospace', overflow: 'hidden',
  },
  nav: { padding: '12px 8px', borderBottom: `1px solid #222` },
  navItem: {
    display: 'flex', alignItems: 'center', gap: '10px', width: '100%',
    background: 'transparent', border: 'none', color: C.dim,
    padding: '9px 10px', cursor: 'pointer', fontSize: '11px',
    letterSpacing: '1px', textAlign: 'left',
    fontFamily: '"IBM Plex Mono", monospace',
    transition: 'color .15s, background .15s',
  },
  navActive: {
    color: C.accent, background: 'rgba(14,165,233,0.08)',
    borderLeft: `2px solid ${C.accent}`, paddingLeft: '8px',
  },
  navIcon: { fontSize: '14px', width: '18px', textAlign: 'center' },
  section: { flex: 1, padding: '12px 8px', overflow: 'hidden', display: 'flex', flexDirection: 'column' },
  sectionHeader: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    marginBottom: '8px',
  },
  sectionLabel: { color: C.dim, fontSize: '10px', letterSpacing: '2px' },
  addBtn: {
    background: 'transparent', border: `1px solid #333`, color: C.accent,
    width: '20px', height: '20px', cursor: 'pointer', fontSize: '14px',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  newProject: { display: 'flex', gap: '4px', marginBottom: '8px' },
  input: {
    flex: 1, background: '#1a1a1a', border: `1px solid ${C.border}`,
    color: C.text, padding: '5px 8px', fontSize: '11px', outline: 'none',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  btnCreate: {
    background: C.accent, border: 'none', color: '#000',
    padding: '5px 8px', cursor: 'pointer', fontWeight: 700, fontSize: '12px',
  },
  projectList: { flex: 1, overflowY: 'auto' },
  projectItem: {
    display: 'flex', alignItems: 'center', gap: '8px', width: '100%',
    background: 'transparent', border: 'none', color: C.dim,
    padding: '7px 8px', cursor: 'pointer', fontSize: '11px', textAlign: 'left',
    fontFamily: '"IBM Plex Mono", monospace', transition: 'color .15s',
  },
  projectActive: { color: C.text, background: 'rgba(14,165,233,0.06)' },
  projectDot: { width: '8px', height: '8px', flexShrink: 0 },
  projectName: { flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  emptyMsg: { color: C.dim, fontSize: '11px', textAlign: 'center', padding: '12px 0', margin: 0 },
  footer: {
    borderTop: `2px solid ${C.border}`, padding: '10px 12px',
    display: 'flex', alignItems: 'center', gap: '10px',
  },
  userAvatar: {
    width: '28px', height: '28px', flexShrink: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#000', fontSize: '10px', fontWeight: 700,
    fontFamily: '"IBM Plex Mono", monospace',
  },
  userInfo: { display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  userName: { color: C.text, fontSize: '11px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  userRole: { color: C.dim, fontSize: '9px', letterSpacing: '1px' },
};
