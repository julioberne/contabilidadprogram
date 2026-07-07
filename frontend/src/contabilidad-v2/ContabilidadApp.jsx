/* ============================================================
   ContabilidadApp.jsx — FIN-SYS Contabilidad v2
   Orquestador principal · Arquitectura modular por hooks
   ============================================================ */
import { useState, useCallback } from 'react';
import './contabilidad-v2.css';

// Hooks centrales
import { useDashboardData } from './hooks/useDashboardData.js';
import { useCalculator } from './hooks/useCalculator.js';

// Engine de templates
import { TenantProvider, useLabel } from './engine/TenantProvider.jsx';

// Componentes
import KPIBar from './components/KPIBar.jsx';
import ContextPanel from './components/ContextPanel.jsx';
import { API } from '../config';

// ── Secciones del panel izquierdo ──────────────────────────
const LEFT_SECTIONS = [
  { id: 'registro',    icon: '✎', label: 'REGISTRO' },
  { id: 'voz',         icon: '🎙', label: 'VOZ' },
  { id: 'borradores',  icon: '📋', label: 'BORRADORES' },
];

function ContabilidadInner() {
  const [activePortfolio, setActivePortfolio] = useState('Negocio A');
  const [activeSection, setActiveSection] = useState('registro');
  const [activeTab, setActiveTab] = useState('terceros');

  // ── Hook maestro — reemplaza fetchData() ──────────────────
  const dashboard = useDashboardData(activePortfolio);

  // ── Calculadora ────────────────────────────────────────────
  const calc = useCalculator();

  // ── Labels dinámicos ───────────────────────────────────────
  const lblTercero = useLabel('tercero');
  const lblCxc = useLabel('cxc');
  const lblCxp = useLabel('cxp');

  // ── Tabs del Panel Contextual ──────────────────────────────
  const PANEL_TABS = [
    { key: 'terceros',  icon: '👤', label: lblTercero + 's' },
    { key: 'cartera',   icon: '📄', label: 'Cartera' },
    { key: 'activos',   icon: '📦', label: 'Recursos' },
    { key: 'etiquetas', icon: '🏷️', label: 'Tags' },
    { key: 'impuestos', icon: '📈', label: 'Tasas' },
    { key: 'cuentas',   icon: '💳', label: 'Cuentas' },
    { key: 'usuario',   icon: '⚙',  label: 'Config' },
  ];

  return (
    <div className="cv2-root">
      {/* ═══ KPI BAR ═══ */}
      <KPIBar cajaViva={dashboard.cajaViva} />

      {/* ═══ PORTFOLIO SWITCHER ═══ */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 0,
        borderBottom: '2px solid #000', background: '#fff',
      }}>
        {dashboard.portfolios.map(p => (
          <button
            key={p.name}
            onClick={() => setActivePortfolio(p.name)}
            style={{
              padding: '6px 14px',
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 10,
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              cursor: 'pointer',
              border: 'none',
              borderRight: '2px solid #000',
              background: activePortfolio === p.name ? '#000' : '#f5f5f0',
              color: activePortfolio === p.name ? '#fff' : '#666',
              transition: 'all 0.15s',
            }}
          >
            {p.name}
          </button>
        ))}
        <div style={{
          marginLeft: 'auto', padding: '4px 12px',
          fontSize: 9, fontFamily: "'IBM Plex Mono', monospace",
          color: '#999', textTransform: 'uppercase',
        }}>
          v2 · {dashboard.transactions.length}/{dashboard.totalTxCount} TX
        </div>
      </div>

      {/* ═══ 3-COLUMN GRID ═══ */}
      <div className="cv2-grid">

        {/* ── COL 1: Panel Izquierdo (Registro) ──────────── */}
        <div style={{ borderRight: '2px solid #000', background: '#fff', overflow: 'auto' }}>
          {/* Section tabs */}
          <div style={{
            display: 'flex', borderBottom: '2px solid #000',
          }}>
            {LEFT_SECTIONS.map(s => (
              <button
                key={s.id}
                onClick={() => setActiveSection(s.id)}
                style={{
                  flex: 1, padding: '8px 4px',
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: 9, fontWeight: 700,
                  textTransform: 'uppercase',
                  cursor: 'pointer',
                  border: 'none',
                  borderRight: '1px solid #000',
                  background: activeSection === s.id ? '#000' : 'transparent',
                  color: activeSection === s.id ? '#fff' : '#999',
                }}
              >
                {s.icon} {s.label}
              </button>
            ))}
          </div>

          {/* Section content */}
          <div style={{ padding: 12 }}>
            {activeSection === 'registro' && (
              <div>
                <div className="cv2-section-label">
                  Formulario de Registro · Fase 3
                </div>
                <p style={{
                  fontSize: 10, fontFamily: "'IBM Plex Mono', monospace",
                  color: '#999', textTransform: 'uppercase',
                }}>
                  ▓ El formulario de transacciones se construirá en la Fase 3.
                  Por ahora puedes ver los KPIs y datos del portafolio "{activePortfolio}" arriba.
                </p>

                {/* Calculator toggle */}
                <button
                  onClick={calc.toggle}
                  className="cv2-btn"
                  style={{ marginTop: 12, width: '100%' }}
                >
                  {calc.open ? '▲ Cerrar Calculadora' : '⊞ Calculadora Rápida'}
                </button>

                {calc.open && (
                  <div style={{
                    border: '2px solid #000', marginTop: 8,
                    background: '#fff', boxShadow: '3px 3px 0 #000',
                  }}>
                    <div style={{
                      padding: '8px 12px', borderBottom: '2px solid #000',
                      textAlign: 'right', fontSize: 18,
                      fontFamily: "'IBM Plex Mono', monospace",
                      fontWeight: 700, background: '#f5f5f0',
                    }}>
                      {calc.display}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 0 }}>
                      {['7','8','9','÷','4','5','6','×','1','2','3','-','C','0','=','+'].map(key => (
                        <button
                          key={key}
                          onClick={() => {
                            if (key === 'C') calc.clear();
                            else if (key === '=') calc.calculate();
                            else if (['+','-','×','÷'].includes(key)) calc.setOperation(key);
                            else calc.input(key);
                          }}
                          style={{
                            padding: '10px 0',
                            fontFamily: "'IBM Plex Mono', monospace",
                            fontSize: 14, fontWeight: 700,
                            cursor: 'pointer',
                            border: '1px solid #000',
                            background: ['+','-','×','÷'].includes(key) ? '#000' : key === 'C' ? '#c00' : key === '=' ? '#00e676' : '#fff',
                            color: ['+','-','×','÷'].includes(key) ? '#fff' : key === 'C' ? '#fff' : '#000',
                          }}
                        >
                          {key}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeSection === 'voz' && (
              <div>
                <div className="cv2-section-label">Grabador de Voz · Fase 3</div>
                <p style={{
                  fontSize: 10, fontFamily: "'IBM Plex Mono', monospace",
                  color: '#999', textTransform: 'uppercase',
                }}>
                  ▓ El grabador de voz se integrará en la Fase 3.
                </p>
              </div>
            )}

            {activeSection === 'borradores' && (
              <div>
                <div className="cv2-section-label">Borradores de Voz · Fase 3</div>
                <p style={{
                  fontSize: 10, fontFamily: "'IBM Plex Mono', monospace",
                  color: '#999', textTransform: 'uppercase',
                }}>
                  ▓ Los borradores se integrarán en la Fase 3.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* ── COL 2: Centro (Libro Diario) ───────────────── */}
        <div style={{ overflow: 'auto', background: '#fafaf5' }}>
          <div style={{
            padding: '8px 16px',
            borderBottom: '2px solid #000',
            background: '#fff',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{
              fontSize: 10, fontWeight: 700,
              fontFamily: "'IBM Plex Mono', monospace",
              textTransform: 'uppercase', letterSpacing: '0.1em',
            }}>
              ≡ Libro Diario · {dashboard.transactions.length} de {dashboard.totalTxCount}
            </span>
            <button
              onClick={dashboard.refreshTransactions}
              className="cv2-btn cv2-btn-secondary"
              style={{ fontSize: 8, padding: '3px 8px' }}
            >
              ↻ Refrescar
            </button>
          </div>

          {/* Transaction list — placeholder table */}
          <div style={{ padding: 0 }}>
            <table style={{
              width: '100%', borderCollapse: 'collapse',
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 10,
            }}>
              <thead>
                <tr style={{ background: '#000', color: '#fff', textTransform: 'uppercase', fontSize: 8 }}>
                  <th style={{ padding: '6px 8px', borderRight: '1px solid #333', textAlign: 'left' }}>Fecha</th>
                  <th style={{ padding: '6px 8px', borderRight: '1px solid #333', textAlign: 'left' }}>Concepto</th>
                  <th style={{ padding: '6px 8px', borderRight: '1px solid #333', textAlign: 'left' }}>{lblTercero}</th>
                  <th style={{ padding: '6px 8px', borderRight: '1px solid #333', textAlign: 'left' }}>Categoría</th>
                  <th style={{ padding: '6px 8px', textAlign: 'right' }}>Monto</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.transactions.map((tx, i) => (
                  <tr
                    key={tx.id || i}
                    style={{
                      borderBottom: '1px solid #e0e0d8',
                      background: i % 2 === 0 ? '#fff' : '#fafaf5',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = '#e8ffe8'}
                    onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? '#fff' : '#fafaf5'}
                  >
                    <td style={{ padding: '5px 8px', borderRight: '1px solid #f0f0e8' }}>
                      {tx.transaction_date || '—'}
                    </td>
                    <td style={{
                      padding: '5px 8px', borderRight: '1px solid #f0f0e8',
                      fontWeight: 700, maxWidth: 200, overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {tx.concept || '—'}
                    </td>
                    <td style={{
                      padding: '5px 8px', borderRight: '1px solid #f0f0e8',
                      color: '#666', maxWidth: 120, overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {tx.third_party_name || '—'}
                    </td>
                    <td style={{
                      padding: '5px 8px', borderRight: '1px solid #f0f0e8',
                      color: '#999', fontSize: 9,
                    }}>
                      {tx.category || '—'}
                    </td>
                    <td style={{
                      padding: '5px 8px', textAlign: 'right', fontWeight: 700,
                      color: tx.type === 'INGRESO' ? '#00c853' : tx.type === 'GASTO' ? '#c00' : '#000',
                    }}>
                      {tx.type === 'GASTO' ? '-' : ''}${Number(tx.amount || 0).toLocaleString('es-CO', { maximumFractionDigits: 0 })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {dashboard.transactions.length === 0 && (
              <div style={{
                padding: 40, textAlign: 'center',
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 10, color: '#999', textTransform: 'uppercase',
              }}>
                ▓ Sin transacciones en "{activePortfolio}"
              </div>
            )}

            {dashboard.transactions.length < dashboard.totalTxCount && (
              <div style={{ padding: 12, textAlign: 'center' }}>
                <button
                  onClick={() => dashboard.loadMoreTransactions(dashboard.transactions.length)}
                  className="cv2-btn cv2-btn-secondary"
                  style={{ fontSize: 9 }}
                >
                  Cargar más ({dashboard.totalTxCount - dashboard.transactions.length} restantes)
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ── COL 3: Panel Derecho (Legos Modulares) ────── */}
        <div style={{
          borderLeft: '2px solid #000', background: '#fff',
          overflow: 'auto', display: 'flex', flexDirection: 'column',
        }}>
          <ContextPanel
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            activePortfolio={activePortfolio}
            allThirdParties={dashboard.allThirdParties}
          />
        </div>
      </div>
    </div>
  );
}

// ── Export con TenantProvider envolviendo todo ──────────────
export default function ContabilidadApp() {
  return (
    <TenantProvider>
      <ContabilidadInner />
    </TenantProvider>
  );
}
