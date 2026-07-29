/* ============================================================
   MiCuenta.jsx — FICHA TÉCNICA del usuario logueado.
   Muestra la identidad completa de la persona (nombre, contacto,
   rol, cargo, antigüedad) + cambio de contraseña propia.
   PUT /hub/users/me/password
   ============================================================ */
import { useState } from 'react';
import { API } from '../config';
import { authHeaders } from './authHeaders.js';
import { useUser } from './providers/UserProvider.jsx';

const ROLE_COLOR = { owner: '#EF4444', admin: '#F59E0B', member: '#0EA5E9', viewer: '#64748b' };
const ROLE_LABEL = {
  owner:  'Propietario · control total del sistema',
  admin:  'Administrador · gestiona RRHH, usuarios y módulos',
  member: 'Miembro · ve su ficha y el equipo en solo-lectura',
  viewer: 'Observador · solo lectura básica',
};

function initialsOf(name, email) {
  const base = (name || email || 'U').trim();
  const parts = base.split(/[\s@._-]+/).filter(Boolean);
  return ((parts[0]?.[0] || 'U') + (parts[1]?.[0] || '')).toUpperCase();
}

function fmtDate(iso) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' });
  } catch { return null; }
}

export default function MiCuenta({ user }) {
  const hu = user?.raw?.user || {};
  const { workspaceName } = useUser();

  // Preferir los datos crudos del hub (rol granular, cédula, cargo, color…)
  const hubRole   = (hu.role || '').toLowerCase();
  const roleColor = ROLE_COLOR[hubRole] || 'var(--shell-green)';
  const name      = hu.name  || user?.name  || 'Usuario';
  const email     = hu.email || user?.email || '';
  const color     = hu.color || roleColor;
  const initials  = initialsOf(name, email);
  const since     = fmtDate(hu.created_at);

  const [form, setForm]   = useState({ old_password: '', new_password: '', confirm: '' });
  const [msg,  setMsg]    = useState(null);   // { ok, text }
  const [busy, setBusy]   = useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setMsg(null);
    if (form.new_password.length < 6) return setMsg({ ok: false, text: 'La nueva contraseña debe tener al menos 6 caracteres.' });
    if (form.new_password !== form.confirm) return setMsg({ ok: false, text: 'La confirmación no coincide.' });
    setBusy(true);
    try {
      const res = await fetch(`${API}/hub/users/me/password`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ old_password: form.old_password, new_password: form.new_password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
      setMsg({ ok: true, text: 'Contraseña actualizada.' });
      setForm({ old_password: '', new_password: '', confirm: '' });
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={S.wrap}>
      <div style={S.title}>FICHA TÉCNICA</div>

      {/* ── Cabecera de identidad ── */}
      <div style={S.card}>
        <div style={S.identity}>
          <div style={{ ...S.avatar, background: color, boxShadow: `4px 4px 0 ${color}` }}>
            {initials}
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={S.name}>{name}</div>
            <div style={S.email}>{email || 'Sin correo'}</div>
            <div style={{ ...S.roleChip, color: roleColor, borderColor: roleColor }}>
              {(hubRole || 'usuario').toUpperCase()}
            </div>
          </div>
        </div>
        <div style={S.roleDesc}>{ROLE_LABEL[hubRole] || 'Usuario del sistema'}</div>
      </div>

      {/* ── Datos de la cuenta ── */}
      <div style={S.card}>
        <div style={S.cardTitle}>DATOS DE LA PERSONA</div>
        <Row label="Nombre completo" value={name} />
        <Row label="Correo"          value={email} />
        <Row label="Cédula"          value={hu.cedula} />
        <Row label="Cargo / rol"     value={hu.description} full />
        <Row label="Espacio"         value={workspaceName} />
        <Row label="Miembro desde"   value={since} />
        <Row label="ID de usuario"   value={hu.id || user?.id} mono />
        <div style={S.hint}>
          Para cambiar tu nombre, correo, cédula o rol, contacta a un administrador
          (Panel Admin → Usuarios y Roles).
        </div>
      </div>

      {/* ── Cambio de contraseña ── */}
      <form style={S.card} onSubmit={submit}>
        <div style={S.cardTitle}>CAMBIAR CONTRASEÑA</div>
        <Field label="Contraseña actual" type="password" value={form.old_password}
          onChange={v => set('old_password', v)} autoComplete="current-password" />
        <Field label="Nueva contraseña" type="password" value={form.new_password}
          onChange={v => set('new_password', v)} autoComplete="new-password" />
        <Field label="Confirmar nueva" type="password" value={form.confirm}
          onChange={v => set('confirm', v)} autoComplete="new-password" />
        {msg && (
          <div style={{ ...S.msg, color: msg.ok ? '#00e676' : '#ff5252', borderColor: msg.ok ? '#00e676' : '#ff5252' }}>
            {msg.ok ? '✓ ' : '⚠ '}{msg.text}
          </div>
        )}
        <button type="submit" disabled={busy} style={S.btn}>
          {busy ? 'GUARDANDO…' : 'ACTUALIZAR CONTRASEÑA'}
        </button>
      </form>
    </div>
  );
}

function Row({ label, value, full, mono }) {
  return (
    <div style={{ ...S.row, ...(full ? S.rowFull : {}) }}>
      <span style={S.rowLabel}>{label}</span>
      <span style={{ ...S.rowValue, ...(full ? { textAlign: 'left' } : {}), ...(mono ? { fontSize: 10, color: '#64748b' } : {}) }}>
        {value || '—'}
      </span>
    </div>
  );
}

function Field({ label, value, onChange, type = 'text', autoComplete }) {
  return (
    <label style={S.field}>
      <span style={S.fieldLabel}>{label}</span>
      <input style={S.input} type={type} value={value} autoComplete={autoComplete}
        onChange={e => onChange(e.target.value)} />
    </label>
  );
}

const FF = "'IBM Plex Mono', monospace";
const S = {
  wrap:      { padding: 24, maxWidth: 580, margin: '0 auto', fontFamily: FF, display: 'flex', flexDirection: 'column', gap: 18 },
  title:     { color: '#00e676', fontSize: 15, fontWeight: 700, letterSpacing: 3 },
  card:      { background: '#111', border: '2px solid #1e1e1e', padding: 18, display: 'flex', flexDirection: 'column', gap: 10 },
  identity:  { display: 'flex', alignItems: 'center', gap: 16 },
  avatar:    { width: 56, height: 56, minWidth: 56, color: '#000', fontSize: 20, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FF },
  name:      { color: '#e2e8f0', fontSize: 16, fontWeight: 700, letterSpacing: 0.5, wordBreak: 'break-word' },
  email:     { color: '#94a3b8', fontSize: 11, marginTop: 2, wordBreak: 'break-word' },
  roleChip:  { display: 'inline-block', marginTop: 6, fontSize: 9, border: '1px solid', padding: '2px 8px', fontWeight: 700, letterSpacing: 1 },
  roleDesc:  { color: '#64748b', fontSize: 10, lineHeight: 1.5, borderTop: '1px solid #1e1e1e', paddingTop: 10 },
  cardTitle: { color: '#64748b', fontSize: 10, letterSpacing: 2, fontWeight: 700, borderBottom: '1px solid #1e1e1e', paddingBottom: 8, marginBottom: 4 },
  row:       { display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 12 },
  rowFull:   { flexDirection: 'column', gap: 4 },
  rowLabel:  { color: '#64748b', whiteSpace: 'nowrap' },
  rowValue:  { color: '#e2e8f0', fontWeight: 600, textAlign: 'right', wordBreak: 'break-word' },
  hint:      { color: '#475569', fontSize: 10, marginTop: 6, lineHeight: 1.5 },
  field:     { display: 'flex', flexDirection: 'column', gap: 4 },
  fieldLabel:{ color: '#64748b', fontSize: 9, letterSpacing: 1, textTransform: 'uppercase' },
  input:     { background: '#1a1a1a', border: '2px solid #333', color: '#e2e8f0', padding: '8px 10px', fontSize: 12, fontFamily: FF, outline: 'none' },
  msg:       { fontSize: 11, border: '1px solid', padding: '6px 8px' },
  btn:       { background: '#00e676', border: 'none', color: '#000', padding: '10px', cursor: 'pointer', fontSize: 11, fontWeight: 700, letterSpacing: 1, fontFamily: FF, marginTop: 4 },
};
