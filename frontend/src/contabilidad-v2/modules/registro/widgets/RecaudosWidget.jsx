// ============================================================
// RecaudosWidget.jsx — Tablero de Recaudos del Mes
// Muestra un grid visual de estudiantes con estado de pago
// 🟢 Pagado  🟡 Pendiente  🔴 Vencido
// ============================================================
import React, { useState, useEffect, useCallback } from 'react';
import { API } from '../../../../config';

// Colores del widget
const C = {
  bg:       '#0a0a14',
  surface:  '#111122',
  border:   '#00ff41',
  accent:   '#00ff41',
  dimGreen: '#00ff4133',
  amber:    '#ffb000',
  red:      '#ff3333',
  text:     '#e0e0e0',
  muted:    '#666680',
};

// Estilo base compartido
const FONT = {
  fontFamily: "'IBM Plex Mono', monospace",
  textTransform: 'uppercase',
  letterSpacing: '1.5px',
};

export default function RecaudosWidget({ config, template, activeCompany, activePortfolio, onTransactionCreated }) {
  const [terceros, setTerceros] = useState([]);
  const [cartera, setCartera] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fecha actual para filtrar mes
  const now = new Date();
  const mesActual = now.getMonth();
  const anioActual = now.getFullYear();
  const nombreMes = now.toLocaleString('es-CO', { month: 'long' });

  // Cargar datos al montar
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const portfolioName = activePortfolio?.name || activePortfolio?.portfolio_name || '';
      const [resTerceros, resCartera] = await Promise.all([
        fetch(`${API}/third-parties`),
        fetch(`${API}/cartera?portfolio=${encodeURIComponent(portfolioName)}`),
      ]);
      if (!resTerceros.ok) throw new Error(`Terceros: ${resTerceros.status}`);
      if (!resCartera.ok) throw new Error(`Cartera: ${resCartera.status}`);

      const dataTerceros = await resTerceros.json();
      const dataCartera = await resCartera.json();

      // Filtrar terceros que sean estudiantes (tipo CLIENTE o sin tipo)
      setTerceros(Array.isArray(dataTerceros) ? dataTerceros : []);

      // Filtrar CXC del mes actual
      const cxcMes = (Array.isArray(dataCartera) ? dataCartera : []).filter(c => {
        const fecha = new Date(c.created_at || c.fecha || c.date);
        return fecha.getMonth() === mesActual && fecha.getFullYear() === anioActual;
      });
      setCartera(cxcMes);
    } catch (err) {
      console.error('[RecaudosWidget] Error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [activePortfolio, mesActual, anioActual]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Determinar estado de pago de cada estudiante
  const getEstado = (tercero) => {
    const cxc = cartera.find(c =>
      c.tercero_id === tercero.id ||
      c.third_party_id === tercero.id ||
      (c.tercero_nombre || '').toLowerCase() === (tercero.name || '').toLowerCase()
    );
    if (!cxc) return 'sin_registro';
    if (cxc.status === 'pagado' || cxc.status === 'paid' || cxc.paid) return 'pagado';
    const vencimiento = new Date(cxc.due_date || cxc.fecha_vencimiento || cxc.created_at);
    if (vencimiento < now) return 'vencido';
    return 'pendiente';
  };

  const estadoColor = {
    pagado:       C.accent,
    pendiente:    C.amber,
    vencido:      C.red,
    sin_registro: C.muted,
  };

  const estadoEmoji = {
    pagado:       '🟢',
    pendiente:    '🟡',
    vencido:      '🔴',
    sin_registro: '⚫',
  };

  // Resumen
  const total = terceros.length;
  const pagados = terceros.filter(t => getEstado(t) === 'pagado').length;
  const montoRecaudado = cartera
    .filter(c => c.status === 'pagado' || c.status === 'paid' || c.paid)
    .reduce((sum, c) => sum + (parseFloat(c.amount || c.monto || 0)), 0);

  // Manejar click en chip (placeholder para registrar pago)
  const handleChipClick = (tercero) => {
    const estado = getEstado(tercero);
    if (estado !== 'pagado') {
      // Aquí se podría abrir un modal de registro de pago
      // o llamar a onTransactionCreated si se desea
    }
  };

  // ── Estilos ──
  const styles = {
    container: {
      ...FONT,
      background: C.bg,
      border: `2px solid ${C.border}`,
      padding: '20px',
      boxShadow: `3px 3px 0 #000`,
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
      background: C.dimGreen,
      border: `1px solid ${C.accent}`,
      color: C.accent,
    },
    summaryBar: {
      display: 'flex',
      gap: '16px',
      marginBottom: '16px',
      padding: '12px',
      background: C.surface,
      border: `1px solid ${C.muted}44`,
    },
    summaryItem: {
      display: 'flex',
      flexDirection: 'column',
      gap: '2px',
    },
    summaryLabel: {
      ...FONT,
      fontSize: '9px',
      color: C.muted,
    },
    summaryValue: {
      ...FONT,
      fontSize: '16px',
      fontWeight: 700,
      color: C.text,
    },
    grid: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '8px',
    },
    chip: (color) => ({
      ...FONT,
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '6px 12px',
      background: `${color}15`,
      border: `1px solid ${color}66`,
      color: color,
      fontSize: '10px',
      cursor: 'pointer',
      transition: 'all 0.15s ease',
    }),
    chipHover: {
      transform: 'translate(-1px, -1px)',
      boxShadow: `2px 2px 0 #000`,
    },
    legend: {
      display: 'flex',
      gap: '16px',
      marginTop: '14px',
      paddingTop: '10px',
      borderTop: `1px solid ${C.muted}33`,
    },
    legendItem: {
      ...FONT,
      fontSize: '9px',
      color: C.muted,
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
    },
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
    emptyMsg: {
      ...FONT,
      color: C.muted,
      fontSize: '11px',
      padding: '20px',
      textAlign: 'center',
    },
    progressBar: {
      height: '4px',
      background: C.surface,
      marginBottom: '12px',
      overflow: 'hidden',
    },
    progressFill: (pct) => ({
      height: '100%',
      width: `${pct}%`,
      background: `linear-gradient(90deg, ${C.accent}, ${C.amber})`,
      transition: 'width 0.4s ease',
    }),
  };

  const pctPagado = total > 0 ? Math.round((pagados / total) * 100) : 0;

  return (
    <div style={styles.container}>
      {/* Encabezado */}
      <div style={styles.header}>
        <h3 style={styles.title}>📊 Recaudos — {nombreMes} {anioActual}</h3>
        <span style={styles.badge}>{pctPagado}% recaudado</span>
      </div>

      {/* Estado de carga / error */}
      {loading && (
        <div style={styles.loadingMsg}>⏳ Cargando recaudos...</div>
      )}
      {error && (
        <div style={styles.errorMsg}>⚠ Error: {error}</div>
      )}

      {!loading && !error && (
        <>
          {/* Barra de progreso visual */}
          <div style={styles.progressBar}>
            <div style={styles.progressFill(pctPagado)} />
          </div>

          {/* Resumen */}
          <div style={styles.summaryBar}>
            <div style={styles.summaryItem}>
              <span style={styles.summaryLabel}>Pagados</span>
              <span style={{ ...styles.summaryValue, color: C.accent }}>
                {pagados}/{total}
              </span>
            </div>
            <div style={styles.summaryItem}>
              <span style={styles.summaryLabel}>Recaudado</span>
              <span style={{ ...styles.summaryValue, color: C.accent }}>
                ${montoRecaudado.toLocaleString('es-CO')}
              </span>
            </div>
            <div style={styles.summaryItem}>
              <span style={styles.summaryLabel}>Pendientes</span>
              <span style={{ ...styles.summaryValue, color: C.amber }}>
                {terceros.filter(t => getEstado(t) === 'pendiente').length}
              </span>
            </div>
            <div style={styles.summaryItem}>
              <span style={styles.summaryLabel}>Vencidos</span>
              <span style={{ ...styles.summaryValue, color: C.red }}>
                {terceros.filter(t => getEstado(t) === 'vencido').length}
              </span>
            </div>
          </div>

          {/* Grid de chips de estudiantes */}
          {terceros.length === 0 ? (
            <div style={styles.emptyMsg}>
              No hay estudiantes registrados como terceros
            </div>
          ) : (
            <div style={styles.grid}>
              {terceros.map((t) => {
                const estado = getEstado(t);
                const color = estadoColor[estado];
                const emoji = estadoEmoji[estado];
                return (
                  <div
                    key={t.id}
                    style={styles.chip(color)}
                    onClick={() => handleChipClick(t)}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translate(-1px, -1px)';
                      e.currentTarget.style.boxShadow = '2px 2px 0 #000';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'none';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                    title={`${t.name} — ${estado.toUpperCase()}`}
                  >
                    <span>{emoji}</span>
                    <span>{(t.name || t.nombre || 'Sin nombre').split(' ')[0]}</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Leyenda */}
          <div style={styles.legend}>
            <span style={styles.legendItem}>🟢 Pagado</span>
            <span style={styles.legendItem}>🟡 Pendiente</span>
            <span style={styles.legendItem}>🔴 Vencido</span>
            <span style={styles.legendItem}>⚫ Sin CXC</span>
          </div>
        </>
      )}
    </div>
  );
}
