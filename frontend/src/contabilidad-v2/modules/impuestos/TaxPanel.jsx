/* ============================================================
   TaxPanel.jsx — FIN-SYS Contabilidad v2 · Phase 2
   Custom Taxes / Impuestos UI panel
   ============================================================ */
import React from 'react';
import { useTaxes } from './useTaxes.js';

const FONT = "'IBM Plex Mono', monospace";

const inputStyle = {
  fontFamily: FONT,
  fontSize: 10,
  padding: '4px 8px',
  border: '2px solid #000',
  borderRadius: 0,
  background: '#fff',
  outline: 'none',
  width: '100%',
};

const formatRate = (r) => Number(r || 0).toFixed(2) + '%';

export function TaxPanel() {
  const tax = useTaxes();

  return (
    <div style={{ fontFamily: FONT }}>
      {/* ── Section header ─────────────────────────────────── */}
      <div style={{
        fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '0.12em', color: '#666', marginBottom: 8,
      }}>
        impuestos · {tax.items.length} registros
        {tax.loading && (
          <span style={{ marginLeft: 8, color: '#999' }}>cargando…</span>
        )}
      </div>

      {/* ── Toggle "add" form ──────────────────────────────── */}
      <button
        onClick={() => tax.setIsAdding(!tax.isAdding)}
        style={{
          fontFamily: FONT,
          fontSize: 9,
          fontWeight: 700,
          textTransform: 'uppercase',
          padding: '5px 12px',
          border: '2px solid #000',
          borderRadius: 0,
          background: tax.isAdding ? '#000' : '#fff',
          color: tax.isAdding ? '#fff' : '#000',
          cursor: 'pointer',
          boxShadow: '3px 3px 0 #000',
          marginBottom: tax.isAdding ? 0 : 12,
          width: '100%',
          textAlign: 'left',
        }}
      >
        {tax.isAdding ? '▲ Cerrar' : '+ Nueva Tasa'}
      </button>

      {/* ── Collapsible create form ────────────────────────── */}
      {tax.isAdding && (
        <div style={{
          border: '2px solid #000',
          borderTop: 'none',
          padding: 10,
          marginBottom: 12,
          background: '#fafaf5',
        }}>
          {/* Name */}
          <div style={{ marginBottom: 6 }}>
            <label style={{
              fontSize: 8, textTransform: 'uppercase',
              letterSpacing: '0.1em', color: '#999', display: 'block', marginBottom: 2,
            }}>
              Nombre
            </label>
            <input
              style={inputStyle}
              placeholder="EJ: ICA, RETE-IVA"
              value={tax.form.name}
              onChange={(e) => tax.updateForm('name', e.target.value)}
            />
          </div>

          {/* Rate */}
          <div style={{ marginBottom: 6 }}>
            <label style={{
              fontSize: 8, textTransform: 'uppercase',
              letterSpacing: '0.1em', color: '#999', display: 'block', marginBottom: 2,
            }}>
              Tasa (%)
            </label>
            <input
              style={{ ...inputStyle, textAlign: 'right' }}
              type="number"
              step="0.01"
              placeholder="0.00"
              value={tax.form.rate}
              onChange={(e) => tax.updateForm('rate', e.target.value)}
            />
          </div>

          {/* Type select */}
          <div style={{ marginBottom: 8 }}>
            <label style={{
              fontSize: 8, textTransform: 'uppercase',
              letterSpacing: '0.1em', color: '#999', display: 'block', marginBottom: 2,
            }}>
              Tipo
            </label>
            <select
              style={{ ...inputStyle, cursor: 'pointer' }}
              value={tax.form.type}
              onChange={(e) => tax.updateForm('type', e.target.value)}
            >
              <option value="ADDITIVE">ADDITIVE</option>
              <option value="DEDUCTIVE">DEDUCTIVE</option>
            </select>
          </div>

          {/* Create button */}
          <button
            onClick={tax.create}
            disabled={!tax.form.name.trim() || !tax.form.rate}
            style={{
              fontFamily: FONT,
              fontSize: 9,
              fontWeight: 700,
              textTransform: 'uppercase',
              padding: '5px 14px',
              border: '2px solid #000',
              borderRadius: 0,
              background: (tax.form.name.trim() && tax.form.rate) ? '#000' : '#ccc',
              color: '#fff',
              cursor: (tax.form.name.trim() && tax.form.rate) ? 'pointer' : 'not-allowed',
              boxShadow: (tax.form.name.trim() && tax.form.rate) ? '3px 3px 0 #000' : 'none',
              width: '100%',
            }}
          >
            Crear Tasa
          </button>
        </div>
      )}

      {/* ── Table ──────────────────────────────────────────── */}
      <table style={{
        width: '100%', borderCollapse: 'collapse',
        border: '2px solid #000',
        boxShadow: '3px 3px 0 #000',
        fontSize: 10,
        fontFamily: FONT,
      }}>
        <thead>
          <tr style={{
            background: '#000', color: '#fff',
            textTransform: 'uppercase', fontSize: 9,
          }}>
            <th style={{ padding: '5px 6px', textAlign: 'left', borderRight: '1px solid #333' }}>
              Nombre
            </th>
            <th style={{ padding: '5px 6px', textAlign: 'right', borderRight: '1px solid #333', width: 70 }}>
              Tasa
            </th>
            <th style={{ padding: '5px 6px', textAlign: 'center', borderRight: '1px solid #333', width: 80 }}>
              Tipo
            </th>
            <th style={{ padding: '5px 6px', textAlign: 'center', width: 40 }}>
              Acc
            </th>
          </tr>
        </thead>
        <tbody>
          {tax.items.map((item, i) => (
            <tr
              key={item.id}
              style={{
                borderBottom: '1px solid #e0e0d8',
                background: i % 2 === 0 ? '#fff' : '#fafaf5',
              }}
            >
              <td style={{ padding: '4px 6px', fontWeight: 700 }}>
                {item.name || '—'}
              </td>
              <td style={{ padding: '4px 6px', textAlign: 'right' }}>
                {formatRate(item.rate)}
              </td>
              <td style={{ padding: '4px 6px', textAlign: 'center' }}>
                <span style={{
                  display: 'inline-block',
                  padding: '1px 6px',
                  fontSize: 8,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  border: '2px solid #000',
                  background: item.type === 'ADDITIVE' ? '#e8ffe8' : '#ffe8e8',
                  color: item.type === 'ADDITIVE' ? '#00701a' : '#b71c1c',
                }}>
                  {item.type}
                </span>
              </td>
              <td style={{ padding: '4px 6px', textAlign: 'center' }}>
                <button
                  style={{
                    fontFamily: FONT, fontSize: 10, cursor: 'pointer',
                    background: 'none', border: 'none', color: '#c00',
                    padding: '2px 4px',
                  }}
                  onClick={() => tax.remove(item.id)}
                  title="Eliminar"
                >
                  🗑
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* ── Empty state ────────────────────────────────────── */}
      {!tax.loading && tax.items.length === 0 && (
        <div style={{
          padding: 24, textAlign: 'center',
          fontSize: 9, color: '#999', textTransform: 'uppercase',
        }}>
          ▓ sin tasas personalizadas
        </div>
      )}

      {/* ── Footer count ───────────────────────────────────── */}
      {tax.items.length > 0 && (
        <div style={{
          fontSize: 8, color: '#999', textTransform: 'uppercase',
          textAlign: 'right', marginTop: 4, letterSpacing: '0.08em',
        }}>
          total: {tax.items.length} tasas
        </div>
      )}
    </div>
  );
}

export default TaxPanel;
