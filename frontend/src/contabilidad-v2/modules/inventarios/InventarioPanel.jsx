/* ============================================================
   InventarioPanel.jsx — FIN-SYS Contabilidad v2 · Phase 2
   Assets / Inventarios UI panel
   ============================================================ */
import React from 'react';
import { useInventarios } from './useInventarios.js';

const FONT = "'IBM Plex Mono', monospace";

const formatMoney = (n) =>
  '$' + Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 0 });

const inputStyle = {
  fontFamily: FONT,
  fontSize: 10,
  padding: '3px 6px',
  border: '2px solid #000',
  borderRadius: 0,
  background: '#fff',
  outline: 'none',
  width: '100%',
};

const btnIcon = {
  fontFamily: FONT,
  fontSize: 10,
  cursor: 'pointer',
  background: 'none',
  border: 'none',
  padding: '2px 4px',
};

export function InventarioPanel({ activePortfolio }) {
  const inv = useInventarios(activePortfolio);

  return (
    <div style={{ fontFamily: FONT }}>
      {/* ── Section header ─────────────────────────────────── */}
      <div style={{
        fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '0.12em', color: '#666', marginBottom: 8,
      }}>
        assets · {inv.items.length} registros
        {inv.loading && (
          <span style={{ marginLeft: 8, color: '#999' }}>cargando…</span>
        )}
      </div>

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
            <th style={{ padding: '5px 6px', textAlign: 'right', borderRight: '1px solid #333', width: 90 }}>
              Valor
            </th>
            <th style={{ padding: '5px 6px', textAlign: 'left', borderRight: '1px solid #333', width: 80 }}>
              Tag
            </th>
            <th style={{ padding: '5px 6px', textAlign: 'center', width: 60 }}>
              Acc
            </th>
          </tr>
        </thead>
        <tbody>
          {inv.items.map((item, i) => (
            <tr
              key={item.id}
              style={{
                borderBottom: '1px solid #e0e0d8',
                background: i % 2 === 0 ? '#fff' : '#fafaf5',
              }}
            >
              {inv.editingId === item.id ? (
                /* ── Inline edit mode ────────────────────── */
                <>
                  <td style={{ padding: '3px 4px' }}>
                    <input
                      style={inputStyle}
                      value={inv.editData.name}
                      onChange={(e) =>
                        inv.setEditData({ ...inv.editData, name: e.target.value })
                      }
                    />
                  </td>
                  <td style={{ padding: '3px 4px' }}>
                    <input
                      style={{ ...inputStyle, textAlign: 'right' }}
                      type="number"
                      value={inv.editData.purchase_value}
                      onChange={(e) =>
                        inv.setEditData({ ...inv.editData, purchase_value: e.target.value })
                      }
                    />
                  </td>
                  <td style={{ padding: '3px 4px' }}>
                    <input
                      style={inputStyle}
                      value={inv.editData.custom_tag}
                      onChange={(e) =>
                        inv.setEditData({ ...inv.editData, custom_tag: e.target.value })
                      }
                    />
                  </td>
                  <td style={{ padding: '3px 4px', textAlign: 'center', whiteSpace: 'nowrap' }}>
                    <button
                      style={{ ...btnIcon, color: '#00c853', fontWeight: 700 }}
                      onClick={() => inv.update(item.id)}
                      title="Guardar"
                    >
                      ✓
                    </button>
                    <button
                      style={{ ...btnIcon, color: '#c00', fontWeight: 700 }}
                      onClick={inv.cancelEdit}
                      title="Cancelar"
                    >
                      ✕
                    </button>
                  </td>
                </>
              ) : (
                /* ── Display mode ────────────────────────── */
                <>
                  <td style={{ padding: '4px 6px', fontWeight: 700 }}>
                    {item.name || '—'}
                  </td>
                  <td style={{ padding: '4px 6px', textAlign: 'right' }}>
                    {formatMoney(item.purchase_value)}
                  </td>
                  <td style={{ padding: '4px 6px', color: '#666' }}>
                    {item.custom_tag || '—'}
                  </td>
                  <td style={{ padding: '4px 6px', textAlign: 'center', whiteSpace: 'nowrap' }}>
                    <button
                      style={btnIcon}
                      onClick={() => inv.startEdit(item)}
                      title="Editar"
                    >
                      ✎
                    </button>
                    <button
                      style={{ ...btnIcon, color: '#c00' }}
                      onClick={() => inv.remove(item.id)}
                      title="Eliminar"
                    >
                      🗑
                    </button>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {/* ── Empty state ────────────────────────────────────── */}
      {!inv.loading && inv.items.length === 0 && (
        <div style={{
          padding: 24, textAlign: 'center',
          fontSize: 9, color: '#999', textTransform: 'uppercase',
        }}>
          ▓ sin activos en "{activePortfolio}"
        </div>
      )}

      {/* ── Footer count ───────────────────────────────────── */}
      {inv.items.length > 0 && (
        <div style={{
          fontSize: 8, color: '#999', textTransform: 'uppercase',
          textAlign: 'right', marginTop: 4, letterSpacing: '0.08em',
        }}>
          total: {inv.items.length} activos
        </div>
      )}
    </div>
  );
}

export default InventarioPanel;
