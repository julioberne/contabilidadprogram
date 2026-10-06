/* ============================================================
   ExportacionApp.jsx — Módulo 14 "Exportación" (spec 13.5).

   La carpeta contable de la empresa: libros con folio, relaciones
   de transacciones y documentos subidos. Módulo propio del registry
   (ruta /exportacion, decisión de Andrés 06-oct-2026); antes era un
   desplegable al fondo de ∑ Análisis.

   Cabecera con el resumen ("12 archivos · 3,1 MB · ⚠ 2 cambiaron"),
   luego la franja de 📥 NUEVA EXPORTACIÓN (lo principal del módulo:
   botón + atajos de paquete + transacciones) y debajo el organizador.
   Ver y generar: owner/admin/contador — el registry oculta el módulo
   a otros roles y el backend responde 403.
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { api } from './api.js';
import { formatoBytes } from './organizador.js';
import Organizador from './Organizador.jsx';
import CompendiosPanel from './CompendiosPanel.jsx';
import { btnNegro } from './Dialogos.jsx';

export default function ExportacionApp({ user }) {
  const [resumen, setResumen] = useState(null);      // null = cargando
  const [error, setError] = useState('');
  const [sinPermiso, setSinPermiso] = useState(false);
  const [paquetes, setPaquetes] = useState(null);     // { predefinidos, guardados } para Nueva exportación
  const [pedido, setPedido] = useState(null);         // atajo de la franja → abre el modal en el organizador
  const [verCompendios, setVerCompendios] = useState(false);   // 🔗 links para clientes (13.6)

  const cargarResumen = useCallback(() => api.get('/accounting-files/resumen')
    .then((r) => { setResumen(r); setError(''); })
    .catch((e) => { if (e.status === 403) setSinPermiso(true); else setError(e.message); }), []);

  useEffect(() => { cargarResumen(); }, [cargarResumen]);
  useEffect(() => {
    api.get('/analytics/export/paquetes').then(setPaquetes).catch(() => setPaquetes({ predefinidos: [], guardados: [] }));
  }, []);

  return (
    <div className="min-h-screen bg-brutalBg text-black font-mono p-2 space-y-2 antialiased">
      {/* Cabecera */}
      <div className="bg-white border-2 border-black shadow-brutal p-2 flex flex-wrap items-center gap-2">
        <span className="font-bold text-[13px]">⇩ EXPORTACIÓN</span>
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
        {!resumen && !error && !sinPermiso && <span className="text-[10px] text-gray-600">cargando…</span>}
        {error && <span className="text-[10px] bg-brutalCrimson text-white px-1">{error}</span>}
        <span className="text-[10px] text-gray-600 hidden sm:inline">
          libros con folio · relaciones de TXs · documentos subidos
        </span>
        <span className="ml-auto text-[10px]">{user?.name}</span>
      </div>

      {!sinPermiso && (
        <div className="bg-white border-2 border-black shadow-brutal p-2 flex flex-wrap items-center gap-1">
          <button type="button" className={`${btnNegro} text-[12px] px-3 py-1`} disabled={!paquetes}
            onClick={() => setPedido({ modo: 'periodo' })}>📥 NUEVA EXPORTACIÓN</button>
          <span className="text-[10px] font-bold ml-1">Atajos:</span>
          {(paquetes?.predefinidos || []).map((p) => (
            <button key={p.clave} type="button" onClick={() => setPedido({ modo: 'periodo', paquete: p.clave })}
              className="border-2 border-black px-2 py-0.5 text-[10px] font-bold bg-white hover:bg-brutalAmber">
              {p.icono} {p.nombre}</button>
          ))}
          <button type="button" onClick={() => setPedido({ modo: 'transacciones' })}
            className="border-2 border-black px-2 py-0.5 text-[10px] font-bold bg-white hover:bg-brutalAmber"
            title="Buscar, filtrar y marcar transacciones del Libro Diario para exportar su relación">
            🧾 Transacciones (filtrar o elegir)</button>
          <button type="button" aria-expanded={verCompendios} onClick={() => setVerCompendios((v) => !v)}
            className={`border-2 border-black px-2 py-0.5 text-[10px] font-bold ml-auto ${verCompendios ? 'bg-black text-white' : 'bg-white hover:bg-brutalAmber'}`}
            title="Links temporales para clientes: estado, visitas, ampliar o revocar">
            🔗 Compendios</button>
        </div>
      )}
      {!sinPermiso && verCompendios && <CompendiosPanel />}

      {sinPermiso ? (
        <div role="alert" className="bg-white border-2 border-black shadow-brutal p-2 text-[11px]">
          <b>Sin permiso.</b> La exportación es para owner, admin o contador.
        </div>
      ) : (
        <div id="organizador-contable">
          <Organizador user={user} resumen={resumen} onCambio={cargarResumen} paquetes={paquetes}
            pedidoNueva={pedido} onPedidoAtendido={() => setPedido(null)} />
        </div>
      )}
    </div>
  );
}
