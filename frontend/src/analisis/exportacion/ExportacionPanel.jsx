/* ============================================================
   ExportacionPanel.jsx — Sección desplegable "📦 EXPORTACIÓN" de
   ∑ Análisis (spec 13.5). Cabecera liviana con el resumen
   ("12 archivos · 3,1 MB · ⚠ 2 cambiaron"); el organizador vive en
   su propio chunk y solo se descarga al desplegar (CA-135-15).
   /analisis/archivo abre la sección directo (CA-135-14).
   Ver y generar: owner/admin/contador — a otro rol (403) no se le muestra.
   ============================================================ */
import { Component, Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react';
import { api } from './api.js';
import { formatoBytes } from './organizador.js';

const Organizador = lazy(() => import('./Organizador.jsx'));
const RUTA_ARCHIVO = '/analisis/archivo';

const enRutaArchivo = () => (window.location.pathname || '').replace(/\/+$/, '') === RUTA_ARCHIVO;

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
  const [abierto, setAbierto] = useState(enRutaArchivo);
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
    if (enRutaArchivo()) setTimeout(() => ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);
  }, []);

  // Atrás/adelante del navegador mantiene la sección en sync con la URL.
  useEffect(() => {
    const onPop = () => setAbierto(enRutaArchivo());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const alternar = () => {
    const nuevo = !abierto;
    setAbierto(nuevo);
    const destino = nuevo ? RUTA_ARCHIVO : '/analisis';
    if (window.location.pathname !== destino) {
      window.history.replaceState(window.history.state, '', destino + window.location.search);
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
