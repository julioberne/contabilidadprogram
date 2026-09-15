import { useState, useEffect, useCallback, useRef } from 'react';
import { API } from '../../config';
// Las transacciones del Bot IA (proceso externo) deben reflejarse sin recargar
// la página. 60s + pausa con pestaña oculta: a 15s eran 480 req/hora y en
// local cada ciclo cuesta ~5s de backend (auditoría 2026-09-04).
// Plan cimientos A5 (2026-09-15): el sondeo se salta si hubo una mutación
// local en el último minuto (esa mutación ya actualizó el estado).
const REFRESH_INTERVAL_MS = 60000;
const PAGE_SIZE = 50;

const DEFAULT_CAJA_VIVA = {
  total_ingresos: 0,
  total_gastos: 0,
  balance_neto: 0,
  capital_inicial: 0,
  patrimonio: 5000000,
  status: 'NOMINAL',
  alerts: [],
  total_ingresos_cop: 0,
  total_gastos_cop: 0,
  balance_neto_cop: 0,
  patrimonio_cop: 0,
  total_ingresos_usd: 0,
  total_gastos_usd: 0,
  balance_neto_usd: 0,
  patrimonio_usd: 0,
};

function flattenCoa(nodes, result = []) {
  if (!nodes || !Array.isArray(nodes)) return result;
  for (const node of nodes) {
    result.push(node);
    if (node.children && node.children.length > 0) {
      flattenCoa(node.children, result);
    }
  }
  return result;
}

/**
 * Datos del dashboard contable.
 *
 * Plan cimientos A5 (2026-09-15): antes, CADA mutación (registrar, editar una
 * celda, adjuntar evidencia, cambiar una nota…) volvía a pedir el dashboard
 * completo + terceros (20 sitios), y el refresco tiraba las páginas cargadas
 * con "Cargar más". Ahora:
 *   - prependTransaction / patchTransaction / removeTransaction actualizan la
 *     lista localmente con la fila que devuelve el backend;
 *   - refreshBalance pide SOLO KPIs + cuentas (GET /dashboard-data/balance);
 *   - fetchAll conserva las páginas ya cargadas (limit = lo que había);
 *   - el sondeo de 60 s se salta si hubo una mutación local reciente.
 */
export function useDashboardData(activePortfolio) {
  const [portfolios, setPortfolios] = useState([]);
  const [cajaViva, setCajaViva] = useState(DEFAULT_CAJA_VIVA);
  const [transactions, setTransactions] = useState([]);
  const [totalTxCount, setTotalTxCount] = useState(0);
  const [accounts, setAccounts] = useState([]);
  const [profile, setProfile] = useState({ name: '', email: '', role: '', avatar_style: '' });
  const [coaTree, setCoaTree] = useState([]);
  const [coaFlatAccounts, setCoaFlatAccounts] = useState([]);
  const [allThirdParties, setAllThirdParties] = useState([]);
  const [loading, setLoading] = useState(true);

  const intervalRef = useRef(null);
  // Cuántas TXs hay cargadas (para que un refresco no pierda páginas)
  const txCountRef = useRef(0);
  useEffect(() => { txCountRef.current = transactions.length; }, [transactions]);
  // Última mutación local: el sondeo periódico no repite trabajo ya hecho
  const lastMutationRef = useRef(0);
  const markMutation = useCallback(() => { lastMutationRef.current = Date.now(); }, []);

  const portfolioQ = activePortfolio ? encodeURIComponent(activePortfolio) : '';

  /**
   * fetchAll(opciones)
   *   true | { silencioso: true }  → sin parpadeo de `loading`
   *   { preservarPaginas: false }  → vuelve a la primera página (default: conserva)
   */
  const fetchAll = useCallback(async (opciones = false) => {
    if (!activePortfolio) return;
    const opts = opciones === true ? { silencioso: true } : (opciones || {});
    const silencioso = opts.silencioso === true;
    const preservar = opts.preservarPaginas !== false;
    const limit = preservar ? Math.max(PAGE_SIZE, txCountRef.current) : PAGE_SIZE;
    try {
      // El refresco periódico no debe parpadear la UI: loading solo en cargas
      // iniciadas por el usuario (montaje, cambio de portafolio, reset/seed).
      if (!silencioso) setLoading(true);
      const [dashRes, tercerosRes] = await Promise.all([
        fetch(`${API}/dashboard-data?portfolio=${portfolioQ}&limit=${limit}&offset=0`),
        fetch(`${API}/third-parties`),
      ]);

      if (dashRes.ok) {
        const data = await dashRes.json();
        setPortfolios(data.portfolios || []);
        // Contrato real del backend (routers/dashboard_data.py): el objeto
        // de KPIs viaja en `balance`, no en `caja_viva`.
        setCajaViva({ ...DEFAULT_CAJA_VIVA, ...(data.balance || {}) });
        setTransactions(data.transactions || []);
        setTotalTxCount(data.total_tx_count ?? (data.transactions || []).length);
        setAccounts(data.accounts || []);
        setProfile(data.profile || { name: '', email: '', role: '', avatar_style: '' });

        // COA viaja como { status: "OK"|"EMPTY", data: [...] } | null
        const tree = (data.coa && data.coa.status === 'OK') ? data.coa.data : [];
        setCoaTree(tree);
        const flat = flattenCoa(tree);
        setCoaFlatAccounts(flat.filter((n) => !n.is_group));
      }

      if (tercerosRes.ok) {
        const terceros = await tercerosRes.json();
        setAllThirdParties(Array.isArray(terceros) ? terceros : terceros.data || []);
      }
    } catch (err) {
      console.error('[useDashboardData] fetchAll error:', err);
    } finally {
      setLoading(false);
    }
  }, [activePortfolio, portfolioQ]);

  /** KPIs + cuentas + conteo, sin la página de TXs (un viaje a la BD). */
  const refreshBalance = useCallback(async () => {
    if (!activePortfolio) return;
    markMutation();
    try {
      const res = await fetch(`${API}/dashboard-data/balance?portfolio=${portfolioQ}`);
      if (res.ok) {
        const data = await res.json();
        if (data.balance) setCajaViva((prev) => ({ ...prev, ...data.balance }));
        if (Array.isArray(data.accounts)) setAccounts(data.accounts);
        if (data.total_tx_count != null) setTotalTxCount(data.total_tx_count);
        if (Array.isArray(data.portfolios)) setPortfolios(data.portfolios);
      }
    } catch (err) {
      console.error('[useDashboardData] refreshBalance error:', err);
    }
  }, [activePortfolio, portfolioQ, markMutation]);

  const refreshTransactions = useCallback(async () => {
    if (!activePortfolio) return;
    try {
      // GET /transactions ignora limit/offset y devuelve lista cruda.
      // El único endpoint que pagina es /dashboard-data.
      const limit = Math.max(PAGE_SIZE, txCountRef.current);
      const res = await fetch(
        `${API}/dashboard-data?portfolio=${portfolioQ}&limit=${limit}&offset=0`
      );
      if (res.ok) {
        const data = await res.json();
        setTransactions(data.transactions || []);
        setTotalTxCount(data.total_tx_count ?? (data.transactions || []).length);
      }
    } catch (err) {
      console.error('[useDashboardData] refreshTransactions error:', err);
    }
  }, [activePortfolio, portfolioQ]);

  const refreshTerceros = useCallback(async () => {
    try {
      const res = await fetch(`${API}/third-parties`);
      if (res.ok) {
        const data = await res.json();
        setAllThirdParties(Array.isArray(data) ? data : data.data || []);
      }
    } catch (err) {
      console.error('[useDashboardData] refreshTerceros error:', err);
    }
  }, []);

  const loadMoreTransactions = useCallback(async (currentCount) => {
    if (!activePortfolio) return;
    try {
      // Paginación real vía /dashboard-data (GET /transactions no pagina)
      const res = await fetch(
        `${API}/dashboard-data?portfolio=${portfolioQ}&limit=${PAGE_SIZE}&offset=${currentCount}`
      );
      if (res.ok) {
        const data = await res.json();
        const newTxs = data.transactions || [];
        setTransactions((prev) => {
          const vistos = new Set(prev.map((t) => t.id));
          return [...prev, ...newTxs.filter((t) => !vistos.has(t.id))];
        });
        if (data.total_tx_count != null) {
          setTotalTxCount(data.total_tx_count);
        }
      }
    } catch (err) {
      console.error('[useDashboardData] loadMoreTransactions error:', err);
    }
  }, [activePortfolio, portfolioQ]);

  // ── Mutaciones locales (la fila viene del backend con la forma exacta de
  //    dashboard-data.transactions: obtener_transaccion en el servidor) ──────
  const prependTransaction = useCallback((tx) => {
    if (!tx || tx.id == null) return;
    markMutation();
    setTransactions((prev) => {
      if (prev.some((t) => t.id === tx.id)) return prev.map((t) => (t.id === tx.id ? tx : t));
      return [tx, ...prev];
    });
    setTotalTxCount((n) => n + 1);
  }, [markMutation]);

  const patchTransaction = useCallback((id, parcial) => {
    if (id == null || !parcial) return;
    markMutation();
    setTransactions((prev) => prev.map((t) => (t.id === id ? { ...t, ...parcial } : t)));
  }, [markMutation]);

  const removeTransaction = useCallback((id) => {
    if (id == null) return;
    markMutation();
    setTransactions((prev) => {
      const habia = prev.some((t) => t.id === id);
      if (habia) setTotalTxCount((n) => Math.max(0, n - 1));
      return prev.filter((t) => t.id !== id);
    });
  }, [markMutation]);

  useEffect(() => {
    fetchAll({ silencioso: false, preservarPaginas: false });

    if (intervalRef.current) clearInterval(intervalRef.current);
    // Con la pestaña oculta no se golpea el backend; al volver, se refresca.
    // Si hubo una mutación local hace menos de un minuto, el estado ya es
    // fresco: se salta el ciclo.
    const refrescoSilencioso = () => {
      if (document.hidden) return;
      if (Date.now() - lastMutationRef.current < REFRESH_INTERVAL_MS) return;
      fetchAll(true);
    };
    intervalRef.current = setInterval(refrescoSilencioso, REFRESH_INTERVAL_MS);
    const alVolver = () => { if (!document.hidden) fetchAll(true); };
    document.addEventListener('visibilitychange', alVolver);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      document.removeEventListener('visibilitychange', alVolver);
    };
  }, [fetchAll]);

  return {
    portfolios,
    cajaViva,
    transactions,
    totalTxCount,
    accounts,
    profile,
    coaTree,
    coaFlatAccounts,
    allThirdParties,
    setAllThirdParties,
    loading,
    refreshBalance,
    refreshTransactions,
    refreshTerceros,
    fetchAll,
    loadMoreTransactions,
    prependTransaction,
    patchTransaction,
    removeTransaction,
    markMutation,
  };
}

export default useDashboardData;
