/* ============================================================
   Dialogos.jsx — Piezas de interfaz del organizador 📦 (13.5-b):
   Modal base (Esc / clic fuera cierra), menú ⋯ por tarjeta y los
   diálogos de texto, carpeta, elegir y confirmar. Paleta brutalista
   clara de Análisis (D-135-07): código propio, no el de RRHH.
   ============================================================ */
import { useEffect, useRef, useState } from 'react';
import { COLORES_CARPETA } from './organizador.js';

export const btn = 'border-2 border-black px-2 py-0.5 text-[10px] font-bold disabled:opacity-40 disabled:cursor-not-allowed';
export const btnNegro = `${btn} bg-black text-white hover:bg-brutalAmber hover:text-black`;
export const btnBlanco = `${btn} bg-white hover:bg-brutalNeutral`;
export const btnPeligro = `${btn} bg-white hover:bg-brutalCrimson hover:text-white`;

export function Modal({ titulo, onCerrar, children, pie, ancho = 'max-w-md', capa = 'z-[220]' }) {
  const ref = useRef(null);
  useEffect(() => {
    // Con un diálogo encima de la vista previa, Esc cierra solo el de arriba.
    const tecla = (e) => {
      if (e.key !== 'Escape') return;
      const abiertos = document.querySelectorAll('[aria-modal="true"]');
      if (abiertos[abiertos.length - 1] === ref.current) onCerrar();
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [onCerrar]);
  return (
    <div className={`fixed inset-0 ${capa} bg-black/60 flex items-center justify-center p-2 sm:p-4`}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onCerrar(); }}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={titulo}
        className={`bg-white border-2 border-black shadow-brutal w-full ${ancho} max-h-[94vh] flex flex-col font-mono text-black`}>
        <div className="flex items-center gap-2 border-b-2 border-black px-2 py-1 bg-brutalNeutral">
          <span className="font-bold text-[11px] truncate min-w-0">{titulo}</span>
          <button type="button" onClick={onCerrar} title="Cerrar (Esc)" aria-label="Cerrar"
            className="ml-auto border-2 border-black bg-white px-1.5 text-[10px] font-bold hover:bg-brutalCrimson hover:text-white">✕</button>
        </div>
        <div className="p-2 overflow-auto text-[11px] min-h-0 flex-1">{children}</div>
        {pie && <div className="border-t-2 border-black p-2 flex flex-wrap justify-end gap-1">{pie}</div>}
      </div>
    </div>
  );
}

export function AvisoError({ texto }) {
  if (!texto) return null;
  return <div role="alert" className="bg-brutalCrimson text-white border-2 border-black p-1 text-[10px]">{texto}</div>;
}

/** Menú ⋯ de una tarjeta. `acciones`: [{clave, etiqueta, onClick, peligro}] (los falsy se omiten). */
export function MenuAcciones({ acciones, titulo = 'Acciones' }) {
  const [abierto, setAbierto] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!abierto) return undefined;
    const fuera = (e) => { if (ref.current && !ref.current.contains(e.target)) setAbierto(false); };
    const tecla = (e) => { if (e.key === 'Escape') setAbierto(false); };
    document.addEventListener('mousedown', fuera);
    document.addEventListener('keydown', tecla);
    return () => { document.removeEventListener('mousedown', fuera); document.removeEventListener('keydown', tecla); };
  }, [abierto]);
  const lista = (acciones || []).filter(Boolean);
  if (!lista.length) return null;
  return (
    <div ref={ref} className="relative" onClick={(e) => e.stopPropagation()} onDoubleClick={(e) => e.stopPropagation()}>
      <button type="button" aria-label={titulo} title={titulo} aria-haspopup="menu" aria-expanded={abierto}
        onClick={() => setAbierto((a) => !a)}
        className="border-2 border-black bg-white px-1.5 text-[11px] font-bold leading-none py-0.5 hover:bg-brutalAmber">⋯</button>
      {abierto && (
        <div role="menu" className="absolute right-0 top-full mt-0.5 z-40 bg-white border-2 border-black shadow-brutal min-w-[180px]">
          {lista.map((a) => (
            <button key={a.clave} type="button" role="menuitem"
              onClick={() => { setAbierto(false); a.onClick(); }}
              className={`block w-full text-left px-2 py-1 text-[10px] font-bold border-b border-black/10 last:border-b-0 ${a.peligro ? 'hover:bg-brutalCrimson hover:text-white' : 'hover:bg-brutalAmber'}`}>
              {a.etiqueta}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function useEnvio(onOk) {
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');
  const enviar = async (valor) => {
    setEnviando(true);
    setError('');
    try { await onOk(valor); } catch (e) { setError(e.message || 'No se pudo.'); setEnviando(false); }
  };
  return { enviando, error, enviar };
}

export function DialogoTexto({ titulo, etiqueta, inicial = '', multilinea = false, max = 160, obligatorio = true, onOk, onCerrar }) {
  const [valor, setValor] = useState(inicial || '');
  const { enviando, error, enviar } = useEnvio(onOk);
  const vacio = obligatorio && !valor.trim();
  const ok = () => { if (!vacio && !enviando) enviar(valor.trim()); };
  return (
    <Modal titulo={titulo} onCerrar={onCerrar} pie={<>
      <button type="button" className={btnBlanco} onClick={onCerrar}>CANCELAR</button>
      <button type="button" className={btnNegro} disabled={vacio || enviando} onClick={ok}>{enviando ? 'GUARDANDO…' : 'GUARDAR'}</button>
    </>}>
      <label className="block space-y-1">
        <span className="font-bold text-[10px]">{etiqueta}</span>
        {multilinea ? (
          <textarea autoFocus value={valor} maxLength={max} rows={4} onChange={(e) => setValor(e.target.value)}
            className="w-full border-2 border-black p-1 text-[11px]" />
        ) : (
          <input autoFocus value={valor} maxLength={max} onChange={(e) => setValor(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') ok(); }}
            className="w-full border-2 border-black px-1 py-0.5 text-[11px]" />
        )}
      </label>
      <div className="mt-1"><AvisoError texto={error} /></div>
    </Modal>
  );
}

export function DialogoCarpeta({ titulo, inicial = {}, onOk, onCerrar }) {
  const [nombre, setNombre] = useState(inicial.nombre || '');
  const [color, setColor] = useState(inicial.color || COLORES_CARPETA[0]);
  const { enviando, error, enviar } = useEnvio(onOk);
  const ok = () => { if (nombre.trim() && !enviando) enviar({ nombre: nombre.trim(), color }); };
  return (
    <Modal titulo={titulo} onCerrar={onCerrar} pie={<>
      <button type="button" className={btnBlanco} onClick={onCerrar}>CANCELAR</button>
      <button type="button" className={btnNegro} disabled={!nombre.trim() || enviando} onClick={ok}>{enviando ? 'GUARDANDO…' : 'GUARDAR'}</button>
    </>}>
      <div className="space-y-2">
        <label className="block space-y-1">
          <span className="font-bold text-[10px]">Nombre</span>
          <input autoFocus value={nombre} maxLength={80} placeholder='Ej: "Para el banco 2026", "Auditoría"'
            onChange={(e) => setNombre(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') ok(); }}
            className="w-full border-2 border-black px-1 py-0.5 text-[11px]" />
        </label>
        <div role="radiogroup" aria-label="Color" className="flex flex-wrap gap-1">
          {COLORES_CARPETA.map((c) => (
            <button key={c} type="button" role="radio" aria-checked={color === c} aria-label={`Color ${c}`} title={c}
              onClick={() => setColor(c)} style={{ background: c }}
              className={`w-7 h-7 border-2 ${color === c ? 'border-black outline outline-2 outline-brutalAmber' : 'border-black/30'}`} />
          ))}
        </div>
        <div className="flex items-center gap-2 border-2 border-black p-1.5" style={{ borderLeft: `8px solid ${color}` }}>
          <span>📁</span><span className="font-bold truncate">{nombre || 'Vista previa'}</span>
        </div>
      </div>
      <div className="mt-1"><AvisoError texto={error} /></div>
    </Modal>
  );
}

/** Elegir una opción de una lista: [{valor, etiqueta, nivel?, deshabilitada?}]. */
export function DialogoElegir({ titulo, ayuda, opciones, actual, onOk, onCerrar }) {
  const [valor, setValor] = useState(actual ?? null);
  const { enviando, error, enviar } = useEnvio(onOk);
  return (
    <Modal titulo={titulo} onCerrar={onCerrar} pie={<>
      <button type="button" className={btnBlanco} onClick={onCerrar}>CANCELAR</button>
      <button type="button" className={btnNegro} disabled={enviando || valor === (actual ?? null)} onClick={() => enviar(valor)}>
        {enviando ? 'GUARDANDO…' : 'APLICAR'}
      </button>
    </>}>
      {ayuda && <p className="text-[10px] text-gray-700 mb-1">{ayuda}</p>}
      <div role="radiogroup" aria-label={titulo} className="border-2 border-black max-h-[50vh] overflow-auto">
        {opciones.map((o) => (
          <button key={String(o.valor)} type="button" role="radio" aria-checked={valor === o.valor}
            disabled={o.deshabilitada} onClick={() => setValor(o.valor)}
            style={{ paddingLeft: `${8 + (o.nivel || 0) * 14}px` }}
            className={`block w-full text-left pr-2 py-1 text-[10px] font-bold border-b border-black/10 disabled:opacity-40 ${valor === o.valor ? 'bg-black text-white' : 'hover:bg-brutalNeutral'}`}>
            {o.etiqueta}
          </button>
        ))}
      </div>
      <div className="mt-1"><AvisoError texto={error} /></div>
    </Modal>
  );
}

export function DialogoConfirmar({ titulo, texto, textoOk = 'CONFIRMAR', peligro = false, onOk, onCerrar }) {
  const { enviando, error, enviar } = useEnvio(onOk);
  return (
    <Modal titulo={titulo} onCerrar={onCerrar} pie={<>
      <button type="button" className={btnBlanco} onClick={onCerrar}>CANCELAR</button>
      <button type="button" autoFocus disabled={enviando} onClick={() => enviar()}
        className={peligro ? `${btn} bg-brutalCrimson text-white hover:bg-black` : btnNegro}>
        {enviando ? 'UN MOMENTO…' : textoOk}
      </button>
    </>}>
      <div className="text-[11px] leading-snug whitespace-pre-line">{texto}</div>
      <div className="mt-1"><AvisoError texto={error} /></div>
    </Modal>
  );
}
