/* ============================================================
   AnalisisApp.jsx — Módulo "Análisis" (Análisis Inteligente, hito 1).

   Dos piezas independientes (si una cae, la otra sigue):
   1) Explorador Perspective (B2): tabla plana consolidada de
      GET /api/analytics/dataset — pivoteo/gráficas en WASM local.
   2) Pregunta en español (B3): POST /api/analytics/ask → texto con
      sello de origen + gráfica PNG dibujada por el BACKEND.

   La empresa de la pregunta la elige el USUARIO en el selector y la
   amarra el backend — jamás la decide la IA (criterio inmutable 2).
   ============================================================ */
import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from './api.js';
import {
  VISTAS_PREDEFINIDAS, cargarVistasGuardadas, guardarVista, borrarVista,
} from './vistas.js';
import './analisis.css';

const btn = 'border-2 border-black px-2 py-0.5 text-[10px] font-bold';

export default function AnalisisApp({ user }) {
  // ── Explorador (Perspective) ──
  const viewerRef = useRef(null);
  const tablaRef = useRef(null);
  const [estadoDatos, setEstadoDatos] = useState('cargando'); // cargando|listo|error
  const [errorDatos, setErrorDatos] = useState('');
  const [meta, setMeta] = useState({ n: 0, generado: '' });
  const [vistaActiva, setVistaActiva] = useState(VISTAS_PREDEFINIDAS[0].nombre);
  const [vistasPropias, setVistasPropias] = useState(() => cargarVistasGuardadas());
  const [nombreNuevo, setNombreNuevo] = useState('');
  const [guardando, setGuardando] = useState(false);

  // ── Pregunta (IA) ──
  const [portfolios, setPortfolios] = useState([]);
  const [portfolioId, setPortfolioId] = useState('');   // '' = todas las empresas
  const [pregunta, setPregunta] = useState('');
  const [preguntando, setPreguntando] = useState(false);
  const [respuesta, setRespuesta] = useState(null);
  const [errorPregunta, setErrorPregunta] = useState('');

  // ── Catálogo de métricas (el menú completo de lo que se puede preguntar) ──
  const [catalogo, setCatalogo] = useState(null);       // null = aún no cargado
  const [verCatalogo, setVerCatalogo] = useState(false);

  // Carga del explorador: WASM + dataset → tabla → viewer → vista inicial.
  useEffect(() => {
    let cancelado = false;
    let tabla = null;
    (async () => {
      try {
        const [{ obtenerWorker }, dataset] = await Promise.all([
          import('./perspectiveBoot.js'),
          api.get('/analytics/dataset'),
        ]);
        const worker = await obtenerWorker();
        if (cancelado) return;
        tabla = await worker.table(dataset.esquema);
        if (dataset.filas.length) await tabla.update(dataset.filas);
        tablaRef.current = tabla;
        if (cancelado || !viewerRef.current) return;
        await viewerRef.current.load(tabla);
        await viewerRef.current.restore(VISTAS_PREDEFINIDAS[0].config);
        if (!cancelado) {
          setMeta({ n: dataset.n, generado: dataset.generado });
          setEstadoDatos('listo');
        }
      } catch (e) {
        console.error('Análisis: el explorador no cargó:', e);
        if (!cancelado) {
          setErrorDatos(e.message || 'El explorador no cargó.');
          setEstadoDatos('error');
        }
      }
    })();
    return () => {
      cancelado = true;
      const v = viewerRef.current;
      // delete() libera la memoria WASM (el worker es singleton y queda vivo)
      Promise.resolve()
        .then(() => v?.delete?.())
        .then(() => tabla?.delete?.())
        .catch(() => {});
      tablaRef.current = null;
    };
  }, []);

  // Empresas para amarrar la pregunta (selector del usuario, no de la IA)
  useEffect(() => {
    api.get('/portfolios')
      .then((p) => setPortfolios(Array.isArray(p) ? p : []))
      .catch(() => {});
  }, []);

  const aplicarVista = useCallback(async (nombre, config) => {
    setVistaActiva(nombre);
    try { await viewerRef.current?.restore(config); }
    catch (e) { console.error('Análisis: restore falló:', e); }
  }, []);

  const onGuardarVista = useCallback(async () => {
    if (!viewerRef.current) return;
    try {
      const config = await viewerRef.current.save();
      setVistasPropias({ ...guardarVista(nombreNuevo, config) });
      setVistaActiva(nombreNuevo.trim());
      setNombreNuevo('');
      setGuardando(false);
    } catch (e) {
      setErrorDatos(e.message || 'No se pudo guardar la vista.');
    }
  }, [nombreNuevo]);

  const onVerCatalogo = useCallback(() => {
    setVerCatalogo((v) => !v);
    if (catalogo === null) {
      api.get('/analytics/catalog')
        .then((d) => setCatalogo(Array.isArray(d?.metricas) ? d.metricas : []))
        .catch((e) => setCatalogo({ error: e.message || 'No se pudo cargar el catálogo.' }));
    }
  }, [catalogo]);

  const onPreguntar = useCallback(async (ev) => {
    ev?.preventDefault?.();
    const q = pregunta.trim();
    if (!q || preguntando) return;
    setPreguntando(true);
    setErrorPregunta('');
    setRespuesta(null);
    try {
      const r = await api.post('/analytics/ask', {
        pregunta: q,
        portfolio_id: portfolioId === '' ? null : Number(portfolioId),
      });
      setRespuesta(r);
    } catch (e) {
      setErrorPregunta(e.message || 'La pregunta falló.');
    } finally {
      setPreguntando(false);
    }
  }, [pregunta, preguntando, portfolioId]);

  const datosResp = respuesta?.datos;
  const listaResp = Array.isArray(datosResp?.valores) ? datosResp.valores : null;

  return (
    <div className="min-h-screen bg-brutalBg text-black font-mono p-2 space-y-2 antialiased">
      {/* Cabecera */}
      <div className="bg-white border-2 border-black shadow-brutal p-2 flex flex-wrap items-center gap-2">
        <span className="font-bold text-[13px]">∑ ANÁLISIS</span>
        <span className="text-[10px] border border-black px-1 bg-brutalNeutral">
          {estadoDatos === 'listo' ? `${meta.n} TXs consolidadas` : estadoDatos === 'cargando' ? 'cargando…' : 'sin datos'}
        </span>
        {meta.generado && (
          <span className="text-[10px] text-gray-600">al {meta.generado.replace('T', ' ')}</span>
        )}
        <span className="ml-auto text-[10px]">{user?.name}</span>
      </div>

      {/* Pregunta en español (B3) */}
      <form onSubmit={onPreguntar} className="bg-white border-2 border-black shadow-brutal p-2 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-bold text-[11px]">◉ PREGUNTA</span>
          <select
            value={portfolioId}
            onChange={(e) => setPortfolioId(e.target.value)}
            className="border-2 border-black px-1 py-0.5 text-[10px] bg-white"
            title="La empresa la amarra el sistema — la IA no la decide"
          >
            <option value="">Todas las empresas</option>
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <input
            value={pregunta}
            onChange={(e) => setPregunta(e.target.value)}
            placeholder='Ej: "¿cuánto gasté este mes?", "cartera vencida", "flujo de los últimos 6 meses"'
            className="flex-1 min-w-[220px] border-2 border-black px-2 py-0.5 text-[11px]"
          />
          <button type="submit" disabled={preguntando || !pregunta.trim()}
            className={`${btn} ${preguntando ? 'bg-brutalNeutral' : 'bg-black text-white hover:bg-brutalAmber hover:text-black'}`}>
            {preguntando ? 'CALCULANDO…' : 'PREGUNTAR'}
          </button>
          <button type="button" onClick={onVerCatalogo}
            title="Qué se puede preguntar: el menú completo de métricas del backend"
            className={`${btn} ${verCatalogo ? 'bg-brutalAmber' : 'bg-white hover:bg-brutalNeutral'}`}>
            📖 CATÁLOGO
          </button>
        </div>
        {verCatalogo && (
          <div className="border-2 border-black p-2 bg-brutalBg space-y-1">
            <div className="text-[10px]">
              <b>El menú de métricas.</b> La IA solo puede ELEGIR de esta lista (jamás calcula por
              su cuenta) — si tu pregunta no cae en ninguna, te lo dice honestamente. Clic en una
              para ponerla en el cuadro.
            </div>
            {catalogo === null && <div className="text-[10px]">Cargando catálogo…</div>}
            {catalogo?.error && (
              <div className="bg-brutalCrimson text-white border-2 border-black p-1 text-[10px]">{catalogo.error}</div>
            )}
            {Array.isArray(catalogo) && (
              <div className="grid gap-1 sm:grid-cols-2">
                {catalogo.map((m) => (
                  <button key={m.id} type="button"
                    onClick={() => setPregunta(m.etiqueta)}
                    className="text-left bg-white border-2 border-black p-2 hover:bg-brutalNeutral">
                    <div className="flex flex-wrap items-baseline gap-1">
                      <span className="font-bold text-[11px]">{m.etiqueta}</span>
                      <span className="text-[9px] bg-black text-white px-1">{m.id}</span>
                    </div>
                    <div className="text-[10px] text-gray-700 mt-0.5">{m.descripcion}</div>
                    {Object.keys(m.params || {}).length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {Object.entries(m.params).map(([nombre, p]) => (
                          <span key={nombre} title={p.descripcion}
                            className="text-[9px] border border-black px-1 bg-brutalBg">
                            {nombre}: {p.opciones ? p.opciones.join('|') : p.tipo}
                            {p.requerido ? '' : ' (opcional)'}
                          </span>
                        ))}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {errorPregunta && (
          <div className="bg-brutalCrimson text-white border-2 border-black p-1 text-[10px]">{errorPregunta}</div>
        )}
        {respuesta && (
          <div className="border-2 border-black p-2 space-y-2 bg-brutalBg">
            <div className="text-[12px] font-bold leading-snug">{respuesta.texto}</div>
            {listaResp && listaResp.length > 0 && (
              <table className="text-[10px] border-collapse">
                <tbody>
                  {listaResp.slice(0, 8).map((v) => (
                    <tr key={v.etiqueta || v.mes}>
                      <td className="border border-black px-1">{v.etiqueta || v.mes}</td>
                      <td className="border border-black px-1 text-right">
                        {(v.valor ?? v.neto ?? 0).toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {respuesta.grafica_png_base64 && (
              <img
                src={`data:image/png;base64,${respuesta.grafica_png_base64}`}
                alt="Gráfica generada por el backend"
                className="border-2 border-black bg-white max-w-full"
              />
            )}
            {datosResp?.origen?.sello && (
              <div className="text-[10px] inline-block bg-black text-white px-1">⚑ {datosResp.origen.sello}</div>
            )}
          </div>
        )}
      </form>

      {/* Vistas del explorador (B2) */}
      <div className="flex flex-wrap items-center gap-1">
        {VISTAS_PREDEFINIDAS.map((v) => (
          <button key={v.nombre}
            className={`${btn} ${vistaActiva === v.nombre ? 'bg-black text-white' : 'bg-white hover:bg-brutalNeutral'}`}
            onClick={() => aplicarVista(v.nombre, v.config)}>
            {v.nombre.toUpperCase()}
          </button>
        ))}
        {Object.entries(vistasPropias).map(([nombre, config]) => (
          <span key={nombre} className="inline-flex">
            <button
              className={`${btn} ${vistaActiva === nombre ? 'bg-black text-white' : 'bg-brutalAmber hover:bg-brutalNeutral'}`}
              onClick={() => aplicarVista(nombre, config)}>
              ★ {nombre.toUpperCase()}
            </button>
            <button title={`Borrar la vista "${nombre}"`}
              className={`${btn} bg-white hover:bg-brutalCrimson hover:text-white`}
              onClick={() => setVistasPropias({ ...borrarVista(nombre) })}>
              ✕
            </button>
          </span>
        ))}
        {guardando ? (
          <span className="inline-flex gap-1">
            <input autoFocus value={nombreNuevo}
              onChange={(e) => setNombreNuevo(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') onGuardarVista(); if (e.key === 'Escape') setGuardando(false); }}
              placeholder="nombre de la vista"
              className="border-2 border-black px-1 py-0.5 text-[10px] w-40" />
            <button className={`${btn} bg-black text-white`} disabled={!nombreNuevo.trim()} onClick={onGuardarVista}>OK</button>
            <button className={`${btn} bg-white`} onClick={() => setGuardando(false)}>✕</button>
          </span>
        ) : (
          <button className={`${btn} bg-white hover:bg-brutalNeutral ml-auto`}
            disabled={estadoDatos !== 'listo'}
            onClick={() => setGuardando(true)}>
            💾 GUARDAR VISTA
          </button>
        )}
      </div>

      {errorDatos && (
        <div className="bg-brutalCrimson text-white border-2 border-black p-1 text-[10px]">
          Explorador sin datos: {errorDatos} (la pregunta de arriba sigue funcionando)
        </div>
      )}

      {/* El visor: pivoteo en WASM dentro del navegador */}
      <div className="analisis-visor border-2 border-black shadow-brutal bg-white relative">
        {estadoDatos === 'cargando' && (
          <div className="absolute inset-0 flex items-center justify-center text-[11px] font-bold bg-white/80 z-10">
            ⏳ Cargando motor de análisis…
          </div>
        )}
        <perspective-viewer ref={viewerRef} theme="Pro Light" />
      </div>
    </div>
  );
}
