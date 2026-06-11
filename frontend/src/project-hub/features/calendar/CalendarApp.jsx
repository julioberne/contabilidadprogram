/* ============================================================
   CalendarApp.jsx — Calendario multi-usuario
   FASE 4: Vistas mensual, semanal, agenda y Gantt
   Librería: react-big-calendar + moment
   ============================================================ */
import { useState, useEffect, useMemo } from 'react';
import { Calendar, momentLocalizer, Views } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import './calendar-overrides.css';
import EventModal from './EventModal';

moment.locale('es');
const localizer = momentLocalizer(moment);

const API = 'http://localhost:8000/api/hub';

const VIEW_LABELS = {
  [Views.MONTH]:  'MES',
  [Views.WEEK]:   'SEMANA',
  [Views.DAY]:    'DÍA',
  [Views.AGENDA]: 'AGENDA',
};

export default function CalendarApp({ workspace, user }) {
  const [events, setEvents]       = useState([]);
  const [tasks,  setTasks]        = useState([]);
  const [members, setMembers]     = useState([]);
  const [view, setView]           = useState(Views.MONTH);
  const [date, setDate]           = useState(new Date());
  const [modal, setModal]         = useState(null); // null | 'new' | event-obj
  const [slotInfo, setSlotInfo]   = useState(null);
  const [showTasks, setShowTasks] = useState(true);
  const [filterUser, setFilterUser] = useState('all');

  // Cargar datos
  useEffect(() => {
    if (!workspace) return;
    fetchEvents();
    fetchMembers();
  }, [workspace?.id]);

  const fetchEvents = async () => {
    try {
      const r = await fetch(`${API}/events?workspace_id=${workspace.id}`);
      setEvents(await r.json());
    } catch {}
  };

  const fetchMembers = async () => {
    try {
      const r = await fetch(`${API}/users?workspace_id=${workspace.id}`);
      setMembers(await r.json());
    } catch {}
  };

  // Combinar eventos + tareas con deadline para el calendario
  const calendarEvents = useMemo(() => {
    const evs = events
      .filter(e => filterUser === 'all' ||
        (e.attendees || []).some(a => a.id === filterUser) ||
        e.created_by === filterUser)
      .map(e => ({
        id: e.id,
        title: e.title,
        start: new Date(e.start_time),
        end:   new Date(e.end_time),
        allDay: e.all_day,
        resource: { type: 'event', color: e.color || '#0EA5E9', data: e },
      }));

    const taskEvs = showTasks
      ? tasks
          .filter(t => t.due_date && t.status !== 'done')
          .map(t => ({
            id: `task-${t.id}`,
            title: `◈ ${t.title}`,
            start: new Date(t.due_date),
            end:   new Date(t.due_date),
            allDay: true,
            resource: { type: 'task', color: '#F59E0B', data: t },
          }))
      : [];

    return [...evs, ...taskEvs];
  }, [events, tasks, showTasks, filterUser]);

  // Estilos de evento según tipo/color/usuario
  const eventPropGetter = (event) => {
    const color = event.resource?.color || '#0EA5E9';
    return {
      style: {
        background: `${color}22`,
        border: `2px solid ${color}`,
        color,
        borderRadius: 0,
        fontSize: '11px',
        fontFamily: '"IBM Plex Mono", monospace',
        padding: '2px 6px',
      },
    };
  };

  const handleSelectSlot = (slotInfo) => {
    setSlotInfo(slotInfo);
    setModal('new');
  };

  const handleSelectEvent = (event) => {
    if (event.resource?.type === 'event') {
      setModal(event.resource.data);
    }
  };

  const handleSaveEvent = async (formData) => {
    if (modal === 'new') {
      const r = await fetch(`${API}/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...formData, workspace_id: workspace.id, created_by: user?.id }),
      });
      const { event } = await r.json();
      setEvents(ev => [...ev, event]);
    } else {
      const r = await fetch(`${API}/events/${modal.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const { event } = await r.json();
      setEvents(ev => ev.map(e => e.id === event.id ? { ...e, ...event } : e));
    }
    setModal(null); setSlotInfo(null);
  };

  if (!workspace) return (
    <div style={styles.empty}>
      <p style={styles.emptyText}>◷ Selecciona un workspace para ver el calendario</p>
    </div>
  );

  return (
    <div style={styles.root}>
      {/* Header con controles */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          {/* Selector de vista */}
          <div style={styles.viewToggle}>
            {Object.entries(VIEW_LABELS).map(([v, label]) => (
              <button key={v}
                style={{ ...styles.viewBtn, ...(view === v ? styles.viewBtnActive : {}) }}
                onClick={() => setView(v)}>
                {label}
              </button>
            ))}
          </div>

          {/* Toggle tareas en calendario */}
          <button
            style={{ ...styles.taskToggle, ...(showTasks ? styles.taskToggleOn : {}) }}
            onClick={() => setShowTasks(t => !t)}>
            ◈ TAREAS {showTasks ? 'ON' : 'OFF'}
          </button>
        </div>

        <div style={styles.headerRight}>
          {/* Filtro por usuario */}
          <select style={styles.select} value={filterUser}
            onChange={e => setFilterUser(e.target.value)}>
            <option value="all">Todos los usuarios</option>
            {members.map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>

          {/* Leyenda de colores */}
          <div style={styles.legend}>
            {members.slice(0, 5).map(m => (
              <div key={m.id} style={styles.legendItem}>
                <div style={{ ...styles.legendDot, background: m.color || '#0EA5E9' }} />
                <span style={styles.legendName}>{m.name.split(' ')[0]}</span>
              </div>
            ))}
          </div>

          <button style={styles.newEventBtn} onClick={() => { setSlotInfo(null); setModal('new'); }}>
            + EVENTO
          </button>
        </div>
      </div>

      {/* Calendario */}
      <div style={styles.calWrapper}>
        <Calendar
          localizer={localizer}
          events={calendarEvents}
          view={view}
          date={date}
          onView={setView}
          onNavigate={setDate}
          onSelectSlot={handleSelectSlot}
          onSelectEvent={handleSelectEvent}
          selectable
          eventPropGetter={eventPropGetter}
          messages={{
            next: '›', previous: '‹', today: 'HOY',
            month: 'MES', week: 'SEMANA', day: 'DÍA', agenda: 'AGENDA',
            noEventsInRange: 'Sin eventos en este rango',
            showMore: (n) => `+${n} más`,
          }}
          style={{ flex: 1 }}
          popup
        />
      </div>

      {/* Modal crear/editar evento */}
      {modal !== null && (
        <EventModal
          event={modal === 'new' ? null : modal}
          members={members}
          slotInfo={slotInfo}
          onSave={handleSaveEvent}
          onClose={() => { setModal(null); setSlotInfo(null); }}
        />
      )}
    </div>
  );
}

const C = { bg: '#0a0a0a', panel: '#111', border: '#1e1e1e', borderAcc: '#0EA5E9', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  root: { display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', background: C.bg },
  empty: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  emptyText: { color: C.dim, fontFamily: '"IBM Plex Mono", monospace', fontSize: '14px' },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '12px 20px', borderBottom: `2px solid ${C.border}`,
    flexShrink: 0, flexWrap: 'wrap', gap: '10px',
  },
  headerLeft:  { display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' },
  headerRight: { display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' },
  viewToggle: { display: 'flex', border: `2px solid #333`, overflow: 'hidden' },
  viewBtn: {
    background: 'transparent', border: 'none', color: C.dim,
    padding: '7px 14px', cursor: 'pointer', fontSize: '11px',
    letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace',
  },
  viewBtnActive: { background: C.accent, color: '#000', fontWeight: 700 },
  taskToggle: {
    background: 'transparent', border: `2px solid #333`, color: C.dim,
    padding: '7px 12px', cursor: 'pointer', fontSize: '10px',
    letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace',
  },
  taskToggleOn: { borderColor: '#F59E0B', color: '#F59E0B' },
  select: {
    background: '#1a1a1a', border: `2px solid #333`, color: C.text,
    padding: '6px 10px', fontSize: '11px', fontFamily: '"IBM Plex Mono", monospace',
    outline: 'none', cursor: 'pointer',
  },
  legend: { display: 'flex', gap: '10px', alignItems: 'center' },
  legendItem: { display: 'flex', alignItems: 'center', gap: '5px' },
  legendDot: { width: '8px', height: '8px', flexShrink: 0 },
  legendName: { color: C.dim, fontSize: '10px', fontFamily: '"IBM Plex Mono", monospace' },
  newEventBtn: {
    background: C.accent, border: 'none', color: '#000',
    padding: '8px 16px', cursor: 'pointer', fontSize: '11px',
    fontWeight: 700, letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace',
    boxShadow: `2px 2px 0 #0369a1`,
  },
  calWrapper: {
    flex: 1, padding: '16px', overflow: 'hidden',
    display: 'flex', flexDirection: 'column',
  },
};
