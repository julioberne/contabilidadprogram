/* ============================================================
   HubSidebar.jsx — Sidebar colapsable + responsive
   - Desktop: sidebar de 240px colapsable a 52px (solo íconos)
   - Mobile (<768px): sidebar oculto, botón hamburguesa en TopBar
   ============================================================ */
import { useState, useEffect } from 'react';
import WorkspaceSwitcher from './WorkspaceSwitcher';

const NAV = [
  { id: 'tasks',    icon: '◈', label: 'TAREAS' },
  { id: 'notes',    icon: '◉', label: 'NOTAS' },
  { id: 'calendar', icon: '◷', label: 'CALENDARIO' },
  { id: 'members',  icon: '◎', label: 'EQUIPO' },
  { id: 'rrhh',     icon: '◐', label: 'EMPRESAS' },
  { id: 'settings', icon: '◬', label: 'AJUSTES' },
];

export default function HubSidebar({
  user, workspace, workspaces,
  onSwitchWorkspace, onCreateWorkspace,
  activeView, onChangeView,
  activeProject, onSelectProject,
  collapsed, onToggleCollapse,
  mobileOpen, onCloseMobile,
}) {
  const [entities,        setEntities]        = useState([]);
  const [projects,        setProjects]        = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [showNewProject,  setShowNewProject]  = useState(false);
  const [newProjectName,  setNewProjectName]  = useState('');

  // DT-3: bloquear scroll del body cuando el drawer mobile está abierto
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [mobileOpen]);

  useEffect(() => {
    if (!workspace) return;
    setLoadingProjects(true);
    fetch(`http://localhost:8000/api/hub/entities?workspace_id=${workspace.id}`)
      .then(r => r.json()).then(data => setEntities(Array.isArray(data) ? data : [])).catch(() => {});
    fetch(`http://localhost:8000/api/hub/projects?workspace_id=${workspace.id}`)
      .then(r => r.json())
      .then(data => {
        const list = Array.isArray(data) ? data : [];
        setProjects(list);
        if (list.length > 0 && !activeProject) onSelectProject(list[0]);
      })
      .catch(() => {})
      .finally(() => setLoadingProjects(false));
  }, [workspace?.id]);

  const createProject = async () => {
    if (!newProjectName.trim()) return;
    const res = await fetch('http://localhost:8000/api/hub/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workspace_id: workspace.id, name: newProjectName.trim(), created_by: user?.id,
      }),
    });
    const { project } = await res.json();
    setProjects(p => [...p, project]);
    setNewProjectName(''); setShowNewProject(false);
    onSelectProject(project);
  };

  const handleNavClick = (id) => {
    onChangeView(id);
    if (onCloseMobile) onCloseMobile(); // cerrar en mobile al navegar
  };

  const isCollapsed = collapsed && !mobileOpen;

  return (
    <>
      {/* Overlay mobile */}
      {mobileOpen && (
        <div style={S.overlay} onClick={onCloseMobile} />
      )}

      <div style={{
        ...S.sidebar,
        width: isCollapsed ? '52px' : '240px',
        minWidth: isCollapsed ? '52px' : '240px',
        // Mobile: posición absoluta sobre el contenido
        ...(mobileOpen ? S.sidebarMobileOpen : {}),
      }}>

        {/* ── TOGGLE COLLAPSE BUTTON ─────────────────────────── */}
        <button
          style={{ ...S.collapseBtn, justifyContent: isCollapsed ? 'center' : 'flex-end' }}
          onClick={onToggleCollapse}
          title={isCollapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}
        >
          <span style={{ fontSize: '12px', color: '#0EA5E9' }}>
            {isCollapsed ? '▶' : '◀'}
          </span>
        </button>

        {/* Workspace Switcher — oculto si colapsado */}
        {!isCollapsed && (
          <WorkspaceSwitcher
            workspace={workspace} workspaces={workspaces}
            onSwitch={onSwitchWorkspace} onCreate={onCreateWorkspace}
          />
        )}

        {/* Avatar compacto si colapsado */}
        {isCollapsed && workspace && (
          <div style={S.wsCompact} title={workspace.name}>
            {workspace.name?.slice(0, 2).toUpperCase()}
          </div>
        )}

        {/* ── NAVEGACIÓN PRINCIPAL ───────────────────────────── */}
        <nav style={S.nav}>
          {NAV.map(n => (
            <button key={n.id}
              style={{
                ...S.navItem,
                ...(activeView === n.id ? S.navActive : {}),
                justifyContent: isCollapsed ? 'center' : 'flex-start',
                paddingLeft: isCollapsed ? '0' : activeView === n.id ? '10px' : '12px',
              }}
              onClick={() => handleNavClick(n.id)}
              title={n.label}>
              <span style={S.navIcon}>{n.icon}</span>
              {!isCollapsed && <span>{n.label}</span>}
            </button>
          ))}
        </nav>

        {/* ── PROYECTOS ─────────────────────────────────────── */}
        {!isCollapsed && (
          <div style={S.section}>
            <div style={S.sectionHeader}>
              <span style={S.sectionLabel}>PROYECTOS</span>
              <button style={S.addBtn} onClick={() => setShowNewProject(v => !v)}>+</button>
            </div>

            {showNewProject && (
              <div style={S.newProject}>
                <input
                  placeholder="Nombre del proyecto..."
                  value={newProjectName}
                  onChange={e => setNewProjectName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && createProject()}
                  style={S.input} autoFocus
                />
                <button onClick={createProject} style={S.btnCreate}>✓</button>
              </div>
            )}

            <div style={S.projectList}>
              {projects.map(p => (
                <button key={p.id}
                  style={{
                    ...S.projectItem,
                    ...(activeProject?.id === p.id ? S.projectActive : {}),
                  }}
                  onClick={() => { onSelectProject(p); handleNavClick('tasks'); }}>
                  <span style={{ ...S.projectDot, background: p.color || '#0EA5E9' }} />
                  <span style={S.projectName}>{p.name}</span>
                </button>
              ))}
              {loadingProjects ? (
                <div style={S.emptyMsg}>CARGANDO...</div>
              ) : projects.length === 0 ? (
                <div style={S.emptyProjects}>
                  <p style={S.emptyMsg}>Sin proyectos</p>
                  <button style={S.emptyCreate} onClick={() => setShowNewProject(true)}>+ Crear uno</button>
                </div>
              ) : null}
            </div>
          </div>
        )}

        {/* Si colapsado: íconos de proyectos (solo puntos de color) */}
        {isCollapsed && (
          <div style={{ padding: '8px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px', overflowY: 'auto', flex: 1 }}>
            {projects.map(p => (
              <button key={p.id}
                title={p.name}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '4px' }}
                onClick={() => { onSelectProject(p); handleNavClick('tasks'); }}>
                <span style={{
                  display: 'block', width: '10px', height: '10px',
                  background: p.color || '#0EA5E9',
                  ...(activeProject?.id === p.id ? { boxShadow: `0 0 0 2px ${p.color || '#0EA5E9'}44` } : {})
                }} />
              </button>
            ))}
          </div>
        )}

        {/* ── FOOTER ────────────────────────────────────────── */}
        <div style={{ ...S.footer, padding: isCollapsed ? '12px 0' : '12px 14px', justifyContent: isCollapsed ? 'center' : 'flex-start' }}>
          <div style={{ ...S.userAvatar, background: user?.color || '#0EA5E9' }} title={user?.name}>
            {user?.name?.slice(0, 2).toUpperCase() || '??'}
          </div>
          {!isCollapsed && (
            <div style={S.userInfo}>
              <span style={S.userName}>{user?.name}</span>
              <span style={S.userRole}>{user?.role?.toUpperCase()}</span>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

const C = { bg: '#0d0d0d', border: '#0EA5E9', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const S = {
  sidebar: {
    background: C.bg,
    borderRight: `2px solid ${C.border}`, height: '100%',
    display: 'flex', flexDirection: 'column',
    fontFamily: '"IBM Plex Mono", monospace', overflow: 'hidden',
    transition: 'width .2s ease, min-width .2s ease',
    flexShrink: 0, position: 'relative', zIndex: 10,
  },
  sidebarMobileOpen: {
    position: 'absolute', top: 0, left: 0, height: '100%',
    width: '240px !important', minWidth: '240px',
    zIndex: 100, boxShadow: '4px 0 20px rgba(0,0,0,.8)',
  },
  overlay: {
    position: 'absolute', inset: 0, background: 'rgba(0,0,0,.6)',
    zIndex: 99, cursor: 'pointer',
  },
  collapseBtn: {
    display: 'flex', alignItems: 'center', padding: '6px 10px',
    background: 'transparent', border: 'none', cursor: 'pointer',
    borderBottom: '1px solid #111', width: '100%', height: '32px',
    flexShrink: 0,
  },
  wsCompact: {
    margin: '6px auto', width: '34px', height: '34px',
    background: '#0EA5E920', border: '1px solid #0EA5E9',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#0EA5E9', fontSize: '11px', fontWeight: 700,
    fontFamily: '"IBM Plex Mono", monospace', cursor: 'default',
  },
  nav: { padding: '8px 4px', borderBottom: '1px solid #222' },
  navItem: {
    display: 'flex', alignItems: 'center', gap: '10px', width: '100%',
    background: 'transparent', border: 'none', color: C.dim,
    paddingTop: '9px', paddingBottom: '9px',
    cursor: 'pointer', fontSize: '13px', letterSpacing: '0.5px',
    fontFamily: '"IBM Plex Mono", monospace', transition: 'color .15s, background .15s',
    borderLeft: '2px solid transparent',
  },
  navActive: {
    color: C.accent, background: 'rgba(14,165,233,0.08)',
    borderLeft: `2px solid ${C.accent}`,
  },
  navIcon: { fontSize: '15px', width: '20px', textAlign: 'center', flexShrink: 0 },
  section: { flex: 1, padding: '12px 8px', overflow: 'hidden', display: 'flex', flexDirection: 'column' },
  sectionHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' },
  sectionLabel: { color: C.dim, fontSize: '11px', letterSpacing: '1.5px', fontWeight: 700 },
  addBtn: {
    background: 'transparent', border: '1px solid #333', color: C.accent,
    width: '22px', height: '22px', cursor: 'pointer', fontSize: '16px',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  newProject: { display: 'flex', gap: '4px', marginBottom: '10px' },
  input: {
    flex: 1, background: '#1a1a1a', border: `1px solid ${C.border}`,
    color: C.text, padding: '6px 10px', fontSize: '12px', outline: 'none',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  btnCreate: { background: C.accent, border: 'none', color: '#000', padding: '6px 10px', cursor: 'pointer', fontWeight: 700, fontSize: '13px' },
  projectList: { flex: 1, overflowY: 'auto' },
  projectItem: {
    display: 'flex', alignItems: 'center', gap: '8px', width: '100%',
    background: 'transparent', border: 'none', color: C.dim,
    padding: '8px 8px', cursor: 'pointer', fontSize: '12px', textAlign: 'left',
    fontFamily: '"IBM Plex Mono", monospace', transition: 'color .15s',
  },
  projectActive: { color: C.text, background: 'rgba(14,165,233,0.06)' },
  projectDot: { width: '9px', height: '9px', flexShrink: 0 },
  projectName: { flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  emptyMsg: { color: C.dim, fontSize: '12px', textAlign: 'center', padding: '10px 0', margin: 0 },
  emptyProjects: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', padding: '10px' },
  emptyCreate: { background: 'transparent', border: `1px dashed ${C.accent}`, color: C.accent, padding: '5px 12px', cursor: 'pointer', fontSize: '11px', fontFamily: '"IBM Plex Mono", monospace' },
  footer: {
    borderTop: `2px solid ${C.border}`, padding: '12px 14px',
    display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0,
  },
  userAvatar: {
    width: '32px', height: '32px', flexShrink: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#000', fontSize: '11px', fontWeight: 700,
    fontFamily: '"IBM Plex Mono", monospace',
  },
  userInfo: { display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  userName: { color: C.text, fontSize: '12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  userRole: { color: C.dim, fontSize: '10px', letterSpacing: '0.5px' },
};
