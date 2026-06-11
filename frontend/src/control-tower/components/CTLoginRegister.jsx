// CTLoginRegister.jsx — Pantalla de Login/Registro del Control Tower
import React, { useState } from 'react';

export default function CTLoginRegister({ onLogin, onRegister, isLoading }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [form, setForm] = useState({ name: '', email: '', password: '', role_label: 'Colaborador' });
  const [err, setErr] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErr('');
    if (!form.email || !form.password) { setErr('Email y contraseña son obligatorios.'); return; }
    if (mode === 'register' && !form.name) { setErr('El nombre es obligatorio.'); return; }
    if (form.password.length < 6) { setErr('La contraseña debe tener al menos 6 caracteres.'); return; }

    const result = mode === 'login'
      ? await onLogin(form.email, form.password)
      : await onRegister(form);

    if (!result.ok) setErr(result.message || 'Error desconocido');
  };

  const quickLogin = () => onLogin('andres@finsys.os', 'admin123');

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4 font-mono">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="text-amber-400 text-5xl font-black tracking-widest mb-2">⬡</div>
          <h1 className="text-white text-3xl font-black uppercase tracking-widest">CONTROL TOWER</h1>
          <p className="text-amber-400 text-xs uppercase tracking-widest mt-1">
            FIN-SYS OS v2.0 // MULTI-ENTITY MANAGEMENT
          </p>
        </div>

        {/* Card */}
        <div className="border-4 border-amber-400 bg-black p-6 shadow-[8px_8px_0px_#fbbf24]">
          {/* Tabs */}
          <div className="flex mb-6 border-b-2 border-amber-400">
            {['login', 'register'].map(m => (
              <button
                key={m}
                onClick={() => { setMode(m); setErr(''); }}
                className={`flex-1 py-2 text-xs font-black uppercase tracking-widest transition-colors ${
                  mode === m
                    ? 'bg-amber-400 text-black'
                    : 'bg-black text-amber-400 hover:bg-amber-400/10'
                }`}
              >
                {m === 'login' ? '→ ACCEDER' : '+ REGISTRAR'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <>
                <div>
                  <label className="text-amber-400 text-[10px] font-bold uppercase block mb-1">
                    NOMBRE COMPLETO *
                  </label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                    placeholder="Ej: Juan Contador"
                    className="w-full bg-black border-2 border-amber-400/60 text-white p-2 text-sm font-mono outline-none focus:border-amber-400 transition-colors"
                  />
                </div>
                <div>
                  <label className="text-amber-400 text-[10px] font-bold uppercase block mb-1">
                    ROL / CARGO
                  </label>
                  <input
                    type="text"
                    value={form.role_label}
                    onChange={e => setForm(p => ({ ...p, role_label: e.target.value }))}
                    placeholder="Ej: Contador Externo, Auditor, Socio..."
                    className="w-full bg-black border-2 border-amber-400/60 text-white p-2 text-sm font-mono outline-none focus:border-amber-400 transition-colors"
                  />
                </div>
              </>
            )}

            <div>
              <label className="text-amber-400 text-[10px] font-bold uppercase block mb-1">EMAIL *</label>
              <input
                type="email"
                value={form.email}
                onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
                placeholder="correo@empresa.com"
                className="w-full bg-black border-2 border-amber-400/60 text-white p-2 text-sm font-mono outline-none focus:border-amber-400 transition-colors"
              />
            </div>

            <div>
              <label className="text-amber-400 text-[10px] font-bold uppercase block mb-1">CONTRASEÑA *</label>
              <input
                type="password"
                value={form.password}
                onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                placeholder="Mínimo 6 caracteres"
                className="w-full bg-black border-2 border-amber-400/60 text-white p-2 text-sm font-mono outline-none focus:border-amber-400 transition-colors"
              />
            </div>

            {err && (
              <div className="border border-red-500 bg-red-500/10 p-2 text-red-400 text-xs font-bold uppercase">
                ⚠ {err}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-amber-400 text-black py-3 font-black uppercase tracking-widest hover:bg-amber-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'PROCESANDO...' : (mode === 'login' ? 'ACCEDER AL TOWER' : 'CREAR CUENTA')}
            </button>
          </form>

          {/* Quick access for existing user */}
          <div className="mt-4 pt-4 border-t border-amber-400/30">
            <button
              onClick={quickLogin}
              disabled={isLoading}
              className="w-full border-2 border-amber-400/50 text-amber-400/80 py-2 text-xs font-bold uppercase hover:border-amber-400 hover:text-amber-400 transition-colors"
            >
              ⚡ CONTINUAR COMO ANDRÉS (DEMO)
            </button>
          </div>
        </div>

        <p className="text-center text-amber-400/40 text-[10px] uppercase tracking-widest mt-4">
          SYS.STATUS: ONLINE // SECURE_LOCAL // RSA-MOCK
        </p>
      </div>
    </div>
  );
}
