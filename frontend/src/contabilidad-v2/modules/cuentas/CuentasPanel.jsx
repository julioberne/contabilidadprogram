/* ================================================================
   CuentasPanel.jsx — Bank Accounts Lego panel
   FIN-SYS Contabilidad v2 · Módulo Cuentas
   Brutalist style · IBM Plex Mono · 0px radius · 2px borders
   ================================================================ */
import React from 'react';
import { useCuentas } from './useCuentas.js';

const ACCOUNT_TYPES = ['Efectivo', 'Ahorros', 'Corriente', 'Crédito'];
const CURRENCIES = ['COP', 'USD'];

const CURRENCY_BADGE = {
  COP: 'bg-green-100 text-green-800 border-green-500',
  USD: 'bg-blue-100 text-blue-800 border-blue-500',
};

const fmt = (n, currency) => {
  const val = Number(n || 0);
  if (currency === 'USD') {
    return 'USD ' + val.toLocaleString('en-US', { maximumFractionDigits: 0 });
  }
  return '$' + val.toLocaleString('es-CO', { maximumFractionDigits: 0 });
};

const inputStyle = {
  width: '100%',
  padding: '4px 6px',
  fontFamily: "'IBM Plex Mono', monospace",
  fontSize: 10,
  border: '2px solid #000',
  borderRadius: 0,
  outline: 'none',
  textTransform: 'uppercase',
};

const selectStyle = {
  ...inputStyle,
  background: '#fff',
  cursor: 'pointer',
};

export function CuentasPanel({ activePortfolio }) {
  const cuentas = useCuentas(activePortfolio);

  const totalBalance = cuentas.items.reduce(
    (sum, a) => sum + Number(a.current_balance ?? a.initial_balance ?? 0),
    0
  );

  return (
    <div style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
      {/* ── CREATE FORM ──────────────────────────────────── */}
      <div
        style={{
          border: '2px solid #000',
          background: '#fff',
          marginBottom: 12,
          boxShadow: '3px 3px 0 #000',
        }}
      >
        <div
          style={{
            padding: '6px 8px',
            background: '#000',
            color: '#fff',
            fontSize: 9,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}
        >
          + Nueva Cuenta
        </div>

        <div style={{ padding: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
          <input
            type="text"
            placeholder="NOMBRE DE LA CUENTA"
            value={cuentas.form.name}
            onChange={(e) => cuentas.updateForm('name', e.target.value)}
            style={inputStyle}
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            <select
              value={cuentas.form.type}
              onChange={(e) => cuentas.updateForm('type', e.target.value)}
              style={selectStyle}
            >
              {ACCOUNT_TYPES.map((t) => (
                <option key={t} value={t}>{t.toUpperCase()}</option>
              ))}
            </select>

            <select
              value={cuentas.form.currency}
              onChange={(e) => cuentas.updateForm('currency', e.target.value)}
              style={selectStyle}
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <input
            type="number"
            placeholder="SALDO INICIAL"
            value={cuentas.form.initial_balance}
            onChange={(e) => cuentas.updateForm('initial_balance', e.target.value)}
            style={inputStyle}
          />

          <button
            onClick={cuentas.create}
            disabled={!cuentas.form.name.trim()}
            style={{
              width: '100%',
              padding: '6px 0',
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 10,
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              cursor: cuentas.form.name.trim() ? 'pointer' : 'not-allowed',
              border: '2px solid #000',
              borderRadius: 0,
              background: cuentas.form.name.trim() ? '#000' : '#ccc',
              color: '#fff',
            }}
          >
            + Crear Cuenta
          </button>
        </div>
      </div>

      {/* ── ACCOUNTS TABLE ───────────────────────────────── */}
      {cuentas.loading ? (
        <div
          style={{
            padding: 20,
            textAlign: 'center',
            fontSize: 10,
            color: '#999',
            textTransform: 'uppercase',
          }}
        >
          ▓ Cargando cuentas…
        </div>
      ) : cuentas.items.length === 0 ? (
        <div
          style={{
            padding: 20,
            textAlign: 'center',
            fontSize: 10,
            color: '#999',
            textTransform: 'uppercase',
          }}
        >
          ▓ Sin cuentas en este portafolio
        </div>
      ) : (
        <div
          style={{
            border: '2px solid #000',
            boxShadow: '3px 3px 0 #000',
          }}
        >
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 9,
            }}
          >
            <thead>
              <tr
                style={{
                  background: '#000',
                  color: '#fff',
                  textTransform: 'uppercase',
                  fontSize: 8,
                }}
              >
                <th style={{ padding: '5px 6px', textAlign: 'left', borderRight: '1px solid #333' }}>
                  Nombre
                </th>
                <th style={{ padding: '5px 6px', textAlign: 'left', borderRight: '1px solid #333' }}>
                  Tipo
                </th>
                <th style={{ padding: '5px 6px', textAlign: 'center', borderRight: '1px solid #333' }}>
                  Moneda
                </th>
                <th style={{ padding: '5px 6px', textAlign: 'right', borderRight: '1px solid #333' }}>
                  Saldo
                </th>
                <th style={{ padding: '5px 6px', textAlign: 'center', width: 60 }}>
                  Acc
                </th>
              </tr>
            </thead>
            <tbody>
              {cuentas.items.map((acct, i) => {
                const isEditing = cuentas.editingId === acct.id;
                const balance = Number(acct.current_balance ?? acct.initial_balance ?? 0);
                const balanceColor = balance >= 0 ? '#00c853' : '#c00';
                const currency = acct.currency || 'COP';
                const badgeClass = CURRENCY_BADGE[currency] || CURRENCY_BADGE.COP;

                if (isEditing) {
                  return (
                    <tr
                      key={acct.id}
                      style={{
                        borderBottom: '1px solid #e0e0d8',
                        background: '#fffde7',
                      }}
                    >
                      <td style={{ padding: '4px 6px', borderRight: '1px solid #f0f0e8' }}>
                        <input
                          type="text"
                          value={cuentas.editData.name}
                          onChange={(e) =>
                            cuentas.setEditData((prev) => ({ ...prev, name: e.target.value }))
                          }
                          style={{ ...inputStyle, border: '1px solid #000' }}
                        />
                      </td>
                      <td style={{ padding: '4px 6px', borderRight: '1px solid #f0f0e8' }}>
                        <select
                          value={cuentas.editData.type}
                          onChange={(e) =>
                            cuentas.setEditData((prev) => ({ ...prev, type: e.target.value }))
                          }
                          style={{ ...selectStyle, border: '1px solid #000' }}
                        >
                          {ACCOUNT_TYPES.map((t) => (
                            <option key={t} value={t}>{t.toUpperCase()}</option>
                          ))}
                        </select>
                      </td>
                      <td style={{ padding: '4px 6px', textAlign: 'center', borderRight: '1px solid #f0f0e8' }}>
                        <span
                          className={badgeClass}
                          style={{
                            display: 'inline-block',
                            padding: '1px 6px',
                            fontSize: 8,
                            fontWeight: 700,
                            border: '1px solid',
                            textTransform: 'uppercase',
                          }}
                        >
                          {currency}
                        </span>
                      </td>
                      <td style={{ padding: '4px 6px', borderRight: '1px solid #f0f0e8' }}>
                        <input
                          type="number"
                          value={cuentas.editData.current_balance}
                          onChange={(e) =>
                            cuentas.setEditData((prev) => ({
                              ...prev,
                              current_balance: e.target.value,
                            }))
                          }
                          style={{ ...inputStyle, border: '1px solid #000', textAlign: 'right' }}
                        />
                      </td>
                      <td style={{ padding: '4px 6px', textAlign: 'center' }}>
                        <button
                          onClick={() => cuentas.update(acct.id)}
                          style={{
                            cursor: 'pointer',
                            border: 'none',
                            background: 'none',
                            fontSize: 12,
                            marginRight: 4,
                          }}
                          title="Guardar"
                        >
                          ✓
                        </button>
                        <button
                          onClick={cuentas.cancelEdit}
                          style={{
                            cursor: 'pointer',
                            border: 'none',
                            background: 'none',
                            fontSize: 12,
                          }}
                          title="Cancelar"
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  );
                }

                return (
                  <tr
                    key={acct.id}
                    style={{
                      borderBottom: '1px solid #e0e0d8',
                      background: i % 2 === 0 ? '#fff' : '#fafaf5',
                    }}
                  >
                    <td
                      style={{
                        padding: '5px 6px',
                        fontWeight: 700,
                        borderRight: '1px solid #f0f0e8',
                      }}
                    >
                      {acct.name}
                    </td>
                    <td
                      style={{
                        padding: '5px 6px',
                        color: '#666',
                        borderRight: '1px solid #f0f0e8',
                        textTransform: 'uppercase',
                      }}
                    >
                      {acct.type}
                    </td>
                    <td
                      style={{
                        padding: '5px 6px',
                        textAlign: 'center',
                        borderRight: '1px solid #f0f0e8',
                      }}
                    >
                      <span
                        className={badgeClass}
                        style={{
                          display: 'inline-block',
                          padding: '1px 6px',
                          fontSize: 8,
                          fontWeight: 700,
                          border: '1px solid',
                          textTransform: 'uppercase',
                        }}
                      >
                        {currency}
                      </span>
                    </td>
                    <td
                      style={{
                        padding: '5px 6px',
                        textAlign: 'right',
                        fontWeight: 700,
                        color: balanceColor,
                        borderRight: '1px solid #f0f0e8',
                      }}
                    >
                      {fmt(balance, currency)}
                    </td>
                    <td style={{ padding: '5px 6px', textAlign: 'center' }}>
                      <button
                        onClick={() => cuentas.startEdit(acct)}
                        style={{
                          cursor: 'pointer',
                          border: 'none',
                          background: 'none',
                          fontSize: 11,
                          marginRight: 4,
                        }}
                        title="Editar"
                      >
                        ✎
                      </button>
                      <button
                        onClick={() => cuentas.remove(acct.id, acct.name)}
                        style={{
                          cursor: 'pointer',
                          border: 'none',
                          background: 'none',
                          fontSize: 11,
                        }}
                        title="Eliminar"
                      >
                        🗑
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── FOOTER: Count + Total ────────────────────────── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: 8,
          padding: '4px 6px',
          fontSize: 9,
          color: '#666',
          textTransform: 'uppercase',
          borderTop: '1px solid #e0e0d8',
        }}
      >
        <span>{cuentas.items.length} cuenta{cuentas.items.length !== 1 ? 's' : ''}</span>
        <span style={{ fontWeight: 700, color: totalBalance >= 0 ? '#00c853' : '#c00' }}>
          Total: {fmt(totalBalance, 'COP')}
        </span>
      </div>
    </div>
  );
}

export default CuentasPanel;
