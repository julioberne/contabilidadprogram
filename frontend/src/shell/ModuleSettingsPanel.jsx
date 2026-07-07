/* ============================================================
   ModuleSettingsPanel.jsx — Panel de Feature Flags Nivel 3
   
   Permite al OWNER/ADMIN:
   - Ver todos los módulos del ERP y su estado
   - Activar/desactivar módulos globalmente
   - Crear reglas por empresa (company_id)
   - Crear reglas por rol (OWNER/ADMIN/MEMBER/VIEWER)
   
   Prioridad de resolución:
   empresa+rol > empresa > rol > global
   ============================================================ */
import { useState, useEffect } from 'react';
import { API } from '../config';


const ROLES = ['OWNER', 'ADMIN', 'MEMBER', 'VIEWER'];

const MODULE_LABELS = {
  'contabilidad':    { icon: '◆', label: 'Contabilidad' },
  'control-tower':   { icon: '◈', label: 'Control Tower' },
  'project-hub':     { icon: '◇', label: 'Project Hub' },
  'contabilidad-v2': { icon: '▣', label: 'Contabilidad v2' },
  'bot':             { icon: '◉', label: 'Bot IA' },
  'trading':         { icon: '△', label: 'Trading NASDAQ' },
};

export default function ModuleSettingsPanel({ onFlagsChanged }) {
  const [flags, setFlags] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(null);
  const [addMode, setAddMode] = useState(false);
  const [newFlag, setNewFlag] = useState({ module_id: '', company_id: '', role_filter: '' });

  // Cargar flags + empresas
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [flagsRes, companiesRes] = await Promise.all([
        fetch(`${API}/module-flags/admin`),
        fetch(`${API}/org/entities`)
      ]);
      const flagsData = await flagsRes.json();
      setFlags(flagsData.flags || []);
      if (companiesRes.ok) {
        const compData = await companiesRes.json();
        setCompanies(compData.filter(e => e.type === 'EMPRESA'));
      }
    } catch (e) {
      console.error('Error cargando flags:', e);
    } finally {
      setLoading(false);
    }
  };

  // Toggle un flag
  const toggleFlag = async (flag) => {
    setSaving(flag.id);
    try {
      await fetch(`${API}/module-flags`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          module_id: flag.module_id,
          enabled: !flag.enabled,
          company_id: flag.company_id,
          role_filter: flag.role_filter,
        })
      });
      await loadData();
      onFlagsChanged?.();
    } catch (e) {
      alert('❌ Error al actualizar flag');
    } finally {
      setSaving(null);
    }
  };

  // Crear nuevo flag
  const createFlag = async () => {
    if (!newFlag.module_id) return alert('Selecciona un módulo');
    setSaving('new');
    try {
      await fetch(`${API}/module-flags`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          module_id: newFlag.module_id,
          enabled: true,
          company_id: newFlag.company_id ? parseInt(newFlag.company_id) : null,
          role_filter: newFlag.role_filter || null,
        })
      });
      setAddMode(false);
      setNewFlag({ module_id: '', company_id: '', role_filter: '' });
      await loadData();
      onFlagsChanged?.();
    } catch (e) {
      alert('❌ Error al crear flag');
    } finally {
      setSaving(null);
    }
  };

  // Eliminar flag
  const deleteFlag = async (flag) => {
    if (!window.confirm(`¿Eliminar regla para "${MODULE_LABELS[flag.module_id]?.label || flag.module_id}"?`)) return;
    try {
      await fetch(`${API}/module-flags/${flag.id}`, { method: 'DELETE' });
      await loadData();
      onFlagsChanged?.();
    } catch (e) {
      alert('❌ Error al eliminar');
    }
  };

  // Agrupar flags: globales vs específicos
  const globalFlags = flags.filter(f => !f.company_id && !f.role_filter);
  const specificFlags = flags.filter(f => f.company_id || f.role_filter);

  if (loading) {
    return (
      <div style={{
        padding: 24,
        fontFamily: 'var(--shell-font)',
        fontSize: 11,
        color: '#555',
        textTransform: 'uppercase',
        letterSpacing: 2,
        background: '#fff',
        minHeight: '100%',
      }}>
        ▓ Cargando configuración...
      </div>
    );
  }

  return (
    <div style={{
      padding: 16,
      fontFamily: 'var(--shell-font, "IBM Plex Mono", monospace)',
      maxWidth: 900,
      margin: '0 auto',
      background: '#ffffff',
      color: '#000000',
      minHeight: '100%',
    }}>

      {/* Header */}
      <div style={{ borderBottom: '2px solid #000', paddingBottom: 8, marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 14, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase' }}>
            ⚙️ Módulos del Sistema
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: 1 }}>
            Feature Flags — Nivel 3 Multi-tenant
          </p>
        </div>
        <span style={{ fontSize: 9, background: '#000', color: '#0f0', padding: '2px 8px', fontWeight: 700, letterSpacing: 1 }}>
          {flags.length} REGLA{flags.length !== 1 ? 'S' : ''}
        </span>
      </div>

      {/* Tabla de Flags Globales */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase', color: '#666', marginBottom: 8, borderBottom: '1px solid #ddd', paddingBottom: 4 }}>
          🌐 Flags Globales (todos los usuarios)
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 8 }}>
          {globalFlags.map(f => {
            const meta = MODULE_LABELS[f.module_id] || { icon: '?', label: f.module_id };
            return (
              <div
                key={f.id}
                style={{
                  border: `2px solid ${f.enabled ? '#000' : '#ccc'}`,
                  padding: '10px 12px',
                  background: f.enabled ? '#fff' : '#f5f5f5',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  transition: 'all 0.15s',
                  opacity: saving === f.id ? 0.5 : 1,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 16 }}>{meta.icon}</span>
                  <span style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
                    {meta.label}
                  </span>
                </div>
                <button
                  onClick={() => toggleFlag(f)}
                  disabled={saving === f.id}
                  style={{
                    padding: '3px 10px',
                    fontSize: 9,
                    fontWeight: 700,
                    fontFamily: 'inherit',
                    letterSpacing: 1,
                    textTransform: 'uppercase',
                    border: '2px solid #000',
                    cursor: 'pointer',
                    background: f.enabled ? '#00c853' : '#eee',
                    color: f.enabled ? '#000' : '#999',
                    transition: 'all 0.15s',
                  }}
                >
                  {f.enabled ? '✅ ON' : '⬚ OFF'}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Tabla de Reglas Específicas */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #ddd', paddingBottom: 4, marginBottom: 8 }}>
          <h3 style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase', color: '#666', margin: 0 }}>
            🏢 Reglas por Empresa / Rol
          </h3>
          <button
            onClick={() => setAddMode(!addMode)}
            style={{
              padding: '3px 12px',
              fontSize: 9,
              fontWeight: 700,
              fontFamily: 'inherit',
              letterSpacing: 1,
              textTransform: 'uppercase',
              border: '2px solid #000',
              background: addMode ? '#ff5252' : '#000',
              color: '#fff',
              cursor: 'pointer',
            }}
          >
            {addMode ? '✕ CANCELAR' : '+ NUEVA REGLA'}
          </button>
        </div>

        {/* Formulario Nueva Regla */}
        {addMode && (
          <div style={{ border: '2px solid #000', padding: 12, marginBottom: 12, background: '#fffde7', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div style={{ flex: 1, minWidth: 150 }}>
              <label style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 2 }}>Módulo</label>
              <select
                value={newFlag.module_id}
                onChange={e => setNewFlag({ ...newFlag, module_id: e.target.value })}
                style={{ width: '100%', padding: 6, fontSize: 11, fontFamily: 'inherit', border: '2px solid #000' }}
              >
                <option value="">— seleccionar —</option>
                {Object.entries(MODULE_LABELS).map(([id, m]) => (
                  <option key={id} value={id}>{m.icon} {m.label}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1, minWidth: 150 }}>
              <label style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 2 }}>Empresa (opcional)</label>
              <select
                value={newFlag.company_id}
                onChange={e => setNewFlag({ ...newFlag, company_id: e.target.value })}
                style={{ width: '100%', padding: 6, fontSize: 11, fontFamily: 'inherit', border: '2px solid #000' }}
              >
                <option value="">🌐 Todas</option>
                {companies.map(c => (
                  <option key={c.id} value={c.id}>🏢 {c.name}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1, minWidth: 120 }}>
              <label style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 2 }}>Rol (opcional)</label>
              <select
                value={newFlag.role_filter}
                onChange={e => setNewFlag({ ...newFlag, role_filter: e.target.value })}
                style={{ width: '100%', padding: 6, fontSize: 11, fontFamily: 'inherit', border: '2px solid #000' }}
              >
                <option value="">👥 Todos</option>
                {ROLES.map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            <button
              onClick={createFlag}
              disabled={saving === 'new'}
              style={{
                padding: '6px 16px', fontSize: 10, fontWeight: 700, fontFamily: 'inherit',
                letterSpacing: 1, textTransform: 'uppercase', border: '2px solid #000',
                background: '#000', color: '#fff', cursor: 'pointer',
              }}
            >
              {saving === 'new' ? '...' : '✓ CREAR'}
            </button>
          </div>
        )}

        {/* Lista de reglas específicas */}
        {specificFlags.length === 0 ? (
          <p style={{ fontSize: 10, color: '#aaa', textTransform: 'uppercase', letterSpacing: 1, padding: 12, border: '1px dashed #ddd', textAlign: 'center' }}>
            Sin reglas específicas — todos los módulos usan la configuración global
          </p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #000', textTransform: 'uppercase', letterSpacing: 1, fontSize: 9 }}>
                <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 700 }}>Módulo</th>
                <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 700 }}>Empresa</th>
                <th style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 700 }}>Rol</th>
                <th style={{ textAlign: 'center', padding: '6px 8px', fontWeight: 700 }}>Estado</th>
                <th style={{ textAlign: 'center', padding: '6px 8px', fontWeight: 700 }}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {specificFlags.map(f => {
                const meta = MODULE_LABELS[f.module_id] || { icon: '?', label: f.module_id };
                return (
                  <tr key={f.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '6px 8px' }}>
                      <span style={{ marginRight: 6 }}>{meta.icon}</span>
                      {meta.label}
                    </td>
                    <td style={{ padding: '6px 8px', color: f.company_name ? '#000' : '#aaa' }}>
                      {f.company_name || '🌐 Todas'}
                    </td>
                    <td style={{ padding: '6px 8px', color: f.role_filter ? '#000' : '#aaa' }}>
                      {f.role_filter || '👥 Todos'}
                    </td>
                    <td style={{ padding: '6px 8px', textAlign: 'center' }}>
                      <button
                        onClick={() => toggleFlag(f)}
                        disabled={saving === f.id}
                        style={{
                          padding: '2px 8px', fontSize: 9, fontWeight: 700,
                          fontFamily: 'inherit', border: '1px solid #000', cursor: 'pointer',
                          background: f.enabled ? '#00c853' : '#eee',
                          color: f.enabled ? '#000' : '#999',
                        }}
                      >
                        {f.enabled ? 'ON' : 'OFF'}
                      </button>
                    </td>
                    <td style={{ padding: '6px 8px', textAlign: 'center' }}>
                      <button
                        onClick={() => deleteFlag(f)}
                        style={{
                          padding: '2px 8px', fontSize: 9, fontFamily: 'inherit',
                          border: '1px solid #c00', background: '#fff', color: '#c00',
                          cursor: 'pointer', fontWeight: 700,
                        }}
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Leyenda */}
      <div style={{ fontSize: 9, color: '#999', borderTop: '1px solid #eee', paddingTop: 8, lineHeight: 1.8 }}>
        <strong style={{ color: '#666' }}>PRIORIDAD:</strong> Empresa+Rol {'>'} Empresa {'>'} Rol {'>'} Global {'>'} Default del registry<br />
        <strong style={{ color: '#666' }}>EJEMPLO:</strong> Si "Bot IA" está OFF globalmente pero ON para empresa "Pegasus" con rol ADMIN,
        solo los admins de Pegasus verán el módulo.
      </div>
    </div>
  );
}
