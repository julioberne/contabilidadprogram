/* ============================================================
   EntityTree.jsx — Árbol jerárquico flexible editable
   FASE 5: Permite agregar/eliminar nodos en cualquier nivel
   ============================================================ */
import { useState, useEffect } from 'react';

const API = 'http://localhost:8000/api/hub';

function TreeNode({ node, allNodes, depth = 0, onDelete, onAdd, expandedIds, toggleExpand }) {
  const children = allNodes.filter(n => n.parent_id === node.id);
  const isExpanded = expandedIds.has(node.id);
  const hasChildren = children.length > 0;

  const [addingChild, setAddingChild] = useState(false);
  const [childName, setChildName]     = useState('');

  const handleAdd = async () => {
    if (!childName.trim()) return;
    await onAdd(childName.trim(), node.id, node.color);
    setChildName(''); setAddingChild(false);
  };

  return (
    <div style={{ marginLeft: depth * 20, marginBottom: '4px' }}>
      {/* Nodo */}
      <div style={{ ...nodeStyles.row, borderLeftColor: node.color || '#0EA5E9' }}>
        {/* Expandir/colapsar */}
        <button style={nodeStyles.toggle}
          onClick={() => toggleExpand(node.id)}
          disabled={!hasChildren}>
          {hasChildren ? (isExpanded ? '▾' : '▸') : '·'}
        </button>

        {/* Dot de color */}
        <div style={{ ...nodeStyles.dot, background: node.color || '#0EA5E9' }} />

        {/* Nombre + tipo */}
        <span style={nodeStyles.name}>{node.name}</span>
        <span style={nodeStyles.type}>{node.type}</span>

        {/* Acciones */}
        <div style={nodeStyles.actions}>
          <button style={nodeStyles.actionBtn} onClick={() => setAddingChild(v => !v)} title="Agregar hijo">+</button>
          <button style={{ ...nodeStyles.actionBtn, color: '#ef4444' }}
            onClick={() => { if (confirm(`¿Eliminar "${node.name}"?`)) onDelete(node.id); }}
            title="Eliminar">✕</button>
        </div>
      </div>

      {/* Formulario agregar hijo */}
      {addingChild && (
        <div style={{ marginLeft: 20, marginTop: '4px', display: 'flex', gap: '6px' }}>
          <input
            style={nodeStyles.input}
            placeholder="Nombre del nodo hijo..."
            value={childName}
            onChange={e => setChildName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
            autoFocus
          />
          <button style={nodeStyles.addBtn} onClick={handleAdd}>✓</button>
          <button style={nodeStyles.cancelBtn} onClick={() => setAddingChild(false)}>✕</button>
        </div>
      )}

      {/* Hijos */}
      {isExpanded && children.map(child => (
        <TreeNode key={child.id} node={child} allNodes={allNodes} depth={0}
          onDelete={onDelete} onAdd={onAdd}
          expandedIds={expandedIds} toggleExpand={toggleExpand} />
      ))}
    </div>
  );
}

export default function EntityTree({ workspace }) {
  const [entities, setEntities]   = useState([]);
  const [loading, setLoading]     = useState(false);
  const [expanded, setExpanded]   = useState(new Set());
  const [newRootName, setNewRootName] = useState('');
  const [newRootType, setNewRootType] = useState('EMPRESA');
  const [addingRoot, setAddingRoot]   = useState(false);

  const ENTITY_TYPES = ['HOLDING', 'EMPRESA', 'SUBEMPRESA', 'PROYECTO', 'DEPARTAMENTO', 'EQUIPO', 'CUSTOM'];
  const TYPE_COLORS  = {
    HOLDING: '#EF4444', EMPRESA: '#F59E0B', SUBEMPRESA: '#0EA5E9',
    PROYECTO: '#10B981', DEPARTAMENTO: '#8B5CF6', EQUIPO: '#EC4899', CUSTOM: '#64748b',
  };

  useEffect(() => {
    if (workspace) loadEntities();
  }, [workspace?.id]);

  const loadEntities = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/entities?workspace_id=${workspace.id}`);
      const data = await r.json();
      setEntities(Array.isArray(data) ? data : []);
      // Expandir primer nivel automáticamente
      const roots = data.filter(e => !e.parent_id);
      setExpanded(new Set(roots.map(e => e.id)));
    } finally { setLoading(false); }
  };

  const toggleExpand = (id) => {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const addEntity = async (name, parentId = null, parentColor = null) => {
    const color = parentColor || TYPE_COLORS[newRootType] || '#0EA5E9';
    const res = await fetch(`${API}/entities`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workspace_id: workspace.id,
        name, parent_id: parentId,
        entity_type: parentId ? 'CUSTOM' : newRootType,
        color,
      }),
    });
    const { entity } = await res.json();
    setEntities(prev => [...prev, entity]);
    if (parentId) setExpanded(prev => new Set([...prev, parentId]));
  };

  const deleteEntity = async (entityId) => {
    await fetch(`${API}/entities/${entityId}`, { method: 'DELETE' });
    setEntities(prev => prev.filter(e => e.id !== entityId && e.parent_id !== entityId));
  };

  const rootEntities = entities.filter(e => !e.parent_id);

  if (!workspace) return (
    <div style={styles.empty}><p style={styles.emptyText}>◬ Selecciona un workspace</p></div>
  );

  return (
    <div style={styles.root}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>ESTRUCTURA ORGANIZACIONAL</h2>
          <p style={styles.subtitle}>Árbol jerárquico flexible — sin límite de niveles</p>
        </div>
        <button style={styles.addBtn} onClick={() => setAddingRoot(v => !v)}>
          + NODO RAÍZ
        </button>
      </div>

      {/* Formulario nodo raíz */}
      {addingRoot && (
        <div style={styles.addRoot}>
          <input style={styles.input} placeholder="Nombre del nodo raíz..."
            value={newRootName} onChange={e => setNewRootName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addEntity(newRootName)} autoFocus />
          <select style={styles.select} value={newRootType} onChange={e => setNewRootType(e.target.value)}>
            {ENTITY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <div style={{ ...styles.colorPreview, background: TYPE_COLORS[newRootType] }} />
          <button style={styles.confirmBtn}
            onClick={() => { addEntity(newRootName); setNewRootName(''); setAddingRoot(false); }}>
            CREAR
          </button>
          <button style={styles.cancelBtn} onClick={() => setAddingRoot(false)}>✕</button>
        </div>
      )}

      {/* Leyenda de tipos */}
      <div style={styles.legend}>
        {ENTITY_TYPES.slice(0, 6).map(t => (
          <div key={t} style={styles.legendItem}>
            <div style={{ ...styles.legendDot, background: TYPE_COLORS[t] }} />
            <span style={styles.legendLabel}>{t}</span>
          </div>
        ))}
      </div>

      {/* Árbol */}
      <div style={styles.tree}>
        {loading && <p style={styles.msg}>CARGANDO...</p>}
        {!loading && rootEntities.length === 0 && (
          <div style={styles.emptyTree}>
            <span style={styles.emptyIcon}>◬</span>
            <p style={styles.emptyMsg}>Sin entidades. Crea el primer nodo raíz.</p>
            <button style={styles.emptyBtn} onClick={() => setAddingRoot(true)}>
              Crear estructura
            </button>
          </div>
        )}
        {rootEntities.map(node => (
          <TreeNode key={node.id} node={node} allNodes={entities}
            onDelete={deleteEntity} onAdd={addEntity}
            expandedIds={expanded} toggleExpand={toggleExpand} />
        ))}
      </div>

      {/* Stats */}
      {entities.length > 0 && (
        <div style={styles.stats}>
          <span style={styles.statsText}>{entities.length} entidades</span>
          <span style={styles.statsText}>·</span>
          <span style={styles.statsText}>{rootEntities.length} nodos raíz</span>
          <span style={styles.statsText}>·</span>
          <span style={styles.statsText}>
            {Math.max(...entities.map(e => e.depth || 0), 0)} niveles de profundidad
          </span>
        </div>
      )}
    </div>
  );
}

const C = { bg: '#0a0a0a', card: '#111', border: '#1e1e1e', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const styles = {
  root: { display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', background: C.bg, fontFamily: '"IBM Plex Mono", monospace' },
  empty: { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  emptyText: { color: C.dim, fontSize: '14px' },
  header: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', padding: '20px 24px', borderBottom: `2px solid ${C.border}`, flexShrink: 0 },
  title: { color: C.accent, fontSize: '14px', margin: '0 0 4px', letterSpacing: '3px' },
  subtitle: { color: C.dim, fontSize: '11px', margin: 0 },
  addBtn: { background: C.accent, border: 'none', color: '#000', padding: '8px 14px', cursor: 'pointer', fontSize: '11px', fontWeight: 700, letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace', boxShadow: `2px 2px 0 #0369a1`, flexShrink: 0 },
  addRoot: { display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 24px', background: '#111', borderBottom: `1px solid ${C.border}`, flexWrap: 'wrap' },
  input: { background: '#1a1a1a', border: `2px solid ${C.accent}`, color: C.text, padding: '7px 12px', fontSize: '12px', fontFamily: '"IBM Plex Mono", monospace', outline: 'none', flex: 1, minWidth: '180px' },
  select: { background: '#1a1a1a', border: `2px solid #333`, color: C.text, padding: '7px 10px', fontSize: '11px', fontFamily: '"IBM Plex Mono", monospace', outline: 'none', cursor: 'pointer' },
  colorPreview: { width: '16px', height: '32px', flexShrink: 0 },
  confirmBtn: { background: C.accent, border: 'none', color: '#000', padding: '7px 14px', cursor: 'pointer', fontSize: '11px', fontWeight: 700, fontFamily: '"IBM Plex Mono", monospace' },
  cancelBtn: { background: 'transparent', border: `1px solid #333`, color: C.dim, padding: '7px 10px', cursor: 'pointer', fontSize: '12px' },
  legend: { display: 'flex', gap: '16px', padding: '10px 24px', borderBottom: `1px solid ${C.border}`, flexWrap: 'wrap', flexShrink: 0 },
  legendItem: { display: 'flex', alignItems: 'center', gap: '6px' },
  legendDot: { width: '8px', height: '8px' },
  legendLabel: { color: C.dim, fontSize: '10px', letterSpacing: '1px' },
  tree: { flex: 1, overflowY: 'auto', padding: '16px 24px' },
  msg: { color: C.dim, fontSize: '12px', textAlign: 'center', padding: '20px' },
  emptyTree: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', padding: '48px' },
  emptyIcon: { fontSize: '48px', color: C.dim },
  emptyMsg: { color: C.dim, fontSize: '12px', margin: 0 },
  emptyBtn: { background: 'transparent', border: `1px dashed ${C.accent}`, color: C.accent, padding: '8px 16px', cursor: 'pointer', fontSize: '11px', fontFamily: '"IBM Plex Mono", monospace' },
  stats: { borderTop: `1px solid ${C.border}`, padding: '8px 24px', display: 'flex', gap: '12px', flexShrink: 0 },
  statsText: { color: C.dim, fontSize: '10px', letterSpacing: '1px' },
};

const nodeStyles = {
  row: {
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '7px 10px', background: '#111',
    border: `1px solid #1e1e1e`, borderLeft: '3px solid',
    transition: 'background .15s', cursor: 'default',
  },
  toggle: {
    background: 'transparent', border: 'none', color: '#64748b',
    cursor: 'pointer', fontSize: '12px', width: '16px', padding: 0, flexShrink: 0,
  },
  dot: { width: '8px', height: '8px', flexShrink: 0 },
  name: { color: '#e2e8f0', fontSize: '12px', flex: 1, fontFamily: '"IBM Plex Mono", monospace' },
  type: { color: '#64748b', fontSize: '9px', letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace' },
  actions: { display: 'flex', gap: '4px', opacity: 0.4, transition: 'opacity .15s' },
  actionBtn: {
    background: 'transparent', border: 'none', color: '#0EA5E9',
    cursor: 'pointer', fontSize: '12px', padding: '0 4px',
    fontFamily: '"IBM Plex Mono", monospace',
  },
  input: {
    background: '#1a1a1a', border: `1px solid #0EA5E9`, color: '#e2e8f0',
    padding: '4px 8px', fontSize: '11px', fontFamily: '"IBM Plex Mono", monospace',
    outline: 'none', flex: 1,
  },
  addBtn: { background: '#0EA5E9', border: 'none', color: '#000', padding: '4px 8px', cursor: 'pointer', fontSize: '11px', fontWeight: 700 },
  cancelBtn: { background: 'transparent', border: '1px solid #333', color: '#64748b', padding: '4px 6px', cursor: 'pointer', fontSize: '11px' },
};
