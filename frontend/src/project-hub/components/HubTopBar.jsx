/* ============================================================
   HubTopBar.jsx — Barra superior del Project Hub
   ============================================================ */
export default function HubTopBar({ user, workspace, activeView, activeProject, onLogout }) {
  const viewLabels = {
    tasks: 'TAREAS', notes: 'NOTAS', calendar: 'CALENDARIO',
    members: 'EQUIPO', settings: 'AJUSTES',
  };

  return (
    <header style={styles.bar}>
      {/* Breadcrumb */}
      <div style={styles.breadcrumb}>
        <span style={styles.ws}>{workspace?.name || 'Sin workspace'}</span>
        {activeProject && (
          <>
            <span style={styles.sep}>/</span>
            <span style={styles.project}>{activeProject.name}</span>
          </>
        )}
        <span style={styles.sep}>/</span>
        <span style={styles.view}>{viewLabels[activeView] || activeView}</span>
      </div>

      {/* Right: status + logout */}
      <div style={styles.right}>
        <div style={styles.status}>
          <span style={styles.dot} />
          <span style={styles.statusText}>PROJECT HUB v1.0</span>
        </div>
        <button style={styles.logoutBtn} onClick={onLogout}>
          ⎋ SALIR
        </button>
      </div>
    </header>
  );
}

const C = { bg: '#0d0d0d', border: '#0EA5E9', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  bar: {
    height: '48px', background: C.bg, borderBottom: `2px solid ${C.border}`,
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '0 20px', fontFamily: '"IBM Plex Mono", monospace', flexShrink: 0,
  },
  breadcrumb: { display: 'flex', alignItems: 'center', gap: '8px' },
  ws: { color: C.dim, fontSize: '12px' },
  sep: { color: '#333', fontSize: '12px' },
  project: { color: C.accent, fontSize: '12px' },
  view: { color: C.text, fontSize: '12px', fontWeight: 700 },
  right: { display: 'flex', alignItems: 'center', gap: '16px' },
  status: { display: 'flex', alignItems: 'center', gap: '6px' },
  dot: { width: '7px', height: '7px', background: '#10b981', borderRadius: '50%' },
  statusText: { color: C.dim, fontSize: '10px', letterSpacing: '1px' },
  logoutBtn: {
    background: 'transparent', border: `1px solid #333`, color: C.dim,
    padding: '4px 10px', cursor: 'pointer', fontSize: '11px',
    fontFamily: '"IBM Plex Mono", monospace',
    transition: 'color .15s, border-color .15s',
  },
};
