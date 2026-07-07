/* ============================================================
   HomeDashboard.jsx — Pantalla de inicio del Shell FIN-SYS OS
   Sección 1: KPIs en tiempo real
   Sección 2: Launchpad de módulos
   ============================================================ */
import { useState, useEffect } from 'react';
import { getLaunchpadModules } from '../registry/moduleRegistry';
import { API } from '../config';


/* ── Formateadores ───────────────────────────────────────── */
const fmt = (n) =>
  n == null ? '—' : new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP',
    maximumFractionDigits: 0,
  }).format(n);

const fmtNum = (n) => n == null ? '—' : Number(n).toLocaleString('es-CO');

/* ── Componente KPI card ─────────────────────────────────── */
function KpiCard({ label, value, sub, color = 'white', id }) {
  return (
    <div className="kpi-card" id={id}>
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value ${color}`}>{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

/* ── Componente Module card ──────────────────────────────── */
function ModuleCard({ mod, onNavigate }) {
  const borderClass = mod.active ? `module-card--${mod.accent}` : 'module-card--dim';

  return (
    <div
      className={`module-card ${borderClass}`}
      id={`home-module-${mod.id}`}
      onClick={() => mod.active && onNavigate(mod.id)}
      role={mod.active ? 'button' : undefined}
      tabIndex={mod.active ? 0 : undefined}
      onKeyDown={e => e.key === 'Enter' && mod.active && onNavigate(mod.id)}
    >
      <div className="module-card-icon">{mod.icon}</div>
      <div className="module-card-name">{mod.name}</div>
      <div className="module-card-desc">{mod.desc}</div>
      <div className={`module-card-status ${mod.active ? 'active' : 'soon'}`}>
        {mod.active ? '● ACTIVO' : '○ PRÓXIMO'}
        {mod.active && <span className="module-card-arrow">→</span>}
      </div>
    </div>
  );
}

/* ── Componente principal ────────────────────────────────── */
export default function HomeDashboard({ user, onNavigate, enabledIds }) {
  const [kpis,    setKpis]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [clock,   setClock]   = useState(new Date());

  // Reloj
  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  // Cargar KPIs reales
  useEffect(() => {
    const load = async () => {
      try {
        const [balRes, hrRes] = await Promise.allSettled([
          fetch(`${API}/portfolios/balance?portfolio=Negocio A`),
          fetch(`${API}/hr/employees/summary`),
        ]);

        const bal = balRes.status === 'fulfilled' && balRes.value.ok
          ? await balRes.value.json()
          : null;

        const hr = hrRes.status === 'fulfilled' && hrRes.value.ok
          ? await hrRes.value.json()
          : null;

        setKpis({ bal, hr });
      } catch (e) {
        setKpis({});
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const ingresos = kpis?.bal?.total_ingresos_cop ?? kpis?.bal?.total_ingresos ?? null;
  const gastos   = kpis?.bal?.total_gastos_cop   ?? kpis?.bal?.total_gastos   ?? null;
  const margen   = ingresos && gastos && ingresos > 0
    ? ((ingresos - gastos) / ingresos * 100).toFixed(1)
    : null;

  const empleados = kpis?.hr?.total ?? null;
  const alertas   = (kpis?.bal?.alerts ?? []).length;

  const fechaStr = clock.toLocaleDateString('es-CO', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
  const horaStr = clock.toLocaleTimeString('es-CO', {
    hour: '2-digit', minute: '2-digit',
  });

  return (
    <div className="home-wrap">
      {/* ── Encabezado ──────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <div style={{ fontSize: 10, letterSpacing: 3, color: 'var(--shell-dim)', textTransform: 'uppercase', marginBottom: 4 }}>
            BIENVENIDO
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: 1, color: 'var(--shell-text)' }}>
            {user?.name || 'Usuario'} <span style={{ color: 'var(--shell-green)' }}>_</span>
          </div>
          <div style={{ fontSize: 9, color: 'var(--shell-dim)', letterSpacing: 1, marginTop: 2 }}>
            {user?.role} · {user?.email}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--shell-text)', letterSpacing: 2 }}>
            {horaStr}
          </div>
          <div style={{ fontSize: 9, color: 'var(--shell-dim)', letterSpacing: 1 }}>
            {fechaStr}
          </div>
        </div>
      </div>

      {/* ── KPIs ────────────────────────────────── */}
      <div>
        <div className="home-section-header">
          <span className="home-section-title">INDICADORES EN TIEMPO REAL</span>
          <div className="home-section-line" />
          <span style={{ fontSize: 9, color: 'var(--shell-dim)', whiteSpace: 'nowrap' }}>
            {loading ? '● CARGANDO...' : '● LIVE'}
          </span>
        </div>
        <div className="home-kpis">
          <KpiCard
            id="kpi-ingresos"
            label="INGRESOS MES"
            value={loading ? '...' : fmt(ingresos)}
            sub={margen ? `Margen: ${margen}%` : 'Sin datos'}
            color="green"
          />
          <KpiCard
            id="kpi-gastos"
            label="GASTOS MES"
            value={loading ? '...' : fmt(gastos)}
            sub={ingresos && gastos ? `vs ingresos: ${((gastos/ingresos)*100).toFixed(0)}%` : '—'}
            color="white"
          />
          <KpiCard
            id="kpi-empleados"
            label="EMPLEADOS ACTIVOS"
            value={loading ? '...' : fmtNum(empleados)}
            sub="Módulo RRHH"
            color="white"
          />
          <KpiCard
            id="kpi-alertas"
            label="ALERTAS"
            value={loading ? '...' : alertas}
            sub={alertas > 0 ? 'Ver Contabilidad' : 'Sin alertas activas'}
            color={alertas > 0 ? 'amber' : 'white'}
          />
        </div>
      </div>

      {/* ── Módulos Launchpad ────────────────────── */}
      <div>
        <div className="home-section-header">
          <span className="home-section-title">MÓDULOS DEL SISTEMA</span>
          <div className="home-section-line" />
          <span style={{ fontSize: 9, color: 'var(--shell-green)', whiteSpace: 'nowrap' }}>
            3 ACTIVOS
          </span>
        </div>
        <div className="home-modules">
          {getLaunchpadModules(enabledIds).map(mod => (
            <ModuleCard key={mod.id} mod={mod} onNavigate={onNavigate} />
          ))}
        </div>
      </div>

      {/* ── Footer ──────────────────────────────── */}
      <div style={{
        marginTop: 'auto',
        paddingTop: 16,
        borderTop: '1px solid var(--shell-border)',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: 9,
        color: 'var(--shell-dim)',
        letterSpacing: 1,
      }}>
        <span>FIN-SYS OS v2.0 · ERP</span>
        <span>PostgreSQL 17 · FastAPI · React + Vite</span>
        <span>© 2026 FIN-SYS</span>
      </div>
    </div>
  );
}
