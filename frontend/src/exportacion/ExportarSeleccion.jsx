/* ============================================================
   ExportarSeleccion.jsx — Puerta del módulo 14 para otros módulos
   (spec 13.5 §4.3, puerta 1: Libro Diario). Abre "Nueva
   exportación" en modo transacciones con los ids ya marcados.
   Carga lo que el organizador le pasaría (paquetes, carpetas,
   empresas) para que el modal funcione igual fuera de ⇩.
   Se importa en diferido: Contabilidad no carga este código
   hasta que alguien pulsa 📥 EXPORTAR SELECCIÓN.
   ============================================================ */
import { useEffect, useState } from 'react';
import { api } from './api.js';
import { Modal } from './Dialogos.jsx';
import NuevaExportacion from './NuevaExportacion.jsx';

export default function ExportarSeleccion({ txIds, onCerrar, onGenerado }) {
  const [datos, setDatos] = useState(null);

  useEffect(() => {
    let vivo = true;
    Promise.all([
      api.get('/analytics/export/paquetes').catch(() => ({ predefinidos: [], guardados: [] })),
      api.get('/accounting-folders').catch(() => []),
      api.get('/portfolios').catch(() => []),
    ]).then(([paquetes, carpetas, portfolios]) => {
      if (vivo) setDatos({ paquetes, carpetas: Array.isArray(carpetas) ? carpetas : [], portfolios: Array.isArray(portfolios) ? portfolios : [] });
    });
    return () => { vivo = false; };
  }, []);

  if (!datos) {
    return (
      <Modal titulo="📥 NUEVA EXPORTACIÓN" onCerrar={onCerrar}>
        <div className="p-4 text-center font-bold">⏳ Preparando la exportación…</div>
      </Modal>
    );
  }
  return (
    <NuevaExportacion paquetes={datos.paquetes} portfolios={datos.portfolios} carpetas={datos.carpetas}
      inicial={{ modo: 'transacciones', txIds }} onCerrar={onCerrar} onGenerado={onGenerado} />
  );
}
