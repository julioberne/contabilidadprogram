import { useState, useEffect } from 'react';
import './hub-typography.css';
import { useProjectHub }    from './hooks/useProjectHub';
import HubLoginRegister     from './components/HubLoginRegister';
import HubTopBar            from './components/HubTopBar';
import HubSidebar           from './components/HubSidebar';
import TaskBoard            from './features/tasks/TaskBoard';
import NotesApp             from './features/notes/NotesApp';
import CalendarApp          from './features/calendar/CalendarApp';
import MembersList          from './features/members/MembersList';
import WorkspaceSettings    from './features/settings/WorkspaceSettings';
import RRHHView             from './features/members/RRHHView';

const MOBILE_BREAKPOINT = 768;

export default function ProjectHubApp({ onExit, user: shellUser }) {
  const hub = useProjectHub();
  const [activeView,    setActiveView]    = useState('tasks');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen,    setMobileOpen]    = useState(false);
  const [isMobile,      setIsMobile]      = useState(window.innerWidth < MOBILE_BREAKPOINT);

  // ── SSO: Effective user (shell fallback when hub.user is null) ──────
  // Prefer the real Hub user object (from API login via shell) over synthetic
  const ssoUser = shellUser ? (
    shellUser.raw?.user || {
      id: shellUser.id || 1,
      email: shellUser.email || 'andres@finsys.os',
      name: shellUser.name || 'Usuario',
      is_superuser: shellUser.role === 'ADMIN',
      color: '#0EA5E9',
    }
  ) : null;

  // The active user is hub's own user OR the synthetic SSO user
  const activeUser = hub.user || ssoUser;

  // ── SSO: Auto-load workspaces when user active but no workspace ──
  useEffect(() => {
    if (activeUser && !hub.workspace && !hub.loading) {
      hub.loadWorkspaces(activeUser.id, activeUser.is_superuser)
        .catch(err => console.error('[SSO] Workspace load failed:', err));
    }
  }, [activeUser, hub.workspace, hub.loading]);

  // Detectar cambio de tamaño de ventana
  useEffect(() => {
    const handler = () => {
      const mobile = window.innerWidth < MOBILE_BREAKPOINT;
      setIsMobile(mobile);
      if (!mobile) setMobileOpen(false);
    };
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  const effectiveCollapsed = isMobile ? !mobileOpen : sidebarCollapsed;

  const handleAuth = async (mode, form) => {
    if (mode === 'login') {
      await hub.login(form.email, form.password);
    } else {
      const user = await hub.register({
        email: form.email, password: form.password,
        name: form.name, cedula: form.cedula,
        description: form.description,
      });
      if (form.wsName) {
        await hub.createWorkspace({ name: form.wsName, nit: form.wsNit });
      } else {
        await hub.loadWorkspaces(user.id, user.is_superuser);
      }
    }
  };

  // ── SSO: Override logout — when embedded, just go home ──────────────
  const handleLogout = shellUser
    ? () => { if (onExit) onExit(); }  // Navigate home, don't destroy session
    : hub.logout;

  // Only show login screen if NO user at all (no shell, no hub)
  if (!activeUser) {
    return (
      <HubLoginRegister
        onSuccess={handleAuth}
        loading={hub.loading}
        error={hub.error}
      />
    );
  }

  const renderView = () => {
    switch (activeView) {
      case 'tasks':    return <TaskBoard project={hub.activeProject} workspace={hub.workspace} user={activeUser} />;
      case 'notes':    return <NotesApp workspace={hub.workspace} user={activeUser} />;
      case 'calendar': return <CalendarApp workspace={hub.workspace} user={activeUser} />;
      case 'members':  return <MembersList workspace={hub.workspace} user={activeUser} />;
      case 'rrhh':     return <RRHHView workspace={hub.workspace} user={activeUser} />;
      case 'settings': return <WorkspaceSettings workspace={hub.workspace} user={activeUser} />;
      default:         return null;
    }
  };

  return (
    <div className='hub-root' style={styles.app}>
      <HubTopBar
        user={activeUser}
        workspace={hub.workspace}
        activeView={activeView}
        activeProject={hub.activeProject}
        onLogout={handleLogout}
        onExit={onExit}
        isMobile={isMobile}
        onMenuToggle={() => isMobile ? setMobileOpen(v => !v) : setSidebarCollapsed(v => !v)}
        sidebarCollapsed={effectiveCollapsed}
      />

      <div style={styles.body}>
        <HubSidebar
          user={activeUser}
          workspace={hub.workspace}
          workspaces={hub.workspaces}
          onSwitchWorkspace={hub.switchWorkspace}
          onCreateWorkspace={hub.createWorkspace}
          activeView={activeView}
          onChangeView={setActiveView}
          activeProject={hub.activeProject}
          onSelectProject={hub.setActiveProject}
          collapsed={effectiveCollapsed}
          onToggleCollapse={() => isMobile ? setMobileOpen(v => !v) : setSidebarCollapsed(v => !v)}
          mobileOpen={mobileOpen}
          onCloseMobile={() => setMobileOpen(false)}
        />

        <main style={styles.main}>
          {renderView()}
        </main>
      </div>
    </div>
  );
}

const styles = {
  app: {
    position: 'relative',
    height: '100%',
    background: '#0a0a0a', display: 'flex', flexDirection: 'column',
    fontFamily: '"IBM Plex Mono", monospace',
    overflow: 'hidden',
  },
  body: { flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' },
  main: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 },
};
