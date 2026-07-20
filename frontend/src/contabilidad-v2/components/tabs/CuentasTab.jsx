// CuentasTab.jsx — Extracted from ContextPanel.jsx
import React from 'react';

export default function CuentasTab({
  accounts,
  newAccName, setNewAccName,
  newAccType, setNewAccType,
  newAccCurrency, setNewAccCurrency,
  newAccBalance, setNewAccBalance,
  handleAddAccount,
  SectionLabel,
}) {
  return (
    <>
      <div className="border border-black p-2 bg-brutalBg space-y-1.5">
        <SectionLabel text="Agregar nueva cuenta financiera" />
        <form onSubmit={handleAddAccount} className="space-y-1">
          <input type="text" value={newAccName} onChange={e => setNewAccName(e.target.value)} placeholder="Nombre (ej: Bancolombia)" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" required />
          <div className="grid grid-cols-2 gap-1">
            <select value={newAccType} onChange={e => setNewAccType(e.target.value)} className="border border-black px-2 py-1 text-[10px] font-mono">
              <option>Ahorros</option><option>Corriente</option><option>Crédito</option><option>Efectivo</option><option>Billetera</option><option>Crypto</option>
            </select>
            <select value={newAccCurrency} onChange={e => setNewAccCurrency(e.target.value)} className="border border-black px-2 py-1 text-[10px] font-mono">
              <option>COP</option><option>USD</option><option>EUR</option>
            </select>
          </div>
          <div className="flex gap-1">
            <input type="number" value={newAccBalance} onChange={e => setNewAccBalance(e.target.value)} placeholder="Saldo Inicial" className="flex-grow border border-black px-2 py-1 text-[10px] font-mono outline-none" />
            <button type="submit" className="bg-black text-white border border-black px-3 py-1 text-[8px] font-bold uppercase hover:bg-brutalGreen hover:text-black">Añadir</button>
          </div>
        </form>
      </div>
      {/* --- BD: user_accounts --- */}
      <SectionLabel text={`user_accounts · ${accounts.length} registros`} />
      <table className="w-full text-[10px] font-mono border border-black">
        <thead className="bg-black text-white uppercase"><tr>
          <th className="p-1 border-r border-black text-left">Cuenta</th>
          <th className="p-1 border-r border-black">Tipo</th>
          <th className="p-1 border-r border-black">Moneda</th>
          <th className="p-1 text-right">Saldo</th>
        </tr></thead>
        <tbody className="divide-y divide-gray-200">
          {accounts.map(acc => (
            <tr key={acc.id} className="hover:bg-brutalBg">
              <td className="p-1 border-r border-black font-bold">{acc.name}</td>
              <td className="p-1 border-r border-black text-center text-[9px]">{acc.type}</td>
              <td className="p-1 border-r border-black text-center">{acc.currency||'COP'}</td>
              <td className="p-1 text-right font-bold">${Number(acc.current_balance||0).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {accounts.length===0 && <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-2">Sin cuentas</p>}
    </>
  );
}
