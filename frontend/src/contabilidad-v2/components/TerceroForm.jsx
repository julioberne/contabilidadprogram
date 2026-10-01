/* ============================================================
   TerceroForm.jsx — Alta de tercero (etapa 09.I).
   Los MISMOS campos del panel Terceros de la web (nombre, tipo y
   número de documento, email, teléfono, dirección), reutilizables
   fuera del ContextPanel: hoy los usa la Mini App de Telegram.

   Regla D-09I-08: si el documento ya es de otra ficha, el servidor
   responde 409 con esa ficha y aquí se ofrece «Usar esa ficha»;
   nunca se crea un duplicado ni se pisa un nombre. Sin documento el
   tercero nace provisional (SN-…) y se completa después.
   ============================================================ */
import { useState } from 'react';
import { API } from '../../config';

const TIPOS = [['NIT', 'NIT'], ['CC', 'CC'], ['CE', 'CE'], ['PP', 'Pasaporte']];

export default function TerceroForm({ inicial = {}, onCreado, onUsarExistente, onCancelar }) {
  const [f, setF] = useState({
    name: inicial.name || '', idType: inicial.idType || 'CC', idNumber: inicial.idNumber || '',
    email: inicial.email || '', phone: inicial.phone || '', address: inicial.address || '',
  });
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');
  const [existe, setExiste] = useState(null);   // {mensaje, tercero} tras un 409

  const campo = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const crear = async () => {
    if (!f.name.trim()) { setError('El nombre es obligatorio.'); return; }
    setEnviando(true); setError(''); setExiste(null);
    try {
      const r = await fetch(`${API}/third-parties`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: f.name.trim(), identification_type: f.idType,
          identification_number: f.idNumber.trim(), email: f.email.trim(),
          phone: f.phone.trim(), address: f.address.trim(),
        }),
      });
      const cuerpo = await r.json().catch(() => ({}));
      if (r.status === 409 && cuerpo.codigo === 'existe') {
        setExiste({ mensaje: cuerpo.detail, tercero: cuerpo.tercero });
        return;
      }
      if (!r.ok) { setError(cuerpo.detail || 'No se pudo crear el tercero.'); return; }
      onCreado?.({ ...cuerpo, name: f.name.trim(), email: f.email.trim(), phone: f.phone.trim(),
                   address: f.address.trim() });
    } catch {
      setError('Sin conexión con el servidor.');
    } finally {
      setEnviando(false);
    }
  };

  const input = 'w-full border-2 border-black px-2 py-2 text-sm font-mono outline-none focus:border-brutalGreen bg-white';

  return (
    <div className="border-2 border-black p-2 bg-brutalBg space-y-2">
      <div className="text-[10px] font-mono text-gray-500 uppercase border-b border-dashed border-gray-300 pb-1">
        Crear tercero
      </div>
      <input type="text" value={f.name} onChange={campo('name')} placeholder="Nombre / Razón Social" aria-label="Nombre" className={input} />
      <div className="grid grid-cols-3 gap-1">
        <select value={f.idType} onChange={campo('idType')} aria-label="Tipo de documento" className={input}>
          {TIPOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <input type="text" inputMode="numeric" value={f.idNumber} onChange={campo('idNumber')} placeholder="Número (opcional)" aria-label="Número de documento" className={`${input} col-span-2`} />
      </div>
      <input type="tel" value={f.phone} onChange={campo('phone')} placeholder="Celular / teléfono" aria-label="Teléfono" className={input} />
      <input type="email" value={f.email} onChange={campo('email')} placeholder="Email" aria-label="Email" className={input} />
      <input type="text" value={f.address} onChange={campo('address')} placeholder="Dirección" aria-label="Dirección" className={input} />
      <div className="text-[10px] font-mono text-gray-500">
        Nada es obligatorio salvo el nombre: sin documento queda como provisional y lo completas cuando lo tengas.
      </div>
      {existe && (
        <div role="status" className="border-2 border-black bg-brutalAmber p-2 text-xs font-mono space-y-1">
          <div>{existe.mensaje}</div>
          {existe.tercero && (
            <button type="button" onClick={() => onUsarExistente?.(existe.tercero)}
              className="w-full border-2 border-black bg-white px-2 py-1 text-xs font-bold uppercase hover:bg-black hover:text-white">
              Usar esa ficha
            </button>
          )}
        </div>
      )}
      {error && <div role="alert" className="text-xs text-red-600 font-mono">{error}</div>}
      <div className="flex gap-1">
        <button type="button" onClick={crear} disabled={enviando}
          className="flex-1 border-2 border-black bg-brutalGreen px-2 py-2 text-sm font-bold uppercase hover:bg-black hover:text-white disabled:opacity-50">
          {enviando ? 'Creando…' : '✓ Crear tercero'}
        </button>
        {onCancelar && (
          <button type="button" onClick={onCancelar}
            className="border-2 border-black bg-white px-3 py-2 text-sm font-bold uppercase hover:bg-black hover:text-white">
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
