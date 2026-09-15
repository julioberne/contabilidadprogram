/* ============================================================
   ContadoresApp.jsx — Módulo 12: Contadores (2026-09-15).
   Gate por rol (contador/owner/admin; el backend lo exige con
   require_contador) + selector de portafolio + pestañas:
   Bandeja · Diario · Plan de cuentas · Reglas · Reportes · Periodos.
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { api } from './useContadoresApi.js';
import BandejaTab from './tabs/BandejaTab.jsx';
import DiarioTab from './tabs/DiarioTab.jsx';
import PeriodosTab from './tabs/PeriodosTab.jsx';
import PortfolioSelect from './components/PortfolioSelect.jsx';

const TABS = [
  ['bandeja', 'BANDEJA'], ['diario', 'DIARIO'], ['coa', 'PLAN DE CUENTAS'],
  ['reglas', 'REGLAS'], ['reportes', 'REPORTES'], ['periodos', 'PERIODOS'],
];

function flatten(nodes, out = []) {
  for (const n of nodes || []) { out.push(n); if (n.children?.length) flatten(n.children, out); }
  return out;
}

export default function ContadoresApp({ user }) {
  const hubRole = (user?.hubRole || user?.raw?.user?.role || 'member').toLowerCase();
  const esAdmin = user?.role === 'ADMIN' || !!user?.raw?.user?.is_superuser;
  const puede = esAdmin || hubRole === 'contador';

  const [tab, setTab] = useState('bandeja');
  const [portfolios, setPortfolios] = useState([]);
  const [portfolioId, setPortfolioId] = useState(null);
  const [cuentas, setCuentas] = useState([]);
  const [resumen, setResumen] = useState({ por_estado: {}, sin_portafolio: 0 });
  const [error, setError] = useState('');

  const cargarResumen = useCallback(async () => {
    try { setResumen(await api.get(`/contadores/resumen${portfolioId != null ? `?portfolio_id=${portfolioId}` : ''}`)); }
    catch { /* silencioso */ }
  }, [portfolioId]);

  useEffect(() => {
    if (!puede) return;
    api.get('/portfolios').then((p) => setPortfolios(Array.isArray(p) ? p : [])).catch(() => {});
  }, [puede]);

  useEffect(() => { if (puede) cargarResumen(); }, [puede, cargarResumen]);

  // Plan de cuentas del portafolio (para el editor de líneas). Sin portafolio
  // se usa el primero (mismo criterio que el dashboard).
  useEffect(() => {
    if (!puede) return;
    const p = (portfolios || []).find((x) => x.id === portfolioId) || portfolios[0];
    if (!p) return;
    api.get(`/coa?portfolio=${encodeURIComponent(p.name)}`)
      .then((d) => setCuentas(flatten(d?.data || []).filter((c) => !c.is_group).map((c) => ({ code: c.code, name: c.name }))))
      .catch((e) => setError(e.message));
  }, [puede, portfolioId, portfolios]);

  if (!puede) {
    return (
      <div className="min-h-screen bg-brutalBg text-black font-mono p-4">
        <div className="bg-white border-2 border-black shadow-brutal p-3 max-w-lg">
          <div className="font-bold">⊟ CONTADORES — acceso restringido</div>
          <div className="text-[11px] mt-1">Este módulo es para el rol <b>contador</b> (o administradores). Tu rol actual: <b>{hubRole}</b>. Pide a un administrador que te asigne el rol en Usuarios y Roles.</div>
        </div>
      </div>
    );
  }

  const pe = resumen.por_estado || {};
  const btn = 'border-2 border-black px-2 py-0.5 text-[10px] font-bold';
  return (
    <div className="min-h-screen bg-brutalBg text-black font-mono p-2 space-y-2 antialiased">
      <div className="bg-white border-2 border-black shadow-brutal p-2 flex flex-wrap items-center gap-2">
        <span className="font-bold text-[13px]">⊟ CONTADORES</span>
        <PortfolioSelect portfolios={portfolios} value={portfolioId} onChange={setPortfolioId} />
        <span className="text-[10px]">
          <b className="bg-brutalAmber border border-black px-1">{pe.BORRADOR || 0} borrador</b>{' '}
          <span className="border border-black px-1">{pe.CONTABILIZADO || 0} contab.</span>{' '}
          <span className="border border-black px-1">{pe.ANULADO || 0} anul.</span>{' '}
          <span className="border border-black px-1">{pe.RECHAZADO || 0} rech.</span>
          {resumen.sin_portafolio ? <span className="ml-1 text-gray-600">· {resumen.sin_portafolio} sin portafolio</span> : null}
        </span>
        <span className="ml-auto text-[10px]">{user?.name} · <b>{hubRole}</b></span>
      </div>
      <div className="flex flex-wrap gap-1">
        {TABS.map(([k, l]) => (
          <button key={k} className={`${btn} ${tab === k ? 'bg-black text-white' : 'bg-white hover:bg-brutalNeutral'}`} onClick={() => setTab(k)}>{l}</button>
        ))}
      </div>
      {error && <div className="bg-brutalCrimson text-white border-2 border-black p-1 text-[10px]">{error}</div>}

      {tab === 'bandeja' && <BandejaTab portfolioId={portfolioId} cuentas={cuentas} onCambio={cargarResumen} />}
      {tab === 'diario' && <DiarioTab portfolioId={portfolioId} portfolios={portfolios} cuentas={cuentas} onCambio={cargarResumen} />}
      {tab === 'periodos' && <PeriodosTab portfolioId={portfolioId} portfolios={portfolios} esAdmin={esAdmin} onCambio={cargarResumen} />}
      {(tab === 'coa' || tab === 'reglas' || tab === 'reportes') && (
        <div className="bg-white border-2 border-black shadow-brutal p-3 text-[11px]">
          Esta pestaña llega en la siguiente fase del módulo (plan B3/B4). El backend de asientos y periodos ya está activo.
        </div>
      )}
    </div>
  );
}
