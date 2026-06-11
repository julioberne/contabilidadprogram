/* ============================================================
   WorkspaceSwitcher.jsx — Selector de workspace tipo Slack
   ============================================================ */
import { useState } from 'react';

export default function WorkspaceSwitcher({ workspace, workspaces, onSwitch, onCreate }) {
  const [open, setOpen]         = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm]         = useState({ name: '', nit: '' });

  const initials = (name) => name?.slice(0, 2).toUpperCase() || '??';
  const bgColor  = (name) => {
    const colors = ['#0EA5E9','#8B5CF6','#10B981','#F59E0B','#EF4444','#EC4899'];
    let h = 0; for (const c of (name || '')) h = c.charCodeAt(0) + h * 31;
    return colors[Math.abs(h) % colors.length];
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.name) return;
    await onCreate(form);
    setCreating(false); setForm({ name: '', nit: '' }); setOpen(false);
  };

  return (
    <div style={styles.root}>
      {/* Trigger */}
      <button style={styles.trigger} onClick={() => setOpen(o => !o)}>
        <div style={{ ...styles.avatar, background: bgColor(workspace?.name) }}>
          {initials(workspace?.name)}
        </div>
        <span style={styles.wsName}>{workspace?.name || 'Sin workspace'}</span>
        <span style={styles.chevron}>{open ? '▲' : '▼'}</span>
      </button>

      {/* Dropdown */}
      {open && (
        <div style={styles.dropdown}>
          <p style={styles.dropLabel}>MIS WORKSPACES</p>
          {workspaces.map(ws => (
            <button key={ws.id} style={styles.wsItem}
              onClick={() => { onSwitch(ws); setOpen(false); }}>
              <div style={{ ...styles.avatarSm, background: bgColor(ws.name) }}>
                {initials(ws.name)}
              </div>
              <span style={styles.wsItemName}>{ws.name}</span>
              {workspace?.id === ws.id && <span style={styles.check}>✓</span>}
            </button>
          ))}

          <div style={styles.divider} />

          {!creating ? (
            <button style={styles.createBtn} onClick={() => setCreating(true)}>
              + Crear workspace
            </button>
          ) : (
            <form onSubmit={handleCreate} style={styles.createForm}>
              <input placeholder="Nombre de organización" value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                style={styles.input} autoFocus />
              <input placeholder="NIT (opcional)" value={form.nit}
                onChange={e => setForm(f => ({ ...f, nit: e.target.value }))}
                style={styles.input} />
              <div style={{ display: 'flex', gap: '6px' }}>
                <button type="submit" style={styles.btnCreate}>CREAR</button>
                <button type="button" style={styles.btnCancel}
                  onClick={() => setCreating(false)}>✕</button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}

const C = { bg: '#111', border: '#0EA5E9', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  root: { position: 'relative', userSelect: 'none' },
  trigger: {
    display: 'flex', alignItems: 'center', gap: '10px',
    background: 'transparent', border: 'none', cursor: 'pointer',
    padding: '8px 12px', width: '100%', textAlign: 'left',
    borderBottom: `2px solid ${C.border}`, marginBottom: '0',
  },
  avatar: {
    width: '32px', height: '32px', borderRadius: '0',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#000', fontSize: '12px', fontWeight: 700, flexShrink: 0,
    fontFamily: '"IBM Plex Mono", monospace',
  },
  avatarSm: {
    width: '24px', height: '24px', borderRadius: '0', flexShrink: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#000', fontSize: '10px', fontWeight: 700,
    fontFamily: '"IBM Plex Mono", monospace',
  },
  wsName: { color: C.text, fontSize: '12px', flex: 1, fontFamily: '"IBM Plex Mono", monospace', fontWeight: 700 },
  chevron: { color: C.accent, fontSize: '10px' },
  dropdown: {
    position: 'absolute', top: '100%', left: 0, right: 0,
    background: '#0d0d0d', border: `2px solid ${C.border}`,
    boxShadow: `4px 4px 0 ${C.border}`, zIndex: 1000, padding: '8px',
    minWidth: '220px',
  },
  dropLabel: { color: C.dim, fontSize: '10px', letterSpacing: '2px', margin: '4px 8px 8px', },
  wsItem: {
    display: 'flex', alignItems: 'center', gap: '8px', width: '100%',
    background: 'transparent', border: 'none', cursor: 'pointer',
    padding: '8px', color: C.text, fontSize: '12px',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  wsItemName: { flex: 1, textAlign: 'left' },
  check: { color: C.accent, fontSize: '14px' },
  divider: { borderTop: `1px solid #333`, margin: '8px 0' },
  createBtn: {
    width: '100%', background: 'transparent', border: `1px dashed #333`,
    color: C.dim, padding: '8px', cursor: 'pointer', fontSize: '12px',
    fontFamily: '"IBM Plex Mono", monospace', textAlign: 'left',
  },
  createForm: { display: 'flex', flexDirection: 'column', gap: '6px', padding: '4px' },
  input: {
    background: '#1a1a1a', border: `1px solid #333`, color: C.text,
    padding: '6px 8px', fontSize: '12px', fontFamily: '"IBM Plex Mono", monospace',
    outline: 'none',
  },
  btnCreate: {
    flex: 1, background: C.accent, color: '#000', border: 'none',
    padding: '6px', fontSize: '11px', cursor: 'pointer',
    fontFamily: '"IBM Plex Mono", monospace', fontWeight: 700,
  },
  btnCancel: {
    background: 'transparent', border: `1px solid #333`,
    color: C.dim, padding: '6px 10px', cursor: 'pointer', fontSize: '12px',
    fontFamily: '"IBM Plex Mono", monospace',
  },
};
