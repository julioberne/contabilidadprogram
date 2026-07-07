// CarteraLedgerTable.jsx — Sub-tabs, sort bar, accounts table, and payment history
import React from 'react';

export default function CarteraLedgerTable({
  filteredCartera, subTab, setSubTab, sortBy, setSortBy,
  panelCartera, cxcCount, cxpCount, SORT_OPTIONS,
  selectedLedger, loadPayments, payments, loadingPay,
  expandedNote, setExpandedNote, getDueSemaforo,
  abonoOpen, setAbonoOpen, abonoAmt, setAbonoAmt,
  abonoDate, setAbonoDate, abonoNote, setAbonoNote,
  handleAbono, setSelectedLedger, setPayments
}) {
  return (
    <>
      {/* ─── SUB-TABS: TODAS / CXC / CXP ─── */}
      <div className="flex border border-black overflow-hidden">
        {[
          { key: 'TODAS', label: `TODAS (${panelCartera.length})` },
          { key: 'CXC', label: `📥 CXC (${cxcCount})` },
          { key: 'CXP', label: `📤 CXP (${cxpCount})` },
        ].map(st => (
          <button key={st.key} onClick={() => { setSubTab(st.key); setSelectedLedger(null); setPayments([]); }}
            className={`flex-1 py-1 text-[9px] font-bold uppercase font-mono border-r border-black last:border-r-0 transition-all ${
              subTab === st.key ? 'bg-black text-white' : 'bg-brutalBg text-gray-500 hover:bg-brutalNeutral'
            }`}>{st.label}</button>
        ))}
      </div>

      {/* ─── SORT BAR ─── */}
      <div className="flex items-center gap-0 border border-black border-t-0 bg-brutalBg overflow-x-auto">
        <span className="px-2 py-1 text-[8px] font-bold uppercase text-gray-400 whitespace-nowrap">⇅ Ordenar:</span>
        {SORT_OPTIONS.map(s => (
          <button key={s.key} onClick={() => setSortBy(s.key)}
            className={`px-2 py-1 text-[8px] font-bold uppercase font-mono whitespace-nowrap border-l border-black transition-all ${
              sortBy === s.key ? 'bg-black text-white' : 'text-gray-500 hover:bg-brutalNeutral'
            }`}>{s.icon} {s.label}</button>
        ))}
      </div>

      {/* ─── ZONA 1: CUENTAS ACTIVAS ─── */}
      <div className="border border-black overflow-hidden">
        <table className="w-full text-[10px] font-mono">
          <thead className="bg-black text-white uppercase">
            <tr>
              <th className="p-1 border-r border-gray-700 text-left" style={{width:'28%'}}>Tercero</th>
              <th className="p-1 border-r border-gray-700 text-right" style={{width:'18%'}}>Monto</th>
              <th className="p-1 border-r border-gray-700 text-center" style={{width:'30%'}}>Progreso</th>
              <th className="p-1 border-r border-gray-700 text-center" style={{width:'14%'}}>Vence</th>
              <th className="p-1 text-center" style={{width:'10%'}}>Est.</th>
            </tr>
          </thead>
          <tbody>
            {filteredCartera.map(c => {
              const sem = getDueSemaforo(c.due_date);
              const isSelected = selectedLedger?.id === c.id;
              const orig = Number(c.original_amount || 0);
              const rem = Number(c.remaining_balance || 0);
              const paid = orig - rem;
              const pct = orig > 0 ? Math.round((paid / orig) * 100) : 0;
              const startStr = c.start_date ? new Date(c.start_date).toLocaleDateString('es-CO', {day:'2-digit',month:'short'}) : '—';

              return (
                <React.Fragment key={c.id}>
                  <tr onClick={() => loadPayments(c)}
                    className={`cursor-pointer transition-colors border-b border-gray-200 ${isSelected ? 'bg-black text-white' : 'hover:bg-brutalBg'}`}>
                    <td className="p-1 border-r border-gray-200">
                      <div className="flex items-center gap-1">
                        <span className={`text-[7px] font-bold px-0.5 border ${isSelected ? 'border-white' : c.type==='CXC'?'bg-green-100 border-green-500 text-green-800':'bg-amber-100 border-amber-500 text-amber-800'}`}>{c.type}</span>
                        <span className="font-bold truncate max-w-[80px]">{c.third_party_name||'—'}</span>
                      </div>
                      <div className="text-[8px] text-gray-400 mt-0.5 flex items-center gap-1">
                        <span>{startStr} → {c.due_date ? new Date(c.due_date).toLocaleDateString('es-CO', {day:'2-digit',month:'short'}) : '—'}</span>
                        {c.payment_frequency && (
                          <span className={`px-0.5 text-[6px] font-bold border ${isSelected ? 'border-gray-400 text-gray-300' : 'border-blue-300 bg-blue-50 text-blue-600'}`}>c/{c.payment_frequency}d</span>
                        )}
                      </div>
                    </td>
                    <td className="p-1 border-r border-gray-200 text-right">
                      <div className="font-bold">${orig.toLocaleString()}</div>
                      <div className={`text-[8px] ${isSelected ? 'text-gray-300' : 'text-red-500'}`}>Debe: ${rem.toLocaleString()}</div>
                    </td>
                    <td className="p-1 border-r border-gray-200">
                      {/* Progress bar */}
                      <div className="flex items-center gap-1">
                        <div className="flex-1 h-2 bg-gray-200 border border-gray-300 overflow-hidden" style={{minWidth:'40px'}}>
                          <div className={`h-full transition-all ${pct >= 100 ? 'bg-green-500' : pct >= 50 ? 'bg-blue-500' : 'bg-amber-400'}`}
                            style={{width:`${Math.min(pct, 100)}%`}} />
                        </div>
                        <span className={`text-[8px] font-bold ${isSelected ? '' : pct >= 100 ? 'text-green-600' : 'text-gray-600'}`}>{pct}%</span>
                      </div>
                      <div className={`text-[8px] mt-0.5 ${isSelected ? 'text-gray-300' : 'text-gray-400'}`}>
                        Abonado: ${paid.toLocaleString()}
                      </div>
                    </td>
                    <td className="p-1 border-r border-gray-200 text-center">
                      <span className={isSelected ? 'text-white text-[9px]' : `text-[9px] ${sem.cls}`}>{sem.dot}</span>
                      <div className={`text-[8px] ${isSelected ? 'text-gray-300' : sem.cls}`}>{sem.label}</div>
                    </td>
                    <td className="p-1 text-center">
                      <span className={`px-1 py-0.5 text-[7px] font-bold border ${
                        isSelected ? 'border-white text-white' :
                        c.status==='PAGADO'?'bg-green-100 border-green-500 text-green-700':
                        c.status==='VENCIDO'?'bg-red-100 border-red-500 text-red-700':
                        'bg-yellow-100 border-yellow-500 text-yellow-700'
                      }`}>{c.status === 'PENDIENTE' ? 'PEND' : c.status === 'PAGADO' ? '✓' : c.status || 'PEND'}</span>
                    </td>
                  </tr>

                  {/* ─── ZONA 2: HISTORIAL EXPANDIBLE ─── */}
                  {isSelected && (
                    <tr>
                      <td colSpan={5} className="p-0">
                        <div className="border-t-2 border-black bg-white">
                          {/* Header */}
                          <div className="flex items-center justify-between px-2 py-1 bg-gray-50 border-b border-gray-200">
                            <span className="text-[9px] font-bold uppercase font-mono">
                              Historial de Abonos · {c.third_party_name}
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="text-[8px] font-mono text-gray-500">
                                ${paid.toLocaleString()} de ${orig.toLocaleString()}
                              </span>
                              {/* Mini progress */}
                              <div className="w-12 h-1.5 bg-gray-200 border border-gray-300 overflow-hidden">
                                <div className={`h-full ${pct >= 100 ? 'bg-green-500' : 'bg-blue-500'}`} style={{width:`${Math.min(pct,100)}%`}} />
                              </div>
                              <span className="text-[8px] font-bold font-mono">{pct}%</span>
                            </div>
                          </div>

                          {loadingPay ? (
                            <p className="text-center text-[10px] text-gray-400 font-mono py-3 uppercase">Cargando...</p>
                          ) : (
                            <>
                              {/* Payment history table */}
                              {payments.length > 0 ? (
                                <table className="w-full text-[10px] font-mono">
                                  <thead className="bg-gray-100 uppercase text-gray-400 text-[8px]">
                                    <tr>
                                      <th className="p-1 border-r border-gray-200 text-left">Fecha</th>
                                      <th className="p-1 border-r border-gray-200 text-right">Abono</th>
                                      <th className="p-1 border-r border-gray-200 text-right">Saldo</th>
                                      <th className="p-1 text-left">Nota</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-gray-100">
                                    {payments.map(p => (
                                      <React.Fragment key={p.id}>
                                        <tr className="hover:bg-brutalBg cursor-pointer" onClick={() => setExpandedNote(expandedNote === p.id ? null : p.id)}>
                                          <td className="p-1 border-r border-gray-200">{p.payment_date}</td>
                                          <td className="p-1 border-r border-gray-200 text-right font-bold text-green-700">+${Number(p.amount).toLocaleString()}</td>
                                          <td className="p-1 border-r border-gray-200 text-right">{p.balance_after!=null ? `$${Number(p.balance_after).toLocaleString()}` : '—'}</td>
                                          <td className="p-1 text-gray-400">
                                            <div className="flex items-center justify-between">
                                              <span className={expandedNote === p.id ? '' : 'truncate max-w-[70px]'}>{p.note||'—'}</span>
                                              {p.note && p.note.length > 12 && (
                                                <span className="text-[7px] text-gray-300 flex-shrink-0 ml-1">{expandedNote === p.id ? '▲' : '▼'}</span>
                                              )}
                                            </div>
                                          </td>
                                        </tr>
                                        {expandedNote === p.id && p.note && (
                                          <tr>
                                            <td colSpan={4} className="px-2 py-1 bg-gray-50 border-b border-gray-200">
                                              <div className="text-[9px] font-mono text-gray-600 whitespace-pre-wrap">{p.note}</div>
                                            </td>
                                          </tr>
                                        )}
                                      </React.Fragment>
                                    ))}
                                  </tbody>
                                </table>
                              ) : (
                                <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-2">Sin abonos</p>
                              )}

                              {/* Abono form */}
                              <div className="border-t border-black p-2">
                                {!abonoOpen ? (
                                  <button onClick={() => setAbonoOpen(true)}
                                    className="w-full py-1 text-[9px] font-bold uppercase font-mono bg-brutalBg border border-black hover:bg-black hover:text-white transition-all">
                                    + Registrar Abono
                                  </button>
                                ) : (
                                  <div className="space-y-1">
                                    <div className="text-[8px] font-bold uppercase font-mono text-gray-500 flex justify-between">
                                      <span>Nuevo abono</span>
                                      <span className="text-red-500">Pendiente: ${rem.toLocaleString()}</span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-1">
                                      <input type="number" value={abonoAmt} onChange={e => setAbonoAmt(e.target.value)}
                                        placeholder="$ Monto" max={rem}
                                        className="border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen" autoFocus />
                                      <input type="date" value={abonoDate} onChange={e => setAbonoDate(e.target.value)}
                                        className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                                    </div>
                                    <input type="text" value={abonoNote} onChange={e => setAbonoNote(e.target.value)}
                                      placeholder="Nota (ej: Cuota #3, transferencia Bancolombia...)"
                                      className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                                    <div className="flex gap-1">
                                      <button onClick={handleAbono} disabled={!abonoAmt || parseFloat(abonoAmt) <= 0}
                                        className="flex-1 bg-black text-white border border-black py-1 text-[9px] font-bold uppercase hover:bg-brutalGreen hover:text-black disabled:opacity-40 transition-all">
                                        Confirmar Abono
                                      </button>
                                      <button onClick={() => { setAbonoOpen(false); setAbonoAmt(''); setAbonoNote(''); }}
                                        className="border border-black px-3 py-1 text-[9px] font-bold hover:bg-brutalBg">✕</button>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
        {filteredCartera.length === 0 && (
          <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-3">
            {subTab === 'TODAS' ? 'Sin cuentas activas' : `Sin cuentas ${subTab}`}
          </p>
        )}
      </div>
    </>
  );
}
