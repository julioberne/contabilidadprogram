/* ============================================================
   CompanySelector.jsx — Selector jerárquico de empresas
   Lee de /api/org/entities/selector (tabla entities de CT)
   CRUD básico: crear empresa con nombre, tipo, industria, parent
   Zero-Impact: Reemplaza el selector de portfolios en App.jsx
   ============================================================ */
import { useState, useEffect, useRef, useCallback } from 'react';
import { API } from '../../../config';

/* ── Mapa de iconos por tipo de entidad ────────────────────── */
const TYPE_ICONS = {
  HOLDING:     '🏛️',
  EMPRESA:     '🏢',
  SUB_EMPRESA: '📍',
  PROYECTO:    '📐',
  TAREA:       '📋',
};

const TYPE_LABELS = {
  HOLDING:     'Holding',
  EMPRESA:     'Empresa',
  SUB_EMPRESA: 'Sub-Empresa',
  PROYECTO:    'Proyecto',
  TAREA:       'Tarea',
};

const INDUSTRIES = [
  { id: 'ESTANDAR',       label: 'Estándar Contable',  icon: '≡' },
  { id: 'EDUCACION',      label: 'Educación',          icon: '🏫' },
  { id: 'INMOBILIARIA',   label: 'Inmobiliaria',       icon: '🏠' },
  { id: 'CONSTRUCCION',   label: 'Construcción',       icon: '🏗️' },
  { id: 'SERVICIOS',      label: 'Servicios',          icon: '💼' },
  { id: 'ENTRETENIMIENTO', label: 'Entretenimiento',   icon: '🎰' },
];

const ENTITY_TYPES = ['HOLDING', 'EMPRESA', 'SUB_EMPRESA', 'PROYECTO', 'TAREA'];

/* ── Componente principal ────────────────────────────────── */
export default function CompanySelector({
  activeCompanyId,
  onSelectCompany,
  onCompaniesLoaded,
  style,
}) {
  const [entities, setEntities]       = useState([]);
  const [loading, setLoading]         = useState(true);
  const [modalOpen, setModalOpen]     = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  /* ── Form state para crear empresa ──────────────────────── */
  const [newName, setNewName]           = useState('');
  const [newType, setNewType]           = useState('EMPRESA');
  const [newParentId, setNewParentId]   = useState(null);
  const [newIndustry, setNewIndustry]   = useState('ESTANDAR');
  const [creating, setCreating]         = useState(false);

  /* ── Fetch entities ─────────────────────────────────────── */
  const fetchEntities = useCallback(async () => {
    try {
      const res = await fetch(`${API}/org/entities/selector`);
      if (!res.ok) throw new Error('fetch failed');
      const data = await res.json();
      setEntities(data);
      onCompaniesLoaded?.(data);
    } catch (e) {
      console.warn('[CompanySelector] Error cargando entities:', e);
      // Fallback: intentar con CT entities
      try {
        const res2 = await fetch(`${API}/ct/entities`);
        if (res2.ok) {
          const tree = await res2.json();
          const flat = flattenTree(tree);
          setEntities(flat);
          onCompaniesLoaded?.(flat);
        }
      } catch (_) {}
    } finally {
      setLoading(false);
    }
  }, [onCompaniesLoaded]);

  useEffect(() => { fetchEntities(); }, [fetchEntities]);

  /* ── Click outside → cerrar dropdown ────────────────────── */
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  /* ── Crear empresa ──────────────────────────────────────── */
  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const res = await fetch(`${API}/org/entities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newName.trim(),
          type: newType,
          parent_id: newParentId,
          industry: newIndustry,
        }),
      });
      if (!res.ok) throw new Error('create failed');
      const created = await res.json();
      setModalOpen(false);
      setNewName('');
      setNewType('EMPRESA');
      setNewParentId(null);
      setNewIndustry('ESTANDAR');
      await fetchEntities();
      // Auto-seleccionar la nueva empresa
      onSelectCompany?.(created);
    } catch (e) {
      console.error('[CompanySelector] Error creando entity:', e);
    } finally {
      setCreating(false);
    }
  };

  /* ── Entidad activa ─────────────────────────────────────── */
  const active = entities.find(e => e.id === activeCompanyId);

  /* ── Indent por nivel ───────────────────────────────────── */
  const getIndent = (entity) => {
    const levelMap = { HOLDING: 0, EMPRESA: 1, SUB_EMPRESA: 2, PROYECTO: 3, TAREA: 4 };
    return (levelMap[entity.type] || 0) * 12;
  };

  /* ── Parents válidos para el formulario ─────────────────── */
  const possibleParents = entities.filter(e =>
    ENTITY_TYPES.indexOf(e.type) < ENTITY_TYPES.indexOf(newType)
  );

  return (
    <div style={{ position: 'relative', ...style }}>
      {/* ── Selector horizontal de tabs (modo compacto) ──── */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          flexWrap: 'wrap',
          padding: '4px 0',
        }}
      >
        <span
          style={{
            fontSize: 9,
            letterSpacing: 2,
            color: '#888',
            textTransform: 'uppercase',
            marginRight: 4,
            whiteSpace: 'nowrap',
          }}
        >
          EMPRESA:
        </span>

        {loading ? (
          <span style={{ fontSize: 10, color: '#666' }}>Cargando...</span>
        ) : (
          entities
            .filter(e => e.type === 'EMPRESA' || e.type === 'HOLDING')
            .map(entity => (
              <button
                key={entity.id}
                onClick={() => onSelectCompany?.(entity)}
                style={{
                  fontFamily: '"IBM Plex Mono", monospace',
                  fontSize: 10,
                  letterSpacing: 1,
                  padding: '4px 10px',
                  border: '2px solid #000',
                  background: activeCompanyId === entity.id ? '#000' : 'transparent',
                  color: activeCompanyId === entity.id ? '#fff' : '#000',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  maxWidth: 160,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  textTransform: 'uppercase',
                  transition: 'all 0.15s',
                }}
                title={`${entity.name} (${entity.industry || 'ESTANDAR'})`}
              >
                {entity.name.substring(0, 16)}
              </button>
            ))
        )}

        {/* ── Botón dropdown para ver todos los niveles ──── */}
        <div ref={dropdownRef} style={{ position: 'relative' }}>
          <button
            onClick={() => setDropdownOpen(v => !v)}
            style={{
              fontFamily: '"IBM Plex Mono", monospace',
              fontSize: 10,
              padding: '4px 8px',
              border: '2px solid #000',
              background: dropdownOpen ? '#000' : 'transparent',
              color: dropdownOpen ? '#0f0' : '#000',
              cursor: 'pointer',
              letterSpacing: 1,
            }}
            title="Ver todas las entidades"
          >
            ▾ TODOS
          </button>

          {/* ── Dropdown ────────────────────────────────── */}
          {dropdownOpen && (
            <div
              style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                zIndex: 100,
                background: '#111',
                border: '2px solid #333',
                minWidth: 280,
                maxHeight: 320,
                overflowY: 'auto',
                boxShadow: '4px 4px 0 #000',
              }}
            >
              {entities.map(entity => (
                <button
                  key={entity.id}
                  onClick={() => {
                    onSelectCompany?.(entity);
                    setDropdownOpen(false);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    width: '100%',
                    padding: '6px 8px',
                    paddingLeft: 8 + getIndent(entity),
                    border: 'none',
                    borderBottom: '1px solid #222',
                    background: activeCompanyId === entity.id ? '#1a3a1a' : 'transparent',
                    color: activeCompanyId === entity.id ? '#0f0' : '#ccc',
                    fontFamily: '"IBM Plex Mono", monospace',
                    fontSize: 10,
                    cursor: 'pointer',
                    textAlign: 'left',
                    letterSpacing: 0.5,
                  }}
                >
                  <span>{TYPE_ICONS[entity.type] || '○'}</span>
                  <span style={{ flex: 1 }}>{entity.name}</span>
                  <span style={{ fontSize: 8, color: '#666' }}>
                    {entity.industry !== 'ESTANDAR' ? entity.industry : ''}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* ── + EMPRESA ─────────────────────────────────── */}
        <button
          onClick={() => setModalOpen(true)}
          style={{
            fontFamily: '"IBM Plex Mono", monospace',
            fontSize: 10,
            padding: '4px 10px',
            border: '2px solid #00ff41',
            background: 'transparent',
            color: '#00ff41',
            cursor: 'pointer',
            letterSpacing: 1,
            fontWeight: 700,
          }}
        >
          + EMPRESA
        </button>
      </header>

      {/* ── Modal crear empresa ────────────────────────── */}
      {modalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 200,
          }}
          onClick={(e) => e.target === e.currentTarget && setModalOpen(false)}
        >
          <div
            style={{
              background: '#111',
              border: '2px solid #333',
              padding: 20,
              minWidth: 360,
              maxWidth: 440,
              fontFamily: '"IBM Plex Mono", monospace',
              color: '#eee',
              boxShadow: '6px 6px 0 #000',
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, marginBottom: 16, textTransform: 'uppercase' }}>
              ▣ CREAR NUEVA EMPRESA
            </div>

            {/* Nombre */}
            <label style={labelStyle}>NOMBRE *</label>
            <input
              value={newName}
              onChange={e => setNewName(e.target.value)}
              placeholder="Ej: Jardín Infantil Pegasus"
              style={inputStyle}
              autoFocus
            />

            {/* Tipo */}
            <label style={labelStyle}>TIPO DE ENTIDAD</label>
            <select
              value={newType}
              onChange={e => setNewType(e.target.value)}
              style={inputStyle}
            >
              {ENTITY_TYPES.map(t => (
                <option key={t} value={t}>
                  {TYPE_ICONS[t]} {TYPE_LABELS[t]}
                </option>
              ))}
            </select>

            {/* Parent */}
            {newType !== 'HOLDING' && (
              <>
                <label style={labelStyle}>ENTIDAD PADRE</label>
                <select
                  value={newParentId || ''}
                  onChange={e => setNewParentId(e.target.value ? Number(e.target.value) : null)}
                  style={inputStyle}
                >
                  <option value="">— Sin padre (raíz) —</option>
                  {possibleParents.map(p => (
                    <option key={p.id} value={p.id}>
                      {'  '.repeat(Math.max(0, ENTITY_TYPES.indexOf(p.type)))} {TYPE_ICONS[p.type]} {p.name}
                    </option>
                  ))}
                </select>
              </>
            )}

            {/* Industria */}
            <label style={labelStyle}>INDUSTRIA</label>
            <select
              value={newIndustry}
              onChange={e => setNewIndustry(e.target.value)}
              style={inputStyle}
            >
              {INDUSTRIES.map(ind => (
                <option key={ind.id} value={ind.id}>
                  {ind.icon} {ind.label}
                </option>
              ))}
            </select>

            {/* Botones */}
            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
                style={{
                  flex: 1,
                  padding: '8px 0',
                  fontFamily: '"IBM Plex Mono", monospace',
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: 2,
                  border: '2px solid #00ff41',
                  background: '#00ff41',
                  color: '#000',
                  cursor: creating ? 'wait' : 'pointer',
                  opacity: creating || !newName.trim() ? 0.5 : 1,
                }}
              >
                {creating ? '▓ CREANDO...' : 'CREAR ✔'}
              </button>
              <button
                onClick={() => setModalOpen(false)}
                style={{
                  padding: '8px 16px',
                  fontFamily: '"IBM Plex Mono", monospace',
                  fontSize: 11,
                  border: '2px solid #555',
                  background: 'transparent',
                  color: '#888',
                  cursor: 'pointer',
                  letterSpacing: 1,
                }}
              >
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Estilos reutilizables ───────────────────────────────── */
const labelStyle = {
  display: 'block',
  fontSize: 9,
  letterSpacing: 2,
  color: '#888',
  marginBottom: 4,
  marginTop: 12,
  textTransform: 'uppercase',
};

const inputStyle = {
  width: '100%',
  padding: '6px 8px',
  fontFamily: '"IBM Plex Mono", monospace',
  fontSize: 11,
  border: '2px solid #333',
  background: '#0a0a0a',
  color: '#eee',
  outline: 'none',
  boxSizing: 'border-box',
};

/* ── Helper: aplanar árbol de CT a lista ─────────────────── */
function flattenTree(tree, level = 0) {
  const result = [];
  for (const node of (tree || [])) {
    result.push({
      id: node.id,
      name: node.name,
      type: node.type || 'EMPRESA',
      parent_id: node.parent_id,
      industry: node.industry || 'ESTANDAR',
      portfolio_id: node.portfolio_id,
      status: node.status || 'AL DIA',
      level,
    });
    if (node.children?.length) {
      result.push(...flattenTree(node.children, level + 1));
    }
  }
  return result;
}
