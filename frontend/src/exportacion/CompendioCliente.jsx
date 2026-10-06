/* ============================================================
   CompendioCliente.jsx — Piezas del 🤝 Compendio para el cliente
   dentro de Nueva exportación (spec 13.6): ¿para quién?, opciones
   (nota, vigencia, NIT, ubicaciones), revisión previa y pantalla
   de éxito con el link (copiar, abrir, WhatsApp).
   ============================================================ */
import { useState } from 'react';
import { btnBlanco, btnNegro } from './Dialogos.jsx';
import { VIGENCIAS, MAX_NOTA, fechaCorta, linkCompleto, textoWhatsApp, urlWhatsApp } from './compendios.js';

const chip = (activo) => `border-2 border-black px-2 py-0.5 text-[10px] font-bold ${activo ? 'bg-black text-white' : 'bg-white hover:bg-brutalNeutral'}`;
const plata = (v, m) => `${m === 'COP' ? '$' : `${m} `}${Number(v || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 })}`;

export function ParaQuien({ destino, onDestino }) {
  return (
    <div className="flex flex-wrap items-center gap-1 border-2 border-black bg-brutalBg p-1" role="radiogroup" aria-label="¿Para quién?">
      <span className="text-[10px] font-bold mr-1">¿PARA QUIÉN?</span>
      <button type="button" role="radio" aria-checked={destino === 'contador'} className={chip(destino === 'contador')}
        onClick={() => onDestino('contador')} title="Relación .xlsx con folio: relación, asientos, resumen y soportes">
        📊 Contador (Relación .xlsx con asientos)</button>
      <button type="button" role="radio" aria-checked={destino === 'cliente'} className={chip(destino === 'cliente')}
        onClick={() => onDestino('cliente')} title="Link temporal para el cliente final: lista, comprobantes y ubicaciones">
        🤝 Cliente (compendio con comprobantes)</button>
    </div>
  );
}

export function OpcionesCompendio({ valor, onCambio }) {
  const set = (k, v) => onCambio({ ...valor, [k]: v });
  return (
    <section className="border-2 border-black bg-white p-2 space-y-2 text-[10px]" aria-label="Opciones del compendio">
      <div className="font-bold text-[11px]">🤝 COMPENDIO PARA EL CLIENTE</div>
      <p className="text-gray-700">El cliente abre un link sin login: totales, la lista que puede buscar y, en cada transacción,
        sus comprobantes y 📍 la ubicación. Sin asientos contables.</p>
      <div className="flex flex-wrap items-center gap-1">
        <b className="mr-1">El link dura</b>
        {VIGENCIAS.map((d) => (
          <button key={d} type="button" aria-pressed={valor.vigencia === d} className={chip(valor.vigencia === d)}
            onClick={() => set('vigencia', d)}>{d} días</button>
        ))}
      </div>
      <label className="flex flex-col gap-0.5"><b>Nota para el cliente (opcional)</b>
        <textarea value={valor.nota} maxLength={MAX_NOTA} rows={2} onChange={(e) => set('nota', e.target.value)}
          placeholder="Ej.: Adjunto los soportes de los gastos del viaje a Medellín."
          className="border-2 border-black px-1 py-0.5 bg-white resize-y" /></label>
      <div className="flex flex-wrap gap-3">
        <label className="flex items-center gap-1"><input type="checkbox" checked={valor.identificacion}
          onChange={(e) => set('identificacion', e.target.checked)} /> Mostrar NIT/CC de los terceros</label>
        <label className="flex items-center gap-1"><input type="checkbox" checked={valor.ubicaciones}
          onChange={(e) => set('ubicaciones', e.target.checked)} /> Mostrar ubicaciones (📍 Google Maps)</label>
      </div>
    </section>
  );
}

export function RevisionCompendio({ data }) {
  if (!data) return null;
  const rango = data.rango?.desde ? `${data.rango.desde} – ${data.rango.hasta}` : '—';
  return (
    <section aria-label="Revisión previa" className="border-2 border-black p-2 text-[10px] space-y-1 bg-white">
      <div className="font-bold text-[11px]">🔍 REVISIÓN PREVIA — lo que verá el cliente</div>
      <div className="grid sm:grid-cols-2 gap-x-4 gap-y-0.5">
        <div><b>Transacciones:</b> {data.n} · fechas: {rango}</div>
        <div><b>Empresas:</b> {(data.empresas || []).map((e) => e.nombre).join(', ') || '—'}</div>
        <div><b>Comprobantes:</b> {data.comprobantes}{data.sin_comprobante?.length ? ` · ${data.sin_comprobante.length} TX sin comprobante` : ''}</div>
        <div className="flex flex-wrap gap-1">
          {Object.entries(data.totales || {}).map(([m, t]) => (
            <span key={m} className="border border-black px-1">{m}: ▲ {plata(t.ingresos, m)} · ▼ {plata(t.gastos, m)} · ∑ {plata(t.neto, m)}</span>
          ))}
        </div>
      </div>
      {data.advertencias?.length > 0 && (
        <ul className="list-disc pl-4 space-y-0.5">{data.advertencias.map((a, i) => <li key={i}>⚠ {a}</li>)}</ul>
      )}
    </section>
  );
}

export function ExitoCompendio({ res }) {
  const [copiado, setCopiado] = useState(false);
  const link = linkCompleto(res.ruta, window.location.origin);
  const copiar = async () => {
    try { await navigator.clipboard.writeText(link); setCopiado(true); }
    catch { document.getElementById('link-compendio')?.select(); }
  };
  return (
    <div className="p-3 space-y-2 text-[11px]">
      <div className="text-[13px] font-bold">✔ {res.folio} · compendio creado</div>
      <div><b>{res.nombre}</b> · {res.n} transacción{res.n === 1 ? '' : 'es'} · el link vence el <b>{fechaCorta(res.expira_en)}</b></div>
      <label className="flex flex-col gap-0.5 text-[10px]"><b>Link para el cliente</b>
        <input id="link-compendio" readOnly value={link} onFocus={(e) => e.target.select()}
          className="border-2 border-black px-1 py-1 bg-brutalBg font-mono text-[11px] w-full" /></label>
      <div className="flex flex-wrap gap-1">
        <button type="button" className={btnNegro} onClick={copiar}>{copiado ? '✔ COPIADO' : '📋 COPIAR LINK'}</button>
        <a className={btnBlanco} href={`${link}?previa=1`} target="_blank" rel="noopener noreferrer"
          title="Vista previa interna: no cuenta como visita del cliente">↗ ABRIR</a>
        <a className={btnBlanco} target="_blank" rel="noopener noreferrer"
          href={urlWhatsApp(textoWhatsApp({ ...res, link }))}>💬 WHATSAPP</a>
      </div>
      <p className="text-[10px] text-gray-700">Quien tenga el link lo ve sin login hasta que venza. Puedes ampliarlo o revocarlo en
        ⇩ Exportación → 🔗 Compendios. Los comprobantes se leen en vivo, como el botón [Ver] del Libro Diario.</p>
    </div>
  );
}
