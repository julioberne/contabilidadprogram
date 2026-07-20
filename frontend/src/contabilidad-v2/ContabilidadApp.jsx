/* ============================================================
   ContabilidadApp.jsx — FIN-SYS Contabilidad v2
   Orquestador principal · Arquitectura modular por hooks
   ============================================================ */
import { useState } from 'react';
import './contabilidad-v2.css';

// Engine: providers (Empresa → Tenant → Draft)
import { EmpresaProvider, useEmpresa } from './engine/EmpresaProvider.jsx';
import { TenantProvider } from './engine/TenantProvider.jsx';
import { TransactionDraftProvider, useTransactionDraft } from './engine/TransactionDraftProvider.jsx';

// Módulos (adapters sobre componentes v1)
import RegistroModule from './modules/registro/RegistroModule.jsx';
import VozModule from './modules/voz/VozModule.jsx';

// Componentes propios
import KPIBar from './components/KPIBar.jsx';
import ContextPanelAdapter from './components/ContextPanelAdapter.jsx';
import DiarioModule from './modules/diario/DiarioModule.jsx';

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

  // ── Modal de comprobante (cableado al Libro Diario) ────────
  const [evidenceUrl, setEvidenceUrl] = useState(null);
  const [selectedEvidenceTx, setSelectedEvidenceTx] = useState(null);

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

        {/* ── COL 2: Panel Derecho (ContextPanel v1 · 7 tabs) ── */}
        <div style={{
          borderLeft: '2px solid #000', background: '#fff',
          overflow: 'auto', display: 'flex', flexDirection: 'column',
        }}>
          <ContextPanelAdapter
            activeTab={activeTab}
            setActiveTab={setActiveTab}
          />
        </div>
      </div>

      {/* ── ROW: Libro Diario v1 (edición inline + expandible) ── */}
      <DiarioModule
        onEvidenceClick={(tx) => {
          setSelectedEvidenceTx(tx);
          setEvidenceUrl(tx.evidence_file_path || "recibo_demo.png");
        }}
      />

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
