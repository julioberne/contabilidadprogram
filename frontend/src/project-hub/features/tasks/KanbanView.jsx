/* ============================================================
   KanbanView.jsx — Vista de tablero Kanban con drag-and-drop
   Usa @dnd-kit/core y @dnd-kit/sortable
   ============================================================ */
import { useState } from 'react';
import {
  DndContext, closestCenter, PointerSensor,
  useSensor, useSensors, DragOverlay,
} from '@dnd-kit/core';
import {
  SortableContext, verticalListSortingStrategy,
  useSortable, arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// ─── Tarjeta sorteable individual ─────────────────────────────────────────────
function SortableTaskCard({ task, members, onTaskClick }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: task.id });

  return (
    <div
      ref={setNodeRef}
      style={{
        ...cardStyles.card,
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.4 : 1,
      }}
      {...attributes} {...listeners}
      onClick={(e) => { e.stopPropagation(); onTaskClick(task); }}
    >
      {/* Borde de prioridad */}
      <div style={{ ...cardStyles.priorityBar, background: PRIORITY_COLORS[task.priority] }} />

      <div style={cardStyles.body}>
        <p style={cardStyles.title}>{task.title}</p>
        {task.description && (
          <p style={cardStyles.desc}>{task.description.slice(0, 80)}{task.description.length > 80 ? '…' : ''}</p>
        )}

        <div style={cardStyles.footer}>
          {/* Avatares de asignados */}
          <div style={cardStyles.avatars}>
            {(task.assignees || []).slice(0, 3).map((a, i) => (
              <div key={a.id} style={{
                ...cardStyles.avatar,
                background: a.color || '#0EA5E9',
                zIndex: 10 - i, marginLeft: i > 0 ? '-8px' : 0,
              }}>
                {a.name?.slice(0, 2).toUpperCase()}
              </div>
            ))}
          </div>

          {/* Deadline */}
          {task.due_date && (
            <span style={{
              ...cardStyles.deadline,
              color: isOverdue(task.due_date) ? '#ef4444'
                   : isNear(task.due_date)   ? '#F59E0B' : '#64748b',
            }}>
              {isOverdue(task.due_date) ? '⚠ ' : '◷ '}{formatDate(task.due_date)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Columna Kanban ────────────────────────────────────────────────────────────
function KanbanColumn({ status, tasks, members, onTaskClick, onNewTask }) {
  const ids = tasks.map(t => t.id);
  return (
    <div style={colStyles.column}>
      <div style={colStyles.header}>
        <div style={{ ...colStyles.dot, background: status.color }} />
        <span style={colStyles.label}>{status.label}</span>
        <span style={{ ...colStyles.count, color: status.color }}>{tasks.length}</span>
      </div>

      <SortableContext items={ids} strategy={verticalListSortingStrategy}>
        <div style={colStyles.cards}>
          {tasks.map(t => (
            <SortableTaskCard key={t.id} task={t} members={members} onTaskClick={onTaskClick} />
          ))}
        </div>
      </SortableContext>

      <button style={colStyles.addBtn} onClick={onNewTask}>+ tarea</button>
    </div>
  );
}

// ─── Vista principal Kanban ────────────────────────────────────────────────────
export default function KanbanView({ tasks, statuses, members, onStatusChange, onTaskClick, onNewTask }) {
  const [activeId, setActiveId] = useState(null);

  const sensors = useSensors(useSensor(PointerSensor, {
    activationConstraint: { distance: 5 },
  }));

  const tasksByStatus = (statusId) => tasks.filter(t => t.status === statusId);

  const handleDragEnd = ({ active, over }) => {
    if (!over || active.id === over.id) { setActiveId(null); return; }

    const draggedTask = tasks.find(t => t.id === active.id);
    const targetTask  = tasks.find(t => t.id === over.id);

    if (draggedTask && targetTask && draggedTask.status !== targetTask.status) {
      onStatusChange(draggedTask.id, targetTask.status);
    }
    setActiveId(null);
  };

  const activeTask = tasks.find(t => t.id === activeId);

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter}
      onDragStart={({ active }) => setActiveId(active.id)}
      onDragEnd={handleDragEnd}>
      <div style={styles.board}>
        {statuses.map(s => (
          <KanbanColumn key={s.id} status={s}
            tasks={tasksByStatus(s.id)} members={members}
            onTaskClick={onTaskClick} onNewTask={onNewTask}
          />
        ))}
      </div>

      <DragOverlay>
        {activeTask && (
          <div style={{ ...cardStyles.card, boxShadow: '4px 4px 0 #0EA5E9', opacity: 0.9 }}>
            <div style={{ ...cardStyles.priorityBar, background: PRIORITY_COLORS[activeTask.priority] }} />
            <div style={cardStyles.body}>
              <p style={cardStyles.title}>{activeTask.title}</p>
            </div>
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const PRIORITY_COLORS = {
  low: '#10B981', medium: '#0EA5E9', high: '#F59E0B', urgent: '#EF4444',
};

function isOverdue(dateStr) {
  return dateStr && new Date(dateStr) < new Date();
}
function isNear(dateStr) {
  if (!dateStr) return false;
  const diff = (new Date(dateStr) - new Date()) / 1000 / 3600;
  return diff >= 0 && diff <= 48;
}
function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' });
}

const C = { bg: '#0a0a0a', col: '#111', border: '#222', text: '#e2e8f0', dim: '#64748b' };

const styles = {
  board: {
    display: 'flex', gap: '16px', padding: '20px', flex: 1,
    overflowX: 'auto', alignItems: 'flex-start',
  },
};

const colStyles = {
  column: {
    minWidth: '260px', maxWidth: '260px', background: C.col,
    border: `2px solid ${C.border}`, display: 'flex', flexDirection: 'column',
    maxHeight: 'calc(100vh - 200px)',
  },
  header: {
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '12px 14px', borderBottom: `1px solid ${C.border}`,
  },
  dot: { width: '10px', height: '10px', flexShrink: 0 },
  label: { flex: 1, color: C.text, fontSize: '11px', letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace' },
  count: { fontSize: '12px', fontWeight: 700, fontFamily: '"IBM Plex Mono", monospace' },
  cards: { flex: 1, overflowY: 'auto', padding: '10px', display: 'flex', flexDirection: 'column', gap: '8px' },
  addBtn: {
    background: 'transparent', border: 'none', color: C.dim,
    padding: '10px', cursor: 'pointer', fontSize: '11px', textAlign: 'center',
    borderTop: `1px solid ${C.border}`, fontFamily: '"IBM Plex Mono", monospace',
    width: '100%',
  },
};

const cardStyles = {
  card: {
    background: '#161616', border: `2px solid #2a2a2a`, cursor: 'grab',
    display: 'flex', overflow: 'hidden', transition: 'border-color .15s',
    userSelect: 'none',
  },
  priorityBar: { width: '4px', flexShrink: 0 },
  body: { flex: 1, padding: '10px 12px' },
  title: { color: C.text, fontSize: '12px', margin: '0 0 4px', fontFamily: '"IBM Plex Mono", monospace', fontWeight: 600 },
  desc: { color: C.dim, fontSize: '11px', margin: '0 0 8px', lineHeight: 1.4 },
  footer: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  avatars: { display: 'flex', alignItems: 'center' },
  avatar: {
    width: '22px', height: '22px', borderRadius: '50%',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#000', fontSize: '8px', fontWeight: 700, border: '2px solid #161616',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  deadline: { fontSize: '10px', fontFamily: '"IBM Plex Mono", monospace' },
};
