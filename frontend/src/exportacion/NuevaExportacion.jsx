/* ============================================================
   NuevaExportacion.jsx — 📥 Nueva exportación (spec 13.5-c).

   Formulario único con atajos (investigación 06-oct: Siigo, Odoo y
   Helisa usan centro de reportes, no asistente), dos pestañas:
   · 📚 Libros por período: paquete → empresa → período → libros →
     avanzado (plegado) — receta del motor 13.4, modo período.
   · 🧾 Transacciones: buscar/filtrar/marcar → Relación (modo
     transacciones, máx. 5000).
   El pre-vuelo es la compuerta: GENERAR solo se activa cuando la
   revisión corresponde EXACTAMENTE a lo que está en pantalla.
   Al generar: folio EXP-AAAA-NNNN + SHA-256, archivo al organizador
   y descarga inmediata.
   ============================================================ */
import { useEffect, useMemo, useState } from 'react';
import { api } from './api.js';
import { Modal, AvisoError, DialogoTexto, btnNegro, btnBlanco } from './Dialogos.jsx';
import { formatoBytes } from './organizador.js';
import { ATAJOS, rangoRelativo, rangoMes, atajoDe } from './periodos.js';
import {
  GRUPOS_HOJAS, NIVELES_PUC, TIPOS_TX, ATAJO_DE_PAQUETE, PERSONALIZADO, MAX_TX,
  paqueteDeHojas, hojasDePaquete, recetaPeriodo, validarPeriodo, recetaTransacciones, distintos,
} from './paquetes.js';
import SelectorTransacciones from './SelectorTransacciones.jsx';

const campo = 'border-2 border-black px-1 py-0.5 text-[10px] bg-white';
const chip = (activo) => `border-2 border-black px-2 py-0.5 text-[10px] font-bold ${activo ? 'bg-black text-white' : 'bg-white hover:bg-brutalNeutral'}`;
const pesos = (n) => `$${Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 })}`;

/** Estado inicial del formulario de período (paquete, ubicación del organizador o mes anterior). */
function formInicial(predefinidos, inicial = {}) {
  const paquete = inicial.paquete && predefinidos.some((p) => p.clave === inicial.paquete) ? inicial.paquete : 'cierre_mes';
  let atajo = ATAJO_DE_PAQUETE[paquete] || 'mes_anterior';
  let rango = rangoRelativo(atajo);
  if (inicial.anio && inicial.mes) { rango = rangoMes(inicial.anio, inicial.mes); atajo = atajoDe(rango.desde, rango.hasta) || ''; }
  return {
    paquete, atajo, ...rango, hojas: hojasDePaquete(predefinidos, paquete),
    empresas: inicial.pid ? [Number(inicial.pid)] : [],
    nivelPuc: '', tipos: [], moneda: '', terceros: [], categorias: [], cuentasPuc: '', nombre: '',
  };
}

function Seccion({ n, titulo, ayuda, children }) {
  return (
    <section className="border-2 border-black bg-white">
      <div className="flex flex-wrap items-baseline gap-2 px-2 py-1 border-b-2 border-black bg-brutalBg">
        <span className="font-bold text-[11px]">{n}. {titulo}</span>
        {ayuda && <span className="text-[10px] text-gray-600">{ayuda}</span>}
      </div>
      <div className="p-2">{children}</div>
    </section>
  );
}

function Revision({ prevuelo }) {
  if (!prevuelo) return null;
  const { sello: s, tamano_bytes: tam, excede_tope: excede, max_mb: maxMb } = prevuelo;
  const tc = s.totales_control || {};
  const relacion = s.modo === 'transacciones';
  const empresas = s.consolidado ? 'Consolidado (todas las empresas)' : (s.empresas || []).map((e) => e.nombre).join(', ');
  const rango = s.rango_real?.desde ? `${s.rango_real.desde} – ${s.rango_real.hasta}` : 'sin movimientos';
  return (
    <section aria-label="Revisión previa" className={`border-2 border-black p-2 text-[10px] space-y-1 ${tc.cuadra ? 'bg-white' : 'bg-brutalAmber/30'}`}>
      <div className="font-bold text-[11px]">🔍 REVISIÓN PREVIA — lo que dirá la carátula</div>
      <div className="grid sm:grid-cols-2 gap-x-4 gap-y-0.5">
        {relacion ? (
          <div className="sm:col-span-2"><b>Relación de transacciones elegidas</b> · fechas de los movimientos: {rango}</div>
        ) : (
          <>
            <div><b>Empresas:</b> {empresas || '—'}</div>
            <div><b>Período:</b> {s.desde || 'inicio'} → {s.hasta || '—'}
              <span className="text-gray-600"> ({s.rango_real?.desde ? `movimientos del ${s.rango_real.desde} al ${s.rango_real.hasta}` : 'sin movimientos'})</span></div>
          </>
        )}
        <div><b>Transacciones:</b> {s.n_txs}{s.n_txs_filtradas != null && s.n_txs_filtradas !== s.n_txs ? ` · ${s.n_txs_filtradas} tras los filtros` : ''}</div>
        <div><b>Asientos en libros:</b> {s.n_asientos} · {s.n_lineas} líneas</div>
        <div><b>Σ débitos:</b> {pesos(tc.debitos)} · <b>Σ créditos:</b> {pesos(tc.creditos)}</div>
        <div className={`font-bold ${tc.cuadra ? '' : 'text-brutalCrimson'}`}>
          {tc.cuadra ? '✔ Partida doble: débitos = créditos' : '✘ No cuadra — revisar antes de entregar'}</div>
        <div><b>Hojas:</b> {(s.hojas || []).join(' · ')}</div>
        <div><b>Tamaño:</b> {formatoBytes(tam)}{excede ? ` — supera el tope de ${maxMb} MB` : ''}</div>
      </div>
      {s.otras_monedas && Object.keys(s.otras_monedas).length > 0 && (
        <div><b>Otras monedas:</b> {Object.entries(s.otras_monedas).map(([m, n]) => `${m}: ${n} TX (aparte, nunca sumadas al COP)`).join('; ')}</div>
      )}
      {s.advertencias?.length > 0 && (
        <ul className="list-disc pl-4 space-y-0.5">
          {s.advertencias.map((a, i) => <li key={i}>⚠ {a}</li>)}
        </ul>
      )}
    </section>
  );
}

export default function NuevaExportacion({ paquetes, portfolios, carpetas, inicial, onCerrar, onGenerado }) {
  const predefinidos = useMemo(() => paquetes?.predefinidos || [], [paquetes]);
  const [guardados, setGuardados] = useState(() => paquetes?.guardados || []);
  const [modo, setModo] = useState(inicial?.modo === 'transacciones' ? 'transacciones' : 'periodo');
  const [f, setF] = useState(() => formInicial(predefinidos, inicial));
  const [guardadoActivo, setGuardadoActivo] = useState(null);
  const [avanzado, setAvanzado] = useState(false);
  const [carpeta, setCarpeta] = useState('');
  const [seleccion, setSeleccion] = useState(() => new Set(inicial?.txIds || []));   // ids marcados en el Libro Diario
  const [nombreRelacion, setNombreRelacion] = useState('');
  const [txs, setTxs] = useState({ lista: [], cargando: true, error: '' });
  const [prevuelo, setPrevuelo] = useState(null);         // { firma, data }
  const [ocupado, setOcupado] = useState('');             // '' | 'revisando' | 'generando'
  const [error, setError] = useState('');
  const [hecho, setHecho] = useState(null);
  const [dialogo, setDialogo] = useState(null);

  // El Libro Diario: alimenta el selector y las listas del avanzado (terceros, categorías).
  useEffect(() => {
    let vivo = true;
    api.get('/transactions')
      .then((d) => { if (vivo) setTxs({ lista: Array.isArray(d) ? d : [], cargando: false, error: '' }); })
      .catch((e) => { if (vivo) setTxs({ lista: [], cargando: false, error: e.message }); });
    return () => { vivo = false; };
  }, []);

  const set = (cambios) => { setF((x) => ({ ...x, ...cambios })); setGuardadoActivo(null); };
  const elegirPaquete = (p) => {
    const atajo = ATAJO_DE_PAQUETE[p.clave];
    set({ paquete: p.clave, hojas: hojasDePaquete(predefinidos, p.clave), ...(atajo ? { atajo, ...rangoRelativo(atajo) } : {}) });
  };
  const aplicarGuardado = (g) => {
    const r = g.receta || {};
    const rango = r.relativo ? rangoRelativo(r.relativo) : { desde: r.desde || '', hasta: r.hasta || f.hasta };
    const hojas = (r.hojas || []).filter((h) => h !== 'caratula');
    const fil = r.filtros || {};
    setF({
      ...f, ...rango, atajo: r.relativo || '', hojas, paquete: paqueteDeHojas(predefinidos, hojas),
      empresas: r.portfolios?.length ? r.portfolios : (r.portfolio_id ? [r.portfolio_id] : []),
      nivelPuc: r.nivel_puc || '', tipos: fil.tipos || [], moneda: fil.moneda || '', terceros: fil.terceros || [],
      categorias: fil.categorias || [], cuentasPuc: (fil.cuentas_puc || []).join(', '), nombre: '',
    });
    setGuardadoActivo(g.id);
  };
  const alternarHoja = (h) => {
    const hojas = f.hojas.includes(h) ? f.hojas.filter((x) => x !== h) : [...f.hojas, h];
    set({ hojas, paquete: paqueteDeHojas(predefinidos, hojas) });
  };
  const alternarEn = (k, v) => set({ [k]: f[k].includes(v) ? f[k].filter((x) => x !== v) : [...f[k], v] });
  const elegirAtajo = (clave) => set({ atajo: clave, ...rangoRelativo(clave) });

  // Lo que se mandaría AHORA (la revisión solo vale para esto).
  const solicitud = useMemo(() => {
    if (modo === 'periodo') {
      const err = validarPeriodo(f);
      return err ? { error: err } : recetaPeriodo(f);
    }
    if (!seleccion.size) return { error: 'Marca al menos una transacción.' };
    if (seleccion.size > MAX_TX) return { error: `Máximo ${MAX_TX} transacciones por relación.` };
    return recetaTransacciones([...seleccion].sort((a, b) => a - b), nombreRelacion);
  }, [modo, f, seleccion, nombreRelacion]);
  const firma = solicitud.error ? null : JSON.stringify(solicitud);
  const revisionVigente = prevuelo && prevuelo.firma === firma ? prevuelo.data : null;
  const puedeGenerar = !!revisionVigente && !revisionVigente.excede_tope && !ocupado;

  const revisar = async () => {
    if (solicitud.error) { setError(solicitud.error); return; }
    setOcupado('revisando'); setError('');
    try {
      const data = await api.post('/analytics/export/preflight', { receta: solicitud.receta, paquete: solicitud.paquete });
      setPrevuelo({ firma, data });
    } catch (e) { setError(e.message); } finally { setOcupado(''); }
  };
  const generar = async () => {
    setOcupado('generando'); setError('');
    try {
      const res = await api.post('/analytics/export', {
        receta: solicitud.receta, paquete: solicitud.paquete, folder_id: carpeta ? Number(carpeta) : null,
      });
      setHecho(res);
      onGenerado?.(res);
      api.descargar(res.id, res.nombre_archivo).catch((e) => setError(`Se archivó, pero la descarga falló: ${e.message}`));
    } catch (e) { setError(e.message); } finally { setOcupado(''); }
  };
  const guardarPaquete = () => setDialogo(
    <DialogoTexto titulo="★ Guardar como paquete" etiqueta="Nombre del paquete (ej.: Para el banco Bancolombia)"
      onCerrar={() => setDialogo(null)}
      onOk={async (nombre) => {
        const g = await api.post('/analytics/export/paquetes', { nombre, receta: solicitud.receta });
        setGuardados((xs) => [...xs, g]);
        setGuardadoActivo(g?.id ?? null);
        setDialogo(null);
      }} />,
  );

  const terceros = useMemo(() => {
    const m = new Map();
    txs.lista.forEach((t) => { if (t.third_party_id != null) m.set(t.third_party_id, t.third_party_name || `#${t.third_party_id}`); });
    return [...m.entries()].sort((a, b) => String(a[1]).localeCompare(String(b[1]), 'es'));
  }, [txs.lista]);
  const categorias = useMemo(() => distintos(txs.lista, 'category'), [txs.lista]);
  const carpetasPropias = (carpetas || []).filter((c) => c && c.id != null);

  const pie = hecho ? (
    <>
      <button type="button" className={btnBlanco} onClick={() => { setHecho(null); setPrevuelo(null); }}>OTRA EXPORTACIÓN</button>
      <button type="button" className={btnNegro} onClick={onCerrar}>LISTO</button>
    </>
  ) : (
    <>
      <span className="mr-auto self-center text-[10px] text-gray-700">
        {solicitud.error ? `⚠ ${solicitud.error}`
          : revisionVigente ? (revisionVigente.excede_tope ? '✘ Supera el tope de tamaño: acota el período o los libros.' : '✔ Revisado: ya puedes generar.')
            : 'Primero REVISAR: verás conteos, cuadre y advertencias antes de generar.'}
      </span>
      <button type="button" className={btnBlanco} onClick={onCerrar}>CANCELAR</button>
      <button type="button" className={btnBlanco} disabled={!!solicitud.error || !!ocupado} onClick={revisar}>
        {ocupado === 'revisando' ? '⏳ REVISANDO…' : '🔍 REVISAR'}</button>
      <button type="button" className={btnNegro} disabled={!puedeGenerar} onClick={generar}
        title={revisionVigente ? 'Genera el libro con folio, lo guarda en el archivo y lo descarga' : 'Revisa primero'}>
        {ocupado === 'generando' ? '⏳ GENERANDO…' : '📥 GENERAR Y DESCARGAR'}</button>
    </>
  );

  return (
    <>
      <Modal titulo="📥 NUEVA EXPORTACIÓN" onCerrar={onCerrar} pie={pie} ancho="max-w-5xl">
        {hecho ? (
          <div className="p-3 space-y-2 text-[11px]">
            <div className="text-[13px] font-bold">✔ {hecho.folio || 'Exportación'} generada</div>
            <div><b>{hecho.nombre}</b> · {formatoBytes(hecho.tamano_bytes)}</div>
            <div className="text-[10px] text-gray-700 break-all">SHA-256: {hecho.sha256}</div>
            <div className="text-[10px]">Quedó en el archivo (con su folio y huella) y se descargó en tu equipo.
              Si los libros cambian después, el archivo mostrará ⚠ y podrás regenerarlo.</div>
            <AvisoError texto={error} />
          </div>
        ) : (
          <div className="space-y-2">
            <div role="tablist" className="flex flex-wrap gap-1">
              <button type="button" role="tab" aria-selected={modo === 'periodo'} className={chip(modo === 'periodo')}
                onClick={() => setModo('periodo')}>📚 LIBROS POR PERÍODO</button>
              <button type="button" role="tab" aria-selected={modo === 'transacciones'} className={chip(modo === 'transacciones')}
                onClick={() => setModo('transacciones')}>🧾 TRANSACCIONES (FILTRAR O ELEGIR)</button>
            </div>

            {modo === 'periodo' ? (
              <>
                <Seccion n={1} titulo="PAQUETE" ayuda="atajo de libros; si cambias los libros pasa a personalizado">
                  <div className="flex flex-wrap gap-1">
                    {predefinidos.map((p) => (
                      <button key={p.clave} type="button" aria-pressed={f.paquete === p.clave && !guardadoActivo}
                        className={chip(f.paquete === p.clave && !guardadoActivo)} onClick={() => elegirPaquete(p)}>
                        {p.icono} {p.nombre}</button>
                    ))}
                    {f.paquete === PERSONALIZADO && !guardadoActivo && <span className={chip(true)}>✎ Personalizado</span>}
                    {guardados.map((g) => (
                      <button key={g.id} type="button" aria-pressed={guardadoActivo === g.id} className={chip(guardadoActivo === g.id)}
                        onClick={() => aplicarGuardado(g)} title={`Guardado por ${g.creado_por || '—'}`}>★ {g.nombre}</button>
                    ))}
                  </div>
                </Seccion>

                <Seccion n={2} titulo="EMPRESA" ayuda="ninguna marcada = consolidado de todas">
                  <div className="flex flex-wrap gap-1">
                    <button type="button" aria-pressed={!f.empresas.length} className={chip(!f.empresas.length)}
                      onClick={() => set({ empresas: [] })}>∑ Consolidado</button>
                    {(portfolios || []).map((p) => (
                      <button key={p.id} type="button" aria-pressed={f.empresas.includes(p.id)} className={chip(f.empresas.includes(p.id))}
                        onClick={() => alternarEn('empresas', p.id)}>🏢 {p.etiqueta || p.name}</button>
                    ))}
                  </div>
                </Seccion>

                <Seccion n={3} titulo="PERÍODO">
                  <div className="flex flex-wrap items-center gap-1">
                    {ATAJOS.map((a) => (
                      <button key={a.clave} type="button" aria-pressed={f.atajo === a.clave} className={chip(f.atajo === a.clave)}
                        onClick={() => elegirAtajo(a.clave)}>{a.etiqueta}</button>
                    ))}
                    <span className="ml-1 text-[10px] font-bold">Desde</span>
                    <input type="date" value={f.desde} aria-label="Desde" className={campo}
                      onChange={(e) => set({ desde: e.target.value, atajo: '' })} />
                    <span className="text-[10px] font-bold">Hasta</span>
                    <input type="date" value={f.hasta} aria-label="Hasta" className={campo}
                      onChange={(e) => set({ hasta: e.target.value, atajo: '' })} />
                  </div>
                </Seccion>

                <Seccion n={4} titulo="LIBROS" ayuda="la carátula (sello, totales de control y advertencias) va siempre">
                  <div className="grid sm:grid-cols-3 gap-2">
                    {GRUPOS_HOJAS.map((g) => (
                      <fieldset key={g.titulo} className="border border-black p-1">
                        <legend className="px-1 text-[10px] font-bold">{g.titulo}</legend>
                        {g.hojas.map(([h, etiqueta]) => (
                          <label key={h} className="flex items-center gap-1 text-[10px] py-0.5 cursor-pointer">
                            <input type="checkbox" checked={f.hojas.includes(h)} onChange={() => alternarHoja(h)} /> {etiqueta}
                          </label>
                        ))}
                      </fieldset>
                    ))}
                  </div>
                </Seccion>

                <section className="border-2 border-black bg-white">
                  <button type="button" aria-expanded={avanzado} onClick={() => setAvanzado((v) => !v)}
                    className="w-full text-left px-2 py-1 font-bold text-[11px] bg-brutalBg hover:bg-brutalNeutral">
                    {avanzado ? '▾' : '▸'} 5. AVANZADO <span className="font-normal text-[10px] text-gray-600">nivel PUC, filtros, nombre, carpeta, guardar paquete</span>
                  </button>
                  {avanzado && (
                    <div className="p-2 grid sm:grid-cols-2 gap-2 border-t-2 border-black text-[10px]">
                      <label className="flex flex-col gap-0.5"><b>Nivel del PUC</b>
                        <select value={f.nivelPuc} onChange={(e) => set({ nivelPuc: e.target.value })} className={campo}>
                          {NIVELES_PUC.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
                        </select></label>
                      <label className="flex flex-col gap-0.5"><b>Moneda</b>
                        <select value={f.moneda} onChange={(e) => set({ moneda: e.target.value })} className={campo}>
                          <option value="">Todas (USD en bloque aparte)</option><option value="COP">Solo COP</option><option value="USD">Solo USD</option>
                        </select></label>
                      <div className="flex flex-col gap-0.5"><b>Tipos de transacción</b>
                        <div className="flex flex-wrap gap-2">{TIPOS_TX.map((t) => (
                          <label key={t} className="flex items-center gap-1"><input type="checkbox" checked={f.tipos.includes(t)}
                            onChange={() => alternarEn('tipos', t)} /> {t}</label>))}</div></div>
                      <label className="flex flex-col gap-0.5"><b>Cuentas PUC (prefijos, separados por coma)</b>
                        <input value={f.cuentasPuc} onChange={(e) => set({ cuentasPuc: e.target.value })} placeholder="Ej.: 1105, 4135, 5135"
                          className={campo} /></label>
                      <div className="flex flex-col gap-0.5"><b>Categorías</b>
                        <div className="border border-black max-h-24 overflow-auto p-1 bg-white">{categorias.map((c) => (
                          <label key={c} className="flex items-center gap-1"><input type="checkbox" checked={f.categorias.includes(c)}
                            onChange={() => alternarEn('categorias', c)} /> {c}</label>))}
                          {!categorias.length && <span className="text-gray-600">{txs.cargando ? 'cargando…' : 'sin categorías'}</span>}</div></div>
                      <div className="flex flex-col gap-0.5"><b>Terceros</b>
                        <div className="border border-black max-h-24 overflow-auto p-1 bg-white">{terceros.map(([id, n]) => (
                          <label key={id} className="flex items-center gap-1"><input type="checkbox" checked={f.terceros.includes(id)}
                            onChange={() => alternarEn('terceros', id)} /> {n}</label>))}
                          {!terceros.length && <span className="text-gray-600">{txs.cargando ? 'cargando…' : 'sin terceros'}</span>}</div></div>
                      <label className="flex flex-col gap-0.5"><b>Nombre del archivo (opcional)</b>
                        <input value={f.nombre} maxLength={120} onChange={(e) => set({ nombre: e.target.value })}
                          placeholder="Por defecto: paquete · empresa · período" className={campo} /></label>
                      <label className="flex flex-col gap-0.5"><b>Guardar también en la carpeta</b>
                        <select value={carpeta} onChange={(e) => setCarpeta(e.target.value)} className={campo}>
                          <option value="">— solo en su lugar automático (empresa › año › mes) —</option>
                          {carpetasPropias.map((c) => <option key={c.id} value={c.id}>📁 {c.nombre}</option>)}
                        </select></label>
                      <div className="sm:col-span-2">
                        <button type="button" className={btnBlanco} disabled={!!solicitud.error} onClick={guardarPaquete}
                          title="Guarda esta receta (empresa, libros, filtros y período relativo) para repetirla con un clic">
                          ★ GUARDAR COMO PAQUETE</button>
                      </div>
                    </div>
                  )}
                </section>
              </>
            ) : (
              <>
                <SelectorTransacciones txs={txs.lista} cargando={txs.cargando} error={txs.error}
                  seleccion={seleccion} onSeleccion={setSeleccion} nombre={nombreRelacion} onNombre={setNombreRelacion}
                  soloMarcadasInicial={!!inicial?.txIds?.length} />
                <label className="flex flex-wrap items-center gap-1 text-[10px]">
                  <b>Guardar también en la carpeta</b>
                  <select value={carpeta} onChange={(e) => setCarpeta(e.target.value)} className={campo}>
                    <option value="">— solo en su lugar automático —</option>
                    {carpetasPropias.map((c) => <option key={c.id} value={c.id}>📁 {c.nombre}</option>)}
                  </select>
                </label>
              </>
            )}

            <Revision prevuelo={revisionVigente} />
            {prevuelo && !revisionVigente && !solicitud.error && (
              <div className="text-[10px] border-2 border-dashed border-black p-1">Cambiaste algo después de revisar: vuelve a REVISAR.</div>
            )}
            <AvisoError texto={error} />
          </div>
        )}
      </Modal>
      {dialogo}
    </>
  );
}
