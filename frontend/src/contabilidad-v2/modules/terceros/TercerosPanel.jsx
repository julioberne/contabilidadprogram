import { useState } from 'react';
import { useTerceros } from './useTerceros.js';
import { useLabel } from '../../engine/TenantProvider.jsx';
import { useTransactionDraft } from '../../engine/TransactionDraftProvider.jsx';

const ID_TYPES = ['NIT', 'CC', 'CE', 'PP'];

export function TercerosPanel() {
  const lblTercero = useLabel('tercero');
  const [formOpen, setFormOpen] = useState(false);
  const draft = useTransactionDraft(); // Access the global draft

  const {
    loading, search, setSearch,
    editingId, editData, setEditData,
    form, updateForm,
    filtered, create, update, remove,
    startEdit, cancelEdit,
  } = useTerceros();

  const handleCreate = async () => {
    await create();
    setFormOpen(false);
  };

  return (
    <div className="space-y-2 font-mono">

      {/* ── SEARCH ────────────────────────────────────── */}
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder={`🔍 Buscar ${lblTercero.toLowerCase()}...`}
        className="cv2-input"
      />

      {/* ── CREATE FORM (collapsible) ─────────────────── */}
      <div style={{ border: '2px solid #000' }}>
        <button
          onClick={() => setFormOpen((p) => !p)}
          style={{
            width: '100%', display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', padding: '5px 8px',
            background: '#f5f5f0', border: 'none', cursor: 'pointer',
            fontFamily: "'IBM Plex Mono', monospace", fontSize: 9,
            fontWeight: 700, textTransform: 'uppercase',
          }}
        >
          <span>✚ Crear {lblTercero}</span>
          <span style={{ color: '#999' }}>{formOpen ? '▲' : '▼'}</span>
        </button>

        {formOpen && (
          <div style={{ padding: 8, borderTop: '2px solid #000' }} className="space-y-1.5">
            <input
              type="text"
              value={form.name}
              onChange={(e) => updateForm('name', e.target.value)}
              placeholder="Nombre / Razón Social"
              className="cv2-input"
              autoFocus
            />
            <div className="grid grid-cols-2 gap-1">
              <select
                value={form.identification_type}
                onChange={(e) => updateForm('identification_type', e.target.value)}
                className="cv2-input"
                style={{ background: '#fff' }}
              >
                {ID_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <input
                type="text"
                value={form.identification_number}
                onChange={(e) => updateForm('identification_number', e.target.value)}
                placeholder="Número"
                className="cv2-input"
              />
            </div>
            <input
              type="email"
              value={form.email}
              onChange={(e) => updateForm('email', e.target.value)}
              placeholder="Email"
              className="cv2-input"
            />
            <div className="grid grid-cols-2 gap-1">
              <input
                type="text"
                value={form.phone}
                onChange={(e) => updateForm('phone', e.target.value)}
                placeholder="Teléfono"
                className="cv2-input"
              />
              <input
                type="text"
                value={form.address}
                onChange={(e) => updateForm('address', e.target.value)}
                placeholder="Dirección"
                className="cv2-input"
              />
            </div>
            <button
              onClick={handleCreate}
              disabled={loading || !form.name.trim()}
              className="cv2-btn"
              style={{ width: '100%' }}
            >
              {loading ? 'Guardando...' : `+ Crear ${lblTercero}`}
            </button>
          </div>
        )}
      </div>

      {/* ── TABLE ─────────────────────────────────────── */}
      <div style={{ border: '2px solid #000', overflow: 'hidden' }}>
        <table style={{
          width: '100%', borderCollapse: 'collapse',
          fontFamily: "'IBM Plex Mono', monospace", fontSize: 10,
        }}>
          <thead>
            <tr style={{ background: '#000', color: '#fff', textTransform: 'uppercase', fontSize: 9 }}>
              <th style={{ padding: '4px 6px', textAlign: 'left', borderRight: '1px solid #333' }}>Nombre</th>
              <th style={{ padding: '4px 6px', textAlign: 'left', borderRight: '1px solid #333', width: 40 }}>Tipo</th>
              <th style={{ padding: '4px 6px', textAlign: 'left', borderRight: '1px solid #333' }}>NIT/CC</th>
              <th style={{ padding: '4px 6px', textAlign: 'left', borderRight: '1px solid #333' }}>Email</th>
              <th style={{ padding: '4px 6px', textAlign: 'center', width: 60 }}>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((tp) => {
              const isEditing = editingId === tp.id;

              return (
                <tr
                  key={tp.id}
                  style={{
                    borderBottom: '1px solid #e0e0d8',
                    background: isEditing ? '#fffff0' : '#fff',
                  }}
                >
                  {/* NOMBRE */}
                  <td style={{ padding: '3px 6px', fontWeight: 700, borderRight: '1px solid #f0f0e8' }}>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editData.name || ''}
                        onChange={(e) => setEditData((d) => ({ ...d, name: e.target.value }))}
                        className="cv2-input"
                        style={{ padding: '2px 4px', fontSize: 10 }}
                        autoFocus
                      />
                    ) : tp.name}
                  </td>

                  {/* TIPO */}
                  <td style={{ padding: '3px 6px', color: '#999', borderRight: '1px solid #f0f0e8' }}>
                    {isEditing ? (
                      <select
                        value={editData.identification_type || 'NIT'}
                        onChange={(e) => setEditData((d) => ({ ...d, identification_type: e.target.value }))}
                        className="cv2-input"
                        style={{ padding: '2px 2px', fontSize: 9 }}
                      >
                        {ID_TYPES.map((t) => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    ) : tp.identification_type}
                  </td>

                  {/* NIT/CC */}
                  <td style={{ padding: '3px 6px', color: '#666', borderRight: '1px solid #f0f0e8' }}>
                    {isEditing ? (
                      <input
                        type="text"
                        value={editData.identification_number || ''}
                        onChange={(e) => setEditData((d) => ({ ...d, identification_number: e.target.value }))}
                        className="cv2-input"
                        style={{ padding: '2px 4px', fontSize: 10 }}
                      />
                    ) : tp.identification_number || '—'}
                  </td>

                  {/* EMAIL */}
                  <td style={{ padding: '3px 6px', color: '#666', borderRight: '1px solid #f0f0e8' }}>
                    {isEditing ? (
                      <input
                        type="email"
                        value={editData.email || ''}
                        onChange={(e) => setEditData((d) => ({ ...d, email: e.target.value }))}
                        className="cv2-input"
                        style={{ padding: '2px 4px', fontSize: 10 }}
                      />
                    ) : tp.email || '—'}
                  </td>

                  {/* ACCIONES */}
                  <td style={{ padding: '3px 6px', textAlign: 'center' }}>
                    {isEditing ? (
                      <div style={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                        <button
                          onClick={() => update(tp.id)}
                          title="Guardar"
                          style={{
                            border: '1px solid #000', background: '#000', color: '#fff',
                            padding: '1px 5px', fontSize: 9, cursor: 'pointer',
                            fontFamily: "'IBM Plex Mono', monospace",
                          }}
                        >✓</button>
                        <button
                          onClick={cancelEdit}
                          title="Cancelar"
                          style={{
                            border: '1px solid #000', background: '#fff', color: '#000',
                            padding: '1px 5px', fontSize: 9, cursor: 'pointer',
                            fontFamily: "'IBM Plex Mono', monospace",
                          }}
                        >✕</button>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                        <button
                          onClick={() => draft.setThirdParty(tp)}
                          title="Vincular a registro"
                          style={{
                            border: draft.thirdParty?.id === tp.id ? '2px solid #00e676' : '1px solid #000',
                            background: draft.thirdParty?.id === tp.id ? '#00e676' : '#f5f5f0',
                            cursor: 'pointer', fontSize: 11, padding: '2px 4px',
                            fontWeight: 700
                          }}
                        >🔗</button>
                        <button
                          onClick={() => startEdit(tp)}
                          title="Editar"
                          style={{
                            border: 'none', background: 'transparent',
                            cursor: 'pointer', fontSize: 11, padding: 0,
                          }}
                        >✎</button>
                        <button
                          onClick={() => remove(tp.id)}
                          title="Eliminar"
                          style={{
                            border: 'none', background: 'transparent',
                            cursor: 'pointer', fontSize: 11, padding: 0,
                          }}
                        >🗑</button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filtered.length === 0 && (
          <div style={{
            padding: 16, textAlign: 'center',
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 10, color: '#999', textTransform: 'uppercase',
          }}>
            {search ? 'Sin resultados' : `Sin ${lblTercero.toLowerCase()}s registrados`}
          </div>
        )}
      </div>

      {/* ── COUNT LABEL ───────────────────────────────── */}
      <div style={{
        fontSize: 8, color: '#999',
        fontFamily: "'IBM Plex Mono', monospace",
        textTransform: 'uppercase', textAlign: 'right',
      }}>
        {filtered.length} {lblTercero.toLowerCase()}s registrados
      </div>
    </div>
  );
}

export default TercerosPanel;
