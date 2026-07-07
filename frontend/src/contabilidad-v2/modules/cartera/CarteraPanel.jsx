import { useState } from 'react';
import { useCartera } from './useCartera.js';
import { useLabel } from '../../engine/TenantProvider.jsx';

const fmtMoney = (n) =>
  '$' + Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 0 });

const SORT_OPTIONS = [
  { key: 'urgente',    icon: '🔥', label: 'Urgente' },
  { key: 'monto-desc', icon: '↓',  label: 'Mayor $' },
  { key: 'monto-asc',  icon: '↑',  label: 'Menor $' },
  { key: 'reciente',   icon: '🕐', label: 'Recientes' },
  { key: 'vence-prox', icon: '📅', label: 'Vence pronto' },
  { key: 'progreso',   icon: '📊', label: '% Pagado' },
];

function getDueSemaforo(dueDateStr) {
  if (!dueDateStr) return { dot: '⚪', label: '—', cls: 'text-gray-400' };
  const now = new Date();
  const due = new Date(dueDateStr);
  const diffDays = Math.round((due - now) / 86400000);
  if (diffDays < 0) return { dot: '🔴', label: `${Math.abs(diffDays)}d vencido`, cls: 'text-red-600 font-bold' };
  if (diffDays <= 7) return { dot: '🟡', label: `${diffDays}d`, cls: 'text-amber-600 font-bold' };
  return { dot: '🟢', label: `${diffDays}d`, cls: 'text-green-700' };
}

export function CarteraPanel() {
  const lblCxc = useLabel('cxc');
  const lblCxp = useLabel('cxp');

  const [kpiOpen, setKpiOpen] = useState(true);
  const [alertsOpen, setAlertsOpen] = useState(true);
  const [expandedNote, setExpandedNote] = useState(null);

  const {
    kpi, alerts, payments, selectedId, selectedEntry,
    loading, subTab, setSubTab, sortBy, setSortBy,
    abonoForm, setAbonoForm,
    filtered, cxcCount, cxpCount, items,
    selectEntry, registerAbono, deleteEntry,
  } = useCartera();

  const selectedOrig = Number(selectedEntry?.original_amount || 0);
  const selectedRem = Number(selectedEntry?.remaining_balance || 0);

  return (
    <div className="space-y-2 font-mono">

      {/* ═══ KPI SUMMARY BAR ═══ */}
      <div style={{ border: '2px solid #000' }}>
        <button
          onClick={() => setKpiOpen((p) => !p)}
          style={{
            width: '100%', display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', padding: '4px 8px',
            background: '#000', color: '#fff', border: 'none', cursor: 'pointer',
            fontFamily: "'IBM Plex Mono', monospace", fontSize: 9,
            fontWeight: 700, textTransform: 'uppercase',
          }}
        >
          <span>📊 Resumen Cartera</span>
          <span style={{ color: '#999' }}>{kpiOpen ? '▲' : '▼'}</span>
        </button>
        {kpiOpen && kpi && (
          <div className="grid grid-cols-4 divide-x divide-black" style={{ borderTop: '2px solid #000' }}>
            {[
              { label: 'CXC',     value: kpi.cxc_total,      cls: 'text-green-700',  bg: 'bg-green-50' },
              { label: 'CXP',     value: kpi.cxp_total,      cls: 'text-amber-700',  bg: 'bg-amber-50' },
              { label: 'Vencido', value: kpi.vencido_total,   cls: 'text-red-700',    bg: 'bg-red-50' },
              { label: '< 7d',    value: kpi.proximo_total,   cls: 'text-yellow-700', bg: 'bg-yellow-50' },
            ].map((k) => (
              <div key={k.label} className={`p-1.5 text-center ${k.bg}`}>
                <div style={{ fontSize: 7, textTransform: 'uppercase', fontWeight: 700, color: '#999' }}>{k.label}</div>
                <div className={k.cls} style={{ fontSize: 10, fontWeight: 700 }}>{fmtMoney(k.value)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ═══ ALERTS ═══ */}
      {alerts.length > 0 && (
        <div style={{ border: '2px solid #000' }}>
          <button
            onClick={() => setAlertsOpen((p) => !p)}
            style={{
              width: '100%', display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', padding: '4px 8px',
              background: '#7f1d1d', color: '#fff', border: 'none', cursor: 'pointer',
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 9,
              fontWeight: 700, textTransform: 'uppercase',
            }}
          >
            <span>🔔 Alertas ({alerts.length})</span>
            <span style={{ color: '#fca5a5' }}>{alertsOpen ? '▲' : '▼'}</span>
          </button>
          {alertsOpen && (
            <div style={{ maxHeight: 144, overflowY: 'auto' }}>
              {alerts.map((a, i) => {
                const sevBg = a.severity === 'critical' ? 'bg-red-50' :
                              a.severity === 'warning' ? 'bg-amber-50' :
                              a.severity === 'success' ? 'bg-green-50' : 'bg-orange-50';
                const badgeCls = a.severity === 'critical' ? 'bg-red-100 border-red-500 text-red-800' :
                                 a.severity === 'warning' ? 'bg-amber-100 border-amber-500 text-amber-800' :
                                 a.severity === 'success' ? 'bg-green-100 border-green-500 text-green-800' :
                                 'bg-orange-100 border-orange-500 text-orange-800';
                const msgCls = a.severity === 'critical' ? 'text-red-600 font-bold' :
                               a.severity === 'warning' ? 'text-amber-600' :
                               a.severity === 'success' ? 'text-green-600' : 'text-orange-600';

                return (
                  <div
                    key={i}
                    className={`flex items-start gap-1.5 ${sevBg}`}
                    style={{ padding: '4px 8px', borderBottom: '1px solid #e5e5e5', fontSize: 9 }}
                  >
                    <span style={{ fontSize: 11, flexShrink: 0, marginTop: 2 }}>{a.icon}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div className="flex items-center gap-1">
                        <span
                          className={badgeCls}
                          style={{ padding: '0 2px', fontSize: 7, fontWeight: 700, border: '1px solid' }}
                        >{a.type}</span>
                        <span style={{ fontWeight: 700 }}>{a.account_type}</span>
                        <span style={{ color: '#999' }} className="truncate">{a.third_party}</span>
                      </div>
                      <div className={msgCls} style={{ fontSize: 8 }}>{a.message}</div>
                      {a.next_payment && (
                        <div style={{ fontSize: 7, color: '#3b82f6', marginTop: 2 }}>
                          📅 Prox corte: {a.next_payment} · c/{a.frequency}d
                        </div>
                      )}
                    </div>
                    <span style={{ fontSize: 8, color: '#999', flexShrink: 0 }}>{a.due_date}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ═══ SUB-TABS ═══ */}
      <div className="flex" style={{ border: '2px solid #000', overflow: 'hidden' }}>
        {[
          { key: 'TODAS', label: `TODAS (${items.length})` },
          { key: 'CXC',   label: `📥 CXC (${cxcCount})` },
          { key: 'CXP',   label: `📤 CXP (${cxpCount})` },
        ].map((st) => (
          <button
            key={st.key}
            onClick={() => { setSubTab(st.key); }}
            style={{
              flex: 1, padding: '4px 0', border: 'none',
              borderRight: '1px solid #000', cursor: 'pointer',
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 9,
              fontWeight: 700, textTransform: 'uppercase',
              background: subTab === st.key ? '#000' : '#f5f5f0',
              color: subTab === st.key ? '#fff' : '#999',
              transition: 'all 0.15s',
            }}
          >{st.label}</button>
        ))}
      </div>

      {/* ═══ SORT BAR ═══ */}
      <div
        className="flex items-center"
        style={{
          border: '2px solid #000', borderTop: 0,
          background: '#f5f5f0', overflowX: 'auto',
        }}
      >
        <span style={{ padding: '4px 8px', fontSize: 8, fontWeight: 700, textTransform: 'uppercase', color: '#999', whiteSpace: 'nowrap' }}>
          ⇅ Ordenar:
        </span>
        {SORT_OPTIONS.map((s) => (
          <button
            key={s.key}
            onClick={() => setSortBy(s.key)}
            style={{
              padding: '4px 8px', border: 'none', borderLeft: '1px solid #000',
              fontSize: 8, fontWeight: 700, textTransform: 'uppercase',
              fontFamily: "'IBM Plex Mono', monospace", whiteSpace: 'nowrap',
              cursor: 'pointer',
              background: sortBy === s.key ? '#000' : 'transparent',
              color: sortBy === s.key ? '#fff' : '#999',
              transition: 'all 0.15s',
            }}
          >{s.icon} {s.label}</button>
        ))}
      </div>

      {/* ═══ ENTRIES TABLE ═══ */}
      <div style={{ border: '2px solid #000', overflow: 'hidden' }}>
        <table style={{
          width: '100%', borderCollapse: 'collapse',
          fontFamily: "'IBM Plex Mono', monospace", fontSize: 10,
        }}>
          <thead>
            <tr style={{ background: '#000', color: '#fff', textTransform: 'uppercase' }}>
              <th style={{ padding: 4, borderRight: '1px solid #333', textAlign: 'left', width: '28%' }}>Tercero</th>
              <th style={{ padding: 4, borderRight: '1px solid #333', textAlign: 'right', width: '18%' }}>Monto</th>
              <th style={{ padding: 4, borderRight: '1px solid #333', textAlign: 'center', width: '30%' }}>Progreso</th>
              <th style={{ padding: 4, borderRight: '1px solid #333', textAlign: 'center', width: '14%' }}>Vence</th>
              <th style={{ padding: 4, textAlign: 'center', width: '10%' }}>Est.</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => {
              const sem = getDueSemaforo(c.due_date);
              const isSelected = selectedId === c.id;
              const orig = Number(c.original_amount || 0);
              const rem = Number(c.remaining_balance || 0);
              const paid = orig - rem;
              const pct = orig > 0 ? Math.round((paid / orig) * 100) : 0;
              const startStr = c.start_date
                ? new Date(c.start_date).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' })
                : '—';
              const dueStr = c.due_date
                ? new Date(c.due_date).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' })
                : '—';

              return (
                <tbody key={c.id}>
                  {/* ── ENTRY ROW ── */}
                  <tr
                    onClick={() => selectEntry(c)}
                    style={{
                      cursor: 'pointer', borderBottom: '1px solid #e0e0d8',
                      background: isSelected ? '#000' : '#fff',
                      color: isSelected ? '#fff' : '#000',
                      transition: 'all 0.15s',
                    }}
                  >
                    {/* TERCERO */}
                    <td style={{ padding: 4, borderRight: '1px solid #e0e0d8' }}>
                      <div className="flex items-center gap-1">
                        <span
                          style={{
                            fontSize: 7, fontWeight: 700, padding: '0 2px',
                            border: '1px solid',
                            background: isSelected ? 'transparent' :
                              c.type === 'CXC' ? '#dcfce7' : '#fef3c7',
                            borderColor: isSelected ? '#fff' :
                              c.type === 'CXC' ? '#22c55e' : '#f59e0b',
                            color: isSelected ? '#fff' :
                              c.type === 'CXC' ? '#166534' : '#92400e',
                          }}
                        >{c.type}</span>
                        <span style={{ fontWeight: 700, maxWidth: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {c.third_party_name || '—'}
                        </span>
                      </div>
                      <div style={{ fontSize: 8, color: isSelected ? '#999' : '#999', marginTop: 2, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span>{startStr} → {dueStr}</span>
                        {c.payment_frequency && (
                          <span style={{
                            padding: '0 2px', fontSize: 6, fontWeight: 700,
                            border: '1px solid',
                            borderColor: isSelected ? '#666' : '#93c5fd',
                            background: isSelected ? 'transparent' : '#eff6ff',
                            color: isSelected ? '#999' : '#2563eb',
                          }}>c/{c.payment_frequency}d</span>
                        )}
                      </div>
                    </td>

                    {/* MONTO */}
                    <td style={{ padding: 4, borderRight: '1px solid #e0e0d8', textAlign: 'right' }}>
                      <div style={{ fontWeight: 700 }}>{fmtMoney(orig)}</div>
                      <div style={{ fontSize: 8, color: isSelected ? '#999' : '#ef4444' }}>Debe: {fmtMoney(rem)}</div>
                    </td>

                    {/* PROGRESO */}
                    <td style={{ padding: 4, borderRight: '1px solid #e0e0d8' }}>
                      <div className="flex items-center gap-1">
                        <div style={{
                          flex: 1, height: 8, background: '#e5e7eb',
                          border: '1px solid #d1d5db', overflow: 'hidden', minWidth: 40,
                        }}>
                          <div style={{
                            height: '100%', width: `${Math.min(pct, 100)}%`,
                            background: pct >= 100 ? '#22c55e' : pct >= 50 ? '#3b82f6' : '#f59e0b',
                            transition: 'width 0.3s',
                          }} />
                        </div>
                        <span style={{
                          fontSize: 8, fontWeight: 700,
                          color: isSelected ? '#fff' : pct >= 100 ? '#16a34a' : '#666',
                        }}>{pct}%</span>
                      </div>
                      <div style={{ fontSize: 8, marginTop: 2, color: isSelected ? '#999' : '#999' }}>
                        Abonado: {fmtMoney(paid)}
                      </div>
                    </td>

                    {/* VENCE */}
                    <td style={{ padding: 4, borderRight: '1px solid #e0e0d8', textAlign: 'center' }}>
                      <span style={{ fontSize: 9 }}>{sem.dot}</span>
                      <div className={isSelected ? '' : sem.cls} style={{ fontSize: 8, color: isSelected ? '#999' : undefined }}>
                        {sem.label}
                      </div>
                    </td>

                    {/* ESTADO */}
                    <td style={{ padding: 4, textAlign: 'center' }}>
                      <span style={{
                        padding: '1px 4px', fontSize: 7, fontWeight: 700,
                        border: '1px solid',
                        ...(isSelected ? { borderColor: '#fff', color: '#fff' } :
                          c.status === 'PAGADO' ? { background: '#dcfce7', borderColor: '#22c55e', color: '#15803d' } :
                          c.status === 'VENCIDO' ? { background: '#fee2e2', borderColor: '#ef4444', color: '#b91c1c' } :
                          { background: '#fef9c3', borderColor: '#eab308', color: '#a16207' }),
                      }}>
                        {c.status === 'PENDIENTE' ? 'PEND' : c.status === 'PAGADO' ? '✓' : c.status || 'PEND'}
                      </span>
                    </td>
                  </tr>

                  {/* ── EXPANDED ROW ── */}
                  {isSelected && (
                    <tr>
                      <td colSpan={5} style={{ padding: 0 }}>
                        <div style={{ borderTop: '2px solid #000', background: '#fff' }}>
                          {/* Header */}
                          <div className="flex items-center justify-between" style={{ padding: '4px 8px', background: '#fafafa', borderBottom: '1px solid #e0e0d8' }}>
                            <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase' }}>
                              Historial de Abonos · {c.third_party_name}
                            </span>
                            <div className="flex items-center gap-2">
                              <span style={{ fontSize: 8, color: '#999' }}>
                                {fmtMoney(paid)} de {fmtMoney(orig)}
                              </span>
                              <div style={{ width: 48, height: 6, background: '#e5e7eb', border: '1px solid #d1d5db', overflow: 'hidden' }}>
                                <div style={{ height: '100%', width: `${Math.min(pct, 100)}%`, background: pct >= 100 ? '#22c55e' : '#3b82f6' }} />
                              </div>
                              <span style={{ fontSize: 8, fontWeight: 700 }}>{pct}%</span>
                            </div>
                          </div>

                          {/* Payments table */}
                          {payments.length > 0 ? (
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10 }}>
                              <thead>
                                <tr style={{ background: '#f5f5f0', textTransform: 'uppercase', color: '#999', fontSize: 8 }}>
                                  <th style={{ padding: 4, textAlign: 'left', borderRight: '1px solid #e0e0d8' }}>Fecha</th>
                                  <th style={{ padding: 4, textAlign: 'right', borderRight: '1px solid #e0e0d8' }}>Abono</th>
                                  <th style={{ padding: 4, textAlign: 'right', borderRight: '1px solid #e0e0d8' }}>Saldo</th>
                                  <th style={{ padding: 4, textAlign: 'left' }}>Nota</th>
                                </tr>
                              </thead>
                              <tbody>
                                {payments.map((p) => (
                                  <tbody key={p.id}>
                                    <tr
                                      onClick={() => setExpandedNote(expandedNote === p.id ? null : p.id)}
                                      style={{ borderBottom: '1px solid #f0f0e8', cursor: 'pointer' }}
                                    >
                                      <td style={{ padding: 4, borderRight: '1px solid #e0e0d8' }}>{p.payment_date}</td>
                                      <td style={{ padding: 4, borderRight: '1px solid #e0e0d8', textAlign: 'right', fontWeight: 700, color: '#15803d' }}>
                                        +{fmtMoney(p.amount)}
                                      </td>
                                      <td style={{ padding: 4, borderRight: '1px solid #e0e0d8', textAlign: 'right' }}>
                                        {p.balance_after != null ? fmtMoney(p.balance_after) : '—'}
                                      </td>
                                      <td style={{ padding: 4, color: '#999' }}>
                                        <div className="flex items-center justify-between">
                                          <span className={expandedNote === p.id ? '' : 'truncate'} style={{ maxWidth: expandedNote === p.id ? 'none' : 70 }}>
                                            {p.note || '—'}
                                          </span>
                                          {p.note && p.note.length > 12 && (
                                            <span style={{ fontSize: 7, color: '#ccc', flexShrink: 0, marginLeft: 4 }}>
                                              {expandedNote === p.id ? '▲' : '▼'}
                                            </span>
                                          )}
                                        </div>
                                      </td>
                                    </tr>
                                    {expandedNote === p.id && p.note && (
                                      <tr>
                                        <td colSpan={4} style={{ padding: '4px 8px', background: '#fafafa', borderBottom: '1px solid #e0e0d8' }}>
                                          <div style={{ fontSize: 9, color: '#666', whiteSpace: 'pre-wrap' }}>{p.note}</div>
                                        </td>
                                      </tr>
                                    )}
                                  </tbody>
                                ))}
                              </tbody>
                            </table>
                          ) : (
                            <div style={{ padding: 12, textAlign: 'center', fontSize: 10, color: '#ccc', textTransform: 'uppercase' }}>
                              Sin abonos
                            </div>
                          )}

                          {/* Abono form */}
                          <div style={{ borderTop: '2px solid #000', padding: 8 }}>
                            {!abonoForm.open ? (
                              <button
                                onClick={() => setAbonoForm((f) => ({ ...f, open: true }))}
                                className="cv2-btn cv2-btn-secondary"
                                style={{ width: '100%', fontSize: 9 }}
                              >
                                + Registrar Abono
                              </button>
                            ) : (
                              <div className="space-y-1">
                                <div className="flex justify-between" style={{ fontSize: 8, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>
                                  <span>Nuevo abono</span>
                                  <span style={{ color: '#ef4444' }}>Pendiente: {fmtMoney(selectedRem)}</span>
                                </div>
                                <div className="grid grid-cols-2 gap-1">
                                  <input
                                    type="number"
                                    value={abonoForm.amount}
                                    onChange={(e) => setAbonoForm((f) => ({ ...f, amount: e.target.value }))}
                                    placeholder="$ Monto"
                                    max={selectedRem}
                                    className="cv2-input"
                                    autoFocus
                                  />
                                  <input
                                    type="date"
                                    value={abonoForm.date}
                                    onChange={(e) => setAbonoForm((f) => ({ ...f, date: e.target.value }))}
                                    className="cv2-input"
                                  />
                                </div>
                                <input
                                  type="text"
                                  value={abonoForm.note}
                                  onChange={(e) => setAbonoForm((f) => ({ ...f, note: e.target.value }))}
                                  placeholder="Nota (ej: Cuota #3, transferencia Bancolombia...)"
                                  className="cv2-input"
                                />
                                <div className="flex gap-1">
                                  <button
                                    onClick={() => registerAbono(c.id)}
                                    disabled={loading || !abonoForm.amount || parseFloat(abonoForm.amount) <= 0}
                                    className="cv2-btn"
                                    style={{ flex: 1, fontSize: 9 }}
                                  >
                                    Confirmar Abono
                                  </button>
                                  <button
                                    onClick={() => setAbonoForm({ amount: '', date: new Date().toISOString().split('T')[0], note: '', open: false })}
                                    className="cv2-btn cv2-btn-secondary"
                                    style={{ padding: '6px 12px', fontSize: 9 }}
                                  >✕</button>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              );
            })}
          </tbody>
        </table>

        {filtered.length === 0 && (
          <div style={{
            padding: 16, textAlign: 'center', fontSize: 10,
            fontFamily: "'IBM Plex Mono', monospace",
            color: '#ccc', textTransform: 'uppercase',
          }}>
            {subTab === 'TODAS' ? 'Sin cuentas activas' : `Sin cuentas ${subTab}`}
          </div>
        )}
      </div>
    </div>
  );
}

export default CarteraPanel;
