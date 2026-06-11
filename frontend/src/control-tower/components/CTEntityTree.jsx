// CTEntityTree.jsx — Árbol recursivo de 5 niveles (Zona 2)
import React, { useState } from 'react';

const ENTITY_ICONS = {
  HOLDING: '🏢',
  EMPRESA: '🏭',
  SUB_EMPRESA: '🏗️',
  PROYECTO: '📁',
  TAREA: '📄',
};

const STATUS_CONFIG = {
  'AL DIA': { label: 'AL DÍA', color: 'text-green-400', border: 'border-green-400/30', dot: '●' },
  'ALERTA': { label: 'ALERTA', color: 'text-amber-400', border: 'border-amber-400/40', dot: '⚠' },
  'CRITICO': { label: 'CRÍTICO', color: 'text-red-400', border: 'border-red-400/40', dot: '✕' },
};

const TYPE_LABELS = {
  HOLDING: 'HOLDING',
  EMPRESA: 'EMPRESA',
  SUB_EMPRESA: 'SUB-EMPRESA',
  PROYECTO: 'PROYECTO',
  TAREA: 'TAREA',
};

function EntityNode({ entity, depth = 0, onSelect, activeEntityId, onDelete, parentChain = [] }) {
  const [expanded, setExpanded] = useState(depth === 0);
  const hasChildren = entity.children?.length > 0;
  const isActive = activeEntityId === entity.id;
  const status = STATUS_CONFIG[entity.status] || STATUS_CONFIG['AL DIA'];
  const chain = [...parentChain, entity];

  const indentPx = depth * 20;

  return (
    <div className={`${depth > 0 ? 'border-l-2 border-amber-400/20 ml-4' : ''}`}>
      <div
        className={`flex items-center gap-2 py-2 px-3 group transition-colors cursor-pointer ${
          isActive
            ? 'bg-amber-400/20 border-l-2 border-amber-400'
            : 'hover:bg-amber-400/10'
        }`}
        style={{ paddingLeft: `${12 + indentPx}px` }}
      >
        {/* Expand/collapse toggle */}
        <button
          onClick={() => setExpanded(p => !p)}
          className={`w-4 h-4 flex items-center justify-center text-amber-400/60 hover:text-amber-400 transition-colors flex-shrink-0 ${!hasChildren ? 'opacity-0 pointer-events-none' : ''}`}
        >
          <span className="text-[10px] font-black">{expanded ? '▼' : '▶'}</span>
        </button>

        {/* Icon */}
        <span className="text-base flex-shrink-0">{ENTITY_ICONS[entity.type] || '📌'}</span>

        {/* Name + type */}
        <div className="flex-1 min-w-0" onClick={() => onSelect(entity, parentChain)}>
          <p className={`text-sm font-black uppercase truncate ${isActive ? 'text-amber-400' : 'text-white'}`}>
            {entity.name}
          </p>
          <p className="text-[9px] text-amber-400/40 uppercase tracking-widest">
            {TYPE_LABELS[entity.type] || entity.type}
            {entity.industry ? ` · ${entity.industry}` : ''}
          </p>
        </div>

        {/* Status badge */}
        <span className={`text-[9px] font-black uppercase flex-shrink-0 hidden sm:block ${status.color}`}>
          {status.dot} {status.label}
        </span>

        {/* Action buttons */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
          <button
            onClick={() => onSelect(entity, parentChain)}
            className="bg-amber-400 text-black text-[9px] font-black px-2 py-0.5 uppercase hover:bg-amber-300 transition-colors"
          >
            GESTIONAR
          </button>
          <button
            onClick={() => onDelete(entity.id)}
            className="border border-red-500/50 text-red-400 text-[9px] font-black px-1.5 py-0.5 hover:bg-red-500/20 transition-colors"
            title="Eliminar entidad"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div>
          {entity.children.map(child => (
            <EntityNode
              key={child.id}
              entity={child}
              depth={depth + 1}
              onSelect={onSelect}
              activeEntityId={activeEntityId}
              onDelete={onDelete}
              parentChain={chain}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function AddEntityModal({ isOpen, onClose, onAdd, entities }) {
  const [form, setForm] = useState({
    name: '', type: 'EMPRESA', parent_id: '', industry: '', sub_industry: '', status: 'AL DIA'
  });

  const flatEntities = [];
  const flatten = (nodes) => nodes.forEach(n => {
    flatEntities.push(n);
    if (n.children?.length) flatten(n.children);
  });
  flatten(entities);

  const handleAdd = async () => {
    if (!form.name.trim()) { alert('El nombre es obligatorio.'); return; }
    await onAdd({ ...form, parent_id: form.parent_id ? parseInt(form.parent_id) : null });
    setForm({ name: '', type: 'EMPRESA', parent_id: '', industry: '', sub_industry: '', status: 'AL DIA' });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-[100]">
      <div className="bg-black border-4 border-amber-400 p-6 w-full max-w-md shadow-[8px_8px_0px_#fbbf24] font-mono">
        <div className="flex justify-between items-center border-b-2 border-amber-400 pb-3 mb-4">
          <h3 className="text-amber-400 font-black uppercase text-sm tracking-widest">+ NUEVA ENTIDAD</h3>
          <button onClick={onClose} className="text-amber-400 hover:text-white font-black text-lg">✕</button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">NOMBRE *</label>
            <input
              value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
              placeholder="Ej: Constructora Norte SAS"
              className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-sm font-mono outline-none focus:border-amber-400"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">TIPO *</label>
              <select
                value={form.type} onChange={e => setForm(p => ({ ...p, type: e.target.value }))}
                className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-xs font-mono outline-none focus:border-amber-400"
              >
                {Object.entries(TYPE_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">ESTADO</label>
              <select
                value={form.status} onChange={e => setForm(p => ({ ...p, status: e.target.value }))}
                className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-xs font-mono outline-none focus:border-amber-400"
              >
                <option value="AL DIA">AL DÍA</option>
                <option value="ALERTA">ALERTA</option>
                <option value="CRITICO">CRÍTICO</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">ENTIDAD PADRE (opcional)</label>
            <select
              value={form.parent_id} onChange={e => setForm(p => ({ ...p, parent_id: e.target.value }))}
              className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-xs font-mono outline-none focus:border-amber-400"
            >
              <option value="">— Sin padre (nivel raíz) —</option>
              {flatEntities.map(e => (
                <option key={e.id} value={e.id}>{ENTITY_ICONS[e.type]} {e.name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">SECTOR</label>
              <input
                value={form.industry} onChange={e => setForm(p => ({ ...p, industry: e.target.value }))}
                placeholder="Ej: EDUCACION"
                className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-xs font-mono outline-none focus:border-amber-400"
              />
            </div>
            <div>
              <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">SUB-SECTOR</label>
              <input
                value={form.sub_industry} onChange={e => setForm(p => ({ ...p, sub_industry: e.target.value }))}
                placeholder="Ej: Jardín"
                className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-xs font-mono outline-none focus:border-amber-400"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-2 mt-5">
          <button
            onClick={onClose}
            className="flex-1 border-2 border-amber-400/50 text-amber-400 py-2 text-xs font-black uppercase hover:bg-amber-400/10"
          >
            CANCELAR
          </button>
          <button
            onClick={handleAdd}
            className="flex-1 bg-amber-400 text-black py-2 text-xs font-black uppercase hover:bg-amber-300"
          >
            ✓ CREAR ENTIDAD
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CTEntityTree({ entities, activeEntity, onSelect, onDelete, onCreate }) {
  const [showAddModal, setShowAddModal] = useState(false);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b-2 border-amber-400/30 bg-black flex-shrink-0">
        <div>
          <p className="text-amber-400 text-[10px] font-black uppercase tracking-widest">ZONA 2</p>
          <p className="text-white text-xs font-black uppercase">EL ÁRBOL DE OPERACIONES</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="bg-amber-400 text-black text-[10px] font-black px-3 py-1.5 uppercase hover:bg-amber-300 transition-colors"
        >
          + NUEVA ENTIDAD
        </button>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto">
        {entities.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-amber-400/40 text-4xl mb-3">🏢</p>
            <p className="text-amber-400/60 text-xs font-bold uppercase">Sin entidades creadas</p>
            <p className="text-white/30 text-[10px] mt-1">Crea tu primera empresa o holding</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="mt-4 bg-amber-400 text-black text-xs font-black px-4 py-2 uppercase hover:bg-amber-300"
            >
              + CREAR PRIMERA ENTIDAD
            </button>
          </div>
        ) : (
          entities.map(entity => (
            <EntityNode
              key={entity.id}
              entity={entity}
              depth={0}
              onSelect={onSelect}
              activeEntityId={activeEntity?.id}
              onDelete={onDelete}
              parentChain={[]}
            />
          ))
        )}
      </div>

      {/* Status bar */}
      <div className="border-t-2 border-amber-400/20 px-4 py-1.5 bg-black flex-shrink-0">
        <p className="text-amber-400/40 text-[9px] font-mono uppercase">
          TREE_VIEW_V2 // {entities.length} RAÍZ(ES) // MOD: EXPANDIBLE
        </p>
      </div>

      <AddEntityModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={onCreate}
        entities={entities}
      />
    </div>
  );
}
