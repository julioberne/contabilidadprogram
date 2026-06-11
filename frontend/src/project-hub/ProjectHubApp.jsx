import { useState } from 'react';
import { useProjectHub } from './hooks/useProjectHub';
import HubLoginRegister    from './components/HubLoginRegister';
import HubTopBar           from './components/HubTopBar';
import HubSidebar          from './components/HubSidebar';
import TaskBoard           from './features/tasks/TaskBoard';
import NotesApp            from './features/notes/NotesApp';
import CalendarApp         from './features/calendar/CalendarApp';
import MembersList         from './features/members/MembersList';
import WorkspaceSettings   from './features/settings/WorkspaceSettings';


export default function ProjectHubApp({ onExit }) {
  const hub = useProjectHub();
  const [activeView, setActiveView] = useState('tasks');

  // ── Auth handler ─────────────────────────────────────────────────────────
  const handleAuth = async (mode, form) => {
    if (mode === 'login') {
      await hub.login(form.email, form.password);
    } else {
      // Registrar usuario
      const user = await hub.register({
        email: form.email, password: form.password,
        name: form.name, cedula: form.cedula,
        description: form.description,
      });

      // Crear workspace si lo pidió
      if (form.wsName) {
        await hub.createWorkspace({ name: form.wsName, nit: form.wsNit });
      } else {
        await hub.loadWorkspaces(user.id, user.is_superuser);
      }
    }
  };

  // ── Sin sesión → Login ───────────────────────────────────────────────────
  if (!hub.user) {
    return (
      <HubLoginRegister
        onSuccess={handleAuth}
        loading={hub.loading}
        error={hub.error}
      />
    );
  }

  // ── Vista activa ─────────────────────────────────────────────────────────
  const renderView = () => {
    switch (activeView) {
      case 'tasks':
        return <TaskBoard project={hub.activeProject} workspace={hub.workspace} user={hub.user} />;
      case 'notes':
        return <NotesApp workspace={hub.workspace} user={hub.user} />;
      case 'calendar':
        return <CalendarApp workspace={hub.workspace} user={hub.user} />;
      case 'members':
        return <MembersList workspace={hub.workspace} user={hub.user} />;
      case 'settings':
        return <WorkspaceSettings workspace={hub.workspace} user={hub.user} />;
      default:
        return null;
    }
  };


  // ── App principal ────────────────────────────────────────────────────────
  return (
    <div style={styles.app}>
      {/* Top bar */}
      <HubTopBar
        user={hub.user}
        workspace={hub.workspace}
        activeView={activeView}
        activeProject={hub.activeProject}
        onLogout={hub.logout}
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
    position: 'fixed', inset: 0,
    background: '#0a0a0a', display: 'flex', flexDirection: 'column',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  body: { flex: 1, display: 'flex', overflow: 'hidden' },
  main: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
};
