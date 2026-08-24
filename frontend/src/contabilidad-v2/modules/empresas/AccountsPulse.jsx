/* ============================================================
   AccountsPulse.jsx — Pulso de cuentas bajo el consolidado.
   Por cada cuenta: saldo inicial → Δ movimientos → esperado/actual.

   El Δ viene del backend (tx_delta en /api/dashboard-data): suma
   REAL de transacciones (ingresos +, gastos −, transferencias ±,
   con conversión TRM), NUNCA "actual − inicial" — esa resta miente
   cuando el saldo actual se edita a mano en 💳 Cuentas.
   Si actual ≠ esperado (inicial + movimientos) se marca DESCUADRE:
   o hubo ajuste manual deliberado, o falta ⟳ Reconciliar.

   El saldo inicial se edita en 💳 Cuentas → ✎ (campo punteado).
   Se alimenta del polling de 15s: las transacciones del Bot IA
   también mueven estas cifras solas.
   ============================================================ */
import React from 'react';
import { useEmpresa } from '../../engine/EmpresaProvider.jsx';

const fmt = (v, currency = 'COP') => {
  const n = Number(v || 0);
  const s = '$' + Math.abs(n).toLocaleString('es-CO', { maximumFractionDigits: 0 });
  return (n < 0 ? '-' : '') + s + (currency !== 'COP' ? ` ${currency}` : '');
};

export default function AccountsPulse() {
  // accounts ya viene filtrado por el backend: cuentas del portafolio activo
  // + compartidas (separación multi-empresa)
  const { accounts = [], activePortfolio } = useEmpresa();
  if (!accounts.length) return null;

  // Tolerancia de 1 peso para redondeos
  const descuadres = accounts.filter(a =>
    a.expected_balance !== undefined &&
    Math.abs(Number(a.current_balance || 0) - Number(a.expected_balance || 0)) > 1);

  return (
    <div style={{
      border: '2px solid #000', background: '#fff', marginBottom: 8,
      fontFamily: '"IBM Plex Mono", monospace', boxShadow: '3px 3px 0 #000',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, padding: '3px 8px',
        borderBottom: '1px solid #ddd', background: '#fafafa',
      }}>
        <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: 2, color: '#888', textTransform: 'uppercase' }}>
          💳 PULSO DE CUENTAS · {activePortfolio || 'TODAS'} <span style={{ color: '#bbb' }}>(+ compartidas)</span>
        </span>
        {descuadres.length > 0 && (
          <span title="El saldo actual no coincide con inicial + transacciones: hubo un ajuste manual o falta Reconciliar (💳 Cuentas → ⟳)."
                style={{ fontSize: 8, color: '#b45309', background: '#fef3c7', border: '1px solid #fbbf24', padding: '0 4px', letterSpacing: 0.5 }}>
            {descuadres.length} DESCUADRE(S)
          </span>
        )}
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 8, color: '#aaa' }}>inicial editable en 💳 Cuentas → ✎</span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
              {['CUENTA', 'SALDO INICIAL', 'Δ MOVIMIENTOS (TX)', 'ESPERADO', 'SALDO ACTUAL'].map((h, i) => (
                <th key={h} style={{
                  padding: '3px 8px', fontSize: 8, fontWeight: 700, letterSpacing: 1.5,
                  textAlign: i === 0 ? 'left' : 'right', color: '#888', textTransform: 'uppercase',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {accounts.map(acc => {
              const delta = Number(acc.tx_delta ?? 0);
              const esperado = acc.expected_balance !== undefined
                ? Number(acc.expected_balance)
                : Number(acc.initial_balance || 0) + delta;
              const actual = Number(acc.current_balance || 0);
              const cuadra = Math.abs(actual - esperado) <= 1;
              const deltaColor = delta > 0 ? '#00c853' : delta < 0 ? '#d50000' : '#888';
              return (
                <tr key={acc.id} style={{ borderBottom: '1px solid #eee', background: cuadra ? 'transparent' : '#fffbeb' }}>
                  <td style={{ padding: '3px 8px', fontSize: 10, fontWeight: 700 }}>
                    {acc.name} <span style={{ fontSize: 8, color: '#999' }}>({acc.type} · {acc.currency})</span>
                  </td>
                  <td style={{ padding: '3px 8px', fontSize: 10, textAlign: 'right', color: '#555' }}>
                    {fmt(acc.initial_balance, acc.currency)}
                  </td>
                  <td style={{ padding: '3px 8px', fontSize: 10, textAlign: 'right', fontWeight: 700, color: deltaColor }}>
                    {delta > 0 ? '▲ +' : delta < 0 ? '▼ ' : '— '}{delta !== 0 ? fmt(delta, acc.currency) : 'sin movimientos'}
                  </td>
                  <td style={{ padding: '3px 8px', fontSize: 10, textAlign: 'right', color: '#555' }}>
                    {fmt(esperado, acc.currency)}
                  </td>
                  <td style={{
                    padding: '3px 8px', fontSize: 10, textAlign: 'right', fontWeight: 700,
                    color: actual < 0 ? '#d50000' : '#000',
                  }}>
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
        </table>
      </div>
    </div>
  );
}
