/* ============================================================
   IndustryWidgets.jsx — Cargador de widgets por industria
   Se monta DEBAJO del formulario de registro en App.jsx.
   Carga su propio template dinámicamente según activeCompany.industry.
   Renderiza los widgets correspondientes con React.lazy.
   Si no hay industria o es ESTANDAR, no renderiza nada.
   ============================================================ */
import React, { Suspense, useMemo, useState, useEffect } from 'react';

/* ── Registro de widgets disponibles ─────────────────────── */
/* Cada key del mapa corresponde al campo "component" del template JSON */
const WIDGET_REGISTRY = {
  RecaudosWidget:   React.lazy(() => import('./widgets/RecaudosWidget')),
  PensionesWidget:  React.lazy(() => import('./widgets/PensionesWidget')),
  UniformesWidget:  React.lazy(() => import('./widgets/UniformesWidget')),
  // Agregar nuevos widgets aquí al crear industrias nuevas:
  // OcupacionWidget: React.lazy(() => import('./widgets/OcupacionWidget')),
};

/* ── Loader brutalista ───────────────────────────────────── */
function WidgetLoader() {
  return (
    <div style={{
      padding: '12px 16px',
      border: '2px solid #333',
      background: '#111',
      color: '#00ff41',
      fontFamily: '"IBM Plex Mono", monospace',
      fontSize: 10,
      letterSpacing: 2,
      textTransform: 'uppercase',
      textAlign: 'center',
      animation: 'pulse 1.5s infinite',
    }}>
      ▓▓▓ CARGANDO WIDGET... ▓▓▓
    </div>
  );
}

/* ── Componente principal ────────────────────────────────── */
export default function IndustryWidgets({
  activeCompany = null,  // Entity activa (con id, name, industry, portfolio_id)
  activePortfolio = '',  // Nombre del portfolio activo (para queries legacy)
  onTransactionCreated,  // Callback cuando un widget crea una transacción
}) {
  const [template, setTemplate] = useState(null);

  // Cargar template dinámicamente según la industria de la empresa activa
  useEffect(() => {
    const industry = activeCompany?.industry;
    if (!industry || industry === 'ESTANDAR') {
      setTemplate(null);
      return;
    }
    // Importación dinámica del JSON de templates
    import(`../../engine/templates/${industry.toLowerCase()}.json`)
      .then(mod => setTemplate(mod.default))
      .catch(() => {
        console.warn(`[IndustryWidgets] Template '${industry}' no encontrado`);
        setTemplate(null);
      });
  }, [activeCompany?.industry]);

  const widgets = useMemo(() => template?.widgets || [], [template]);

  if (!template || widgets.length === 0) {
    return null;
  }

  const industryName = template.name || template.id;
  const industryIcon = template.icon || '🏭';

  return (
    <div style={{
      marginTop: 8,
      border: '2px solid #1a1a2e',
      background: '#0a0a14',
      fontFamily: '"IBM Plex Mono", monospace',
    }}>
      {/* Header de industria */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 10px',
        borderBottom: '1px solid #1a1a2e',
        background: '#111122',
      }}>
        <span style={{ fontSize: 14 }}>{industryIcon}</span>
        <span style={{
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: 2,
          color: '#00ff41',
          textTransform: 'uppercase',
        }}>
          OPERACIÓN: {industryName}
        </span>
        <span style={{ flex: 1 }} />
        <span style={{
          fontSize: 8,
          color: '#555',
          letterSpacing: 1,
        }}>
          {widgets.length} WIDGET{widgets.length > 1 ? 'S' : ''}
        </span>
      </div>

      {/* Grid de widgets */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: 0,
      }}>
        {widgets.map(widgetDef => {
          const WidgetComponent = WIDGET_REGISTRY[widgetDef.component];
          if (!WidgetComponent) {
            return (
              <div
                key={widgetDef.id}
                style={{
                  padding: 10,
                  borderBottom: '1px solid #1a1a2e',
                  borderRight: '1px solid #1a1a2e',
                  color: '#555',
                  fontSize: 9,
                }}
              >
                ⚠️ Widget "{widgetDef.component}" no registrado
              </div>
            );
          }

          return (
            <div
              key={widgetDef.id}
              style={{
                borderBottom: '1px solid #1a1a2e',
                borderRight: '1px solid #1a1a2e',
                minHeight: 100,
              }}
            >
              <Suspense fallback={<WidgetLoader />}>
                <WidgetComponent
                  config={widgetDef}
                  template={template}
                  activeCompany={activeCompany}
                  activePortfolio={activePortfolio}
                  onTransactionCreated={onTransactionCreated}
                />
              </Suspense>
            </div>
          );
        })}
      </div>
    </div>
  );
}
