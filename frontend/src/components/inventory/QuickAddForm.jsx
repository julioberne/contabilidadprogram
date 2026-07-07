// QuickAddForm.jsx — Extracted from InventoryPanel.jsx
import React, { useState } from 'react';
import { COLORS, CATEGORIAS, UNIDADES, API_BASE_URL } from './constants';
import { S } from './styles';

// ════════════════════════════════════════════════════════════
// COMPONENTE: FORMULARIO RÁPIDO DE AGREGAR ITEM
// ════════════════════════════════════════════════════════════
export default function QuickAddForm({ activePortfolio, onCreated }) {
  const [form, setForm] = useState({
    name: '',
    sku: '',
    category: 'General',
    unit: 'unidad',
    cost_price: '',
    sell_price: '',
    current_stock: '',
    min_stock: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const update = (field, value) => setForm((p) => ({ ...p, [field]: value }));

  const handleSubmit = async () => {
    if (!form.name.trim()) return alert('El nombre es obligatorio');
    setSubmitting(true);
    try {
      const body = {
        portfolio_name: activePortfolio,
        name: form.name.trim(),
        sku: form.sku.trim() || null,
        category: form.category,
        unit: form.unit,
        cost_price: form.cost_price ? parseFloat(form.cost_price) : 0,
        sell_price: form.sell_price ? parseFloat(form.sell_price) : 0,
        current_stock: form.current_stock ? parseInt(form.current_stock, 10) : 0,
        min_stock: form.min_stock ? parseInt(form.min_stock, 10) : 0,
      };
      const res = await fetch(`${API_BASE_URL}/inventory/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Error ${res.status}`);
      }
      // Reset y notificar
      setForm({ name: '', sku: '', category: 'General', unit: 'unidad', cost_price: '', sell_price: '', current_stock: '', min_stock: '' });
      if (onCreated) onCreated();
    } catch (e) {
      alert(e.message);
    }
    setSubmitting(false);
  };

  return (
    <div style={{
      background: COLORS.white,
      borderBottom: `2px solid ${COLORS.black}`,
      padding: '14px 16px',
    }}>
      <div style={{ ...S.label, fontSize: 10, marginBottom: 10, color: COLORS.black }}>
        ▸ NUEVO ITEM DE INVENTARIO
      </div>

      {/* Fila 1: Nombre + SKU */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 8, marginBottom: 8 }}>
        <div>
          <div style={S.label}>NOMBRE *</div>
          <input
            type="text"
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            placeholder="Nombre del producto"
            style={S.input}
          />
        </div>
        <div>
          <div style={S.label}>SKU</div>
          <input
            type="text"
            value={form.sku}
            onChange={(e) => update('sku', e.target.value)}
            placeholder="INV-001"
            style={S.input}
          />
        </div>
      </div>

      {/* Fila 2: Categoría + Unidad */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
        <div>
          <div style={S.label}>CATEGORÍA</div>
          <select value={form.category} onChange={(e) => update('category', e.target.value)} style={S.select}>
            {CATEGORIAS.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <div style={S.label}>UNIDAD</div>
          <select value={form.unit} onChange={(e) => update('unit', e.target.value)} style={S.select}>
            {UNIDADES.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
      </div>

      {/* Fila 3: Precios */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
        <div>
          <div style={S.label}>PRECIO COSTO</div>
          <input
            type="number"
            value={form.cost_price}
            onChange={(e) => update('cost_price', e.target.value)}
            placeholder="0"
            style={S.input}
          />
        </div>
        <div>
          <div style={S.label}>PRECIO VENTA</div>
          <input
            type="number"
            value={form.sell_price}
            onChange={(e) => update('sell_price', e.target.value)}
            placeholder="0"
            style={S.input}
          />
        </div>
      </div>

      {/* Fila 4: Stock */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
        <div>
          <div style={S.label}>STOCK INICIAL</div>
          <input
            type="number"
            value={form.current_stock}
            onChange={(e) => update('current_stock', e.target.value)}
            placeholder="0"
            style={S.input}
          />
        </div>
        <div>
          <div style={S.label}>STOCK MÍNIMO</div>
          <input
            type="number"
            value={form.min_stock}
            onChange={(e) => update('min_stock', e.target.value)}
            placeholder="0"
            style={S.input}
          />
        </div>
      </div>

      {/* Botón submit */}
      <button
        onClick={handleSubmit}
        disabled={submitting}
        style={{
          ...S.btnPrimary,
          width: '100%',
          opacity: submitting ? 0.5 : 1,
          background: COLORS.greenSoft,
          color: COLORS.black,
        }}
        onMouseEnter={(e) => { if (!submitting) { e.target.style.background = COLORS.black; e.target.style.color = COLORS.white; } }}
        onMouseLeave={(e) => { e.target.style.background = COLORS.greenSoft; e.target.style.color = COLORS.black; }}
      >
        {submitting ? 'GUARDANDO...' : '▪ GUARDAR ITEM'}
      </button>
    </div>
  );
}
