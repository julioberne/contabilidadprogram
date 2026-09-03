/* ============================================================
   BotDraftsPanel.jsx — Bandeja de borradores del Bot IA (Etapa C)
   Lista los transaction_drafts del usuario, permite editarlos con
   formulario determinista (sin LLM), confirmarlos o descartarlos
   por fila o MASIVAMENTE por casillas. Regla 6: nada toca la
   contabilidad sin confirmación humana explícita.
   Se monta en dos lugares: pestaña BORRADORES de Contabilidad y
   módulo Bot IA del registry (BotApp).
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { API } from '../config';
import { authHeaders } from '../shell/authHeaders';
import NumInput from '../shared/NumInput';
import { CATEGORIAS } from '../contabilidad-v2/modules/registro/TransactionForm.jsx';

const ESTADOS = ['BORRADOR', 'ERROR', 'CONFIRMADO', 'DESCARTADO', 'TODOS'];
const ESTADO_STYLE = {
  BORRADOR: 'bg-brutalAmber text-black', PROCESANDO: 'bg-gray-300 text-black',
  CONFIRMADO: 'bg-brutalGreen text-black', ERROR: 'bg-brutalCrimson text-white',
  DESCARTADO: 'bg-gray-200 text-gray-500',
};
const fmt = (v) => v == null ? '—'
  : `$${Number(v).toLocaleString('es-CO', Number.isInteger(Number(v))
      ? { maximumFractionDigits: 0 } : { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const hdrs = () => ({ 'Content-Type': 'application/json', ...authHeaders() });

export default function BotDraftsPanel() {
  const [drafts, setDrafts] = useState([]);
  const [filtro, setFiltro] = useState('BORRADOR');
  const [loading, setLoading] = useState(true);
  const [sel, setSel] = useState(new Set());
  const [editingId, setEditingId] = useState(null);
  const [edit, setEdit] = useState({});
  const [busy, setBusy] = useState(null);           // id | 'bulk' | null
  const [resultados, setResultados] = useState({}); // id → mensaje del driver
  const [cuentas, setCuentas] = useState([]);
  const [allTags, setAllTags] = useState([]);   // tag_definitions — mismas del registro
  const [linkInfo, setLinkInfo] = useState(null);

  const cargar = useCallback(async (estado = filtro) => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/bot/drafts?status=${estado}`, { headers: hdrs() });
      setDrafts(r.ok ? await r.json() : []);
    } catch { setDrafts([]); }
    setSel(new Set());
    setLoading(false);
  }, [filtro]);

  useEffect(() => { cargar(filtro); }, [filtro, cargar]);
  useEffect(() => {
    fetch(`${API}/accounts`).then(r => r.json()).then(a => setCuentas(a.map(x => x.name))).catch(() => {});
    fetch(`${API}/tags`).then(r => r.json()).then(t => setAllTags(Array.isArray(t) ? t : [])).catch(() => {});
  }, []);

  const editables = drafts.filter(d => d.status === 'BORRADOR' || d.status === 'ERROR');
  const toggleSel = (id) => setSel(prev => {
    const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n;
  });
  const toggleTodos = () => setSel(prev =>
    prev.size === editables.length ? new Set() : new Set(editables.map(d => d.id)));

  // ── Acciones por fila ──
  const accion = async (id, verbo) => {           // verbo: confirm | discard
    setBusy(id);
    try {
      const r = await fetch(`${API}/bot/drafts/${id}/${verbo}`, { method: 'POST', headers: hdrs() });
      const d = await r.json().catch(() => ({}));
      setResultados(prev => ({ ...prev, [id]: d.result || d.detail || `Error ${r.status}` }));
    } catch { setResultados(prev => ({ ...prev, [id]: 'Sin conexión con el servidor.' })); }
    setBusy(null);
    await cargar();
  };

  // ── Masivo por casillas — secuencial, resultado por fila ──
  const masivo = async (verbo) => {
    const ids = [...sel];
    if (!ids.length) return;
    const nombre = verbo === 'confirm' ? 'CONFIRMAR (crea transacciones reales)' : 'DESCARTAR';
    if (!window.confirm(`¿${nombre} ${ids.length} borrador(es)? #${ids.join(', #')}`)) return;
    setBusy('bulk');
    const res = {};
    for (const id of ids) {
      try {
        const r = await fetch(`${API}/bot/drafts/${id}/${verbo}`, { method: 'POST', headers: hdrs() });
        const d = await r.json().catch(() => ({}));
        res[id] = d.result || d.detail || `Error ${r.status}`;
      } catch { res[id] = 'Sin conexión.'; }
    }
    setResultados(prev => ({ ...prev, ...res }));
    setBusy(null);
    await cargar();
  };

  // ── Edición determinista ──
  const startEdit = (d) => {
    const p = d.payload || {};
    setEditingId(d.id);
    setEdit({
      type: p.type || 'GASTO', amount: p.amount ?? '', concept: p.concept || '',
      category: p.category || '', payment_method: p.payment_method || '',
      transaction_date: p.transaction_date || '',
      apply_iva: !!p.apply_iva, apply_gmf: !!p.apply_gmf,
      tags: Array.isArray(p.tags) ? p.tags : [],
      tp_name: p.third_party?.name || '', tp_num: p.third_party?.identification_number || '',
    });
  };
  const saveEdit = async (id) => {
    setBusy(id);
    const body = {
      type: edit.type, amount: edit.amount === '' ? null : Number(edit.amount),
      concept: edit.concept, category: edit.category, payment_method: edit.payment_method,
      transaction_date: edit.transaction_date, tags: edit.tags || [],
      apply_iva: edit.apply_iva, apply_gmf: edit.apply_gmf,
      third_party: { name: edit.tp_name, identification_number: edit.tp_num },
    };
    try {
      const r = await fetch(`${API}/bot/drafts/${id}`, { method: 'PUT', headers: hdrs(), body: JSON.stringify(body) });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) setResultados(prev => ({ ...prev, [id]: d.detail || `Error ${r.status}` }));
      else { setEditingId(null); setResultados(prev => ({ ...prev, [id]: '✎ Guardado.' })); }
    } catch { setResultados(prev => ({ ...prev, [id]: 'Sin conexión.' })); }
    setBusy(null);
    await cargar();
  };

  const pedirCodigo = async () => {
    try {
      const r = await fetch(`${API}/bot/link-code`, { method: 'POST', headers: hdrs() });
      setLinkInfo(r.ok ? await r.json() : { error: (await r.json().catch(() => ({}))).detail || 'Error' });
    } catch { setLinkInfo({ error: 'Sin conexión.' }); }
  };

  const inp = 'border border-black px-1 py-0.5 text-[10px] font-mono outline-none bg-white';

  return (
    <div className="bg-white border-2 border-black p-2 shadow-brutal space-y-2 font-mono">
      {/* ── Header: filtros + vinculación ── */}
      <div className="flex flex-wrap items-center gap-1 border-b-2 border-black pb-1.5">
        <h2 className="text-sm font-bold uppercase mr-2">🤖 Bandeja del Bot</h2>
        {ESTADOS.map(e => (
          <button key={e} type="button" onClick={() => setFiltro(e)}
            className={`px-2 py-0.5 text-[8px] font-bold uppercase border transition-all ${
              filtro === e ? 'bg-black text-white border-black' : 'border-gray-300 hover:border-black'}`}>
            {e}
          </button>
        ))}
        <span className="flex-1" />
        <button type="button" onClick={() => cargar()} className="px-2 py-0.5 text-[9px] border border-black hover:bg-black hover:text-white" title="Refrescar">⟳</button>
        <button type="button" onClick={pedirCodigo} className="px-2 py-0.5 text-[8px] font-bold uppercase border border-black bg-brutalBg hover:bg-black hover:text-white">🔗 Vincular Telegram</button>
      </div>
      {linkInfo && (
        <div className="border border-black bg-brutalBg p-1.5 text-[10px]">
          {linkInfo.error ? `⚠ ${linkInfo.error}` : (<>
            Escríbele al bot: <b className="bg-black text-brutalGreen px-1">/vincular {linkInfo.code}</b>
            {' '}(expira en {linkInfo.expira_en_minutos} min)
          </>)}
        </div>
      )}

      {/* ── Barra de acciones masivas ── */}
      {sel.size > 0 && (
        <div className="flex items-center gap-2 border-2 border-black bg-brutalAmber p-1.5">
          <span className="text-[10px] font-bold uppercase">{sel.size} seleccionado(s)</span>
          <button type="button" disabled={busy === 'bulk'} onClick={() => masivo('confirm')}
            className="px-2 py-0.5 text-[9px] font-bold uppercase border border-black bg-brutalGreen hover:bg-black hover:text-white disabled:opacity-50">
            ✔ Confirmar seleccionados
          </button>
          <button type="button" disabled={busy === 'bulk'} onClick={() => masivo('discard')}
            className="px-2 py-0.5 text-[9px] font-bold uppercase border border-black bg-white hover:bg-brutalCrimson hover:text-white disabled:opacity-50">
            🗑 Descartar
          </button>
          {busy === 'bulk' && <span className="text-[9px] uppercase animate-pulse">Procesando…</span>}
        </div>
      )}

      {/* ── Tabla ── */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[10px]">
          <thead>
            <tr className="bg-black text-white uppercase text-[8px]">
              <th className="p-1 text-center w-6">
                <input type="checkbox" title="Seleccionar todos los editables"
                  checked={editables.length > 0 && sel.size === editables.length}
                  onChange={toggleTodos} disabled={!editables.length} />
              </th>
              <th className="p-1 text-left">#</th>
              <th className="p-1 text-left">Origen</th>
              <th className="p-1 text-left">Mensaje original</th>
              <th className="p-1 text-left">Tipo</th>
              <th className="p-1 text-right">Monto</th>
              <th className="p-1 text-left">Concepto</th>
              <th className="p-1 text-left">Cuenta</th>
              <th className="p-1 text-left">Estado</th>
              <th className="p-1 text-center">Acc.</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan={10} className="p-3 text-center text-gray-400 uppercase">Cargando…</td></tr>
            ) : drafts.length === 0 ? (
              <tr><td colSpan={10} className="p-3 text-center text-gray-400 uppercase">
                Sin borradores en «{filtro}». Envíale un gasto al bot de Telegram y aparecerá aquí.
              </td></tr>
            ) : drafts.map(d => {
              const p = d.payload || {};
              const editable = d.status === 'BORRADOR' || d.status === 'ERROR';
              return (
                <FragmentoFila key={d.id} d={d} p={p} editable={editable}
                  sel={sel} toggleSel={toggleSel} busy={busy}
                  editingId={editingId} edit={edit} setEdit={setEdit}
                  startEdit={startEdit} saveEdit={saveEdit} setEditingId={setEditingId}
                  accion={accion} resultado={resultados[d.id]}
                  cuentas={cuentas} allTags={allTags} inp={inp} />
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-[8px] text-gray-400 uppercase">
        Regla 6: el LLM solo propone — nada toca la contabilidad sin tu confirmación. Confirmar crea la transacción y su asiento de partida doble.
      </p>
    </div>
  );
}

/* ── Fila (+ edición expandida) ─────────────────────────────── */
function FragmentoFila({ d, p, editable, sel, toggleSel, busy, editingId, edit, setEdit,
                         startEdit, saveEdit, setEditingId, accion, resultado, cuentas, allTags, inp }) {
  const upd = (k) => (e) => setEdit(prev => ({ ...prev, [k]: e.target.value }));
  const editando = editingId === d.id;
  return (
    <>
      <tr className={`hover:bg-brutalBg ${d.status === 'ERROR' ? 'bg-red-50' : ''}`}>
        <td className="p-1 text-center">
          <input type="checkbox" checked={sel.has(d.id)} onChange={() => toggleSel(d.id)} disabled={!editable} />
        </td>
        <td className="p-1 font-bold">#{d.id}</td>
        <td className="p-1 whitespace-nowrap" title={`Canal: ${d.channel} · ${d.created_at}`}>
          {d.channel === 'telegram' ? '✈' : d.channel === 'web' ? '🌐' : '💬'}{d.media_path ? ' 🎙' : ''}
          <span className="text-gray-400 ml-1">{String(d.created_at).slice(5, 16)}</span>
        </td>
        <td className="p-1 max-w-[220px] truncate" title={d.raw_text || ''}>{d.raw_text || '—'}</td>
        <td className="p-1">
          <span className={`px-1 text-[8px] font-bold ${p.type === 'INGRESO' ? 'text-brutalGreen' : p.type === 'GASTO' ? 'text-red-600' : 'text-blue-600'}`}>{p.type || '—'}</span>
        </td>
        <td className="p-1 text-right font-bold">{fmt(p.amount)}</td>
        <td className="p-1 max-w-[180px] truncate" title={p.concept}>{p.concept || '—'}</td>
        <td className="p-1 max-w-[120px] truncate" title={p.payment_method}>{p.payment_method || '—'}</td>
        <td className="p-1">
          <span className={`px-1 text-[8px] font-bold uppercase ${ESTADO_STYLE[d.status] || ''}`}
                title={d.error || (p.missing_fields?.length ? `Faltan: ${p.missing_fields.join(', ')}` : '')}>
            {d.status}{d.status === 'CONFIRMADO' && d.confirmed_transaction_id ? ` #${d.confirmed_transaction_id}` : ''}
          </span>
          {p.missing_fields?.length > 0 && d.status === 'BORRADOR' &&
            <span className="text-[8px] text-amber-600 ml-1" title={`Faltan: ${p.missing_fields.join(', ')}`}>⚠</span>}
        </td>
        <td className="p-1 text-center whitespace-nowrap">
          {editable && !editando && <>
            <button type="button" className="px-1 hover:text-blue-600" title="Editar" onClick={() => startEdit(d)}>✎</button>
            <button type="button" className="px-1 hover:text-brutalGreen disabled:opacity-40" title="Confirmar (crea la transacción)"
              disabled={busy === d.id} onClick={() => accion(d.id, 'confirm')}>✔</button>
            <button type="button" className="px-1 hover:text-red-600 disabled:opacity-40" title="Descartar"
              disabled={busy === d.id} onClick={() => accion(d.id, 'discard')}>🗑</button>
          </>}
          {editando && <>
            <button type="button" className="px-1 hover:text-brutalGreen" title="Guardar" disabled={busy === d.id} onClick={() => saveEdit(d.id)}>💾</button>
            <button type="button" className="px-1 hover:text-red-600" title="Cancelar" onClick={() => setEditingId(null)}>✕</button>
          </>}
        </td>
      </tr>
      {(resultado || d.error) && (
        <tr><td colSpan={10} className={`px-2 py-0.5 text-[9px] ${d.status === 'ERROR' ? 'text-red-700 bg-red-50' : 'text-gray-600'}`}>
          {resultado || `⚠ ${d.error}`}
        </td></tr>
      )}
      {editando && (
        <tr className="bg-yellow-50 border-y-2 border-black">
          <td colSpan={10} className="p-2">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-1.5">
              <label className="text-[8px] font-bold uppercase">Tipo
                <select className={`${inp} w-full`} value={edit.type} onChange={upd('type')}>
                  {['INGRESO', 'GASTO', 'TRANSFERENCIA'].map(t => <option key={t}>{t}</option>)}
                </select>
              </label>
              <label className="text-[8px] font-bold uppercase">Monto
                <NumInput className={`${inp} w-full text-right`} value={edit.amount} onChange={upd('amount')} />
              </label>
              <label className="text-[8px] font-bold uppercase col-span-2">Concepto
                <input className={`${inp} w-full`} value={edit.concept} onChange={upd('concept')} />
              </label>
              <label className="text-[8px] font-bold uppercase">Cuenta / método
                <select className={`${inp} w-full`} value={edit.payment_method} onChange={upd('payment_method')}>
                  {!cuentas.includes(edit.payment_method) && <option value={edit.payment_method}>{edit.payment_method || '—'}</option>}
                  {cuentas.map(c => <option key={c}>{c}</option>)}
                </select>
              </label>
              <label className="text-[8px] font-bold uppercase">Categoría
                <select className={`${inp} w-full`} value={edit.category} onChange={upd('category')}>
                  {!(CATEGORIAS[edit.type] || []).includes(edit.category) && <option value={edit.category}>{edit.category || '—'}</option>}
                  {(CATEGORIAS[edit.type] || []).map(c => <option key={c}>{c}</option>)}
                </select>
              </label>
              <label className="text-[8px] font-bold uppercase">Fecha
                <input type="date" className={`${inp} w-full`} value={edit.transaction_date} onChange={upd('transaction_date')} />
              </label>
              <label className="text-[8px] font-bold uppercase">Etiquetas
                <div className={`${inp} w-full flex flex-wrap gap-1 min-h-[22px] cursor-default`}>
                  {allTags.length === 0 && <span className="text-gray-400">sin etiquetas creadas</span>}
                  {allTags.map(t => {
                    const on = (edit.tags || []).includes(t.name);
                    return (
                      <span key={t.id || t.name}
                        onClick={() => setEdit(prev => ({ ...prev,
                          tags: on ? prev.tags.filter(x => x !== t.name) : [...(prev.tags || []), t.name] }))}
                        className={`px-1 border cursor-pointer text-[9px] ${on ? 'border-black bg-brutalGreen font-bold' : 'border-gray-300 bg-white hover:bg-brutalNeutral'}`}>
                        {on ? '☑' : '☐'} {t.name}
                      </span>
                    );
                  })}
                </div>
              </label>
              <label className="text-[8px] font-bold uppercase">Tercero
                <input className={`${inp} w-full`} value={edit.tp_name} onChange={upd('tp_name')} placeholder="Nombre" />
              </label>
              <label className="text-[8px] font-bold uppercase">NIT/CC
                <input className={`${inp} w-full`} value={edit.tp_num} onChange={upd('tp_num')} placeholder="999999999" />
              </label>
              <div className="flex items-end gap-2 text-[9px] font-bold uppercase">
                <label><input type="checkbox" checked={edit.apply_iva} onChange={e => setEdit(prev => ({ ...prev, apply_iva: e.target.checked }))} /> IVA</label>
                <label><input type="checkbox" checked={edit.apply_gmf} onChange={e => setEdit(prev => ({ ...prev, apply_gmf: e.target.checked }))} /> GMF</label>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
