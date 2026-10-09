/* ============================================================
   BorradorEditable.jsx — Mini App de Telegram (9-oct-2026).

   · BorradorEditable: el borrador con su MENSAJE ORIGINAL (el SMS
     completo, o lo que se escribió/dictó) y los campos que Andrés
     completa desde el chat: concepto y monto. Se guarda por el mismo
     endpoint de la bandeja web con `avisar_chat`: el bot reenvía el
     resumen y, al confirmar, el borrador llega así al libro diario.
   · RecordarMedio: el dato con que el banco nombra a la contraparte
     (cuenta, celular, llave o el nombre tal como lo escribe, p. ej.
     «PARKING INTERNATIONA») queda en la ficha del tercero, y los
     próximos SMS con ese dato llegan con el tercero ya puesto.
     Siempre un acto explícito (Regla 6b): botón o casilla visible.
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { API } from '../config';

const cop = (n) => {
  try {
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(n) || 0);
  } catch {
    return `$${n}`;
  }
};

/** «50000» · «$50.000» · «50.000,00» · «12,100.00» → número; otra cosa → null.
    Mismo criterio que el bot: con dos separadores, el último es el decimal;
    con uno solo, es de miles si se repite o deja 3 dígitos al final. */
export function parseMonto(texto) {
  const s = String(texto ?? '').replace(/[$\s]/g, '').replace(/cop$/i, '');
  if (!/^\d[\d.,]*$/.test(s)) return null;
  let limpio = s;
  const coma = s.includes(','), punto = s.includes('.');
  if (coma && punto) {
    const decimal = s.lastIndexOf(',') > s.lastIndexOf('.') ? ',' : '.';
    const miles = decimal === ',' ? '.' : ',';
    limpio = s.split(miles).join('').replace(decimal, '.');
  } else if (coma || punto) {
    const sep = coma ? ',' : '.';
    const partes = s.split(sep);
    limpio = partes.length > 2 || partes[partes.length - 1].length === 3 ? partes.join('') : partes.join('.');
  }
  const n = Number(limpio);
  return Number.isFinite(n) && n > 0 ? n : null;
}

/** Texto corto del medio de pago del SMS (igual que terceros_cuentas.describir). */
export function describirMedio(medio) {
  if (!medio) return '';
  if (medio.tipo === 'celular') return `cel ${medio.valor}`;
  if (medio.tipo === 'cuenta') return `cuenta *${medio.valor}`;
  if (medio.tipo === 'llave') return `llave ${medio.valor}`;
  return `«${medio.valor}»`;
}

const CELULAR = /^3\d{9}$/;
const TIPOS_DE_UN_CELULAR = ['celular', 'llave', 'cuenta'];
/** ¿La ficha ya tiene ese medio? Un celular es uno solo aunque se haya guardado como llave o cuenta. */
function tieneMedio(medios, medio) {
  return (medios || []).some(m => (m.tipo === medio.tipo && m.valor === medio.valor)
    || (CELULAR.test(medio.valor) && m.valor === medio.valor
        && TIPOS_DE_UN_CELULAR.includes(m.tipo) && TIPOS_DE_UN_CELULAR.includes(medio.tipo)));
}

/** POST del medio a la ficha. → {ok, status, detail} (409 = ya es de otra ficha). */
export async function guardarMedio(terceroId, medio, mover = false) {
  const url = `${API}/third-parties/${terceroId}/accounts${mover ? '/mover' : ''}`;
  const r = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tipo: medio.tipo, valor: medio.valor }),
  });
  const cuerpo = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, detail: cuerpo.detail || '' };
}

export default function BorradorEditable({ draft, onGuardado, logout }) {
  const p = draft.payload || {};
  const sms = p.sms || {};
  const [concepto, setConcepto] = useState(p.concept || '');
  const [monto, setMonto] = useState(p.amount ? String(p.amount) : '');
  const [estado, setEstado] = useState('');
  const [ocupado, setOcupado] = useState(false);

  // Lo que manda es el borrador más reciente (p. ej. tras asignar un tercero)
  useEffect(() => {
    setConcepto(p.concept || '');
    setMonto(p.amount ? String(p.amount) : '');
  }, [draft.id, p.concept, p.amount]);

  const montoNum = parseMonto(monto);
  const montoInvalido = monto.trim() !== '' && montoNum === null;
  const cambios = {};
  if (concepto.trim() && concepto.trim() !== (p.concept || '').trim()) cambios.concept = concepto.trim().slice(0, 255);
  if (montoNum !== null && montoNum !== Number(p.amount)) cambios.amount = montoNum;
  const hayCambios = Object.keys(cambios).length > 0;
  const faltan = p.missing_fields || [];

  const guardar = async () => {
    setOcupado(true); setEstado('');
    try {
      const r = await fetch(`${API}/bot/drafts/${draft.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...cambios, avisar_chat: true }),
      });
      const cuerpo = await r.json().catch(() => ({}));
      if (r.status === 401) { logout(); return; }
      if (!r.ok) { setEstado(`No se pudo guardar: ${cuerpo.detail || r.status}`); return; }
      onGuardado(cuerpo);
      setEstado('Guardado. El bot te manda el resumen actualizado al chat en su siguiente vuelta.');
    } catch {
      setEstado('Sin conexión con el servidor.');
    } finally {
      setOcupado(false);
    }
  };

  const input = 'w-full border-2 border-black px-2 py-1.5 text-sm outline-none focus:border-brutalGreen bg-white disabled:bg-gray-100';
  return (
    <div className="border-2 border-black p-2 bg-white font-mono text-xs space-y-1.5">
      <div className="flex justify-between">
        <span className="font-bold">Borrador #{draft.id}</span>
        <span className="text-gray-500">{p.type || ''} · {draft.status}</span>
      </div>
      <div className="text-gray-500">{p.transaction_date || ''} · {p.payment_method || 'cuenta sin resolver'} · {p.portfolio_name || draft.portfolio_name || ''}</div>
      {(sms.destino || sms.contraparte) && (
        <div className="text-gray-700">
          📲 SMS: {sms.familia ? `${sms.familia} · ` : ''}{sms.destino ? `destino ${sms.destino}` : ''}{sms.contraparte ? ` · ${sms.contraparte}` : ''}
        </div>
      )}

      <label className="block">
        <span className="text-[10px] uppercase text-gray-500">Monto</span>
        <input value={monto} onChange={(e) => setMonto(e.target.value)} disabled={!draft.editable}
          inputMode="decimal" placeholder="50000" aria-label="Monto" className={`${input} text-lg font-bold`} />
        {montoInvalido
          ? <span role="alert" className="text-red-700">Escribe solo el valor, ej. 50000 o 50.000</span>
          : montoNum !== null && <span className="text-gray-500">{cop(montoNum)}</span>}
      </label>
      <label className="block">
        <span className="text-[10px] uppercase text-gray-500">Concepto</span>
        <textarea value={concepto} onChange={(e) => setConcepto(e.target.value)} disabled={!draft.editable}
          rows={2} maxLength={255} aria-label="Concepto" placeholder="¿De qué fue este movimiento?" className={input} />
      </label>
      {draft.editable && (
        <button type="button" onClick={guardar} disabled={!hayCambios || montoInvalido || ocupado}
          className="w-full border-2 border-black bg-brutalGreen px-2 py-1.5 text-xs font-bold uppercase hover:bg-black hover:text-white disabled:opacity-40">
          {ocupado ? 'Guardando…' : 'Guardar concepto y monto'}
        </button>
      )}
      {estado && <div role="status" className="text-[11px]">{estado}</div>}
      {faltan.length > 0 && (
        <div className="text-[11px] text-amber-800">⚠ Falta: {faltan.join(', ')}. Puedes completarlo aquí o respondiendo al mensaje del bot.</div>
      )}

      {draft.raw_text && (
        <details open className="border-t border-dashed border-gray-300 pt-1">
          <summary className="cursor-pointer text-[10px] uppercase text-gray-500">
            📩 Mensaje original{draft.channel === 'sms' ? ' (SMS del banco)' : ''}
          </summary>
          <pre className="whitespace-pre-wrap break-words text-[11px] text-gray-800 mt-1 font-mono">{draft.raw_text}</pre>
        </details>
      )}
    </div>
  );
}

/** Bloque «📲 Dato del SMS» para el tercero asignado: ¿ya está en su ficha?
    Si no, 💾 recordarlo; si es de otra ficha, 🔁 moverlo (decisión explícita). */
export function RecordarMedio({ medio, tercero, refrescar = 0, logout }) {
  const [estado, setEstado] = useState('cargando');   // cargando | ya | falta | de_otro | error
  const [detalle, setDetalle] = useState('');
  const [ocupado, setOcupado] = useState(false);

  const revisar = useCallback(async () => {
    try {
      const r = await fetch(`${API}/third-parties/${tercero.id}/accounts`);
      if (r.status === 401) { logout(); return; }
      const medios = r.ok ? await r.json() : [];
      setEstado(tieneMedio(medios, medio) ? 'ya' : 'falta');
    } catch {
      setEstado('falta');
    }
  }, [tercero.id, medio, logout]);

  useEffect(() => { revisar(); }, [revisar, refrescar]);

  const accion = async (mover) => {
    setOcupado(true); setDetalle('');
    try {
      const r = await guardarMedio(tercero.id, medio, mover);
      if (r.status === 401) { logout(); return; }
      if (r.ok) { setEstado('ya'); return; }
      if (r.status === 409) { setEstado('de_otro'); setDetalle(r.detail); return; }
      setEstado('error'); setDetalle(r.detail || `Error ${r.status}`);
    } catch {
      setEstado('error'); setDetalle('Sin conexión con el servidor.');
    } finally {
      setOcupado(false);
    }
  };

  const desc = describirMedio(medio);
  const btn = 'border-2 border-black px-2 py-1 text-[11px] font-bold uppercase hover:bg-black hover:text-white disabled:opacity-50';
  return (
    <div className="border-2 border-black p-2 bg-brutalBg font-mono text-xs space-y-1" aria-label="Dato del SMS">
      <div className="text-[10px] uppercase text-gray-500">📲 Dato del SMS</div>
      {estado === 'ya' && (
        <div>✓ {desc} ya está en la ficha de <b>{tercero.name}</b>: los próximos SMS con ese dato llegan con este tercero.</div>
      )}
      {estado === 'falta' && (
        <>
          <div>El banco lo identifica como {desc}. Guárdalo en la ficha y los próximos SMS llegan con <b>{tercero.name}</b>.</div>
          <button type="button" onClick={() => accion(false)} disabled={ocupado} className={`${btn} bg-brutalGreen`}>
            💾 Recordar en la ficha de {tercero.name}
          </button>
        </>
      )}
      {estado === 'de_otro' && (
        <>
          <div className="text-amber-800">{detalle}</div>
          <button type="button" onClick={() => accion(true)} disabled={ocupado} className={`${btn} bg-white`}>
            🔁 Moverlo a {tercero.name}
          </button>
        </>
      )}
      {estado === 'error' && <div role="alert" className="text-red-700">{detalle}</div>}
    </div>
  );
}
