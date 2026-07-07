/* ============================================================
   Sidebar.jsx — Barra lateral unificada del Shell FIN-SYS OS
   Grupos: INICIO · FINANCIERO · GESTIÓN · OPERACIONES · SISTEMA
   ============================================================ */
import { useState, useEffect } from 'react';
import { getNavGroups } from '../registry/moduleRegistry';


/* ── Mapa de acento → clase CSS activa ───────────────────── */
const ACTIVE_CLASS = {
  green: 'active',
  amber: 'active-amber',
  blue:  'active-blue',
};

/* ── Componente ──────────────────────────────────────────── */
export default function Sidebar({ user, activeView, onNavigate, collapsed, onToggle, mobileOpen, enabledIds }) {
  const [clock, setClock] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 60000);
    return () => clearInterval(t);
  }, []);

  const sidebarClass = [
    'shell-sidebar',
    collapsed ? 'collapsed' : '',
    mobileOpen ? 'mobile-open' : '',
  ].filter(Boolean).join(' ');

  return (
    <aside className={sidebarClass} id="shell-sidebar">
      {/* ── Toggle collapse ──────────────────────── */}
      <button
        className="shell-collapse-btn"
        onClick={onToggle}
        title={collapsed ? 'Expandir' : 'Colapsar'}
        id="shell-sidebar-toggle"
      >
        {collapsed ? '▶' : '◀'}
      </button>

      {/* ── Brand ────────────────────────────────── */}
      <div className="shell-brand">
        <span className="shell-brand-icon">▣</span>
        <div className="shell-brand-text">
          <div className="shell-brand-name">FIN-SYS OS</div>
          <div className="shell-brand-ver">v2.0 · ERP</div>
        </div>
      </div>

      {/* ── Company selector ─────────────────────── */}
      {!collapsed && (
        <div className="shell-company">
          <button className="shell-company-btn" id="shell-company-selector">
            HOLDING PRINCIPAL <span>▾</span>
          </button>
        </div>
      )}

      {/* ── Navigation ───────────────────────────── */}
      <nav className="shell-nav" id="shell-nav">
        {getNavGroups(enabledIds).map(({ group, items }) => (
          <div className="shell-nav-group" key={group}>
            <div className="shell-nav-label">{group}</div>
            {items.map(item => {
              const isActive = activeView === item.id;
              const cls = [
                'shell-nav-item',
                isActive ? ACTIVE_CLASS[item.accent] : '',
                item.soon ? 'dim' : '',
              ].filter(Boolean).join(' ');

              return (
                <button
                  key={item.id}
                  id={`shell-nav-${item.id}`}
                  className={cls}
                  onClick={() => !item.soon && onNavigate(item.id)}
                  title={collapsed ? item.label : undefined}
                >
                  <span className="shell-nav-icon">{item.icon}</span>
                  <span className="shell-nav-text">{item.label}</span>
                  {item.soon && !collapsed && (
                    <span className="shell-nav-badge">PRÓX</span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* ── Settings (solo OWNER/ADMIN) — fijo en el footer ── */}
      {user && (user.role === 'OWNER' || user.role === 'ADMIN') && (
        <div style={{
          padding: '4px 8px',
          borderTop: '1px solid var(--shell-border, #222)',
        }}>
          <button
            id="shell-nav-module-settings"
            className={`shell-nav-item${activeView === 'module-settings' ? ' active' : ''}`}
            onClick={() => onNavigate('module-settings')}
            title={collapsed ? 'Módulos' : undefined}
            style={{ width: '100%' }}
          >
            <span className="shell-nav-icon">⚙</span>
            <span className="shell-nav-text">Módulos</span>
          </button>
        </div>
      )}

      {/* ── User footer ──────────────────────────── */}
      {user && (
        <div className="shell-user">
          <div className="shell-user-avatar">{user.initials || 'U'}</div>
          {!collapsed && (
            <div className="shell-user-info">
              <div className="shell-user-email">{user.email}</div>
              <div className="shell-user-role">{user.role}</div>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
