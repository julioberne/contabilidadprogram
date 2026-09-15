import { ESTADO_STYLE } from '../fmt.js';

export default function EstadoBadge({ estado }) {
  const cls = ESTADO_STYLE[estado] || 'bg-gray-100 text-black';
  return (
    <span className={`inline-block border border-black px-1 text-[9px] font-bold tracking-wider ${cls}`}>
      {estado || '—'}
    </span>
  );
}
