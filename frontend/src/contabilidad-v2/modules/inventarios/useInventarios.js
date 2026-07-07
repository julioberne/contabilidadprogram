/* ============================================================
   useInventarios.js — FIN-SYS Contabilidad v2 · Phase 2
   CRUD hook for Assets / Inventarios
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../../config';

export function useInventarios(activePortfolio) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({ name: '', purchase_value: '', custom_tag: '' });

  // ── Fetch ──────────────────────────────────────────────────
  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API}/assets?portfolio=${encodeURIComponent(activePortfolio)}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('[useInventarios] fetch error:', err);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [activePortfolio]);

  // ── Auto-fetch on mount & portfolio change ─────────────────
  useEffect(() => {
    if (activePortfolio) fetch_();
  }, [activePortfolio, fetch_]);

  // ── Update ─────────────────────────────────────────────────
  const update = useCallback(async (id) => {
    try {
      const res = await fetch(`${API}/assets/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editData.name,
          purchase_value: parseFloat(editData.purchase_value) || 0,
          custom_tag: editData.custom_tag,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setEditingId(null);
      setEditData({ name: '', purchase_value: '', custom_tag: '' });
      await fetch_();
    } catch (err) {
      console.error('[useInventarios] update error:', err);
    }
  }, [editData, fetch_]);

  // ── Remove ─────────────────────────────────────────────────
  const remove = useCallback(async (id) => {
    if (!window.confirm('¿Eliminar este activo permanentemente?')) return;
    try {
      const res = await fetch(`${API}/assets/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetch_();
    } catch (err) {
      console.error('[useInventarios] remove error:', err);
    }
  }, [fetch_]);

  // ── Edit helpers ───────────────────────────────────────────
  const startEdit = useCallback((item) => {
    setEditingId(item.id);
    setEditData({
      name: item.name || '',
      purchase_value: String(item.purchase_value ?? ''),
      custom_tag: item.custom_tag || '',
    });
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingId(null);
    setEditData({ name: '', purchase_value: '', custom_tag: '' });
  }, []);

  return {
    items,
    loading,
    editingId,
    editData,
    setEditData,
    fetch: fetch_,
    update,
    remove,
    startEdit,
    cancelEdit,
  };
}

export default useInventarios;
