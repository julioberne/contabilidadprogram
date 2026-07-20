/* ============================================================
   ContabilidadApp.jsx — FIN-SYS Contabilidad v2
   Orquestador principal · Arquitectura modular por hooks
   ============================================================ */
import { useState } from 'react';
import './contabilidad-v2.css';

// Engine: providers (Empresa → Tenant → Draft)
import { EmpresaProvider, useEmpresa } from './engine/EmpresaProvider.jsx';
import { TenantProvider, useLabel } from './engine/TenantProvider.jsx';
import { TransactionDraftProvider, useTransactionDraft } from './engine/TransactionDraftProvider.jsx';

// Módulos (adapters sobre componentes v1)
import RegistroModule from './modules/registro/RegistroModule.jsx';
import VozModule from './modules/voz/VozModule.jsx';

// Componentes propios
import KPIBar from './components/KPIBar.jsx';
import ContextPanel from './components/ContextPanel.jsx';

// Modales v1 (imports transitorios — se mudan en Fase 7)
import ThirdPartyModal from '../components/ThirdPartyModal.jsx';
import EvidenceModal from '../components/EvidenceModal.jsx';

function ContabilidadInner() {
  const [activeTab, setActiveTab] = useState('terceros');

  // ── Datos de empresa/portafolio + dashboard (EmpresaProvider) ──
  const dashboard = useEmpresa();
  const { activePortfolio, setActivePortfolio } = dashboard;

  // ── Draft global (para los modales) ────────────────────────
  const draft = useTransactionDraft();

  // ── Modal de comprobante (se cablea al Libro Diario en Fase 3) ──
  const [evidenceUrl, setEvidenceUrl] = useState(null);
  const [selectedEvidenceTx, setSelectedEvidenceTx] = useState(null);

  // ── Labels dinámicos ───────────────────────────────────────
  const lblTercero = useLabel('tercero');

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

        {/* ── COL 1: Panel Izquierdo (Voz IA + Registro v1) ── */}
        <div style={{ borderRight: '2px solid #000', background: '#fff', overflow: 'auto' }}>
          <div style={{ padding: 12 }} className="space-y-2">
            <VozModule />
            <RegistroModule />
          </div>
        </div>

        {/* ── COL 2: Panel Derecho (Legos Modulares) ────── */}
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

      {/* ── ROW: Libro Diario Abajo ───────────────── */}
      <div style={{ overflow: 'auto', background: '#fafaf5', borderTop: '2px solid #000' }}>
        <div style={{
          padding: '8px 16px',
          borderBottom: '2px solid #000',
          background: '#fff',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span style={{
            fontSize: 12, fontWeight: 800,
            fontFamily: "'IBM Plex Mono', monospace",
            textTransform: 'uppercase', letterSpacing: '0.1em',
            color: '#000',
          }}>
            ≡ Libro Diario · {dashboard.transactions.length} de {dashboard.totalTxCount}
          </span>
          <button
            onClick={dashboard.refreshTransactions}
            className="cv2-btn cv2-btn-secondary"
            style={{ fontSize: 10, padding: '4px 12px', fontWeight: 800, color: '#000', border: '2px solid #000' }}
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
                fontSize: 14, color: '#000', fontWeight: 800, textTransform: 'uppercase',
              }}>
                ▓ SIN TRANSACCIONES EN "{activePortfolio}"
              </div>
            )}

            {dashboard.transactions.length < dashboard.totalTxCount && (
              <div style={{ padding: 12, textAlign: 'center' }}>
                <button
                  onClick={() => dashboard.loadMoreTransactions(dashboard.transactions.length)}
                  className="cv2-btn cv2-btn-secondary"
                  style={{ fontSize: 10, fontWeight: 800, color: '#000', border: '2px solid #000' }}
                >
                  CARGAR MÁS ({dashboard.totalTxCount - dashboard.transactions.length} RESTANTES)
                </button>
              </div>
            )}
          </div>
        </div>

      {/* 🖼️ Modal de comprobante (v1 — se cablea al diario en Fase 3) */}
      <EvidenceModal
        evidenceUrl={evidenceUrl}
        selectedEvidenceTx={selectedEvidenceTx}
        onClose={() => {
          setEvidenceUrl(null);
          setSelectedEvidenceTx(null);
        }}
        profile={dashboard.profile}
      />

      {/* 👤 Modal de terceros (v1 — wiring verbatim de App.jsx) */}
      <ThirdPartyModal
        isOpen={draft.isThirdPartyModalOpen}
        onClose={() => draft.setIsThirdPartyModalOpen(false)}
        onSelect={(tp) => {
          draft.setThirdPartyType(tp.identification_type);
          draft.setThirdPartyNumber(tp.identification_number);
          draft.setThirdPartyName(tp.name);
          draft.setThirdPartyEmail(tp.email);
          draft.setThirdPartyPhone(tp.phone);
          draft.setThirdPartyWebsite(tp.website);
        }}
      />
    </div>
  );
}

// ── Puente: TenantProvider con la industria REAL de la empresa activa ──
function TenantBridge({ children }) {
  const { activeCompany } = useEmpresa();
  return (
    <TenantProvider industry={activeCompany?.industry}>
      {children}
    </TenantProvider>
  );
}

// ── Export: jerarquía Empresa → Tenant → Draft ──────────────
export default function ContabilidadApp() {
  return (
    <EmpresaProvider>
      <TenantBridge>
        <TransactionDraftProvider>
          <ContabilidadInner />
        </TransactionDraftProvider>
      </TenantBridge>
    </EmpresaProvider>
  );
}
