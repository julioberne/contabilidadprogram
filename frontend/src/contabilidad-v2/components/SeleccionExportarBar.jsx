/* ============================================================
   SeleccionExportarBar.jsx — Barra de acción de las casillas del
   Libro Diario (spec 13.5 §4.3, CA-135-08). Pegada abajo mientras
   haya ≥1 TX marcada: "☑ N seleccionadas · ▲ ING · ▼ GAS (por
   moneda) · ✕ Limpiar · 📥 Exportar selección".
   📥 abre ahí mismo Nueva exportación (módulo 14) en modo
   transacciones con lo marcado; su código se carga en diferido
   y el modal va en un portal para que ninguna capa lo tape.
   ============================================================ */
import { lazy, Suspense, useState } from 'react';
import { createPortal } from 'react-dom';
import { resumenSeleccion } from '../modules/diario/seleccion.js';

const ExportarSeleccion = lazy(() => import('../../exportacion/ExportarSeleccion.jsx'));

const monto = (v, moneda) => `${moneda === 'COP' ? '$' : `${moneda} `}${Number(v || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 })}`;
const boton = 'border-2 border-white px-2 py-0.5 uppercase font-bold';

export default function SeleccionExportarBar({ txs, onLimpiar, onGenerado }) {
  const [abierto, setAbierto] = useState(false);
  const { n, porMoneda } = resumenSeleccion(txs);
  if (!n) return null;

  return (
    <>
      <div role="region" aria-label="Selección para exportar"
        className="sticky bottom-0 z-20 mt-1 bg-black text-white border-2 border-black shadow-brutal px-2 py-1 flex flex-wrap items-center gap-1 font-mono text-[10px] font-bold uppercase">
        <span>☑ {n} seleccionada{n === 1 ? '' : 's'}</span>
        {Object.entries(porMoneda).map(([m, t]) => (
          <span key={m} className="inline-flex gap-1">
            <span className="border border-white bg-brutalGreen text-black px-1">▲ ING {monto(t.ingresos, m)}</span>
            <span className="border border-white bg-brutalCrimson text-white px-1">▼ GAS {monto(t.gastos, m)}</span>
          </span>
        ))}
        <span className="ml-auto inline-flex gap-1">
          <button type="button" onClick={onLimpiar} className={`${boton} bg-black hover:bg-white hover:text-black`}>✕ Limpiar</button>
          <button type="button" onClick={() => setAbierto(true)}
            title="Relación de transacciones con folio: carátula, relación, asientos, resumen y soportes"
            className={`${boton} bg-brutalAmber text-black hover:bg-white`}>📥 Exportar selección</button>
        </span>
      </div>
      {abierto && createPortal(
        <Suspense fallback={null}>
          <ExportarSeleccion txIds={txs.map((t) => t.id)} onCerrar={() => setAbierto(false)} onGenerado={onGenerado} />
        </Suspense>,
        document.body,
      )}
    </>
  );
}
