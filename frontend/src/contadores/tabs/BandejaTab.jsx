/* ============================================================
   BandejaTab.jsx — Bandeja de asientos del contador.
   Un ítem por asiento (grupo) con sus líneas y la transacción de
   origen. Filtros por estado/fechas/texto, edición inline de
   borradores, contabilizar / rechazar / anular, y acciones
   masivas por casillas (patrón BotDraftsPanel).
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { api } from '../useContadoresApi.js';
import { fmt, fmtFecha } from '../fmt.js';
import EstadoBadge from '../components/EstadoBadge.jsx';
import PeriodoPicker from '../components/PeriodoPicker.jsx';
import LineasEditor, { lineasValidas, lineasPayload } from '../components/LineasEditor.jsx';
import MotivoModal from '../components/MotivoModal.jsx';

const ESTADOS = ['BORRADOR', 'CONTABILIZADO', 'RECHAZADO', 'ANULADO', 'TODOS'];

export default function BandejaTab({ portfolioId, cuentas, estadoInicial = 'BORRADOR', onCambio }) {
  const [estado, setEstado] = useState(estadoInicial);
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const [q, setQ] = useState('');
  const [sinPf, setSinPf] = useState(false);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sel, setSel] = useState(new Set());
  const [abierto, setAbierto] = useState(null);      // entry_group_id expandido
  const [editando, setEditando] = useState(null);    // { id, lineas, fecha, descripcion }
  const [busy, setBusy] = useState(null);
  const [modal, setModal] = useState(null);          // { tipo: 'rechazar'|'anular'|'lote-rechazar', id }
  const [resultados, setResultados] = useState({});
  const LIMIT = 50;

  const cargar = useCallback(async (off = 0) => {
    setLoading(true); setError('');
    try {
      const p = new URLSearchParams({ estado, limit: LIMIT, offset: off });
      if (portfolioId != null) p.set('portfolio_id', portfolioId);
      if (sinPf) p.set('sin_portafolio', 'true');
      if (desde) p.set('desde', desde);
      if (hasta) p.set('hasta', hasta);
      if (q.trim()) p.set('q', q.trim());
      const d = await api.get(`/contadores/bandeja?${p.toString()}`);
      setItems(off ? (prev) => [...prev, ...(d.items || [])] : d.items || []);
      setTotal(d.total || 0);
      setOffset(off);
    } catch (e) { setError(e.message); }
    setSel(new Set());
    setLoading(false);
  }, [estado, portfolioId, sinPf, desde, hasta, q]);

  useEffect(() => { cargar(0); }, [cargar]);

  const refrescar = async () => { await cargar(0); onCambio?.(); };

  const accion = async (id, verbo, body) => {
    setBusy(id);
    try {
      await api.post(`/contadores/asientos/${id}/${verbo}`, body);
      setResultados((r) => ({ ...r, [id]: `✔ ${verbo}` }));
      setModal(null);
      await refrescar();
    } catch (e) {
      setResultados((r) => ({ ...r, [id]: `✖ ${e.message}` }));
    } finally { setBusy(null); }
  };

  const lote = async (accionLote, motivo) => {
    const ids = [...sel];
    if (!ids.length) return;
    if (accionLote === 'contabilizar' && !window.confirm(`¿CONTABILIZAR ${ids.length} asiento(s)? Entran a los libros.`)) return;
    setBusy('lote');
    try {
      const d = await api.post('/contadores/asientos/lote', { ids, accion: accionLote, motivo });
      setResultados((r) => ({ ...r, ...Object.fromEntries(Object.entries(d.resultados).map(([k, v]) => [k, v === 'ok' ? `✔ ${accionLote}` : `✖ ${v}`])) }));
      setModal(null);
      await refrescar();
    } catch (e) { setError(e.message); }
    finally { setBusy(null); }
  };

  const empezarEdicion = (it) => setEditando({
    id: it.entry_group_id, fecha: fmtFecha(it.fecha), descripcion: it.descripcion || '',
    lineas: it.lineas.map((l) => ({ cuenta_codigo: l.cuenta_codigo, cuenta_nombre: l.cuenta_nombre || '',
                                    debito: l.debito || '', credito: l.credito || '' })),
  });
  const guardarEdicion = async () => {
    if (!editando || !lineasValidas(editando.lineas)) return;
    setBusy(editando.id);
    try {
      await api.put(`/contadores/asientos/${editando.id}/lineas`, {
        lineas: lineasPayload(editando.lineas), fecha: editando.fecha, descripcion: editando.descripcion,
      });
      setResultados((r) => ({ ...r, [editando.id]: '✎ Guardado' }));
      setEditando(null);
      await refrescar();
    } catch (e) { setResultados((r) => ({ ...r, [editando.id]: `✖ ${e.message}` })); }
    finally { setBusy(null); }
  };

  const seleccionables = items.filter((i) => i.estado === 'BORRADOR');
  const toggleSel = (id) => setSel((p) => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const toggleTodos = () => setSel((p) => p.size === seleccionables.length ? new Set() : new Set(seleccionables.map((i) => i.entry_group_id)));

  const btn = 'border border-black px-1.5 py-0.5 text-[10px] font-bold hover:bg-black hover:text-white disabled:opacity-40';
  const inp = 'border border-black px-1 py-0.5 text-[10px] font-mono bg-white';

  return (
    <div className="space-y-2">
      {/* Filtros */}
      <div className="bg-white border-2 border-black p-2 shadow-brutal space-y-1">
        <div className="flex flex-wrap items-center gap-1">
          {ESTADOS.map((e) => (
            <button key={e} className={`${btn} ${estado === e ? 'bg-black text-white' : ''}`} onClick={() => setEstado(e)}>{e}</button>
          ))}
          <span className="ml-2 text-[10px]">{total} asiento(s)</span>
          <label className="ml-auto text-[10px] flex items-center gap-1">
            <input type="checkbox" checked={sinPf} onChange={(e) => setSinPf(e.target.checked)} /> sin portafolio
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PeriodoPicker desde={desde} hasta={hasta} onChange={(a, b) => { setDesde(a || ''); setHasta(b || ''); }} />
          <input className={`${inp} w-48`} placeholder="buscar ref / descripción" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className={btn} onClick={() => cargar(0)}>↻</button>
        </div>
        {seleccionables.length > 0 && (
          <div className="flex flex-wrap items-center gap-1 border-t border-black pt-1">
            <label className="text-[10px] flex items-center gap-1">
              <input type="checkbox" checked={sel.size > 0 && sel.size === seleccionables.length} onChange={toggleTodos} />
              seleccionar borradores ({sel.size})
            </label>
            <button className={`${btn} bg-brutalGreen`} disabled={!sel.size || busy === 'lote'} onClick={() => lote('contabilizar')}>✔ CONTABILIZAR SELECCIÓN</button>
            <button className={btn} disabled={!sel.size || busy === 'lote'} onClick={() => setModal({ tipo: 'lote-rechazar' })}>✕ RECHAZAR SELECCIÓN</button>
          </div>
        )}
      </div>

      {error && <div className="bg-brutalCrimson text-white border-2 border-black p-1 text-[10px]">{error}</div>}
      {loading && !items.length && <div className="text-[10px]">▓ Cargando…</div>}
      {!loading && !items.length && <div className="text-[10px] bg-white border-2 border-black p-2">Sin asientos con estos filtros.</div>}

      {/* Lista */}
      {items.map((it) => {
        const id = it.entry_group_id;
        const exp = abierto === id;
        const edit = editando?.id === id;
        return (
          <div key={id} className={`bg-white border-2 border-black shadow-brutal ${it.estado === 'BORRADOR' ? '' : 'opacity-95'}`}>
            <div className="flex flex-wrap items-center gap-2 p-1.5 cursor-pointer" onClick={() => setAbierto(exp ? null : id)}>
              {it.estado === 'BORRADOR' && (
                <input type="checkbox" checked={sel.has(id)} onClick={(e) => e.stopPropagation()} onChange={() => toggleSel(id)} />
              )}
              <EstadoBadge estado={it.estado} />
              <span className="text-[10px] font-bold">{fmtFecha(it.fecha)}</span>
              <span className="text-[10px]">{it.referencia || id}</span>
              <span className="text-[10px] text-gray-700 truncate max-w-md">{it.descripcion}</span>
              <span className="text-[10px] ml-auto font-bold">{fmt(it.total_debito)}</span>
              {!it.cuadra && <span className="text-[9px] text-brutalCrimson font-bold">DESCUADRE</span>}
              <span className="text-[9px] border border-black px-1">{it.portfolio_name || 'sin portafolio'}</span>
              <span className="text-[10px]">{exp ? '▲' : '▼'}</span>
            </div>
            {resultados[id] && <div className="px-2 pb-1 text-[10px] font-bold">{resultados[id]}</div>}
            {exp && (
              <div className="border-t-2 border-black p-2 space-y-2">
                {it.tx && (
                  <div className="text-[10px] border border-dashed border-black p-1 bg-brutalNeutral">
                    <b>TX #{it.tx_id}</b> · {it.tx.type} · {fmt(it.tx.amount)} (neto {fmt(it.tx.net_value)}) · {it.tx.category || '—'}
                    {' '}· {it.tx.tercero || 'sin tercero'} · {it.tx.cuenta || 'sin cuenta'} · {fmtFecha(it.tx.fecha)}
                    <div className="truncate">{it.tx.concept}</div>
                  </div>
                )}
                {edit ? (
                  <div className="space-y-1">
                    <div className="flex gap-2 items-center text-[10px]">
                      <label>Fecha <input type="date" className={inp} value={editando.fecha} onChange={(e) => setEditando({ ...editando, fecha: e.target.value })} /></label>
                      <input className={`${inp} flex-1`} value={editando.descripcion} placeholder="descripción"
                             onChange={(e) => setEditando({ ...editando, descripcion: e.target.value })} />
                    </div>
                    <LineasEditor lineas={editando.lineas} cuentas={cuentas} listId={`coa-${id}`}
                                  onChange={(l) => setEditando({ ...editando, lineas: l })} />
                    <div className="flex gap-1">
                      <button className={`${btn} bg-black text-white`} disabled={!lineasValidas(editando.lineas) || busy === id} onClick={guardarEdicion}>GUARDAR</button>
                      <button className={btn} onClick={() => setEditando(null)}>CANCELAR</button>
                    </div>
                  </div>
                ) : (
                  <table className="w-full text-[10px] font-mono">
                    <thead><tr className="bg-black text-white"><th className="px-1 text-left">#</th><th className="px-1 text-left">CUENTA</th><th className="px-1 text-left">NOMBRE</th><th className="px-1 text-right">DÉBITO</th><th className="px-1 text-right">CRÉDITO</th></tr></thead>
                    <tbody>
                      {it.lineas.map((l) => (
                        <tr key={l.id} className="border-b border-black">
                          <td className="px-1">{l.linea}</td>
                          <td className="px-1 font-bold">{l.cuenta_codigo}</td>
                          <td className="px-1">{l.cuenta_nombre} <span className="text-gray-500">{l.cuenta_tipo}</span></td>
                          <td className="px-1 text-right">{Number(l.debito) ? fmt(l.debito) : ''}</td>
                          <td className="px-1 text-right">{Number(l.credito) ? fmt(l.credito) : ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                <div className="text-[9px] text-gray-600">
                  creado por {it.created_by || '—'} · {it.posted_by ? `contabilizado por ${it.posted_by} (${fmtFecha(it.posted_at)})` : ''}
                  {it.revisado_por ? ` · revisado por ${it.revisado_por}` : ''}{it.motivo ? ` · motivo: ${it.motivo}` : ''}
                  {it.reversa_de ? ` · reversa de ${it.reversa_de}` : ''}{it.anulado_por ? ` · anulado por ${it.anulado_por}` : ''}
                </div>
                {!edit && (
                  <div className="flex flex-wrap gap-1">
                    {it.estado === 'BORRADOR' && <>
                      <button className={`${btn} bg-brutalGreen`} disabled={busy === id || !it.cuadra} onClick={() => accion(id, 'contabilizar')}>✔ CONTABILIZAR</button>
                      <button className={btn} disabled={busy === id} onClick={() => empezarEdicion(it)}>✎ EDITAR LÍNEAS</button>
                      <button className={btn} disabled={busy === id} onClick={() => setModal({ tipo: 'rechazar', id })}>✕ RECHAZAR</button>
                    </>}
                    {it.estado === 'CONTABILIZADO' && (
                      <button className={`${btn} text-brutalCrimson`} disabled={busy === id}
                              title="Genera el asiento espejo con fecha de hoy; el periodo original no cambia"
                              onClick={() => setModal({ tipo: 'anular', id })}>⟲ ANULAR (contra-asiento)</button>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {items.length < total && (
        <button className={`${btn} w-full bg-white`} disabled={loading} onClick={() => cargar(offset + LIMIT)}>
          CARGAR MÁS ({items.length}/{total})
        </button>
      )}

      {modal?.tipo === 'rechazar' && (
        <MotivoModal titulo={`Rechazar ${modal.id}`} confirmar="RECHAZAR" busy={busy === modal.id}
                     descripcion="El asiento nunca entrará a los libros. La transacción de origen no se toca."
                     onConfirm={(m) => accion(modal.id, 'rechazar', { motivo: m })} onClose={() => setModal(null)} />
      )}
      {modal?.tipo === 'anular' && (
        <MotivoModal titulo={`Anular ${modal.id}`} confirmar="ANULAR" busy={busy === modal.id}
                     descripcion="Se registra un contra-asiento (espejo) con fecha de hoy y el original queda ANULADO. El periodo original no cambia."
                     onConfirm={(m) => accion(modal.id, 'anular', { motivo: m })} onClose={() => setModal(null)} />
      )}
      {modal?.tipo === 'lote-rechazar' && (
        <MotivoModal titulo={`Rechazar ${sel.size} borrador(es)`} confirmar="RECHAZAR" busy={busy === 'lote'}
                     onConfirm={(m) => lote('rechazar', m)} onClose={() => setModal(null)} />
      )}
    </div>
  );
}
