// QuickAddForm.jsx — Extracted from InventoryPanel.jsx
import React, { useState } from 'react';
import { COLORS, CATEGORIAS, UNIDADES, API_BASE_URL, fmtCOP } from './constants';
import { S } from './styles';
import NumInput from '../../../shared/NumInput';

// ════════════════════════════════════════════════════════════
// COMPONENTE: FORMULARIO RÁPIDO DE AGREGAR ITEM
// ════════════════════════════════════════════════════════════
export default function QuickAddForm({ activePortfolio, activeCompany, existingItems = [], onCreated }) {
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

  // ── Previsualización en vivo del recurso ─────────────────
  const stockNum = parseInt(form.current_stock, 10) || 0;
  const costNum  = parseFloat(form.cost_price) || 0;
  const sellNum  = parseFloat(form.sell_price) || 0;
  const lineCost = stockNum * costNum;
  const lineSell = stockNum * sellNum;
  const lineUtil = lineSell - lineCost;

  // ¿Ya existe este recurso en esta empresa? (match por SKU o nombre)
  const dup = existingItems.find((it) => {
    const skuMatch  = form.sku.trim() && it.sku && it.sku.toLowerCase() === form.sku.trim().toLowerCase();
    const nameMatch = form.name.trim() && it.name && it.name.toLowerCase() === form.name.trim().toLowerCase();
    return skuMatch || nameMatch;
  });
  const combinedStock = (dup?.current_stock ?? 0) + stockNum;

  const handleSubmit = async () => {
    if (!form.name.trim()) return alert('El nombre es obligatorio');
    setSubmitting(true);
    try {
      const body = {
        portfolio_name: activePortfolio,
        company_id: activeCompany?.id ?? null,
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
      <div style={{ ...S.label, fontSize: 10, marginBottom: 8, color: COLORS.black }}>
        ▸ NUEVO ITEM DE INVENTARIO
      </div>

      {/* Empresa destino: deja claro a dónde se agrega el recurso */}
      <div style={{
        fontSize: 10, marginBottom: 10, padding: '6px 8px',
        border: `2px solid ${activeCompany?.id != null ? COLORS.black : COLORS.amber}`,
        background: activeCompany?.id != null ? '#f0f8f0' : '#fff8e6',
        display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <span style={{ fontWeight: 700 }}>EMPRESA DESTINO:</span>
        {activeCompany?.id != null ? (
          <span style={{ fontWeight: 700 }}>{activeCompany.name}</span>
        ) : (
          <span style={{ color: '#a15c00' }}>
            ⚠ Ninguna empresa seleccionada — el recurso quedará a nivel general del portafolio. Selecciona una empresa para asignarlo a ella.
          </span>
        )}
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
          <NumInput
            value={form.cost_price}
            onChange={(e) => update('cost_price', e.target.value)}
            placeholder="0"
            style={S.input}
          />
        </div>
        <div>
          <div style={S.label}>PRECIO VENTA</div>
          <NumInput
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
          <NumInput
            value={form.current_stock}
            onChange={(e) => update('current_stock', e.target.value)}
            placeholder="0"
            style={S.input}
          />
        </div>
        <div>
          <div style={S.label}>STOCK MÍNIMO</div>
          <NumInput
            value={form.min_stock}
            onChange={(e) => update('min_stock', e.target.value)}
            placeholder="0"
            style={S.input}
          />
        </div>
      </div>

      {/* ── Previsualización del recurso ─────────────────────── */}
      {stockNum > 0 && (
        <div style={{
          border: `2px solid ${COLORS.black}`, background: '#0d0d0d', color: COLORS.headerText,
          padding: '8px 10px', marginBottom: 12, fontSize: 11,
        }}>
          {dup && (
            <div style={{ color: COLORS.amber, fontWeight: 700, marginBottom: 6, letterSpacing: '0.5px' }}>
              ⚠ Ya existe "{dup.name}" con {dup.current_stock} en stock · total quedaría {combinedStock} {form.unit}
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
            <span>CANTIDAD: <b>{stockNum.toLocaleString('es-CO')} {form.unit}</b></span>
            <span>COSTO: <b>{fmtCOP(lineCost)}</b></span>
            <span>VENTA: <b>{fmtCOP(lineSell)}</b></span>
            <span>UTILIDAD: <b style={{ color: lineUtil >= 0 ? COLORS.greenSoft : COLORS.crimson }}>{fmtCOP(lineUtil)}</b></span>
          </div>
        </div>
      )}

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
