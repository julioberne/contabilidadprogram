/* ============================================================
   TagsPanel.jsx — FIN-SYS Contabilidad v2 · Phase 2
   Tags management UI panel
   ============================================================ */
import React from 'react';
import { useTags } from './useTags.js';

const FONT = "'IBM Plex Mono', monospace";

const inputStyle = {
  fontFamily: FONT,
  fontSize: 10,
  padding: '4px 8px',
  border: '2px solid #000',
  borderRadius: 0,
  background: '#fff',
  outline: 'none',
};

export function TagsPanel() {
  const tags = useTags();

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') tags.create();
  };

  return (
    <div style={{ fontFamily: FONT }}>
      {/* ── Section header ─────────────────────────────────── */}
      <div style={{
        fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '0.12em', color: '#666', marginBottom: 8,
      }}>
        etiquetas · {tags.items.length} registros
        {tags.loading && (
          <span style={{ marginLeft: 8, color: '#999' }}>cargando…</span>
        )}
      </div>

      {/* ── Create form ────────────────────────────────────── */}
      <div style={{
        display: 'flex', gap: 0, marginBottom: 12,
      }}>
        <input
          style={{ ...inputStyle, flex: 1, borderRight: 'none' }}
          placeholder="NOMBRE DE ETIQUETA"
          value={tags.newTagName}
          onChange={(e) => tags.setNewTagName(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          onClick={tags.create}
          disabled={!tags.newTagName.trim()}
          style={{
            fontFamily: FONT,
            fontSize: 9,
            fontWeight: 700,
            textTransform: 'uppercase',
            padding: '4px 12px',
            border: '2px solid #000',
            borderRadius: 0,
            background: tags.newTagName.trim() ? '#000' : '#ccc',
            color: '#fff',
            cursor: tags.newTagName.trim() ? 'pointer' : 'not-allowed',
            boxShadow: tags.newTagName.trim() ? '3px 3px 0 #000' : 'none',
            whiteSpace: 'nowrap',
          }}
        >
          + Crear
        </button>
      </div>

      {/* ── Tags list ──────────────────────────────────────── */}
      <div style={{
        border: '2px solid #000',
        boxShadow: '3px 3px 0 #000',
        background: '#fff',
      }}>
        {tags.items.map((tag, i) => (
          <div
            key={tag.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 8px',
              borderBottom: i < tags.items.length - 1 ? '1px solid #e0e0d8' : 'none',
              background: i % 2 === 0 ? '#fff' : '#fafaf5',
              fontSize: 10,
            }}
          >
            {/* Color swatch */}
            <div style={{
              width: 10, height: 10, flexShrink: 0,
              border: '2px solid #000',
              background: tag.color || '#000',
            }} />

            {tags.editingId === tag.id ? (
              /* ── Inline edit ─────────────────────────── */
              <>
                <input
                  style={{ ...inputStyle, flex: 1, fontSize: 10, padding: '2px 6px' }}
                  value={tags.editData.name}
                  onChange={(e) =>
                    tags.setEditData({ ...tags.editData, name: e.target.value })
                  }
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') tags.update(tag.id);
                    if (e.key === 'Escape') tags.cancelEdit();
                  }}
                  autoFocus
                />
                <button
                  style={{
                    fontFamily: FONT, fontSize: 10, cursor: 'pointer',
                    background: 'none', border: 'none', color: '#00c853',
                    fontWeight: 700, padding: '2px 4px',
                  }}
                  onClick={() => tags.update(tag.id)}
                  title="Guardar"
                >
                  ✓
                </button>
                <button
                  style={{
                    fontFamily: FONT, fontSize: 10, cursor: 'pointer',
                    background: 'none', border: 'none', color: '#c00',
                    fontWeight: 700, padding: '2px 4px',
                  }}
                  onClick={tags.cancelEdit}
                  title="Cancelar"
                >
                  ✕
                </button>
              </>
            ) : (
              /* ── Display mode ────────────────────────── */
              <>
                <span style={{ flex: 1, fontWeight: 700, textTransform: 'uppercase' }}>
                  {tag.name}
                </span>
                <button
                  style={{
                    fontFamily: FONT, fontSize: 10, cursor: 'pointer',
                    background: 'none', border: 'none', padding: '2px 4px',
                  }}
                  onClick={() => tags.startEdit(tag)}
                  title="Editar"
                >
                  ✎
                </button>
                <button
                  style={{
                    fontFamily: FONT, fontSize: 10, cursor: 'pointer',
                    background: 'none', border: 'none', color: '#c00',
                    padding: '2px 4px',
                  }}
                  onClick={() => tags.remove(tag.id)}
                  title="Eliminar"
                >
                  🗑
                </button>
              </>
            )}
          </div>
        ))}

        {/* Empty state */}
        {!tags.loading && tags.items.length === 0 && (
          <div style={{
            padding: 24, textAlign: 'center',
            fontSize: 9, color: '#999', textTransform: 'uppercase',
          }}>
            ▓ sin etiquetas creadas
          </div>
        )}
      </div>

      {/* ── Footer count ───────────────────────────────────── */}
      {tags.items.length > 0 && (
        <div style={{
          fontSize: 8, color: '#999', textTransform: 'uppercase',
          textAlign: 'right', marginTop: 4, letterSpacing: '0.08em',
        }}>
          total: {tags.items.length} etiquetas
        </div>
      )}
    </div>
  );
}

export default TagsPanel;
