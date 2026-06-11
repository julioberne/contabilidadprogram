/* ============================================================
   EventModal.jsx — Modal crear/editar evento del calendario
   ============================================================ */
import { useState } from 'react';
import moment from 'moment';

const EVENT_COLORS = [
  { label: 'CIAN',   value: '#0EA5E9' },
  { label: 'VERDE',  value: '#10B981' },
  { label: 'AMBAR',  value: '#F59E0B' },
  { label: 'ROJO',   value: '#EF4444' },
  { label: 'MORADO', value: '#8B5CF6' },
  { label: 'ROSA',   value: '#EC4899' },
];

export default function EventModal({ event, members, slotInfo, onSave, onClose }) {
  const isNew = !event;

  const defaultStart = slotInfo?.start
    ? moment(slotInfo.start).format('YYYY-MM-DDTHH:mm')
    : moment().format('YYYY-MM-DDTHH:mm');
  const defaultEnd = slotInfo?.end
    ? moment(slotInfo.end).format('YYYY-MM-DDTHH:mm')
    : moment().add(1, 'hour').format('YYYY-MM-DDTHH:mm');

  const [form, setForm] = useState({
    title:        event?.title        || '',
    description:  event?.description  || '',
    start_time:   event?.start_time
                    ? moment(event.start_time).format('YYYY-MM-DDTHH:mm')
                    : defaultStart,
    end_time:     event?.end_time
                    ? moment(event.end_time).format('YYYY-MM-DDTHH:mm')
                    : defaultEnd,
    all_day:      event?.all_day      || false,
    color:        event?.color        || '#0EA5E9',
    attendee_ids: (event?.attendees || []).map(a => a.id),
  });
  const [saving, setSaving] = useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const toggleAttendee = (uid) => {
    set('attendee_ids',
      form.attendee_ids.includes(uid)
        ? form.attendee_ids.filter(id => id !== uid)
        : [...form.attendee_ids, uid]
    );
  };

  const handleSave = async () => {
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      await onSave({
        ...form,
        start_time: new Date(form.start_time).toISOString(),
        end_time:   new Date(form.end_time).toISOString(),
      });
    } finally { setSaving(false); }
  };

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={e => e.stopPropagation()}>
        {/* Header con color del evento */}
        <div style={{ ...styles.header, borderTopColor: form.color }}>
          <h3 style={{ ...styles.heading, color: form.color }}>
            {isNew ? '+ NUEVO EVENTO' : 'EDITAR EVENTO'}
          </h3>
          <button style={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div style={styles.body}>
          {/* Título */}
          <label style={styles.label}>TÍTULO *</label>
          <input style={styles.input} value={form.title}
            onChange={e => set('title', e.target.value)}
            placeholder="Nombre del evento..." autoFocus />

          {/* Descripción */}
          <label style={styles.label}>DESCRIPCIÓN</label>
          <textarea style={{ ...styles.input, height: '64px', resize: 'vertical' }}
            value={form.description}
            onChange={e => set('description', e.target.value)}
            placeholder="Detalles del evento..." />

          {/* Todo el día */}
          <label style={styles.checkLabel}>
            <input type="checkbox" checked={form.all_day}
              onChange={e => set('all_day', e.target.checked)}
              style={{ marginRight: '8px', accentColor: form.color }} />
            <span>Todo el día</span>
          </label>

          {/* Fechas */}
          <div style={styles.row2}>
            <div style={styles.col}>
              <label style={styles.label}>INICIO</label>
              <input style={styles.input}
                type={form.all_day ? 'date' : 'datetime-local'}
                value={form.all_day ? form.start_time.slice(0, 10) : form.start_time}
                onChange={e => set('start_time', e.target.value)} />
            </div>
            <div style={styles.col}>
              <label style={styles.label}>FIN</label>
              <input style={styles.input}
                type={form.all_day ? 'date' : 'datetime-local'}
                value={form.all_day ? form.end_time.slice(0, 10) : form.end_time}
                onChange={e => set('end_time', e.target.value)} />
            </div>
          </div>

          {/* Color del evento */}
          <label style={styles.label}>COLOR</label>
          <div style={styles.colorRow}>
            {EVENT_COLORS.map(c => (
              <button key={c.value}
                style={{
                  ...styles.colorBtn,
                  background: c.value,
                  outline: form.color === c.value ? `3px solid #fff` : 'none',
                  outlineOffset: '2px',
                }}
                onClick={() => set('color', c.value)}
                title={c.label}
              />
            ))}
          </div>

          {/* Asistentes */}
          {members.length > 0 && (
            <>
              <label style={styles.label}>ASISTENTES</label>
              <div style={styles.memberList}>
                {members.map(m => {
                  const selected = form.attendee_ids.includes(m.id);
                  return (
                    <button key={m.id}
                      style={{ ...styles.memberBtn, ...(selected ? { ...styles.memberSelected, borderColor: form.color } : {}) }}
                      onClick={() => toggleAttendee(m.id)}>
                      <div style={{ ...styles.avatar, background: m.color || '#0EA5E9' }}>
                        {m.name?.slice(0, 2).toUpperCase()}
                      </div>
                      <span style={styles.memberName}>{m.name}</span>
                      {selected && <span style={{ color: form.color }}>✓</span>}
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          <button style={styles.cancelBtn} onClick={onClose}>CANCELAR</button>
          <button
            style={{ ...styles.saveBtn, background: form.color, boxShadow: `2px 2px 0 ${form.color}88` }}
            onClick={handleSave}
            disabled={saving || !form.title.trim()}>
            {saving ? 'GUARDANDO...' : isNew ? 'CREAR' : 'GUARDAR'}
          </button>
        </div>
      </div>
    </div>
  );
}

const C = { bg: '#111', border: '#0EA5E9', text: '#e2e8f0', dim: '#64748b' };

const styles = {
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 1000, fontFamily: '"IBM Plex Mono", monospace',
  },
  modal: {
    background: C.bg, borderTop: `4px solid ${C.border}`,
    border: `2px solid #222`, boxShadow: `6px 6px 0 #0EA5E9`,
    width: '480px', maxWidth: '95vw', maxHeight: '90vh',
    display: 'flex', flexDirection: 'column',
  },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '16px 20px', borderBottom: `2px solid #222`, borderTop: `4px solid`,
  },
  heading: { fontSize: '13px', margin: 0, letterSpacing: '2px' },
  closeBtn: { background: 'transparent', border: 'none', color: C.dim, cursor: 'pointer', fontSize: '16px' },
  body: { padding: '20px', overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' },
  label: { color: C.dim, fontSize: '10px', letterSpacing: '2px', display: 'block', marginBottom: '4px' },
  input: {
    background: '#1a1a1a', border: `2px solid #333`, color: C.text,
    padding: '9px 12px', fontSize: '12px', fontFamily: '"IBM Plex Mono", monospace',
    outline: 'none', width: '100%', boxSizing: 'border-box',
  },
  checkLabel: {
    display: 'flex', alignItems: 'center', color: C.dim,
    fontSize: '12px', cursor: 'pointer',
  },
  row2: { display: 'flex', gap: '12px' },
  col: { flex: 1, display: 'flex', flexDirection: 'column' },
  colorRow: { display: 'flex', gap: '10px', flexWrap: 'wrap' },
  colorBtn: {
    width: '28px', height: '28px', border: 'none', cursor: 'pointer',
    flexShrink: 0, transition: 'transform .1s',
  },
  memberList: { display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '160px', overflowY: 'auto' },
  memberBtn: {
    display: 'flex', alignItems: 'center', gap: '10px', padding: '7px 10px',
    background: 'transparent', border: `1px solid #333`, cursor: 'pointer',
    color: C.text, fontFamily: '"IBM Plex Mono", monospace', fontSize: '12px',
    transition: 'border-color .15s',
  },
  memberSelected: { background: 'rgba(14,165,233,0.06)' },
  avatar: {
    width: '26px', height: '26px', flexShrink: 0,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#000', fontSize: '9px', fontWeight: 700,
  },
  memberName: { flex: 1, textAlign: 'left' },
  footer: {
    display: 'flex', justifyContent: 'flex-end', gap: '10px',
    padding: '14px 20px', borderTop: `2px solid #222`,
  },
  cancelBtn: {
    background: 'transparent', border: `2px solid #333`, color: C.dim,
    padding: '8px 16px', cursor: 'pointer', fontSize: '11px',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  saveBtn: {
    border: 'none', color: '#000', padding: '8px 20px', cursor: 'pointer',
    fontSize: '12px', fontWeight: 700, letterSpacing: '1px',
    fontFamily: '"IBM Plex Mono", monospace',
  },
};
