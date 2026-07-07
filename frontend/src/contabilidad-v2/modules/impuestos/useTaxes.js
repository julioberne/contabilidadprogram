/* ============================================================
   useTaxes.js — FIN-SYS Contabilidad v2 · Phase 2
   CRUD hook for Custom Taxes / Impuestos
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../../config';

const EMPTY_FORM = { name: '', rate: '', type: 'ADDITIVE' };

export function useTaxes() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [isAdding, setIsAdding] = useState(false);

  // ── Fetch ──────────────────────────────────────────────────
  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/custom-taxes`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('[useTaxes] fetch error:', err);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Auto-fetch on mount ────────────────────────────────────
  useEffect(() => {
    fetch_();
  }, [fetch_]);

  // ── Create ─────────────────────────────────────────────────
  const create = useCallback(async () => {
    const trimmedName = form.name.trim();
    const parsedRate = parseFloat(form.rate);
    if (!trimmedName || isNaN(parsedRate)) return;
    try {
      const res = await fetch(`${API}/custom-taxes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: trimmedName,
          rate: parsedRate,
          type: form.type,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setForm({ ...EMPTY_FORM });
      setIsAdding(false);
      await fetch_();
    } catch (err) {
      console.error('[useTaxes] create error:', err);
    }
  }, [form, fetch_]);

  // ── Remove ─────────────────────────────────────────────────
  const remove = useCallback(async (id) => {
    if (!window.confirm('¿Eliminar esta tasa personalizada permanentemente?')) return;
    try {
      const res = await fetch(`${API}/custom-taxes/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetch_();
    } catch (err) {
      console.error('[useTaxes] remove error:', err);
    }
  }, [fetch_]);

  // ── Form updater ───────────────────────────────────────────
  const updateForm = useCallback((field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  return {
    items,
    loading,
    form,
    updateForm,
    isAdding,
    setIsAdding,
    fetch: fetch_,
    create,
    remove,
  };
}

export default useTaxes;
