/* MotivoModal — pide un motivo (rechazar / anular / reabrir). */
import { useState } from 'react';

export default function MotivoModal({ titulo, descripcion, confirmar = 'CONFIRMAR', onConfirm, onClose, busy }) {
  const [motivo, setMotivo] = useState('');
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white border-2 border-black shadow-brutal p-3 w-96 font-mono space-y-2"
           onClick={(e) => e.stopPropagation()}>
        <div className="font-bold text-[12px] border-b-2 border-black pb-1">{titulo}</div>
        {descripcion && <div className="text-[10px] text-gray-700">{descripcion}</div>}
        <textarea className="w-full border border-black p-1 text-[11px] h-20" autoFocus
                  placeholder="Motivo (obligatorio)" value={motivo}
                  onChange={(e) => setMotivo(e.target.value)} />
        <div className="flex justify-end gap-1">
          <button type="button" className="border border-black px-2 py-0.5 text-[10px]" onClick={onClose}>CANCELAR</button>
          <button type="button" disabled={!motivo.trim() || busy}
                  className="border-2 border-black bg-black text-white px-2 py-0.5 text-[10px] font-bold disabled:opacity-40"
                  onClick={() => onConfirm(motivo.trim())}>
            {busy ? '…' : confirmar}
          </button>
        </div>
      </div>
    </div>
  );
}
