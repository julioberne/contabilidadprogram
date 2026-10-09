/* ============================================================
   BotApp.jsx — Módulo 09 Bot IA (slot 'bot' del registry).
   Pestañas: 🗂 Borradores (bandeja, Etapa C) y 📓 Bitácora
   (anomalías del bot, 9-oct-2026). Etapas futuras se agregan
   aquí como otra pestaña sin tocar el registry.
   ============================================================ */
import { useState } from 'react';
import BotDraftsPanel from './BotDraftsPanel.jsx';
import BotBitacoraPanel from './BotBitacoraPanel.jsx';

const PESTANAS = [
  { id: 'borradores', label: '🗂 Borradores' },
  { id: 'bitacora', label: '📓 Bitácora' },
];

export default function BotApp() {
  const [pestana, setPestana] = useState('borradores');
  return (
    <div className="min-h-screen bg-brutalBg text-black font-mono p-2 space-y-2 antialiased">
      <div role="tablist" className="flex gap-1">
        {PESTANAS.map(p => (
          <button key={p.id} type="button" role="tab" aria-selected={pestana === p.id}
            onClick={() => setPestana(p.id)}
            className={`border-2 border-black px-3 py-1 text-xs font-bold uppercase ${pestana === p.id ? 'bg-black text-white' : 'bg-white hover:bg-brutalGreen'}`}>
            {p.label}
          </button>
        ))}
      </div>
      {pestana === 'borradores' ? <BotDraftsPanel /> : <BotBitacoraPanel />}
    </div>
  );
}
