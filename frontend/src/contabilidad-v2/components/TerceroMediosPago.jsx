// TerceroMediosPago.jsx — Medios de pago de un tercero (Bot IA, etapa 09.G §10)
//
// Cuentas, celulares, llaves y el nombre con que el banco llama al tercero en
// sus SMS. Es el dato estructurado con el que el bot trae el tercero YA puesto
// en el borrador de un SMS. Regla 6b: lo registra una persona — aquí, o con el
// botón 💾 del bot —; nunca se memoriza solo. Un medio pertenece a una sola
// ficha: si ya es de otro tercero, el servidor responde 409 y se ofrece
// traerlo aquí de forma explícita.
import { useEffect, useState } from 'react';
import { API } from '../../config';

const TIPOS_MEDIO = [
  { id: 'celular', label: '📱 Celular (Nequi / Daviplata)', ph: '3001234567' },
  { id: 'cuenta', label: '🏦 Cuenta bancaria', ph: 'número completo de la cuenta' },
  { id: 'llave', label: '🔑 Llave (pagos con QR)', ph: '0087671656' },
  { id: 'nombre_banco', label: '🏷 Nombre en el SMS del banco', ph: 'SANDRA JIMENEZ' },
];
const ICONO = { celular: '📱', cuenta: '🏦', llave: '🔑', nombre_banco: '🏷' };

// Lee los medios de una ficha. Nunca lanza: sin red o sin permiso → lista vacía
// (el error real aparece al intentar agregar).
async function leerMedios(base) {
  try {
    const r = await fetch(base);
    const d = r.ok ? await r.json() : [];
    return Array.isArray(d) ? d : [];
  } catch {
    return [];
  }
}

export default function TerceroMediosPago({ terceroId }) {
  // La lista se guarda junto al tercero al que pertenece: si el id cambia,
  // lo cargado deja de valer sin tener que limpiar nada a mano.
  const [carga, setCarga] = useState({ id: null, lista: null });
  const [tipo, setTipo] = useState('celular');
  const [valor, setValor] = useState('');
  const [banco, setBanco] = useState('');
  const [error, setError] = useState('');
  const [conflicto, setConflicto] = useState(null);  // {tipo, valor} que hoy está en OTRA ficha
  const [busy, setBusy] = useState(false);

  const base = `${API}/third-parties/${terceroId}/accounts`;
  const tipoActual = TIPOS_MEDIO.find(t => t.id === tipo) || TIPOS_MEDIO[0];
  const medios = carga.id === terceroId ? carga.lista : null;   // null = cargando

  useEffect(() => {
    let vivo = true;
    leerMedios(base).then(lista => { if (vivo) setCarga({ id: terceroId, lista }); });
    return () => { vivo = false; };
  }, [base, terceroId]);

  const cargar = async () => setCarga({ id: terceroId, lista: await leerMedios(base) });

  const leerError = async (r) => {
    const d = await r.json().catch(() => ({}));
    return d.detail ? String(d.detail) : `Error ${r.status}`;
  };

  const agregar = async () => {
    if (!valor.trim() || busy) return;
    setBusy(true); setError(''); setConflicto(null);
    try {
      const r = await fetch(base, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tipo, valor: valor.trim(), banco: banco.trim() || null }),
      });
      if (r.ok) {
        setValor(''); setBanco('');
        await cargar();
      } else {
        setError(await leerError(r));
        if (r.status === 409) setConflicto({ tipo, valor: valor.trim() });
      }
    } catch {
      setError('No se pudo conectar con el servidor.');
    } finally {
      setBusy(false);
    }
  };

  // Decisión explícita: el medio deja la otra ficha y pasa a esta
  const traerAqui = async () => {
    if (!conflicto || busy) return;
    setBusy(true);
    try {
      const r = await fetch(`${base}/mover`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(conflicto),
      });
      if (r.ok) {
        setError(''); setConflicto(null); setValor(''); setBanco('');
        await cargar();
      } else {
        setError(await leerError(r));
      }
    } catch {
      setError('No se pudo conectar con el servidor.');
    } finally {
      setBusy(false);
    }
  };

  const quitar = async (medio) => {
    if (busy || !confirm(`¿Quitar ${medio.descripcion} de esta ficha?`)) return;
    setBusy(true); setError('');
    try {
      const r = await fetch(`${base}/${medio.id}`, { method: 'DELETE' });
      if (!r.ok) setError(await leerError(r));
      await cargar();
    } catch {
      setError('No se pudo conectar con el servidor.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="border border-black bg-white p-1.5 space-y-1" data-testid="medios-pago">
      <div className="text-[8px] font-mono font-bold uppercase text-gray-600"
           title="El bot compara estos datos, por igualdad, con lo que trae el SMS del banco. Si coincide, el borrador llega con este tercero ya puesto.">
        🏦 Cuentas, celulares y llaves — con esto el bot reconoce a este tercero en los SMS
      </div>

      {medios === null && <div className="text-[9px] font-mono text-gray-400">Cargando…</div>}
      {medios?.length === 0 && (
        <div className="text-[9px] font-mono text-gray-400">
          Sin medios de pago. Agrégalos aquí o toca 💾 Guardar en el bot después de asignar el tercero a un borrador.
        </div>
      )}
      {medios?.map(m => (
        <div key={m.id} className="flex items-center gap-1 text-[10px] font-mono border-b border-dashed border-gray-200 py-0.5">
          <span title={m.tipo}>{ICONO[m.tipo] || '•'}</span>
          <span className="font-bold break-all">{m.valor}</span>
          {m.banco && <span className="text-gray-500">· {m.banco}</span>}
          {m.etiqueta && <span className="text-gray-500">· {m.etiqueta}</span>}
          <span className="text-[8px] text-gray-400 ml-auto"
                title={m.origen === 'bot' ? 'Guardado desde el bot de Telegram (botón 💾)' : 'Registrado en la web'}>
            {m.origen === 'bot' ? '🤖 bot' : '🖥 web'}
          </span>
          <button type="button" onClick={() => quitar(m)} disabled={busy}
                  title="Quitar de esta ficha" aria-label={`Quitar ${m.descripcion}`}
                  className="text-[9px] text-gray-300 hover:text-red-500 font-bold">🗑</button>
        </div>
      ))}

      <div className="grid grid-cols-2 gap-1 pt-0.5">
        <select value={tipo} onChange={e => { setTipo(e.target.value); setError(''); setConflicto(null); }}
                aria-label="Tipo de medio de pago"
                className="border border-black px-1 py-0.5 text-[9px] font-mono">
          {TIPOS_MEDIO.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
        </select>
        <input type="text" value={valor} onChange={e => setValor(e.target.value)}
               onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); agregar(); } }}
               placeholder={tipoActual.ph} aria-label="Valor del medio de pago"
               className="border border-black px-1 py-0.5 text-[10px] font-mono outline-none focus:border-brutalGreen" />
        <input type="text" value={banco} onChange={e => setBanco(e.target.value)}
               placeholder="Banco (opcional)" aria-label="Banco"
               className="border border-black px-1 py-0.5 text-[10px] font-mono outline-none" />
        <button type="button" onClick={agregar} disabled={busy || !valor.trim()}
                className="border border-black bg-brutalGreen px-1 py-0.5 text-[9px] font-bold uppercase hover:bg-black hover:text-white disabled:opacity-50">
          ＋ Agregar
        </button>
      </div>

      {error && (
        <div className="text-[9px] font-mono text-red-600" role="alert">
          ⚠ {error}
          {conflicto && (
            <button type="button" onClick={traerAqui} disabled={busy}
                    className="ml-1 border border-black bg-white px-1 text-[8px] font-bold uppercase text-black hover:bg-black hover:text-white">
              Traerlo a esta ficha
            </button>
          )}
        </div>
      )}
    </div>
  );
}
