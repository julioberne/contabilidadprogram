/* ============================================================
   TiposModal.jsx — Tipos documentales (las "categorías" de RRHH,
   versión contable): los default se renombran o recolorean pero no
   se borran; los propios se crean aquí y los borra un administrador.
   ============================================================ */
import { useState } from 'react';
import { api } from './api.js';
import { AvisoError, Modal, btnBlanco, btnNegro } from './Dialogos.jsx';
import { COLORES_CARPETA } from './organizador.js';

const campo = 'border-2 border-black px-1 py-0.5 text-[10px] bg-white';

function Fila({ t, admin, onCambio }) {
  const [editando, setEditando] = useState(false);
  const [nombre, setNombre] = useState(t.nombre);
  const [icono, setIcono] = useState(t.icono || '');
  const [color, setColor] = useState(t.color);
  const [error, setError] = useState('');
  const [ocupado, setOcupado] = useState(false);

  const correr = async (fn) => {
    setOcupado(true);
    setError('');
    try { await fn(); await onCambio(); setEditando(false); } catch (e) { setError(e.message); } finally { setOcupado(false); }
  };
  const guardar = () => correr(() => api.patch(`/accounting-doc-types/${t.id}`, { nombre: nombre.trim(), icono, color }));
  const borrar = () => {
    if (!window.confirm(`¿Borrar el tipo «${t.nombre}»? Sus ${t.n_archivos} archivo(s) quedan "sin tipo" (no se borran).`)) return;
    correr(() => api.del(`/accounting-doc-types/${t.id}`));
  };

  return (
    <li className="border-b border-black/10 py-1">
      {editando ? (
        <div className="flex flex-wrap items-center gap-1">
          <input aria-label="Icono" value={icono} maxLength={4} onChange={(e) => setIcono(e.target.value)} className={`${campo} w-10 text-center`} />
          <input aria-label="Nombre" autoFocus value={nombre} maxLength={60} onChange={(e) => setNombre(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && nombre.trim()) guardar(); }} className={`${campo} flex-1 min-w-[120px]`} />
          <span className="inline-flex gap-0.5" role="radiogroup" aria-label="Color">
            {COLORES_CARPETA.map((c) => (
              <button key={c} type="button" role="radio" aria-checked={color === c} aria-label={`Color ${c}`} onClick={() => setColor(c)}
                style={{ background: c }} className={`w-4 h-4 border ${color === c ? 'border-black outline outline-2 outline-brutalAmber' : 'border-black/30'}`} />
            ))}
          </span>
          <button type="button" className={btnNegro} disabled={ocupado || !nombre.trim()} onClick={guardar}>OK</button>
          <button type="button" className={btnBlanco} onClick={() => setEditando(false)}>✕</button>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-[10px]">
          <span className="w-3 h-3 border border-black shrink-0" style={{ background: t.color }} />
          <span className="font-bold truncate min-w-0 flex-1">{t.icono} {t.nombre}</span>
          {t.es_default && <span className="text-[8px] border border-black px-1 bg-brutalNeutral">DEFAULT</span>}
          <span className="text-gray-600">{t.n_archivos}</span>
          <button type="button" className="underline" onClick={() => setEditando(true)}>editar</button>
          {admin && !t.es_default && <button type="button" className="underline text-brutalCrimson" disabled={ocupado} onClick={borrar}>borrar</button>}
        </div>
      )}
      <AvisoError texto={error} />
    </li>
  );
}

export default function TiposModal({ tipos, admin, onCambio, onCerrar }) {
  const [nombre, setNombre] = useState('');
  const [icono, setIcono] = useState('🏷');
  const [error, setError] = useState('');
  const [ocupado, setOcupado] = useState(false);

  const crear = async () => {
    if (!nombre.trim()) return;
    setOcupado(true);
    setError('');
    try {
      await api.post('/accounting-doc-types', { nombre: nombre.trim(), icono, color: COLORES_CARPETA[tipos.length % COLORES_CARPETA.length] });
      setNombre('');
      await onCambio();
    } catch (e) { setError(e.message); } finally { setOcupado(false); }
  };

  return (
    <Modal titulo="🏷 Tipos documentales" onCerrar={onCerrar} ancho="max-w-lg" pie={
      <button type="button" className={btnBlanco} onClick={onCerrar}>LISTO</button>}>
      <p className="text-[10px] text-gray-700 mb-1">
        Clasifican los archivos en el lateral. Lo generado cae solo en su tipo (un cierre en 📘 Libros, una relación en
        📋 Relaciones); lo subido va a 📎 Soportes si no eliges otro.
      </p>
      <ul className="border-2 border-black px-1.5">
        {tipos.map((t) => <Fila key={t.id} t={t} admin={admin} onCambio={onCambio} />)}
      </ul>
      <div className="flex flex-wrap items-center gap-1 mt-2">
        <input aria-label="Icono del tipo nuevo" value={icono} maxLength={4} onChange={(e) => setIcono(e.target.value)} className={`${campo} w-10 text-center`} />
        <input aria-label="Nombre del tipo nuevo" value={nombre} maxLength={60} placeholder="Nuevo tipo (ej: Nómina, Contratos)"
          onChange={(e) => setNombre(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') crear(); }} className={`${campo} flex-1 min-w-[160px]`} />
        <button type="button" className={btnNegro} disabled={ocupado || !nombre.trim()} onClick={crear}>+ CREAR</button>
      </div>
      <div className="mt-1"><AvisoError texto={error} /></div>
    </Modal>
  );
}
