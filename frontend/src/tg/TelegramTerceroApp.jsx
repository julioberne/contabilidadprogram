/* ============================================================
   TelegramTerceroApp.jsx — Mini App de Telegram (etapa 09.I, v1).

   La abre el botón «📝 Completar tercero» de un borrador del bot
   (tg.html?draft=N). Una sola pantalla: el borrador que llegó y el
   tercero: buscar y asignar uno existente, crear uno nuevo con el
   mismo formulario de la web, o abrir su ficha para completarla
   (datos, cuentas, celulares, llaves) o eliminarla.

   Sesión: la MISMA de la web (usuario y clave; useGlobalSession).
   Al asignar, el borrador se edita por el mismo endpoint de la
   bandeja web con `avisar_chat`: el bot reenvía el resumen al chat
   en su siguiente vuelta (el backend no habla con Telegram).
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { API } from '../config';
import { useGlobalSession } from '../shell/hooks/useGlobalSession.js';
import TerceroForm from '../contabilidad-v2/components/TerceroForm.jsx';
import TerceroFicha from '../contabilidad-v2/components/TerceroFicha.jsx';
import { tgClose, tgParam } from './telegram.js';

const GENERICO = '999999999';
const cop = (n) => {
  try {
    return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(Number(n) || 0);
  } catch {
    return `$${n}`;
  }
};
const norm = (s) => (s || '').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
const digitos = (s) => (s || '').toString().replace(/\D/g, '');

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

function Borrador({ draft }) {
  const p = draft.payload || {};
  const sms = p.sms || {};
  return (
    <div className="border-2 border-black p-2 bg-white font-mono text-xs space-y-0.5">
      <div className="flex justify-between">
        <span className="font-bold">Borrador #{draft.id}</span>
        <span className="text-gray-500">{p.type || ''} · {draft.status}</span>
      </div>
      <div className="text-lg font-bold">{cop(p.amount)}</div>
      <div>{p.concept || <span className="text-gray-400">sin concepto</span>}</div>
      <div className="text-gray-500">{p.transaction_date || ''} · {p.payment_method || 'cuenta sin resolver'} · {p.portfolio_name || draft.portfolio_name || ''}</div>
      {(sms.destino || sms.contraparte) && (
        <div className="text-gray-700 border-t border-dashed border-gray-300 pt-0.5">
          📲 SMS: {sms.familia ? `${sms.familia} · ` : ''}{sms.destino ? `destino ${sms.destino}` : ''}{sms.contraparte ? ` · ${sms.contraparte}` : ''}
        </div>
      )}
    </div>
  );
}

export default function TelegramTerceroApp() {
  const { user, login, logout, loading, error } = useGlobalSession();
  const draftId = tgParam('draft');
  const [draft, setDraft] = useState(null);
  const [cargaError, setCargaError] = useState('');
  const [terceros, setTerceros] = useState([]);
  const [q, setQ] = useState('');
  const [vista, setVista] = useState('inicio');   // inicio | crear | ficha
  const [fichaDe, setFichaDe] = useState(null);
  const [aviso, setAviso] = useState('');
  const [ocupado, setOcupado] = useState(false);

  const cargarTerceros = useCallback(async () => {
    const r = await fetch(`${API}/third-parties`);
    if (r.status === 401) { logout(); return; }
    if (r.ok) setTerceros(await r.json());
  }, [logout]);

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
      setDraft(await r.json());
      await cargarTerceros();
    })().catch(() => { if (vivo) setCargaError('Sin conexión con el servidor.'); });
    return () => { vivo = false; };
  }, [user, draftId, logout, cargarTerceros]);

  const actual = draft?.payload?.third_party || null;
  const tieneTercero = actual && actual.identification_number && actual.identification_number !== GENERICO;
  const terceroActual = tieneTercero
    ? (terceros.find(t => actual.id && String(t.id) === String(actual.id))
       || terceros.find(t => t.identification_number === actual.identification_number)
       || actual)
    : null;

  const asignar = async (t) => {
    if (!draft) return;
    setOcupado(true); setAviso('');
    try {
      const r = await fetch(`${API}/bot/drafts/${draft.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          third_party: { id: t.id, identification_type: t.identification_type || 'CC',
                         identification_number: t.identification_number, name: t.name },
          avisar_chat: true,
        }),
      });
      const cuerpo = await r.json().catch(() => ({}));
      if (!r.ok) { setAviso(`No se pudo asignar: ${cuerpo.detail || r.status}`); return; }
      setDraft({ ...draft, ...cuerpo, status: cuerpo.status || draft.status });
      setAviso(`Asignado: ${t.name}. El bot te manda el resumen actualizado al chat en su siguiente vuelta (menos de un minuto).`);
      setFichaDe(t); setVista('ficha'); setQ('');
    } catch {
      setAviso('Sin conexión con el servidor.');
    } finally {
      setOcupado(false);
    }
  };

  const abrirFicha = (t) => { setFichaDe(t); setVista('ficha'); };

  const candidatos = q.trim().length >= 2
    ? terceros.filter(t => norm(t.name).includes(norm(q)) || (digitos(q) && (digitos(t.identification_number).includes(digitos(q)) || digitos(t.phone).includes(digitos(q))))).slice(0, 8)
    : [];

  if (!user) {
    return <div className="p-3 max-w-md mx-auto"><Login login={login} loading={loading} error={error} /></div>;
  }

  const btn = 'border-2 border-black px-2 py-2 text-sm font-bold uppercase hover:bg-black hover:text-white';

  return (
    <div className="p-2 max-w-md mx-auto space-y-2 font-mono">
      <div className="flex items-center justify-between">
        <div className="text-xs font-bold uppercase">FIN-SYS · Tercero del borrador</div>
        <div className="flex gap-1">
          <button type="button" onClick={logout} className="text-[10px] underline text-gray-500">salir</button>
          <button type="button" onClick={tgClose} className={`${btn} bg-white text-xs py-1`} aria-label="Cerrar">Cerrar</button>
        </div>
      </div>

      {cargaError && <div role="alert" className="border-2 border-black bg-brutalAmber p-2 text-xs">{cargaError}</div>}
      {draft && <Borrador draft={draft} />}
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
                {terceroActual.id && <button type="button" onClick={() => abrirFicha(terceroActual)} className={`${btn} bg-white text-xs py-1`}>Ficha</button>}
              </div>
            ) : (
              <div className="text-sm text-gray-500">Sin tercero. Búscalo abajo o créalo.</div>
            )}
          </div>

          <div className="border-2 border-black p-2 bg-brutalBg space-y-1">
            <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="🔍 Buscar por nombre, documento o celular"
              aria-label="Buscar tercero" className="w-full border-2 border-black px-2 py-2 text-sm outline-none focus:border-brutalGreen bg-white" />
            {q.trim().length >= 2 && candidatos.length === 0 && <div className="text-xs text-gray-500">Nadie coincide con «{q}».</div>}
            {candidatos.map(t => (
              <div key={t.id} className="flex items-center justify-between gap-1 border-b border-gray-200 py-1">
                <div className="text-xs truncate"><span className="font-bold">{t.name}</span><span className="text-gray-500"> · {t.identification_type} {t.identification_number}</span></div>
                <div className="flex gap-1 shrink-0">
                  <button type="button" onClick={() => abrirFicha(t)} className={`${btn} bg-white text-[10px] py-1 px-1.5`}>Ficha</button>
                  {draft.editable && <button type="button" onClick={() => asignar(t)} disabled={ocupado} className={`${btn} bg-brutalGreen text-[10px] py-1 px-1.5 disabled:opacity-50`}>Asignar</button>}
                </div>
              </div>
            ))}
            <button type="button" onClick={() => setVista('crear')} className={`${btn} w-full bg-white`}>➕ Crear tercero nuevo</button>
          </div>
        </>
      )}

      {vista === 'crear' && (
        <TerceroForm
          inicial={{ name: q, phone: digitos(draft?.payload?.sms?.destino).length === 10 ? digitos(draft.payload.sms.destino) : '' }}
          onCancelar={() => setVista('inicio')}
          onCreado={async (t) => { await cargarTerceros().catch(() => {}); if (draft?.editable) await asignar(t); else abrirFicha(t); }}
          onUsarExistente={async (t) => { if (draft?.editable) await asignar(t); else abrirFicha(t); }}
        />
      )}

      {vista === 'ficha' && fichaDe && (
        <TerceroFicha
          tercero={fichaDe}
          onCerrar={() => setVista('inicio')}
          onGuardado={async (t) => { setFichaDe(t); await cargarTerceros().catch(() => {}); }}
          onEliminado={async () => { setFichaDe(null); setVista('inicio'); setAviso('Tercero eliminado. Si el borrador lo tenía asignado, asigna otro.'); await cargarTerceros().catch(() => {}); }}
        />
      )}

      {vista === 'ficha' && fichaDe && draft?.editable && !(terceroActual && String(terceroActual.id) === String(fichaDe.id)) && (
        <button type="button" onClick={() => asignar(fichaDe)} disabled={ocupado} className={`${btn} w-full bg-brutalGreen disabled:opacity-50`}>
          Asignar «{fichaDe.name}» a este borrador
        </button>
      )}
    </div>
  );
}
