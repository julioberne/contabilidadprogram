/* ============================================================
   EmpresaProvider.jsx — Contexto de empresa/portafolio + datos
   del dashboard.
   Centraliza el estado que App.jsx (v1) manejaba localmente:
   - activePortfolio (string legacy, clave de casi todos los queries)
   - activeCompany (entity de Control Tower)
   - bridge entity → portfolio (semántica exacta de App.jsx:301-313)
   - datos consolidados vía useDashboardData (auto-refresh 30s)
   ============================================================ */
import { createContext, useContext, useState, useCallback } from 'react';
import { useDashboardData } from '../hooks/useDashboardData.js';

const EmpresaContext = createContext(null);

/* Deep-linking por empresa (2026-09-06, pedido de Andrés): la empresa activa
   vive en la URL — /contabilidad/<id>-<slug> — así el F5 no la pierde, los
   enlaces se comparten y atrás/adelante navega entre empresas. El id manda
   (único e inmutable); el slug es solo legibilidad. */
export const slugEmpresa = (name) => String(name || '')
  .normalize('NFD').replace(/[̀-ͯ]/g, '')   // sin tildes
  .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
  .slice(0, 40);

export const empresaIdDesdeURL = () => {
  const m = window.location.pathname.match(/^\/contabilidad\/(\d+)(?:-|$)/);
  return m ? Number(m[1]) : null;
};

export function EmpresaProvider({ children }) {
  const [activePortfolio, setActivePortfolio] = useState('Negocio A');
  const [activeCompany, setActiveCompany] = useState(null);

  // Hook maestro: reemplaza el fetchData() de App.jsx
  const dashboard = useDashboardData(activePortfolio);

  // --- Selección de Empresa desde CompanySelector (bridge entity → portfolio) ---
  // Port verbatim de App.jsx handleSelectCompany
  const handleSelectCompany = useCallback((entity) => {
    setActiveCompany(entity);
    // Sincronizar la URL con la empresa activa (pushState: atrás/adelante
    // recorre empresas). Solo dentro del módulo contabilidad.
    if (entity?.id && window.location.pathname.startsWith('/contabilidad')) {
      const destino = `/contabilidad/${entity.id}-${slugEmpresa(entity.name)}`;
      if (window.location.pathname !== destino) {
        window.history.pushState({ view: 'contabilidad', empresaId: entity.id }, '',
                                 destino + window.location.search);
      }
    }
    // Bridge: buscar el portfolio asociado a esta entity para mantener compatibilidad
    if (entity.portfolio_id) {
      const matchedPort = dashboard.portfolios.find(p => p.id === entity.portfolio_id);
      if (matchedPort) {
        setActivePortfolio(matchedPort.name);
        return;
      }
    }
    // Si no hay portfolio_id, mantener el portfolio actual (no pisar con entity.name)
    // El usuario puede cambiar portfolio manualmente desde el DashboardPanel
  }, [dashboard.portfolios]);

  const value = {
    activePortfolio, setActivePortfolio,
    activeCompany, setActiveCompany,
    handleSelectCompany,
    ...dashboard,
  };

  return (
    <EmpresaContext.Provider value={value}>
      {children}
    </EmpresaContext.Provider>
  );
}

export function useEmpresa() {
  const ctx = useContext(EmpresaContext);
  if (!ctx) {
    throw new Error('useEmpresa must be used within an EmpresaProvider');
  }
  return ctx;
}

export default EmpresaProvider;
