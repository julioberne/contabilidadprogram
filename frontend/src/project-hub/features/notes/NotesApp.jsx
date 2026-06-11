/* ============================================================
   NotesApp.jsx — Lista de notas (privadas + compartidas)
   FASE 3 del Project Hub
   ============================================================ */
import { useState, useEffect } from 'react';
import NoteEditor from './NoteEditor';

const API = 'http://localhost:8000/api/hub';

export default function NotesApp({ workspace, user }) {
  const [notes, setNotes]           = useState([]);
  const [activeNote, setActiveNote] = useState(null);
  const [filter, setFilter]         = useState('all'); // 'all' | 'mine' | 'shared'
  const [loading, setLoading]       = useState(false);
  const [creating, setCreating]     = useState(false);

  const load = async () => {
    if (!workspace || !user) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/notes?workspace_id=${workspace.id}&user_id=${user.id}`);
      const data = await r.json();
      setNotes(Array.isArray(data) ? data : []);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [workspace?.id, user?.id]);

  const createNote = async () => {
    if (!workspace || !user) return;
    setCreating(true);
    const r = await fetch(`${API}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workspace_id: workspace.id, user_id: user.id, title: 'Sin título' }),
    });
    const { note } = await r.json();
    setNotes(n => [note, ...n]);
    setActiveNote(note);
    setCreating(false);
  };

  const handleSave = async (noteId, title, content, is_private) => {
    const r = await fetch(`${API}/notes/${noteId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, content, is_private }),
    });
    const { note } = await r.json();
    setNotes(ns => ns.map(n => n.id === note.id ? { ...n, ...note } : n));
    setActiveNote(prev => prev?.id === note.id ? { ...prev, ...note } : prev);
  };

  const filtered = notes.filter(n => {
    if (filter === 'mine')   return n.user_id === user?.id;
    if (filter === 'shared') return !n.is_private;
    return true;
  });

  const formatDate = (d) => d ? new Date(d).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: '2-digit' }) : '';

  return (
    <div style={styles.root}>
      {/* Panel izquierdo — lista de notas */}
      <div style={styles.list}>
        {/* Header */}
        <div style={styles.listHeader}>
          <span style={styles.listTitle}>NOTAS</span>
          <button style={styles.newBtn} onClick={createNote} disabled={creating}>
            {creating ? '…' : '+ NUEVA'}
          </button>
        </div>

        {/* Filtros */}
        <div style={styles.filters}>
          {['all', 'mine', 'shared'].map(f => (
            <button key={f} style={{ ...styles.filterBtn, ...(filter === f ? styles.filterActive : {}) }}
              onClick={() => setFilter(f)}>
              {f === 'all' ? 'TODAS' : f === 'mine' ? 'MÍ AS' : 'COMPARTIDAS'}
            </button>
          ))}
        </div>

        {/* Lista */}
        <div style={styles.noteList}>
          {loading && <p style={styles.msg}>Cargando...</p>}
          {!loading && filtered.length === 0 && (
            <div style={styles.emptyState}>
              <span style={styles.emptyIcon}>◉</span>
              <p style={styles.emptyText}>Sin notas aún</p>
              <button style={styles.emptyBtn} onClick={createNote}>Crear primera nota</button>
            </div>
          )}
          {filtered.map(note => (
            <button key={note.id}
              style={{ ...styles.noteItem, ...(activeNote?.id === note.id ? styles.noteActive : {}) }}
              onClick={() => setActiveNote(note)}>
              <div style={styles.noteItemTop}>
                <span style={styles.noteTitle}>{note.title || 'Sin título'}</span>
                <span style={{ ...styles.badge, ...(note.is_private ? styles.badgePrivate : styles.badgeShared) }}>
                  {note.is_private ? '🔒' : '🌐'}
                </span>
              </div>
              <div style={styles.noteItemBot}>
                <span style={styles.noteAuthor}>{note.author_name || 'Tú'}</span>
                <span style={styles.noteDate}>{formatDate(note.updated_at)}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Panel derecho — editor */}
      <div style={styles.editor}>
        {activeNote ? (
          <NoteEditor
            key={activeNote.id}
            note={activeNote}
            canEdit={activeNote.user_id === user?.id || user?.is_superuser}
            onSave={handleSave}
          />
        ) : (
          <div style={styles.noNote}>
            <span style={styles.noNoteIcon}>◉</span>
            <p style={styles.noNoteText}>Selecciona una nota o crea una nueva</p>
          </div>
        )}
      </div>
    </div>
  );
}

const C = { bg: '#0a0a0a', panel: '#111', border: '#1e1e1e', borderAcc: '#0EA5E9', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  root: { display: 'flex', flex: 1, overflow: 'hidden' },
  list: {
    width: '260px', minWidth: '260px', background: C.panel,
    borderRight: `2px solid ${C.border}`, display: 'flex', flexDirection: 'column',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  listHeader: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '14px 14px', borderBottom: `2px solid ${C.border}`,
  },
  listTitle: { color: C.accent, fontSize: '12px', fontWeight: 700, letterSpacing: '2px' },
  newBtn: {
    background: C.accent, border: 'none', color: '#000',
    padding: '5px 10px', cursor: 'pointer', fontSize: '10px',
    fontWeight: 700, letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace',
  },
  filters: { display: 'flex', borderBottom: `1px solid ${C.border}` },
  filterBtn: {
    flex: 1, background: 'transparent', border: 'none', color: C.dim,
    padding: '7px 4px', cursor: 'pointer', fontSize: '9px', letterSpacing: '1px',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  filterActive: { color: C.accent, borderBottom: `2px solid ${C.accent}` },
  noteList: { flex: 1, overflowY: 'auto' },
  msg: { color: C.dim, fontSize: '11px', textAlign: 'center', padding: '20px', fontFamily: '"IBM Plex Mono", monospace' },
  emptyState: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    padding: '32px 16px', gap: '10px',
  },
  emptyIcon: { fontSize: '32px', color: C.dim },
  emptyText: { color: C.dim, fontSize: '12px', margin: 0, fontFamily: '"IBM Plex Mono", monospace' },
  emptyBtn: {
    background: 'transparent', border: `1px dashed ${C.accent}`, color: C.accent,
    padding: '6px 12px', cursor: 'pointer', fontSize: '11px',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  noteItem: {
    display: 'block', width: '100%', background: 'transparent', border: 'none',
    borderBottom: `1px solid ${C.border}`, padding: '12px 14px',
    cursor: 'pointer', textAlign: 'left', transition: 'background .15s',
  },
  noteActive: { background: 'rgba(14,165,233,0.08)', borderLeft: `3px solid ${C.accent}` },
  noteItemTop: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' },
  noteTitle: { color: C.text, fontSize: '12px', fontWeight: 600, fontFamily: '"IBM Plex Mono", monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 },
  badge: { fontSize: '11px', flexShrink: 0, marginLeft: '6px' },
  badgePrivate: {}, badgeShared: {},
  noteItemBot: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  noteAuthor: { color: C.dim, fontSize: '10px', fontFamily: '"IBM Plex Mono", monospace' },
  noteDate: { color: C.dim, fontSize: '10px', fontFamily: '"IBM Plex Mono", monospace' },
  editor: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  noNote: {
    flex: 1, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', gap: '12px',
  },
  noNoteIcon: { fontSize: '48px', color: C.dim },
  noNoteText: { color: C.dim, fontSize: '13px', fontFamily: '"IBM Plex Mono", monospace' },
};
