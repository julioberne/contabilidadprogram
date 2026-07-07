// ItemRow.jsx — Extracted from InventoryPanel.jsx
import React, { useState } from 'react';
import { COLORS, fmtCOP } from './constants';
import { S } from './styles';
import MovementPanel from './MovementPanel';

// ── Chip de estado de stock ────────────────────────────────
const StockChip = ({ current, min }) => {
  let bg = COLORS.greenSoft;
  let label = 'OK';
  if (current <= min) {
    bg = COLORS.crimson;
    label = 'BAJO';
  } else if (current <= min * 2) {
    bg = COLORS.amber;
    label = 'MEDIO';
  }
  return <span style={S.chip(bg, current <= min ? COLORS.white : COLORS.black)}>{label}</span>;
};

// ════════════════════════════════════════════════════════════
// COMPONENTE: FILA DE ITEM
// ════════════════════════════════════════════════════════════
export default function ItemRow({
  item, isExpanded, onToggle,
  editingStockId, editingStockVal,
  onEditStock, onStockValChange, onStockSave, onStockCancel,
  onDelete, onMovementCreated,
}) {
  const [hovered, setHovered] = useState(false);
  const isEditingStock = editingStockId === item.id;

  return (
    <div style={{ borderBottom: `2px solid ${COLORS.black}` }}>
      {/* Fila principal */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '70px 1fr 100px 65px 90px 90px 60px 36px',
          background: hovered ? '#e8e8e2' : COLORS.white,
          cursor: 'pointer',
          transition: 'background 0.12s ease',
          alignItems: 'center',
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={(e) => {
          // No colapsar si se está editando stock
          if (isEditingStock) return;
          onToggle();
        }}
      >
        {/* SKU */}
        <div style={{ padding: '8px 6px', fontSize: 10, fontWeight: 600, color: COLORS.gray, borderRight: `1px solid ${COLORS.grayLight}` }}>
          {item.sku || '—'}
        </div>

        {/* Nombre */}
        <div style={{ padding: '8px 6px', fontSize: 12, fontWeight: 600, borderRight: `1px solid ${COLORS.grayLight}`, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {item.name}
        </div>

        {/* Categoría */}
        <div style={{ padding: '8px 6px', fontSize: 10, color: COLORS.gray, borderRight: `1px solid ${COLORS.grayLight}` }}>
          {item.category || '—'}
        </div>

        {/* Stock (editable inline) */}
        <div
          style={{ padding: '6px 4px', textAlign: 'center', borderRight: `1px solid ${COLORS.grayLight}` }}
          onClick={(e) => {
            e.stopPropagation();
            if (!isEditingStock) onEditStock(item.id, item.current_stock);
          }}
        >
          {isEditingStock ? (
            <div style={{ display: 'flex', gap: 2 }}>
              <input
                type="number"
                value={editingStockVal}
                onChange={(e) => onStockValChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') onStockSave(item.id);
                  if (e.key === 'Escape') onStockCancel();
                }}
                autoFocus
                style={{
                  ...S.input,
                  width: 40,
                  padding: '2px 4px',
                  fontSize: 11,
                  textAlign: 'center',
                }}
                onClick={(e) => e.stopPropagation()}
              />
              <button
                onClick={(e) => { e.stopPropagation(); onStockSave(item.id); }}
                style={{ ...S.btnSecondary, padding: '1px 4px', fontSize: 9, lineHeight: '14px' }}
              >
                ✓
              </button>
            </div>
          ) : (
            <span style={{
              fontSize: 12,
              fontWeight: 700,
              cursor: 'text',
              borderBottom: `1px dashed ${COLORS.grayLight}`,
              padding: '0 4px',
            }}>
              {item.current_stock ?? 0}
            </span>
          )}
        </div>

        {/* Precio Venta */}
        <div style={{ padding: '8px 6px', fontSize: 11, textAlign: 'right', borderRight: `1px solid ${COLORS.grayLight}` }}>
          {fmtCOP(item.sell_price)}
        </div>

        {/* Precio Costo */}
        <div style={{ padding: '8px 6px', fontSize: 11, textAlign: 'right', color: COLORS.gray, borderRight: `1px solid ${COLORS.grayLight}` }}>
          {fmtCOP(item.cost_price)}
        </div>

        {/* Estado */}
        <div style={{ padding: '6px 4px', textAlign: 'center', borderRight: `1px solid ${COLORS.grayLight}` }}>
          <StockChip current={item.current_stock ?? 0} min={item.min_stock ?? 0} />
        </div>

        {/* Acción eliminar */}
        <div
          style={{ padding: '6px 4px', textAlign: 'center', cursor: 'pointer' }}
          onClick={(e) => { e.stopPropagation(); onDelete(item.id, item.name); }}
          title="Eliminar"
        >
          <span style={{ fontSize: 12, color: COLORS.crimson, fontWeight: 700, opacity: hovered ? 1 : 0.3, transition: 'opacity 0.15s' }}>✕</span>
        </div>
      </div>

      {/* Panel expandido: movimientos */}
      {isExpanded && (
        <MovementPanel item={item} onMovementCreated={onMovementCreated} />
      )}
    </div>
  );
}
