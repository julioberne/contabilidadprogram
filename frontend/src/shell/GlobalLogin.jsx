/* ============================================================
   GlobalLogin.jsx — Pantalla de login único del Shell
   Identidad: Retro-Brutalista · IBM Plex Mono · verde #00ff88
   ============================================================ */
import { useState } from 'react';
import './shell.css';

export default function GlobalLogin({ onLogin, loading, error: extError }) {
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [localErr, setLocalErr] = useState('');
  const err = extError || localErr;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalErr('');
    if (!email || !password) {
      setLocalErr('Email y contraseña son obligatorios.');
      return;
    }
    await onLogin(email, password);
  };

  return (
    <div className="login-overlay">
      <div className="login-card">
        <div className="login-logo">▣</div>
        <h1 className="login-title">FIN-SYS OS</h1>
        <p className="login-subtitle">v2.0 — ENTERPRISE RESOURCE PLATFORM</p>

        <form onSubmit={handleSubmit}>
          <input
            id="shell-login-email"
            className="login-input"
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            autoComplete="username"
            autoFocus
          />
          <input
            id="shell-login-password"
            className="login-input"
            type="password"
            placeholder="Contraseña"
            value={password}
            onChange={e => setPassword(e.target.value)}
            autoComplete="current-password"
          />

          {err && <div className="login-error">⚠ {err}</div>}

          <button
            id="shell-login-submit"
            className="login-btn"
            type="submit"
            disabled={loading}
          >
            {loading ? 'AUTENTICANDO...' : 'ENTRAR AL SISTEMA'}
          </button>
        </form>

        <p style={{
          marginTop: 20,
          fontSize: 9,
          color: '#333',
          textAlign: 'center',
          letterSpacing: 1,
          fontFamily: 'IBM Plex Mono, monospace',
        }}>
          FIN-SYS OS v2.0 · ACCESO RESTRINGIDO
        </p>
      </div>
    </div>
  );
}
