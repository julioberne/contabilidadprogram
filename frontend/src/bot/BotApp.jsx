/* ============================================================
   BotApp.jsx — Módulo 09 Bot IA (slot 'bot' del registry).
   Hoy: la bandeja de borradores (Etapa C). Etapas futuras
   (consultas, comandos) se agregan aquí sin tocar el registry.
   ============================================================ */
import BotDraftsPanel from './BotDraftsPanel.jsx';

export default function BotApp() {
  return (
    <div className="min-h-screen bg-brutalBg text-black font-mono p-2 space-y-2 antialiased">
      <BotDraftsPanel />
    </div>
  );
}
