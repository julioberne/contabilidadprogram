/* ============================================================
   DiarioModule.jsx — Adapter del Libro Diario (Módulo 02)
   Monta LibroDiario de v1 VERBATIM (import transitorio) con
   estado de useLibroDiario + datos del EmpresaProvider.
   onEvidenceClick lo inyecta el shell (abre EvidenceModal).

   16-oct-2026: las filas vienen de /api/diario/movimientos
   (búsqueda, filtros, orden y grupos en el servidor). Los
   filtros viven en la URL: F5 o compartir el enlace conserva
   la vista. Cuando el resto del módulo muta datos (cajaViva
   cambia) la tabla se recarga sola.
   ============================================================ */
import React from 'react';
import LibroDiario from './LibroDiario.jsx';
import DiarioFiltrosBar from './DiarioFiltrosBar.jsx';
import DiarioGrupos from './DiarioGrupos.jsx';
import { useEmpresa } from '../../engine/EmpresaProvider.jsx';
import { useLibroDiario } from './useLibroDiario.js';
import { useDiarioFiltrado, MAX_TODO } from './useDiarioFiltrado.js';
import { CLAVES_URL, aCsv, aParametros, codigoPuc, desdeParametros, filtrosActivos } from './diarioFiltros.js';
import { API } from '../../../config';
import { authHeaders } from '../../../shell/authHeaders.js';
import { api } from '../../../exportacion/api.js';
import { esperarOperacion } from '../../../shared/operaciones.js';

function escribirUrl(filtros, orden, agrupar) {
  const p = new URLSearchParams(window.location.search);
  CLAVES_URL.forEach((k) => p.delete(k));
  aParametros(filtros, { orden, agrupar }).forEach((v, k) => p.set(k, v));
  const qs = p.toString();
  window.history.replaceState(window.history.state, '', window.location.pathname + (qs ? `?${qs}` : ''));
}

/** Hasta aquí el navegador arma el CSV al instante; más, va a la cola (H5.3). */
const CSV_DIRECTO = 2000;

/** Pide el CSV grande a la cola y espera el archivo → {id, nombre_archivo, n, folio, orden_usado} o
 *  null si la cola no está activa (409) o el usuario no puede (403): entonces sigue el CSV del navegador. */
async function csvEnCola(portfolio, filtros, orden) {
  const p = aParametros(filtros, { orden });
  p.delete('rango');
  if (portfolio) p.set('portfolio', portfolio);
  if (!p.get('orden')) p.set('orden', orden);
  const r = await fetch(`${API}/diario/csv?${p}`, { method: 'POST', headers: { ...authHeaders() } });
  if (r.status === 409 || r.status === 403) return null;
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.detail || `Error ${r.status} al pedir el CSV`);
  return esperarOperacion(d.operacion);
}

function descargar(texto, nombre) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([texto], { type: 'text/csv;charset=utf-8' }));
  a.download = nombre; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

/** Abre el Libro Mayor de Contadores en esa cuenta y empresa. */
function irAlMayor(tx) {
  const cuenta = codigoPuc(tx.category);
  if (!cuenta) return;
  const p = new URLSearchParams({ tab: 'reportes', rep: 'mayor', cuenta });
  if (tx.portfolio_name) p.set('empresa', tx.portfolio_name);
  window.history.pushState({ view: 'contadores' }, '', `/contadores?${p}`);
  window.dispatchEvent(new PopStateEvent('popstate'));
}

export default function DiarioModule({ onEvidenceClick }) {
  const empresa = useEmpresa();

  const inicial = React.useMemo(() => desdeParametros(window.location.search), []);
  const [filtros, setFiltros] = React.useState(inicial.filtros);
  const [orden, setOrden] = React.useState(inicial.orden);
  const [agrupar, setAgrupar] = React.useState(inicial.agrupar);
  React.useEffect(() => { escribirUrl(filtros, orden, agrupar); }, [filtros, orden, agrupar]);

  const senal = React.useMemo(() => ({}), [empresa.cajaViva, empresa.totalTxCount]); // eslint-disable-line react-hooks/exhaustive-deps
  const fil = useDiarioFiltrado({ portfolio: empresa.activePortfolio, filtros, orden, agrupar, senal });
  const diario = useLibroDiario({ onActualizada: fil.parchar });
  const activos = filtrosActivos(filtros);

  const [exportando, setExportando] = React.useState(false);
  const exportarCsv = async () => {
    setExportando(true);
    try {
      // H5.3: más de CSV_DIRECTO filas → lo arma el worker (sin el tope de
      // MAX_TODO) y queda en el organizador. Si la cola no está activa (409) o
      // el usuario no es contador (403), se sigue con el CSV del navegador.
      if (fil.total > CSV_DIRECTO) {
        const archivo = await csvEnCola(empresa.activePortfolio, filtros, orden);
        if (archivo) {
          await api.descargar(archivo.id, archivo.nombre_archivo);
          alert(`📥 CSV de ${archivo.n} movimientos listo y guardado en el organizador (${archivo.folio})`
            + (archivo.orden_usado !== orden ? '. Va ordenado por fecha (el orden elegido no aplica a exportaciones grandes).' : '.'));
          return;
        }
      }
      const filas = fil.rows.length >= fil.total ? fil.rows : await fil.traerTodo();
      const hoy = new Date().toISOString().slice(0, 10);
      descargar(aCsv(filas), `libro-diario-${(empresa.activePortfolio || 'empresa').replace(/\s+/g, '-')}-${hoy}.csv`);
      if (fil.total > MAX_TODO) alert(`⚠ Se exportaron las primeras ${MAX_TODO} de ${fil.total}. Acota los filtros para el resto.`);
    } catch (e) { alert(`❌ ${e.message}`); }
    finally { setExportando(false); }
  };

  return (
    <LibroDiario
      transactions={fil.rows}
      totalTxCount={fil.total}
      loadingMore={fil.cargandoMas}
      loadMoreTransactions={fil.cargarMas}
      expandedTxId={diario.expandedTxId} setExpandedTxId={diario.setExpandedTxId}
      editingCell={diario.editingCell} setEditingCell={diario.setEditingCell}
      editValue={diario.editValue} setEditValue={diario.setEditValue}
      saveInlineEdit={diario.saveInlineEdit}
      toggleRecurrence={diario.toggleRecurrence}
      accounts={empresa.accounts}
      coaFlatAccounts={empresa.coaFlatAccounts}
      onEvidenceClick={onEvidenceClick}
      onEliminada={fil.quitar}
      onLoteHecho={fil.recargar}
      traerTodo={fil.traerTodo}
      totalesFiltro={activos ? fil.totales : null}
      filtrando={activos}
      error={fil.error}
      cargando={fil.cargando}
      irAlMayor={irAlMayor}
      renderBarra={({ onMarcarTodo }) => (
        <>
          <DiarioFiltrosBar filtros={filtros} setFiltros={setFiltros} orden={orden} setOrden={setOrden}
            agrupar={agrupar} setAgrupar={setAgrupar} activePortfolio={empresa.activePortfolio}
            total={fil.total} cargando={fil.cargando} onExportarCsv={exportarCsv}
            onMarcarTodo={onMarcarTodo} exportando={exportando} aviso={fil.aviso} />
          <DiarioGrupos agrupar={agrupar} grupos={fil.grupos} filtros={filtros} setFiltros={setFiltros}
            onCerrar={() => setAgrupar('')} />
        </>
      )}
    />
  );
}
