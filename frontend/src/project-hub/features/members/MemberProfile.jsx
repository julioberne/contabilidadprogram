/* ============================================================
   MemberProfile.jsx — Perfil individual con sistema de pestañas
   Pestañas: Rendimiento (existente) | Ficha RRHH | Salario
   FASE 5 original + Módulo 08c RRHH
   ============================================================ */
import { useState } from 'react';
import HRProfileTab  from './tabs/HRProfileTab';
import SalaryTab     from './tabs/SalaryTab';
import DocumentsTab  from './tabs/DocumentsTab';
import HistorialTab  from './tabs/HistorialTab';
import MemberTasksBreakdown from './MemberTasksBreakdown';
import { API_HUB } from '../../../config';

const ROLES = ['owner', 'admin', 'member', 'viewer'];

const TABS = [
  { id: 'rendimiento', label: 'RENDIMIENTO' },
  { id: 'rrhh',        label: 'FICHA RRHH'  },
  { id: 'salario',     label: 'SALARIO'      },
  { id: 'documentos',  label: 'DOCUMENTOS'  },
  { id: 'historial',   label: 'HISTORIAL'   },
];

export default function MemberProfile({ member, metrics, workspace, currentUser, onBack, onSaved, onRemoved }) {
  const [activeTab, setActiveTab] = useState('rendimiento');
  const [editing,   setEditing]   = useState(false);
  const [form,      setForm]      = useState({});
  const [saving,    setSaving]    = useState(false);
  const [editError, setEditError] = useState('');

  const isAdmin = currentUser?.role === 'owner' || currentUser?.role === 'admin' || currentUser?.is_superuser;

  if (!member) return null;

  const startEdit = () => {
    setEditError('');
    setForm({
      name: member.name || '', role: member.role || 'member',
      cedula: member.cedula || '', email: member.email || '',
      description: member.description || '',
    });
    setEditing(true);
  };

  const saveEdit = async () => {
    if (!form.name.trim()) { setEditError('El nombre es obligatorio.'); return; }
    setSaving(true); setEditError('');
    try {
      const res = await fetch(`${API_HUB}/users/${member.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace_id: workspace.id, ...form }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
      setEditing(false);
      onSaved?.(data.member);
    } catch (e) { setEditError(e.message); }
    finally { setSaving(false); }
  };

  const removeMember = async () => {
    if (!confirm(`¿Quitar a "${member.name}" de ${workspace.name}?\n\nSe desvincula del equipo; su ficha de usuario no se borra.`)) return;
    try {
      const res = await fetch(`${API_HUB}/users/${member.id}?workspace_id=${workspace.id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      onRemoved?.();
    } catch (e) { setEditError(e.message); }
  };

  const done    = metrics?.tasks_done    || 0;
  const pending = metrics?.tasks_pending || 0;
  const overdue = metrics?.tasks_overdue || 0;
  const avgHrs  = metrics?.avg_hours_to_complete
    ? parseFloat(metrics.avg_hours_to_complete).toFixed(1)
    : null;
  const total   = done + pending;
  const pct     = total > 0 ? Math.round((done / total) * 100) : 0;

  const initials = member.name?.slice(0, 2).toUpperCase() || '??';
  const color    = member.color || '#0EA5E9';

  return (
    <div style={styles.root}>
      {/* Back */}
      <button style={styles.back} onClick={onBack}>‹ VOLVER AL EQUIPO</button>

      {/* Perfil card — siempre visible en todas las pestañas */}
      <div style={styles.profileCard}>
        <div style={{ ...styles.avatar, background: color, boxShadow: `4px 4px 0 ${color}88` }}>
          {member.avatar_url
            ? <img src={member.avatar_url} alt={member.name} style={styles.avatarImg} />
            : initials}
        </div>

        {!editing ? (
          <>
            <div style={styles.profileInfo}>
              <h2 style={styles.name}>{member.name}</h2>
              <div style={styles.meta}>
                <span style={{ ...styles.roleBadge, borderColor: getRoleColor(member.role), color: getRoleColor(member.role) }}>
                  {member.role?.toUpperCase()}
                </span>
                {member.cedula && <span style={styles.metaItem}>CC {member.cedula}</span>}
                {member.email
                  ? <span style={styles.metaItem}>{member.email}</span>
                  : <span style={{ ...styles.metaItem, fontStyle: 'italic', color: '#475569' }}>sin login</span>}
              </div>
              {member.description && <p style={styles.desc}>{member.description}</p>}
            </div>
            {isAdmin && (
              <div style={styles.actions}>
                <button style={styles.editBtn} onClick={startEdit}>✎ EDITAR</button>
                <button style={styles.removeBtn} onClick={removeMember}>✕ QUITAR</button>
              </div>
            )}
          </>
        ) : (
          <div style={styles.editForm}>
            <div style={styles.editGrid}>
              <label style={styles.field}>
                <span style={styles.fieldLabel}>Nombre *</span>
                <input style={styles.input} value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              </label>
              <label style={styles.field}>
                <span style={styles.fieldLabel}>Rol / Función</span>
                <select style={styles.input} value={form.role}
                  onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
                  {ROLES.map(r => <option key={r} value={r}>{r.toUpperCase()}</option>)}
                </select>
              </label>
              <label style={styles.field}>
                <span style={styles.fieldLabel}>Cédula</span>
                <input style={styles.input} value={form.cedula}
                  onChange={e => setForm(f => ({ ...f, cedula: e.target.value }))} />
              </label>
              <label style={styles.field}>
                <span style={styles.fieldLabel}>Email (login opcional)</span>
                <input style={styles.input} value={form.email} placeholder="sin login"
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
              </label>
            </div>
            <label style={styles.field}>
              <span style={styles.fieldLabel}>Descripción / Funciones</span>
              <textarea style={{ ...styles.input, minHeight: '54px', resize: 'vertical' }} value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </label>
            {editError && <span style={styles.err}>{editError}</span>}
            <div style={styles.editActions}>
              <button style={styles.saveBtn} onClick={saveEdit} disabled={saving}>
                {saving ? 'GUARDANDO…' : '✔ GUARDAR'}
              </button>
              <button style={styles.cancelBtn} onClick={() => setEditing(false)} disabled={saving}>CANCELAR</button>
            </div>
          </div>
        )}
      </div>

      {/* ── TABS ──────────────────────────────────────────────── */}
      <div style={styles.tabs}>
        {TABS.map(tab => (
          <button key={tab.id}
            style={{
              ...styles.tab,
              color:        activeTab === tab.id ? '#0EA5E9' : '#64748b',
              borderBottom: activeTab === tab.id ? '2px solid #0EA5E9' : '2px solid transparent',
            }}
            onClick={() => setActiveTab(tab.id)}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── TAB CONTENT ───────────────────────────────────────── */}
      <div style={styles.tabContent}>

        {/* RENDIMIENTO — vista original sin cambios */}
        {activeTab === 'rendimiento' && (
          <div style={styles.content}>
            <div style={styles.metricsGrid}>
              <MetricCard label="TAREAS COMPLETADAS" value={done}    color="#10B981" icon="✓" />
              <MetricCard label="EN PROGRESO"         value={pending} color="#0EA5E9" icon="◈" />
              <MetricCard label="VENCIDAS"             value={overdue} color="#EF4444" icon="⚠" />
              {avgHrs && <MetricCard label="TIEMPO PROMEDIO" value={`${avgHrs}h`} color="#F59E0B" icon="◷" />}
            </div>

            <div style={styles.section}>
              <div style={styles.sectionHeader}>
                <span style={styles.sectionLabel}>RENDIMIENTO GLOBAL</span>
                <span style={{ color, fontWeight: 700, fontSize: '14px', fontFamily: '"IBM Plex Mono", monospace' }}>{pct}%</span>
              </div>
              <div style={styles.bigBar}>
                <div style={{ ...styles.bigBarFill, width: `${pct}%`, background: color }} />
              </div>
              <p style={styles.barCaption}>{done} de {total} tareas completadas</p>
            </div>

            {/* Desglose real de tareas: agrupado por estado, con proyecto/empresa */}
            <div style={styles.section}>
              <MemberTasksBreakdown member={member} workspace={workspace} />
            </div>

            {member.joined_at && (
              <div style={styles.section}>
                <span style={styles.sectionLabel}>MIEMBRO DESDE</span>
                <p style={styles.joinDate}>
                  {new Date(member.joined_at).toLocaleDateString('es-CO', {
                    day: '2-digit', month: 'long', year: 'numeric'
                  })}
                </p>
              </div>
            )}
          </div>
        )}

        {/* FICHA RRHH */}
        {activeTab === 'rrhh' && (
          <HRProfileTab
            member={member}
            workspace={workspace}
            currentUser={currentUser}
          />
        )}

        {/* SALARIO */}
        {activeTab === 'salario' && (
          <SalaryTab
            member={member}
            workspace={workspace}
            currentUser={currentUser}
          />
        )}

        {/* DOCUMENTOS */}
        {activeTab === 'documentos' && (
          <DocumentsTab
            member={member}
            workspace={workspace}
            currentUser={currentUser}
          />
        )}

        {/* HISTORIAL DE PAGOS */}
        {activeTab === 'historial' && (
          <HistorialTab
            member={member}
            workspace={workspace}
            currentUser={currentUser}
          />
        )}

      </div>
    </div>
  );
}

function MetricCard({ label, value, color, icon }) {
  return (
    <div style={{ ...cardStyles.root, borderTopColor: color }}>
      <span style={{ ...cardStyles.icon, color }}>{icon}</span>
      <span style={cardStyles.value}>{value}</span>
      <span style={cardStyles.label}>{label}</span>
    </div>
  );
}

function getRoleColor(role) {
  return { owner: '#EF4444', admin: '#F59E0B', member: '#0EA5E9', viewer: '#64748b' }[role] || '#64748b';
}

const C = { bg: '#0a0a0a', card: '#111', border: '#1e1e1e', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  root:        { display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', background: C.bg, fontFamily: '"IBM Plex Mono", monospace' },
  back:        { background: 'transparent', border: 'none', color: C.accent, padding: '12px 24px', cursor: 'pointer', fontSize: '12px', letterSpacing: '1px', textAlign: 'left', borderBottom: `1px solid ${C.border}`, fontFamily: '"IBM Plex Mono", monospace' },
  profileCard: { display: 'flex', gap: '24px', alignItems: 'flex-start', padding: '16px 20px', borderBottom: `1px solid ${C.border}`, flexWrap: 'wrap', flexShrink: 0 },
  avatar:      { width: '80px', height: '80px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontSize: '24px', fontWeight: 700, overflow: 'hidden' },
  avatarImg:   { width: '100%', height: '100%', objectFit: 'cover' },
  profileInfo: { flex: 1, display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '200px' },
  actions:     { display: 'flex', flexDirection: 'column', gap: '6px', flexShrink: 0 },
  editBtn:     { background: 'transparent', border: '1px solid #0EA5E9', color: '#0EA5E9', padding: '6px 12px', cursor: 'pointer', fontSize: '10px', letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace' },
  removeBtn:   { background: 'transparent', border: '1px solid #EF4444', color: '#EF4444', padding: '6px 12px', cursor: 'pointer', fontSize: '10px', letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace' },
  editForm:    { flex: 1, display: 'flex', flexDirection: 'column', gap: '10px', minWidth: '260px' },
  editGrid:    { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' },
  field:       { display: 'flex', flexDirection: 'column', gap: '3px' },
  fieldLabel:  { color: '#64748b', fontSize: '9px', letterSpacing: '1px', textTransform: 'uppercase' },
  input:       { background: '#1a1a1a', border: '2px solid #333', color: '#e2e8f0', padding: '7px 9px', fontSize: '12px', fontFamily: '"IBM Plex Mono", monospace', outline: 'none' },
  err:         { color: '#EF4444', fontSize: '11px' },
  editActions: { display: 'flex', gap: '8px' },
  saveBtn:     { background: '#0EA5E9', border: 'none', color: '#000', padding: '8px 18px', cursor: 'pointer', fontSize: '11px', fontWeight: 700, letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace' },
  cancelBtn:   { background: 'transparent', border: '1px solid #333', color: '#64748b', padding: '8px 16px', cursor: 'pointer', fontSize: '11px', letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace' },
  name:        { color: C.text, fontSize: '20px', margin: 0, letterSpacing: '-0.5px', wordBreak: 'break-word' },
  meta:        { display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' },
  roleBadge:   { border: '1px solid', padding: '2px 8px', fontSize: '10px', letterSpacing: '2px' },
  metaItem:    { color: C.dim, fontSize: '11px' },
  desc:        { color: C.dim, fontSize: '12px', lineHeight: 1.6, margin: 0, maxWidth: '500px', wordBreak: 'break-word' },
  tabs:        { display: 'flex', borderBottom: `2px solid ${C.border}`, flexShrink: 0 },
  tab:         { background: 'transparent', border: 'none', padding: '10px 20px', cursor: 'pointer', fontSize: '11px', letterSpacing: '1.5px', fontFamily: '"IBM Plex Mono", monospace', transition: 'color .15s' },
  tabContent:  { flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', minWidth: 0 },
  content:     { flex: 1, overflowY: 'auto', overflowX: 'hidden', padding: '20px' },
  metricsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '14px', marginBottom: '24px' },
  section:     { marginBottom: '24px' },
  sectionHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' },
  sectionLabel:  { color: C.dim, fontSize: '10px', letterSpacing: '2px' },
  bigBar:      { height: '12px', background: '#1e1e1e', overflow: 'hidden', border: `1px solid ${C.border}` },
  bigBarFill:  { height: '100%', transition: 'width .6s ease' },
  barCaption:  { color: C.dim, fontSize: '11px', margin: '6px 0 0' },
  joinDate:    { color: C.text, fontSize: '13px', margin: '4px 0 0' },
};

const cardStyles = {
  root:  { background: '#111', borderTop: '3px solid', padding: '16px', display: 'flex', flexDirection: 'column', gap: '4px' },
  icon:  { fontSize: '20px' },
  value: { color: '#e2e8f0', fontSize: '28px', fontWeight: 700, letterSpacing: '-1px', fontFamily: '"IBM Plex Mono", monospace' },
  label: { color: '#64748b', fontSize: '9px', letterSpacing: '2px', fontFamily: '"IBM Plex Mono", monospace' },
};
