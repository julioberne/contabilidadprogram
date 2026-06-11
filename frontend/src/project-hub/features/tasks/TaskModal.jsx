/* ============================================================
   TaskModal.jsx — Modal para crear / editar una tarea
   Incluye: título, descripción, prioridad, deadline, asignados multi-select
   ============================================================ */
import { useState } from 'react';

const PRIORITIES = [
  { id: 'low',    label: 'BAJA',    color: '#10B981' },
  { id: 'medium', label: 'MEDIA',   color: '#0EA5E9' },
  { id: 'high',   label: 'ALTA',    color: '#F59E0B' },
  { id: 'urgent', label: 'URGENTE', color: '#EF4444' },
];

const STATUSES = [
  { id: 'todo',        label: 'Por hacer' },
  { id: 'in_progress', label: 'En progreso' },
  { id: 'review',      label: 'En revisión' },
  { id: 'done',        label: 'Completado' },
];

export default function TaskModal({ task, members, onSave, onDelete, onClose }) {
  const isNew = !task;
  const [form, setForm] = useState({
    title:       task?.title       || '',
    description: task?.description || '',
    status:      task?.status      || 'todo',
    priority:    task?.priority    || 'medium',
    due_date:    task?.due_date    || '',
    assignee_ids: (task?.assignees || []).map(a => a.id),
  });
  const [saving, setSaving] = useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const toggleAssignee = (uid) => {
    set('assignee_ids',
      form.assignee_ids.includes(uid)
        ? form.assignee_ids.filter(id => id !== uid)
        : [...form.assignee_ids, uid]
    );
  };

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try { await onSave(form); } finally { setSaving(false); }
  };

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <h3 style={styles.heading}>{isNew ? '+ NUEVA TAREA' : 'EDITAR TAREA'}</h3>
          <button style={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        {/* Body */}
        <div style={styles.body}>
          <label style={styles.label}>TÍTULO *</label>
          <input style={styles.input} value={form.title}
            onChange={e => set('title', e.target.value)}
            placeholder="Nombre de la tarea..." autoFocus />

          <label style={styles.label}>DESCRIPCIÓN</label>
          <textarea style={{ ...styles.input, height: '80px', resize: 'vertical' }}
            value={form.description}
            onChange={e => set('description', e.target.value)}
            placeholder="Detalle adicional..." />

          <div style={styles.row2}>
            {/* Estado */}
            <div style={styles.col}>
              <label style={styles.label}>ESTADO</label>
              <select style={styles.select} value={form.status}
                onChange={e => set('status', e.target.value)}>
                {STATUSES.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
            </div>
            {/* Deadline */}
            <div style={styles.col}>
              <label style={styles.label}>FECHA LÍMITE</label>
              <input style={styles.input} type="date" value={form.due_date}
                onChange={e => set('due_date', e.target.value)} />
            </div>
          </div>

          {/* Prioridad */}
          <label style={styles.label}>PRIORIDAD</label>
          <div style={styles.priorities}>
            {PRIORITIES.map(p => (
              <button key={p.id}
                style={{
                  ...styles.priorityBtn,
                  borderColor: form.priority === p.id ? p.color : '#333',
                  color: form.priority === p.id ? p.color : '#64748b',
                  background: form.priority === p.id ? `${p.color}15` : 'transparent',
                }}
                onClick={() => set('priority', p.id)}>
                {p.label}
              </button>
            ))}
          </div>

          {/* Asignados */}
          {members.length > 0 && (
            <>
              <label style={styles.label}>ASIGNAR A</label>
              <div style={styles.memberList}>
                {members.map(m => {
                  const selected = form.assignee_ids.includes(m.id);
                  return (
                    <button key={m.id}
                      style={{ ...styles.memberBtn, ...(selected ? styles.memberSelected : {}) }}
                      onClick={() => toggleAssignee(m.id)}>
                      <div style={{ ...styles.memberAvatar, background: m.color || '#0EA5E9' }}>
                        {m.name?.slice(0, 2).toUpperCase()}
                      </div>
                      <div style={styles.memberInfo}>
                        <span style={styles.memberName}>{m.name}</span>
                        <span style={styles.memberRole}>{m.role}</span>
                      </div>
                      {selected && <span style={styles.check}>✓</span>}
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          {!isNew && (
            <button style={styles.deleteBtn}
              onClick={() => { if (confirm('¿Eliminar esta tarea?')) onDelete(task.id); }}>
              ✕ ELIMINAR
            </button>
          )}
          <div style={{ flex: 1 }} />
          <button style={styles.cancelBtn} onClick={onClose}>CANCELAR</button>
          <button style={styles.saveBtn} onClick={handleSave} disabled={saving || !form.title.trim()}>
            {saving ? 'GUARDANDO...' : isNew ? 'CREAR TAREA' : 'GUARDAR'}
          </button>
        </div>
      </div>
    </div>
  );
}

const C = { bg: '#111', border: '#0EA5E9', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 1000, fontFamily: '"IBM Plex Mono", monospace',
  },
  modal: {
    background: C.bg, border: `2px solid ${C.border}`,
    boxShadow: `6px 6px 0 ${C.border}`, width: '520px', maxWidth: '95vw',
    maxHeight: '90vh', display: 'flex', flexDirection: 'column',
  },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '16px 20px', borderBottom: `2px solid #222`,
  },
  heading: { color: C.accent, fontSize: '14px', margin: 0, letterSpacing: '2px' },
  closeBtn: {
    background: 'transparent', border: 'none', color: C.dim,
    cursor: 'pointer', fontSize: '16px',
  },
  body: { padding: '20px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '12px' },
  label: { color: C.dim, fontSize: '10px', letterSpacing: '2px', display: 'block', marginBottom: '4px' },
  input: {
    background: '#1a1a1a', border: `2px solid #333`, color: C.text,
    padding: '9px 12px', fontSize: '13px', fontFamily: '"IBM Plex Mono", monospace',
    outline: 'none', width: '100%', boxSizing: 'border-box',
  },
  select: {
    background: '#1a1a1a', border: `2px solid #333`, color: C.text,
    padding: '9px 12px', fontSize: '12px', fontFamily: '"IBM Plex Mono", monospace',
    outline: 'none', width: '100%', cursor: 'pointer',
  },
  row2: { display: 'flex', gap: '12px' },
  col: { flex: 1, display: 'flex', flexDirection: 'column' },
  priorities: { display: 'flex', gap: '8px' },
  priorityBtn: {
    flex: 1, padding: '7px', border: '2px solid', cursor: 'pointer',
    fontSize: '10px', letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace',
    transition: 'all .15s',
  },
  memberList: { display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '180px', overflowY: 'auto' },
  memberBtn: {
    display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 10px',
    background: 'transparent', border: `1px solid #333`, cursor: 'pointer',
    color: C.text, textAlign: 'left', transition: 'border-color .15s',
  },
  memberSelected: { borderColor: C.accent, background: 'rgba(14,165,233,0.08)' },
  memberAvatar: {
    width: '28px', height: '28px', flexShrink: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#000', fontSize: '10px', fontWeight: 700,
  },
  memberInfo: { flex: 1, display: 'flex', flexDirection: 'column' },
  memberName: { fontSize: '12px', color: C.text },
  memberRole: { fontSize: '10px', color: C.dim, letterSpacing: '1px' },
  check: { color: C.accent, fontSize: '14px' },
  footer: {
    display: 'flex', gap: '10px', padding: '16px 20px',
    borderTop: `2px solid #222`, alignItems: 'center',
  },
  deleteBtn: {
    background: 'transparent', border: `2px solid #ef4444`, color: '#ef4444',
    padding: '8px 14px', cursor: 'pointer', fontSize: '11px', letterSpacing: '1px',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  cancelBtn: {
    background: 'transparent', border: `2px solid #333`, color: C.dim,
    padding: '8px 16px', cursor: 'pointer', fontSize: '12px',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  saveBtn: {
    background: C.accent, border: 'none', color: '#000',
    padding: '8px 20px', cursor: 'pointer', fontSize: '12px',
    fontWeight: 700, letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace',
    boxShadow: `2px 2px 0 #0369a1`,
  },
};
