/* ============================================================
   useTags.js — FIN-SYS Contabilidad v2 · Phase 2
   CRUD hook for Tags
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../../config';

export function useTags() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({ name: '' });

  // ── Fetch ──────────────────────────────────────────────────
  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/tags`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('[useTags] fetch error:', err);
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
    const trimmed = newTagName.trim();
    if (!trimmed) return;
    try {
      const res = await fetch(`${API}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed, color: '#000000' }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setNewTagName('');
      await fetch_();
    } catch (err) {
      console.error('[useTags] create error:', err);
    }
  }, [newTagName, fetch_]);

  // ── Update ─────────────────────────────────────────────────
  const update = useCallback(async (id) => {
    try {
      const res = await fetch(`${API}/tags/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editData),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setEditingId(null);
      setEditData({ name: '' });
      await fetch_();
    } catch (err) {
      console.error('[useTags] update error:', err);
    }
  }, [editData, fetch_]);

  // ── Remove ─────────────────────────────────────────────────
  const remove = useCallback(async (id) => {
    if (!window.confirm('¿Eliminar esta etiqueta permanentemente?')) return;
    try {
      const res = await fetch(`${API}/tags/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetch_();
    } catch (err) {
      console.error('[useTags] remove error:', err);
    }
  }, [fetch_]);

  // ── Edit helpers ───────────────────────────────────────────
  const startEdit = useCallback((item) => {
    setEditingId(item.id);
    setEditData({ name: item.name || '' });
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingId(null);
    setEditData({ name: '' });
  }, []);

  return {
    items,
    loading,
    newTagName,
    setNewTagName,
    editingId,
    editData,
    setEditData,
    fetch: fetch_,
    create,
    update,
    remove,
    startEdit,
    cancelEdit,
  };
}

export default useTags;
