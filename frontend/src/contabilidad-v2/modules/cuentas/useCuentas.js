/* ================================================================
   useCuentas.js — Bank Accounts CRUD hook
   FIN-SYS Contabilidad v2 · Módulo Cuentas
   ================================================================ */
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../../config';

const EMPTY_FORM = {
  name: '',
  type: 'Ahorros',
  currency: 'COP',
  initial_balance: '',
};

export function useCuentas(activePortfolio) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({});

  /* ── fetch ──────────────────────────────────────────────── */
  const fetchAccounts = useCallback(async () => {
    if (!activePortfolio) return;
    try {
      setLoading(true);
      const res = await fetch(
        `${API}/user-accounts?portfolio=${encodeURIComponent(activePortfolio)}`
      );
      if (res.ok) {
        const data = await res.json();
        setItems(Array.isArray(data) ? data : data.accounts || data.data || []);
      }
    } catch (err) {
      console.error('[useCuentas] fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [activePortfolio]);

  /* ── create ─────────────────────────────────────────────── */
  const create = useCallback(async () => {
    if (!form.name.trim()) return;
    try {
      const res = await fetch(`${API}/user-accounts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name.trim(),
          type: form.type,
          currency: form.currency,
          initial_balance: parseFloat(form.initial_balance || 0),
          portfolio: activePortfolio,
        }),
      });
      if (res.ok) {
        setForm({ ...EMPTY_FORM });
        await fetchAccounts();
      }
    } catch (err) {
      console.error('[useCuentas] create error:', err);
    }
  }, [form, activePortfolio, fetchAccounts]);

  /* ── update ─────────────────────────────────────────────── */
  const update = useCallback(async (id) => {
    try {
      const res = await fetch(`${API}/user-accounts/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editData.name,
          type: editData.type,
          current_balance: parseFloat(editData.current_balance || 0),
        }),
      });
      if (res.ok) {
        setEditingId(null);
        setEditData({});
        await fetchAccounts();
      }
    } catch (err) {
      console.error('[useCuentas] update error:', err);
    }
  }, [editData, fetchAccounts]);

  /* ── remove ─────────────────────────────────────────────── */
  const remove = useCallback(async (id, name) => {
    if (!window.confirm(`¿Eliminar la cuenta '${name}'?`)) return;
    try {
      const res = await fetch(`${API}/user-accounts/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        await fetchAccounts();
      }
    } catch (err) {
      console.error('[useCuentas] remove error:', err);
    }
  }, [fetchAccounts]);

  /* ── inline edit helpers ────────────────────────────────── */
  const startEdit = useCallback((account) => {
    setEditingId(account.id);
    setEditData({
      name: account.name || '',
      type: account.type || 'Ahorros',
      current_balance: String(account.current_balance ?? account.initial_balance ?? 0),
    });
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingId(null);
    setEditData({});
  }, []);

  /* ── form helpers ───────────────────────────────────────── */
  const updateForm = useCallback((field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const resetForm = useCallback(() => {
    setForm({ ...EMPTY_FORM });
  }, []);

  /* ── auto-fetch on mount / portfolio change ─────────────── */
  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  return {
    items,
    loading,
    form,
    updateForm,
    resetForm,
    editingId,
    editData,
    setEditData,
    fetch: fetchAccounts,
    create,
    update,
    remove,
    startEdit,
    cancelEdit,
  };
}

export default useCuentas;
