import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import estandarTemplate from './templates/estandar.json';
import { API } from '../../config';

/* ── context ─────────────────────────────────────────────── */
const TenantContext = createContext(null);

const DEFAULT_LABELS = {
  tercero:    'Tercero',
  cxc:        'Cuenta por Cobrar',
  cxp:        'Cuenta por Pagar',
  ingreso:    'Ingreso',
  gasto:      'Gasto',
  activo:     'Recurso',
  cobro:      'Cobro',
  pago:       'Pago',
};

/* ── provider ────────────────────────────────────────────── */
export function TenantProvider({ portfolioId, industry: industryProp, children }) {
  const [template, setTemplate] = useState(estandarTemplate);

  const resolveTemplate = useCallback(async (pid, directIndustry) => {
    // Si se pasa industria directamente (desde CompanySelector), usarla
    const targetIndustry = directIndustry || null;

    if (!pid && !targetIndustry) { setTemplate(estandarTemplate); return; }

    let industry = targetIndustry;

    // Si no hay industria directa, resolver desde API
    if (!industry && pid) {
      try {
        const res = await fetch(`${API}/dashboard?portfolio_id=${pid}`);
        if (res.ok) {
          const data = await res.json();
          industry = data?.industry_type;
        }
      } catch (_) { /* network error — fall through */ }
    }

    if (industry && industry !== 'ESTANDAR') {
      try {
        const mod = await import(`./templates/${industry.toLowerCase()}.json`);
        setTemplate(mod.default);
        return;
      } catch (_) {
        /* template no existe aún — fall through to default */
        console.warn(`[TenantProvider] Template '${industry}' no encontrado, usando ESTANDAR`);
      }
    }

    setTemplate(estandarTemplate);
  }, []);

  useEffect(() => {
    resolveTemplate(portfolioId, industryProp);
  }, [portfolioId, industryProp, resolveTemplate]);

  const value = {
    template,
    labels:       template.labels        || {},
    contactTypes: template.contact_types || [],
    kpis:         template.kpis          || [],
  };

  return (
    <TenantContext.Provider value={value}>
      {children}
    </TenantContext.Provider>
  );
}

/* ── hooks ───────────────────────────────────────────────── */
export function useLabel(key) {
  const ctx = useContext(TenantContext);
  const labels = ctx?.labels || {};
  return labels[key] || DEFAULT_LABELS[key] || key;
}

export function useTenantConfig() {
  const ctx = useContext(TenantContext);
  if (!ctx) throw new Error('useTenantConfig must be used inside <TenantProvider>');
  return ctx;
}

export default TenantProvider;
