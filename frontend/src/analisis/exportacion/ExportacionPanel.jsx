/* ============================================================
   ExportacionPanel.jsx — Sección desplegable "📦 EXPORTACIÓN" de
   ∑ Análisis (spec 13.5). Cabecera liviana con el resumen
   ("12 archivos · 3,1 MB · ⚠ 2 cambiaron"); el organizador vive en
   su propio chunk y solo se descarga al desplegar (CA-135-15).
   /analisis/exportacion abre la sección directo (CA-135-14), también
   desde el sub-ítem 📦 Exportación del menú lateral.
   Ver y generar: owner/admin/contador — a otro rol (403) no se le muestra.
   ============================================================ */
import { Component, Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react';
import { api } from './api.js';
import { formatoBytes } from './organizador.js';

const Organizador = lazy(() => import('./Organizador.jsx'));
const RUTA_EXPORTACION = '/analisis/exportacion';
// Mismo nombre que EVENTO_RUTA de shell/useRoute.js (no se importa el shell desde este chunk).
const EVENTO_RUTA = 'finsys:ruta';

const enRutaExportacion = () => (window.location.pathname || '').replace(/\/+$/, '') === RUTA_EXPORTACION;
const irALaSeccion = (ref) => setTimeout(() => ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);

/** Si el organizador cae (o su chunk no baja), el resto de ∑ Análisis sigue en pie. */
class Limite extends Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error) { console.error('Análisis 📦: el organizador falló:', error); }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div role="alert" className="bg-white border-2 border-black shadow-brutal p-2 text-[10px] flex flex-wrap items-center gap-2">
        <b>📦 EXPORTACIÓN</b>
        <span className="bg-brutalCrimson text-white px-1">no cargó: {this.state.error.message || 'error'}</span>
        <button type="button" className="border-2 border-black px-2 font-bold bg-white hover:bg-brutalNeutral"
          onClick={() => this.setState({ error: null })}>REINTENTAR</button>
      </div>
    );
  }
}

export default function ExportacionPanel(props) {
  return <Limite><Panel {...props} /></Limite>;
}

function Panel({ user }) {
  const [abierto, setAbierto] = useState(enRutaExportacion);
  const [resumen, setResumen] = useState(null);      // null = cargando
  const [error, setError] = useState('');
  const [sinPermiso, setSinPermiso] = useState(false);
  const ref = useRef(null);

  const cargarResumen = useCallback(() => api.get('/accounting-files/resumen')
    .then((r) => { setResumen(r); setError(''); })
    .catch((e) => { if (e.status === 403) setSinPermiso(true); else setError(e.message); }), []);

  useEffect(() => { cargarResumen(); }, [cargarResumen]);

  // Entrada por enlace directo: llevar la vista a la sección.
  useEffect(() => {
    if (enRutaExportacion()) irALaSeccion(ref);
  }, []);

  // Atrás/adelante y el menú lateral (ya dentro de Análisis) mantienen la
  // sección en sync con la URL. El aviso del propio botón no se re-procesa.
  useEffect(() => {
    const sync = (e) => {
      if (e.detail?.origen === 'exportacion') return;
      const dentro = enRutaExportacion();
      setAbierto(dentro);
      if (dentro) irALaSeccion(ref);
    };
    window.addEventListener('popstate', sync);
    window.addEventListener(EVENTO_RUTA, sync);
    return () => {
      window.removeEventListener('popstate', sync);
      window.removeEventListener(EVENTO_RUTA, sync);
    };
  }, []);

  const alternar = () => {
    const nuevo = !abierto;
    setAbierto(nuevo);
    const destino = nuevo ? RUTA_EXPORTACION : '/analisis';
    if (window.location.pathname !== destino) {
      window.history.replaceState(window.history.state, '', destino + window.location.search);
      // La barra lateral resalta (o no) el sub-ítem 📦 Exportación.
      window.dispatchEvent(new CustomEvent(EVENTO_RUTA, { detail: { path: destino, origen: 'exportacion' } }));
    }
  };

  if (sinPermiso) return null;

  return (
    <section ref={ref} aria-label="Exportación" className="bg-white border-2 border-black shadow-brutal scroll-mt-2">
      <button type="button" onClick={alternar} aria-expanded={abierto} aria-controls="organizador-contable"
        className={`w-full flex flex-wrap items-center gap-2 p-2 text-left ${abierto ? 'border-b-2 border-black bg-brutalBg' : 'hover:bg-brutalBg'}`}>
        <span className="font-bold text-[13px]">📦 EXPORTACIÓN</span>
        <span className="text-[11px] font-bold">{abierto ? '▴' : '▾'}</span>
        {resumen && (
          <span className="text-[10px] border border-black px-1 bg-brutalNeutral">
            {resumen.archivos} archivo{resumen.archivos === 1 ? '' : 's'} · {formatoBytes(resumen.bytes)}
          </span>
        )}
        {resumen?.cambiaron > 0 && (
          <span className="text-[10px] font-bold border border-black px-1 bg-brutalAmber" title="Los libros cambiaron después de exportarlos">
            ⚠ {resumen.cambiaron} cambiaron
          </span>
        )}
        {resumen?.por_vencer > 0 && (
          <span className="text-[10px] border border-black px-1 bg-white" title={`Se purgan pronto si no los fijas (${resumen.retencion_dias} días)`}>
            ⏳ {resumen.por_vencer} por vencer
          </span>
        )}
        {!resumen && !error && <span className="text-[10px] text-gray-600">cargando…</span>}
        {error && <span className="text-[10px] bg-brutalCrimson text-white px-1">{error}</span>}
        <span className="ml-auto text-[10px] text-gray-600 hidden sm:inline">
          libros con folio · relaciones de TXs · documentos subidos
        </span>
      </button>
      {abierto && (
        <div id="organizador-contable" className="p-2 bg-brutalBg">
          <Suspense fallback={<div className="p-4 text-center font-bold text-[11px]">⏳ Cargando el organizador…</div>}>
            <Organizador user={user} resumen={resumen} onCambio={cargarResumen} />
          </Suspense>
        </div>
      )}
    </section>
  );
}
