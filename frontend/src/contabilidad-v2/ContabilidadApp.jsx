/* ============================================================
   ContabilidadApp.jsx — FIN-SYS Contabilidad (unificado)
   UI de v1 (layout verbatim de App.jsx:423-714) sobre la
   arquitectura modular v2: providers (Empresa → Tenant → Draft)
   + módulos adapter que montan los componentes v1 reales.
   ============================================================ */
import { useState } from 'react';
import './contabilidad-v2.css';

// Engine: providers (Empresa → Tenant → Draft)
import { EmpresaProvider, useEmpresa } from './engine/EmpresaProvider.jsx';
import { TenantProvider } from './engine/TenantProvider.jsx';
import { TransactionDraftProvider, useTransactionDraft } from './engine/TransactionDraftProvider.jsx';

// Hooks
import { useAdminActions } from './hooks/useAdminActions.js';

// Módulos (adapters sobre componentes v1)
import RegistroModule from './modules/registro/RegistroModule.jsx';
import VozModule from './modules/voz/VozModule.jsx';
import DiarioModule from './modules/diario/DiarioModule.jsx';
import ContextPanelAdapter from './components/ContextPanelAdapter.jsx';

// Componentes v1 (imports transitorios — se mudan en Fase 7)
import CompanySelector from './modules/empresas/CompanySelector.jsx';
import DashboardPanel from './modules/empresas/DashboardPanel.jsx';
import ThirdPartyModal from './components/ThirdPartyModal.jsx';
import EvidenceModal from './components/EvidenceModal.jsx';

function ContabilidadInner() {
  const [activeTab, setActiveTab] = useState('terceros');
  const [activeLeftSection, setActiveLeftSection] = useState('registro');

  // ── Datos de empresa/portafolio + dashboard (EmpresaProvider) ──
  const dashboard = useEmpresa();
  const { activePortfolio, activeCompany, handleSelectCompany, cajaViva } = dashboard;

  // ── Draft global (para los modales) ────────────────────────
  const draft = useTransactionDraft();

  // ── Acciones administrativas (⚡ Semillar / ⚠️ Reiniciar) ───
  const { handleSeedSynthetic, handleResetDatabase } = useAdminActions();

  // ── Modal de comprobante ───────────────────────────────────
  const [evidenceUrl, setEvidenceUrl] = useState(null);
  const [selectedEvidenceTx, setSelectedEvidenceTx] = useState(null);

  return (
    <div className="min-h-screen bg-brutalBg text-black font-mono p-2 flex flex-col antialiased selection:bg-brutalGreen">

      {/* ============================================================================== */}
      {/* 🏛️ BARRA DE PORTAFOLIOS — compacta, sin duplicar el título del shell */}
      {/* ============================================================================== */}
      <header className="border-2 border-black bg-white px-2 py-1 mb-2 shadow-brutal flex items-center justify-between flex-wrap gap-1">
        {/* Selector de Empresa (CompanySelector — entities de Control Tower) */}
        <CompanySelector
          activeCompanyId={activeCompany?.id}
          onSelectCompany={handleSelectCompany}
          onCompaniesLoaded={(entities) => {
            // Auto-seleccionar la primera empresa si no hay ninguna activa
            if (!activeCompany && entities.length > 0) {
              const firstEmpresa = entities.find(e => e.type === 'EMPRESA') || entities[0];
              handleSelectCompany(firstEmpresa);
            }
          }}
          style={{ flex: 1 }}
        />
        {/* Acciones rápidas + estado */}
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 border ${
            cajaViva.status === 'NOMINAL' ? 'bg-brutalGreen border-black text-black' :
            cajaViva.status === 'INSOLVENTE' ? 'bg-brutalCrimson border-black text-white animate-pulse' :
            'bg-brutalAmber border-black text-black'
          }`}>{cajaViva.status || 'CARGANDO'}</span>
          <button onClick={handleSeedSynthetic} className="px-2 py-0.5 text-[10px] font-bold uppercase bg-brutalAmber border border-black text-black hover:bg-black hover:text-white transition-all" type="button" title="Datos sintéticos">⚡ Semillar</button>
          <button onClick={handleResetDatabase} className="px-2 py-0.5 text-[10px] font-bold uppercase bg-brutalCrimson border border-black text-white hover:bg-black transition-all" type="button" title="Reiniciar BD">⚠️ Reiniciar</button>
        </div>
      </header>

      {/* Alert Banner for Financial Risk */}
      {cajaViva.alerts && cajaViva.alerts.length > 0 && (
        <div className="bg-brutalCrimson border-2 border-black text-white p-2 mb-2 shadow-brutal flex flex-col space-y-1 uppercase animate-pulse">
          <span className="font-extrabold text-sm tracking-widest flex items-center">
            🚨 ALERTA DE RIESGO FINANCIERO Y PATRIMONIAL DETECTADA 🚨
          </span>
          <div className="text-xs space-y-1 normal-case font-mono font-medium">
            {cajaViva.alerts.map((alertText, index) => (
              <p key={index}>• {alertText}</p>
            ))}
          </div>
        </div>
      )}

      {/* ============================================================================== */}
      {/* 📊 DASHBOARD PANEL COLAPSABLE */}
      {/* ============================================================================== */}
      <DashboardPanel
        cajaViva={cajaViva}
        activeCompany={activeCompany}
        activePortfolio={activePortfolio}
        onQuickAction={(action) => {
          if (action === 'registro') setActiveLeftSection('registro');
          if (action === 'tercero') { setActiveTab('terceros'); }
          if (action === 'recurso') { setActiveTab('activos'); }
          if (action === 'balance') { /* scroll to libro diario */ }
        }}
        onSelectCompany={handleSelectCompany}
        onCompaniesChanged={() => {
          // El CompanySelector se refresca solo al montar
        }}
        industryKpis={[]}
        industryData={{}}
      />

      {/* ============================================================================== */}
      {/* 💼 SPLIT SCREEN WORKSPACE */}
      {/* ============================================================================== */}
      <div className="flex flex-col gap-2 flex-grow">

        {/* ── FILA SUPERIOR ── */}
        <div className="grid grid-cols-5 gap-2 items-start">

          {/* PANEL IZQUIERDO VERTICAL (col-span-2) */}
          <div className="lg:col-span-2 col-span-5 space-y-2">

          {/* ═══ NAV SUBSECCIONES ═══ */}
          <div className="bg-white border-2 border-black p-1.5 shadow-brutal">
            <div className="flex flex-wrap gap-1">
              {[
                { id: 'registro', label: '📝 Registro', icon: '' },
                { id: 'facturacion', label: '🧾 Facturación', icon: '' },
              ].map((sec) => (
                <button
                  key={sec.id}
                  type="button"
                  onClick={() => setActiveLeftSection(sec.id)}
                  className={`px-2 py-0.5 text-[9px] font-bold uppercase border transition-all ${
                    activeLeftSection === sec.id
                      ? 'bg-black text-white border-black'
                      : 'border-gray-300 hover:border-black hover:bg-brutalNeutral'
                  }`}
                >{sec.label}</button>
              ))}
            </div>
          </div>

          {/* ═══ FACTURACIÓN (subsección — placeholder v1) ═══ */}
          {activeLeftSection === 'facturacion' && (
            <div className="bg-white border-2 border-black p-2 shadow-brutal">
              <h2 className="text-sm font-bold uppercase border-b-2 border-black pb-1 mb-2">🧾 Facturación</h2>
              <div className="space-y-2">
                <p className="text-[10px] text-gray-500 uppercase">Módulo de facturación electrónica en desarrollo.</p>
                <div className="grid grid-cols-2 gap-1">
                  <button type="button" className="border-2 border-black bg-brutalBg p-2 text-[10px] font-bold uppercase hover:bg-brutalNeutral transition-all text-left">
                    📄 Nueva Factura
                  </button>
                  <button type="button" className="border-2 border-black bg-brutalBg p-2 text-[10px] font-bold uppercase hover:bg-brutalNeutral transition-all text-left">
                    📋 Historial
                  </button>
                  <button type="button" className="border-2 border-black bg-brutalBg p-2 text-[10px] font-bold uppercase hover:bg-brutalNeutral transition-all text-left">
                    📊 Reportes
                  </button>
                  <button type="button" className="border-2 border-black bg-brutalBg p-2 text-[10px] font-bold uppercase hover:bg-brutalNeutral transition-all text-left">
                    ⚙️ Configuración
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Módulo de Voz IA — Widget Colapsable (adapter v1) */}
          {activeLeftSection === 'registro' && <VozModule />}

          {/* Formulario Manual Módulo 01 (adapter v1) */}
          {activeLeftSection === 'registro' && <RegistroModule />}

        </div>{/* fin panel izquierdo */}

          {/* PANEL DERECHO — FORM + BD POR TAB (adapter v1) */}
          <ContextPanelAdapter
            activeTab={activeTab}
            setActiveTab={setActiveTab}
          />

        </div>{/* fin fila superior */}

        {/* ── FILA INFERIOR: Libro Diario ancho completo (adapter v1) ── */}
        <DiarioModule
          onEvidenceClick={(tx) => {
            setSelectedEvidenceTx(tx);
            setEvidenceUrl(tx.evidence_file_path || "recibo_demo.png");
          }}
        />

        </div>{/* fin flex-col workspace */}

      {/* 🖼️ EVIDENCE MODAL POPUP (v1) */}
      <EvidenceModal
        evidenceUrl={evidenceUrl}
        selectedEvidenceTx={selectedEvidenceTx}
        onClose={() => {
          setEvidenceUrl(null);
          setSelectedEvidenceTx(null);
        }}
        profile={dashboard.profile}
      />

      {/* Footer */}
      <footer className="mt-8 text-center text-xs text-gray-400 uppercase tracking-widest">
        FIN-SYS OS v2.0 // NOMINAL OPERATION MODE // LOCALHOST DEPLOY
      </footer>

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
