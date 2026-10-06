/* ============================================================
   CompendiosPanel.jsx — 🔗 Compendios para clientes (spec 13.6):
   los links creados, con su estado, vencimiento y visitas; copiar,
   abrir, ⏳ ampliar o ⛔ revocar. Vive en la franja de ⇩
   Exportación (no en el organizador: un compendio no es un
   archivo, es un link).
   13.6-c 📈: arriba, la actividad reciente de los clientes; en cada
   fila ● EN VIVO y "revisó X de N"; 📈 abre el seguimiento. Se
   refresca solo cada 30 s mientras la pestaña está visible.
   ============================================================ */
import { useCallback, useState } from 'react';
import { api } from './api.js';
import { AvisoError, DialogoConfirmar, DialogoElegir, btnBlanco, btnPeligro } from './Dialogos.jsx';
import { ESTADOS, VIGENCIAS, fechaCorta, haceCuanto, linkCompleto } from './compendios.js';
import { REFRESCO_PANEL_MS, horaCorta, textoEvento, useRefresco } from './seguimiento.js';
import SeguimientoCompendio from './SeguimientoCompendio.jsx';

export default function CompendiosPanel({ admin = false }) {
  const [lista, setLista] = useState(null);          // null = cargando
  const [actividad, setActividad] = useState([]);
  const [error, setError] = useState('');
  const [dialogo, setDialogo] = useState(null);
  const [copiado, setCopiado] = useState(null);
  const [siguiendo, setSiguiendo] = useState(null);

  const cargar = useCallback(() => Promise.all([
    api.get('/compendios')
      .then((d) => { setLista(Array.isArray(d) ? d : []); setError(''); })
      .catch((e) => { setLista((x) => x || []); setError(e.message); }),
    api.get('/compendios/actividad?limite=10')
      .then((d) => setActividad(Array.isArray(d) ? d : []))
      .catch(() => {}),
  ]), []);
  useRefresco(cargar, REFRESCO_PANEL_MS);

  const [bajando, setBajando] = useState(null);
  const bajar = async (c, formato) => {           // ⬇ PDF (13.6-d) · 💾 HTML offline (13.6-e)
    setBajando(`${c.id}-${formato}`);
    try { await api.descargarRuta(`/compendios/${c.id}/${formato}`, `${c.folio}.${formato}`); }
    catch (e) { setError(`El ${formato.toUpperCase()} falló: ${e.message}`); }
    finally { setBajando(null); }
  };
  // 🗑 Borrar (06-oct, solo admin): un compendio revocado o vencido, o todos los inactivos de una vez.
  const borrar = (c) => setDialogo(
    <DialogoConfirmar titulo={`🗑 Borrar ${c.folio}`} peligro textoOk="BORRAR"
      texto={`Se borra para siempre: el compendio, su foto y toda su actividad (visitas y qué revisó).\nEl folio ${c.folio} queda como hueco en la secuencia.`}
      onCerrar={() => setDialogo(null)}
      onOk={async () => { await api.del(`/compendios/${c.id}`); setLista((xs) => xs.filter((x) => x.id !== c.id)); setDialogo(null); }} />,
  );
  const inactivos = (lista || []).filter((c) => c.estado !== 'vigente').length;
  const borrarInactivos = () => setDialogo(
    <DialogoConfirmar titulo={`🗑 Borrar ${inactivos} compendio(s) inactivo(s)`} peligro textoOk="BORRAR TODOS"
      texto={'Se borran para siempre todos los compendios REVOCADOS o VENCIDOS, con su foto y su actividad.\nLos vigentes no se tocan.'}
      onCerrar={() => setDialogo(null)}
      onOk={async () => { await api.del('/compendios/inactivos'); setDialogo(null); cargar(); }} />,
  );
  const reemplazar = (c) => setLista((xs) => xs.map((x) => (x.id === c.id ? { ...x, ...c } : x)));
  const copiar = async (c) => {
    try { await navigator.clipboard.writeText(linkCompleto(c.ruta, window.location.origin)); setCopiado(c.id); }
    catch (e) { setError(`No pude copiar: ${e.message}`); }
  };
  const ampliar = (c) => setDialogo(
    <DialogoElegir titulo={`⏳ Ampliar ${c.folio}`} ayuda={`Vence el ${fechaCorta(c.expira_en)}. Se suma desde esa fecha.`}
      opciones={VIGENCIAS.map((d) => ({ valor: d, etiqueta: `+ ${d} días` }))} actual={null}
      onCerrar={() => setDialogo(null)}
      onOk={async (dias) => { reemplazar(await api.patch(`/compendios/${c.id}`, { ampliar_dias: dias })); setDialogo(null); }} />,
  );
  const revocar = (c) => setDialogo(
    <DialogoConfirmar titulo={`⛔ Revocar ${c.folio}`} peligro textoOk="REVOCAR"
      texto={`El link deja de funcionar YA para quien lo tenga.\nNo se puede deshacer: para volver a compartir, crea otro compendio.`}
      onCerrar={() => setDialogo(null)}
      onOk={async () => { reemplazar(await api.patch(`/compendios/${c.id}`, { revocar: true })); setDialogo(null); }} />,
  );

  return (
    <section aria-label="Compendios para clientes" className="bg-white border-2 border-black shadow-brutal p-2 space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-bold text-[12px]">🔗 COMPENDIOS PARA CLIENTES</span>
        <span className="text-[10px] text-gray-600">links temporales sin login · se crean desde 📥 → 🧾 Transacciones → 🤝 Cliente</span>
        {admin && inactivos > 0 && (
          <button type="button" className={`${btnPeligro} ml-auto`} onClick={borrarInactivos}
            title="Libera espacio: borra los revocados y vencidos con su actividad">🗑 BORRAR INACTIVOS ({inactivos})</button>
        )}
        <button type="button" className={`${btnBlanco} ${admin && inactivos > 0 ? '' : 'ml-auto'}`} onClick={cargar}
          title="Se actualiza solo cada 30 s">↻</button>
      </div>
      <AvisoError texto={error} />

      {actividad.length > 0 && (
        <div aria-label="Actividad reciente de clientes" className="border-2 border-black bg-brutalBg p-1">
          <div className="text-[10px] font-bold mb-0.5">📈 ACTIVIDAD RECIENTE DE CLIENTES</div>
          <ol className="text-[10px] space-y-0.5 max-h-28 overflow-auto">
            {actividad.map((e, k) => (
              <li key={`${e.en}-${k}`} className="flex flex-wrap gap-1">
                <b className="w-20 shrink-0">{horaCorta(e.en)}</b>
                <span>{e.folio} · {e.dispositivo || 'visitante'} — {textoEvento(e)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {lista === null && <div className="text-[10px]">cargando…</div>}
      {lista?.length === 0 && !error && <div className="text-[10px] text-gray-600">Aún no hay compendios.</div>}
      <ul className="divide-y divide-black/20">
        {(lista || []).map((c) => {
          const e = ESTADOS[c.estado] || ESTADOS.vencido;
          const ultima = haceCuanto(c.ultima_visita);
          return (
            <li key={c.id} className="py-1 flex flex-wrap items-center gap-1 text-[10px]">
              <span className={`border border-black px-1 font-bold ${e.clase}`}>{e.texto}</span>
              {c.en_vivo && <span className="border border-black px-1 font-bold bg-brutalGreen animate-pulse">● EN VIVO</span>}
              <b>{c.folio}</b>
              <span className="truncate max-w-[260px]" title={c.nombre}>{c.nombre}</span>
              <span className="text-gray-700">· {c.n} TX · {c.estado === 'revocado' ? `revocado ${fechaCorta(c.revocado_en)}` : `vence ${fechaCorta(c.expira_en)}`}
                {' '}· 👁 {c.visitas}{ultima ? ` (última ${ultima})` : ''}
                {c.visitas > 0 ? ` · ✔ revisó ${c.revisadas} de ${c.n}` : ' · aún sin abrir'}</span>
              <span className="ml-auto flex flex-wrap gap-1">
                <button type="button" className={btnBlanco} onClick={() => setSiguiendo(c)}>📈 SEGUIMIENTO</button>
                <button type="button" className={btnBlanco} disabled={!!bajando} onClick={() => bajar(c, 'pdf')}
                  title="Portada, índice y una página por transacción con sus comprobantes">
                  {bajando === `${c.id}-pdf` ? '⏳ PDF…' : '⬇ PDF'}</button>
                <button type="button" className={btnBlanco} disabled={!!bajando} onClick={() => bajar(c, 'html')}
                  title="Un solo archivo con todo adentro: se manda por WhatsApp o correo y abre sin internet">
                  {bajando === `${c.id}-html` ? '⏳ HTML…' : '💾 HTML'}</button>
                {c.ruta && <>
                  <button type="button" className={btnBlanco} onClick={() => copiar(c)}>{copiado === c.id ? '✔ COPIADO' : '📋 LINK'}</button>
                  <a className={btnBlanco} href={`${c.ruta}?previa=1`} target="_blank" rel="noopener noreferrer"
                    title="Vista previa interna: no cuenta como visita del cliente">↗ ABRIR</a>
                </>}
                {c.estado !== 'revocado' && <button type="button" className={btnBlanco} onClick={() => ampliar(c)}>⏳ AMPLIAR</button>}
                {c.estado === 'vigente' && <button type="button" className={btnPeligro} onClick={() => revocar(c)}>⛔ REVOCAR</button>}
                {admin && c.estado !== 'vigente' && (
                  <button type="button" className={btnPeligro} onClick={() => borrar(c)}
                    title="Borra el compendio y su actividad para liberar espacio">🗑 BORRAR</button>
                )}
              </span>
            </li>
          );
        })}
      </ul>
      {dialogo}
      {siguiendo && <SeguimientoCompendio compendio={siguiendo} admin={admin} onCerrar={() => setSiguiendo(null)} />}
    </section>
  );
}
