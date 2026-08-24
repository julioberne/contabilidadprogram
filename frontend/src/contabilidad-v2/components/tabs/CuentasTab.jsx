// CuentasTab.jsx — Panel de Cuentas: saldos, CRUD, vínculos a empresas y desfase.
// Consolidación 2026-08-24: el módulo "Pulso de Cuentas" se eliminó (duplicaba
// este tab); sus funciones únicas viven aquí:
//   · chips VISIBLE EN por cuenta (vínculos N:M a empresas/portafolios)
//   · 🔗 traer cuentas de otras empresas al portafolio activo
//   · DESFASE: esperado (inicial + transacciones) vs saldo real del banco —
//     la diferencia identifica ajustes manuales o gastos financieros no
//     contemplados. ⟳ Reconciliar alinea el libro DESPUÉS de revisarla.
import React, { useState } from 'react';
import { API } from '../../../config';
import { useEmpresa } from '../../engine/EmpresaProvider.jsx';

const TIPOS = ['Ahorros', 'Corriente', 'Crédito', 'Efectivo', 'Billetera', 'Crypto'];

/** Las cuentas de crédito viven en negativo por diseño; el resto no debería. */
export const esCuentaCredito = (acc) => String(acc?.type || '').toLowerCase().startsWith('créd')
  || String(acc?.type || '').toLowerCase().startsWith('cred');

const fmt = (n, currency = 'COP') =>
  `${currency === 'COP' ? '$' : ''}${Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 })}`;

const esperadoDe = (acc) => acc.expected_balance !== undefined
  ? Number(acc.expected_balance)
  : Number(acc.initial_balance || 0) + Number(acc.tx_delta || 0);

const desfaseDe = (acc) => Number(acc.current_balance || 0) - esperadoDe(acc);

export default function CuentasTab({
  accounts,
  newAccName, setNewAccName,
  newAccType, setNewAccType,
  newAccCurrency, setNewAccCurrency,
  newAccBalance, setNewAccBalance,
  handleAddAccount,
  handleUpdateAccount,
  handleDeleteAccount,
  handleReconcile,
  refreshAccounts,
  accError,
  SectionLabel,
}) {
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState({});
  const [addingLinkTo, setAddingLinkTo] = useState(null);   // fila con "+" abierto
  const [traerOpen, setTraerOpen] = useState(false);        // panel 🔗 traer cuenta
  const [otrasCuentas, setOtrasCuentas] = useState(null);   // null = sin cargar
  const [busy, setBusy] = useState(false);
  const { portfolios = [], activePortfolio } = useEmpresa();

  // ── Vínculos N:M cuenta ↔ portafolio ──
  const vincular = async (accountId, portfolioName) => {
    setBusy(true);
    try {
      await fetch(`${API}/accounts/${accountId}/links`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio_name: portfolioName }),
      });
      refreshAccounts?.();
      if (traerOpen) cargarOtras();
    } finally { setBusy(false); setAddingLinkTo(null); }
  };

  const desvincular = async (accountId, portfolioName) => {
    setBusy(true);
    try {
      await fetch(`${API}/accounts/${accountId}/links?portfolio_name=${encodeURIComponent(portfolioName)}`,
                  { method: 'DELETE' });
      refreshAccounts?.();
    } finally { setBusy(false); }
  };

  // Cuentas de otras empresas que se pueden traer al portafolio activo
  const cargarOtras = async () => {
    try {
      const r = await fetch(`${API}/accounts`);
      if (!r.ok) return;
      const todas = await r.json();
      setOtrasCuentas(todas.filter(a =>
        a.portfolio_links?.length && !a.portfolio_links.includes(activePortfolio)));
    } catch { setOtrasCuentas([]); }
  };

  // ── Totales por moneda: real, esperado y desfase ──
  const totales = accounts.reduce((acc, a) => {
    const cur = a.currency || 'COP';
    acc[cur] = acc[cur] || { real: 0, esperado: 0 };
    acc[cur].real += Number(a.current_balance || 0);
    acc[cur].esperado += esperadoDe(a);
    return acc;
  }, {});
  const hayDesfase = accounts.some(a => Math.abs(desfaseDe(a)) > 1);

  const enRojo = accounts.filter(a => Number(a.current_balance || 0) < 0 && !esCuentaCredito(a));

  const startEdit = (acc) => {
    setEditingId(acc.id);
    setDraft({ name: acc.name, type: acc.type, current_balance: acc.current_balance,
               initial_balance: acc.initial_balance });
  };

  const saveEdit = async (id) => {
    const ok = await handleUpdateAccount(id, {
      name: draft.name,
      type: draft.type,
      // Saldo ACTUAL = el valor real del banco. Vacío = no tocar.
      current_balance: draft.current_balance === '' ? null : Number(draft.current_balance),
      // Saldo INICIAL = el punto de partida del cálculo esperado.
      initial_balance: draft.initial_balance === '' || draft.initial_balance === undefined
        ? null : Number(draft.initial_balance),
    });
    if (ok) setEditingId(null);
  };

  return (
    <>
      {accError && (
        <div className="border-2 border-black bg-red-500 text-white px-2 py-1 text-[9px] font-mono font-bold uppercase">
          ⚠ {accError}
        </div>
      )}

      {/* ═══ RESUMEN: REAL vs ESPERADO ═══ */}
      <div className="border-2 border-black bg-black text-white p-2 space-y-1">
        <div className="text-[8px] font-mono uppercase tracking-widest text-gray-400">
          Disponible total · {activePortfolio || 'todas'}
        </div>
        {Object.keys(totales).length === 0 && (
          <div className="text-[10px] font-mono text-gray-500">Sin cuentas registradas</div>
        )}
        {Object.entries(totales).map(([cur, t]) => {
          const desfase = t.real - t.esperado;
          return (
            <div key={cur} className="space-y-0">
              <div className="flex justify-between items-baseline">
                <span className="text-[9px] font-mono text-gray-400">{cur}</span>
                <span className={`text-sm font-mono font-bold ${t.real < 0 ? 'text-red-400' : 'text-brutalGreen'}`}>
                  {fmt(t.real, cur)}
                </span>
              </div>
              {Math.abs(desfase) > 1 && (
                <div className="flex justify-between items-baseline"
                     title="Real − esperado (inicial + transacciones). Un desfase negativo suele ser gastos financieros no contemplados; uno positivo, ingresos sin registrar o ajustes manuales.">
                  <span className="text-[8px] font-mono text-amber-400">esperado {fmt(t.esperado, cur)}</span>
                  <span className="text-[9px] font-mono font-bold text-amber-400">
                    desfase {desfase > 0 ? '+' : ''}{fmt(desfase, cur)}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {enRojo.length > 0 && (
        <div className="border-2 border-black bg-red-100 p-2">
          <div className="text-[9px] font-mono font-bold uppercase text-red-700">
            ⚠ {enRojo.length} cuenta{enRojo.length > 1 ? 's' : ''} sobregirada{enRojo.length > 1 ? 's' : ''}
          </div>
          <div className="text-[9px] font-mono text-red-700 mt-0.5">
            {enRojo.map(a => `${a.name} (${fmt(a.current_balance, a.currency)})`).join(' · ')}
          </div>
        </div>
      )}

      {/* ═══ ALTA (nace vinculada al portafolio activo) ═══ */}
      <div className="border border-black p-2 bg-brutalBg space-y-1.5">
        <SectionLabel text={`Agregar nueva cuenta financiera → ${activePortfolio || 'compartida'}`} />
        <form onSubmit={handleAddAccount} className="space-y-1">
          <input type="text" value={newAccName} onChange={e => setNewAccName(e.target.value)} placeholder="Nombre (ej: Bancolombia)" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" required />
          <div className="grid grid-cols-2 gap-1">
            <select value={newAccType} onChange={e => setNewAccType(e.target.value)} className="border border-black px-2 py-1 text-[10px] font-mono">
              {TIPOS.map(t => <option key={t}>{t}</option>)}
            </select>
            <select value={newAccCurrency} onChange={e => setNewAccCurrency(e.target.value)} className="border border-black px-2 py-1 text-[10px] font-mono">
              <option>COP</option><option>USD</option><option>EUR</option>
            </select>
          </div>
          <div className="flex gap-1">
            <input type="number" step="any" value={newAccBalance} onChange={e => setNewAccBalance(e.target.value)} placeholder="Saldo Inicial" className="flex-grow border border-black px-2 py-1 text-[10px] font-mono outline-none" />
            <button type="submit" className="bg-black text-white border border-black px-3 py-1 text-[8px] font-bold uppercase hover:bg-brutalGreen hover:text-black">Añadir</button>
          </div>
        </form>
      </div>

      {/* ═══ TABLA / CRUD ═══ */}
      <div className="flex justify-between items-center gap-1">
        <SectionLabel text={`user_accounts · ${accounts.length} registros`} />
        <div className="flex gap-1 shrink-0">
          <button
            onClick={() => { const abrir = !traerOpen; setTraerOpen(abrir); if (abrir) cargarOtras(); }}
            title="Traer una cuenta de otra empresa/portafolio a esta"
            className={`border border-black px-2 py-0.5 text-[8px] font-mono font-bold uppercase ${traerOpen ? 'bg-black text-white' : 'hover:bg-black hover:text-white'}`}
          >🔗 Traer cuenta</button>
          <button
            onClick={handleReconcile}
            title="Alinea el saldo actual con el esperado (inicial + transacciones). Revisa primero el DESFASE: esa diferencia son ajustes manuales o gastos financieros no contemplados."
            className="border border-black px-2 py-0.5 text-[8px] font-mono font-bold uppercase hover:bg-black hover:text-white"
          >⟳ Reconciliar</button>
        </div>
      </div>

      {/* Panel: traer cuentas de otras empresas al portafolio activo */}
      {traerOpen && (
        <div className="border border-black bg-amber-50 p-2 space-y-1">
          <div className="text-[8px] font-mono font-bold uppercase text-amber-800">
            Vincular a {activePortfolio || '—'}:
          </div>
          {otrasCuentas === null && <div className="text-[9px] font-mono text-gray-500">Cargando…</div>}
          {otrasCuentas?.length === 0 && (
            <div className="text-[9px] font-mono text-gray-500">
              No hay cuentas exclusivas de otras empresas (las compartidas ya se ven aquí).
            </div>
          )}
          {otrasCuentas?.map(a => (
            <button key={a.id} disabled={busy || !activePortfolio}
                    onClick={() => vincular(a.id, activePortfolio)}
                    title={`Hoy visible en: ${a.portfolio_links.join(', ')}`}
                    className="border border-black bg-white px-2 py-0.5 mr-1 mb-1 text-[9px] font-mono font-bold hover:bg-black hover:text-white">
              ＋ {a.name} <span className="font-normal text-gray-500">({a.portfolio_links.join(', ')})</span>
            </button>
          ))}
        </div>
      )}

      <table className="w-full text-[10px] font-mono border border-black">
        <thead className="bg-black text-white uppercase"><tr>
          <th className="p-1 border-r border-black text-left">Cuenta / visible en</th>
          <th className="p-1 border-r border-black">Tipo</th>
          <th className="p-1 border-r border-black">Moneda</th>
          <th className="p-1 border-r border-black text-right">Saldo</th>
          <th className="p-1 text-[8px]">Acc.</th>
        </tr></thead>
        <tbody className="divide-y divide-gray-200">
          {accounts.map(acc => {
            const saldo = Number(acc.current_balance || 0);
            const negativo = saldo < 0;
            const alerta = negativo && !esCuentaCredito(acc);
            const links = acc.portfolio_links || [];
            const desfase = desfaseDe(acc);
            const cuadra = Math.abs(desfase) <= 1;
            const linkDisponibles = portfolios.filter(p => !links.includes(p.name));

            if (editingId === acc.id) {
              return (
                <tr key={acc.id} className="bg-yellow-50">
                  <td className="p-1 border-r border-black">
                    <input value={draft.name} onChange={e => setDraft(d => ({ ...d, name: e.target.value }))}
                      className="w-full border border-black px-1 text-[10px] font-mono outline-none" />
                  </td>
                  <td className="p-1 border-r border-black">
                    <select value={draft.type} onChange={e => setDraft(d => ({ ...d, type: e.target.value }))}
                      className="w-full border border-black text-[9px] font-mono">
                      {TIPOS.map(t => <option key={t}>{t}</option>)}
                    </select>
                  </td>
                  <td className="p-1 border-r border-black text-center text-[9px] text-gray-400">{acc.currency || 'COP'}</td>
                  <td className="p-1 border-r border-black space-y-0.5">
                    <input type="number" step="any" value={draft.current_balance}
                      onChange={e => setDraft(d => ({ ...d, current_balance: e.target.value }))}
                      title="Saldo ACTUAL: el valor real que ves en el banco. Vacío = no tocar."
                      placeholder="Real (banco)"
                      className="w-full border border-black px-1 text-[10px] font-mono text-right outline-none" />
                    <input type="number" step="any" value={draft.initial_balance}
                      onChange={e => setDraft(d => ({ ...d, initial_balance: e.target.value }))}
                      title="Saldo INICIAL: punto de partida del cálculo esperado. Vacío = no tocar."
                      placeholder="Inicial"
                      className="w-full border border-dashed border-black px-1 text-[10px] font-mono text-right outline-none bg-yellow-50" />
                  </td>
                  <td className="p-1 text-center whitespace-nowrap">
                    <button onClick={() => saveEdit(acc.id)} className="px-1 hover:text-brutalGreen" title="Guardar">✔</button>
                    <button onClick={() => setEditingId(null)} className="px-1 hover:text-red-600" title="Cancelar">✕</button>
                  </td>
                </tr>
              );
            }

            return (
              <tr key={acc.id} className={alerta ? 'bg-red-50' : cuadra ? 'hover:bg-brutalBg' : 'bg-amber-50'}>
                <td className="p-1 border-r border-black">
                  <div className="font-bold">{alerta && <span title="Sobregirada">⚠ </span>}{acc.name}</div>
                  <div className="mt-0.5">
                    {links.length === 0 && (
                      <span className="text-[8px] px-1 border border-dashed border-gray-400 text-gray-500"
                            title="Compartida: visible en todos los portafolios">🌐 todas</span>
                    )}
                    {links.map(name => (
                      <span key={name}
                            className="inline-flex items-center gap-0.5 text-[8px] px-1 mr-0.5 border border-black bg-brutalGreen">
                        {name}
                        <button onClick={() => desvincular(acc.id, name)} disabled={busy}
                                title={`Quitar de ${name}${links.length === 1 ? ' (volverá a ser compartida)' : ''}`}
                                className="hover:text-red-700">×</button>
                      </span>
                    ))}
                    {addingLinkTo === acc.id ? (
                      <select autoFocus defaultValue="" onBlur={() => setAddingLinkTo(null)}
                              onChange={e => { if (e.target.value) vincular(acc.id, e.target.value); }}
                              className="text-[8px] border border-black font-mono">
                        <option value="" disabled>vincular a…</option>
                        {linkDisponibles.map(p => <option key={p.id} value={p.name}>{p.name}</option>)}
                      </select>
                    ) : (
                      linkDisponibles.length > 0 && (
                        <button onClick={() => setAddingLinkTo(acc.id)} disabled={busy}
                                title="Vincular esta cuenta a otra empresa/portafolio"
                                className="text-[8px] px-1 border border-black bg-white hover:bg-black hover:text-white">＋</button>
                      )
                    )}
                  </div>
                </td>
                <td className="p-1 border-r border-black text-center text-[9px]">{acc.type}</td>
                <td className="p-1 border-r border-black text-center">{acc.currency || 'COP'}</td>
                <td className={`p-1 border-r border-black text-right font-bold ${negativo ? 'text-red-600' : ''}`}>
                  {fmt(saldo, acc.currency)}
                  {!cuadra && (
                    <div className="text-[8px] font-normal text-amber-700"
                         title="Real − esperado (inicial + transacciones). Negativo: gastos financieros no contemplados; positivo: ingresos sin registrar o ajuste manual.">
                      esp. {fmt(esperadoDe(acc), acc.currency)} · dif {desfase > 0 ? '+' : ''}{fmt(desfase, acc.currency)}
                    </div>
                  )}
                </td>
                <td className="p-1 text-center whitespace-nowrap">
                  <button onClick={() => startEdit(acc)} className="px-1 hover:text-brutalGreen" title="Editar (saldo real del banco / inicial / nombre)">✎</button>
                  <button onClick={() => handleDeleteAccount(acc.id, acc.name)} className="px-1 hover:text-red-600" title="Eliminar">🗑</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {accounts.length === 0 && <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-2">Sin cuentas</p>}
    </>
  );
}
