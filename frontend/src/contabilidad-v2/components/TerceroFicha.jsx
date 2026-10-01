/* ============================================================
   TerceroFicha.jsx — La ficha completa de un tercero (etapa 09.I):
   los mismos campos de la fila expandida del panel Terceros de la
   web + sus medios de pago (TerceroMediosPago). Reutilizable fuera
   del ContextPanel: hoy la abre la Mini App de Telegram.

   Guardar = PUT /api/third-parties/{id} (edición deliberada de la
   ficha, D-09I-08). Si el documento escrito ya es de otra ficha el
   servidor responde 409 y aquí se ofrece «Usar esa ficha». Un
   provisional (SN-…) conserva su número mientras no se escriba otro.
   Eliminar = DELETE /api/third-parties/{id}, que responde 409 si el
   tercero tiene historia (transacciones/cartera/borradores).
   ============================================================ */
import { useState } from 'react';
import { API } from '../../config';
import TerceroMediosPago from './TerceroMediosPago';

const TIPOS = ['NIT', 'CC', 'CE', 'PP'];
const esProvisional = (num) => (num || '').startsWith('SN-');

export default function TerceroFicha({ tercero, onGuardado, onEliminado, onCerrar, onUsarExistente }) {
  const [f, setF] = useState({
    name: tercero.name || '', identification_type: tercero.identification_type || 'CC',
    // El SN- no se muestra: el campo queda libre para escribir el documento real
    identification_number: esProvisional(tercero.identification_number) ? '' : (tercero.identification_number || ''),
    email: tercero.email || '', phone: tercero.phone || '', address: tercero.address || '', website: tercero.website || '',
  });
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState('');
  const [error, setError] = useState('');
  const [existe, setExiste] = useState(null);   // {mensaje, tercero} tras un 409

  const provisional = esProvisional(tercero.identification_number) && f.identification_number.trim() === '';
  const campo = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const guardar = async () => {
    if (!f.name.trim()) { setError('El nombre es obligatorio.'); return; }
    setGuardando(true); setError(''); setAviso(''); setExiste(null);
    const num = f.identification_number.trim();
    const cuerpo = {
      name: f.name.trim(), identification_type: f.identification_type,
      // vacío → se conserva el número que tenía (el SN- del provisional, o el real)
      identification_number: num || tercero.identification_number,
      email: f.email.trim(), phone: f.phone.trim(), address: f.address.trim(), website: f.website.trim(),
    };
    try {
      const r = await fetch(`${API}/third-parties/${tercero.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo),
      });
      const resp = await r.json().catch(() => ({}));
      if (r.status === 409 && resp.codigo === 'existe') {
        setExiste({ mensaje: resp.detail, tercero: resp.tercero });
        return;
      }
      if (!r.ok) { setError(resp.detail || 'No se pudo guardar la ficha.'); return; }
      setAviso('Ficha guardada.');
      onGuardado?.({ ...tercero, ...cuerpo });
    } catch {
      setError('Sin conexión con el servidor.');
    } finally {
      setGuardando(false);
    }
  };

  const eliminar = async () => {
    if (!window.confirm(`¿Eliminar a «${tercero.name}»? Solo se puede si no tiene transacciones.`)) return;
    setError(''); setAviso('');
    try {
      const r = await fetch(`${API}/third-parties/${tercero.id}`, { method: 'DELETE' });
      const resp = await r.json().catch(() => ({}));
      if (!r.ok) { setError(resp.detail || 'No se pudo eliminar.'); return; }
      onEliminado?.(tercero);
    } catch {
      setError('Sin conexión con el servidor.');
    }
  };

  const input = 'w-full border-2 border-black px-2 py-2 text-sm font-mono outline-none focus:border-brutalGreen bg-white';

  return (
    <div className="border-2 border-black p-2 bg-brutalBg space-y-2">
      <div className="flex items-center justify-between border-b border-dashed border-gray-300 pb-1">
        <div className="text-[10px] font-mono text-gray-500 uppercase">Ficha del tercero · #{tercero.id}</div>
        {onCerrar && (
          <button type="button" onClick={onCerrar} aria-label="Cerrar ficha"
            className="border-2 border-black bg-white px-2 text-xs font-bold hover:bg-black hover:text-white">✕</button>
        )}
      </div>
      {provisional && (
        <div className="border-2 border-black bg-brutalAmber p-1.5 text-[11px] font-mono">
          Sin documento todavía: hoy lo identifica el nombre. Escribe el número cuando lo tengas.
        </div>
      )}
      <input type="text" value={f.name} onChange={campo('name')} placeholder="Nombre / Razón Social" aria-label="Nombre" className={input} />
      <div className="grid grid-cols-3 gap-1">
        <select value={f.identification_type} onChange={campo('identification_type')} aria-label="Tipo de documento" className={input}>
          {TIPOS.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <input type="text" inputMode="numeric" value={f.identification_number} onChange={campo('identification_number')}
          placeholder="Número de documento" aria-label="Número de documento" className={`${input} col-span-2`} />
      </div>
      <input type="tel" value={f.phone} onChange={campo('phone')} placeholder="Celular / teléfono de contacto" aria-label="Teléfono" className={input} />
      <input type="email" value={f.email} onChange={campo('email')} placeholder="Email" aria-label="Email" className={input} />
      <input type="text" value={f.address} onChange={campo('address')} placeholder="Dirección" aria-label="Dirección" className={input} />
      <input type="text" value={f.website} onChange={campo('website')} placeholder="Sitio web" aria-label="Sitio web" className={input} />
      {existe && (
        <div role="status" className="border-2 border-black bg-brutalAmber p-2 text-xs font-mono space-y-1">
          <div>{existe.mensaje}</div>
          {existe.tercero && onUsarExistente && (
            <button type="button" onClick={() => onUsarExistente(existe.tercero)}
              className="w-full border-2 border-black bg-white px-2 py-1 text-xs font-bold uppercase hover:bg-black hover:text-white">
              Usar esa ficha
            </button>
          )}
        </div>
      )}
      {aviso && <div role="status" className="text-xs text-green-700 font-mono">{aviso}</div>}
      {error && <div role="alert" className="text-xs text-red-600 font-mono">{error}</div>}
      <div className="flex gap-1">
        <button type="button" onClick={guardar} disabled={guardando}
          className="flex-1 border-2 border-black bg-brutalGreen px-2 py-2 text-sm font-bold uppercase hover:bg-black hover:text-white disabled:opacity-50">
          {guardando ? 'Guardando…' : '✓ Guardar ficha'}
        </button>
        <button type="button" onClick={eliminar} aria-label="Eliminar tercero"
          className="border-2 border-black bg-white px-3 py-2 text-sm font-bold hover:bg-red-600 hover:text-white">
          🗑
        </button>
      </div>
      <div className="text-[10px] font-mono text-gray-500 pt-1 border-t border-dashed border-gray-300">
        Cuentas, celulares y llaves con los que el bot reconoce a este tercero en los SMS. Se guardan al agregarlos.
      </div>
      <TerceroMediosPago terceroId={tercero.id} />
    </div>
  );
}
