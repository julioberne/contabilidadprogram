/* ============================================================
   UsuariosPanel.jsx — Gestión de usuarios y roles (solo owner/admin).
   Lista todos los usuarios y permite cambiar su rol global.
   GET /hub/users/all · PUT /hub/users/{id}/role  (require_admin)
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import { API } from '../config';
import { authHeaders } from './authHeaders.js';

const ROLES = ['owner', 'admin', 'member', 'viewer'];
const ROLE_COLOR = { owner: '#EF4444', admin: '#F59E0B', member: '#0EA5E9', viewer: '#64748b' };
const ROLE_DESC = {
  owner:  'Control total del sistema',
  admin:  'Gestiona RRHH, usuarios y módulos',
  member: 'Ve su ficha; equipo en solo-lectura',
  viewer: 'Solo lectura básica',
};

export default function UsuariosPanel({ user }) {
  const isAdmin = user?.role === 'ADMIN';
  const [users,   setUsers]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');
  const [savingId, setSavingId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API}/hub/users/all`, { headers: authHeaders() });
      if (!res.ok) throw new Error(res.status === 403 ? 'Requiere rol administrador.' : `Error ${res.status}`);
      setUsers(await res.json());
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { if (isAdmin) load(); else setLoading(false); }, [isAdmin, load]);

  const changeRole = async (u, role) => {
    if (role === u.role) return;
    setSavingId(u.id); setError('');
    try {
      const res = await fetch(`${API}/hub/users/${u.id}/role`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ role }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
      setUsers(us => us.map(x => x.id === u.id ? { ...x, role } : x));
    } catch (e) { setError(e.message); }
    finally { setSavingId(null); }
  };

  if (!isAdmin) return (
    <div style={S.wrap}>
      <div style={S.title}>USUARIOS Y ROLES</div>
      <div style={S.block}>Solo un administrador u owner puede gestionar usuarios.</div>
    </div>
  );

  return (
    <div style={S.wrap}>
      <div style={S.title}>USUARIOS Y ROLES</div>
      <div style={S.sub}>
        Cambia el rol de cada persona. El rol define qué puede ver y hacer en todo el sistema
        (incluido el acceso a RRHH). {users.length} usuario{users.length !== 1 ? 's' : ''}.
      </div>

      {error && <div style={S.err}>⚠ {error}</div>}
      {loading ? <div style={S.block}>Cargando…</div> : (
        <div style={S.table}>
          <div style={{ ...S.tr, ...S.thead }}>
            <span>USUARIO</span><span>EMAIL</span><span>ROL</span><span>PERMISOS</span>
          </div>
          {users.map(u => {
            const canLogin = !!u.email;
            return (
              <div key={u.id} style={S.tr}>
                <span style={S.name}>
                  <span style={{ ...S.dot, background: ROLE_COLOR[u.role] || '#64748b' }} />
                  {u.name}
                </span>
                <span style={S.email}>
                  {u.email || <em style={{ color: '#475569' }}>sin login</em>}
                </span>
                <span>
                  <select
                    value={u.role}
                    disabled={savingId === u.id || !canLogin}
                    onChange={e => changeRole(u, e.target.value)}
                    title={!canLogin ? 'Sin email/login no puede tener acceso al sistema' : ''}
                    style={{ ...S.select, borderColor: ROLE_COLOR[u.role] || '#333', color: ROLE_COLOR[u.role] || '#e2e8f0' }}
                  >
                    {ROLES.map(r => <option key={r} value={r}>{r.toUpperCase()}</option>)}
                  </select>
                </span>
                <span style={S.desc}>{ROLE_DESC[u.role]}</span>
              </div>
            );
          })}
        </div>
      )}
      <div style={S.legend}>
        <b>owner/admin</b>: acceso completo a RRHH y gestión · <b>member</b>: ve su propia ficha
        y el equipo en solo-lectura · <b>viewer</b>: lectura básica.
      </div>
    </div>
  );
}

const FF = "'IBM Plex Mono', monospace";
const S = {
  wrap:   { padding: 24, fontFamily: FF, display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 900, margin: '0 auto' },
  title:  { color: '#00e676', fontSize: 15, fontWeight: 700, letterSpacing: 3 },
  sub:    { color: '#64748b', fontSize: 11, lineHeight: 1.6 },
  block:  { color: '#64748b', fontSize: 12, padding: 20, textAlign: 'center' },
  err:    { color: '#ff5252', border: '1px solid #ff5252', padding: '6px 10px', fontSize: 11 },
  table:  { border: '2px solid #1e1e1e', display: 'flex', flexDirection: 'column' },
  tr:     { display: 'grid', gridTemplateColumns: '1.4fr 1.6fr 130px 1.6fr', gap: 10, alignItems: 'center', padding: '9px 12px', borderBottom: '1px solid #1a1a1a', fontSize: 12 },
  thead:  { color: '#64748b', fontSize: 9, letterSpacing: 1.5, fontWeight: 700, background: '#0d0d0d' },
  name:   { color: '#e2e8f0', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  dot:    { width: 8, height: 8, flexShrink: 0 },
  email:  { color: '#94a3b8', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  select: { background: '#1a1a1a', border: '2px solid', padding: '5px 6px', fontSize: 11, fontFamily: FF, cursor: 'pointer', width: '100%' },
  desc:   { color: '#64748b', fontSize: 10 },
  legend: { color: '#475569', fontSize: 10, lineHeight: 1.6, borderTop: '1px solid #1e1e1e', paddingTop: 10 },
};
