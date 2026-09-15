/* ============================================================
   PlanCuentasTab.jsx — Plan de cuentas (chart_of_accounts) por
   portafolio: árbol por parent_id, CRUD inline, badge de
   movimientos/reglas, "Copiar PUC desde…".
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { api } from '../useContadoresApi.js';

const TIPOS = ['ACTIVO', 'PASIVO', 'PATRIMONIO', 'INGRESO', 'GASTO'];
const BTN = 'border border-black px-1.5 py-0.5 text-[10px] font-bold hover:bg-black hover:text-white disabled:opacity-40';
const INP = 'border border-black px-1 py-0.5 text-[10px] font-mono bg-white';

function arbol(filas) {
  const porId = Object.fromEntries(filas.map((f) => [f.id, { ...f, children: [] }]));
  const raiz = [];
  filas.forEach((f) => {
    const n = porId[f.id];
    if (f.parent_id && porId[f.parent_id]) porId[f.parent_id].children.push(n); else raiz.push(n);
  });
  return raiz;
}

/* Fila del árbol: componente de módulo (no se recrea en cada render, así
   los inputs de edición conservan el foco). */
function FilaCuenta({ n, nivel, ctx }) {
  const { edit, setEdit, busy, colapsados, toggle, guardar, eliminar, setNuevo } = ctx;
  const editando = edit?.id === n.id;
  const bloqueada = !!n.hijos || !!n.movimientos || !!n.reglas;
  return (
    <>
      <tr className={`border-b border-black ${n.is_group ? 'bg-brutalNeutral font-bold' : ''}`}>
        <td className="px-1 py-0.5 whitespace-nowrap" style={{ paddingLeft: 4 + nivel * 14 }}>
          {n.children.length
            ? <button className="mr-1" onClick={() => toggle(n.id)}>{colapsados.has(n.id) ? '▸' : '▾'}</button>
            : <span className="mr-1 inline-block w-2" />}
          {n.code}
        </td>
        <td className="px-1 py-0.5">
          {editando
            ? <input className={`${INP} w-full`} value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} />
            : n.name}
        </td>
        <td className="px-1 py-0.5">
          {editando
            ? <select className={INP} value={edit.account_type} onChange={(e) => setEdit({ ...edit, account_type: e.target.value })}>{TIPOS.map((t) => <option key={t}>{t}</option>)}</select>
            : <span className="text-[9px] border border-black px-1">{n.account_type}</span>}
        </td>
        <td className="px-1 py-0.5 text-[9px] text-gray-700 whitespace-nowrap">
          {n.is_group ? `grupo · ${n.hijos} sub` : `${n.movimientos} mov.`}{n.reglas ? ` · ${n.reglas} regla(s)` : ''}
        </td>
        <td className="px-1 py-0.5 whitespace-nowrap">
          {editando ? <>
            <button className={`${BTN} bg-black text-white`} disabled={busy} onClick={guardar}>OK</button>{' '}
            <button className={BTN} onClick={() => setEdit(null)}>✕</button>
          </> : <>
            <button className={BTN} onClick={() => setEdit({ id: n.id, name: n.name, account_type: n.account_type, description: n.description || '' })}>✎</button>{' '}
            {n.is_group && <button className={BTN} title="Nueva subcuenta" onClick={() => setNuevo({ code: n.code, name: '', account_type: n.account_type, is_group: false, parent_code: n.code })}>+</button>}{' '}
            <button className={`${BTN} text-brutalCrimson`} disabled={bloqueada}
                    title={bloqueada ? 'No se puede borrar: tiene subcuentas, movimientos o reglas' : 'Eliminar'}
                    onClick={() => eliminar(n)}>🗑</button>
          </>}
        </td>
      </tr>
      {!colapsados.has(n.id) && n.children.map((h) => <FilaCuenta key={h.id} n={h} nivel={nivel + 1} ctx={ctx} />)}
    </>
  );
}

export default function PlanCuentasTab({ portfolioId, portfolios, esAdmin, onCambio }) {
  const pid = portfolioId ?? (portfolios?.[0]?.id ?? null);
  const nombre = (portfolios || []).find((p) => p.id === pid)?.name || '';
  const [filas, setFilas] = useState([]);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [nuevo, setNuevo] = useState(null);
  const [edit, setEdit] = useState(null);
  const [colapsados, setColapsados] = useState(new Set());
  const [origen, setOrigen] = useState('');

  const cargar = useCallback(async () => {
    if (pid == null) return;
    setError('');
    try { setFilas(await api.get(`/contadores/coa?portfolio_id=${pid}`)); }
    catch (e) { setError(e.message); }
  }, [pid]);
  useEffect(() => { cargar(); }, [cargar]);

  const ejecutar = async (fn, ok) => {
    setBusy(true); setError(''); setMsg('');
    try { await fn(); setMsg(ok); await cargar(); onCambio?.(); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const crear = () => ejecutar(async () => {
    await api.post('/contadores/coa', { ...nuevo, portfolio_id: pid, parent_code: nuevo.parent_code || null });
    setNuevo(null);
  }, `✔ Cuenta ${nuevo.code} creada`);
  const guardar = () => ejecutar(async () => {
    await api.put(`/contadores/coa/${edit.id}`, { name: edit.name, account_type: edit.account_type, description: edit.description });
    setEdit(null);
  }, '✔ Cuenta actualizada');
  const eliminar = (c) => {
    if (!window.confirm(`¿Eliminar la cuenta ${c.code} ${c.name}?`)) return;
    ejecutar(() => api.del(`/contadores/coa/${c.id}`), `✔ Cuenta ${c.code} eliminada`);
  };
  const copiar = () => ejecutar(async () => {
    const d = await api.post('/contadores/coa/copiar', { from_portfolio_id: Number(origen), to_portfolio_id: pid });
    setMsg(`✔ ${d.creadas} cuenta(s) copiadas de ${d.origen}`);
  }, '');
  const toggle = (id) => setColapsados((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  if (pid == null) return <div className="text-[10px]">Elige un portafolio.</div>;
  const raices = arbol(filas);
  const ctx = { edit, setEdit, busy, colapsados, toggle, guardar, eliminar, setNuevo };

  return (
    <div className="space-y-2">
      <div className="bg-white border-2 border-black p-2 shadow-brutal flex flex-wrap items-center gap-2 text-[10px]">
        <b>{nombre}</b> · {filas.length} cuenta(s)
        <button className={BTN} onClick={() => setNuevo({ code: '', name: '', account_type: 'ACTIVO', is_group: false, parent_code: '' })}>+ CUENTA</button>
        {esAdmin && (
          <span className="ml-auto flex items-center gap-1">
            Copiar PUC desde
            <select className={INP} value={origen} onChange={(e) => setOrigen(e.target.value)}>
              <option value="">—</option>
              {(portfolios || []).filter((p) => p.id !== pid).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <button className={BTN} disabled={!origen || busy} onClick={copiar}>COPIAR</button>
          </span>
        )}
        {msg && <span className="font-bold">{msg}</span>}
      </div>
      {error && <div className="bg-brutalCrimson text-white border-2 border-black p-1 text-[10px]">{error}</div>}
      {nuevo && (
        <div className="bg-white border-2 border-black p-2 shadow-brutal flex flex-wrap gap-1 items-center text-[10px]">
          <input className={`${INP} w-24`} placeholder="código" value={nuevo.code} onChange={(e) => setNuevo({ ...nuevo, code: e.target.value.trim() })} />
          <input className={`${INP} w-56`} placeholder="nombre" value={nuevo.name} onChange={(e) => setNuevo({ ...nuevo, name: e.target.value })} />
          <select className={INP} value={nuevo.account_type} onChange={(e) => setNuevo({ ...nuevo, account_type: e.target.value })}>{TIPOS.map((t) => <option key={t}>{t}</option>)}</select>
          <input className={`${INP} w-24`} placeholder="padre (código)" value={nuevo.parent_code} onChange={(e) => setNuevo({ ...nuevo, parent_code: e.target.value.trim() })} />
          <label className="flex items-center gap-1"><input type="checkbox" checked={nuevo.is_group} onChange={(e) => setNuevo({ ...nuevo, is_group: e.target.checked })} /> grupo</label>
          <button className={`${BTN} bg-brutalGreen`} disabled={busy || !nuevo.code || !nuevo.name} onClick={crear}>CREAR</button>
          <button className={BTN} onClick={() => setNuevo(null)}>CANCELAR</button>
        </div>
      )}
      <div className="bg-white border-2 border-black shadow-brutal overflow-x-auto">
        <table className="w-full text-[10px] font-mono">
          <thead><tr className="bg-black text-white"><th className="px-1 text-left">CÓDIGO</th><th className="px-1 text-left">NOMBRE</th><th className="px-1 text-left">TIPO</th><th className="px-1 text-left">USO</th><th className="px-1"></th></tr></thead>
          <tbody>
            {raices.map((n) => <FilaCuenta key={n.id} n={n} nivel={0} ctx={ctx} />)}
            {!filas.length && <tr><td colSpan={5} className="p-2">Sin plan de cuentas. {esAdmin ? 'Cópialo desde otro portafolio o crea cuentas.' : 'Pide a un administrador que lo copie.'}</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
