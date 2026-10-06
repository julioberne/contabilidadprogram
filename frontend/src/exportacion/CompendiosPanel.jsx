/* ============================================================
   CompendiosPanel.jsx — 🔗 Compendios para clientes (spec 13.6):
   los links creados, con su estado, vencimiento y visitas; copiar,
   abrir, ⏳ ampliar o ⛔ revocar. Vive en la franja de ⇩
   Exportación (no en el organizador: un compendio no es un
   archivo, es un link).
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { api } from './api.js';
import { AvisoError, DialogoConfirmar, DialogoElegir, btnBlanco, btnPeligro } from './Dialogos.jsx';
import { ESTADOS, VIGENCIAS, fechaCorta, haceCuanto, linkCompleto } from './compendios.js';

export default function CompendiosPanel() {
  const [lista, setLista] = useState(null);          // null = cargando
  const [error, setError] = useState('');
  const [dialogo, setDialogo] = useState(null);
  const [copiado, setCopiado] = useState(null);

  const cargar = useCallback(() => api.get('/compendios')
    .then((d) => { setLista(Array.isArray(d) ? d : []); setError(''); })
    .catch((e) => { setLista([]); setError(e.message); }), []);
  useEffect(() => { cargar(); }, [cargar]);

  const reemplazar = (c) => setLista((xs) => xs.map((x) => (x.id === c.id ? c : x)));
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
        <button type="button" className={`${btnBlanco} ml-auto`} onClick={cargar}>↻</button>
      </div>
      <AvisoError texto={error} />
      {lista === null && <div className="text-[10px]">cargando…</div>}
      {lista?.length === 0 && !error && <div className="text-[10px] text-gray-600">Aún no hay compendios.</div>}
      <ul className="divide-y divide-black/20">
        {(lista || []).map((c) => {
          const e = ESTADOS[c.estado] || ESTADOS.vencido;
          const ultima = haceCuanto(c.ultima_visita);
          return (
            <li key={c.id} className="py-1 flex flex-wrap items-center gap-1 text-[10px]">
              <span className={`border border-black px-1 font-bold ${e.clase}`}>{e.texto}</span>
              <b>{c.folio}</b>
              <span className="truncate max-w-[260px]" title={c.nombre}>{c.nombre}</span>
              <span className="text-gray-700">· {c.n} TX · {c.estado === 'revocado' ? `revocado ${fechaCorta(c.revocado_en)}` : `vence ${fechaCorta(c.expira_en)}`}
                {' '}· 👁 {c.visitas}{ultima ? ` (última ${ultima})` : ''}</span>
              <span className="ml-auto flex flex-wrap gap-1">
                {c.ruta && <>
                  <button type="button" className={btnBlanco} onClick={() => copiar(c)}>{copiado === c.id ? '✔ COPIADO' : '📋 LINK'}</button>
                  <a className={btnBlanco} href={c.ruta} target="_blank" rel="noopener noreferrer">↗ ABRIR</a>
                </>}
                {c.estado !== 'revocado' && <button type="button" className={btnBlanco} onClick={() => ampliar(c)}>⏳ AMPLIAR</button>}
                {c.estado === 'vigente' && <button type="button" className={btnPeligro} onClick={() => revocar(c)}>⛔ REVOCAR</button>}
              </span>
            </li>
          );
        })}
      </ul>
      {dialogo}
    </section>
  );
}
