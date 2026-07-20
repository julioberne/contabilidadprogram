import { useState, useEffect, useCallback, useRef } from 'react';
import { API } from '../../config';
const REFRESH_INTERVAL_MS = 30000;

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

  const fetchAll = useCallback(async () => {
    if (!activePortfolio) return;
    try {
      setLoading(true);
      const [dashRes, tercerosRes] = await Promise.all([
        fetch(`${API}/dashboard-data?portfolio=${activePortfolio}`),
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
  }, [activePortfolio]);

  const refreshBalance = useCallback(async () => {
    if (!activePortfolio) return;
    try {
      const res = await fetch(`${API}/portfolios/balance?portfolio=${activePortfolio}`);
      if (res.ok) {
        const data = await res.json();
        setCajaViva((prev) => ({ ...prev, ...data }));
      }
    } catch (err) {
      console.error('[useDashboardData] refreshBalance error:', err);
    }
  }, [activePortfolio]);

  const refreshTransactions = useCallback(async () => {
    if (!activePortfolio) return;
    try {
      // GET /transactions ignora limit/offset y devuelve lista cruda.
      // El único endpoint que pagina es /dashboard-data.
      const res = await fetch(
        `${API}/dashboard-data?portfolio=${encodeURIComponent(activePortfolio)}&limit=50&offset=0`
      );
      if (res.ok) {
        const data = await res.json();
        setTransactions(data.transactions || []);
        setTotalTxCount(data.total_tx_count ?? (data.transactions || []).length);
      }
    } catch (err) {
      console.error('[useDashboardData] refreshTransactions error:', err);
    }
  }, [activePortfolio]);

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
        `${API}/dashboard-data?portfolio=${encodeURIComponent(activePortfolio)}&limit=50&offset=${currentCount}`
      );
      if (res.ok) {
        const data = await res.json();
        const newTxs = data.transactions || [];
        setTransactions((prev) => [...prev, ...newTxs]);
        if (data.total_tx_count != null) {
          setTotalTxCount(data.total_tx_count);
        }
      }
    } catch (err) {
      console.error('[useDashboardData] loadMoreTransactions error:', err);
    }
  }, [activePortfolio]);

  useEffect(() => {
    fetchAll();

    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(fetchAll, REFRESH_INTERVAL_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
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
  };
}

export default useDashboardData;
