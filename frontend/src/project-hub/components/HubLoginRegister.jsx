/* ============================================================
   HubLoginRegister.jsx — Login y Registro del Project Hub
   Paleta: fondo #0a0a0a, acento cian #0EA5E9, brutalista
   ============================================================ */
import { useState } from 'react';

export default function HubLoginRegister({ onSuccess, loading, error: extError }) {
  const [mode, setMode]       = useState('login'); // 'login' | 'register' | 'workspace'
  const [form, setForm]       = useState({
    email: '', password: '', name: '', cedula: '',
    description: '', wsName: '', wsNit: '',
  });
  const [localError, setLocalError] = useState('');

  const err = extError || localError;

  const handleChange = (e) => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError('');
    if (!form.email || !form.password) { setLocalError('Email y contraseña requeridos'); return; }
    try {
      await onSuccess(mode, form);
    } catch (e) { setLocalError(e.message); }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.card}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.logo}>⬡</div>
          <h1 style={styles.title}>PROJECT HUB</h1>
          <p style={styles.subtitle}>FIN-SYS OS v2.0 — Módulo 08</p>
        </div>

        {/* Tabs */}
        <div style={styles.tabs}>
          {['login', 'register'].map(t => (
            <button key={t} style={{ ...styles.tab, ...(mode === t ? styles.tabActive : {}) }}
              onClick={() => setMode(t)}>
              {t === 'login' ? 'INICIAR SESIÓN' : 'REGISTRARSE'}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={styles.form}>
          {mode === 'register' && (
            <>
              <input name="name" placeholder="Nombre completo" value={form.name}
                onChange={handleChange} style={styles.input} />
              <input name="cedula" placeholder="Cédula / NIT" value={form.cedula}
                onChange={handleChange} style={styles.input} />
              <textarea name="description" placeholder="¿Qué haces? (descripción breve)"
                value={form.description} onChange={handleChange}
                style={{ ...styles.input, height: '64px', resize: 'none' }} />
            </>
          )}
          <input name="email" type="email" placeholder="Email" value={form.email}
            onChange={handleChange} style={styles.input} />
          <input name="password" type="password" placeholder="Contraseña" value={form.password}
            onChange={handleChange} style={styles.input} />

          {mode === 'register' && (
            <div style={styles.wsSection}>
              <p style={styles.wsLabel}>— Crear workspace (opcional) —</p>
              <input name="wsName" placeholder="Nombre de la organización" value={form.wsName}
                onChange={handleChange} style={styles.input} />
              <input name="wsNit" placeholder="NIT de la empresa" value={form.wsNit}
                onChange={handleChange} style={styles.input} />
            </div>
          )}

          {err && <div style={styles.error}>⚠ {err}</div>}

          <button type="submit" style={styles.btn} disabled={loading}>
            {loading ? 'PROCESANDO...' : mode === 'login' ? 'ENTRAR' : 'CREAR CUENTA'}
          </button>
        </form>
      </div>
    </div>
  );
}

const C = { bg: '#0a0a0a', card: '#111', border: '#0EA5E9', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  overlay: {
    position: 'absolute', inset: 0, background: C.bg,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  card: {
    background: C.card, border: `2px solid ${C.border}`,
    boxShadow: `6px 6px 0 ${C.border}`,
    padding: '40px', width: '420px', maxWidth: '95vw',
  },
  header: { textAlign: 'center', marginBottom: '28px' },
  logo: { fontSize: '48px', color: C.accent, lineHeight: 1 },
  title: { color: C.accent, fontSize: '20px', fontWeight: 700, letterSpacing: '4px', margin: '8px 0 4px' },
  subtitle: { color: C.dim, fontSize: '11px', letterSpacing: '1px' },
  tabs: { display: 'flex', borderBottom: `2px solid ${C.border}`, marginBottom: '24px' },
  tab: {
    flex: 1, padding: '10px', background: 'transparent', border: 'none',
    color: C.dim, fontSize: '11px', letterSpacing: '1px', cursor: 'pointer',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  tabActive: { color: C.accent, borderBottom: `2px solid ${C.accent}`, marginBottom: '-2px' },
  form: { display: 'flex', flexDirection: 'column', gap: '12px' },
  input: {
    background: '#1a1a1a', border: `2px solid #333`, color: C.text,
    padding: '10px 12px', fontSize: '13px', outline: 'none', width: '100%',
    boxSizing: 'border-box', fontFamily: '"IBM Plex Mono", monospace',
    transition: 'border-color .2s',
  },
  wsSection: { borderTop: `1px solid #333`, paddingTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' },
  wsLabel: { color: C.dim, fontSize: '11px', textAlign: 'center', margin: 0 },
  error: { background: '#1a0a0a', border: '2px solid #ef4444', color: '#ef4444', padding: '10px', fontSize: '12px' },
  btn: {
    background: C.accent, color: '#000', border: 'none', padding: '12px',
    fontSize: '13px', fontWeight: 700, letterSpacing: '2px', cursor: 'pointer',
    fontFamily: '"IBM Plex Mono", monospace', marginTop: '8px',
    boxShadow: `3px 3px 0 #0369a1`, transition: 'transform .1s, box-shadow .1s',
  },
};
