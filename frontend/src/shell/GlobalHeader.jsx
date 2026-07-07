import { useState, useEffect, useRef, useCallback } from 'react';
import { useUser } from './providers/UserProvider.jsx';
import { useNotify } from './providers/NotificationProvider.jsx';

const TYPE_COLORS = { SUCCESS: '#00e676', INFO: '#4fc3f7', WARNING: '#FFB000', ERROR: '#c00' };

function relativeTime(isoStr) {
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'ahora';
  if (mins < 60) return `hace ${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `hace ${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return 'ayer';
  return `hace ${days}d`;
}

function formatClock() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

export function GlobalHeader({ activeView, moduleLabels, onLogout, isMobile, onHamburger }) {
  const { user } = useUser();
  const { notifications, unreadCount, markAllRead, clearAll, notify } = useNotify();

  const [clock, setClock] = useState(formatClock);
  const [notifOpen, setNotifOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const [prevView, setPrevView] = useState(activeView);

  const notifRef = useRef(null);
  const userRef = useRef(null);

  // ── Welcome notification on first mount ──
  useEffect(() => {
    if (user && notify) {
      notify(`Bienvenido, ${user.name || 'Usuario'}. Sesión activa.`, 'SUCCESS', 'sistema');
    }
  }, []); // Only on mount

  // ── Notify on module navigation ──
  useEffect(() => {
    if (activeView && activeView !== prevView && notify) {
      const label = (moduleLabels && moduleLabels[activeView]) || activeView;
      if (label && label !== 'HOME') {
        notify(`Navegando a ${label}`, 'INFO', 'shell');
      }
      setPrevView(activeView);
    }
  }, [activeView]);

  // Clock tick every 60s
  useEffect(() => {
    const id = setInterval(() => setClock(formatClock()), 60000);
    return () => clearInterval(id);
  }, []);

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClick(e) {
      if (notifOpen && notifRef.current && !notifRef.current.contains(e.target)) {
        setNotifOpen(false);
      }
      if (userOpen && userRef.current && !userRef.current.contains(e.target)) {
        setUserOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [notifOpen, userOpen]);

  const initials = user
    ? (user.name || user.email || '')
        .split(/[\s@]+/)
        .slice(0, 2)
        .map((w) => w[0] || '')
        .join('')
        .toUpperCase()
    : '??';

  const displayName = user?.name || user?.email || 'USUARIO';
  const displayEmail = user?.email || '';
  const displayRole = user?.role || 'USER';

  const toggleNotif = useCallback(() => {
    setNotifOpen((v) => {
      if (!v && markAllRead) markAllRead(); // Mark as read when opening
      return !v;
    });
    setUserOpen(false);
  }, [markAllRead]);

  const toggleUser = useCallback(() => {
    setUserOpen((v) => !v);
    setNotifOpen(false);
  }, []);

  const handleClear = useCallback(() => {
    clearAll();
    setNotifOpen(false);
  }, [clearAll]);

  const visibleNotifs = (notifications || []).slice(0, 10);
  const totalNotifs = (notifications || []).length;

  const breadcrumbLabel = (moduleLabels && moduleLabels[activeView]) || activeView || 'HOME';

  // ── Styles ──
  const S = {
    bar: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      height: 36,
      background: '#111',
      borderBottom: '2px solid #333',
      fontFamily: "'IBM Plex Mono', monospace",
      padding: '0 12px',
      position: 'relative',
      zIndex: 100,
      boxSizing: 'border-box',
    },
    left: { display: 'flex', alignItems: 'center', gap: 8 },
    avatar: {
      width: 24,
      height: 24,
      background: '#00e676',
      color: '#000',
      fontSize: 11,
      fontWeight: 700,
      fontFamily: "'IBM Plex Mono', monospace",
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: 0,
      border: '2px solid #00e676',
      flexShrink: 0,
    },
    name: {
      color: '#fff',
      fontSize: 10,
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
      fontFamily: "'IBM Plex Mono', monospace",
    },
    role: {
      fontSize: 8,
      background: '#222',
      border: '1px solid #444',
      padding: '1px 6px',
      color: '#00e676',
      textTransform: 'uppercase',
      fontFamily: "'IBM Plex Mono', monospace",
      borderRadius: 0,
    },
    center: {
      fontSize: 10,
      textTransform: 'uppercase',
      letterSpacing: '0.1em',
      fontFamily: "'IBM Plex Mono', monospace",
    },
    right: { display: 'flex', alignItems: 'center', gap: 10 },
    bellBtn: {
      position: 'relative',
      background: 'transparent',
      border: 'none',
      cursor: 'pointer',
      fontSize: 12,
      padding: 0,
      lineHeight: 1,
    },
    badge: {
      position: 'absolute',
      top: -4,
      right: -4,
      minWidth: 14,
      height: 14,
      borderRadius: 0,
      background: '#c00',
      color: '#fff',
      fontSize: 7,
      fontWeight: 700,
      fontFamily: "'IBM Plex Mono', monospace",
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      border: '1px solid #111',
      padding: '0 2px',
      boxSizing: 'border-box',
    },
    clock: {
      fontSize: 9,
      color: '#666',
      fontFamily: "'IBM Plex Mono', monospace",
    },
    dropToggle: {
      background: 'transparent',
      border: 'none',
      cursor: 'pointer',
      fontSize: 10,
      color: '#666',
      padding: 0,
      fontFamily: "'IBM Plex Mono', monospace",
    },
    dropdown: {
      position: 'absolute',
      right: 0,
      top: 'calc(100% + 2px)',
      background: '#111',
      border: '2px solid #333',
      borderRadius: 0,
      zIndex: 200,
      fontFamily: "'IBM Plex Mono', monospace",
    },
  };

  return (
    <div style={S.bar}>
      {/* ── LEFT ── */}
      <div style={S.left}>
        {isMobile && (
          <button
            onClick={onHamburger}
            style={{
              background: 'transparent', border: 'none',
              color: '#fff', fontSize: 16, cursor: 'pointer',
              fontFamily: "'IBM Plex Mono', monospace",
              padding: 0, marginRight: 4,
            }}
          >☰</button>
        )}
        <div style={S.avatar}>{initials}</div>
        <span style={S.name}>{displayName}</span>
        <span style={S.role}>{displayRole}</span>
      </div>

      {/* ── CENTER ── */}
      <div style={S.center}>
        <span style={{ color: '#666' }}>HOME</span>
        <span style={{ color: '#444' }}> › </span>
        <span style={{ color: '#fff', fontWeight: 700 }}>{breadcrumbLabel}</span>
      </div>

      {/* ── RIGHT ── */}
      <div style={S.right}>
        {/* Bell */}
        <div ref={notifRef} style={{ position: 'relative' }}>
          <button style={S.bellBtn} onClick={toggleNotif} title="Notificaciones">
            🔔
            {unreadCount > 0 && <span style={S.badge}>{unreadCount}</span>}
          </button>

          {notifOpen && (
            <div style={{ ...S.dropdown, minWidth: 300, maxHeight: 400, overflowY: 'auto' }}>
              {/* Header */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 8px',
                  borderBottom: '1px solid #333',
                }}
              >
                <span
                  style={{
                    fontSize: 9,
                    fontWeight: 700,
                    color: '#fff',
                    textTransform: 'uppercase',
                    fontFamily: "'IBM Plex Mono', monospace",
                  }}
                >
                  NOTIFICACIONES
                </span>
                <button
                  onClick={handleClear}
                  style={{
                    fontSize: 8,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    fontFamily: "'IBM Plex Mono', monospace",
                    background: '#222',
                    color: '#ccc',
                    border: '2px solid #000',
                    borderRadius: 0,
                    padding: '2px 8px',
                    cursor: 'pointer',
                    boxShadow: '3px 3px 0 #000',
                  }}
                >
                  LIMPIAR
                </button>
              </div>

              {/* Items */}
              {visibleNotifs.length === 0 && (
                <div
                  style={{
                    padding: 12,
                    fontSize: 9,
                    color: '#666',
                    textAlign: 'center',
                    textTransform: 'uppercase',
                    fontFamily: "'IBM Plex Mono', monospace",
                  }}
                >
                  SIN NOTIFICACIONES
                </div>
              )}

              {visibleNotifs.map((n, i) => (
                <div
                  key={n.id || i}
                  style={{
                    display: 'flex',
                    gap: 8,
                    padding: 8,
                    borderBottom: '1px solid #222',
                    background: n.read ? '#111' : '#1a1a1a',
                    alignItems: 'flex-start',
                  }}
                >
                  {/* Type dot */}
                  <div
                    style={{
                      width: 4,
                      height: 4,
                      minWidth: 4,
                      background: TYPE_COLORS[n.type] || '#666',
                      marginTop: 4,
                      borderRadius: 0,
                    }}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 9,
                        color: '#ccc',
                        fontFamily: "'IBM Plex Mono', monospace",
                        wordBreak: 'break-word',
                      }}
                    >
                      {n.message}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 }}>
                      {n.module && (
                        <span
                          style={{
                            fontSize: 7,
                            background: '#222',
                            border: '1px solid #444',
                            padding: '0 4px',
                            color: '#888',
                            textTransform: 'uppercase',
                            fontFamily: "'IBM Plex Mono', monospace",
                            borderRadius: 0,
                          }}
                        >
                          {n.module}
                        </span>
                      )}
                      <span
                        style={{
                          fontSize: 7,
                          color: '#555',
                          fontFamily: "'IBM Plex Mono', monospace",
                        }}
                      >
                        {n.timestamp ? relativeTime(n.timestamp) : ''}
                      </span>
                    </div>
                  </div>
                </div>
              ))}

              {/* Footer */}
              {totalNotifs > 10 && (
                <div
                  style={{
                    padding: '6px 8px',
                    fontSize: 8,
                    color: '#666',
                    textAlign: 'center',
                    textTransform: 'uppercase',
                    fontFamily: "'IBM Plex Mono', monospace",
                    borderTop: '1px solid #222',
                  }}
                >
                  VER TODAS ({totalNotifs})
                </div>
              )}
            </div>
          )}
        </div>

        {/* Clock */}
        <span style={S.clock}>{clock}</span>

        {/* User dropdown */}
        <div ref={userRef} style={{ position: 'relative' }}>
          <button style={S.dropToggle} onClick={toggleUser}>
            ▾
          </button>

          {userOpen && (
            <div style={{ ...S.dropdown, minWidth: 180 }}>
              {/* User info */}
              <div style={{ padding: '8px 10px', borderBottom: '1px solid #333' }}>
                <div
                  style={{
                    fontSize: 9,
                    fontWeight: 700,
                    color: '#fff',
                    textTransform: 'uppercase',
                    fontFamily: "'IBM Plex Mono', monospace",
                  }}
                >
                  {displayName}
                </div>
                <div
                  style={{
                    fontSize: 8,
                    color: '#666',
                    fontFamily: "'IBM Plex Mono', monospace",
                    marginTop: 2,
                  }}
                >
                  {displayEmail}
                </div>
              </div>

              {/* Config (disabled) */}
              <button
                disabled
                style={{
                  display: 'block',
                  width: '100%',
                  padding: '6px 10px',
                  fontSize: 9,
                  color: '#666',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: '1px solid #333',
                  textAlign: 'left',
                  cursor: 'not-allowed',
                  fontFamily: "'IBM Plex Mono', monospace",
                  textTransform: 'uppercase',
                  borderRadius: 0,
                }}
              >
                ⚙ CONFIGURACIÓN
              </button>

              {/* Logout */}
              <button
                onClick={() => {
                  setUserOpen(false);
                  onLogout();
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#220000')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                style={{
                  display: 'block',
                  width: '100%',
                  padding: '6px 10px',
                  fontSize: 9,
                  color: '#c00',
                  background: 'transparent',
                  border: 'none',
                  textAlign: 'left',
                  cursor: 'pointer',
                  fontFamily: "'IBM Plex Mono', monospace",
                  textTransform: 'uppercase',
                  borderRadius: 0,
                }}
              >
                ✕ CERRAR SESIÓN
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default GlobalHeader;
