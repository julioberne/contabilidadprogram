// CTCollaborators.jsx — Panel de gestión de colaboradores y roles dinámicos
import React, { useState } from 'react';

const PERMISSION_LABELS = {
  ledger: 'Libro Mayor',
  reports: 'Reportes',
  users: 'Gestión Usuarios',
  approvals: 'Aprobaciones',
};

const PERM_PRESETS = {
  'Super-Contador': { ledger: true, reports: true, users: true, approvals: true },
  'Contador': { ledger: true, reports: true, users: false, approvals: true },
  'Auditor': { ledger: false, reports: true, users: false, approvals: false },
  'Colaborador': { ledger: true, reports: false, users: false, approvals: false },
  'Cliente': { ledger: false, reports: true, users: false, approvals: false },
};

export default function CTCollaborators({
  members, users, activeEntity,
  onInvite, onClose
}) {
  const [showInvite, setShowInvite] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [roleLabel, setRoleLabel] = useState('Colaborador');
  const [preset, setPreset] = useState('Colaborador');
  const [permissions, setPermissions] = useState(PERM_PRESETS['Colaborador']);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const applyPreset = (p) => {
    setPreset(p);
    setRoleLabel(p);
    setPermissions(PERM_PRESETS[p] || PERM_PRESETS['Colaborador']);
  };

  const handleInvite = async () => {
    if (!selectedUserId) { alert('Selecciona un usuario.'); return; }
    setIsSubmitting(true);
    try {
      await onInvite(parseInt(selectedUserId), roleLabel, permissions);
      setShowInvite(false);
      setSelectedUserId('');
    } catch (e) {
      alert(`Error: ${e.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Users not yet in members
  const memberIds = members.map(m => m.user_id);
  const availableUsers = users.filter(u => !memberIds.includes(u.id));

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-[100]">
      <div className="bg-black border-4 border-amber-400 w-full max-w-2xl shadow-[8px_8px_0px_#fbbf24] font-mono flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b-2 border-amber-400 flex-shrink-0">
          <div>
            <p className="text-amber-400/60 text-[10px] uppercase font-bold">
              {activeEntity?.name || 'Entidad'}
            </p>
            <h3 className="text-amber-400 font-black uppercase">👥 GESTIÓN DE COLABORADORES</h3>
          </div>
          <button onClick={onClose} className="text-amber-400 hover:text-white font-black text-xl">✕</button>
        </div>

        {/* Current Members */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-white text-xs font-black uppercase">
              MIEMBROS ACTIVOS ({members.length})
            </p>
            <button
              onClick={() => setShowInvite(p => !p)}
              className="bg-amber-400 text-black text-[9px] font-black px-3 py-1.5 uppercase hover:bg-amber-300">
              + INVITAR COLABORADOR
            </button>
          </div>

          {/* Invite Form */}
          {showInvite && (
            <div className="border-2 border-amber-400/40 p-4 bg-amber-400/5 space-y-3">
              <p className="text-amber-400 text-[10px] font-black uppercase">+ NUEVO COLABORADOR</p>

              <div>
                <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">
                  USUARIO DEL WORKSPACE *
                </label>
                <select value={selectedUserId}
                  onChange={e => setSelectedUserId(e.target.value)}
                  className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-xs font-mono outline-none focus:border-amber-400">
                  <option value="">— Seleccionar usuario —</option>
                  {availableUsers.map(u => (
                    <option key={u.id} value={u.id}>{u.name} ({u.email})</option>
                  ))}
                </select>
                {availableUsers.length === 0 && (
                  <p className="text-amber-400/40 text-[9px] mt-1">
                    Todos los usuarios ya son miembros. Registra nuevos usuarios primero.
                  </p>
                )}
              </div>

              <div>
                <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">
                  ROL PERSONALIZADO
                </label>
                <input value={roleLabel}
                  onChange={e => setRoleLabel(e.target.value)}
                  placeholder="Ej: Contador Externo, Socio, Auditor..."
                  className="w-full bg-black border-2 border-amber-400/50 text-white p-2 text-sm font-mono outline-none focus:border-amber-400" />
              </div>

              {/* Preset buttons */}
              <div>
                <label className="text-amber-400/60 text-[10px] uppercase font-bold block mb-1">
                  PRESET DE PERMISOS
                </label>
                <div className="flex flex-wrap gap-1">
                  {Object.keys(PERM_PRESETS).map(p => (
                    <button key={p}
                      onClick={() => applyPreset(p)}
                      className={`px-2 py-1 text-[9px] font-black uppercase transition-colors ${
                        preset === p ? 'bg-amber-400 text-black' : 'border border-amber-400/30 text-amber-400/60 hover:border-amber-400'
                      }`}>
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              {/* Permissions Matrix */}
              <div className="border border-amber-400/20 p-3 bg-black">
                <p className="text-amber-400/60 text-[9px] uppercase font-bold mb-2">MATRIZ DE PERMISOS</p>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(PERMISSION_LABELS).map(([key, label]) => (
                    <label key={key} className="flex items-center gap-2 cursor-pointer group">
                      <input
                        type="checkbox"
                        checked={permissions[key] || false}
                        onChange={e => setPermissions(p => ({ ...p, [key]: e.target.checked }))}
                        className="accent-amber-400 w-3 h-3"
                      />
                      <span className={`text-[10px] font-bold uppercase transition-colors ${
                        permissions[key] ? 'text-white' : 'text-white/30'
                      }`}>
                        {label}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                <button onClick={() => setShowInvite(false)}
                  className="flex-1 border-2 border-amber-400/40 text-amber-400/60 py-2 text-xs font-black uppercase hover:border-amber-400">
                  CANCELAR
                </button>
                <button onClick={handleInvite} disabled={isSubmitting}
                  className="flex-1 bg-amber-400 text-black py-2 text-xs font-black uppercase hover:bg-amber-300 disabled:opacity-50">
                  {isSubmitting ? 'INVITANDO...' : '✓ ASIGNAR ACCESO'}
                </button>
              </div>
            </div>
          )}

          {/* Members List */}
          {members.length === 0 ? (
            <div className="text-center py-8 border-2 border-dashed border-amber-400/20">
              <p className="text-4xl text-amber-400/30 mb-3">👥</p>
              <p className="text-amber-400/60 text-xs font-bold uppercase">Sin colaboradores asignados</p>
              <p className="text-white/30 text-[10px] mt-1">Invita a contadores, auditores o socios</p>
            </div>
          ) : (
            <div className="space-y-2">
              {members.map(m => (
                <div key={m.id} className="border-2 border-amber-400/20 hover:border-amber-400/50 p-3 transition-colors flex items-center gap-4">
                  {/* Avatar */}
                  <div className="w-10 h-10 bg-amber-400 text-black font-black flex items-center justify-center text-sm flex-shrink-0">
                    {(m.name || 'U')[0].toUpperCase()}
                  </div>
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-black text-sm uppercase">{m.name}</p>
                    <p className="text-amber-400/60 text-[10px]">{m.email}</p>
                  </div>
                  {/* Role badge */}
                  <div className="text-right flex-shrink-0">
                    <span className="border border-amber-400/50 text-amber-400 text-[9px] font-black uppercase px-2 py-0.5">
                      {m.role_label}
                    </span>
                    {m.expires_at && (
                      <p className="text-white/30 text-[9px] mt-1">Vence: {m.expires_at?.split('T')[0]}</p>
                    )}
                  </div>
                  {/* Perms */}
                  <div className="hidden sm:flex flex-col gap-0.5 flex-shrink-0">
                    {Object.entries(PERMISSION_LABELS).map(([k, label]) => {
                      const perms = typeof m.permissions === 'string' ? JSON.parse(m.permissions) : m.permissions || {};
                      return (
                        <span key={k} className={`text-[8px] font-bold uppercase ${perms[k] ? 'text-green-400' : 'text-white/15'}`}>
                          {perms[k] ? '✓' : '○'} {label}
                        </span>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="border-t-2 border-amber-400/20 px-5 py-2 flex-shrink-0">
          <p className="text-amber-400/30 text-[9px] font-mono uppercase">
            {members.length} COLABORADOR(ES) // ENTITY: {activeEntity?.name || 'N/A'}
          </p>
        </div>
      </div>
    </div>
  );
}
