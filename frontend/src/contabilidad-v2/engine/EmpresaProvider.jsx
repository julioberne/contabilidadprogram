/* ============================================================
   EmpresaProvider.jsx — Contexto de empresa/portafolio + datos
   del dashboard.
   Centraliza el estado que App.jsx (v1) manejaba localmente:
   - activePortfolio (string legacy, clave de casi todos los queries)
   - activeCompany (entity de Control Tower)
   - bridge entity → portfolio (semántica exacta de App.jsx:301-313)
   - datos consolidados vía useDashboardData (auto-refresh 30s)
   ============================================================ */
import { createContext, useContext, useState, useCallback, useRef } from 'react';
import { API } from '../../config';
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

  // Guarda anti-carrera: si el usuario cambia de empresa mientras el
  // ensure-portfolio de la anterior sigue en vuelo, esa respuesta tardía
  // no debe pisar el portafolio de la selección nueva.
  const seleccionRef = useRef(0);

  // --- Selección de Empresa desde CompanySelector (bridge entity → portfolio) ---
  // Port verbatim de App.jsx handleSelectCompany
  const handleSelectCompany = useCallback((entity) => {
    const marca = ++seleccionRef.current;
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
    // Sin presupuesto propio (o lista de portafolios desactualizada): el
    // backend lo garantiza — lo crea con el nombre de la empresa si no existe
    // (2026-09-07, pedido de Andrés). Así lo que se registre estando en
    // /contabilidad/<id>-<slug> queda atribuido a ESA empresa en el
    // consolidado, no al portafolio que estuviera activo antes.
    if (entity?.id) {
      fetch(`${API}/org/entities/${entity.id}/ensure-portfolio`, { method: 'POST' })
        .then(r => (r.ok ? r.json() : null))
        .then(d => {
          if (d?.portfolio_name && seleccionRef.current === marca) {
            setActivePortfolio(d.portfolio_name);
          }
        })
        .catch(() => {});   // sin red: se queda el portafolio anterior (como antes)
    }
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
