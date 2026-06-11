/* ============================================================
   NoteEditor.jsx — Editor de notas tipo Notion con BlockNote
   FASE 3: Soporta bloques de texto, headings, checklists,
           tablas, código e imágenes (Supabase Storage)
   ============================================================ */
import { useState, useCallback, useRef } from 'react';
import { useCreateBlockNote } from '@blocknote/react';
import { BlockNoteView }       from '@blocknote/mantine';
import '@blocknote/mantine/style.css';

const API = 'http://localhost:8000/api/hub';

export default function NoteEditor({ note, canEdit, onSave }) {
  const [title, setTitle]         = useState(note?.title || 'Sin título');
  const [isPrivate, setIsPrivate] = useState(note?.is_private ?? true);
  const [saving, setSaving]       = useState(false);
  const [saved, setSaved]         = useState(false);
  const saveTimeout               = useRef(null);

  // Parsear contenido existente
  const initialContent = (() => {
    try {
      const c = note?.content;
      if (!c) return undefined;
      if (typeof c === 'string') {
        const parsed = JSON.parse(c);
        return Array.isArray(parsed) && parsed.length > 0 ? parsed : undefined;
      }
      return Array.isArray(c) && c.length > 0 ? c : undefined;
    } catch { return undefined; }
  })();

  // Editor BlockNote con soporte de imagen (upload a backend)
  const editor = useCreateBlockNote({
    initialContent,
    uploadFile: async (file) => {
      // Subir imagen como base64 al backend (solución sin Supabase Storage directo)
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result); // retorna data URL
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
    },
  });

  // Guardado auto con debounce de 1.5s
  const scheduleAutoSave = useCallback(async () => {
    if (!canEdit) return;
    if (saveTimeout.current) clearTimeout(saveTimeout.current);
    setSaved(false);
    saveTimeout.current = setTimeout(async () => {
      setSaving(true);
      try {
        const content = editor.document;
        await onSave(note.id, title, content, isPrivate);
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      } finally { setSaving(false); }
    }, 1500);
  }, [canEdit, editor, note?.id, title, isPrivate, onSave]);

  const handleTitleChange = (e) => {
    setTitle(e.target.value);
    scheduleAutoSave();
  };

  const handlePrivacyToggle = async () => {
    const newPrivate = !isPrivate;
    setIsPrivate(newPrivate);
    setSaving(true);
    try {
      const content = editor.document;
      await onSave(note.id, title, content, newPrivate);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally { setSaving(false); }
  };

  const handleManualSave = async () => {
    if (!canEdit) return;
    if (saveTimeout.current) clearTimeout(saveTimeout.current);
    setSaving(true);
    try {
      await onSave(note.id, title, editor.document, isPrivate);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally { setSaving(false); }
  };

  return (
    <div style={styles.root}>
      {/* Barra de herramientas del editor */}
      <div style={styles.toolbar}>
        <div style={styles.toolbarLeft}>
          {/* Toggle privacidad */}
          <button
            style={{ ...styles.privacyBtn, ...(isPrivate ? styles.private : styles.shared) }}
            onClick={handlePrivacyToggle}
            disabled={!canEdit}
            title={isPrivate ? 'Solo tú puedes ver esta nota' : 'Visible para todo el equipo'}
          >
            {isPrivate ? '🔒 PRIVADA' : '🌐 COMPARTIDA'}
          </button>
        </div>

        <div style={styles.toolbarRight}>
          {/* Status guardado */}
          <span style={styles.saveStatus}>
            {saving ? '⟳ guardando…'
             : saved  ? '✓ guardado'
             : canEdit ? '·'  : '👁 solo lectura'}
          </span>

          {canEdit && (
            <button style={styles.saveBtn} onClick={handleManualSave} disabled={saving}>
              GUARDAR
            </button>
          )}
        </div>
      </div>

      {/* Título editable */}
      <div style={styles.titleSection}>
        <input
          style={styles.titleInput}
          value={title}
          onChange={handleTitleChange}
          placeholder="Sin título"
          readOnly={!canEdit}
        />
      </div>

      {/* Editor BlockNote */}
      <div style={styles.editorWrapper} onClick={() => canEdit && editor.focus()}>
        <BlockNoteView
          editor={editor}
          editable={canEdit}
          onChange={scheduleAutoSave}
          theme="dark"
          style={{ height: '100%' }}
        />
      </div>
    </div>
  );
}

const C = { bg: '#0a0a0a', toolbar: '#111', border: '#1e1e1e', borderAcc: '#0EA5E9', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  root: {
    display: 'flex', flexDirection: 'column', height: '100%',
    background: C.bg, fontFamily: '"IBM Plex Mono", monospace',
    overflow: 'hidden',
  },
  toolbar: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '8px 24px', background: C.toolbar,
    borderBottom: `1px solid ${C.border}`, flexShrink: 0,
  },
  toolbarLeft: { display: 'flex', gap: '8px', alignItems: 'center' },
  toolbarRight: { display: 'flex', gap: '12px', alignItems: 'center' },
  privacyBtn: {
    padding: '4px 12px', border: '1px solid', cursor: 'pointer',
    fontSize: '10px', letterSpacing: '1px',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  private: { borderColor: '#64748b', color: '#64748b', background: 'transparent' },
  shared:  { borderColor: C.accent,  color: C.accent,  background: 'rgba(14,165,233,0.1)' },
  saveStatus: { color: C.dim, fontSize: '10px', letterSpacing: '1px' },
  saveBtn: {
    background: C.accent, border: 'none', color: '#000',
    padding: '4px 14px', cursor: 'pointer', fontSize: '10px',
    fontWeight: 700, letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace',
  },
  titleSection: {
    padding: '24px 48px 8px', flexShrink: 0,
    borderBottom: `1px solid ${C.border}`,
  },
  titleInput: {
    width: '100%', background: 'transparent', border: 'none',
    color: C.text, fontSize: '26px', fontWeight: 700,
    fontFamily: '"IBM Plex Mono", monospace', outline: 'none',
    letterSpacing: '-0.5px',
  },
  editorWrapper: {
    flex: 1, overflowY: 'auto', padding: '0 24px 24px',
    // Override estilos de BlockNote para que coincidan con el tema oscuro
    '--bn-colors-editor-background': '#0a0a0a',
    '--bn-colors-editor-text': '#e2e8f0',
    '--bn-colors-menu-background': '#111',
    '--bn-colors-tooltip-background': '#1a1a1a',
    '--bn-colors-hovered-background': 'rgba(14,165,233,0.08)',
    '--bn-colors-selected-background': 'rgba(14,165,233,0.15)',
    '--bn-colors-border': '#1e1e1e',
    '--bn-font-family': '"IBM Plex Mono", monospace',
  },
};
