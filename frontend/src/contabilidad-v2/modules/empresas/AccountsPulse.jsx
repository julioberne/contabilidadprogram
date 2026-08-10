/* ============================================================
   AccountsPulse.jsx — Pulso de cuentas bajo el consolidado.
   Responde a: "tenemos un valor en una cuenta, ejecutamos gastos
   e ingresos, pero no evidenciamos cuánto disminuye o aumenta".
   Por cada cuenta (user_accounts): saldo inicial → Δ movimientos
   → saldo actual, con color según el sentido. Se alimenta del
   polling de 15s del dashboard (empresa.accounts), así que las
   transacciones del Bot IA también mueven estas cifras solas.
   ============================================================ */
import React from 'react';
import { useEmpresa } from '../../engine/EmpresaProvider.jsx';

const fmt = (v, currency = 'COP') => {
  const n = Number(v || 0);
  const s = '$' + Math.abs(n).toLocaleString('es-CO', { maximumFractionDigits: 0 });
  return (n < 0 ? '-' : '') + s + (currency !== 'COP' ? ` ${currency}` : '');
};

export default function AccountsPulse() {
  const { accounts = [] } = useEmpresa();
  if (!accounts.length) return null;

  return (
    <div style={{
      border: '2px solid #000', background: '#fff', marginBottom: 8,
      fontFamily: '"IBM Plex Mono", monospace', boxShadow: '3px 3px 0 #000',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 4, padding: '3px 8px',
        borderBottom: '1px solid #ddd', background: '#fafafa',
      }}>
        <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: 2, color: '#888', textTransform: 'uppercase' }}>
          💳 PULSO DE CUENTAS · SALDO INICIAL → MOVIMIENTOS → ACTUAL
        </span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
              {['CUENTA', 'SALDO INICIAL', 'Δ MOVIMIENTOS', 'SALDO ACTUAL'].map((h, i) => (
                <th key={h} style={{
                  padding: '3px 8px', fontSize: 8, fontWeight: 700, letterSpacing: 1.5,
                  textAlign: i === 0 ? 'left' : 'right', color: '#888', textTransform: 'uppercase',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {accounts.map(acc => {
              const delta = Number(acc.current_balance || 0) - Number(acc.initial_balance || 0);
              const deltaColor = delta > 0 ? '#00c853' : delta < 0 ? '#d50000' : '#888';
              return (
                <tr key={acc.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '3px 8px', fontSize: 10, fontWeight: 700 }}>
                    {acc.name} <span style={{ fontSize: 8, color: '#999' }}>({acc.type} · {acc.currency})</span>
                  </td>
                  <td style={{ padding: '3px 8px', fontSize: 10, textAlign: 'right', color: '#555' }}>
                    {fmt(acc.initial_balance, acc.currency)}
                  </td>
                  <td style={{ padding: '3px 8px', fontSize: 10, textAlign: 'right', fontWeight: 700, color: deltaColor }}>
                    {delta > 0 ? '▲ +' : delta < 0 ? '▼ ' : '— '}{delta !== 0 ? fmt(delta, acc.currency) : 'sin movimientos'}
                  </td>
                  <td style={{
                    padding: '3px 8px', fontSize: 10, textAlign: 'right', fontWeight: 700,
                    color: Number(acc.current_balance) < 0 ? '#d50000' : '#000',
                  }}>
                    {fmt(acc.current_balance, acc.currency)}
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
