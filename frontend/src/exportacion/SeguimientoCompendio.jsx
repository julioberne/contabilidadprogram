/* ============================================================
   SeguimientoCompendio.jsx — 📈 Seguimiento de un compendio
   (spec 13.6 §11): KPIs, qué revisó el cliente por transacción
   (las nunca abiertas resaltadas) y la línea de tiempo. Se
   refresca sola cada 15 s mientras la pestaña está visible.
   ============================================================ */
import { useCallback, useState } from 'react';
import { api } from './api.js';
import { Modal, AvisoError, DialogoConfirmar, btnPeligro } from './Dialogos.jsx';
import { fechaCorta } from './compendios.js';
import { REFRESCO_SEGUIMIENTO_MS, horaCorta, tardanza, textoEvento, useRefresco } from './seguimiento.js';

const plata = (v, m) => `${m === 'COP' || !m ? '$' : `${m} `}${Number(v || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 })}`;
const chip = 'border-2 border-black px-2 py-0.5 text-[10px] font-bold bg-white';

export default function SeguimientoCompendio({ compendio, onCerrar, admin = false }) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  const [hora, setHora] = useState(null);
  const [dialogo, setDialogo] = useState(null);
  const cargar = useCallback(() => api.get(`/compendios/${compendio.id}/seguimiento`)
    .then((d) => { setDatos(d); setError(''); setHora(new Date()); })
    .catch((e) => setError(e.message)), [compendio.id]);
  useRefresco(cargar, REFRESCO_SEGUIMIENTO_MS);

  const r = datos?.resumen;
  // 🧹 (06-oct, solo admin): borra el detalle de actividad; quedan los totales (visitas, descargas).
  const borrarActividad = () => setDialogo(
    <DialogoConfirmar titulo="🧹 Borrar la actividad" peligro textoOk="BORRAR ACTIVIDAD"
      texto={`Se borra el detalle de ${compendio.folio}: quién abrió qué y cuándo.\nEl compendio y su link no cambian; quedan los totales de visitas y descargas.`}
      onCerrar={() => setDialogo(null)}
      onOk={async () => { await api.del(`/compendios/${compendio.id}/actividad`); setDialogo(null); cargar(); }} />,
  );
  return (
    <Modal titulo={`📈 SEGUIMIENTO — ${compendio.folio} · ${compendio.nombre}`} onCerrar={onCerrar} ancho="max-w-4xl">
      <AvisoError texto={error} />
      {!datos && !error && <div className="p-3 text-center font-bold">⏳ Cargando…</div>}
      {datos && (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-1">
            {r.en_vivo && <span className={`${chip} bg-brutalGreen animate-pulse`}>● EN VIVO</span>}
            <span className={chip}>👁 {r.aperturas} apertura{r.aperturas === 1 ? '' : 's'}</span>
            <span className={chip}>👤 {r.visitantes} visitante{r.visitantes === 1 ? '' : 's'}</span>
            <span className={`${chip} ${r.revisadas < r.total ? 'bg-brutalAmber' : 'bg-brutalGreen'}`}>
              ✔ revisó {r.revisadas} de {r.total}</span>
            <span className="text-[10px]">
              {r.primera ? <>1.ª apertura <b>{fechaCorta(r.primera)} {horaCorta(r.primera)}</b>
                {tardanza(r.horas_hasta_primera) ? ` (${tardanza(r.horas_hasta_primera)})` : ''}</> : 'Aún no lo ha abierto.'}
              {r.ultima && <> · última actividad {horaCorta(r.ultima)}</>}
            </span>
          </div>

          <section aria-label="Qué revisó" className="border-2 border-black bg-white">
            <div className="px-2 py-1 border-b-2 border-black bg-brutalBg font-bold text-[11px]">QUÉ REVISÓ</div>
            <div className="max-h-[32vh] overflow-auto">
              <table className="w-full text-[10px]">
                <thead className="sticky top-0 bg-brutalNeutral text-left">
                  <tr><th className="p-1 w-5"></th><th className="p-1">Fecha</th><th className="p-1">Concepto</th>
                    <th className="p-1 text-right">Valor</th><th className="p-1">👁</th><th className="p-1">📎 vistos</th><th className="p-1">Última vez</th></tr>
                </thead>
                <tbody>
                  {datos.por_tx.map((t) => (
                    <tr key={t.i} className={`border-t border-black/20 ${t.revisada ? '' : 'bg-brutalAmber/30'}`}>
                      <td className="p-1 font-bold">{t.revisada ? '✔' : '✘'}</td>
                      <td className="p-1 whitespace-nowrap">{t.fecha}</td>
                      <td className="p-1 truncate max-w-[260px]" title={t.concepto}>{t.concepto}</td>
                      <td className="p-1 text-right whitespace-nowrap">{plata(t.neto, t.moneda)}</td>
                      <td className="p-1">{t.revisada ? t.aperturas : '—'}</td>
                      <td className="p-1">{t.comprobantes_total ? `${t.comprobantes_vistos}/${t.comprobantes_total}` : 'sin comprobante'}</td>
                      <td className="p-1 whitespace-nowrap">{t.revisada ? horaCorta(t.ultima) : 'sin abrir'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section aria-label="Actividad" className="border-2 border-black bg-white">
            <div className="px-2 py-1 border-b-2 border-black bg-brutalBg flex flex-wrap gap-2 items-baseline">
              <span className="font-bold text-[11px]">ACTIVIDAD</span>
              <span className="text-[10px] text-gray-600">se actualiza sola cada 15 s{hora ? ` · ${hora.toLocaleTimeString('es-CO', { hour12: false })}` : ''}</span>
              {admin && datos.eventos.length > 0 && (
                <button type="button" className={`${btnPeligro} ml-auto`} onClick={borrarActividad}
                  title="Libera espacio: borra el detalle de actividad de este compendio">🧹 BORRAR ACTIVIDAD</button>
              )}
            </div>
            <ol className="max-h-[28vh] overflow-auto text-[10px] divide-y divide-black/10">
              {datos.eventos.map((e, k) => (
                <li key={`${e.en}-${k}`} className="px-2 py-0.5 flex flex-wrap gap-1">
                  <span className="font-bold w-20 shrink-0">{horaCorta(e.en)}</span>
                  <span>{e.visitante}{e.dispositivo ? ` · ${e.dispositivo}` : ''} — {textoEvento(e)}</span>
                </li>
              ))}
              {!datos.eventos.length && <li className="px-2 py-2 text-gray-600">Sin actividad todavía. Cuando el cliente abra el link aparecerá aquí.</li>}
            </ol>
          </section>
        </div>
      )}
      {dialogo}
    </Modal>
  );
}
