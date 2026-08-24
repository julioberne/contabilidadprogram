/* ============================================================
   AccountsPulse.jsx — Pulso de cuentas con tabs por portafolio.

   UX (de flujo a stock): el Consolidado de arriba muestra el FLUJO
   por empresa; este panel muestra el STOCK — qué cuentas tiene cada
   portafolio y cuánto valen. Tabs sincrónicas:
     · una tab por portafolio + TODAS (vista global con dueño)
     · "▸" marca el portafolio ACTIVO; la selección lo sigue, pero
       puedes inspeccionar otro sin cambiar dónde trabajas
     · asignación inline: el select "pertenece a" de cada fila
       reasigna la cuenta (compartida ↔ portafolio) al instante
     · total por moneda al pie = el valor de esa empresa de un vistazo

   Datos: GET /api/accounts (todas, con portfolio_name + tx_delta +
   expected_balance). El Δ viene de transacciones REALES; si actual ≠
   esperado (inicial + Δ) se marca DESCUADRE (ajuste manual o falta
   ⟳ Reconciliar). Refresco cada 15s — el Bot IA mueve esto solo.
   ============================================================ */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { API } from '../../../config';
import { useEmpresa } from '../../engine/EmpresaProvider.jsx';

const TODAS = '__TODAS__';

const fmt = (v, currency = 'COP') => {
  const n = Number(v || 0);
  const s = '$' + Math.abs(n).toLocaleString('es-CO', { maximumFractionDigits: 0 });
  return (n < 0 ? '-' : '') + s + (currency !== 'COP' ? ` ${currency}` : '');
};

const S = {
  tab: (active, esActivo) => ({
    fontFamily: '"IBM Plex Mono", monospace', fontSize: 9, fontWeight: 700,
    letterSpacing: 1, textTransform: 'uppercase', padding: '3px 8px',
    border: '1px solid #000', borderBottom: active ? 'none' : '1px solid #000',
    background: active ? '#fff' : esActivo ? '#dcfce7' : '#f0f0f0',
    color: active ? '#000' : '#555', cursor: 'pointer', marginRight: 2,
  }),
  th: { padding: '3px 8px', fontSize: 8, fontWeight: 700, letterSpacing: 1.5, textAlign: 'right', color: '#888', textTransform: 'uppercase' },
  td: { padding: '3px 8px', fontSize: 10, textAlign: 'right' },
};

export default function AccountsPulse() {
  const { portfolios = [], activePortfolio, fetchAll } = useEmpresa();
  const [accounts, setAccounts] = useState([]);
  const [tab, setTab] = useState(activePortfolio || TODAS);
  const [saving, setSaving] = useState(null);
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

  // Sincrónica: la tab sigue al portafolio activo cuando este cambia
  useEffect(() => { if (activePortfolio) setTab(activePortfolio); }, [activePortfolio]);

  const reasignar = async (acc, portfolioName) => {
    setSaving(acc.id);
    try {
      await fetch(`${API}/accounts/${acc.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: acc.name, type: acc.type, portfolio_name: portfolioName }),
      });
      await cargar();
      fetchAll?.();               // saldos/patrimonio del portafolio cambian
    } finally {
      setSaving(null);
    }
  };

  if (!accounts.length) return null;

  const visibles = tab === TODAS
    ? accounts
    : accounts.filter(a => a.portfolio_name === tab || a.portfolio_id == null);

  const descuadres = visibles.filter(a =>
    a.expected_balance !== undefined &&
    Math.abs(Number(a.current_balance || 0) - Number(a.expected_balance || 0)) > 1);

  const totales = visibles.reduce((acc, a) => {
    const cur = a.currency || 'COP';
    acc[cur] = (acc[cur] || 0) + Number(a.current_balance || 0);
    return acc;
  }, {});

  return (
    <div style={{
      border: '2px solid #000', background: '#fff', marginBottom: 8,
      fontFamily: '"IBM Plex Mono", monospace', boxShadow: '3px 3px 0 #000',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 8px', borderBottom: '1px solid #ddd', background: '#fafafa' }}>
        <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: 2, color: '#888', textTransform: 'uppercase' }}>
          💳 PULSO DE CUENTAS
        </span>
        {descuadres.length > 0 && (
          <span title="El saldo actual no coincide con inicial + transacciones: ajuste manual o falta Reconciliar (💳 Cuentas → ⟳)."
                style={{ fontSize: 8, color: '#b45309', background: '#fef3c7', border: '1px solid #fbbf24', padding: '0 4px', letterSpacing: 0.5 }}>
            {descuadres.length} DESCUADRE(S)
          </span>
        )}
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 8, color: '#aaa' }}>compartida = visible en todos · asigna con el select de cada fila</span>
      </div>

      {/* Tabs por portafolio */}
      <div style={{ display: 'flex', alignItems: 'flex-end', padding: '4px 8px 0 8px', background: '#fafafa', borderBottom: '1px solid #000', flexWrap: 'wrap' }}>
        <button style={S.tab(tab === TODAS, false)} onClick={() => setTab(TODAS)}>TODAS</button>
        {portfolios.map(p => (
          <button key={p.id} style={S.tab(tab === p.name, p.name === activePortfolio)}
                  onClick={() => setTab(p.name)}
                  title={p.name === activePortfolio ? 'Portafolio ACTIVO (donde registras ahora)' : `Ver cuentas de ${p.name}`}>
            {p.name === activePortfolio ? '▸ ' : ''}{p.name}
          </button>
        ))}
      </div>

      {/* Tabla */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
              <th style={{ ...S.th, textAlign: 'left' }}>CUENTA</th>
              <th style={{ ...S.th, textAlign: 'left' }}>PERTENECE A</th>
              <th style={S.th}>SALDO INICIAL</th>
              <th style={S.th}>Δ MOVIMIENTOS (TX)</th>
              <th style={S.th}>ESPERADO</th>
              <th style={S.th}>SALDO ACTUAL</th>
            </tr>
          </thead>
          <tbody>
            {visibles.length === 0 && (
              <tr><td colSpan={6} style={{ ...S.td, textAlign: 'center', color: '#999', padding: 10 }}>
                Este portafolio no tiene cuentas propias — asígnale una desde TODAS o créala en 💳 Cuentas.
              </td></tr>
            )}
            {visibles.map(acc => {
              const delta = Number(acc.tx_delta ?? 0);
              const esperado = acc.expected_balance !== undefined
                ? Number(acc.expected_balance)
                : Number(acc.initial_balance || 0) + delta;
              const actual = Number(acc.current_balance || 0);
              const cuadra = Math.abs(actual - esperado) <= 1;
              const deltaColor = delta > 0 ? '#00c853' : delta < 0 ? '#d50000' : '#888';
              return (
                <tr key={acc.id} style={{ borderBottom: '1px solid #eee', background: cuadra ? 'transparent' : '#fffbeb', opacity: saving === acc.id ? 0.5 : 1 }}>
                  <td style={{ ...S.td, textAlign: 'left', fontWeight: 700 }}>
                    {acc.name} <span style={{ fontSize: 8, color: '#999' }}>({acc.type} · {acc.currency})</span>
                  </td>
                  <td style={{ ...S.td, textAlign: 'left' }}>
                    <select
                      value={acc.portfolio_name || ''}
                      disabled={saving === acc.id}
                      onChange={e => reasignar(acc, e.target.value)}
                      title="Dueño de la cuenta. Compartida = visible en todos los portafolios."
                      style={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: 8, padding: '1px 2px',
                               border: acc.portfolio_name ? '1px solid #000' : '1px dashed #aaa',
                               background: acc.portfolio_name ? '#dcfce7' : '#fff', maxWidth: 130 }}>
                      <option value="">— compartida —</option>
                      {portfolios.map(p => <option key={p.id} value={p.name}>{p.name}</option>)}
                    </select>
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
