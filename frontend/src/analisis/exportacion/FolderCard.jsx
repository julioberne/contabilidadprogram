/* FolderCard.jsx — Tarjeta de carpeta del organizador 📦 (automática o propia). */
import { MenuAcciones } from './Dialogos.jsx';

export default function FolderCard({ etiqueta, n, icono = '📁', color = '#000000', onAbrir, acciones, titulo }) {
  return (
    <div role="button" tabIndex={0} title={titulo || `Abrir ${etiqueta}`}
      onClick={onAbrir} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onAbrir(); } }}
      style={{ borderLeft: `8px solid ${color}` }}
      className="bg-white border-2 border-black px-2 py-1.5 flex items-center gap-2 cursor-pointer hover:shadow-brutal hover:-translate-y-px focus:outline focus:outline-2 focus:outline-brutalAmber transition-shadow">
      <span className="text-[18px] leading-none shrink-0">{icono}</span>
      <span className="font-bold text-[11px] truncate min-w-0 flex-1">{etiqueta}</span>
      <span className="text-[9px] border border-black px-1 bg-brutalNeutral shrink-0" title={`${n} archivo(s)`}>{n}</span>
      {acciones && <MenuAcciones acciones={acciones} titulo={`Acciones de la carpeta ${etiqueta}`} />}
    </div>
  );
}
