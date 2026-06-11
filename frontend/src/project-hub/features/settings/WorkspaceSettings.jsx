/* ============================================================
   WorkspaceSettings.jsx — Configuración del workspace
   FASE 5: Info general + árbol de entidades
   ============================================================ */
import EntityTree from './EntityTree';

export default function WorkspaceSettings({ workspace, user }) {
  if (!workspace) return (
    <div style={styles.empty}><p style={styles.emptyText}>◬ Selecciona un workspace</p></div>
  );

  const canEdit = user?.role === 'owner' || user?.role === 'admin' || user?.is_superuser;

  return (
    <div style={styles.root}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.title}>AJUSTES DEL WORKSPACE</h2>
        <span style={styles.wsName}>{workspace.name}</span>
      </div>

      {/* Info básica */}
      <div style={styles.infoSection}>
        <div style={styles.infoGrid}>
          <div style={styles.infoItem}>
            <span style={styles.infoLabel}>NOMBRE</span>
            <span style={styles.infoVal}>{workspace.name}</span>
          </div>
          {workspace.nit && (
            <div style={styles.infoItem}>
              <span style={styles.infoLabel}>NIT</span>
              <span style={styles.infoVal}>{workspace.nit}</span>
            </div>
          )}
          <div style={styles.infoItem}>
            <span style={styles.infoLabel}>PLAN</span>
            <span style={{ ...styles.infoVal, color: '#10B981' }}>{(workspace.plan || 'FREE').toUpperCase()}</span>
          </div>
          <div style={styles.infoItem}>
            <span style={styles.infoLabel}>ID</span>
            <span style={{ ...styles.infoVal, color: '#64748b', fontSize: '10px' }}>{workspace.id}</span>
          </div>
        </div>

        {!canEdit && (
          <div style={styles.readOnlyBanner}>
            👁 Solo lectura — No tienes permisos de administrador en este workspace
          </div>
        )}
      </div>

      {/* Árbol de entidades */}
      <div style={styles.treeSection}>
        <EntityTree workspace={workspace} />
      </div>
    </div>
  );
}

const C = { bg: '#0a0a0a', card: '#111', border: '#1e1e1e', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  root: { display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', background: C.bg, fontFamily: '"IBM Plex Mono", monospace' },
  empty: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  emptyText: { color: C.dim, fontSize: '14px' },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '20px 24px', borderBottom: `2px solid ${C.border}`, flexShrink: 0,
  },
  title: { color: C.accent, fontSize: '14px', margin: 0, letterSpacing: '3px' },
  wsName: { color: C.dim, fontSize: '12px' },
  infoSection: { padding: '20px 24px', borderBottom: `2px solid ${C.border}`, flexShrink: 0 },
  infoGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '16px', marginBottom: '12px' },
  infoItem: { display: 'flex', flexDirection: 'column', gap: '4px' },
  infoLabel: { color: C.dim, fontSize: '9px', letterSpacing: '2px' },
  infoVal: { color: C.text, fontSize: '13px', fontWeight: 600 },
  readOnlyBanner: {
    background: '#1a1400', border: `1px solid #F59E0B`, color: '#F59E0B',
    padding: '8px 14px', fontSize: '11px', marginTop: '8px',
  },
  treeSection: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
};
