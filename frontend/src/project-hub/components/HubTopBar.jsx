/* ============================================================
   HubTopBar.jsx — Barra superior del Project Hub
   ============================================================ */
export default function HubTopBar({ user, workspace, activeView, activeProject, onLogout, onExit, isMobile, onMenuToggle, sidebarCollapsed }) {
  const viewLabels = {
    tasks: 'TAREAS', notes: 'NOTAS', calendar: 'CALENDARIO',
    members: 'EQUIPO', settings: 'AJUSTES',
  };

  return (
    <header style={styles.bar}>
      {/* Hamburger / Collapse toggle */}
      <button style={styles.menuBtn} onClick={onMenuToggle} title="Menú">
        {isMobile
          ? (sidebarCollapsed ? '☰' : '✕')
          : (sidebarCollapsed ? '▶' : '◀')
        }
      </button>

      {/* Logo + Breadcrumb */}
      <div style={styles.left}>
        <span style={styles.logo}>⬡</span>
        <div style={styles.breadcrumb}>
          <span style={styles.hubLabel}>PROJECT HUB</span>
          {!isMobile && <><span style={styles.sep}>/</span><span style={styles.ws}>{workspace?.name || '—'}</span></>}
          {!isMobile && activeProject && activeView === 'tasks' && (
            <><span style={styles.sep}>/</span><span style={styles.project}>{activeProject.name}</span></>
          )}
          <span style={styles.sep}>/</span>
          <span style={styles.view}>{viewLabels[activeView] || activeView}</span>
        </div>
      </div>

      {/* Right: status + acciones */}
      <div style={styles.right}>
        {/* Status online — solo desktop */}
        {!isMobile && (
          <div style={styles.status}>
            <span style={styles.dot} />
            <span style={styles.statusText}>ONLINE</span>
          </div>
        )}

        {/* Usuario actual */}
        {user && (
          <div style={styles.userChip}>
            <div style={{ ...styles.userAvatar, background: user.color || '#0EA5E9' }}>
              {user.name?.slice(0, 2).toUpperCase()}
            </div>
            {!isMobile && <span style={styles.userName}>{user.name?.split(' ')[0]}</span>}
          </div>
        )}

        {/* Logout */}
        <button style={styles.logoutBtn} onClick={onLogout} title="Cerrar sesión">
          {isMobile ? '⎋' : '⎋ LOGOUT'}
        </button>

        {/* Volver a FIN-SYS APP */}
        {onExit && (
          <button style={styles.exitBtn} onClick={onExit} title="Volver a FIN-SYS OS">
            {isMobile ? '✕' : '✕ SALIR'}
          </button>
        )}
      </div>
    </header>
  );
}

const C = { bg: '#0d0d0d', border: '#0EA5E9', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  bar: {
    height: '52px', background: C.bg, borderBottom: `2px solid ${C.border}`,
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '0 12px', fontFamily: '"IBM Plex Mono", monospace', flexShrink: 0,
    gap: '8px', overflow: 'hidden',
  },
  menuBtn: {
    background: 'transparent', border: '1px solid #333', color: C.accent,
    width: '34px', height: '34px', cursor: 'pointer', fontSize: '14px',
    fontFamily: '"IBM Plex Mono", monospace', display: 'flex',
    alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  left: { display: 'flex', alignItems: 'center', gap: '10px', flex: 1, overflow: 'hidden', minWidth: 0 },
  logo: { color: C.accent, fontSize: '20px', lineHeight: 1 },
  hubLabel: { color: C.accent, fontSize: '14px', fontWeight: 700, letterSpacing: '1.5px' },
  breadcrumb: { display: 'flex', alignItems: 'center', gap: '8px' },
  sep: { color: '#444', fontSize: '14px' },
  ws: { color: C.dim, fontSize: '13px' },
  project: { color: C.text, fontSize: '13px' },
  view: { color: C.text, fontSize: '13px', fontWeight: 700 },
  right: { display: 'flex', alignItems: 'center', gap: '12px' },
  status: { display: 'flex', alignItems: 'center', gap: '6px' },
  dot: { width: '8px', height: '8px', background: '#10b981', borderRadius: '50%' },
  statusText: { color: '#10b981', fontSize: '11px', letterSpacing: '0.5px' },
  userChip: { display: 'flex', alignItems: 'center', gap: '8px' },
  userAvatar: {
    width: '28px', height: '28px', display: 'flex', alignItems: 'center',
    justifyContent: 'center', color: '#000', fontSize: '11px', fontWeight: 700, flexShrink: 0,
  },
  userName: { color: C.dim, fontSize: '12px' },
  logoutBtn: {
    background: 'transparent', border: '1px solid #333', color: C.dim,
    padding: '5px 12px', cursor: 'pointer', fontSize: '12px',
    fontFamily: '"IBM Plex Mono", monospace', letterSpacing: '0.5px',
  },
  exitBtn: {
    background: 'transparent', border: '1px solid #ef4444', color: '#ef4444',
    padding: '5px 12px', cursor: 'pointer', fontSize: '12px',
    fontFamily: '"IBM Plex Mono", monospace', letterSpacing: '0.5px',
  },
};
