/* ============================================================
   TelegramTerceroApp.jsx — Mini App de Telegram (etapa 09.I).

   La abre el botón «📝 Completar» de un borrador del bot
   (tg.html?draft=N). Una sola pantalla: el borrador que llegó, con
   su mensaje original, concepto y monto editables (9-oct-2026), y el
   tercero: buscar y asignar uno existente, crear uno nuevo con el
   mismo formulario de la web, o abrir su ficha para completarla
   (datos, cuentas, celulares, llaves) o eliminarla. Si el borrador
   viene de un SMS, el dato con que el banco nombra a la contraparte
   se puede recordar en la ficha (casilla al asignar o 💾).

   Sesión: la MISMA de la web (usuario y clave; useGlobalSession).
   Al asignar, el borrador se edita por el mismo endpoint de la
   bandeja web con `avisar_chat`: el bot reenvía el resumen al chat
   en su siguiente vuelta (el backend no habla con Telegram). Si se
   guarda la ficha del tercero ya asignado, el borrador se vuelve a
   sincronizar (el documento o el nombre pudieron cambiar).
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { API } from '../config';
import { useGlobalSession } from '../shell/hooks/useGlobalSession.js';
import TerceroForm from '../contabilidad-v2/components/TerceroForm.jsx';
import TerceroFicha from '../contabilidad-v2/components/TerceroFicha.jsx';
import { tgClose, tgParam } from './telegram.js';
import BorradorEditable, { RecordarMedio, guardarMedio, describirMedio } from './BorradorEditable.jsx';
import EtiquetasBorrador from './EtiquetasBorrador.jsx';
import { useBusqueda, buscarUna } from '../shared/busqueda/useBusqueda.js';

const GENERICO = '999999999';
const digitos = (s) => (s || '').toString().replace(/\D/g, '');
const esNumerico = (s) => s.trim() !== '' && /^[\d\s.\-+()]+$/.test(s.trim());

function Login({ login, loading, error }) {
  const [email, setEmail] = useState('');
  const [clave, setClave] = useState('');
  const input = 'w-full border-2 border-black px-2 py-2 text-sm font-mono outline-none focus:border-brutalGreen bg-white';
  return (
    <form className="border-2 border-black p-3 bg-brutalBg space-y-2" onSubmit={(e) => { e.preventDefault(); login(email, clave); }}>
      <div className="text-xs font-mono font-bold uppercase">Entrar a FIN-SYS</div>
      <div className="text-[11px] font-mono text-gray-500">Mismo usuario y clave de la web. Solo la primera vez.</div>
      <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" aria-label="Email" autoComplete="username" className={input} />
      <input type="password" value={clave} onChange={(e) => setClave(e.target.value)} placeholder="Clave" aria-label="Clave" autoComplete="current-password" className={input} />
      {error && <div role="alert" className="text-xs text-red-600 font-mono">{error}</div>}
      <button type="submit" disabled={loading}
        className="w-full border-2 border-black bg-brutalGreen px-2 py-2 text-sm font-bold uppercase hover:bg-black hover:text-white disabled:opacity-50">
        {loading ? 'Entrando…' : 'Entrar'}
      </button>
    </form>
  );
}

export default function TelegramTerceroApp() {
  const { user, login, logout, loading, error } = useGlobalSession();
  const draftId = tgParam('draft');
  const [draft, setDraft] = useState(null);
  const [cargaError, setCargaError] = useState('');
  // H3 (estándar de consultas): nada de catálogo completo en el celular. La
  // búsqueda va al servidor (top-8) y el tercero asignado se resuelve solo.
  const [resuelto, setResuelto] = useState(undefined); // undefined = resolviendo · null = no existe
  const [conocidos, setConocidos] = useState({});      // id → ficha completa ya vista
  const [version, setVersion] = useState(0);           // repetir la búsqueda tras crear/editar
  const [q, setQ] = useState('');
  const [vista, setVista] = useState('inicio');   // inicio | crear | ficha
  const [fichaDe, setFichaDe] = useState(null);
  const [aviso, setAviso] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const [eliminadoId, setEliminadoId] = useState(null);
  const [recordar, setRecordar] = useState(true);        // casilla «recordar el dato del SMS»
  const [refrescarMedio, setRefrescarMedio] = useState(0);

  const recordarFichas = useCallback((lista) => {
    if (!lista?.length) return;
    setConocidos((c) => { const n = { ...c }; lista.forEach((t) => { n[t.id] = { ...n[t.id], ...t }; }); return n; });
  }, []);

  // Resuelve el tercero del borrador por id (o documento) con UNA consulta de una fila.
  const resolverAsignado = useCallback(async (borrador) => {
    const tp = borrador?.payload?.third_party;
    if (!tp || !tp.identification_number || tp.identification_number === GENERICO) { setResuelto(null); return; }
    try {
      const d = await buscarUna('terceros', tp.id ? { ids: [tp.id] } : { ident: tp.identification_number });
      const f = (d.items || [])[0] || null;
      if (f) recordarFichas([f]);
      setResuelto(f);
    } catch (e) {
      if (e.status === 401) logout();
      else setResuelto(undefined);   // sin conexión: se muestra lo que dice el borrador
    }
  }, [logout, recordarFichas]);

  const refrescar = useCallback(async (borrador) => {
    setVersion((v) => v + 1);
    await resolverAsignado(borrador);
  }, [resolverAsignado]);

  useEffect(() => {
    if (!user) return;
    let vivo = true;
    (async () => {
      if (!draftId) { setCargaError('Falta el borrador: abre esta pantalla desde el botón del bot.'); return; }
      const r = await fetch(`${API}/bot/drafts/${draftId}`);
      if (!vivo) return;
      if (r.status === 401) { logout(); return; }
      if (!r.ok) {
        const c = await r.json().catch(() => ({}));
        setCargaError(c.detail || `No se pudo cargar el borrador #${draftId}.`);
        return;
      }
      const b = await r.json();
      setDraft(b);
      await resolverAsignado(b);
    })().catch(() => { if (vivo) setCargaError('Sin conexión con el servidor.'); });
    return () => { vivo = false; };
  }, [user, draftId, logout, resolverAsignado]);

  const { items: candidatos, cargando: buscando } = useBusqueda('terceros', q, {
    minimo: 2, limite: 8, version, onNoAutorizado: logout,
  });

  // Siempre la ficha COMPLETA: lo ya visto aporta los campos que falten (el 409
  // y el payload traen objetos parciales) y lo recibido manda (es lo más
  // reciente, p. ej. lo que se acaba de guardar en la ficha).
  const completo = (t) => {
    if (!t || !t.id) return t;
    const base = { ...candidatos.find((x) => String(x.id) === String(t.id)), ...conocidos[t.id] };
    return { ...base, ...t };
  };

  const actual = draft?.payload?.third_party || null;
  const medio = draft?.payload?.sms?.medio || null;      // {tipo, valor} del SMS (09.G §10)
  const tieneTercero = !!(actual && actual.identification_number && actual.identification_number !== GENERICO);
  const asignadoEliminado = tieneTercero && actual.id && eliminadoId && String(eliminadoId) === String(actual.id);
  const enLista = tieneTercero && resuelto ? resuelto : null;
  // Mientras se resuelve se muestra lo que dice el borrador; resuelto y sin ficha, ya no existe
  const terceroActual = tieneTercero && !asignadoEliminado ? (enLista || (resuelto === undefined ? actual : null)) : null;
  const asignadoFaltante = tieneTercero && !asignadoEliminado && resuelto === null;

  const asignar = async (t) => {
    if (!draft) return;
    const ficha = completo(t);
    setOcupado(true); setAviso('');
    try {
      const r = await fetch(`${API}/bot/drafts/${draft.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          third_party: { id: ficha.id, identification_type: ficha.identification_type || 'CC',
                         identification_number: ficha.identification_number, name: ficha.name },
          avisar_chat: true,
        }),
      });
      const cuerpo = await r.json().catch(() => ({}));
      if (r.status === 401) { logout(); return; }
      if (!r.ok) { setAviso(`No se pudo asignar: ${cuerpo.detail || r.status}`); return; }
      const nuevo = { ...draft, ...cuerpo, status: cuerpo.status || draft.status };
      setDraft(nuevo);
      setResuelto(ficha);
      recordarFichas([ficha]);
      setEliminadoId(null);
      let extra = '';
      if (recordar && medio) {
        // Casilla visible y marcada a la vista del humano: acto explícito (Regla 6b)
        const m = await guardarMedio(ficha.id, medio).catch(() => ({ ok: false, detail: 'sin conexión' }));
        extra = m.ok ? ` ${describirMedio(medio)} quedó en su ficha: los próximos SMS llegan con este tercero.`
          : ` No se guardó ${describirMedio(medio)} en la ficha: ${m.detail || m.status}.`;
        setRefrescarMedio(n => n + 1);
      }
      setAviso(`Asignado: ${ficha.name}. El bot te manda el resumen actualizado al chat en su siguiente vuelta (menos de un minuto).${extra}`);
      setFichaDe(ficha); setVista('ficha'); setQ('');
    } catch {
      setAviso('Sin conexión con el servidor.');
    } finally {
      setOcupado(false);
    }
  };

  const abrirFicha = (t) => { setFichaDe(completo(t)); setVista('ficha'); };


  // Prellenado de «Crear»: lo buscado va al nombre solo si es texto; si son
  // dígitos, al celular (10 dígitos) o al documento. El celular del SMS manda.
  const celSms = digitos(draft?.payload?.sms?.destino).length === 10 ? digitos(draft.payload.sms.destino) : '';
  const qDig = digitos(q);
  // Sin búsqueda, el nombre arranca con lo que dice el SMS (literal, editable):
  // el comercio/remitente o «Cel 319…» para asociar el número y poner el nombre después.
  const ETIQUETA_MEDIO = { celular: 'Cel', cuenta: 'Cuenta', llave: 'Llave' };
  const nombreDelSms = draft?.payload?.sms?.contraparte
    || (medio ? (ETIQUETA_MEDIO[medio.tipo] ? `${ETIQUETA_MEDIO[medio.tipo]} ${medio.valor}` : medio.valor) : '');
  const inicialCrear = esNumerico(q)
    ? { name: '', phone: celSms || (qDig.length === 10 ? qDig : ''), idNumber: qDig.length === 10 && !celSms ? '' : (qDig.length === 10 ? '' : qDig) }
    : { name: q.trim() || nombreDelSms, phone: celSms };

  if (!user) {
    return <div className="p-3 max-w-md mx-auto"><Login login={login} loading={loading} error={error} /></div>;
  }

  const btn = 'border-2 border-black px-2 py-2 text-sm font-bold uppercase hover:bg-black hover:text-white';
  const fichaEsLaAsignada = fichaDe && tieneTercero && actual.id && String(actual.id) === String(fichaDe.id);

  return (
    <div className="p-2 max-w-md mx-auto space-y-2 font-mono">
      <div className="flex items-center justify-between">
        <div className="text-xs font-bold uppercase">FIN-SYS · Completar borrador</div>
        <div className="flex gap-1">
          <button type="button" onClick={logout} className="text-[10px] underline text-gray-500">salir</button>
          <button type="button" onClick={tgClose} className={`${btn} bg-white text-xs py-1`} aria-label="Cerrar">Cerrar</button>
        </div>
      </div>

      {cargaError && <div role="alert" className="border-2 border-black bg-brutalAmber p-2 text-xs">{cargaError}</div>}
      {draft && (
        <BorradorEditable draft={draft} logout={logout}
          onGuardado={(c) => setDraft({ ...draft, ...c, status: c.status || draft.status })} />
      )}
      {draft && (
        <EtiquetasBorrador draft={draft} logout={logout}
          onGuardado={(c) => setDraft({ ...draft, ...c, status: c.status || draft.status })} />
      )}
      {draft && medio && enLista && !asignadoEliminado && (
        <RecordarMedio key={enLista.id} medio={medio} tercero={enLista} refrescar={refrescarMedio} logout={logout} />
      )}
      {draft && !draft.editable && (
        <div role="status" className="border-2 border-black bg-brutalAmber p-2 text-xs">
          Este borrador ya está en estado {draft.status}: se puede ver, pero no cambiar.
        </div>
      )}
      {aviso && <div role="status" className="border-2 border-black bg-white p-2 text-xs">{aviso}</div>}

      {vista === 'inicio' && draft && (
        <>
          <div className="border-2 border-black p-2 bg-brutalBg space-y-1">
            <div className="text-[10px] uppercase text-gray-500">Tercero actual</div>
            {terceroActual ? (
              <div className="flex items-center justify-between gap-1">
                <div className="text-sm font-bold truncate">{terceroActual.name}
                  <span className="font-normal text-gray-500 text-xs"> · {terceroActual.identification_type} {terceroActual.identification_number}</span>
                </div>
                {enLista && <button type="button" onClick={() => abrirFicha(enLista)} aria-label={`Ficha de ${terceroActual.name}`} className={`${btn} bg-white text-xs py-1`}>Ficha</button>}
              </div>
            ) : (asignadoEliminado || asignadoFaltante) ? (
              <div className="text-sm text-red-700">El tercero asignado ya no existe. Asigna otro.</div>
            ) : (
              <div className="text-sm text-gray-500">Sin tercero. Búscalo abajo o créalo.</div>
            )}
          </div>

          <div className="border-2 border-black p-2 bg-brutalBg space-y-1">
            <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="🔍 Buscar por nombre, documento o celular"
              aria-label="Buscar tercero" className="w-full border-2 border-black px-2 py-2 text-sm outline-none focus:border-brutalGreen bg-white" />
            {q.trim().length >= 2 && buscando && candidatos.length === 0 && <div className="text-xs text-gray-500">Buscando…</div>}
            {q.trim().length >= 2 && !buscando && candidatos.length === 0 && <div className="text-xs text-gray-500">Nadie coincide con «{q}».</div>}
            {candidatos.map(t => (
              <div key={t.id} className="flex items-center justify-between gap-1 border-b border-gray-200 py-1">
                <div className="text-xs truncate"><span className="font-bold">{t.name}</span><span className="text-gray-500"> · {t.identification_type} {t.identification_number}</span></div>
                <div className="flex gap-1 shrink-0">
                  <button type="button" onClick={() => abrirFicha(t)} aria-label={`Ficha de ${t.name}`} className={`${btn} bg-white text-[10px] py-1 px-1.5`}>Ficha</button>
                  {draft.editable && <button type="button" onClick={() => asignar(t)} disabled={ocupado} aria-label={`Asignar ${t.name}`} className={`${btn} bg-brutalGreen text-[10px] py-1 px-1.5 disabled:opacity-50`}>Asignar</button>}
                </div>
              </div>
            ))}
            <button type="button" onClick={() => setVista('crear')} className={`${btn} w-full bg-white`}>➕ Crear tercero nuevo</button>
            {medio && draft.editable && (
              <label className="flex items-start gap-1.5 text-[11px] pt-1">
                <input type="checkbox" checked={recordar} onChange={(e) => setRecordar(e.target.checked)}
                  aria-label="Recordar el dato del SMS al asignar" className="mt-0.5" />
                <span>Al asignar, recordar {describirMedio(medio)} en esa ficha (así los próximos SMS llegan con el tercero).</span>
              </label>
            )}
          </div>
        </>
      )}

      {vista === 'crear' && (
        <TerceroForm
          inicial={inicialCrear}
          onCancelar={() => setVista('inicio')}
          onCreado={async (t) => { recordarFichas([t]); setVersion((v) => v + 1); if (draft?.editable) await asignar(t); else abrirFicha(t); }}
          onUsarExistente={async (t) => { if (draft?.editable) await asignar(t); else abrirFicha(t); }}
        />
      )}

      {vista === 'ficha' && fichaDe && (
        <TerceroFicha
          key={fichaDe.id}
          tercero={fichaDe}
          onCerrar={() => setVista('inicio')}
          onUsarExistente={async (t) => { if (draft?.editable) await asignar(t); else abrirFicha(t); }}
          onGuardado={async (t) => {
            setFichaDe(t);
            recordarFichas([t]);
            await refrescar(draft).catch(() => {});
            // La ficha asignada cambió (documento formalizado, nombre corregido):
            // el borrador debe llevar los datos vigentes para que al confirmar
            // no nazca otra ficha ni se pise un nombre.
            if (draft?.editable && fichaEsLaAsignada) await asignar(t);
          }}
          onEliminado={async (t) => {
            setFichaDe(null); setVista('inicio');
            if (tieneTercero && actual.id && String(actual.id) === String(t.id)) setEliminadoId(t.id);
            setAviso(`Tercero «${t.name}» eliminado.${fichaEsLaAsignada ? ' El borrador lo tenía asignado: asigna otro.' : ''}`);
            await refrescar(draft).catch(() => {});
          }}
        />
      )}

      {vista === 'ficha' && fichaDe && draft?.editable && !fichaEsLaAsignada && (
        <button type="button" onClick={() => asignar(fichaDe)} disabled={ocupado} className={`${btn} w-full bg-brutalGreen disabled:opacity-50`}>
          Asignar «{fichaDe.name}» a este borrador
        </button>
      )}
    </div>
  );
}
