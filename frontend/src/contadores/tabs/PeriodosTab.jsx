/* ============================================================
   PeriodosTab.jsx — Cierre de periodos: grilla año × 12 meses por
   portafolio con estado y conteo de asientos. Cerrar (contador) /
   Reabrir (solo admin).
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { api } from '../useContadoresApi.js';
import MotivoModal from '../components/MotivoModal.jsx';

const MESES = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'];

export default function PeriodosTab({ portfolioId, portfolios, esAdmin, onCambio }) {
  const [anio, setAnio] = useState(new Date().getFullYear());
  const [meses, setMeses] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(null);
  const [reabrir, setReabrir] = useState(null);
  const pid = portfolioId ?? (portfolios?.[0]?.id ?? null);
  const nombre = (portfolios || []).find((p) => p.id === pid)?.name || '';

  const cargar = useCallback(async () => {
    if (pid == null) return;
    setError('');
    try { setMeses(await api.get(`/contadores/periodos?portfolio_id=${pid}&anio=${anio}`)); }
    catch (e) { setError(e.message); }
  }, [pid, anio]);
  useEffect(() => { cargar(); }, [cargar]);

  const cerrar = async (mes) => {
    if (!window.confirm(`¿Cerrar ${MESES[mes - 1]} ${anio} de ${nombre}? No se podrán registrar ni editar transacciones ni asientos de ese mes.`)) return;
    setBusy(mes); setError('');
    try { await api.post('/contadores/periodos/cerrar', { portfolio_id: pid, anio, mes }); await cargar(); onCambio?.(); }
    catch (e) { setError(e.message); }
    finally { setBusy(null); }
  };
  const hacerReabrir = async (motivo) => {
    setBusy(reabrir); setError('');
    try { await api.post('/contadores/periodos/reabrir', { portfolio_id: pid, anio, mes: reabrir, motivo }); setReabrir(null); await cargar(); onCambio?.(); }
    catch (e) { setError(e.message); }
    finally { setBusy(null); }
  };

  const btn = 'border border-black px-1.5 py-0.5 text-[10px] font-bold hover:bg-black hover:text-white disabled:opacity-40';
  if (pid == null) return <div className="text-[10px]">Elige un portafolio.</div>;

  return (
    <div className="space-y-2">
      <div className="bg-white border-2 border-black p-2 shadow-brutal flex items-center gap-2 text-[10px]">
        <b>{nombre}</b>
        <button className={btn} onClick={() => setAnio(anio - 1)}>◀</button>
        <span className="font-bold text-[12px]">{anio}</span>
        <button className={btn} onClick={() => setAnio(anio + 1)}>▶</button>
        <span className="text-gray-600">Cerrar bloquea registrar/editar/borrar en ese mes. Un asiento contabilizado de un mes cerrado solo se anula con espejo en el mes actual.</span>
      </div>
      {error && <div className="bg-brutalCrimson text-white border-2 border-black p-1 text-[10px]">{error}</div>}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {meses.map((m) => {
          const cerrado = m.estado === 'CERRADO';
          const a = m.asientos || {};
          return (
            <div key={m.mes} className={`border-2 border-black p-2 shadow-brutal font-mono ${cerrado ? 'bg-brutalNeutral' : 'bg-white'}`}>
              <div className="flex items-center justify-between">
                <b className="text-[12px]">{MESES[m.mes - 1]}</b>
                <span className={`text-[9px] border border-black px-1 font-bold ${cerrado ? 'bg-black text-white' : 'bg-brutalGreen'}`}>{m.estado}</span>
              </div>
              <div className="text-[9px] mt-1">
                borrador {a.BORRADOR || 0} · contab. {a.CONTABILIZADO || 0} · anul. {a.ANULADO || 0} · rech. {a.RECHAZADO || 0}
              </div>
              {cerrado && <div className="text-[9px] text-gray-600">por {m.cerrado_por} · {m.cerrado_en?.slice(0, 10)}{m.nota ? ` · ${m.nota}` : ''}</div>}
              <div className="mt-1 flex gap-1">
                {!cerrado && <button className={btn} disabled={busy === m.mes} onClick={() => cerrar(m.mes)}>CERRAR</button>}
                {cerrado && esAdmin && <button className={btn} disabled={busy === m.mes} onClick={() => setReabrir(m.mes)}>REABRIR</button>}
              </div>
            </div>
          );
        })}
      </div>
      {reabrir && (
        <MotivoModal titulo={`Reabrir ${MESES[reabrir - 1]} ${anio}`} confirmar="REABRIR" busy={busy === reabrir}
                     descripcion="Solo administradores. Queda registrado quién y por qué."
                     onConfirm={hacerReabrir} onClose={() => setReabrir(null)} />
      )}
    </div>
  );
}
