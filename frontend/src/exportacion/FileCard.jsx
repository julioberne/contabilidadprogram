/* FileCard.jsx — Archivo del organizador 📦 en cuadrícula (tarjeta) o lista (fila).
   Clic → vista previa. Insignias: ✅ vigente / ⚠ cambió / 📌 fijado / ⏳ por vencer. */
import { MenuAcciones } from './Dialogos.jsx';
import {
  diasParaVencer, estadoVigencia, etiquetaPeriodo, fechaHora, formatoBytes, iconoArchivo,
} from './organizador.js';

function Insignias({ item, tipo }) {
  const vig = estadoVigencia(item);
  const dias = diasParaVencer(item);
  return (
    <div className="flex flex-wrap gap-1 items-center">
      {vig && (
        <span title={vig.detalles.length ? vig.detalles.join('\n') : 'Los libros no cambiaron desde esta exportación'}
          className={`text-[8px] font-bold border border-black px-1 ${vig.tono === 'ok' ? 'bg-brutalGreen' : 'bg-brutalAmber'}`}>
          {vig.icono} {vig.texto}
        </span>
      )}
      {item.fijado && <span title="Fijado: no se purga" className="text-[8px] font-bold border border-black px-1 bg-white">📌 FIJADO</span>}
      {dias !== null && (
        <span title={`Se purga el ${item.vence_el} si no lo fijas`} className="text-[8px] font-bold border border-black px-1 bg-brutalNeutral">
          ⏳ {dias === 0 ? 'vence hoy' : `${dias} d`}
        </span>
      )}
      {tipo && (
        <span title={`Tipo documental: ${tipo.nombre}`} style={{ borderColor: tipo.color, color: tipo.color }}
          className="text-[8px] font-bold border px-1 bg-white truncate max-w-[120px]">
          {tipo.icono} {tipo.nombre}
        </span>
      )}
    </div>
  );
}

export default function FileCard({ item, tipo, vista = 'grid', onAbrir, acciones }) {
  const { icono, ext } = iconoArchivo(item.mime_type, item.nombre_archivo);
  const lugar = [item.empresa || (item.origen === 'GENERADO' ? 'Consolidado' : null),
    item.periodo_hasta ? etiquetaPeriodo(item.periodo_desde, item.periodo_hasta) : null].filter(Boolean).join(' · ');
  const abrirConTecla = (e) => { if (e.key === 'Enter') { e.preventDefault(); onAbrir(); } };

  if (vista === 'lista') {
    return (
      <div role="button" tabIndex={0} onClick={onAbrir} onKeyDown={abrirConTecla} title={`Ver ${item.nombre}`}
        className="bg-white border-2 border-black px-2 py-1 flex flex-wrap sm:flex-nowrap items-center gap-2 cursor-pointer hover:bg-brutalBg focus:outline focus:outline-2 focus:outline-brutalAmber">
        <span className="text-[16px] leading-none shrink-0">{icono}</span>
        <div className="min-w-0 flex-1">
          <div className="font-bold text-[11px] truncate">{item.nombre}</div>
          <div className="text-[9px] text-gray-700 truncate">
            {item.folio ? <b className="text-black">{item.folio}</b> : <span>SUBIDO</span>}{lugar ? ` · ${lugar}` : ''}
          </div>
        </div>
        <div className="shrink-0"><Insignias item={item} tipo={tipo} /></div>
        <span className="text-[9px] text-gray-700 shrink-0 w-14 text-right">{formatoBytes(item.tamano_bytes)}</span>
        <span className="text-[9px] text-gray-700 shrink-0 w-24 text-right hidden sm:inline">{fechaHora(item.creado_en)}</span>
        <MenuAcciones acciones={acciones} titulo={`Acciones de ${item.nombre}`} />
      </div>
    );
  }

  return (
    <div role="button" tabIndex={0} onClick={onAbrir} onKeyDown={abrirConTecla} title={`Ver ${item.nombre}`}
      className="bg-white border-2 border-black p-2 flex flex-col gap-1 cursor-pointer min-h-[132px] hover:shadow-brutal hover:-translate-y-px focus:outline focus:outline-2 focus:outline-brutalAmber transition-shadow">
      <div className="flex items-start gap-1">
        <span className="text-[22px] leading-none">{icono}</span>
        <span className="text-[8px] font-bold bg-black text-white px-1 mt-0.5">{ext}</span>
        <div className="ml-auto"><MenuAcciones acciones={acciones} titulo={`Acciones de ${item.nombre}`} /></div>
      </div>
      <div className="font-bold text-[11px] leading-tight break-words line-clamp-2">{item.nombre}</div>
      <div className="text-[10px] font-bold">{item.folio || <span className="text-gray-600 font-normal">documento subido</span>}</div>
      {lugar && <div className="text-[9px] text-gray-700 truncate">{lugar}</div>}
      <div className="text-[9px] text-gray-600">{formatoBytes(item.tamano_bytes)} · {fechaHora(item.creado_en).slice(0, 10)}</div>
      <div className="mt-auto"><Insignias item={item} tipo={tipo} /></div>
    </div>
  );
}
