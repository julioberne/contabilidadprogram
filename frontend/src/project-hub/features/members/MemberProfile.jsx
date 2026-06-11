/* ============================================================
   MemberProfile.jsx — Perfil individual con historial de tareas
   FASE 5
   ============================================================ */

export default function MemberProfile({ member, metrics, onBack }) {
  if (!member) return null;

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

      <div style={styles.content}>
        {/* Perfil card */}
        <div style={styles.profileCard}>
          {/* Avatar grande */}
          <div style={{ ...styles.avatar, background: color, boxShadow: `4px 4px 0 ${color}88` }}>
            {member.avatar_url
              ? <img src={member.avatar_url} alt={member.name} style={styles.avatarImg} />
              : initials}
          </div>

          <div style={styles.profileInfo}>
            <h2 style={styles.name}>{member.name}</h2>
            <div style={styles.meta}>
              <span style={{ ...styles.roleBadge, borderColor: getRoleColor(member.role), color: getRoleColor(member.role) }}>
                {member.role?.toUpperCase()}
              </span>
              {member.cedula && (
                <span style={styles.metaItem}>CC {member.cedula}</span>
              )}
              <span style={styles.metaItem}>{member.email}</span>
            </div>
            {member.description && (
              <p style={styles.desc}>{member.description}</p>
            )}
          </div>
        </div>

        {/* Métricas principales */}
        <div style={styles.metricsGrid}>
          <MetricCard label="TAREAS COMPLETADAS" value={done} color="#10B981" icon="✓" />
          <MetricCard label="EN PROGRESO" value={pending} color="#0EA5E9" icon="◈" />
          <MetricCard label="VENCIDAS" value={overdue} color="#EF4444" icon="⚠" />
          {avgHrs && <MetricCard label="TIEMPO PROMEDIO" value={`${avgHrs}h`} color="#F59E0B" icon="◷" />}
        </div>

        {/* Barra de progreso global */}
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

        {/* Fecha de unión */}
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
  root: { display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', background: C.bg, fontFamily: '"IBM Plex Mono", monospace' },
  back: { background: 'transparent', border: 'none', color: C.accent, padding: '12px 24px', cursor: 'pointer', fontSize: '12px', letterSpacing: '1px', textAlign: 'left', borderBottom: `1px solid ${C.border}`, fontFamily: '"IBM Plex Mono", monospace' },
  content: { flex: 1, overflowY: 'auto', padding: '24px' },
  profileCard: { display: 'flex', gap: '24px', alignItems: 'flex-start', marginBottom: '28px', flexWrap: 'wrap' },
  avatar: { width: '80px', height: '80px', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000', fontSize: '24px', fontWeight: 700, overflow: 'hidden' },
  avatarImg: { width: '100%', height: '100%', objectFit: 'cover' },
  profileInfo: { flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' },
  name: { color: C.text, fontSize: '22px', margin: 0, letterSpacing: '-0.5px' },
  meta: { display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' },
  roleBadge: { border: '1px solid', padding: '2px 8px', fontSize: '10px', letterSpacing: '2px' },
  metaItem: { color: C.dim, fontSize: '11px' },
  desc: { color: C.dim, fontSize: '12px', lineHeight: 1.6, margin: 0, maxWidth: '500px' },
  metricsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '14px', marginBottom: '24px' },
  section: { marginBottom: '24px' },
  sectionHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' },
  sectionLabel: { color: C.dim, fontSize: '10px', letterSpacing: '2px' },
  bigBar: { height: '12px', background: '#1e1e1e', overflow: 'hidden', border: `1px solid ${C.border}` },
  bigBarFill: { height: '100%', transition: 'width .6s ease' },
  barCaption: { color: C.dim, fontSize: '11px', margin: '6px 0 0' },
  joinDate: { color: C.text, fontSize: '13px', margin: '4px 0 0' },
};

const cardStyles = {
  root: { background: '#111', borderTop: '3px solid', padding: '16px', display: 'flex', flexDirection: 'column', gap: '4px' },
  icon: { fontSize: '20px' },
  value: { color: '#e2e8f0', fontSize: '28px', fontWeight: 700, letterSpacing: '-1px', fontFamily: '"IBM Plex Mono", monospace' },
  label: { color: '#64748b', fontSize: '9px', letterSpacing: '2px', fontFamily: '"IBM Plex Mono", monospace' },
};
