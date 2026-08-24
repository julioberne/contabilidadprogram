/* ============================================================
   AccountsPulse.jsx — Pulso de cuentas con tabs por portafolio
   y vínculos N:M (account_portfolio_links).

   Modelo: una cuenta SIN vínculos es COMPARTIDA (visible en todos
   los portafolios); con vínculos, visible SOLO en esos. Varias
   empresas pueden compartir una cuenta, y cada empresa puede crear
   y vincular las suyas.

   UX por tab (portafolio):
     · 🔗 VINCULAR: trae una cuenta existente a esta empresa
     · ＋ NUEVA CUENTA: se crea ya vinculada a esta empresa
     · columna VISIBLE EN: chips (× desvincula, + agrega vínculo)
     · Σ total por moneda al pie = el valor de esta empresa
   El "▸" marca el portafolio ACTIVO; la tab lo sigue (sincrónica)
   pero se puede inspeccionar otra empresa sin cambiar dónde se
   trabaja. Δ movimientos viene de transacciones REALES; actual ≠
   esperado ⇒ DESCUADRE (ajuste manual o falta ⟳ Reconciliar).
   ============================================================ */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { API } from '../../../config';
import { useEmpresa } from '../../engine/EmpresaProvider.jsx';

const TODAS = '__TODAS__';
const TIPOS = ['Ahorros', 'Corriente', 'Crédito', 'Efectivo', 'Billetera', 'Crypto'];

const fmt = (v, currency = 'COP') => {
  const n = Number(v || 0);
  const s = '$' + Math.abs(n).toLocaleString('es-CO', { maximumFractionDigits: 0 });
  return (n < 0 ? '-' : '') + s + (currency !== 'COP' ? ` ${currency}` : '');
};

const mono = { fontFamily: '"IBM Plex Mono", monospace' };
const S = {
  tab: (active, esActivo) => ({
    ...mono, fontSize: 9, fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase',
    padding: '3px 8px', border: '1px solid #000',
    borderBottom: active ? 'none' : '1px solid #000',
    background: active ? '#fff' : esActivo ? '#dcfce7' : '#f0f0f0',
    color: active ? '#000' : '#555', cursor: 'pointer', marginRight: 2,
  }),
  th: { padding: '3px 8px', fontSize: 8, fontWeight: 700, letterSpacing: 1.5, textAlign: 'right', color: '#888', textTransform: 'uppercase' },
  td: { padding: '3px 8px', fontSize: 10, textAlign: 'right' },
  toolBtn: (on) => ({
    ...mono, fontSize: 8, fontWeight: 700, letterSpacing: 0.5, textTransform: 'uppercase',
    padding: '2px 6px', border: '1px solid #000', cursor: 'pointer',
    background: on ? '#000' : '#fff', color: on ? '#fff' : '#000', marginLeft: 4,
  }),
  miniInput: { ...mono, fontSize: 9, padding: '2px 4px', border: '1px solid #000' },
  chip: { display: 'inline-flex', alignItems: 'center', gap: 2, fontSize: 8, fontWeight: 700,
          background: '#dcfce7', border: '1px solid #000', padding: '0 3px', marginRight: 2, marginBottom: 1 },
};

export default function AccountsPulse() {
  const { portfolios = [], activePortfolio, fetchAll } = useEmpresa();
  const [accounts, setAccounts] = useState([]);
  const [tab, setTab] = useState(activePortfolio || TODAS);
  const [busy, setBusy] = useState(false);
  const [addingLinkTo, setAddingLinkTo] = useState(null);   // id de cuenta con "+" abierto
  const [linkPickerOpen, setLinkPickerOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [nueva, setNueva] = useState({ name: '', type: 'Ahorros', currency: 'COP', initial_balance: '' });
  const timerRef = useRef(null);

  const cargar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/accounts`);
      if (r.ok) setAccounts(await r.json());
    } catch { /* siguiente tick */ }
  }, []);

  useEffect(() => {
    cargar();
    timerRef.current = setInterval(cargar, 15000);
    return () => clearInterval(timerRef.current);
  }, [cargar]);

  // Sincrónica: la tab sigue al portafolio activo
  useEffect(() => { if (activePortfolio) setTab(activePortfolio); }, [activePortfolio]);

  const refrescar = async () => { await cargar(); fetchAll?.(); };

  const vincular = async (accountId, portfolioName) => {
    setBusy(true);
    try {
      await fetch(`${API}/accounts/${accountId}/links`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio_name: portfolioName }),
      });
      await refrescar();
    } finally { setBusy(false); setAddingLinkTo(null); setLinkPickerOpen(false); }
  };

  const desvincular = async (accountId, portfolioName) => {
    setBusy(true);
    try {
      await fetch(`${API}/accounts/${accountId}/links?portfolio_name=${encodeURIComponent(portfolioName)}`,
                  { method: 'DELETE' });
      await refrescar();
    } finally { setBusy(false); }
  };

  const crearCuenta = async (e) => {
    e.preventDefault();
    if (!nueva.name.trim() || tab === TODAS) return;
    setBusy(true);
    try {
      await fetch(`${API}/accounts`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: nueva.name.trim(), type: nueva.type, currency: nueva.currency,
          initial_balance: parseFloat(nueva.initial_balance) || 0,
          portfolio: tab,                 // nace vinculada a ESTA empresa
        }),
      });
      setNueva({ name: '', type: 'Ahorros', currency: 'COP', initial_balance: '' });
      setCreating(false);
      await refrescar();
    } finally { setBusy(false); }
  };

  if (!accounts.length && tab === TODAS) return null;

  const esVisible = (a) => !a.portfolio_links?.length || a.portfolio_links.includes(tab);
  const visibles = tab === TODAS ? accounts : accounts.filter(esVisible);
  // Cuentas de otros portafolios que se pueden traer a esta tab
  const vinculables = tab === TODAS ? [] : accounts.filter(a => !esVisible(a));

  const descuadres = visibles.filter(a =>
    a.expected_balance !== undefined &&
    Math.abs(Number(a.current_balance || 0) - Number(a.expected_balance || 0)) > 1);

  const totales = visibles.reduce((acc, a) => {
    const cur = a.currency || 'COP';
    acc[cur] = (acc[cur] || 0) + Number(a.current_balance || 0);
    return acc;
  }, {});

  return (
    <div style={{ border: '2px solid #000', background: '#fff', marginBottom: 8, ...mono, boxShadow: '3px 3px 0 #000' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 8px', borderBottom: '1px solid #ddd', background: '#fafafa' }}>
        <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: 2, color: '#888', textTransform: 'uppercase' }}>
          💳 PULSO DE CUENTAS
        </span>
        {descuadres.length > 0 && (
          <span title="El saldo actual no coincide con inicial + transacciones: ajuste manual o falta Reconciliar (💳 Cuentas → ⟳)."
                style={{ fontSize: 8, color: '#b45309', background: '#fef3c7', border: '1px solid #fbbf24', padding: '0 4px' }}>
            {descuadres.length} DESCUADRE(S)
          </span>
        )}
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 8, color: '#aaa' }}>sin chips = compartida (visible en todos)</span>
      </div>

      {/* Tabs por portafolio + acciones de la tab */}
      <div style={{ display: 'flex', alignItems: 'center', padding: '4px 8px 0 8px', background: '#fafafa', borderBottom: '1px solid #000', flexWrap: 'wrap' }}>
        <button style={S.tab(tab === TODAS, false)} onClick={() => setTab(TODAS)}>TODAS</button>
        {portfolios.map(p => (
          <button key={p.id} style={S.tab(tab === p.name, p.name === activePortfolio)}
                  onClick={() => setTab(p.name)}
                  title={p.name === activePortfolio ? 'Portafolio ACTIVO (donde registras ahora)' : `Ver cuentas de ${p.name}`}>
            {p.name === activePortfolio ? '▸ ' : ''}{p.name}
          </button>
        ))}
        <span style={{ flex: 1 }} />
        {tab !== TODAS && (
          <span style={{ paddingBottom: 3 }}>
            <button style={S.toolBtn(linkPickerOpen)} disabled={busy}
                    onClick={() => { setLinkPickerOpen(v => !v); setCreating(false); }}
                    title="Traer una cuenta existente a esta empresa">🔗 VINCULAR</button>
            <button style={S.toolBtn(creating)} disabled={busy}
                    onClick={() => { setCreating(v => !v); setLinkPickerOpen(false); }}
                    title="Crear una cuenta nueva vinculada a esta empresa">＋ NUEVA CUENTA</button>
          </span>
        )}
      </div>

      {/* Vincular cuenta existente */}
      {linkPickerOpen && tab !== TODAS && (
        <div style={{ padding: '4px 8px', background: '#fffbeb', borderBottom: '1px solid #000', fontSize: 9 }}>
          {vinculables.length === 0
            ? <span style={{ color: '#777' }}>Todas las cuentas ya son visibles aquí (las compartidas cuentan).</span>
            : (<>
                <span style={{ fontWeight: 700, textTransform: 'uppercase', fontSize: 8 }}>Vincular a {tab}: </span>
                {vinculables.map(a => (
                  <button key={a.id} disabled={busy} onClick={() => vincular(a.id, tab)}
                          style={{ ...S.toolBtn(false), marginBottom: 2 }}
                          title={`Hoy visible en: ${a.portfolio_links.join(', ')}`}>
                    ＋ {a.name}
                  </button>
                ))}
              </>)}
        </div>
      )}

      {/* Crear cuenta nueva vinculada a la tab */}
      {creating && tab !== TODAS && (
        <form onSubmit={crearCuenta}
              style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap', padding: '4px 8px', background: '#f0fdf4', borderBottom: '1px solid #000' }}>
          <span style={{ fontSize: 8, fontWeight: 700, textTransform: 'uppercase' }}>Nueva cuenta de {tab}:</span>
          <input style={{ ...S.miniInput, width: 150 }} placeholder="Nombre (ej: Caja Menor)" required
                 value={nueva.name} onChange={e => setNueva(n => ({ ...n, name: e.target.value }))} />
          <select style={S.miniInput} value={nueva.type} onChange={e => setNueva(n => ({ ...n, type: e.target.value }))}>
            {TIPOS.map(t => <option key={t}>{t}</option>)}
          </select>
          <select style={S.miniInput} value={nueva.currency} onChange={e => setNueva(n => ({ ...n, currency: e.target.value }))}>
            <option>COP</option><option>USD</option><option>EUR</option>
          </select>
          <input style={{ ...S.miniInput, width: 90 }} type="number" step="any" placeholder="Saldo inicial"
                 value={nueva.initial_balance} onChange={e => setNueva(n => ({ ...n, initial_balance: e.target.value }))} />
          <button type="submit" disabled={busy} style={S.toolBtn(true)}>✓ CREAR</button>
        </form>
      )}

      {/* Tabla */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
              <th style={{ ...S.th, textAlign: 'left' }}>CUENTA</th>
              <th style={{ ...S.th, textAlign: 'left' }}>VISIBLE EN</th>
              <th style={S.th}>SALDO INICIAL</th>
              <th style={S.th}>Δ MOVIMIENTOS (TX)</th>
              <th style={S.th}>ESPERADO</th>
              <th style={S.th}>SALDO ACTUAL</th>
            </tr>
          </thead>
          <tbody>
            {visibles.length === 0 && (
              <tr><td colSpan={6} style={{ ...S.td, textAlign: 'center', color: '#999', padding: 10 }}>
                {tab === TODAS ? 'Sin cuentas — créalas en 💳 Cuentas.'
                  : 'Esta empresa no tiene cuentas visibles — usa 🔗 VINCULAR o ＋ NUEVA CUENTA arriba.'}
              </td></tr>
            )}
            {visibles.map(acc => {
              const links = acc.portfolio_links || [];
              const delta = Number(acc.tx_delta ?? 0);
              const esperado = acc.expected_balance !== undefined
                ? Number(acc.expected_balance)
                : Number(acc.initial_balance || 0) + delta;
              const actual = Number(acc.current_balance || 0);
              const cuadra = Math.abs(actual - esperado) <= 1;
              const deltaColor = delta > 0 ? '#00c853' : delta < 0 ? '#d50000' : '#888';
              const linkDisponibles = portfolios.filter(p => !links.includes(p.name));
              return (
                <tr key={acc.id} style={{ borderBottom: '1px solid #eee', background: cuadra ? 'transparent' : '#fffbeb', opacity: busy ? 0.6 : 1 }}>
                  <td style={{ ...S.td, textAlign: 'left', fontWeight: 700 }}>
                    {acc.name} <span style={{ fontSize: 8, color: '#999' }}>({acc.type} · {acc.currency})</span>
                  </td>
                  <td style={{ ...S.td, textAlign: 'left', maxWidth: 220 }}>
                    {links.length === 0 && (
                      <span style={{ ...S.chip, background: '#f0f0f0', borderStyle: 'dashed' }}
                            title="Compartida: visible en todos los portafolios">🌐 todas</span>
                    )}
                    {links.map(name => (
                      <span key={name} style={S.chip} title={`Visible en ${name}`}>
                        {name}
                        <button type="button" disabled={busy} onClick={() => desvincular(acc.id, name)}
                                title={`Quitar de ${name}${links.length === 1 ? ' (volverá a ser compartida)' : ''}`}
                                style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: 8, padding: 0 }}>×</button>
                      </span>
                    ))}
                    {addingLinkTo === acc.id ? (
                      <select autoFocus style={{ ...S.miniInput, fontSize: 8 }} defaultValue=""
                              onBlur={() => setAddingLinkTo(null)}
                              onChange={e => { if (e.target.value) vincular(acc.id, e.target.value); }}>
                        <option value="" disabled>vincular a…</option>
                        {linkDisponibles.map(p => <option key={p.id} value={p.name}>{p.name}</option>)}
                      </select>
                    ) : (
                      linkDisponibles.length > 0 && (
                        <button type="button" disabled={busy} onClick={() => setAddingLinkTo(acc.id)}
                                title="Vincular esta cuenta a otro portafolio"
                                style={{ ...S.chip, background: '#fff', cursor: 'pointer' }}>＋</button>
                      )
                    )}
                  </td>
                  <td style={{ ...S.td, color: '#555' }}>{fmt(acc.initial_balance, acc.currency)}</td>
                  <td style={{ ...S.td, fontWeight: 700, color: deltaColor }}>
                    {delta > 0 ? '▲ +' : delta < 0 ? '▼ ' : '— '}{delta !== 0 ? fmt(delta, acc.currency) : 'sin movimientos'}
                  </td>
                  <td style={{ ...S.td, color: '#555' }}>{fmt(esperado, acc.currency)}</td>
                  <td style={{ ...S.td, fontWeight: 700, color: actual < 0 ? '#d50000' : '#000' }}>
                    {fmt(actual, acc.currency)}
                    {!cuadra && (
                      <span title={`Difiere del esperado (${fmt(esperado, acc.currency)}): ajuste manual o falta Reconciliar`}
                            style={{ marginLeft: 4, fontSize: 9, color: '#b45309' }}>⚠</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
          {visibles.length > 0 && (
            <tfoot>
              <tr style={{ borderTop: '2px solid #000', background: '#0a0a14', color: '#fff' }}>
                <td colSpan={5} style={{ ...S.td, textAlign: 'left', fontSize: 9, letterSpacing: 2 }}>
                  Σ TOTAL {tab === TODAS ? 'GLOBAL' : tab.toUpperCase()}
                </td>
                <td style={{ ...S.td, fontWeight: 700 }}>
                  {Object.entries(totales).map(([cur, v]) => (
                    <div key={cur} style={{ color: v < 0 ? '#f87171' : '#4ade80' }}>{fmt(v, cur)}</div>
                  ))}
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}
