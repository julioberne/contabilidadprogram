// ============================================================
// InventoryPanel.jsx — Panel de Inventario para FIN-SYS OS
// Estilo: Retro-Brutalista (IBM Plex Mono, bordes duros, 0px radius)
// ============================================================
import React, { useState, useEffect, useCallback } from 'react';
import { COLORS, API_BASE_URL, fmtCOP } from './inventory/constants';
import { S } from './inventory/styles';
import ItemRow from './inventory/ItemRow';
import QuickAddForm from './inventory/QuickAddForm';

// ════════════════════════════════════════════════════════════
// COMPONENTE PRINCIPAL
// ════════════════════════════════════════════════════════════
export default function InventoryPanel({ activePortfolio, activeCompany, onDataChanged }) {
  // ── Estado global ────────────────────────────────────────
  const [items, setItems] = useState([]);
  const [summary, setSummary] = useState({ total_items: 0, total_value: 0, low_stock_count: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // ── Estado de UI ─────────────────────────────────────────
  const [expandedItemId, setExpandedItemId] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingStockId, setEditingStockId] = useState(null);
  const [editingStockVal, setEditingStockVal] = useState('');

  // ── Cargar datos ─────────────────────────────────────────
  const fetchItems = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE_URL}/inventory/items?portfolio=${encodeURIComponent(activePortfolio)}`);
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      setItems(Array.isArray(data) ? data : (data.items || []));
    } catch (e) {
      setError(e.message);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [activePortfolio]);

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/inventory/summary?portfolio=${encodeURIComponent(activePortfolio)}`);
      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      }
    } catch (_) { /* silencioso */ }
  }, [activePortfolio]);

  useEffect(() => {
    if (activePortfolio) {
      fetchItems();
      fetchSummary();
    }
  }, [activePortfolio, fetchItems, fetchSummary]);

  // ── Refrescar después de mutación ────────────────────────
  const refresh = async () => {
    await Promise.all([fetchItems(), fetchSummary()]);
    if (onDataChanged) onDataChanged();
  };

  // ── Actualizar stock inline ──────────────────────────────
  const handleStockSave = async (itemId) => {
    const val = parseInt(editingStockVal, 10);
    if (isNaN(val) || val < 0) return;
    try {
      const res = await fetch(`${API_BASE_URL}/inventory/items/${itemId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_stock: val }),
      });
      if (!res.ok) throw new Error('Error actualizando stock');
      setEditingStockId(null);
      await refresh();
    } catch (e) {
      alert(e.message);
    }
  };

  // ── Eliminar item (soft delete) ──────────────────────────
  const handleDelete = async (itemId, nombre) => {
    if (!window.confirm(`¿Eliminar "${nombre}"?`)) return;
    try {
      const res = await fetch(`${API_BASE_URL}/inventory/items/${itemId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Error eliminando');
      await refresh();
    } catch (e) {
      alert(e.message);
    }
  };

  // ════════════════════════════════════════════════════════════
  // RENDER
  // ════════════════════════════════════════════════════════════
  return (
    <div style={{ ...S.font, background: COLORS.bg, minHeight: '100%' }}>
      {/* ── HEADER ─────────────────────────────────────────── */}
      <div style={{
        background: COLORS.headerBg,
        color: COLORS.headerText,
        padding: '12px 16px',
        borderBottom: `2px solid ${COLORS.black}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase' }}>
            ▪ INVENTARIO
          </div>
          <div style={{ fontSize: 9, color: COLORS.gray, marginTop: 2, letterSpacing: '1px' }}>
            {activePortfolio || 'Sin portafolio'}
            {activeCompany?.industry ? ` · ${activeCompany.industry}` : ''}
          </div>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          style={{
            ...S.btnPrimary,
            background: showAddForm ? COLORS.crimson : COLORS.black,
            fontSize: 10,
            padding: '6px 12px',
          }}
          onMouseEnter={(e) => { e.target.style.transform = 'translate(-1px,-1px)'; e.target.style.boxShadow = `4px 4px 0 ${COLORS.black}`; }}
          onMouseLeave={(e) => { e.target.style.transform = 'none'; e.target.style.boxShadow = `3px 3px 0 ${COLORS.black}`; }}
        >
          {showAddForm ? '✕ CERRAR' : '+ AGREGAR'}
        </button>
      </div>

      {/* ── 1. BARRA DE RESUMEN ────────────────────────────── */}
      <div style={{
        display: 'flex',
        gap: 0,
        borderBottom: `2px solid ${COLORS.black}`,
      }}>
        {[
          { label: 'ITEMS', value: summary.total_items ?? items.length, color: COLORS.black },
          { label: 'VALOR TOTAL', value: fmtCOP(summary.total_value), color: COLORS.greenSoft },
          { label: 'ALERTAS', value: summary.low_stock_count ?? 0, color: summary.low_stock_count > 0 ? COLORS.crimson : COLORS.black },
        ].map((stat, i) => (
          <div key={i} style={{
            flex: 1,
            padding: '10px 12px',
            borderRight: i < 2 ? `2px solid ${COLORS.black}` : 'none',
            background: COLORS.white,
            textAlign: 'center',
          }}>
            <div style={{ ...S.label, marginBottom: 4 }}>{stat.label}</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: stat.color, letterSpacing: '0.5px' }}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>

      {/* ── 3. FORMULARIO RÁPIDO (colapsable) ──────────────── */}
      {showAddForm && (
        <QuickAddForm
          activePortfolio={activePortfolio}
          onCreated={async () => { setShowAddForm(false); await refresh(); }}
        />
      )}

      {/* ── ERROR / LOADING ────────────────────────────────── */}
      {error && (
        <div style={{
          margin: 12,
          padding: '10px 14px',
          background: '#fff0f0',
          border: `2px solid ${COLORS.crimson}`,
          fontSize: 11,
          color: COLORS.crimson,
          fontWeight: 600,
        }}>
          ⚠ {error}
          <button onClick={fetchItems} style={{ ...S.btnSecondary, marginLeft: 10, fontSize: 9, padding: '3px 8px' }}>
            REINTENTAR
          </button>
        </div>
      )}

      {loading && (
        <div style={{ textAlign: 'center', padding: 30, fontSize: 11, color: COLORS.gray, letterSpacing: '2px' }}>
          CARGANDO INVENTARIO...
        </div>
      )}

      {/* ── 2. TABLA DE ITEMS ──────────────────────────────── */}
      {!loading && items.length === 0 && !error && (
        <div style={{
          textAlign: 'center',
          padding: '40px 20px',
          color: COLORS.gray,
          fontSize: 11,
          letterSpacing: '1px',
        }}>
          NO HAY ITEMS REGISTRADOS
          <br />
          <span style={{ fontSize: 9 }}>Usa el botón + AGREGAR para crear el primero</span>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div style={{ overflow: 'auto' }}>
          {/* Encabezados de tabla */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '70px 1fr 100px 65px 90px 90px 60px 36px',
            background: COLORS.headerBg,
            color: COLORS.headerText,
            borderBottom: `2px solid ${COLORS.black}`,
          }}>
            {['SKU', 'NOMBRE', 'CATEGORÍA', 'STOCK', 'P.VENTA', 'P.COSTO', 'ESTADO', ''].map((h, i) => (
              <div key={i} style={{
                ...S.label,
                color: COLORS.grayLight,
                padding: '8px 6px',
                borderRight: i < 7 ? `1px solid #333` : 'none',
                marginBottom: 0,
              }}>
                {h}
              </div>
            ))}
          </div>

          {/* Filas */}
          {items.map((item) => (
            <ItemRow
              key={item.id}
              item={item}
              isExpanded={expandedItemId === item.id}
              onToggle={() => setExpandedItemId(expandedItemId === item.id ? null : item.id)}
              editingStockId={editingStockId}
              editingStockVal={editingStockVal}
              onEditStock={(id, val) => { setEditingStockId(id); setEditingStockVal(String(val)); }}
              onStockValChange={setEditingStockVal}
              onStockSave={handleStockSave}
              onStockCancel={() => setEditingStockId(null)}
              onDelete={handleDelete}
              onMovementCreated={refresh}
            />
          ))}
        </div>
      )}
    </div>
  );
}
