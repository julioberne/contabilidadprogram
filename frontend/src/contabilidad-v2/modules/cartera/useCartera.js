import { useState, useEffect, useCallback, useMemo } from 'react';
import { API } from '../../../config';

function today() {
  return new Date().toISOString().split('T')[0];
}

/* ── Sort functions (match original CarteraTab exactly) ───── */
const SORT_FNS = {
  'urgente': (a, b) => {
    const sp = { VENCIDO: 0, PENDIENTE: 1, PAGADO: 2 };
    const sa = sp[a.status] ?? 1;
    const sb = sp[b.status] ?? 1;
    if (sa !== sb) return sa - sb;
    return new Date(a.due_date || '2099-01-01') - new Date(b.due_date || '2099-01-01');
  },
  'monto-desc': (a, b) => (b.original_amount || 0) - (a.original_amount || 0),
  'monto-asc': (a, b) => (a.original_amount || 0) - (b.original_amount || 0),
  'reciente': (a, b) => new Date(b.start_date || b.created_at || 0) - new Date(a.start_date || a.created_at || 0),
  'vence-prox': (a, b) => new Date(a.due_date || '2099-01-01') - new Date(b.due_date || '2099-01-01'),
  'progreso': (a, b) => {
    const pa = a.original_amount ? ((a.original_amount - (a.remaining_balance || 0)) / a.original_amount) : 0;
    const pb = b.original_amount ? ((b.original_amount - (b.remaining_balance || 0)) / b.original_amount) : 0;
    return pb - pa;
  },
};

export function useCartera() {
  const [items, setItems] = useState([]);
  const [kpi, setKpi] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [payments, setPayments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [subTab, setSubTab] = useState('TODAS');
  const [sortBy, setSortBy] = useState('urgente');
  const [abonoForm, setAbonoForm] = useState({ amount: '', date: today(), note: '', open: false });

  /* ── FETCH ITEMS ───────────────────────────────────── */
  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/cartera`);
      if (res.ok) {
        const data = await res.json();
        setItems(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error('[useCartera] fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  /* ── FETCH KPI ─────────────────────────────────────── */
  const fetchKpi = useCallback(async () => {
    try {
      const res = await fetch(`${API}/cartera/summary`);
      if (res.ok) setKpi(await res.json());
    } catch (err) {
      console.error('[useCartera] fetchKpi error:', err);
    }
  }, []);

  /* ── FETCH ALERTS ──────────────────────────────────── */
  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${API}/cartera/alerts`);
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.alerts || []);
      }
    } catch (err) {
      console.error('[useCartera] fetchAlerts error:', err);
    }
  }, []);

  /* ── FETCH PAYMENTS ────────────────────────────────── */
  const fetchPayments = useCallback(async (ledgerId) => {
    try {
      const res = await fetch(`${API}/cartera/${ledgerId}/payments`);
      if (res.ok) setPayments(await res.json());
    } catch (err) {
      console.error('[useCartera] fetchPayments error:', err);
    }
  }, []);

  /* ── FETCH ALL ─────────────────────────────────────── */
  const fetchAll = useCallback(() => {
    fetchItems();
    fetchKpi();
    fetchAlerts();
  }, [fetchItems, fetchKpi, fetchAlerts]);

  /* ── SELECT ENTRY (toggle) ─────────────────────────── */
  const selectEntry = useCallback(async (entry) => {
    if (selectedId === entry.id) {
      setSelectedId(null);
      setPayments([]);
      setAbonoForm({ amount: '', date: today(), note: '', open: false });
      return;
    }
    setSelectedId(entry.id);
    setAbonoForm({ amount: '', date: today(), note: '', open: false });
    await fetchPayments(entry.id);
  }, [selectedId, fetchPayments]);

  /* ── REGISTER ABONO ────────────────────────────────── */
  const registerAbono = useCallback(async (ledgerId) => {
    if (!abonoForm.amount || parseFloat(abonoForm.amount) <= 0) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/cartera/${ledgerId}/payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: parseFloat(abonoForm.amount),
          payment_date: abonoForm.date,
          note: abonoForm.note,
        }),
      });
      if (res.ok) {
        setAbonoForm({ amount: '', date: today(), note: '', open: false });
        await fetchItems();
        await fetchPayments(ledgerId);
        fetchKpi();
        fetchAlerts();
      }
    } catch (err) {
      console.error('[useCartera] registerAbono error:', err);
    } finally {
      setLoading(false);
    }
  }, [abonoForm, fetchItems, fetchPayments, fetchKpi, fetchAlerts]);

  /* ── DELETE ENTRY ──────────────────────────────────── */
  const deleteEntry = useCallback(async (ledgerId) => {
    if (!window.confirm('¿Eliminar esta cuenta de cartera?')) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/cartera/${ledgerId}`, { method: 'DELETE' });
      if (res.ok) {
        if (selectedId === ledgerId) {
          setSelectedId(null);
          setPayments([]);
        }
        fetchAll();
      }
    } catch (err) {
      console.error('[useCartera] deleteEntry error:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedId, fetchAll]);

  /* ── UPDATE STATUS ─────────────────────────────────── */
  const updateStatus = useCallback(async (ledgerId, status) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/cartera/${ledgerId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (res.ok) fetchAll();
    } catch (err) {
      console.error('[useCartera] updateStatus error:', err);
    } finally {
      setLoading(false);
    }
  }, [fetchAll]);

  /* ── DERIVED: filtered + sorted ────────────────────── */
  const filtered = useMemo(() => {
    const byType = items.filter((c) => {
      if (subTab === 'CXC') return c.type === 'CXC';
      if (subTab === 'CXP') return c.type === 'CXP';
      return true;
    });
    return [...byType].sort(SORT_FNS[sortBy] || SORT_FNS['urgente']);
  }, [items, subTab, sortBy]);

  const selectedEntry = useMemo(() => items.find((i) => i.id === selectedId) || null, [items, selectedId]);
  const cxcCount = useMemo(() => items.filter((c) => c.type === 'CXC').length, [items]);
  const cxpCount = useMemo(() => items.filter((c) => c.type === 'CXP').length, [items]);

  /* ── AUTO FETCH ────────────────────────────────────── */
  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  return {
    items,
    kpi,
    alerts,
    payments,
    selectedId,
    selectedEntry,
    loading,
    subTab,
    setSubTab,
    sortBy,
    setSortBy,
    abonoForm,
    setAbonoForm,
    filtered,
    cxcCount,
    cxpCount,
    fetchAll,
    fetch: fetchItems,
    selectEntry,
    registerAbono,
    deleteEntry,
    updateStatus,
  };
}

export default useCartera;
