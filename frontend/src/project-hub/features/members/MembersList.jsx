/* ============================================================
   MembersList.jsx — Vista de equipo con métricas por usuario
   FASE 5: Muestra cada miembro con sus KPIs de rendimiento
   ============================================================ */
import { useState, useEffect } from 'react';
import MemberProfile from './MemberProfile';
import CompanyMapTab from './CompanyMapTab';
import { useQueryParam } from '../../../shell/useRoute.js';
import { API_HUB } from '../../../config';

const API = API_HUB;

const BLANK_FORM = { name: '', email: '', cedula: '', role: 'member', description: '', password: '' };

export default function MembersList({ workspace, user }) {
  const [members,  setMembers]  = useState([]);
  const [metrics,  setMetrics]  = useState([]);
  // Persona abierta reflejada en la URL: /rrhh?view=members&member=<id>
  const [selectedId, setSelectedId] = useQueryParam('member', '');
  const [loading,  setLoading]  = useState(false);
  const [form,     setForm]     = useState(BLANK_FORM);
  const [addError, setAddError] = useState('');
  const [saving,   setSaving]   = useState(false);
  const [showAdd,  setShowAdd]  = useState(false);
  const [showMap,  setShowMap]  = useState(false);   // Mapa de Empresas (ADMIN)
  const isAdmin = user?.role === 'owner' || user?.role === 'admin' || user?.is_superuser;

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

  // Persona abierta: se resuelve desde la URL contra la lista cargada.
  // String() en ambos lados: los ids del hub son UUID (string), pero el
  // usuario sintético del SSO usa id numérico — así el match nunca falla.
  const selected = selectedId
    ? membersWithMetrics.find(m => String(m.id) === String(selectedId))
    : null;

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { setAddError('El nombre es obligatorio.'); return; }
    setSaving(true); setAddError('');
    try {
      // Crea la ficha de la persona y la vincula al workspace (login opcional)
      const res = await fetch(`${API}/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_id: workspace.id,
          name: form.name.trim(),
          email: form.email.trim() || null,
          cedula: form.cedula.trim() || null,
          description: form.description.trim() || null,
          role: form.role,
          password: form.password.trim() || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
      await loadAll();
      setForm(BLANK_FORM); setShowAdd(false);
    } catch (e) { setAddError(e.message); }
    finally { setSaving(false); }
  };

  if (!workspace) return (
    <div style={styles.empty}><p style={styles.emptyText}>◎ Selecciona un workspace</p></div>
  );

  if (selected) return (
    <MemberProfile
      member={selected}
      metrics={membersWithMetrics.find(m => m.id === selected.id)}
      workspace={workspace}
      currentUser={user}
      onBack={() => setSelectedId('')}
      onSaved={(updated) => { setSelectedId(updated.id); loadAll(); }}
      onRemoved={() => { setSelectedId(''); loadAll(); }}
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
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {isAdmin && (
            <button
              style={{ ...styles.addBtn, background: showMap ? '#0EA5E9' : 'transparent', color: showMap ? '#000' : '#0EA5E9', border: '2px solid #0EA5E9' }}
              onClick={() => setShowMap(v => !v)}
              title="Mapa de empresas y asignaciones"
            >
              {showMap ? '✕ CERRAR MAPA' : '◈ MAPA EMPRESAS'}
            </button>
          )}
          {isAdmin && (
            <button style={styles.addBtn} onClick={() => setShowAdd(v => !v)}>
              + AGREGAR
            </button>
          )}
        </div>
      </div>

      {/* Formulario alta de trabajador (roster, login opcional) */}
      {showAdd && (
        <form style={styles.addForm} onSubmit={handleAddMember}>
          <div style={styles.addRow}>
            <input style={styles.input} placeholder="Nombre completo *" autoFocus
              value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            <input style={styles.inputSm} placeholder="Cédula"
              value={form.cedula} onChange={e => setForm(f => ({ ...f, cedula: e.target.value }))} />
            <select style={styles.select} value={form.role}
              onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
              <option value="member">MEMBER</option>
              <option value="admin">ADMIN</option>
              <option value="viewer">VIEWER</option>
              <option value="owner">OWNER</option>
            </select>
          </div>
          <div style={styles.addRow}>
            <input style={styles.input} placeholder="Email (opcional — solo si tendrá login)"
              value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
            <input style={styles.inputSm} type="password" placeholder="Clave (opcional)"
              value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
          </div>
          <input style={styles.input} placeholder="Cargo / funciones (opcional)"
            value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          <div style={styles.addRow}>
            <button type="submit" style={styles.submitBtn} disabled={saving}>
              {saving ? 'CREANDO…' : '＋ CREAR TRABAJADOR'}
            </button>
            <button type="button" style={styles.cancelBtn}
              onClick={() => { setShowAdd(false); setAddError(''); setForm(BLANK_FORM); }}>CANCELAR</button>
            {addError && <span style={styles.addError}>{addError}</span>}
          </div>
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
              <button key={m.id} style={styles.card} onClick={() => setSelectedId(m.id)}>
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

      {/* ── MAPA DE EMPRESAS (solo ADMIN) ─────────────────────── */}
      {showMap && isAdmin && (
        <div style={styles.mapSection}>
          <CompanyMapTab
            workspace={workspace}
            currentUser={user}
            members={members}
          />
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
  mapSection: { flex: '0 0 45vh', minHeight: '320px', borderTop: '2px solid #0EA5E9', display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  empty: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  emptyText: { color: C.dim, fontSize: '14px' },
  header: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', padding: '20px 24px', borderBottom: `2px solid ${C.border}`, flexShrink: 0 },
  title: { color: C.accent, fontSize: '17px', margin: '0 0 4px', letterSpacing: '3px' },
  subtitle: { color: C.dim, fontSize: '12px', margin: 0 },
  addBtn: { background: C.accent, border: 'none', color: '#000', padding: '8px 16px', cursor: 'pointer', fontSize: '11px', fontWeight: 700, letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace', boxShadow: `2px 2px 0 #0369a1` },
  addForm: { display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px 24px', background: '#111', borderBottom: `1px solid ${C.border}` },
  addRow: { display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' },
  addLabel: { color: C.dim, fontSize: '12px' },
  input: { background: '#1a1a1a', border: `2px solid #333`, color: C.text, padding: '7px 10px', fontSize: '12px', fontFamily: '"IBM Plex Mono", monospace', outline: 'none', flex: 1, minWidth: '200px' },
  inputSm: { background: '#1a1a1a', border: `2px solid #333`, color: C.text, padding: '7px 10px', fontSize: '12px', fontFamily: '"IBM Plex Mono", monospace', outline: 'none', width: '150px' },
  select: { background: '#1a1a1a', border: `2px solid #333`, color: C.text, padding: '7px 10px', fontSize: '12px', fontFamily: '"IBM Plex Mono", monospace', outline: 'none', cursor: 'pointer' },
  submitBtn: { background: C.accent, border: 'none', color: '#000', padding: '7px 16px', cursor: 'pointer', fontSize: '12px', fontWeight: 700, fontFamily: '"IBM Plex Mono", monospace' },
  cancelBtn: { background: 'transparent', border: '1px solid #333', color: C.dim, padding: '7px 14px', cursor: 'pointer', fontSize: '12px', fontFamily: '"IBM Plex Mono", monospace' },
  addError: { color: '#ef4444', fontSize: '12px' },
  loading: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: C.dim, fontSize: '12px' },
  grid: { flex: 1, overflowY: 'auto', padding: '20px 24px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px', alignContent: 'start' },
  card: { background: C.card, border: `2px solid ${C.border}`, display: 'flex', gap: '16px', padding: '18px', cursor: 'pointer', textAlign: 'left', transition: 'border-color .15s, box-shadow .15s', fontFamily: '"IBM Plex Mono", monospace', width: '100%' },
  avatar: { width: '48px', height: '48px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontSize: '16px', fontWeight: 700, overflow: 'hidden' },
  avatarImg: { width: '100%', height: '100%', objectFit: 'cover' },
  cardBody: { flex: 1, display: 'flex', flexDirection: 'column', gap: '6px', minWidth: 0 },
  cardTop: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' },
  name: { color: C.text, fontSize: '13px', fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  roleBadge: { border: '1px solid', color: C.dim, padding: '1px 6px', fontSize: '10px', letterSpacing: '1px', flexShrink: 0 },
  desc: { color: C.dim, fontSize: '12px', margin: 0, lineHeight: 1.4 },
  progressRow: { display: 'flex', alignItems: 'center', gap: '8px' },
  progressBar: { flex: 1, height: '4px', background: '#1e1e1e', overflow: 'hidden' },
  progressFill: { height: '100%', transition: 'width .4s' },
  pct: { color: C.dim, fontSize: '11px', flexShrink: 0 },
  kpis: { display: 'flex', gap: '14px' },
  kpi: { display: 'flex', flexDirection: 'column', gap: '1px' },
  kpiVal: { color: C.accent, fontSize: '16px', fontWeight: 700 },
  kpiLabel: { color: C.dim, fontSize: '10px', letterSpacing: '1px' },
  noMembers: { color: C.dim, fontSize: '13px', gridColumn: '1/-1', textAlign: 'center', padding: '40px' },
};
