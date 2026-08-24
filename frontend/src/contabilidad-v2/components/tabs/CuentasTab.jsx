// CuentasTab.jsx — Panel de Cuentas: saldos, CRUD y control de disponible
import React, { useState } from 'react';
import { useEmpresa } from '../../engine/EmpresaProvider.jsx';

const TIPOS = ['Ahorros', 'Corriente', 'Crédito', 'Efectivo', 'Billetera', 'Crypto'];

/** Las cuentas de crédito viven en negativo por diseño; el resto no debería. */
export const esCuentaCredito = (acc) => String(acc?.type || '').toLowerCase().startsWith('créd')
  || String(acc?.type || '').toLowerCase().startsWith('cred');

const fmt = (n, currency = 'COP') =>
  `${currency === 'COP' ? '$' : ''}${Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 })}`;

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
  accError,
  SectionLabel,
}) {
  const [editingId, setEditingId] = useState(null);
  const [draft, setDraft] = useState({});
  // Portafolios reales para asignar cuentas (separación multi-empresa)
  const { portfolios = [], activePortfolio } = useEmpresa();

  // Totales por moneda — sin esto no hay forma de ver el disponible real
  const totales = accounts.reduce((acc, a) => {
    const cur = a.currency || 'COP';
    acc[cur] = (acc[cur] || 0) + Number(a.current_balance || 0);
    return acc;
  }, {});

  const enRojo = accounts.filter(a => Number(a.current_balance || 0) < 0 && !esCuentaCredito(a));

  const startEdit = (acc) => {
    setEditingId(acc.id);
    setDraft({ name: acc.name, type: acc.type, current_balance: acc.current_balance,
               initial_balance: acc.initial_balance,
               portfolio_name: acc.portfolio_name || '' });
  };

  const saveEdit = async (id) => {
    const ok = await handleUpdateAccount(id, {
      name: draft.name,
      type: draft.type,
      // Solo se manda si el usuario lo tocó: si no, lo gobierna el motor incremental
      current_balance: draft.current_balance === '' ? null : Number(draft.current_balance),
      // Saldo inicial editable — es la base del Pulso de Cuentas; tras
      // cambiarlo, ⟳ Reconciliar recalcula el actual (inicial + transacciones)
      initial_balance: draft.initial_balance === '' || draft.initial_balance === undefined
        ? null : Number(draft.initial_balance),
      // '' = compartida (todos los portafolios); nombre = solo ese portafolio
      portfolio_name: draft.portfolio_name ?? null,
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

      {/* ═══ RESUMEN DE DISPONIBLE ═══ */}
      <div className="border-2 border-black bg-black text-white p-2 space-y-1">
        <div className="text-[8px] font-mono uppercase tracking-widest text-gray-400">Disponible total</div>
        {Object.keys(totales).length === 0 && (
          <div className="text-[10px] font-mono text-gray-500">Sin cuentas registradas</div>
        )}
        {Object.entries(totales).map(([cur, total]) => (
          <div key={cur} className="flex justify-between items-baseline">
            <span className="text-[9px] font-mono text-gray-400">{cur}</span>
            <span className={`text-sm font-mono font-bold ${total < 0 ? 'text-red-400' : 'text-brutalGreen'}`}>
              {fmt(total, cur)}
            </span>
          </div>
        ))}
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

      {/* ═══ ALTA ═══ */}
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
      <div className="flex justify-between items-center">
        <SectionLabel text={`user_accounts · ${accounts.length} registros`} />
        <button
          onClick={handleReconcile}
          title="Recalcula los saldos sumando todas las transacciones desde cero"
          className="border border-black px-2 py-0.5 text-[8px] font-mono font-bold uppercase hover:bg-black hover:text-white shrink-0"
        >⟳ Reconciliar</button>
      </div>

      <table className="w-full text-[10px] font-mono border border-black">
        <thead className="bg-black text-white uppercase"><tr>
          <th className="p-1 border-r border-black text-left">Cuenta</th>
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
                      title="Ajuste manual de saldo ACTUAL. Vacío = no tocar."
                      placeholder="Actual"
                      className="w-full border border-black px-1 text-[10px] font-mono text-right outline-none" />
                    <input type="number" step="any" value={draft.initial_balance}
                      onChange={e => setDraft(d => ({ ...d, initial_balance: e.target.value }))}
                      title="Saldo INICIAL (base del Pulso de Cuentas). Vacío = no tocar."
                      placeholder="Inicial"
                      className="w-full border border-dashed border-black px-1 text-[10px] font-mono text-right outline-none bg-yellow-50" />
                  </td>
                  <td className="p-1 text-center whitespace-nowrap">
                    <select value={draft.portfolio_name} onChange={e => setDraft(d => ({ ...d, portfolio_name: e.target.value }))}
                      title="Portafolio dueño de la cuenta. Compartida = visible en todos."
                      className="w-full border border-black text-[8px] font-mono mb-0.5">
                      <option value="">— compartida —</option>
                      {portfolios.map(p => <option key={p.id} value={p.name}>{p.name}</option>)}
                    </select>
                    <button onClick={() => saveEdit(acc.id)} className="px-1 hover:text-brutalGreen" title="Guardar">✔</button>
                    <button onClick={() => setEditingId(null)} className="px-1 hover:text-red-600" title="Cancelar">✕</button>
                  </td>
                </tr>
              );
            }

            return (
              <tr key={acc.id} className={alerta ? 'bg-red-50' : 'hover:bg-brutalBg'}>
                <td className="p-1 border-r border-black font-bold">
                  {alerta && <span title="Sobregirada">⚠ </span>}{acc.name}
                  <span className={`ml-1 text-[8px] font-normal px-1 border ${acc.portfolio_links?.length ? 'border-black bg-brutalGreen text-black' : 'border-gray-300 text-gray-400'}`}
                        title={acc.portfolio_links?.length
                          ? `Visible en: ${acc.portfolio_links.join(', ')}`
                          : 'Compartida: visible en todos los portafolios'}>
                    {acc.portfolio_links?.length > 1
                      ? `${acc.portfolio_links.length} portafolios`
                      : (acc.portfolio_links?.[0] || 'compartida')}
                  </span>
                </td>
                <td className="p-1 border-r border-black text-center text-[9px]">{acc.type}</td>
                <td className="p-1 border-r border-black text-center">{acc.currency || 'COP'}</td>
                <td className={`p-1 border-r border-black text-right font-bold ${negativo ? 'text-red-600' : ''}`}>
                  {fmt(saldo, acc.currency)}
                </td>
                <td className="p-1 text-center whitespace-nowrap">
                  <button onClick={() => startEdit(acc)} className="px-1 hover:text-brutalGreen" title="Editar">✎</button>
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
