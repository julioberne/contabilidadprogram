/* ============================================================
   main.jsx — FIN-SYS OS v2.0 · Shell Unificado
   Zero-Impact Policy: App.jsx, ControlTowerApp, ProjectHubApp
   no se modifican. Solo se envuelven en el nuevo shell.
   ============================================================ */
import { useState, useEffect, lazy, Suspense } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import './shell/shell.css';

// SOL-06: Módulos cargados bajo demanda (code splitting)
const App             = lazy(() => import('./App.jsx'));
const ControlTowerApp = lazy(() => import('./control-tower/ControlTowerApp.jsx'));
const ProjectHubApp   = lazy(() => import('./project-hub/ProjectHubApp.jsx'));

// Shell nuevo (siempre cargado — es ligero)
import GlobalLogin    from './shell/GlobalLogin.jsx';
import Sidebar        from './shell/Sidebar.jsx';
import HomeDashboard  from './shell/HomeDashboard.jsx';
import { useGlobalSession } from './shell/hooks/useGlobalSession.js';

const MOBILE_BP = 900;

function FINSYSShell() {
  const { user, loading, error, login, logout } = useGlobalSession();
  const [view,        setView]        = useState('home');
  const [collapsed,   setCollapsed]   = useState(false);
  const [mobileOpen,  setMobileOpen]  = useState(false);
  const [isMobile,    setIsMobile]    = useState(window.innerWidth < MOBILE_BP);

  useEffect(() => {
    const handler = () => {
      const m = window.innerWidth < MOBILE_BP;
      setIsMobile(m);
      if (!m) setMobileOpen(false);
    };
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  // ── Login global ──────────────────────────────────────────
  if (!user) {
    return (
      <GlobalLogin
        onLogin={login}
        loading={loading}
        error={error}
      />
    );
  }

  // ── Etiqueta del módulo activo (breadcrumb) ───────────────
  const MODULE_LABELS = {
    home:         'Dashboard Ejecutivo',
    contabilidad: 'Contabilidad',
    rrhh:         'Recursos Humanos',
    tower:        'Control Tower',
    tesoreria:    'Tesorería',
    facturacion:  'Facturación',
    organigrama:  'Organigrama',
    ventas:       'Ventas & CRM',
    compras:      'Compras',
    logistica:    'Logística',
    bot:          'Bot IA',
    config:       'Configuración',
    auditoria:    'Auditoría',
  };

  // Módulos que usan pantalla completa (sin topbar del shell)
  const FULLSCREEN = ['tower', 'rrhh'];
  const isFullscreen = FULLSCREEN.includes(view);

  // Módulos que necesitan overflow: hidden en el contenedor
  // NOTA: 'contabilidad' necesita scroll propio — NO incluir aquí
  const NO_SCROLL = ['tower', 'rrhh'];
  const noScroll  = NO_SCROLL.includes(view);

  const now = new Date();
  const dateLabel = now.toLocaleDateString('es-CO', {
    day: '2-digit', month: 'short', year: 'numeric',
  }) + ' · ' + now.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="shell-root">
      {/* ── Sidebar ─────────────────────────────── */}
      <Sidebar
        user={user}
        activeView={view}
        onNavigate={(v) => { setView(v); isMobile && setMobileOpen(false); }}
        collapsed={isMobile ? false : collapsed}
        onToggle={() => isMobile ? setMobileOpen(v => !v) : setCollapsed(v => !v)}
        mobileOpen={mobileOpen}
      />

      {/* Mobile overlay */}
      {isMobile && mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(0,0,0,0.7)',
            zIndex: 199,
          }}
        />
      )}

      {/* ── Main area ───────────────────────────── */}
      <div className="shell-main">
        {/* Topbar — siempre visible excepto en fullscreen puro */}
        <div className="shell-topbar" id="shell-topbar">
          {/* Hamburger en mobile */}
          {isMobile && (
            <button
              id="shell-hamburger"
              onClick={() => setMobileOpen(v => !v)}
              style={{
                background: 'transparent', border: 'none',
                color: 'var(--shell-text)', fontSize: 18,
                cursor: 'pointer', marginRight: 12,
                fontFamily: 'var(--shell-font)',
              }}
            >☰</button>
          )}

          <div className="shell-breadcrumb">
            HOME <span>› {MODULE_LABELS[view] || view.toUpperCase()}</span>
          </div>

          <div className="shell-topbar-right">
            <span className="shell-datetime">{dateLabel}</span>
            <button
              id="shell-logout-btn"
              onClick={logout}
              style={{
                background: 'transparent',
                border: '1px solid var(--shell-border-hi)',
                color: 'var(--shell-dim)',
                fontFamily: 'var(--shell-font)',
                fontSize: 9,
                letterSpacing: 1,
                padding: '4px 8px',
                cursor: 'pointer',
                textTransform: 'uppercase',
              }}
            >
              → SALIR
            </button>
          </div>
        </div>

        {/* ── Contenido del módulo activo ─────────── */}
        <div
          className={`shell-content${noScroll ? ' no-scroll' : ''}`}
          id="shell-content"
        >
          {view === 'home' && (
            <HomeDashboard user={user} onNavigate={setView} />
          )}

          <Suspense fallback={
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              height: '100%', fontFamily: 'var(--shell-font, "IBM Plex Mono", monospace)',
              color: 'var(--shell-dim, #888)', fontSize: 11, letterSpacing: 2,
              textTransform: 'uppercase',
            }}>
              ▓ CARGANDO MÓDULO...
            </div>
          }>
            {view === 'contabilidad' && (
              <div style={{ minHeight: '100%', width: '100%' }}>
                <App />
              </div>
            )}

            {view === 'rrhh' && (
              <div style={{ height: '100%', position: 'relative', overflow: 'hidden' }}>
                <ProjectHubApp
                  onExit={() => setView('home')}
                  embeddedMode
                />
              </div>
            )}

            {view === 'tower' && (
              <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <ControlTowerApp
                  onGoBack={() => setView('home')}
                  embeddedMode
                />
              </div>
            )}
          </Suspense>
        </div>
      </div>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<FINSYSShell />);

