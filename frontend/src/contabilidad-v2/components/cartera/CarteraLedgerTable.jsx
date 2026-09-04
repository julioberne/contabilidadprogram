// CarteraLedgerTable.jsx — Sub-tabs, sort bar, accounts table, and payment history
import React from 'react';
import NumInput from '../../../shared/NumInput';

export default function CarteraLedgerTable({
  filteredCartera, subTab, setSubTab, sortBy, setSortBy,
  panelCartera, cxcCount, cxpCount, SORT_OPTIONS,
  selectedLedger, loadPayments, payments, loadingPay,
  expandedNote, setExpandedNote, getDueSemaforo,
  abonoOpen, setAbonoOpen, abonoAmt, setAbonoAmt,
  abonoDate, setAbonoDate, abonoNote, setAbonoNote,
  handleAbono, setSelectedLedger, setPayments,
  searchQ, setSearchQ, handleQuickCuota, handleSavePlan,
  handleDeletePayment, handleSaveLedger
}) {
  // Edición inline del plan (📐 definir/cambiar cuota e interés)
  const [planEditId, setPlanEditId] = React.useState(null);
  const [planDraft, setPlanDraft] = React.useState({});
  const abrirPlanEdit = (c) => {
    setPlanEditId(c.id);
    setPlanDraft({
      min_payment: c.min_payment || '',
      interest_rate: c.interest_rate || '',
      interest_period: c.interest_period || 'MENSUAL',
    });
  };
  const guardarPlan = async (id) => {
    const ok = await handleSavePlan(id, {
      min_payment: parseFloat(planDraft.min_payment) > 0 ? parseFloat(planDraft.min_payment) : null,
      interest_rate: parseFloat(planDraft.interest_rate) > 0 ? parseFloat(planDraft.interest_rate) : null,
      interest_period: planDraft.interest_period,
    });
    if (ok) setPlanEditId(null);
  };
  const fmtCorte = (iso) => iso ? new Date(iso + 'T00:00:00').toLocaleDateString('es-CO', {day:'2-digit', month:'short'}) : null;

  // ✎ Edición inline de la CUENTA (monto, fechas, frecuencia, plazo)
  const [ledgerEditId, setLedgerEditId] = React.useState(null);
  const [ledgerDraft, setLedgerDraft] = React.useState({});
  const abrirLedgerEdit = (c) => {
    setLedgerEditId(c.id);
    setLedgerDraft({
      original_amount: c.original_amount || '',
      start_date: c.start_date || '', due_date: c.due_date || '',
      payment_frequency: String(c.payment_frequency || 30), term: c.term || 'Corto',
      concept: c.concept || '',
    });
  };
  const guardarLedger = async (id) => {
    const ok = await handleSaveLedger(id, {
      original_amount: parseFloat(ledgerDraft.original_amount) > 0 ? parseFloat(ledgerDraft.original_amount) : null,
      start_date: ledgerDraft.start_date || null, due_date: ledgerDraft.due_date || null,
      payment_frequency: parseInt(ledgerDraft.payment_frequency) || null, term: ledgerDraft.term,
      concept: ledgerDraft.concept ?? '',
    });
    if (ok) setLedgerEditId(null);
  };

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

      {/* ─── BUSCADOR ─── */}
      <div className="flex items-center border border-black border-t-0 bg-white">
        <span className="px-2 text-[10px]">🔍</span>
        <input type="text" value={searchQ || ''} onChange={e => setSearchQ(e.target.value)}
          placeholder="Buscar por tercero, NIT/CC o concepto..."
          className="flex-1 py-1 pr-2 text-[10px] font-mono outline-none placeholder-gray-400" />
        {searchQ && (
          <button onClick={() => setSearchQ('')} title="Limpiar búsqueda"
            className="px-2 text-[10px] text-gray-400 hover:text-black">✕</button>
        )}
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
                      {/* Concepto: qué se está cobrando/pagando */}
                      {c.concept && (
                        <div className={`text-[8px] mt-0.5 truncate max-w-[180px] ${isSelected ? 'text-gray-300' : 'text-gray-500'}`}
                             title={c.concept}>
                          📝 {c.concept}
                        </div>
                      )}
                      {/* Cuándo DEBERÍA ser el próximo pago/cobro */}
                      {c.proximo_corte && (
                        <div className={`text-[8px] mt-0.5 font-bold ${isSelected ? 'text-yellow-300' : 'text-indigo-600'}`}
                             title="Próxima fecha esperada según la frecuencia de corte">
                          📅 Próx. {c.type === 'CXC' ? 'cobro' : 'pago'}: {fmtCorte(c.proximo_corte)}
                        </div>
                      )}
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
                      {c.plan?.en_mora && (
                        <div className="mt-0.5">
                          <span className="px-1 py-0.5 text-[7px] font-bold border bg-red-600 border-red-700 text-white"
                                title={`Cuota mínima incumplida: debe llevar $${Number(c.plan.cuota_exigida).toLocaleString('es-CO')} y lleva $${Number(c.plan.abonado_total).toLocaleString('es-CO')}`}>
                            🔥 MORA
                          </span>
                        </div>
                      )}
                    </td>
                  </tr>

                  {/* ─── ZONA 2: HISTORIAL EXPANDIBLE ─── */}
                  {isSelected && (
                    <tr>
                      <td colSpan={5} className="p-0">
                        <div className="border-t-2 border-black bg-white">
                          {/* Header */}
                          <div className="flex items-center justify-between px-2 py-1 bg-gray-50 border-b border-gray-200">
                            <span className="text-[9px] font-bold uppercase font-mono flex items-center gap-1">
                              Historial de Abonos · {c.third_party_name}
                              <button onClick={() => ledgerEditId === c.id ? setLedgerEditId(null) : abrirLedgerEdit(c)}
                                title="Editar la cuenta (monto, fechas, frecuencia, plazo)"
                                className="px-1 text-[10px] hover:text-blue-700">✎</button>
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

                          {/* ✎ Editor inline de la CUENTA */}
                          {ledgerEditId === c.id && (
                            <div className="px-2 py-1.5 border-b border-black bg-blue-50 flex flex-wrap items-end gap-2 text-[9px] font-mono">
                              <span className="font-bold uppercase">✎ Cuenta</span>
                              <label className="text-[8px] font-bold uppercase">Monto total
                                <NumInput value={ledgerDraft.original_amount}
                                  onChange={e => setLedgerDraft(d => ({ ...d, original_amount: e.target.value }))}
                                  className="block border border-black px-1 py-0.5 text-[10px] font-mono outline-none bg-white text-right w-28" />
                              </label>
                              <label className="text-[8px] font-bold uppercase">Inicio
                                <input type="date" value={ledgerDraft.start_date}
                                  onChange={e => setLedgerDraft(d => ({ ...d, start_date: e.target.value }))}
                                  className="block border border-black px-1 py-0.5 text-[10px] font-mono bg-white" />
                              </label>
                              <label className="text-[8px] font-bold uppercase">Vencimiento
                                <input type="date" value={ledgerDraft.due_date}
                                  onChange={e => setLedgerDraft(d => ({ ...d, due_date: e.target.value }))}
                                  className="block border border-black px-1 py-0.5 text-[10px] font-mono bg-white" />
                              </label>
                              <label className="text-[8px] font-bold uppercase">Corte c/días
                                <input type="text" inputMode="numeric" value={ledgerDraft.payment_frequency}
                                  onChange={e => setLedgerDraft(d => ({ ...d, payment_frequency: e.target.value.replace(/\D/g, '') }))}
                                  className="block border border-black px-1 py-0.5 text-[10px] font-mono bg-white text-right w-14" />
                              </label>
                              <label className="text-[8px] font-bold uppercase flex-1 min-w-[140px]">Concepto
                                <input type="text" value={ledgerDraft.concept}
                                  onChange={e => setLedgerDraft(d => ({ ...d, concept: e.target.value }))}
                                  placeholder="¿Qué se cobra/paga?"
                                  className="block border border-black px-1 py-0.5 text-[10px] font-mono outline-none bg-white w-full" />
                              </label>
                              <label className="text-[8px] font-bold uppercase">Plazo
                                <select value={ledgerDraft.term}
                                  onChange={e => setLedgerDraft(d => ({ ...d, term: e.target.value }))}
                                  className="block border border-black px-1 py-0.5 text-[10px] font-mono bg-white">
                                  <option value="Corto">Corto</option><option value="Mediano">Mediano</option><option value="Largo">Largo</option>
                                </select>
                              </label>
                              <button onClick={() => guardarLedger(c.id)}
                                className="px-2 py-0.5 text-[9px] font-bold uppercase border border-black bg-brutalGreen hover:bg-black hover:text-white">💾 Guardar</button>
                              <button onClick={() => setLedgerEditId(null)}
                                className="px-2 py-0.5 text-[9px] font-bold uppercase border border-black bg-white hover:bg-red-100">✕</button>
                              <span className="text-[8px] text-gray-500 w-full">Si cambias el monto, el saldo se recalcula contra lo ya abonado. La cuota/interés se editan en 📐 Plan.</span>
                            </div>
                          )}

                          {/* 📐 Editor inline del plan (definir o cambiar cuota/interés) */}
                          {planEditId === c.id ? (
                            <div className="px-2 py-1.5 border-b border-black bg-yellow-50 flex flex-wrap items-end gap-2 text-[9px] font-mono">
                              <span className="font-bold uppercase">📐 Plan</span>
                              <label className="text-[8px] font-bold uppercase">Cuota mínima
                                <NumInput value={planDraft.min_payment}
                                  onChange={e => setPlanDraft(d => ({ ...d, min_payment: e.target.value }))}
                                  placeholder="$0" className="block border border-black px-1 py-0.5 text-[10px] font-mono outline-none bg-white text-right w-28" />
                              </label>
                              <label className="text-[8px] font-bold uppercase">Tasa %
                                <NumInput value={planDraft.interest_rate}
                                  onChange={e => setPlanDraft(d => ({ ...d, interest_rate: e.target.value }))}
                                  placeholder="0" className="block border border-black px-1 py-0.5 text-[10px] font-mono outline-none bg-white text-right w-16" />
                              </label>
                              <label className="text-[8px] font-bold uppercase">Periodo
                                <select value={planDraft.interest_period}
                                  onChange={e => setPlanDraft(d => ({ ...d, interest_period: e.target.value }))}
                                  className="block border border-black px-1 py-0.5 text-[10px] font-mono bg-white">
                                  <option value="MENSUAL">Mensual</option>
                                  <option value="ANUAL">Anual</option>
                                </select>
                              </label>
                              <button onClick={() => guardarPlan(c.id)}
                                className="px-2 py-0.5 text-[9px] font-bold uppercase border border-black bg-brutalGreen hover:bg-black hover:text-white">💾 Guardar</button>
                              <button onClick={() => setPlanEditId(null)}
                                className="px-2 py-0.5 text-[9px] font-bold uppercase border border-black bg-white hover:bg-red-100">✕</button>
                            </div>
                          ) : !c.plan && (
                            <div className="px-2 py-1 border-b border-gray-200 bg-gray-50">
                              <button onClick={() => abrirPlanEdit(c)}
                                className="text-[9px] font-mono font-bold uppercase border border-dashed border-gray-400 px-2 py-0.5 hover:border-black hover:bg-yellow-50">
                                📐 Definir cuota / interés
                              </button>
                            </div>
                          )}

                          {/* 📐 Plan de pagos (derivado — cuota, mora, interés) */}
                          {c.plan && planEditId !== c.id && (
                            <div className={`px-2 py-1 border-b text-[9px] font-mono flex flex-wrap items-center gap-x-3 gap-y-0.5 ${c.plan.en_mora ? 'bg-red-50 border-red-200' : 'bg-blue-50 border-blue-200'}`}>
                              <span className="font-bold uppercase">📐 Plan</span>
                              {c.plan.cuota_minima > 0 && (
                                <span title="Cuota mínima exigida en cada corte">
                                  Cuota: <b>${Number(c.plan.cuota_minima).toLocaleString('es-CO')}</b> c/{c.payment_frequency || 30}d
                                </span>
                              )}
                              {c.plan.cuota_exigida != null && (
                                <span title={`${c.plan.cortes_cumplidos || 0} corte(s) cumplidos × cuota mínima`}>
                                  Debe llevar: <b>${Number(c.plan.cuota_exigida).toLocaleString('es-CO')}</b> · lleva ${Number(c.plan.abonado_total).toLocaleString('es-CO')}
                                </span>
                              )}
                              {c.plan.proximo_corte && <span>Próx. corte: <b>{c.plan.proximo_corte}</b></span>}
                              {c.plan.interest_rate > 0 && (
                                <span title="Interés simple sobre saldo, prorrateado por día. Los abonos cubren primero el interés.">
                                  Interés {c.plan.interest_rate}% {c.plan.interest_period === 'ANUAL' ? 'anual' : 'mensual'} ·
                                  devengado <b className="text-amber-700">${Number(c.plan.interes_devengado || 0).toLocaleString('es-CO')}</b> ({c.plan.interes_dias}d)
                                </span>
                              )}
                              <span className={`px-1 text-[8px] font-bold border ${c.plan.en_mora ? 'bg-red-600 text-white border-red-700' : 'bg-green-100 text-green-700 border-green-500'}`}>
                                {c.plan.en_mora ? '🔥 EN MORA' : '✓ AL DÍA'}
                              </span>
                              <button onClick={() => abrirPlanEdit(c)} title="Editar cuota / interés"
                                className="px-1 text-[9px] hover:text-blue-700">✎</button>
                              {/* 🧮 Calculadora de mora: por qué, cuánto y cómo salir */}
                              {c.plan.en_mora && c.plan.mora_monto > 0 && (
                                <div className="w-full mt-0.5 px-1.5 py-1 border border-red-300 bg-red-100 text-red-800 text-[9px] leading-snug">
                                  <b>🧮 Mora: ${Number(c.plan.mora_monto).toLocaleString('es-CO')}</b>
                                  {' '}({c.plan.cuotas_atrasadas} cuota{c.plan.cuotas_atrasadas > 1 ? 's' : ''} atrasada{c.plan.cuotas_atrasadas > 1 ? 's' : ''})
                                  {' '}— van {c.plan.cortes_cumplidos} corte{c.plan.cortes_cumplidos > 1 ? 's' : ''} × ${Number(c.plan.cuota_minima).toLocaleString('es-CO')} = ${Number(c.plan.cuota_exigida).toLocaleString('es-CO')} exigidos y lleva ${Number(c.plan.abonado_total).toLocaleString('es-CO')}.
                                  {' '}Se pone al día pagando <b>${Number(c.plan.mora_monto).toLocaleString('es-CO')}</b>
                                  {c.plan.proximo_corte && <> · próxima cuota: <b>{fmtCorte(c.plan.proximo_corte)}</b></>}
                                </div>
                              )}
                            </div>
                          )}

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
                                          <td className="p-1 border-r border-gray-200 text-right">
                                            <span className="font-bold text-green-700">+${Number(p.amount).toLocaleString()}</span>
                                            {Number(p.interest_part) > 0 && (
                                              <div className="text-[7px] text-amber-700" title="Desglose: primero interés devengado, el resto amortiza capital">
                                                int ${Number(p.interest_part).toLocaleString('es-CO')} · cap ${Number(p.principal_part || 0).toLocaleString('es-CO')}
                                              </div>
                                            )}
                                          </td>
                                          <td className="p-1 border-r border-gray-200 text-right">{p.balance_after!=null ? `$${Number(p.balance_after).toLocaleString()}` : '—'}</td>
                                          <td className="p-1 text-gray-400">
                                            <div className="flex items-center justify-between">
                                              <span className={expandedNote === p.id ? '' : 'truncate max-w-[70px]'}>{p.note||'—'}</span>
                                              <span className="flex items-center flex-shrink-0 ml-1">
                                                {p.note && p.note.length > 12 && (
                                                  <span className="text-[7px] text-gray-300">{expandedNote === p.id ? '▲' : '▼'}</span>
                                                )}
                                                <button onClick={(e) => { e.stopPropagation(); handleDeletePayment(p); }}
                                                  title="Eliminar este abono (borra su asiento y recalcula el saldo)"
                                                  className="px-1 text-[10px] text-gray-300 hover:text-red-600">🗑</button>
                                              </span>
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
                                  <div className="flex gap-1">
                                    <button onClick={() => setAbonoOpen(true)}
                                      className="flex-1 py-1 text-[9px] font-bold uppercase font-mono bg-brutalBg border border-black hover:bg-black hover:text-white transition-all">
                                      + Registrar Abono
                                    </button>
                                    {c.plan?.cuota_minima > 0 && rem > 0 && (
                                      <button onClick={() => handleQuickCuota(c)}
                                        title="Registra en un clic un abono por el valor de la cuota mínima"
                                        className="flex-1 py-1 text-[9px] font-bold uppercase font-mono bg-brutalGreen border border-black hover:bg-black hover:text-white transition-all">
                                        ⚡ Registrar cuota (${Number(c.plan.cuota_minima).toLocaleString('es-CO')})
                                      </button>
                                    )}
                                  </div>
                                ) : (
                                  <div className="space-y-1">
                                    <div className="text-[8px] font-bold uppercase font-mono text-gray-500 flex justify-between">
                                      <span>Nuevo abono</span>
                                      <span className="text-red-500">Pendiente: ${rem.toLocaleString()}</span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-1">
                                      <NumInput value={abonoAmt} onChange={e => setAbonoAmt(e.target.value)}
                                        placeholder="$ Monto"
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
