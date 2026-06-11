// CTApprovalsCenter.jsx — Centro de aprobaciones
import React, { useState } from 'react';

const fmt = (n) => new Intl.NumberFormat('es-CO', {
  style: 'currency', currency: 'COP', maximumFractionDigits: 0
}).format(n || 0);

const STATUS_CONFIG = {
  PENDIENTE: { label: 'PENDIENTE', color: 'text-amber-400', bg: 'bg-amber-400/10 border-amber-400/40' },
  APROBADO: { label: 'APROBADO', color: 'text-green-400', bg: 'bg-green-400/10 border-green-400/40' },
  RECHAZADO: { label: 'RECHAZADO', color: 'text-red-400', bg: 'bg-red-400/10 border-red-400/40' },
};

function NewApprovalForm({ onSubmit, onCancel, activeEntity }) {
  const [form, setForm] = useState({ description: '', amount: '' });

  const handleSubmit = async () => {
    if (!form.description || !form.amount) { alert('Descripción y monto son obligatorios.'); return; }
    await onSubmit({ description: form.description, amount: parseFloat(form.amount) });
    setForm({ description: '', amount: '' });
    onCancel();
  };

  return (
    <div className="border-2 border-amber-400/40 p-4 bg-amber-400/5 space-y-3">
      <p className="text-amber-400 text-[10px] font-black uppercase">+ NUEVA SOLICITUD DE APROBACIÓN</p>
      <div>
        <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">DESCRIPCIÓN *</label>
        <input value={form.description}
          onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
          placeholder="Ej: Pago arriendo oficina julio"
          className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-sm font-mono outline-none focus:border-amber-400" />
      </div>
      <div>
        <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">MONTO *</label>
        <input type="number" value={form.amount}
          onChange={e => setForm(p => ({ ...p, amount: e.target.value }))}
          placeholder="0"
          className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-sm font-mono outline-none focus:border-amber-400" />
      </div>
      <div className="flex gap-2">
        <button onClick={onCancel}
          className="flex-1 border-2 border-amber-400/40 text-amber-400/60 py-2 text-xs font-black uppercase hover:border-amber-400">
          CANCELAR
        </button>
        <button onClick={handleSubmit}
          className="flex-1 bg-amber-400 text-black py-2 text-xs font-black uppercase hover:bg-amber-300">
          ENVIAR A COLA
        </button>
      </div>
    </div>
  );
}

export default function CTApprovalsCenter({ approvals, onResolve, onCreateApproval, activeEntity, onClose }) {
  const [filter, setFilter] = useState('PENDIENTE');
  const [showNewForm, setShowNewForm] = useState(false);
  const [resolveNote, setResolveNote] = useState({});

  const filtered = approvals.filter(a => filter === 'ALL' ? true : a.status === filter);
  const pendingCount = approvals.filter(a => a.status === 'PENDIENTE').length;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-[100]">
      <div className="bg-black border-4 border-amber-400 w-full max-w-2xl shadow-[8px_8px_0px_#fbbf24] font-mono flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b-2 border-amber-400 flex-shrink-0">
          <div>
            <p className="text-amber-400/60 text-[10px] uppercase font-bold">CONTROL TOWER</p>
            <h3 className="text-amber-400 font-black uppercase">
              🔔 CENTRO DE APROBACIONES
              {pendingCount > 0 && (
                <span className="ml-2 bg-red-500 text-white text-[9px] px-1.5 py-0.5 font-black">
                  {pendingCount}
                </span>
              )}
            </h3>
          </div>
          <button onClick={onClose} className="text-amber-400 hover:text-white font-black text-xl">✕</button>
        </div>

        {/* Filters + New Button */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-amber-400/30 flex-shrink-0">
          <div className="flex gap-1">
            {['PENDIENTE', 'APROBADO', 'RECHAZADO', 'ALL'].map(f => (
              <button key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 text-[9px] font-black uppercase transition-colors ${
                  filter === f ? 'bg-amber-400 text-black' : 'border border-amber-400/30 text-amber-400/60 hover:border-amber-400'
                }`}>
                {f === 'ALL' ? 'TODOS' : f}
              </button>
            ))}
          </div>
          <button
            onClick={() => setShowNewForm(p => !p)}
            className="bg-amber-400/20 border border-amber-400/50 text-amber-400 text-[9px] font-black px-3 py-1 uppercase hover:bg-amber-400/40">
            + NUEVA
          </button>
        </div>

        {/* New Form */}
        {showNewForm && (
          <div className="px-5 py-3 border-b border-amber-400/30 flex-shrink-0">
            <NewApprovalForm
              onSubmit={onCreateApproval}
              onCancel={() => setShowNewForm(false)}
              activeEntity={activeEntity}
            />
          </div>
        )}

        {/* List */}
        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-3">
          {filtered.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-amber-400/40 text-3xl">✓</p>
              <p className="text-amber-400/60 text-xs font-bold uppercase mt-2">
                {filter === 'PENDIENTE' ? 'No hay aprobaciones pendientes' : 'Sin registros'}
              </p>
            </div>
          ) : (
            filtered.map(approval => {
              const sc = STATUS_CONFIG[approval.status] || STATUS_CONFIG.PENDIENTE;
              return (
                <div key={approval.id} className={`border-2 p-4 ${sc.bg}`}>
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm font-black uppercase truncate">
                        {approval.description || `Aprobación #${approval.id}`}
                      </p>
                      <p className="text-amber-400/60 text-[9px] uppercase">
                        {approval.entity_name || 'Entidad no especificada'}
                        {approval.requested_by_name && ` · Por: ${approval.requested_by_name}`}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0 ml-3">
                      <p className="text-white font-black text-sm">{fmt(approval.amount)}</p>
                      <p className={`text-[9px] font-black uppercase ${sc.color}`}>{sc.label}</p>
                    </div>
                  </div>

                  {approval.status === 'PENDIENTE' && (
                    <div className="flex gap-2 mt-3">
                      <input
                        value={resolveNote[approval.id] || ''}
                        onChange={e => setResolveNote(p => ({ ...p, [approval.id]: e.target.value }))}
                        placeholder="Nota opcional..."
                        className="flex-1 bg-black border border-amber-400/30 text-white text-[10px] p-1.5 font-mono outline-none focus:border-amber-400"
                      />
                      <button
                        onClick={() => onResolve(approval.id, 'APROBADO', resolveNote[approval.id] || '')}
                        className="bg-green-500 text-white text-[10px] font-black px-3 py-1.5 uppercase hover:bg-green-400">
                        ✓ APROBAR
                      </button>
                      <button
                        onClick={() => onResolve(approval.id, 'RECHAZADO', resolveNote[approval.id] || '')}
                        className="bg-red-500 text-white text-[10px] font-black px-3 py-1.5 uppercase hover:bg-red-400">
                        ✕ RECHAZAR
                      </button>
                    </div>
                  )}

                  {approval.notes && approval.status !== 'PENDIENTE' && (
                    <p className="text-amber-400/40 text-[9px] mt-2 font-mono">
                      NOTA: {approval.notes}
                    </p>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
