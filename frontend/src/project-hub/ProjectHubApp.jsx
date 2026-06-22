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

export default function ProjectHubApp({ onExit }) {
  const hub = useProjectHub();
  const [activeView,    setActiveView]    = useState('tasks');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen,    setMobileOpen]    = useState(false);
  const [isMobile,      setIsMobile]      = useState(window.innerWidth < MOBILE_BREAKPOINT);

  // Detectar cambio de tamaño de ventana
  useEffect(() => {
    const handler = () => {
      const mobile = window.innerWidth < MOBILE_BREAKPOINT;
      setIsMobile(mobile);
      if (!mobile) setMobileOpen(false); // cerrar drawer al volver a desktop
    };
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  // En mobile, el sidebar siempre está "colapsado" (oculto) a menos que mobileOpen
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

  if (!hub.user) {
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
      case 'tasks':    return <TaskBoard project={hub.activeProject} workspace={hub.workspace} user={hub.user} />;
      case 'notes':    return <NotesApp workspace={hub.workspace} user={hub.user} />;
      case 'calendar': return <CalendarApp workspace={hub.workspace} user={hub.user} />;
      case 'members':  return <MembersList workspace={hub.workspace} user={hub.user} />;
      case 'rrhh':     return <RRHHView workspace={hub.workspace} user={hub.user} />;
      case 'settings': return <WorkspaceSettings workspace={hub.workspace} user={hub.user} />;
      default:         return null;
    }
  };

  return (
    <div className='hub-root' style={styles.app}>
      {/* Top bar — pasa handler para hamburguesa en mobile */}
      <HubTopBar
        user={hub.user}
        workspace={hub.workspace}
        activeView={activeView}
        activeProject={hub.activeProject}
        onLogout={hub.logout}
        onExit={onExit}
        isMobile={isMobile}
        onMenuToggle={() => isMobile ? setMobileOpen(v => !v) : setSidebarCollapsed(v => !v)}
        sidebarCollapsed={effectiveCollapsed}
      />

      {/* Body: sidebar + contenido */}
      <div style={styles.body}>
        <HubSidebar
          user={hub.user}
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

        {/* Contenido principal */}
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
