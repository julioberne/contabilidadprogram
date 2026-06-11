// CTSidePanel.jsx — Panel lateral de acciones rápidas (Zona 3)
import React, { useState } from 'react';

// ── Quick Transaction Modal ────────────────────────────────────────────────────
function QuickTxModal({ isOpen, onClose, onSubmit, activeEntity }) {
  const [form, setForm] = useState({
    type: 'INGRESO',
    amount: '',
    concept: '',
    category: 'Ventas',
    payment_method: 'Efectivo',
    portfolio_name: activeEntity?.name || 'Negocio A',
    third_party_name: '',
    third_party_id_number: '',
    third_party_id_type: 'NIT',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async () => {
    if (!form.amount || !form.concept || !form.third_party_name) {
      alert('Monto, concepto y tercero son obligatorios.');
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await onSubmit({ ...form, amount: parseFloat(form.amount) });
      setResult({ ok: true, id: res.transaction_id });
    } catch (e) {
      setResult({ ok: false, msg: e.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-[100]">
      <div className="bg-black border-4 border-amber-400 p-5 w-full max-w-md shadow-[8px_8px_0px_#fbbf24] font-mono max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center border-b-2 border-amber-400 pb-3 mb-4">
          <div>
            <p className="text-amber-400/60 text-[10px] uppercase font-bold">CONTROL TOWER</p>
            <h3 className="text-amber-400 font-black uppercase text-sm">📝 TRANSACCIÓN RÁPIDA</h3>
          </div>
          <button onClick={onClose} className="text-amber-400 hover:text-white font-black text-lg">✕</button>
        </div>

        {result ? (
          <div className={`p-4 border-2 text-center ${result.ok ? 'border-green-400 text-green-400' : 'border-red-400 text-red-400'}`}>
            <p className="text-2xl mb-2">{result.ok ? '✓' : '✕'}</p>
            <p className="font-black uppercase text-sm">
              {result.ok ? `REGISTRADO — TX#${result.id}` : `ERROR: ${result.msg}`}
            </p>
            <button onClick={() => { setResult(null); if (result.ok) onClose(); }}
              className="mt-3 bg-amber-400 text-black px-4 py-1.5 text-xs font-black uppercase hover:bg-amber-300">
              {result.ok ? 'CERRAR' : 'REINTENTAR'}
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Tipo */}
            <div className="flex gap-2">
              {['INGRESO', 'GASTO'].map(t => (
                <button key={t}
                  onClick={() => setForm(p => ({ ...p, type: t }))}
                  className={`flex-1 py-2 text-xs font-black uppercase transition-colors ${
                    form.type === t
                      ? (t === 'INGRESO' ? 'bg-green-500 text-white' : 'bg-red-500 text-white')
                      : 'border-2 border-amber-400/40 text-amber-400/60 hover:border-amber-400'
                  }`}>
                  {t === 'INGRESO' ? '▲ INGRESO' : '▼ GASTO'}
                </button>
              ))}
            </div>

            {/* Entidad/Portafolio */}
            <div>
              <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">PORTAFOLIO VINCULADO</label>
              <input value={form.portfolio_name}
                onChange={e => setForm(p => ({ ...p, portfolio_name: e.target.value }))}
                placeholder="Nombre del portafolio"
                className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-sm font-mono outline-none focus:border-amber-400" />
            </div>

            {/* Monto + Concepto */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">MONTO *</label>
                <input type="number" value={form.amount}
                  onChange={e => setForm(p => ({ ...p, amount: e.target.value }))}
                  placeholder="0"
                  className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-sm font-mono outline-none focus:border-amber-400" />
              </div>
              <div>
                <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">MÉTODO PAGO</label>
                <select value={form.payment_method}
                  onChange={e => setForm(p => ({ ...p, payment_method: e.target.value }))}
                  className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-xs font-mono outline-none focus:border-amber-400">
                  {['Efectivo', 'Transferencia', 'Tarjeta Débito', 'Tarjeta Crédito', 'Cheque'].map(m => (
                    <option key={m}>{m}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">CONCEPTO *</label>
              <input value={form.concept}
                onChange={e => setForm(p => ({ ...p, concept: e.target.value }))}
                placeholder="Descripción breve de la transacción"
                className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-sm font-mono outline-none focus:border-amber-400" />
            </div>

            <div>
              <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">CATEGORÍA</label>
              <select value={form.category}
                onChange={e => setForm(p => ({ ...p, category: e.target.value }))}
                className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-xs font-mono outline-none focus:border-amber-400">
                {['Ventas', 'Servicios', 'Nómina', 'Infraestructura', 'Marketing', 'Impuestos', 'Otros'].map(c => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </div>

            {/* Tercero */}
            <div className="border-t border-amber-400/20 pt-3">
              <p className="text-amber-400/40 text-[9px] uppercase font-bold mb-2">TERCERO</p>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">TIPO ID</label>
                  <select value={form.third_party_id_type}
                    onChange={e => setForm(p => ({ ...p, third_party_id_type: e.target.value }))}
                    className="w-full bg-black border-2 border-amber-400/50 text-white p-1.5 text-xs font-mono outline-none">
                    <option>NIT</option>
                    <option>CC</option>
                    <option>CE</option>
                  </select>
                </div>
                <div>
                  <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">No. ID</label>
                  <input value={form.third_party_id_number}
                    onChange={e => setForm(p => ({ ...p, third_party_id_number: e.target.value }))}
                    placeholder="12345"
                    className="w-full bg-black border-2 border-amber-400/50 text-white p-1.5 text-xs font-mono outline-none" />
                </div>
                <div>
                  <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">NOMBRE *</label>
                  <input value={form.third_party_name}
                    onChange={e => setForm(p => ({ ...p, third_party_name: e.target.value }))}
                    placeholder="Empresa / Persona"
                    className="w-full bg-black border-2 border-amber-400/50 text-white p-1.5 text-xs font-mono outline-none" />
                </div>
              </div>
            </div>

            <button onClick={handleSubmit} disabled={isSubmitting}
              className="w-full bg-amber-400 text-black py-3 font-black uppercase text-sm hover:bg-amber-300 disabled:opacity-50 transition-colors">
              {isSubmitting ? 'REGISTRANDO...' : `▲ REGISTRAR ${form.type}`}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Side Panel ─────────────────────────────────────────────────────────────────
export default function CTSidePanel({
  activeEntity, session,
  onOpenApprovals, onOpenResources, onOpenCollaborators,
  onQuickTransaction
}) {
  const [showTxModal, setShowTxModal] = useState(false);

  const actions = [
    {
      icon: '📝',
      label: 'REGISTRAR TRANSACCIÓN',
      sub: 'Registrar venta/gasto',
      color: 'hover:bg-amber-400 hover:text-black border-amber-400/50',
      onClick: () => setShowTxModal(true),
      disabled: !activeEntity,
    },
    {
      icon: '📋',
      label: 'COLA DE APROBACIONES',
      sub: 'Revisar pendientes',
      color: 'hover:bg-red-500 hover:text-white border-red-500/50',
      onClick: onOpenApprovals,
      disabled: !activeEntity,
    },
    {
      icon: '👥',
      label: 'GESTIONAR COLABORADORES',
      sub: 'Invitar / asignar roles',
      color: 'hover:bg-blue-500 hover:text-white border-blue-500/50',
      onClick: onOpenCollaborators,
      disabled: !activeEntity,
    },
    {
      icon: '🪪',
      label: 'INVENTARIO DE IDs',
      sub: 'NIT, RUT, Contratos...',
      color: 'hover:bg-purple-500 hover:text-white border-purple-500/50',
      onClick: onOpenResources,
      disabled: !activeEntity,
    },
  ];

  return (
    <div className="flex flex-col h-full bg-black">
      {/* Header */}
      <div className="px-4 py-2.5 border-b-2 border-amber-400/30 flex-shrink-0">
        <p className="text-amber-400 text-[10px] font-black uppercase tracking-widest">ZONA 3</p>
        <p className="text-white text-xs font-black uppercase">EL PANEL LATERAL</p>
      </div>

      {/* Context indicator */}
      {activeEntity ? (
        <div className="mx-3 mt-3 p-2 border border-amber-400/40 bg-amber-400/5 flex-shrink-0">
          <p className="text-[9px] text-amber-400/60 uppercase font-bold">ENTIDAD ACTIVA</p>
          <p className="text-amber-400 text-xs font-black uppercase truncate">{activeEntity.name}</p>
        </div>
      ) : (
        <div className="mx-3 mt-3 p-2 border border-amber-400/20 bg-black flex-shrink-0">
          <p className="text-[9px] text-amber-400/30 uppercase font-bold text-center">
            ← Selecciona una entidad para habilitar las acciones
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex-1 p-3 space-y-2 overflow-y-auto">
        {actions.map((action, idx) => (
          <button
            key={idx}
            onClick={action.onClick}
            disabled={action.disabled}
            className={`w-full border-2 p-3 text-left transition-all group ${action.color} ${
              action.disabled ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'
            }`}
          >
            <div className="flex items-center gap-3">
              <span className="text-xl flex-shrink-0">{action.icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-white text-xs font-black uppercase group-hover:text-current truncate">
                  {action.label}
                </p>
                <p className="text-amber-400/40 text-[9px] group-hover:text-current/60 truncate">
                  {action.sub}
                </p>
              </div>
              <span className="text-amber-400/40 group-hover:text-current text-sm">›</span>
            </div>
          </button>
        ))}
      </div>

      {/* System Status */}
      <div className="border-t-2 border-amber-400/20 p-3 bg-black/50 flex-shrink-0">
        <div className="border border-amber-400/20 p-2 font-mono text-[9px] text-amber-400/60">
          <p>SYS.STATUS: ONLINE</p>
          <p>SESSION: {session?.name?.split(' ')[0] || 'N/A'}</p>
          <p>UPLINK: SECURE [LOCAL]</p>
          <p>TRACE: ACTIVE_LOG_V2</p>
          <span className="inline-block w-2 h-2 bg-amber-400 animate-pulse mt-1" />
        </div>
      </div>

      <QuickTxModal
        isOpen={showTxModal}
        onClose={() => setShowTxModal(false)}
        onSubmit={onQuickTransaction}
        activeEntity={activeEntity}
      />
    </div>
  );
}
