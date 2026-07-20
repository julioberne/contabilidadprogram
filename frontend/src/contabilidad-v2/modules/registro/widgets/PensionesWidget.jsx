// ============================================================
// PensionesWidget.jsx — Generador Masivo de Pensiones
// Genera CXC mensuales para todos los estudiantes del jardín
// Detecta duplicados, muestra progreso en tiempo real
// ============================================================
import React, { useState, useEffect, useCallback } from 'react';
import { API } from '../../../../config';

// Colores del widget — acento ámbar
const C = {
  bg:       '#0a0a14',
  surface:  '#111122',
  border:   '#ff8f00',
  accent:   '#ff8f00',
  dimAmber: '#ff8f0022',
  green:    '#00ff41',
  red:      '#ff3333',
  text:     '#e0e0e0',
  muted:    '#666680',
};

const FONT = {
  fontFamily: "'IBM Plex Mono', monospace",
  textTransform: 'uppercase',
  letterSpacing: '1.5px',
};

export default function PensionesWidget({ config, template, activeCompany, activePortfolio, onTransactionCreated }) {
  const [terceros, setTerceros] = useState([]);
  const [cartera, setCartera] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Estado de generación
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [result, setResult] = useState(null);

  // Configuración de pensión
  const pensionAmount = template?.pension_config?.amount || template?.pension_config?.monto || 450000;
  const pensionConcept = template?.pension_config?.concept || 'PENSIÓN MENSUAL';

  // Fecha actual
  const now = new Date();
  const mesActual = now.getMonth();
  const anioActual = now.getFullYear();
  const nombreMes = now.toLocaleString('es-CO', { month: 'long' });

  // Cargar datos
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

      setTerceros(Array.isArray(dataTerceros) ? dataTerceros : []);

      // Filtrar CXC del mes actual
      const cxcMes = (Array.isArray(dataCartera) ? dataCartera : []).filter(c => {
        const fecha = new Date(c.created_at || c.fecha || c.date);
        return fecha.getMonth() === mesActual && fecha.getFullYear() === anioActual;
      });
      setCartera(cxcMes);
    } catch (err) {
      console.error('[PensionesWidget] Error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [activePortfolio, mesActual, anioActual]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Estudiantes que YA tienen CXC este mes
  const estudiantesConCxc = new Set(
    cartera.map(c => c.tercero_id || c.third_party_id).filter(Boolean)
  );

  // Estudiantes que NECESITAN CXC
  const estudiantesSinCxc = terceros.filter(t => !estudiantesConCxc.has(t.id));

  // Generar pensiones masivamente
  const handleGenerar = async () => {
    if (generating || estudiantesSinCxc.length === 0) return;

    setGenerating(true);
    setResult(null);
    const total = estudiantesSinCxc.length;
    setProgress({ current: 0, total });

    let creadas = 0;
    let errores = 0;

    for (let i = 0; i < estudiantesSinCxc.length; i++) {
      const estudiante = estudiantesSinCxc[i];
      try {
        const portfolioName = activePortfolio?.name || activePortfolio?.portfolio_name || '';
        const body = {
          portfolio: portfolioName,
          portfolio_id: activePortfolio?.id,
          tercero_id: estudiante.id,
          third_party_id: estudiante.id,
          tercero_nombre: estudiante.name || estudiante.nombre,
          type: 'CXC',
          concept: pensionConcept,
          description: `${pensionConcept} — ${nombreMes.toUpperCase()} ${anioActual}`,
          amount: pensionAmount,
          monto: pensionAmount,
          status: 'pendiente',
          due_date: new Date(anioActual, mesActual + 1, 5).toISOString().split('T')[0],
        };

        const res = await fetch(`${API}/cartera`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });

        if (res.ok) {
          creadas++;
        } else {
          errores++;
          console.warn(`[PensionesWidget] Error creando CXC para ${estudiante.name}:`, res.status);
        }
      } catch (err) {
        errores++;
        console.error(`[PensionesWidget] Error:`, err);
      }

      setProgress({ current: i + 1, total });
    }

    setResult({ creadas, errores, mes: nombreMes, anio: anioActual });
    setGenerating(false);

    // Recargar datos
    await fetchData();

    // Notificar al padre
    if (onTransactionCreated && creadas > 0) {
      onTransactionCreated({ type: 'pensiones_generadas', count: creadas });
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
    mesTag: {
      ...FONT,
      fontSize: '10px',
      padding: '4px 10px',
      background: C.dimAmber,
      border: `1px solid ${C.accent}`,
      color: C.accent,
    },
    infoGrid: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '12px',
      marginBottom: '16px',
    },
    infoCard: {
      padding: '14px',
      background: C.surface,
      border: `1px solid ${C.muted}33`,
    },
    infoLabel: {
      ...FONT,
      fontSize: '9px',
      color: C.muted,
      marginBottom: '4px',
    },
    infoValue: {
      ...FONT,
      fontSize: '18px',
      fontWeight: 700,
      color: C.text,
    },
    statusRow: {
      display: 'flex',
      justifyContent: 'space-between',
      padding: '10px 14px',
      marginBottom: '14px',
      background: C.surface,
      border: `1px solid ${C.muted}33`,
    },
    statusItem: {
      ...FONT,
      fontSize: '10px',
      color: C.muted,
    },
    statusVal: (color) => ({
      fontWeight: 700,
      color: color,
    }),
    button: (disabled) => ({
      ...FONT,
      width: '100%',
      padding: '14px',
      fontSize: '13px',
      fontWeight: 700,
      letterSpacing: '2px',
      background: disabled ? C.muted + '33' : C.accent,
      color: disabled ? C.muted : '#000',
      border: `2px solid ${disabled ? C.muted : C.accent}`,
      cursor: disabled ? 'not-allowed' : 'pointer',
      boxShadow: disabled ? 'none' : '3px 3px 0 #000',
      transition: 'all 0.15s ease',
    }),
    progressContainer: {
      marginBottom: '14px',
    },
    progressText: {
      ...FONT,
      fontSize: '11px',
      color: C.accent,
      marginBottom: '6px',
      textAlign: 'center',
    },
    progressBar: {
      height: '6px',
      background: C.surface,
      border: `1px solid ${C.muted}33`,
      overflow: 'hidden',
    },
    progressFill: (pct) => ({
      height: '100%',
      width: `${pct}%`,
      background: `linear-gradient(90deg, ${C.accent}, #ffcc00)`,
      transition: 'width 0.3s ease',
    }),
    resultBox: (ok) => ({
      ...FONT,
      padding: '14px',
      marginTop: '14px',
      fontSize: '11px',
      background: ok ? `${C.green}15` : `${C.red}15`,
      border: `1px solid ${ok ? C.green : C.red}44`,
      color: ok ? C.green : C.red,
      textAlign: 'center',
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

  const pctProgress = progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : 0;

  return (
    <div style={styles.container}>
      {/* Encabezado */}
      <div style={styles.header}>
        <h3 style={styles.title}>🎓 Pensiones — Generador</h3>
        <span style={styles.mesTag}>{nombreMes} {anioActual}</span>
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
          {/* Info principal */}
          <div style={styles.infoGrid}>
            <div style={styles.infoCard}>
              <div style={styles.infoLabel}>Valor Pensión</div>
              <div style={{ ...styles.infoValue, color: C.accent }}>
                ${pensionAmount.toLocaleString('es-CO')}
              </div>
            </div>
            <div style={styles.infoCard}>
              <div style={styles.infoLabel}>Total Esperado</div>
              <div style={styles.infoValue}>
                ${(pensionAmount * terceros.length).toLocaleString('es-CO')}
              </div>
            </div>
          </div>

          {/* Estado actual */}
          <div style={styles.statusRow}>
            <span style={styles.statusItem}>
              Total estudiantes:{' '}
              <span style={styles.statusVal(C.text)}>{terceros.length}</span>
            </span>
            <span style={styles.statusItem}>
              Con CXC:{' '}
              <span style={styles.statusVal(C.green)}>{estudiantesConCxc.size}</span>
            </span>
            <span style={styles.statusItem}>
              Sin CXC:{' '}
              <span style={styles.statusVal(C.accent)}>{estudiantesSinCxc.length}</span>
            </span>
          </div>

          {/* Barra de progreso (solo durante generación) */}
          {generating && (
            <div style={styles.progressContainer}>
              <div style={styles.progressText}>
                ⚡ Generando... {progress.current}/{progress.total}
              </div>
              <div style={styles.progressBar}>
                <div style={styles.progressFill(pctProgress)} />
              </div>
            </div>
          )}

          {/* Botón de generación */}
          <button
            style={styles.button(generating || estudiantesSinCxc.length === 0)}
            disabled={generating || estudiantesSinCxc.length === 0}
            onClick={handleGenerar}
            onMouseEnter={(e) => {
              if (!generating && estudiantesSinCxc.length > 0) {
                e.currentTarget.style.transform = 'translate(-2px, -2px)';
                e.currentTarget.style.boxShadow = '5px 5px 0 #000';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'none';
              e.currentTarget.style.boxShadow = '3px 3px 0 #000';
            }}
          >
            {generating
              ? `⏳ Generando ${progress.current}/${progress.total}...`
              : estudiantesSinCxc.length === 0
                ? '✅ Todas las pensiones ya fueron generadas'
                : `🚀 Generar ${estudiantesSinCxc.length} Pensiones`
            }
          </button>

          {/* Resultado */}
          {result && (
            <div style={styles.resultBox(result.errores === 0)}>
              {result.errores === 0
                ? `✅ ${result.creadas} pensiones creadas para ${result.mes} ${result.anio}`
                : `⚠ ${result.creadas} creadas, ${result.errores} errores — ${result.mes} ${result.anio}`
              }
            </div>
          )}
        </>
      )}
    </div>
  );
}
