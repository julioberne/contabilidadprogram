/* ============================================================
   DashboardPanel.jsx — Lista compacta de empresas con balances
   v3: Reemplaza tabs grandes + KPI cards por una lista inline
   donde cada empresa muestra su balance. Sumatoria al final.
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import { API } from '../config';
const LS_KEY = 'finsys_dashboard_collapsed';

const fmt = (val) => {
  if (val === null || val === undefined || isNaN(val)) return '$0';
  return `$${Number(val).toLocaleString('es-CO', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
};

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
  const [balances, setBalances] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try { localStorage.setItem(LS_KEY, String(collapsed)); } catch {}
  }, [collapsed]);

  /* ── Cargar entities ────────────────────────────────────── */
  const fetchEntities = useCallback(async () => {
    try {
      const res = await fetch(`${API}/org/entities/selector`);
      if (!res.ok) throw new Error('fetch failed');
      setEntities(await res.json());
    } catch {
      try {
        const res2 = await fetch(`${API}/ct/entities`);
        if (res2.ok) setEntities(flattenTree(await res2.json()));
      } catch (_) {}
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchEntities(); }, [fetchEntities]);

  /* ── Cargar balances por empresa ─────────────────────────── */
  useEffect(() => {
    if (entities.length === 0) return;
    const names = [...new Set(entities.map(e => e.name))];
    Promise.allSettled(
      names.map(async (pName) => {
        try {
          const res = await fetch(`${API}/dashboard-data?portfolio=${encodeURIComponent(pName)}`);
          if (res.ok) {
            const d = await res.json();
            setBalances(prev => ({
              ...prev,
              [pName]: {
                ingresos: d.balance?.total_ingresos_cop ?? 0,
                gastos: d.balance?.total_gastos_cop ?? 0,
                balance: d.balance?.balance_neto_cop ?? 0,
                patrimonio: d.balance?.patrimonio_cop ?? 0,
              },
            }));
          }
        } catch (_) {}
      })
    );
  }, [entities]);

  /* ── Sumatoria ──────────────────────────────────────────── */
  const totals = Object.values(balances).reduce(
    (acc, b) => ({
      ingresos: acc.ingresos + (b.ingresos || 0),
      gastos: acc.gastos + (b.gastos || 0),
      balance: acc.balance + (b.balance || 0),
      patrimonio: acc.patrimonio + (b.patrimonio || 0),
    }),
    { ingresos: 0, gastos: 0, balance: 0, patrimonio: 0 }
  );

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
        <span style={{ flex: 1 }} />
        {/* Accesos rápidos inline */}
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
              <th style={{ ...S.th, textAlign: 'right' }}>INGRESOS</th>
              <th style={{ ...S.th, textAlign: 'right' }}>GASTOS</th>
              <th style={{ ...S.th, textAlign: 'right' }}>BALANCE</th>
              <th style={{ ...S.th, textAlign: 'right' }}>PATRIMONIO</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} style={{ ...S.td, textAlign: 'center', color: '#aaa' }}>Cargando...</td></tr>
            ) : (
              entities.map(entity => {
                const b = balances[entity.name] || {};
                const isActive = entity.id === activeCompany?.id;
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
                    <td style={{ ...S.td, fontWeight: isActive ? 700 : 400, whiteSpace: 'nowrap' }}>
                      {isActive && <span style={{ color: '#00c853', marginRight: 3 }}>●</span>}
                      <span style={{ fontSize: 10 }}>{TYPE_ICONS[entity.type] || '○'}</span>{' '}
                      {entity.name}
                      {entity.industry && entity.industry !== 'ESTANDAR' && (
                        <span style={{
                          fontSize: 7, background: '#1a1a2e', color: '#00ff41',
                          padding: '0 4px', marginLeft: 4, letterSpacing: 0.5, verticalAlign: 'middle',
                        }}>{entity.industry}</span>
                      )}
                    </td>
                    <td style={{ ...S.td, textAlign: 'right', color: '#00c853' }}>{fmt(b.ingresos)}</td>
                    <td style={{ ...S.td, textAlign: 'right', color: '#d50000' }}>{fmt(b.gastos)}</td>
                    <td style={{ ...S.td, textAlign: 'right', fontWeight: 700, color: (b.balance || 0) >= 0 ? '#00c853' : '#d50000' }}>{fmt(b.balance)}</td>
                    <td style={{ ...S.td, textAlign: 'right', color: '#ff8f00' }}>{fmt(b.patrimonio)}</td>
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
                <td style={{ ...S.td, textAlign: 'right', color: '#4ade80' }}>{fmt(totals.ingresos)}</td>
                <td style={{ ...S.td, textAlign: 'right', color: '#f87171' }}>{fmt(totals.gastos)}</td>
                <td style={{ ...S.td, textAlign: 'right', color: totals.balance >= 0 ? '#4ade80' : '#f87171' }}>{fmt(totals.balance)}</td>
                <td style={{ ...S.td, textAlign: 'right', color: '#fbbf24' }}>{fmt(totals.patrimonio)}</td>
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

function flattenTree(tree, level = 0) {
  const result = [];
  for (const node of (tree || [])) {
    result.push({
      id: node.id, name: node.name, type: node.type || 'EMPRESA',
      parent_id: node.parent_id, industry: node.industry || 'ESTANDAR',
      portfolio_id: node.portfolio_id, level,
    });
    if (node.children?.length) result.push(...flattenTree(node.children, level + 1));
  }
  return result;
}

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
