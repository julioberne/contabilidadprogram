/* ============================================================
   BotBitacoraPanel.jsx — 📓 Bitácora de anomalías del Bot IA.
   Pedido de Andrés (9-oct-2026): ver en una tabla, tal cual quedó
   registrado y sin inferencias, lo que el bot no pudo resolver
   (SMS sin plantilla, cuentas sin registrar, respuestas sin
   borrador, descartes, correcciones…) para ir mejorando el sistema.
   Informativa: marcar «revisada» no cambia nada contable.
   Datos: GET/PUT /api/bot/anomalias (routers/bot_anomalias.py).
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { API } from '../config';
import { authHeaders } from '../shell/authHeaders';

const hdrs = () => ({ 'Content-Type': 'application/json', ...authHeaders() });

// Nombre corto para la tabla; el texto largo (del backend) va en el título.
const CORTO = {
  sms_plantilla_nueva: 'SMS sin plantilla',
  sms_cuenta_no_registrada: 'Cuenta no registrada',
  sms_contraparte_sin_ficha: 'Contraparte sin ficha',
  sms_traslado_sin_destino: 'Traslado sin destino',
  sms_error: 'Error con un SMS',
  reply_sin_borrador: 'Respuesta sin borrador',
  reply_borrador_cerrado: 'Respuesta a cerrado',
  borrador_descartado: 'Borrador descartado',
  correccion_sms: 'Corrección a un SMS',
  confirmacion_fallida: 'Confirmación fallida',
  error_bot: 'Error del bot',
};
const DIAS = [7, 30, 90, 180];

const fecha = (s) => {
  try {
    return new Date(s).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return s;
  }
};

function Fila({ a, tipos, onMarcar, ocupado }) {
  const [abierta, setAbierta] = useState(false);
  const texto = a.texto || '';
  return (
    <>
      <tr className={`border-b border-gray-200 align-top ${a.revisada ? 'text-gray-400' : ''}`}>
        <td className="px-1 py-1 whitespace-nowrap">{fecha(a.created_at)}</td>
        <td className="px-1 py-1" title={tipos[a.tipo] || a.tipo}>{CORTO[a.tipo] || a.tipo}</td>
        <td className="px-1 py-1">{a.detalle || '—'}</td>
        <td className="px-1 py-1 whitespace-nowrap">{a.draft_id ? `#${a.draft_id}` : '—'}</td>
        <td className="px-1 py-1">{a.canal || '—'}</td>
        <td className="px-1 py-1 max-w-[16rem]">
          {texto || a.datos ? (
            <button type="button" onClick={() => setAbierta(v => !v)} className="text-left underline decoration-dotted"
              aria-expanded={abierta} aria-label={`Ver registro ${a.id}`}>
              {texto ? (texto.length > 60 ? `${texto.slice(0, 60)}…` : texto) : 'ver datos'}
            </button>
          ) : '—'}
        </td>
        <td className="px-1 py-1 whitespace-nowrap">
          <button type="button" disabled={ocupado} onClick={() => onMarcar(a, !a.revisada)}
            className={`border-2 border-black px-1.5 py-0.5 text-[10px] font-bold uppercase disabled:opacity-50 ${a.revisada ? 'bg-brutalGreen text-black' : 'bg-white hover:bg-black hover:text-white'}`}>
            {a.revisada ? '✓ Revisada' : 'Marcar revisada'}
          </button>
        </td>
      </tr>
      {abierta && (
        <tr className="border-b border-gray-200 bg-brutalBg">
          <td colSpan={7} className="px-2 py-1.5 space-y-1">
            {texto && <pre className="whitespace-pre-wrap break-words text-[11px] font-mono">{texto}</pre>}
            {a.datos && (
              <pre className="whitespace-pre-wrap break-words text-[10px] font-mono text-gray-600">
                {JSON.stringify(a.datos, null, 1)}
              </pre>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export default function BotBitacoraPanel() {
  const [dias, setDias] = useState(30);
  const [estado, setEstado] = useState('abiertas');
  const [tipo, setTipo] = useState('');
  const [datos, setDatos] = useState(null);       // null = cargando
  const [error, setError] = useState('');
  const [ocupado, setOcupado] = useState(null);

  const cargar = useCallback(async () => {
    setError('');
    try {
      const qs = new URLSearchParams({ dias: String(dias), estado, tipo });
      const r = await fetch(`${API}/bot/anomalias?${qs}`, { headers: hdrs() });
      const cuerpo = await r.json().catch(() => ({}));
      if (!r.ok) { setError(cuerpo.detail || `Error ${r.status}`); setDatos({ items: [], resumen: {}, tipos: {} }); return; }
      setDatos(cuerpo);
    } catch {
      setError('Sin conexión con el servidor.');
      setDatos({ items: [], resumen: {}, tipos: {} });
    }
  }, [dias, estado, tipo]);

  useEffect(() => { cargar(); }, [cargar]);

  const marcar = async (a, revisada) => {
    setOcupado(a.id);
    try {
      const r = await fetch(`${API}/bot/anomalias/${a.id}`, {
        method: 'PUT', headers: hdrs(), body: JSON.stringify({ revisada }),
      });
      if (!r.ok) {
        const c = await r.json().catch(() => ({}));
        setError(c.detail || `No se pudo marcar (${r.status})`);
      }
    } catch {
      setError('Sin conexión con el servidor.');
    }
    setOcupado(null);
    await cargar();
  };

  const tipos = datos?.tipos || {};
  const resumen = datos?.resumen || {};
  const items = datos?.items || [];
  const sel = 'border-2 border-black bg-white px-1 py-0.5 text-xs font-mono';

  return (
    <div className="border-2 border-black bg-white p-2 space-y-2 font-mono text-xs">
      <div>
        <div className="text-sm font-bold uppercase">📓 Bitácora del bot</div>
        <div className="text-[11px] text-gray-600">
          Registro tal cual de lo que el bot no pudo resolver. Es informativa: no frena nada; sirve para saber
          qué plantillas, cuentas o anclas de terceros faltan. Se guarda 180 días.
        </div>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <label>Días{' '}
          <select value={dias} onChange={(e) => setDias(Number(e.target.value))} aria-label="Días" className={sel}>
            {DIAS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        <label>Mostrar{' '}
          <select value={estado} onChange={(e) => setEstado(e.target.value)} aria-label="Estado" className={sel}>
            <option value="abiertas">Pendientes</option>
            <option value="todas">Todas</option>
          </select>
        </label>
        <label>Tipo{' '}
          <select value={tipo} onChange={(e) => setTipo(e.target.value)} aria-label="Tipo" className={sel}>
            <option value="">Todos</option>
            {Object.keys(tipos).map(t => <option key={t} value={t}>{CORTO[t] || t}</option>)}
          </select>
        </label>
        <button type="button" onClick={cargar} className="border-2 border-black px-2 py-0.5 font-bold uppercase hover:bg-black hover:text-white">
          ↻ Actualizar
        </button>
      </div>

      {Object.keys(resumen).length > 0 && (
        <div className="flex flex-wrap gap-1" aria-label="Resumen por tipo">
          {Object.entries(resumen).map(([t, n]) => (
            <button key={t} type="button" onClick={() => setTipo(tipo === t ? '' : t)} title={tipos[t] || t}
              className={`border-2 border-black px-1.5 py-0.5 text-[11px] ${tipo === t ? 'bg-black text-white' : 'bg-brutalBg'}`}>
              {CORTO[t] || t}: <b>{n.abiertas}</b> / {n.total}
            </button>
          ))}
        </div>
      )}

      {error && <div role="alert" className="border-2 border-black bg-brutalAmber p-1.5">{error}</div>}
      {datos && datos.disponible === false && (
        <div role="status" className="border-2 border-black bg-brutalAmber p-1.5">
          La bitácora se activa con el próximo despliegue (la tabla se crea al arrancar el servidor).
        </div>
      )}

      {datos === null ? (
        <div className="text-gray-500">Cargando…</div>
      ) : items.length === 0 ? (
        <div className="text-gray-500">Nada {estado === 'abiertas' ? 'pendiente' : 'registrado'} en los últimos {dias} días.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] border-collapse">
            <thead>
              <tr className="border-b-2 border-black text-left uppercase text-[10px]">
                <th className="px-1 py-1">Fecha</th><th className="px-1 py-1">Tipo</th><th className="px-1 py-1">Detalle</th>
                <th className="px-1 py-1">Borrador</th><th className="px-1 py-1">Canal</th><th className="px-1 py-1">Texto original</th>
                <th className="px-1 py-1">Estado</th>
              </tr>
            </thead>
            <tbody>
              {items.map(a => <Fila key={a.id} a={a} tipos={tipos} onMarcar={marcar} ocupado={ocupado === a.id} />)}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
