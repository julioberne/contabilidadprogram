/* ============================================================
   CalendarioCierres.jsx — Vista 🗓 del organizador (spec 13.5-d,
   CA-135-13): una fila por paquete y una columna por mes, con el
   último folio de cada cierre y su vigencia (✅ vigente · ⚠ los
   libros cambiaron). Clic en un folio → lo abre; clic en "—" →
   📥 Nueva exportación ya cargada con ese paquete, mes y empresa.
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { api } from './api.js';
import { AvisoError, btnBlanco } from './Dialogos.jsx';
import { MESES_CORTOS } from './organizador.js';
import { ESTADO_CIERRE, celda, folioCorto, mesAbierto, resumenFila } from './cierres.js';

export default function CalendarioCierres({ portfolios, pidInicial, onAbrir, onNueva }) {
  const [anio, setAnio] = useState(() => new Date().getFullYear());
  const [pid, setPid] = useState(pidInicial ? String(pidInicial) : '');
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');

  const cargar = useCallback(() => api.get(`/accounting-files/cierres?anio=${anio}${pid ? `&portfolio_id=${pid}` : ''}`)
    .then((d) => { setDatos(d); setError(''); })
    .catch((e) => { setDatos(null); setError(e.message); }), [anio, pid]);
  useEffect(() => { cargar(); }, [cargar]);

  const hoy = new Date();
  const paquetes = datos?.paquetes || [];
  return (
    <section aria-label="Vista de cierres" className="space-y-1">
      <div className="flex flex-wrap items-center gap-1 text-[10px]">
        <span className="font-bold text-[11px]">🗓 CIERRES</span>
        <button type="button" className={btnBlanco} onClick={() => setAnio((a) => a - 1)} aria-label="Año anterior">◀</button>
        <b className="px-1">{anio}</b>
        <button type="button" className={btnBlanco} onClick={() => setAnio((a) => a + 1)} aria-label="Año siguiente"
          disabled={anio >= hoy.getFullYear()}>▶</button>
        <select value={pid} onChange={(e) => setPid(e.target.value)} aria-label="Empresa"
          className="border-2 border-black px-1 py-0.5 text-[10px] bg-white">
          <option value="">∑ Consolidado</option>
          {(portfolios || []).map((p) => <option key={p.id} value={p.id}>🏢 {p.etiqueta || p.name}</option>)}
        </select>
        <span className="text-gray-600">último folio por paquete y mes · ✅ vigente · ⚠ los libros cambiaron · — sin cierre (clic para exportarlo)</span>
      </div>
      <AvisoError texto={error} />
      {!datos && !error && <div className="text-[10px]">cargando…</div>}
      {datos && (
        <div className="overflow-x-auto border-2 border-black bg-white">
          <table className="w-full text-[10px] border-collapse">
            <thead className="bg-brutalNeutral">
              <tr>
                <th className="p-1 text-left border-r border-black">Paquete</th>
                {MESES_CORTOS.map((m) => <th key={m} className="p-1 text-center uppercase">{m}</th>)}
                <th className="p-1 text-center border-l border-black">Cerrados</th>
              </tr>
            </thead>
            <tbody>
              {paquetes.map((p) => {
                const r = resumenFila(datos, p.clave, anio, hoy);
                return (
                  <tr key={p.clave} className="border-t border-black/30">
                    <td className="p-1 font-bold whitespace-nowrap border-r border-black">{p.icono} {p.nombre}</td>
                    {MESES_CORTOS.map((m, k) => {
                      const mes = k + 1;
                      const c = celda(datos, p.clave, mes);
                      if (c) {
                        const e = ESTADO_CIERRE[c.estado] || ESTADO_CIERRE.SIN_HUELLA;
                        return (
                          <td key={m} className="p-0.5 text-center">
                            <button type="button" onClick={() => onAbrir?.(c.id)}
                              title={`${c.folio} · ${e.ayuda}${c.fijado ? ' · 📌 fijado' : ''}`}
                              className={`w-full border border-black px-0.5 font-bold ${e.clase} hover:bg-black hover:text-white`}>
                              {e.icono}{folioCorto(c.folio)}{c.fijado ? '📌' : ''}</button>
                          </td>
                        );
                      }
                      const abierto = mesAbierto(anio, mes, hoy);
                      return (
                        <td key={m} className="p-0.5 text-center">
                          {abierto ? <span className="text-gray-300">·</span> : (
                            <button type="button" onClick={() => onNueva?.({ pid: pid ? Number(pid) : null, anio, mes, paquete: p.clave })}
                              title={`Sin cierre: exportar ${p.nombre} de ${m} ${anio}`}
                              className="w-full border border-dashed border-black/40 text-gray-500 hover:bg-brutalAmber hover:text-black">—</button>
                          )}
                        </td>
                      );
                    })}
                    <td className="p-1 text-center border-l border-black whitespace-nowrap">
                      {r.cerrados}/{r.posibles}{r.cambiaron ? ` · ⚠${r.cambiaron}` : ''}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
