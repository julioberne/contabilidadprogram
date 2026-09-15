/* ============================================================
   ReglasTab.jsx — Posting rules: categoría + tipo → cuentas.
   Globales + del portafolio. Form con categorías del registro
   (shared/categorias.js) o texto libre, cuentas con datalist,
   __BANK__ como placeholder y previsualización del asiento.
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { api } from '../useContadoresApi.js';
import { CATEGORIAS } from '../../shared/categorias.js';
import CuentaSelect from '../components/CuentaSelect.jsx';
import { fmt } from '../fmt.js';

const TIPOS = ['GASTO', 'INGRESO', 'TRANSFERENCIA', 'CXC', 'CXP'];
const vacio = (pid) => ({ rule_name: '', category: '', transaction_type: 'GASTO', debit_account_code: '',
  credit_account_code: '__BANK__', description: '', portfolio_id: pid ?? null, is_active: true });

export default function ReglasTab({ portfolioId, portfolios, cuentas, onCambio }) {
  const [reglas, setReglas] = useState([]);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState(null);      // nueva o edición (con id)
  const [preview, setPreview] = useState(null);
  const btn = 'border border-black px-1.5 py-0.5 text-[10px] font-bold hover:bg-black hover:text-white disabled:opacity-40';
  const inp = 'border border-black px-1 py-0.5 text-[10px] font-mono bg-white';
  const cuentasConBank = [{ code: '__BANK__', name: 'Cuenta bancaria de la TX (resuelta al asentar)' }, ...(cuentas || [])];

  const cargar = useCallback(async () => {
    setError('');
    try { setReglas(await api.get(`/contadores/posting-rules${portfolioId != null ? `?portfolio_id=${portfolioId}` : ''}`)); }
    catch (e) { setError(e.message); }
  }, [portfolioId]);
  useEffect(() => { cargar(); }, [cargar]);

  const ejecutar = async (fn, ok) => {
    setBusy(true); setError(''); setMsg('');
    try { await fn(); setMsg(ok); await cargar(); onCambio?.(); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const guardar = () => ejecutar(async () => {
    const body = { ...form, rule_name: form.rule_name || form.category };
    if (form.id) await api.put(`/contadores/posting-rules/${form.id}`, body);
    else await api.post('/contadores/posting-rules', body);
    setForm(null);
  }, '✔ Regla guardada');
  const eliminar = (r) => {
    if (!window.confirm(`¿Eliminar la regla "${r.rule_name}" (${r.category} / ${r.transaction_type})?`)) return;
    ejecutar(() => api.del(`/contadores/posting-rules/${r.id}`), '✔ Regla eliminada');
  };
  const toggleActiva = (r) => ejecutar(() => api.put(`/contadores/posting-rules/${r.id}`, { is_active: !r.is_active }), r.is_active ? 'Regla desactivada' : 'Regla activada');
  const previsualizar = async (r) => {
    try {
      const p = new URLSearchParams({ category: r.category, tx_type: r.transaction_type, amount: 100000 });
      setPreview({ regla: r, ...(await api.get(`/posting-rules/preview?${p}`)) });
    } catch (e) { setError(e.message); }
  };

  const categoriasSugeridas = form ? (CATEGORIAS[form.transaction_type] || []) : [];

  return (
    <div className="space-y-2">
      <div className="bg-white border-2 border-black p-2 shadow-brutal flex flex-wrap items-center gap-2 text-[10px]">
        <b>{reglas.length} regla(s)</b> · globales + {portfolioId != null ? 'del portafolio' : 'todas'}
        <button className={btn} onClick={() => setForm(vacio(portfolioId))}>+ REGLA</button>
        <span className="text-gray-600">Cada registro busca la regla por (categoría, tipo); si no hay, usa __FALLBACK__. Lo que el contador decide aquí es cómo se contabiliza cada cosa.</span>
        {msg && <span className="font-bold">{msg}</span>}
      </div>
      {error && <div className="bg-brutalCrimson text-white border-2 border-black p-1 text-[10px]">{error}</div>}

      {form && (
        <div className="bg-white border-2 border-black p-2 shadow-brutal space-y-1 text-[10px]">
          <div className="flex flex-wrap gap-1 items-center">
            <select className={inp} value={form.transaction_type} onChange={(e) => setForm({ ...form, transaction_type: e.target.value })}>{TIPOS.map((t) => <option key={t}>{t}</option>)}</select>
            <input list="cat-list" className={`${inp} w-44`} placeholder="categoría" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
            <datalist id="cat-list">{categoriasSugeridas.map((c) => <option key={c} value={c} />)}<option value="__FALLBACK__" /></datalist>
            <input className={`${inp} w-44`} placeholder="nombre de la regla" value={form.rule_name} onChange={(e) => setForm({ ...form, rule_name: e.target.value })} />
            <select className={inp} value={form.portfolio_id ?? ''} onChange={(e) => setForm({ ...form, portfolio_id: e.target.value === '' ? null : Number(e.target.value) })}>
              <option value="">GLOBAL</option>
              {(portfolios || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div className="flex flex-wrap gap-2 items-center">
            <label>Débito <CuentaSelect cuentas={cuentasConBank} value={form.debit_account_code} listId="coa-deb" onChange={(v) => setForm({ ...form, debit_account_code: v })} /></label>
            <label>Crédito <CuentaSelect cuentas={cuentasConBank} value={form.credit_account_code} listId="coa-cre" onChange={(v) => setForm({ ...form, credit_account_code: v })} /></label>
            <input className={`${inp} flex-1`} placeholder="descripción" value={form.description || ''} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <label className="flex items-center gap-1"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> activa</label>
            <button className={`${btn} bg-brutalGreen`} disabled={busy || !form.category || !form.debit_account_code || !form.credit_account_code} onClick={guardar}>{form.id ? 'GUARDAR' : 'CREAR'}</button>
            <button className={btn} onClick={() => setForm(null)}>CANCELAR</button>
          </div>
        </div>
      )}

      {preview && (
        <div className="bg-white border-2 border-black p-2 shadow-brutal text-[10px]">
          <b>Previsualización</b> de "{preview.regla.rule_name}" con $100.000: {preview.found
            ? <>Db <b>{preview.debit.cuenta_codigo}</b> {fmt(preview.debit.monto)} · Cr <b>{preview.credit.cuenta_codigo}</b> {fmt(preview.credit.monto)} · {preview.balanced ? 'CUADRA' : 'NO CUADRA'}</>
            : 'sin regla aplicable'}
          <button className={`${btn} ml-2`} onClick={() => setPreview(null)}>✕</button>
        </div>
      )}

      <div className="bg-white border-2 border-black shadow-brutal overflow-x-auto">
        <table className="w-full text-[10px] font-mono">
          <thead><tr className="bg-black text-white"><th className="px-1 text-left">TIPO</th><th className="px-1 text-left">CATEGORÍA</th><th className="px-1 text-left">REGLA</th><th className="px-1 text-left">DÉBITO</th><th className="px-1 text-left">CRÉDITO</th><th className="px-1 text-left">ÁMBITO</th><th className="px-1"></th></tr></thead>
          <tbody>
            {reglas.map((r) => (
              <tr key={r.id} className={`border-b border-black ${r.is_active ? '' : 'opacity-50'}`}>
                <td className="px-1 py-0.5 font-bold">{r.transaction_type}</td>
                <td className="px-1 py-0.5">{r.category}</td>
                <td className="px-1 py-0.5">{r.rule_name}<div className="text-[9px] text-gray-600">{r.description}</div></td>
                <td className="px-1 py-0.5">{r.debit_account_code} <span className="text-gray-600">{r.debit_name || ''}</span></td>
                <td className="px-1 py-0.5">{r.credit_account_code} <span className="text-gray-600">{r.credit_name || ''}</span></td>
                <td className="px-1 py-0.5"><span className="text-[9px] border border-black px-1">{r.portfolio_name || 'GLOBAL'}</span></td>
                <td className="px-1 py-0.5 whitespace-nowrap">
                  <button className={btn} onClick={() => previsualizar(r)} title="Previsualizar">👁</button>{' '}
                  <button className={btn} onClick={() => setForm({ ...r, description: r.description || '' })}>✎</button>{' '}
                  <button className={btn} onClick={() => toggleActiva(r)}>{r.is_active ? 'OFF' : 'ON'}</button>{' '}
                  <button className={`${btn} text-brutalCrimson`} onClick={() => eliminar(r)}>🗑</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
