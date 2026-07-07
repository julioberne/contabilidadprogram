/* ================================================================
   ContextPanel.jsx — Thin tab router for right-column Lego panels
   FIN-SYS Contabilidad v2 · Phase 2
   Replaces the monolith with a ~80-line router
   ================================================================ */
import React, { lazy, Suspense } from 'react';
import { useLabel } from '../engine/TenantProvider.jsx';

/* ── Direct imports (modules that exist) ─────────────────────── */
import TercerosPanel from '../modules/terceros/TercerosPanel.jsx';
import InventarioPanel from '../modules/inventarios/InventarioPanel.jsx';
import TagsPanel from '../modules/tags/TagsPanel.jsx';
import TaxPanel from '../modules/impuestos/TaxPanel.jsx';
import CuentasPanel from '../modules/cuentas/CuentasPanel.jsx';

/* ── Lazy-load module panels not yet created ─────────────────── */
const CarteraPanel = lazy(() => import('../modules/cartera/CarteraPanel.jsx').catch(() => ({ default: () => <PhasePlaceholder label="Cartera" /> })));

/* ── Placeholder for modules not yet built ───────────────────── */
function PhasePlaceholder({ label }) {
  return (
    <div style={{
      padding: 24, textAlign: 'center',
      fontFamily: "'IBM Plex Mono', monospace",
      fontSize: 10, color: '#999', textTransform: 'uppercase',
    }}>
      ▓ Módulo "{label}" — Fase 2 pendiente
    </div>
  );
}

/* ── Loading fallback ────────────────────────────────────────── */
function LoadingFallback() {
  return (
    <div style={{
      padding: 20, textAlign: 'center',
      fontFamily: "'IBM Plex Mono', monospace",
      fontSize: 10, color: '#999', textTransform: 'uppercase',
    }}>
      ▓ Cargando módulo…
    </div>
  );
}

/* ── Panel map ───────────────────────────────────────────────── */
const PANEL_MAP = {
  terceros:   (props) => <TercerosPanel {...props} />,
  cartera:    (props) => <CarteraPanel {...props} />,
  activos:    (props) => <InventarioPanel {...props} />,
  etiquetas:  (props) => <TagsPanel {...props} />,
  impuestos:  (props) => <TaxPanel {...props} />,
  cuentas:    (props) => <CuentasPanel activePortfolio={props.activePortfolio} />,
};

/* ── Main Component ──────────────────────────────────────────── */
export function ContextPanel({ activeTab, setActiveTab, activePortfolio, allThirdParties }) {
  const lblTercero = useLabel('tercero');

  const PANEL_TABS = [
    { key: 'terceros',  icon: '👤', label: lblTercero + 's' },
    { key: 'cartera',   icon: '📄', label: 'Cartera' },
    { key: 'activos',   icon: '📦', label: 'Recursos' },
    { key: 'etiquetas', icon: '🏷️', label: 'Tags' },
    { key: 'impuestos', icon: '📈', label: 'Tasas' },
    { key: 'cuentas',   icon: '💳', label: 'Cuentas' },
    { key: 'usuario',   icon: '⚙',  label: 'Config' },
  ];

  const renderContent = PANEL_MAP[activeTab];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', fontFamily: "'IBM Plex Mono', monospace",
    }}>
      {/* ── TAB BAR ──────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        borderBottom: '2px solid #000',
        background: '#f5f5f0',
        overflowX: 'auto',
        flexShrink: 0,
      }}>
        {PANEL_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '6px 8px',
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 9,
              fontWeight: 700,
              textTransform: 'uppercase',
              whiteSpace: 'nowrap',
              cursor: 'pointer',
              border: 'none',
              borderRight: '1px solid #000',
              borderRadius: 0,
              background: activeTab === tab.key ? '#000' : 'transparent',
              color: activeTab === tab.key ? '#fff' : '#999',
              transition: 'all 0.15s',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* ── CONTENT AREA ─────────────────────────────────── */}
      <div style={{ flex: 1, padding: 12, overflow: 'auto' }}>
        {activeTab === 'usuario' ? (
          <div style={{
            padding: 24, textAlign: 'center',
            fontSize: 10, color: '#999', textTransform: 'uppercase',
          }}>
            ▓ Configuración de Usuario — Fase 3
          </div>
        ) : renderContent ? (
          <Suspense fallback={<LoadingFallback />}>
            {renderContent({ activePortfolio, allThirdParties })}
          </Suspense>
        ) : (
          <PhasePlaceholder label={activeTab} />
        )}
      </div>
    </div>
  );
}

export default ContextPanel;
