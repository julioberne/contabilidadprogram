/* ============================================================
   main.jsx — FIN-SYS OS v2.0 · Shell Unificado
   Módulos definidos en registry/moduleRegistry.js (SSOT).
   ============================================================ */
import { useState, useEffect, Suspense, useCallback } from 'react';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import { createRoot } from 'react-dom/client';
import './index.css';
import './shell/shell.css';
import { getModuleLabels, getNoScrollIds, getRenderableModules, applyFlags } from './registry/moduleRegistry';
import { API } from './config';
import ModuleSettingsPanel from './shell/ModuleSettingsPanel.jsx';

// Shell nuevo (siempre cargado — es ligero)
import GlobalLogin    from './shell/GlobalLogin.jsx';
import Sidebar        from './shell/Sidebar.jsx';
import HomeDashboard  from './shell/HomeDashboard.jsx';
import GlobalHeader   from './shell/GlobalHeader.jsx';
import { UserProvider }         from './shell/providers/UserProvider.jsx';
import { NotificationProvider } from './shell/providers/NotificationProvider.jsx';
import { useGlobalSession } from './shell/hooks/useGlobalSession.js';

const MOBILE_BP = 900;

function FINSYSShell() {
  const { user, loading, error, login, logout } = useGlobalSession();
  const [view,        setView]        = useState('home');
  const [collapsed,   setCollapsed]   = useState(false);
  const [mobileOpen,  setMobileOpen]  = useState(false);
  const [isMobile,    setIsMobile]    = useState(window.innerWidth < MOBILE_BP);
  const [enabledIds,  setEnabledIds]  = useState(null); // Feature flags resueltos

  // ── Fetch Feature Flags ──────────────────────────────────
  const loadFlags = useCallback(async () => {
    try {
      const res = await fetch(`${API}/module-flags`);
      if (res.ok) {
        const data = await res.json();
        setEnabledIds(applyFlags(data.flags || []));
      }
    } catch {
      // Si no hay BD o falla, usar defaults del registry
      setEnabledIds(null);
    }
  }, []);

  useEffect(() => { if (user) loadFlags(); }, [user, loadFlags]);

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

  // ── Datos derivados del Module Registry (flag-aware) ────
  const MODULE_LABELS = getModuleLabels();
  const noScroll = getNoScrollIds().includes(view);
  const renderableModules = getRenderableModules(enabledIds);

  return (
    <UserProvider user={user} logout={logout}>
    <NotificationProvider>
    <div className="shell-root">
      {/* ── Sidebar ─────────────────────────────── */}
      <Sidebar
        user={user}
        activeView={view}
        onNavigate={(v) => { setView(v); isMobile && setMobileOpen(false); }}
        collapsed={isMobile ? false : collapsed}
        onToggle={() => isMobile ? setMobileOpen(v => !v) : setCollapsed(v => !v)}
        mobileOpen={mobileOpen}
        enabledIds={enabledIds}
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
        {/* Global Header — reemplaza el viejo topbar inline */}
        <GlobalHeader
          activeView={view}
          moduleLabels={MODULE_LABELS}
          onLogout={logout}
          isMobile={isMobile}
          onHamburger={() => setMobileOpen(v => !v)}
        />

        {/* ── Contenido del módulo activo ─────────── */}
        <div
          className={`shell-content${noScroll ? ' no-scroll' : ''}`}
          id="shell-content"
        >
          {view === 'home' && (
            <HomeDashboard user={user} onNavigate={setView} enabledIds={enabledIds} />
          )}

          {view === 'module-settings' && (
            <ModuleSettingsPanel onFlagsChanged={loadFlags} />
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
            {renderableModules.map(mod => {
              if (view !== mod.id) return null;
              const Comp = mod.component;
              const props = { user };
              // Resolver callbacks especiales del registry
              if (mod.extraProps) {
                Object.entries(mod.extraProps).forEach(([k, v]) => {
                  props[k] = v === '__SET_HOME__' ? () => setView('home') : v;
                });
              }
              return (
                <div style={mod.wrapStyle || {}} key={mod.id}>
                  <ErrorBoundary module={mod.label}>
                    <Comp {...props} />
                  </ErrorBoundary>
                </div>
              );
            })}
          </Suspense>
        </div>
      </div>
    </div>
    </NotificationProvider>
    </UserProvider>
  );
}

createRoot(document.getElementById('root')).render(<FINSYSShell />);

