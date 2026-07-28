/* ============================================================
   MiCuenta.jsx — Vista de cuenta personal del usuario logueado.
   Ver datos propios + cambiar contraseña (PUT /hub/users/me/password).
   ============================================================ */
import { useState } from 'react';
import { API } from '../config';
import { authHeaders } from './authHeaders.js';

export default function MiCuenta({ user }) {
  const hu = user?.raw?.user || {};
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
      <div style={S.title}>MI CUENTA</div>

      {/* Datos personales (solo lectura) */}
      <div style={S.card}>
        <div style={S.cardTitle}>DATOS DE LA CUENTA</div>
        <Row label="Nombre"  value={user?.name} />
        <Row label="Email"   value={user?.email} />
        <Row label="Rol"     value={(user?.role || '').toUpperCase()} />
        {hu.cedula && <Row label="Cédula" value={hu.cedula} />}
        <div style={S.hint}>
          Para cambiar tu nombre, email o rol, contacta a un administrador (panel Usuarios y Roles).
        </div>
      </div>

      {/* Cambio de contraseña */}
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

function Row({ label, value }) {
  return (
    <div style={S.row}>
      <span style={S.rowLabel}>{label}</span>
      <span style={S.rowValue}>{value || '—'}</span>
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
  wrap:      { padding: 24, maxWidth: 560, margin: '0 auto', fontFamily: FF, display: 'flex', flexDirection: 'column', gap: 18 },
  title:     { color: '#00e676', fontSize: 15, fontWeight: 700, letterSpacing: 3 },
  card:      { background: '#111', border: '2px solid #1e1e1e', padding: 18, display: 'flex', flexDirection: 'column', gap: 10 },
  cardTitle: { color: '#64748b', fontSize: 10, letterSpacing: 2, fontWeight: 700, borderBottom: '1px solid #1e1e1e', paddingBottom: 8, marginBottom: 4 },
  row:       { display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 12 },
  rowLabel:  { color: '#64748b' },
  rowValue:  { color: '#e2e8f0', fontWeight: 600, textAlign: 'right', wordBreak: 'break-word' },
  hint:      { color: '#475569', fontSize: 10, marginTop: 6, lineHeight: 1.5 },
  field:     { display: 'flex', flexDirection: 'column', gap: 4 },
  fieldLabel:{ color: '#64748b', fontSize: 9, letterSpacing: 1, textTransform: 'uppercase' },
  input:     { background: '#1a1a1a', border: '2px solid #333', color: '#e2e8f0', padding: '8px 10px', fontSize: 12, fontFamily: FF, outline: 'none' },
  msg:       { fontSize: 11, border: '1px solid', padding: '6px 8px' },
  btn:       { background: '#00e676', border: 'none', color: '#000', padding: '10px', cursor: 'pointer', fontSize: 11, fontWeight: 700, letterSpacing: 1, fontFamily: FF, marginTop: 4 },
};
