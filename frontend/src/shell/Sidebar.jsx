/* ============================================================
   Sidebar.jsx — Barra lateral unificada del Shell FIN-SYS OS
   Grupos: INICIO · FINANCIERO · GESTIÓN · OPERACIONES · SISTEMA
   ============================================================ */
import { useState } from 'react';
import { getNavGroups } from '../registry/moduleRegistry';
import { usePathname } from './useRoute';


/* ── Mapa de acento → clase CSS activa ───────────────────── */
const ACTIVE_CLASS = {
  green: 'active',
  amber: 'active-amber',
  blue:  'active-blue',
};

/* ── Sub-ítems plegados (▸), recordados por navegador ────── */
const CLAVE_PLEGADOS = 'finsys.nav.plegados';

function leerPlegados() {
  try { return new Set(JSON.parse(localStorage.getItem(CLAVE_PLEGADOS) || '[]')); }
  catch { return new Set(); }
}

const enSubRuta = (path, sub) => path === sub.path || path.startsWith(`${sub.path}/`);

/* ── Componente ──────────────────────────────────────────── */
export default function Sidebar({ user, activeView, onNavigate, collapsed, onToggle, mobileOpen, enabledIds }) {
  const path = usePathname();
  const [plegados, setPlegados] = useState(leerPlegados);

  const alternarSub = (id) => setPlegados(prev => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    try { localStorage.setItem(CLAVE_PLEGADOS, JSON.stringify([...next])); } catch { /* sin storage */ }
    return next;
  });

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
              const subs = !item.soon && item.sub?.length ? item.sub : null;
              const subActivo = isActive && subs?.some(s => enSubRuta(path, s));
              const abierto = subs && !plegados.has(item.id);
              const cls = [
                'shell-nav-item',
                isActive && !subActivo ? ACTIVE_CLASS[item.accent] : '',
                item.soon ? 'dim' : '',
              ].filter(Boolean).join(' ');

              const boton = (
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
              if (!subs) return boton;

              return (
                <div key={item.id}>
                  <div className="shell-nav-row">
                    {boton}
                    <button
                      type="button"
                      className="shell-nav-caret"
                      id={`shell-nav-${item.id}-caret`}
                      onClick={() => alternarSub(item.id)}
                      aria-expanded={abierto}
                      title={abierto ? `Plegar ${item.label}` : `Desplegar ${item.label}`}
                    >
                      {abierto ? '▾' : '▸'}
                    </button>
                  </div>
                  {abierto && subs.map(s => (
                    <button
                      key={s.id}
                      id={`shell-nav-${item.id}-${s.id}`}
                      className={[
                        'shell-nav-item', 'shell-nav-sub',
                        isActive && enSubRuta(path, s) ? ACTIVE_CLASS[item.accent] : '',
                      ].filter(Boolean).join(' ')}
                      onClick={() => onNavigate(item.id, { path: s.path })}
                      title={collapsed ? `${item.label} · ${s.label}` : undefined}
                    >
                      <span className="shell-nav-icon">{s.icon}</span>
                      <span className="shell-nav-text">{s.label}</span>
                    </button>
                  ))}
                </div>
              );
            })}
          </div>
        ))}
      </nav>

      {/* ── Zona ADMIN (solo OWNER/ADMIN) — fija en el footer ── */}
      {user && (user.role === 'OWNER' || user.role === 'ADMIN') && (
        <div style={{
          padding: '4px 8px',
          borderTop: '1px solid var(--shell-border, #222)',
        }}>
          <button
            id="shell-nav-admin"
            className={`shell-nav-item${activeView === 'admin' ? ' active-amber' : ''}`}
            onClick={() => onNavigate('admin')}
            title={collapsed ? 'Administración' : undefined}
            style={{ width: '100%' }}
          >
            <span className="shell-nav-icon">▣</span>
            <span className="shell-nav-text">Administración</span>
          </button>
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
