/* ============================================================
   AdminConsole.jsx — Panel de Administración (SOLO owner/admin)
   Centro único desde donde el admin administra todo el sistema:
   RRHH · Contabilidad · Control Tower + usuarios, roles y módulos.
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import { API } from '../config';
import { authHeaders } from './authHeaders.js';

const ROLE_COLOR = { owner: '#EF4444', admin: '#F59E0B', member: '#0EA5E9', viewer: '#64748b' };

/* Tarjetas de administración → navegan a cada módulo/panel */
const ADMIN_MODULES = [
  { id: 'rrhh',            icon: '⊙', name: 'RRHH',           accent: 'blue',
    desc: 'Empleados · Nómina · Documentos\nPerfiles · Historial' },
  { id: 'contabilidad',   icon: '≡', name: 'Contabilidad',   accent: 'green',
    desc: 'Transacciones · CoA · Balances\nPortafolios · Activos · IVA' },
  { id: 'tower',          icon: '⬡', name: 'Control Tower',  accent: 'amber',
    desc: 'Holding · Empresas · Balance\nConsolidado · Árbol Corporativo' },
];

const SYSTEM_CARDS = [
  { id: 'usuarios',        icon: '⚑', name: 'Usuarios y Roles', accent: 'green',
    desc: 'Crear, editar y cambiar el rol\nde cada persona del sistema' },
  { id: 'module-settings', icon: '⚙', name: 'Módulos',          accent: 'green',
    desc: 'Activar o desactivar módulos\ndel sistema (feature flags)' },
];

function AdminCard({ card, onNavigate }) {
  return (
    <div
      className={`module-card module-card--${card.accent}`}
      id={`admin-card-${card.id}`}
      onClick={() => onNavigate(card.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onNavigate(card.id)}
    >
      <div className="module-card-icon">{card.icon}</div>
      <div className="module-card-name">{card.name}</div>
      <div className="module-card-desc">{card.desc}</div>
      <div className="module-card-status active">
        ADMINISTRAR <span className="module-card-arrow">→</span>
      </div>
    </div>
  );
}

export default function AdminConsole({ user, onNavigate, enabledIds }) {
  const [users,   setUsers]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API}/hub/users/all`, { headers: authHeaders() });
      if (!res.ok) throw new Error(res.status === 403 ? 'Requiere rol administrador.' : `Error ${res.status}`);
      setUsers(await res.json());
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const total     = users.length;
  const admins    = users.filter(u => u.role === 'owner' || u.role === 'admin').length;
  const conAcceso = users.filter(u => !!u.email).length;
  const modulos   = enabledIds ? enabledIds.size : '—';

  return (
    <div className="home-wrap">
      {/* ── Encabezado / identidad del admin ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={S.kicker}>PANEL DE ADMINISTRACIÓN</div>
          <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: 1, color: 'var(--shell-text)' }}>
            {user?.name || 'Administrador'} <span style={{ color: 'var(--shell-green)' }}>_</span>
          </div>
          <div style={{ fontSize: 9, color: 'var(--shell-dim)', letterSpacing: 1, marginTop: 2 }}>
            {user?.role} · {user?.email}
          </div>
        </div>
        <div style={S.adminBadge}>● ACCESO TOTAL</div>
      </div>

      {error && <div style={S.err}>⚠ {error}</div>}

      {/* ── KPIs del sistema ── */}
      <div>
        <div className="home-section-header">
          <span className="home-section-title">ESTADO DEL SISTEMA</span>
          <div className="home-section-line" />
          <span style={{ fontSize: 9, color: 'var(--shell-dim)', whiteSpace: 'nowrap' }}>
            {loading ? '● CARGANDO...' : '● LIVE'}
          </span>
        </div>
        <div className="home-kpis">
          <Kpi label="USUARIOS"        value={loading ? '...' : total}     sub="Total en el sistema" />
          <Kpi label="ADMINISTRADORES" value={loading ? '...' : admins}    sub="owner + admin" color="amber" />
          <Kpi label="CON ACCESO"      value={loading ? '...' : conAcceso} sub="Pueden iniciar sesión" />
          <Kpi label="MÓDULOS ACTIVOS" value={modulos}                     sub="Habilitados" color="green" />
        </div>
      </div>

      {/* ── Administrar módulos del negocio ── */}
      <div>
        <div className="home-section-header">
          <span className="home-section-title">ADMINISTRAR MÓDULOS</span>
          <div className="home-section-line" />
        </div>
        <div className="home-modules">
          {ADMIN_MODULES.map(c => <AdminCard key={c.id} card={c} onNavigate={onNavigate} />)}
        </div>
      </div>

      {/* ── Gestión del sistema ── */}
      <div>
        <div className="home-section-header">
          <span className="home-section-title">GESTIÓN DEL SISTEMA</span>
          <div className="home-section-line" />
        </div>
        <div className="home-modules">
          {SYSTEM_CARDS.map(c => <AdminCard key={c.id} card={c} onNavigate={onNavigate} />)}
        </div>
      </div>

      {/* ── Usuarios recientes (resumen) ── */}
      <div>
        <div className="home-section-header">
          <span className="home-section-title">USUARIOS DEL SISTEMA</span>
          <div className="home-section-line" />
          <button style={S.linkBtn} onClick={() => onNavigate('usuarios')}>
            GESTIONAR →
          </button>
        </div>
        <div style={S.table}>
          <div style={{ ...S.tr, ...S.thead }}>
            <span>USUARIO</span><span>EMAIL</span><span>ROL</span>
          </div>
          {loading ? (
            <div style={S.block}>Cargando…</div>
          ) : users.length === 0 ? (
            <div style={S.block}>Sin usuarios.</div>
          ) : users.map(u => (
            <div key={u.id} style={S.tr}>
              <span style={S.name}>
                <span style={{ ...S.dot, background: u.color || ROLE_COLOR[u.role] || '#64748b' }} />
                {u.name}
                {u.id === user?.id && <span style={S.youTag}>TÚ</span>}
              </span>
              <span style={S.email}>{u.email || <em style={{ color: '#475569' }}>sin login</em>}</span>
              <span style={{ ...S.roleTag, color: ROLE_COLOR[u.role] || '#e2e8f0', borderColor: ROLE_COLOR[u.role] || '#333' }}>
                {(u.role || '').toUpperCase()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Kpi({ label, value, sub, color = 'white' }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value ${color}`}>{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

const FF = "'IBM Plex Mono', monospace";
const S = {
  kicker:    { fontSize: 10, letterSpacing: 3, color: 'var(--shell-dim)', textTransform: 'uppercase', marginBottom: 4 },
  adminBadge:{ fontSize: 9, letterSpacing: 1.5, color: '#EF4444', border: '1px solid #EF4444', padding: '4px 10px', fontWeight: 700, whiteSpace: 'nowrap' },
  err:       { color: '#ff5252', border: '1px solid #ff5252', padding: '6px 10px', fontSize: 11, fontFamily: FF },
  linkBtn:   { background: 'transparent', border: 'none', color: 'var(--shell-green)', fontSize: 9, fontWeight: 700, letterSpacing: 1, cursor: 'pointer', fontFamily: FF, whiteSpace: 'nowrap' },
  table:     { border: '2px solid var(--shell-border-hi)', display: 'flex', flexDirection: 'column', fontFamily: FF },
  tr:        { display: 'grid', gridTemplateColumns: '1.6fr 1.8fr 100px', gap: 10, alignItems: 'center', padding: '9px 12px', borderBottom: '1px solid #1a1a1a', fontSize: 12 },
  thead:     { color: 'var(--shell-dim)', fontSize: 9, letterSpacing: 1.5, fontWeight: 700, background: '#0d0d0d' },
  block:     { color: 'var(--shell-dim)', fontSize: 12, padding: 20, textAlign: 'center' },
  name:      { color: 'var(--shell-text)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  dot:       { width: 8, height: 8, flexShrink: 0, borderRadius: '50%' },
  youTag:    { fontSize: 7, background: 'var(--shell-green)', color: '#000', padding: '1px 4px', fontWeight: 700, letterSpacing: 0.5 },
  email:     { color: '#94a3b8', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  roleTag:   { fontSize: 9, border: '1px solid', padding: '2px 6px', fontWeight: 700, letterSpacing: 0.5, textAlign: 'center' },
};
