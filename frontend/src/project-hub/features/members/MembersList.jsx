/* ============================================================
   MembersList.jsx — Vista de equipo con métricas por usuario
   FASE 5: Muestra cada miembro con sus KPIs de rendimiento
   ============================================================ */
import { useState, useEffect } from 'react';
import MemberProfile from './MemberProfile';

const API = 'http://localhost:8000/api/hub';

export default function MembersList({ workspace, user }) {
  const [members,  setMembers]  = useState([]);
  const [metrics,  setMetrics]  = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [addEmail, setAddEmail] = useState('');
  const [addRole,  setAddRole]  = useState('member');
  const [addError, setAddError] = useState('');
  const [showAdd,  setShowAdd]  = useState(false);

  useEffect(() => {
    if (!workspace) return;
    loadAll();
  }, [workspace?.id]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [mRes, kRes] = await Promise.all([
        fetch(`${API}/users?workspace_id=${workspace.id}`),
        fetch(`${API}/metrics?workspace_id=${workspace.id}`),
      ]);
      const membersData = await mRes.json();
      const metricsData = await kRes.json();
      setMembers(Array.isArray(membersData) ? membersData : []);
      setMetrics(Array.isArray(metricsData) ? metricsData : []);
    } finally { setLoading(false); }
  };

  // Combinar miembro + métricas
  const membersWithMetrics = members.map(m => ({
    ...m,
    ...((metrics.find(mx => mx.id === m.id)) || {}),
  }));

  const handleAddMember = async (e) => {
    e.preventDefault();
    setAddError('');
    try {
      // Buscar usuario por email (login sin contraseña no es posible, se usa endpoint de búsqueda)
      const res = await fetch(`${API}/users/add-member`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace_id: workspace.id, user_id: addEmail, role: addRole }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Error');
      await loadAll();
      setAddEmail(''); setShowAdd(false);
    } catch (e) { setAddError(e.message); }
  };

  if (!workspace) return (
    <div style={styles.empty}><p style={styles.emptyText}>◎ Selecciona un workspace</p></div>
  );

  if (selected) return (
    <MemberProfile
      member={selected}
      metrics={membersWithMetrics.find(m => m.id === selected.id)}
      onBack={() => setSelected(null)}
    />
  );

  return (
    <div style={styles.root}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>EQUIPO</h2>
          <p style={styles.subtitle}>{workspace.name} — {members.length} miembro{members.length !== 1 ? 's' : ''}</p>
        </div>
        {(user?.role === 'owner' || user?.role === 'admin' || user?.is_superuser) && (
          <button style={styles.addBtn} onClick={() => setShowAdd(v => !v)}>
            + AGREGAR
          </button>
        )}
      </div>

      {/* Formulario agregar */}
      {showAdd && (
        <form style={styles.addForm} onSubmit={handleAddMember}>
          <span style={styles.addLabel}>Agregar por User ID:</span>
          <input style={styles.input} placeholder="UUID del usuario"
            value={addEmail} onChange={e => setAddEmail(e.target.value)} />
          <select style={styles.select} value={addRole} onChange={e => setAddRole(e.target.value)}>
            <option value="member">MEMBER</option>
            <option value="admin">ADMIN</option>
            <option value="viewer">VIEWER</option>
          </select>
          <button type="submit" style={styles.submitBtn}>AGREGAR</button>
          {addError && <span style={styles.addError}>{addError}</span>}
        </form>
      )}

      {/* Grid de miembros */}
      {loading ? (
        <div style={styles.loading}>CARGANDO...</div>
      ) : (
        <div style={styles.grid}>
          {membersWithMetrics.map(m => {
            const done    = m.tasks_done    || 0;
            const pending = m.tasks_pending || 0;
            const total   = done + pending;
            const pct     = total > 0 ? Math.round((done / total) * 100) : 0;
            const avgHrs  = m.avg_hours_to_complete
              ? parseFloat(m.avg_hours_to_complete).toFixed(1)
              : null;

            return (
              <button key={m.id} style={styles.card} onClick={() => setSelected(m)}>
                {/* Avatar */}
                <div style={{ ...styles.avatar, background: m.color || '#0EA5E9' }}>
                  {m.avatar_url
                    ? <img src={m.avatar_url} alt={m.name} style={styles.avatarImg} />
                    : m.name?.slice(0, 2).toUpperCase()}
                </div>

                {/* Info */}
                <div style={styles.cardBody}>
                  <div style={styles.cardTop}>
                    <span style={styles.name}>{m.name}</span>
                    <span style={{ ...styles.roleBadge, borderColor: getRoleColor(m.role) }}>
                      {m.role?.toUpperCase()}
                    </span>
                  </div>
                  {m.description && <p style={styles.desc}>{m.description.slice(0, 60)}{m.description.length > 60 ? '…' : ''}</p>}

                  {/* Barra de progreso de tareas */}
                  <div style={styles.progressRow}>
                    <div style={styles.progressBar}>
                      <div style={{ ...styles.progressFill, width: `${pct}%`, background: m.color || '#0EA5E9' }} />
                    </div>
                    <span style={styles.pct}>{pct}%</span>
                  </div>

                  {/* Mini KPIs */}
                  <div style={styles.kpis}>
                    <div style={styles.kpi}>
                      <span style={styles.kpiVal}>{done}</span>
                      <span style={styles.kpiLabel}>HECHAS</span>
                    </div>
                    <div style={styles.kpi}>
                      <span style={{ ...styles.kpiVal, color: pending > 0 ? '#F59E0B' : '#64748b' }}>{pending}</span>
                      <span style={styles.kpiLabel}>PENDIENTES</span>
                    </div>
                    {avgHrs && (
                      <div style={styles.kpi}>
                        <span style={styles.kpiVal}>{avgHrs}h</span>
                        <span style={styles.kpiLabel}>PROMEDIO</span>
                      </div>
                    )}
                    {m.tasks_overdue > 0 && (
                      <div style={styles.kpi}>
                        <span style={{ ...styles.kpiVal, color: '#ef4444' }}>{m.tasks_overdue}</span>
                        <span style={styles.kpiLabel}>VENCIDAS</span>
                      </div>
                    )}
                  </div>
                </div>
              </button>
            );
          })}

          {members.length === 0 && (
            <div style={styles.noMembers}>
              <p>Sin miembros aún. Invita a tu equipo.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function getRoleColor(role) {
  return { owner: '#EF4444', admin: '#F59E0B', member: '#0EA5E9', viewer: '#64748b' }[role] || '#64748b';
}

const C = { bg: '#0a0a0a', card: '#111', border: '#1e1e1e', borderAcc: '#0EA5E9', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  root: { display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', background: C.bg, fontFamily: '"IBM Plex Mono", monospace' },
  empty: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  emptyText: { color: C.dim, fontSize: '14px' },
  header: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', padding: '20px 24px', borderBottom: `2px solid ${C.border}`, flexShrink: 0 },
  title: { color: C.accent, fontSize: '16px', margin: '0 0 4px', letterSpacing: '3px' },
  subtitle: { color: C.dim, fontSize: '11px', margin: 0 },
  addBtn: { background: C.accent, border: 'none', color: '#000', padding: '8px 16px', cursor: 'pointer', fontSize: '11px', fontWeight: 700, letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace', boxShadow: `2px 2px 0 #0369a1` },
  addForm: { display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 24px', background: '#111', borderBottom: `1px solid ${C.border}`, flexWrap: 'wrap' },
  addLabel: { color: C.dim, fontSize: '11px' },
  input: { background: '#1a1a1a', border: `2px solid #333`, color: C.text, padding: '6px 10px', fontSize: '11px', fontFamily: '"IBM Plex Mono", monospace', outline: 'none', flex: 1, minWidth: '200px' },
  select: { background: '#1a1a1a', border: `2px solid #333`, color: C.text, padding: '6px 10px', fontSize: '11px', fontFamily: '"IBM Plex Mono", monospace', outline: 'none', cursor: 'pointer' },
  submitBtn: { background: C.accent, border: 'none', color: '#000', padding: '6px 14px', cursor: 'pointer', fontSize: '11px', fontWeight: 700, fontFamily: '"IBM Plex Mono", monospace' },
  addError: { color: '#ef4444', fontSize: '11px' },
  loading: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.dim, fontSize: '12px' },
  grid: { flex: 1, overflowY: 'auto', padding: '20px 24px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px', alignContent: 'start' },
  card: { background: C.card, border: `2px solid ${C.border}`, display: 'flex', gap: '16px', padding: '18px', cursor: 'pointer', textAlign: 'left', transition: 'border-color .15s, box-shadow .15s', fontFamily: '"IBM Plex Mono", monospace', width: '100%' },
  avatar: { width: '48px', height: '48px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontSize: '16px', fontWeight: 700, overflow: 'hidden' },
  avatarImg: { width: '100%', height: '100%', objectFit: 'cover' },
  cardBody: { flex: 1, display: 'flex', flexDirection: 'column', gap: '6px', minWidth: 0 },
  cardTop: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' },
  name: { color: C.text, fontSize: '13px', fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  roleBadge: { border: '1px solid', color: C.dim, padding: '1px 6px', fontSize: '9px', letterSpacing: '1px', flexShrink: 0 },
  desc: { color: C.dim, fontSize: '11px', margin: 0, lineHeight: 1.4 },
  progressRow: { display: 'flex', alignItems: 'center', gap: '8px' },
  progressBar: { flex: 1, height: '4px', background: '#1e1e1e', overflow: 'hidden' },
  progressFill: { height: '100%', transition: 'width .4s' },
  pct: { color: C.dim, fontSize: '10px', flexShrink: 0 },
  kpis: { display: 'flex', gap: '14px' },
  kpi: { display: 'flex', flexDirection: 'column', gap: '1px' },
  kpiVal: { color: C.text, fontSize: '14px', fontWeight: 700, color: C.accent },
  kpiLabel: { color: C.dim, fontSize: '9px', letterSpacing: '1px' },
  noMembers: { color: C.dim, fontSize: '12px', gridColumn: '1/-1', textAlign: 'center', padding: '40px' },
};
