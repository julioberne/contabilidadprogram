/* ============================================================
   BuscadorRemoto.jsx — Selector con búsqueda en el servidor
   (estándar de consultas H3, F1–F4). Reemplaza a los selectores
   que descargaban el catálogo entero (terceros, cuentas, etiquetas).

   - Combobox accesible (patrón WAI-ARIA APG): el foco queda en el
     input; ↑/↓ recorren, Enter elige, Esc cierra.
   - Muestra el top-N del servidor y, si hay más, «escribe más para
     afinar». Con menos de `minimo` caracteres no consulta.

     <BuscadorRemoto recurso="terceros" onElegir={(t) => …} />
   ============================================================ */
import { useId, useState } from 'react';
import { useBusqueda } from './useBusqueda.js';

const subtituloPorDefecto = (it) => [it.identification_type, it.identification_number].filter(Boolean).join(' ')
  || [it.type, it.currency].filter(Boolean).join(' · ');

export default function BuscadorRemoto({
  recurso = 'terceros', onElegir, placeholder = '🔍 Buscar…', minimo = 2, limite = 8,
  etiqueta = 'Buscar', subtitulo = subtituloPorDefecto, version, onNoAutorizado, className = '',
}) {
  const [q, setQ] = useState('');
  const [abierto, setAbierto] = useState(false);
  const [activo, setActivo] = useState(-1);
  const idLista = useId();
  const { items, mas, cargando, error } = useBusqueda(recurso, q, { minimo, limite, version, onNoAutorizado });
  const corto = q.trim().length < minimo;

  const elegir = (it) => { onElegir?.(it); setQ(''); setAbierto(false); setActivo(-1); };
  const teclas = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setAbierto(true); setActivo((i) => Math.min(items.length - 1, i + 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActivo((i) => Math.max(0, i - 1)); }
    else if (e.key === 'Enter' && abierto && items[activo]) { e.preventDefault(); elegir(items[activo]); }
    else if (e.key === 'Escape') { setAbierto(false); setActivo(-1); }
  };

  return (
    <div className={`relative ${className}`}>
      <input
        type="search" value={q} placeholder={placeholder} aria-label={etiqueta}
        role="combobox" aria-expanded={abierto && !corto} aria-controls={idLista} aria-autocomplete="list"
        aria-activedescendant={activo >= 0 ? `${idLista}-${activo}` : undefined}
        onChange={(e) => { setQ(e.target.value); setAbierto(true); setActivo(-1); }}
        onFocus={() => setAbierto(true)} onBlur={() => setTimeout(() => setAbierto(false), 150)} onKeyDown={teclas}
        className="w-full border-2 border-black px-2 py-1.5 text-xs font-mono outline-none focus:border-brutalGreen bg-white" />
      {abierto && !corto && (
        <ul id={idLista} role="listbox" aria-label={`Resultados de ${etiqueta}`}
          className="absolute z-40 left-0 right-0 mt-0.5 bg-white border-2 border-black shadow-brutal max-h-64 overflow-y-auto">
          {cargando && !items.length && <li className="px-2 py-1 text-[10px] font-mono text-gray-400 uppercase">Buscando…</li>}
          {error && <li role="alert" className="px-2 py-1 text-[10px] font-mono text-red-700">{error}</li>}
          {!cargando && !error && !items.length && (
            <li className="px-2 py-1 text-[10px] font-mono text-gray-500">Nadie coincide con «{q.trim()}».</li>
          )}
          {items.map((it, i) => (
            <li key={it.id ?? it.name} id={`${idLista}-${i}`} role="option" aria-selected={i === activo}
              onMouseDown={(e) => { e.preventDefault(); elegir(it); }}
              className={`px-2 py-1 text-xs font-mono cursor-pointer border-b border-gray-100 ${i === activo ? 'bg-black text-white' : 'hover:bg-brutalBg'}`}>
              <span className="font-bold">{it.name}</span>
              {subtitulo(it) && <span className={i === activo ? 'text-gray-300' : 'text-gray-500'}> · {subtitulo(it)}</span>}
            </li>
          ))}
          {mas && <li className="px-2 py-1 text-[10px] font-mono text-gray-500 uppercase">Hay más: escribe más para afinar</li>}
        </ul>
      )}
    </div>
  );
}
