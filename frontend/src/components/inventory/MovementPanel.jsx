// MovementPanel.jsx — Extracted from InventoryPanel.jsx
import React, { useState, useEffect } from 'react';
import { COLORS, API_BASE_URL, fmtCOP } from './constants';
import { S } from './styles';

// ════════════════════════════════════════════════════════════
// COMPONENTE: PANEL DE MOVIMIENTOS (inline por item)
// ════════════════════════════════════════════════════════════
export default function MovementPanel({ item, onMovementCreated }) {
  const [movements, setMovements] = useState([]);
  const [loadingMov, setLoadingMov] = useState(true);
  const [movType, setMovType] = useState('ENTRADA');
  const [movQty, setMovQty] = useState('');
  const [movPrice, setMovPrice] = useState('');
  const [movNotes, setMovNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Cargar movimientos recientes
  useEffect(() => {
    const fetchMov = async () => {
      setLoadingMov(true);
      try {
        const res = await fetch(`${API_BASE_URL}/inventory/movements?item_id=${item.id}&limit=10`);
        if (res.ok) {
          const data = await res.json();
          setMovements(Array.isArray(data) ? data : (data.movements || []));
        }
      } catch (_) { /* silencioso */ }
      setLoadingMov(false);
    };
    fetchMov();
  }, [item.id]);

  // Registrar movimiento
  const handleSubmit = async () => {
    const qty = parseInt(movQty, 10);
    if (!qty || qty <= 0) return alert('Cantidad inválida');
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/inventory/movements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_id: item.id,
          type: movType,
          quantity: qty,
          unit_price: movPrice ? parseFloat(movPrice) : null,
          notes: movNotes || null,
        }),
      });
      if (!res.ok) throw new Error('Error registrando movimiento');
      // Limpiar y refrescar
      setMovQty('');
      setMovPrice('');
      setMovNotes('');
      // Refrescar lista de movimientos
      const res2 = await fetch(`${API_BASE_URL}/inventory/movements?item_id=${item.id}&limit=10`);
      if (res2.ok) {
        const data = await res2.json();
        setMovements(Array.isArray(data) ? data : (data.movements || []));
      }
      if (onMovementCreated) onMovementCreated();
    } catch (e) {
      alert(e.message);
    }
    setSubmitting(false);
  };

  const typeColors = {
    ENTRADA: COLORS.greenSoft,
    SALIDA: COLORS.crimson,
    AJUSTE: COLORS.amber,
  };

  return (
    <div style={{
      background: COLORS.bgAlt,
      borderTop: `2px solid ${COLORS.black}`,
      padding: '12px 14px',
    }}>
      {/* Título */}
      <div style={{ ...S.label, fontSize: 10, marginBottom: 10, color: COLORS.black }}>
        ▸ MOVIMIENTOS — {item.name}
      </div>

      {/* Botones de tipo */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 10 }}>
        {['ENTRADA', 'SALIDA', 'AJUSTE'].map((t) => (
          <button
            key={t}
            onClick={() => setMovType(t)}
            style={{
              ...S.btnSecondary,
              flex: 1,
              background: movType === t ? typeColors[t] : COLORS.white,
              color: movType === t && t === 'SALIDA' ? COLORS.white : COLORS.black,
              fontWeight: movType === t ? 700 : 500,
              borderRight: t !== 'AJUSTE' ? 'none' : `2px solid ${COLORS.black}`,
              boxShadow: movType === t ? `2px 2px 0 ${COLORS.black}` : 'none',
            }}
          >
            {t === 'ENTRADA' ? '↓ ' : t === 'SALIDA' ? '↑ ' : '⟳ '}{t}
          </button>
        ))}
      </div>

      {/* Inputs de movimiento */}
      <div style={{ display: 'grid', gridTemplateColumns: '80px 100px 1fr auto', gap: 6, alignItems: 'end', marginBottom: 12 }}>
        <div>
          <div style={S.label}>CANT.</div>
          <input
            type="number"
            min="1"
            value={movQty}
            onChange={(e) => setMovQty(e.target.value)}
            placeholder="0"
            style={{ ...S.input, fontSize: 11 }}
          />
        </div>
        <div>
          <div style={S.label}>P.UNIT (OPC)</div>
          <input
            type="number"
            value={movPrice}
            onChange={(e) => setMovPrice(e.target.value)}
            placeholder="$0"
            style={{ ...S.input, fontSize: 11 }}
          />
        </div>
        <div>
          <div style={S.label}>NOTAS (OPC)</div>
          <input
            type="text"
            value={movNotes}
            onChange={(e) => setMovNotes(e.target.value)}
            placeholder="Referencia, proveedor..."
            style={{ ...S.input, fontSize: 11 }}
          />
        </div>
        <button
          onClick={handleSubmit}
          disabled={submitting}
          style={{
            ...S.btnPrimary,
            padding: '7px 14px',
            fontSize: 10,
            opacity: submitting ? 0.5 : 1,
          }}
        >
          {submitting ? '...' : 'REGISTRAR'}
        </button>
      </div>

      {/* Lista de movimientos recientes */}
      <div style={{ ...S.label, marginBottom: 6 }}>ÚLTIMOS MOVIMIENTOS</div>
      {loadingMov ? (
        <div style={{ fontSize: 10, color: COLORS.gray, padding: 8 }}>Cargando...</div>
      ) : movements.length === 0 ? (
        <div style={{ fontSize: 10, color: COLORS.gray, padding: 8, textAlign: 'center' }}>
          Sin movimientos registrados
        </div>
      ) : (
        <div style={{ border: `2px solid ${COLORS.black}`, background: COLORS.white }}>
          {movements.map((mov, i) => (
            <div
              key={mov.id || i}
              style={{
                display: 'grid',
                gridTemplateColumns: '70px 50px 90px 1fr auto',
                fontSize: 10,
                borderBottom: i < movements.length - 1 ? `1px solid ${COLORS.grayLight}` : 'none',
                alignItems: 'center',
              }}
            >
              {/* Tipo */}
              <div style={{ padding: '5px 6px' }}>
                <span style={S.chip(typeColors[mov.type] || COLORS.grayLight, mov.type === 'SALIDA' ? COLORS.white : COLORS.black)}>
                  {mov.type}
                </span>
              </div>
              {/* Cantidad */}
              <div style={{ padding: '5px 4px', fontWeight: 700, textAlign: 'center' }}>
                {mov.type === 'SALIDA' ? '-' : '+'}{mov.quantity}
              </div>
              {/* Precio */}
              <div style={{ padding: '5px 4px', color: COLORS.gray }}>
                {mov.unit_price ? fmtCOP(mov.unit_price) : '—'}
              </div>
              {/* Notas */}
              <div style={{ padding: '5px 4px', color: COLORS.gray, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {mov.notes || '—'}
              </div>
              {/* Fecha */}
              <div style={{ padding: '5px 6px', color: COLORS.grayLight, fontSize: 9 }}>
                {mov.created_at ? new Date(mov.created_at).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }) : ''}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
