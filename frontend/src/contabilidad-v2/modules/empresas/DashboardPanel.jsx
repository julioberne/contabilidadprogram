/* ============================================================
   DashboardPanel.jsx — Lista compacta de empresas con balances
   v3: Reemplaza tabs grandes + KPI cards por una lista inline
   donde cada empresa muestra su balance. Sumatoria al final.
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../../config';
import { flattenTree } from './flattenTree.js';
const LS_KEY = 'finsys_dashboard_collapsed';

/* Moneda con decimales, formato colombiano: $1.234.567,89
   Antes se truncaba a 0 decimales, así que los centavos desaparecían de la
   vista aunque el libro diario sí los mostraba. */
const fmt = (val) => {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return `$${Number(val).toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

/* Una empresa sin portafolio contable vinculado no tiene cifras. Mostrar $0
   mentiría (se lee como "no facturó"); esto dice la verdad. */
const SIN_VINCULAR = '—';

const TYPE_ICONS = { HOLDING: '🏛️', EMPRESA: '🏢', SUB_EMPRESA: '📍', PROYECTO: '📐', TAREA: '📋' };

export default function DashboardPanel({
  cajaViva = {},
  activeCompany = null,
  activePortfolio = '',
  onQuickAction,
  onSelectCompany,
  onCompaniesChanged,
  industryKpis = [],
  industryData = {},
}) {
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(LS_KEY) === 'true'; } catch { return false; }
  });
  const [entities, setEntities] = useState([]);
  const [totals, setTotals] = useState({ ingresos: 0, gastos: 0, balance: 0 });
  const [unlinkedCount, setUnlinkedCount] = useState(0);
  const [portfolios, setPortfolios] = useState([]);
  const [linking, setLinking] = useState(null);   // id de la entidad guardando
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try { localStorage.setItem(LS_KEY, String(collapsed)); } catch {}
  }, [collapsed]);

  /* ── Consolidado real, en UNA sola llamada ─────────────────
     Antes esto eran N peticiones a /dashboard-data?portfolio=<nombre-de-la-
     entidad>. El nombre de una entidad no es el nombre de un portafolio
     contable, así que la API respondía 200 con ceros + el patrimonio GLOBAL:
     cada fila mostraba el mismo número y el total lo multiplicaba por N
     (6 empresas × $2.100.000 = "$12.600.000" que no existía).
     Ahora el backend resuelve el vínculo por entities.portfolio_id, suma cada
     portafolio una sola vez y marca como no vinculadas las que no tienen. */
  const fetchConsolidated = useCallback(async () => {
    try {
      const res = await fetch(`${API}/org/consolidated`);
      if (!res.ok) throw new Error('fetch failed');
      const d = await res.json();
      setEntities(d.entities || []);
      setTotals(d.totals || { ingresos: 0, gastos: 0, balance: 0 });
      setUnlinkedCount(d.unlinked_count || 0);
      setPortfolios(d.portfolios || []);
    } catch {
      // Fallback: al menos listar las empresas, sin cifras inventadas
      try {
        const res2 = await fetch(`${API}/org/entities/selector`);
        if (res2.ok) setEntities(await res2.json());
        else {
          const res3 = await fetch(`${API}/ct/entities`);
          if (res3.ok) setEntities(flattenTree(await res3.json()));
        }
      } catch (_) {}
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchConsolidated(); }, [fetchConsolidated]);

  /* ── Vincular / desvincular empresa ↔ portafolio ───────────
     Se edita desde la propia fila: es donde el usuario ve el problema.
     portfolio_id null = desvincular (el backend acepta el null explícito). */
  const handleLink = useCallback(async (entityId, value) => {
    setLinking(entityId);
    try {
      const res = await fetch(`${API}/org/entities/${entityId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio_id: value ? Number(value) : null }),
      });
      if (!res.ok) throw new Error('No se pudo guardar el vínculo');
      await fetchConsolidated();   // recalcula cifras y agregados del árbol
      onCompaniesChanged?.();
    } catch (e) {
      alert(e.message || 'No se pudo guardar el vínculo.');
    } finally {
      setLinking(null);
    }
  }, [fetchConsolidated, onCompaniesChanged]);

  /* ── Crear portafolio contable nuevo ───────────────────────
     Cada portafolio es un libro contable independiente (cuentas, COA,
     transacciones propias); las empresas se vinculan a uno desde su fila. */
  const handleCreatePortfolio = useCallback(async () => {
    const name = window.prompt('Nombre del nuevo portafolio contable:\n(cada portafolio es un libro independiente — luego vincúlalo a una empresa desde su fila)');
    if (!name || !name.trim()) return;
    try {
      const res = await fetch(`${API}/portfolios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), industry_type: 'ESTANDAR' }),
      });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(d.detail || 'No se pudo crear el portafolio');
      await fetchConsolidated();       // el dropdown de vínculos lo muestra ya
      onCompaniesChanged?.();
      alert(`✅ Portafolio "${name.trim()}" creado. Vincúlalo a una empresa en la columna PORTAFOLIO.`);
    } catch (e) {
      alert(e.message || 'No se pudo crear el portafolio.');
    }
  }, [fetchConsolidated, onCompaniesChanged]);

  /* ── Jerarquía colapsable: padre ▸ hijo ▸ proyecto ▸ tarea ──
     Las entidades llegan ordenadas jerárquicamente con parent_id + level;
     colapsar un padre oculta TODO su subárbol. */
  const [collapsedIds, setCollapsedIds] = useState(new Set());
  const toggleCollapse = (id) => setCollapsedIds(prev => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });
  const conHijos = new Set(entities.filter(e =>
    entities.some(h => h.parent_id === e.id)).map(e => e.id));
  const ocultos = new Set();
  const ocultarDescendientes = (pid) => entities
    .filter(e => e.parent_id === pid)
    .forEach(e => { ocultos.add(e.id); ocultarDescendientes(e.id); });
  collapsedIds.forEach(id => ocultarDescendientes(id));
  const entidadesVisibles = entities.filter(e => !ocultos.has(e.id));

  const industryLabel = activeCompany?.industry && activeCompany.industry !== 'ESTANDAR'
    ? activeCompany.industry : null;

  /* ── Colapsado: una sola línea ──────────────────────────── */
  if (collapsed) {
    return (
      <div onClick={() => setCollapsed(false)} style={{ ...S.container, cursor: 'pointer', padding: '3px 8px' }} title="Expandir">
        <span style={S.headerLabel}>▶ DASHBOARD</span>
        <span style={{ fontSize: 9, fontWeight: 700 }}>{activeCompany?.name || activePortfolio}</span>
        <span style={{ flex: 1 }} />
        <Chip label="BAL" value={fmt(cajaViva.balance_neto_cop)} color={cajaViva.balance_neto_cop >= 0 ? '#00c853' : '#d50000'} />
        <Chip label="PAT" value={fmt(cajaViva.patrimonio_cop)} color="#ff8f00" />
        <Chip label="∑" value={fmt(totals.balance)} color="#6366f1" />
      </div>
    );
  }

  /* ── Expandido: lista de empresas + accesos rápidos ──────── */
  return (
    <div style={S.container}>
      {/* Header */}
      <div style={S.header}>
        <span style={S.headerLabel}>▼ CONSOLIDADO · {entities.length} EMPRESAS</span>
        {unlinkedCount > 0 && (
          <span
            style={{ fontSize: 8, color: '#b45309', background: '#fef3c7', border: '1px solid #fbbf24', padding: '0 4px', letterSpacing: 0.5 }}
            title="Estas empresas no tienen un portafolio contable vinculado, así que no aportan cifras al consolidado."
          >
            {unlinkedCount} SIN VINCULAR
          </span>
        )}
        {/* La contabilidad activa: los módulos de abajo (registro, libro,
            pulso de cuentas) trabajan sobre ESTE portafolio */}
        <span
          style={{ fontSize: 8, color: '#166534', background: '#dcfce7', border: '1px solid #4ade80', padding: '0 4px', letterSpacing: 0.5, fontWeight: 700 }}
          title="Portafolio contable sobre el que trabajan el registro, el libro diario y el pulso de cuentas. Cambia seleccionando una empresa vinculada."
        >
          ▸ TRABAJANDO EN: {activePortfolio || '—'}
        </span>
        <span style={{ flex: 1 }} />
        {/* Accesos rápidos inline */}
        <QBtn label="＋ Portafolio" onClick={handleCreatePortfolio} />
        <QBtn label="📝 Registro" onClick={() => onQuickAction?.('registro')} />
        <QBtn label="👤 Tercero" onClick={() => onQuickAction?.('tercero')} />
        <QBtn label="📦 Recurso" onClick={() => onQuickAction?.('recurso')} />
        <button onClick={() => setCollapsed(true)} style={S.collapseBtn} title="Colapsar">▲</button>
      </div>

      {/* Lista de empresas con balances */}
      <div style={{ maxHeight: 220, overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
              <th style={S.th}>EMPRESA</th>
              <th style={S.th}>PORTAFOLIO</th>
              <th style={{ ...S.th, textAlign: 'right' }}>INGRESOS</th>
              <th style={{ ...S.th, textAlign: 'right' }}>GASTOS</th>
              <th style={{ ...S.th, textAlign: 'right' }}>BALANCE</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} style={{ ...S.td, textAlign: 'center', color: '#aaa' }}>Cargando...</td></tr>
            ) : (
              entidadesVisibles.map(entity => {
                const linked = entity.linked;              // vínculo propio
                const hasFigures = entity.has_figures;     // propio + hijas
                const isActive = entity.id === activeCompany?.id;
                const esPadre = conHijos.has(entity.id);
                const colapsado = collapsedIds.has(entity.id);
                return (
                  <tr
                    key={entity.id}
                    onClick={() => onSelectCompany?.(entity)}
                    style={{
                      borderBottom: '1px solid #eee',
                      background: isActive ? '#e8ffe8' : 'transparent',
                      cursor: 'pointer',
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = '#f8f8f8'; }}
                    onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
                  >
                    <td style={{ ...S.td, fontWeight: isActive ? 700 : 400, whiteSpace: 'nowrap',
                                 paddingLeft: 8 + (entity.level || 0) * 14 }}>
                      {esPadre ? (
                        <button
                          onClick={(e) => { e.stopPropagation(); toggleCollapse(entity.id); }}
                          title={colapsado ? 'Expandir subárbol' : 'Colapsar subárbol'}
                          style={{ border: '1px solid #000', background: colapsado ? '#000' : '#fff',
                                   color: colapsado ? '#fff' : '#000', cursor: 'pointer',
                                   fontSize: 10, fontWeight: 700, width: 18, height: 16,
                                   lineHeight: '13px', textAlign: 'center', padding: 0,
                                   marginRight: 4, verticalAlign: 'middle' }}
                        >{colapsado ? '▸' : '▾'}</button>
                      ) : (
                        <span style={{ display: 'inline-block', width: 22 }} />
                      )}
                      {isActive && <span style={{ color: '#00c853', marginRight: 3 }}>●</span>}
                      <span style={{ fontSize: 10 }}>{TYPE_ICONS[entity.type] || '○'}</span>{' '}
                      {entity.name}
                      {esPadre && colapsado && (
                        <span style={{ fontSize: 7, color: '#6366f1', marginLeft: 4 }}
                              title="Subárbol colapsado">
                          +{entities.filter(e => { let p = e; while (p.parent_id != null) { if (p.parent_id === entity.id) return true; p = entities.find(x => x.id === p.parent_id) || {}; } return false; }).length}
                        </span>
                      )}
                      {entity.industry && entity.industry !== 'ESTANDAR' && (
                        <span style={{
                          fontSize: 7, background: '#1a1a2e', color: '#00ff41',
                          padding: '0 4px', marginLeft: 4, letterSpacing: 0.5, verticalAlign: 'middle',
                        }}>{entity.industry}</span>
                      )}
                    </td>
                    <td style={{ ...S.td, whiteSpace: 'nowrap' }} onClick={e => e.stopPropagation()}>
                      <select
                        value={entity.portfolio_id ?? ''}
                        disabled={linking === entity.id}
                        onChange={e => handleLink(entity.id, e.target.value)}
                        title={linked
                          ? `Contabilidad de: ${entity.portfolio_name}`
                          : 'Sin portafolio contable. Elige uno para que esta empresa aporte cifras.'}
                        style={{
                          fontFamily: '"IBM Plex Mono", monospace', fontSize: 9,
                          padding: '1px 2px', maxWidth: 140,
                          border: `1px solid ${linked ? '#ccc' : '#fbbf24'}`,
                          background: linked ? '#fff' : '#fffbeb',
                          color: linked ? '#333' : '#b45309',
                          cursor: linking === entity.id ? 'wait' : 'pointer',
                        }}
                      >
                        <option value="">— sin vincular —</option>
                        {portfolios.map(p => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                      </select>
                    </td>
                    <td style={{ ...S.td, textAlign: 'right', color: hasFigures ? '#00c853' : '#ccc' }}>{hasFigures ? fmt(entity.ingresos) : SIN_VINCULAR}</td>
                    <td style={{ ...S.td, textAlign: 'right', color: hasFigures ? '#d50000' : '#ccc' }}>{hasFigures ? fmt(entity.gastos) : SIN_VINCULAR}</td>
                    <td style={{ ...S.td, textAlign: 'right', fontWeight: 700, color: !hasFigures ? '#ccc' : (entity.balance || 0) >= 0 ? '#00c853' : '#d50000' }}>
                      {hasFigures ? fmt(entity.balance) : SIN_VINCULAR}
                      {entity.aggregated && (
                        <span
                          style={{ fontSize: 7, color: '#6366f1', marginLeft: 3, verticalAlign: 'super' }}
                          title={`Incluye ${entity.scope_count} portafolio(s) de esta empresa y sus dependientes.`}
                        >∑</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
          {/* Fila de TOTAL */}
          {!loading && entities.length > 0 && (
            <tfoot>
              <tr style={{ borderTop: '2px solid #000', background: '#0a0a14', color: '#fff', fontWeight: 700 }}>
                <td style={{ ...S.td, letterSpacing: 2, fontSize: 9 }}>∑ TOTAL CONSOLIDADO</td>
                {/* Cada portafolio cuenta una sola vez aunque varias empresas
                    apunten al mismo — antes se sumaba fila por fila. */}
                <td style={{ ...S.td, fontSize: 8, color: '#888' }}>{entities.length - unlinkedCount} vinculada(s)</td>
                <td style={{ ...S.td, textAlign: 'right', color: '#4ade80' }}>{fmt(totals.ingresos)}</td>
                <td style={{ ...S.td, textAlign: 'right', color: '#f87171' }}>{fmt(totals.gastos)}</td>
                <td style={{ ...S.td, textAlign: 'right', color: totals.balance >= 0 ? '#4ade80' : '#f87171' }}>{fmt(totals.balance)}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}

/* ── Sub-componentes ─────────────────────────────────────── */

function Chip({ label, value, color }) {
  return (
    <span style={{ fontSize: 9, display: 'inline-flex', gap: 3, alignItems: 'center', marginLeft: 6 }}>
      <span style={{ color: '#999', fontWeight: 700 }}>{label}</span>
      <span style={{ color, fontWeight: 700 }}>{value}</span>
    </span>
  );
}

function QBtn({ label, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        fontFamily: '"IBM Plex Mono", monospace', fontSize: 8,
        padding: '1px 6px', border: '1px solid #ccc', background: '#f8f8f8',
        color: '#555', cursor: 'pointer', letterSpacing: 0.5, marginLeft: 2,
        transition: 'all 0.15s',
      }}
      onMouseEnter={e => { e.target.style.background = '#000'; e.target.style.color = '#fff'; }}
      onMouseLeave={e => { e.target.style.background = '#f8f8f8'; e.target.style.color = '#555'; }}
    >
      {label}
    </button>
  );
}

/* flattenTree ahora vive en ./flattenTree.js (compartido con CompanySelector) */

/* ── Estilos ─────────────────────────────────────────────── */

const S = {
  container: {
    border: '2px solid #000', background: '#fff', marginBottom: 8,
    fontFamily: '"IBM Plex Mono", monospace', boxShadow: '3px 3px 0 #000',
    display: 'flex', flexDirection: 'column',
  },
  header: {
    display: 'flex', alignItems: 'center', gap: 4,
    padding: '3px 8px', borderBottom: '1px solid #ddd', background: '#fafafa',
  },
  headerLabel: {
    fontSize: 9, fontWeight: 700, letterSpacing: 2, color: '#888', textTransform: 'uppercase',
  },
  collapseBtn: {
    fontFamily: '"IBM Plex Mono", monospace', fontSize: 9,
    padding: '1px 6px', border: '1px solid #ccc', background: '#f0f0f0',
    color: '#888', cursor: 'pointer', marginLeft: 4,
  },
  th: {
    padding: '3px 8px', fontSize: 8, fontWeight: 700, letterSpacing: 1.5,
    textTransform: 'uppercase', textAlign: 'left', color: '#888',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  td: {
    padding: '3px 8px', fontSize: 10, fontFamily: '"IBM Plex Mono", monospace',
  },
};
