/* ============================================================
   DiarioGrupos.jsx — Subtotales de lo filtrado por tercero,
   cuenta COA, mes, medio de pago, etiqueta, tipo o empresa.
   Un clic en un grupo lo convierte en filtro.
   ============================================================ */
import { AGRUPACIONES, filtroDeGrupo } from './diarioFiltros.js';

const fmt = (v) => `$${Number(v || 0).toLocaleString('es-CO', { maximumFractionDigits: 0 })}`;

export default function DiarioGrupos({ agrupar, grupos, filtros, setFiltros, onCerrar }) {
  if (!agrupar || !grupos) return null;
  const etiqueta = AGRUPACIONES.find(([k]) => k === agrupar)?.[1] || agrupar;
  const max = Math.max(1, ...grupos.map((g) => Math.max(g.ingresos_cop, g.gastos_cop)));

  return (
    <div className="mb-2 border-2 border-black bg-white">
      <div className="bg-black text-white px-2 py-0.5 flex items-center justify-between text-[10px] font-bold uppercase">
        <span>∑ Subtotales · {etiqueta} · {grupos.length} grupo{grupos.length === 1 ? '' : 's'}</span>
        <button type="button" onClick={onCerrar} className="hover:text-brutalCrimson" aria-label="Quitar agrupación">✕</button>
      </div>
      {agrupar === 'etiqueta' && (
        <div className="px-2 py-0.5 text-[9px] font-mono text-gray-500 border-b border-black">
          Una transacción con varias etiquetas suma en cada una: los subtotales pueden superar el total.
        </div>
      )}
      <div className="max-h-64 overflow-y-auto">
        <table className="w-full text-[10px] font-mono">
          <thead className="bg-brutalBg uppercase sticky top-0">
            <tr className="border-b border-black">
              <th className="px-1 text-left">{etiqueta.replace('Por ', '')}</th>
              <th className="px-1 text-right">N</th>
              <th className="px-1 text-right">Ingresos</th>
              <th className="px-1 text-right">Gastos</th>
              <th className="px-1 text-right">Neto</th>
              <th className="px-1 w-24" />
            </tr>
          </thead>
          <tbody>
            {grupos.map((g) => {
              const neto = g.ingresos_cop - g.gastos_cop;
              const siguiente = filtroDeGrupo(agrupar, g, filtros);
              return (
                <tr key={`${g.clave}-${g.ref ?? ''}`} className={`border-b border-black ${siguiente ? 'hover:bg-brutalBg cursor-pointer' : ''}`}
                  onClick={() => siguiente && setFiltros(siguiente)} title={siguiente ? 'Clic para filtrar por este grupo' : ''}>
                  <td className="px-1 font-bold truncate max-w-[220px]">{g.clave}</td>
                  <td className="px-1 text-right">{g.n}</td>
                  <td className="px-1 text-right text-green-700">{g.ingresos_cop ? fmt(g.ingresos_cop) : '-'}</td>
                  <td className="px-1 text-right text-red-700">{g.gastos_cop ? fmt(g.gastos_cop) : '-'}</td>
                  <td className={`px-1 text-right font-bold ${neto < 0 ? 'text-red-700' : ''}`}>{fmt(neto)}</td>
                  <td className="px-1">
                    <div className="flex h-2 gap-px" aria-hidden="true">
                      <div className="bg-brutalGreen border border-black" style={{ width: `${(g.ingresos_cop / max) * 50}%` }} />
                      <div className="bg-brutalCrimson border border-black" style={{ width: `${(g.gastos_cop / max) * 50}%` }} />
                    </div>
                  </td>
                </tr>
              );
            })}
            {!grupos.length && <tr><td colSpan={6} className="px-1 py-2 text-center text-gray-400 uppercase">Sin datos</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
