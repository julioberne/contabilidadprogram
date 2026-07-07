import { useState, useEffect, useCallback } from 'react';
import { API } from '../../../config';

const DEFAULT_FORM = {
  name: '',
  identification_type: 'NIT',
  identification_number: '',
  email: '',
  phone: '',
  address: '',
};

export function useTerceros() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({});
  const [form, setForm] = useState({ ...DEFAULT_FORM });

  /* ── FETCH ─────────────────────────────────────────── */
  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/third-parties`);
      if (res.ok) {
        const data = await res.json();
        setItems(Array.isArray(data) ? data : data.data || []);
      }
    } catch (err) {
      console.error('[useTerceros] fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  /* ── CREATE ────────────────────────────────────────── */
  const create = useCallback(async () => {
    if (!form.name.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/third-parties`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name.trim(),
          identification_type: form.identification_type,
          identification_number: form.identification_number,
          email: form.email,
          phone: form.phone,
          address: form.address,
        }),
      });
      if (res.ok) {
        setForm({ ...DEFAULT_FORM });
        await fetchItems();
      }
    } catch (err) {
      console.error('[useTerceros] create error:', err);
    } finally {
      setLoading(false);
    }
  }, [form, fetchItems]);

  /* ── UPDATE ────────────────────────────────────────── */
  const update = useCallback(async (id) => {
    if (!editData.name?.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/third-parties/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editData),
      });
      if (res.ok) {
        setEditingId(null);
        setEditData({});
        await fetchItems();
      }
    } catch (err) {
      console.error('[useTerceros] update error:', err);
    } finally {
      setLoading(false);
    }
  }, [editData, fetchItems]);

  /* ── DELETE ────────────────────────────────────────── */
  const remove = useCallback(async (id) => {
    if (!window.confirm('¿Eliminar este tercero?')) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/third-parties/${id}`, { method: 'DELETE' });
      if (res.ok) await fetchItems();
    } catch (err) {
      console.error('[useTerceros] remove error:', err);
    } finally {
      setLoading(false);
    }
  }, [fetchItems]);

  /* ── EDIT HELPERS ──────────────────────────────────── */
  const startEdit = useCallback((tp) => {
    setEditingId(tp.id);
    setEditData({ ...tp });
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingId(null);
    setEditData({});
  }, []);

  /* ── FORM HELPERS ──────────────────────────────────── */
  const updateForm = useCallback((field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const resetForm = useCallback(() => {
    setForm({ ...DEFAULT_FORM });
  }, []);

  /* ── DERIVED ───────────────────────────────────────── */
  const filtered = items.filter((tp) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      tp.name.toLowerCase().includes(q) ||
      (tp.identification_number || '').includes(q)
    );
  });

  /* ── AUTO FETCH ────────────────────────────────────── */
  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  return {
    items,
    loading,
    search,
    setSearch,
    editingId,
    editData,
    setEditData,
    form,
    updateForm,
    resetForm,
    filtered,
    fetch: fetchItems,
    create,
    update,
    remove,
    startEdit,
    cancelEdit,
  };
}

export default useTerceros;
