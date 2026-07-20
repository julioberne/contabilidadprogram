// ============================================================
// UniformesWidget.jsx — Caja Rápida de Uniformes
// Despacho rápido: estudiante + artículo + método de pago
// Pago Inmediato → POST /api/transactions (INGRESO)
// A Crédito → POST /api/cartera (CXC)
// ============================================================
import React, { useState, useEffect, useCallback } from 'react';
import { API } from '../../../../config';

// Colores del widget — acento cyan
const C = {
  bg:       '#0a0a14',
  surface:  '#111122',
  border:   '#00bcd4',
  accent:   '#00bcd4',
  dimCyan:  '#00bcd422',
  green:    '#00ff41',
  amber:    '#ffb000',
  red:      '#ff3333',
  text:     '#e0e0e0',
  muted:    '#666680',
};

const FONT = {
  fontFamily: "'IBM Plex Mono', monospace",
  textTransform: 'uppercase',
  letterSpacing: '1.5px',
};

export default function UniformesWidget({ config, template, activeCompany, activePortfolio, onTransactionCreated }) {
  // Datos
  const [terceros, setTerceros] = useState([]);
  const [inventario, setInventario] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Formulario
  const [selectedStudent, setSelectedStudent] = useState('');
  const [selectedItem, setSelectedItem] = useState('');
  const [cantidad, setCantidad] = useState(1);
  const [payMode, setPayMode] = useState('inmediato'); // 'inmediato' | 'credito'

  // Estado de envío
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);

  // Despachos recientes (en memoria de sesión)
  const [despachos, setDespachos] = useState([]);

  // Cargar datos
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const portfolioName = activePortfolio?.name || activePortfolio?.portfolio_name || '';
      const [resTerceros, resAssets] = await Promise.all([
        fetch(`${API}/third-parties`),
        fetch(`${API}/assets?portfolio=${encodeURIComponent(portfolioName)}`),
      ]);
      if (!resTerceros.ok) throw new Error(`Terceros: ${resTerceros.status}`);

      const dataTerceros = await resTerceros.json();
      setTerceros(Array.isArray(dataTerceros) ? dataTerceros : []);

      // Intentar cargar inventario; si falla, usar items por defecto
      if (resAssets.ok) {
        const dataAssets = await resAssets.json();
        setInventario(Array.isArray(dataAssets) ? dataAssets : []);
      } else {
        // Items por defecto para uniformes de jardín
        setInventario([
          { id: 'uni-01', name: 'Uniforme Diario', price: 85000 },
          { id: 'uni-02', name: 'Uniforme Deportivo', price: 75000 },
          { id: 'uni-03', name: 'Bata / Delantal', price: 35000 },
          { id: 'uni-04', name: 'Sudadera', price: 55000 },
          { id: 'uni-05', name: 'Kit Completo', price: 220000 },
        ]);
      }
    } catch (err) {
      console.error('[UniformesWidget] Error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [activePortfolio]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Obtener artículo seleccionado
  const itemObj = inventario.find(i => String(i.id) === String(selectedItem));
  const studentObj = terceros.find(t => String(t.id) === String(selectedStudent));
  const totalVenta = itemObj ? (itemObj.price || itemObj.valor || 0) * cantidad : 0;

  // Manejar despacho
  const handleDespachar = async () => {
    if (!selectedStudent || !selectedItem || submitting) return;

    setSubmitting(true);
    setSubmitResult(null);

    try {
      const portfolioName = activePortfolio?.name || activePortfolio?.portfolio_name || '';
      const desc = `${itemObj?.name || 'Artículo'} x${cantidad} — ${studentObj?.name || 'Estudiante'}`;

      if (payMode === 'inmediato') {
        // Registrar como ingreso
        const body = {
          portfolio: portfolioName,
          portfolio_id: activePortfolio?.id,
          type: 'INGRESO',
          description: desc,
          concept: 'VENTA UNIFORMES',
          amount: totalVenta,
          tercero_id: selectedStudent,
          third_party_id: selectedStudent,
          tercero_nombre: studentObj?.name || '',
        };

        const res = await fetch(`${API}/transactions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });

        if (!res.ok) throw new Error(`Error ${res.status}`);
        setSubmitResult({ ok: true, msg: `💰 Pago registrado: $${totalVenta.toLocaleString('es-CO')}` });
      } else {
        // Registrar como CXC
        const body = {
          portfolio: portfolioName,
          portfolio_id: activePortfolio?.id,
          type: 'CXC',
          concept: 'UNIFORMES A CRÉDITO',
          description: desc,
          amount: totalVenta,
          monto: totalVenta,
          tercero_id: selectedStudent,
          third_party_id: selectedStudent,
          tercero_nombre: studentObj?.name || '',
          status: 'pendiente',
          due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        };

        const res = await fetch(`${API}/cartera`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });

        if (!res.ok) throw new Error(`Error ${res.status}`);
        setSubmitResult({ ok: true, msg: `📋 CXC creada: $${totalVenta.toLocaleString('es-CO')} a 30 días` });
      }

      // Agregar a despachos recientes
      setDespachos(prev => [{
        id: Date.now(),
        student: studentObj?.name || 'N/A',
        item: itemObj?.name || 'N/A',
        qty: cantidad,
        total: totalVenta,
        mode: payMode,
        time: new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }),
      }, ...prev].slice(0, 8));

      // Limpiar formulario
      setSelectedStudent('');
      setSelectedItem('');
      setCantidad(1);

      // Notificar al padre
      if (onTransactionCreated) {
        onTransactionCreated({ type: 'uniforme_despachado', amount: totalVenta });
      }
    } catch (err) {
      console.error('[UniformesWidget] Error:', err);
      setSubmitResult({ ok: false, msg: `⚠ ${err.message}` });
    } finally {
      setSubmitting(false);
    }
  };

  // ── Estilos ──
  const styles = {
    container: {
      ...FONT,
      background: C.bg,
      border: `2px solid ${C.border}`,
      padding: '20px',
      boxShadow: '3px 3px 0 #000',
      fontSize: '12px',
    },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '16px',
      paddingBottom: '12px',
      borderBottom: `1px solid ${C.border}44`,
    },
    title: {
      ...FONT,
      fontSize: '14px',
      fontWeight: 700,
      color: C.accent,
      margin: 0,
    },
    badge: {
      ...FONT,
      fontSize: '10px',
      padding: '4px 10px',
      background: C.dimCyan,
      border: `1px solid ${C.accent}`,
      color: C.accent,
    },
    formGrid: {
      display: 'flex',
      flexDirection: 'column',
      gap: '12px',
      marginBottom: '14px',
    },
    fieldGroup: {
      display: 'flex',
      flexDirection: 'column',
      gap: '4px',
    },
    label: {
      ...FONT,
      fontSize: '9px',
      color: C.muted,
    },
    select: {
      ...FONT,
      fontSize: '11px',
      padding: '10px 12px',
      background: C.surface,
      color: C.text,
      border: `1px solid ${C.muted}44`,
      outline: 'none',
      cursor: 'pointer',
      appearance: 'none',
      borderRadius: 0,
    },
    inputRow: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '12px',
    },
    numberInput: {
      ...FONT,
      fontSize: '11px',
      padding: '10px 12px',
      background: C.surface,
      color: C.text,
      border: `1px solid ${C.muted}44`,
      outline: 'none',
      width: '100%',
      boxSizing: 'border-box',
      borderRadius: 0,
    },
    payToggle: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '0px',
      border: `2px solid ${C.accent}`,
    },
    payOption: (active) => ({
      ...FONT,
      fontSize: '10px',
      fontWeight: 700,
      padding: '10px',
      textAlign: 'center',
      background: active ? C.accent : 'transparent',
      color: active ? '#000' : C.accent,
      cursor: 'pointer',
      border: 'none',
      transition: 'all 0.15s ease',
      borderRadius: 0,
    }),
    totalBar: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '12px 14px',
      marginBottom: '14px',
      background: C.surface,
      border: `1px solid ${C.accent}33`,
    },
    totalLabel: {
      ...FONT,
      fontSize: '10px',
      color: C.muted,
    },
    totalValue: {
      ...FONT,
      fontSize: '20px',
      fontWeight: 700,
      color: C.accent,
    },
    button: (disabled) => ({
      ...FONT,
      width: '100%',
      padding: '14px',
      fontSize: '13px',
      fontWeight: 700,
      letterSpacing: '2px',
      background: disabled ? `${C.muted}33` : C.accent,
      color: disabled ? C.muted : '#000',
      border: `2px solid ${disabled ? C.muted : C.accent}`,
      cursor: disabled ? 'not-allowed' : 'pointer',
      boxShadow: disabled ? 'none' : '3px 3px 0 #000',
      transition: 'all 0.15s ease',
      borderRadius: 0,
    }),
    resultBox: (ok) => ({
      ...FONT,
      padding: '10px 14px',
      marginTop: '12px',
      fontSize: '10px',
      background: ok ? `${C.green}15` : `${C.red}15`,
      border: `1px solid ${ok ? C.green : C.red}44`,
      color: ok ? C.green : C.red,
      textAlign: 'center',
    }),
    despachosSection: {
      marginTop: '18px',
      paddingTop: '14px',
      borderTop: `1px solid ${C.muted}33`,
    },
    despachosTitle: {
      ...FONT,
      fontSize: '10px',
      color: C.muted,
      marginBottom: '10px',
    },
    despachoRow: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '8px 10px',
      marginBottom: '4px',
      background: C.surface,
      border: `1px solid ${C.muted}22`,
      fontSize: '10px',
    },
    despachoLeft: {
      display: 'flex',
      flexDirection: 'column',
      gap: '2px',
    },
    despachoName: {
      ...FONT,
      fontSize: '10px',
      color: C.text,
    },
    despachoDetail: {
      ...FONT,
      fontSize: '8px',
      color: C.muted,
    },
    despachoRight: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-end',
      gap: '2px',
    },
    despachoAmount: {
      ...FONT,
      fontSize: '11px',
      fontWeight: 700,
      color: C.accent,
    },
    despachoBadge: (mode) => ({
      ...FONT,
      fontSize: '7px',
      padding: '2px 6px',
      background: mode === 'inmediato' ? `${C.green}22` : `${C.amber}22`,
      color: mode === 'inmediato' ? C.green : C.amber,
      border: `1px solid ${mode === 'inmediato' ? C.green : C.amber}44`,
    }),
    loadingMsg: {
      ...FONT,
      color: C.accent,
      fontSize: '11px',
      padding: '20px',
      textAlign: 'center',
    },
    errorMsg: {
      ...FONT,
      color: C.red,
      fontSize: '11px',
      padding: '12px',
      background: `${C.red}15`,
      border: `1px solid ${C.red}44`,
    },
  };

  const canSubmit = selectedStudent && selectedItem && cantidad > 0 && !submitting;

  return (
    <div style={styles.container}>
      {/* Encabezado */}
      <div style={styles.header}>
        <h3 style={styles.title}>👕 Caja Rápida — Uniformes</h3>
        <span style={styles.badge}>Despacho</span>
      </div>

      {/* Carga / error */}
      {loading && (
        <div style={styles.loadingMsg}>⏳ Cargando datos...</div>
      )}
      {error && (
        <div style={styles.errorMsg}>⚠ Error: {error}</div>
      )}

      {!loading && !error && (
        <>
          {/* Formulario */}
          <div style={styles.formGrid}>
            {/* Selección de estudiante */}
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Estudiante</label>
              <select
                style={styles.select}
                value={selectedStudent}
                onChange={(e) => setSelectedStudent(e.target.value)}
              >
                <option value="">— Seleccionar —</option>
                {terceros.map(t => (
                  <option key={t.id} value={t.id}>
                    {t.name || t.nombre}
                  </option>
                ))}
              </select>
            </div>

            {/* Selección de artículo */}
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Artículo</label>
              <select
                style={styles.select}
                value={selectedItem}
                onChange={(e) => setSelectedItem(e.target.value)}
              >
                <option value="">— Seleccionar —</option>
                {inventario.map(i => (
                  <option key={i.id} value={i.id}>
                    {i.name || i.nombre} — ${(i.price || i.valor || 0).toLocaleString('es-CO')}
                  </option>
                ))}
              </select>
            </div>

            {/* Cantidad + Modo de pago */}
            <div style={styles.inputRow}>
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Cantidad</label>
                <input
                  type="number"
                  min="1"
                  max="99"
                  style={styles.numberInput}
                  value={cantidad}
                  onChange={(e) => setCantidad(Math.max(1, parseInt(e.target.value) || 1))}
                />
              </div>
              <div style={styles.fieldGroup}>
                <label style={styles.label}>Método de Pago</label>
                <div style={styles.payToggle}>
                  <button
                    style={styles.payOption(payMode === 'inmediato')}
                    onClick={() => setPayMode('inmediato')}
                  >
                    💵 Inmediato
                  </button>
                  <button
                    style={styles.payOption(payMode === 'credito')}
                    onClick={() => setPayMode('credito')}
                  >
                    📋 A Crédito
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Total */}
          <div style={styles.totalBar}>
            <span style={styles.totalLabel}>Total</span>
            <span style={styles.totalValue}>
              ${totalVenta.toLocaleString('es-CO')}
            </span>
          </div>

          {/* Botón despachar */}
          <button
            style={styles.button(!canSubmit)}
            disabled={!canSubmit}
            onClick={handleDespachar}
            onMouseEnter={(e) => {
              if (canSubmit) {
                e.currentTarget.style.transform = 'translate(-2px, -2px)';
                e.currentTarget.style.boxShadow = '5px 5px 0 #000';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'none';
              e.currentTarget.style.boxShadow = '3px 3px 0 #000';
            }}
          >
            {submitting ? '⏳ Procesando...' : '🚀 Despachar'}
          </button>

          {/* Resultado del envío */}
          {submitResult && (
            <div style={styles.resultBox(submitResult.ok)}>
              {submitResult.msg}
            </div>
          )}

          {/* Despachos recientes */}
          {despachos.length > 0 && (
            <div style={styles.despachosSection}>
              <div style={styles.despachosTitle}>
                📦 Despachos Recientes ({despachos.length})
              </div>
              {despachos.map(d => (
                <div key={d.id} style={styles.despachoRow}>
                  <div style={styles.despachoLeft}>
                    <span style={styles.despachoName}>{d.student}</span>
                    <span style={styles.despachoDetail}>
                      {d.item} x{d.qty} · {d.time}
                    </span>
                  </div>
                  <div style={styles.despachoRight}>
                    <span style={styles.despachoAmount}>
                      ${d.total.toLocaleString('es-CO')}
                    </span>
                    <span style={styles.despachoBadge(d.mode)}>
                      {d.mode === 'inmediato' ? 'PAGADO' : 'CRÉDITO'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
