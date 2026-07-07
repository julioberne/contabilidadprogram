// CarteraNewForm.jsx — Collapsible form for creating new CXC/CXP accounts
import React from 'react';

export default function CarteraNewForm({
  formOpen, setFormOpen, formType, setFormType, formTerm, setFormTerm,
  selectedTpId, selectedTpLabel, setSelectedTpId, setSelectedTpLabel,
  tpSearch, setTpSearch, filteredTps, showTpCreate, setShowTpCreate,
  newTpName, setNewTpName, newTpIdType, setNewTpIdType, newTpIdNum, setNewTpIdNum,
  newTpEmail, setNewTpEmail, handleCreateTp,
  formStartDate, setFormStartDate, formDue, setFormDue,
  formFrequency, setFormFrequency, formFreqCustom, setFormFreqCustom,
  formAmount, setFormAmount, formPartial, setFormPartial, saldo,
  showAsiento, setShowAsiento, asientoPreview, setAsientoPreview,
  handleSaveCartera, saving, API_BASE
}) {
  return (
    <div className="border border-black">
      <button onClick={() => setFormOpen(p => !p)}
        className="w-full flex justify-between items-center px-2 py-1.5 bg-brutalBg hover:bg-brutalNeutral transition-all border-b border-black">
        <span className="text-[9px] font-bold uppercase font-mono">✚ Nueva Cuenta CXC / CXP</span>
        <span className="text-[9px] font-mono text-gray-500">{formOpen ? '▲' : '▼'}</span>
      </button>

      {formOpen && (
        <div className="p-2 space-y-1.5">
          {/* Tipo + Plazo */}
          <div className="grid grid-cols-2 gap-1">
            <select value={formType} onChange={e => setFormType(e.target.value)} className="border border-black px-2 py-1 text-[10px] font-mono bg-white">
              <option value="CXC">📥 CXC — Por Cobrar</option>
              <option value="CXP">📤 CXP — Por Pagar</option>
            </select>
            <select value={formTerm} onChange={e => setFormTerm(e.target.value)} className="border border-black px-2 py-1 text-[10px] font-mono bg-white">
              <option value="Corto">Corto Plazo</option>
              <option value="Mediano">Mediano Plazo</option>
              <option value="Largo">Largo Plazo</option>
            </select>
          </div>

          {/* Tercero: búsqueda */}
          <div>
            <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">
              {formType === 'CXC' ? '¿A quién le vas a cobrar?' : '¿A quién le tienes que pagar?'}
            </label>
            {selectedTpId ? (
              <div className="flex items-center justify-between border border-black px-2 py-1 bg-white">
                <span className="text-[10px] font-bold font-mono">{selectedTpLabel}</span>
                <button onClick={() => { setSelectedTpId(''); setSelectedTpLabel(''); setTpSearch(''); }}
                  className="text-[9px] text-gray-400 hover:text-red-500 font-bold">✕</button>
              </div>
            ) : (
              <>
                <input type="text" value={tpSearch} onChange={e => setTpSearch(e.target.value)}
                  placeholder="🔍 Buscar tercero..." autoComplete="off"
                  className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen bg-white" />
                {tpSearch.length >= 1 && (
                  <div className="border border-t-0 border-black bg-white max-h-28 overflow-y-auto z-10 relative">
                    {filteredTps.length === 0 ? (
                      <div className="px-2 py-1 text-[10px] text-gray-400 font-mono italic">Sin resultados</div>
                    ) : filteredTps.map(tp => (
                      <div key={tp.id} onClick={() => {
                        setSelectedTpId(String(tp.id));
                        setSelectedTpLabel(`${tp.name} · ${tp.identification_type} ${tp.identification_number}`);
                        setTpSearch('');
                      }} className="px-2 py-1 text-[10px] font-mono hover:bg-brutalGreen cursor-pointer border-b border-gray-100 flex justify-between">
                        <span className="font-bold">{tp.name}</span>
                        <span className="text-gray-400">{tp.identification_type} {tp.identification_number}</span>
                      </div>
                    ))}
                    <div onClick={() => { setShowTpCreate(true); setTpSearch(''); }}
                      className="px-2 py-1 text-[10px] font-mono hover:bg-black hover:text-white cursor-pointer font-bold text-center border-t border-black">
                      + Crear nuevo tercero
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Crear tercero inline */}
          {showTpCreate && (
            <div className="border border-black p-2 bg-white space-y-1">
              <div className="text-[8px] font-bold uppercase font-mono text-gray-500">Nuevo Tercero</div>
              <input type="text" value={newTpName} onChange={e => setNewTpName(e.target.value)} placeholder="Nombre / Razón Social"
                className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" autoFocus />
              <div className="grid grid-cols-3 gap-1">
                <select value={newTpIdType} onChange={e => setNewTpIdType(e.target.value)} className="border border-black px-1 py-1 text-[10px] font-mono">
                  <option value="NIT">NIT</option><option value="CC">CC</option><option value="CE">CE</option>
                </select>
                <input type="text" value={newTpIdNum} onChange={e => setNewTpIdNum(e.target.value)} placeholder="Número"
                  className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                <input type="email" value={newTpEmail} onChange={e => setNewTpEmail(e.target.value)} placeholder="Email"
                  className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
              </div>
              <div className="flex gap-1">
                <button onClick={handleCreateTp} className="flex-1 bg-black text-white border border-black px-2 py-1 text-[9px] font-bold hover:bg-brutalGreen hover:text-black">Crear y Seleccionar</button>
                <button onClick={() => setShowTpCreate(false)} className="border border-black px-2 py-1 text-[9px] font-bold hover:bg-brutalBg">Cancelar</button>
              </div>
            </div>
          )}

          {/* Fechas: Inicio → Vencimiento */}
          <div className="grid grid-cols-2 gap-1">
            <div>
              <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">📅 Fecha Inicio</label>
              <input type="date" value={formStartDate} onChange={e => setFormStartDate(e.target.value)}
                className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none bg-white" />
            </div>
            <div>
              <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">🏁 Fecha Vencimiento</label>
              <input type="date" value={formDue} onChange={e => setFormDue(e.target.value)}
                className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none bg-white" />
            </div>
          </div>

          {/* Frecuencia de corte */}
          <div>
            <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">🔄 Frecuencia de Corte</label>
            <div className="flex gap-0.5">
              {[{v:'15',l:'C/15d'},{v:'20',l:'C/20d'},{v:'30',l:'C/30d'},{v:'custom',l:'✏️'}].map(opt => (
                <button key={opt.v} type="button"
                  onClick={() => setFormFrequency(opt.v)}
                  className={`flex-1 py-1 text-[9px] font-mono font-bold border border-black transition-all ${
                    formFrequency === opt.v ? 'bg-black text-white' : 'bg-white text-black hover:bg-brutalNeutral'
                  }`}>{opt.l}</button>
              ))}
            </div>
            {formFrequency === 'custom' && (
              <input type="number" value={formFreqCustom} onChange={e => setFormFreqCustom(e.target.value)}
                placeholder="Días entre cortes (ej: 7, 10, 45)"
                className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none bg-white mt-0.5" />
            )}
          </div>

          {formStartDate && formDue && new Date(formDue) > new Date(formStartDate) && (() => {
            const plazo = Math.round((new Date(formDue) - new Date(formStartDate)) / 86400000);
            const freq = formFrequency === 'custom' ? (parseInt(formFreqCustom) || 30) : parseInt(formFrequency);
            const cortes = Math.floor(plazo / freq);
            return (
              <div className="text-[8px] font-mono text-gray-400 text-right flex justify-between">
                <span>📅 {cortes} cortes cada {freq}d</span>
                <span>Plazo: {plazo} días</span>
              </div>
            );
          })()}

          {/* Importe total */}
          <div>
            <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">Importe Total</label>
            <input type="number" value={formAmount} onChange={e => setFormAmount(e.target.value)} placeholder="$0"
              className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none bg-white text-right" />
          </div>

          {/* Abono inicial + Saldo */}
          <div className="grid grid-cols-2 gap-1">
            <div>
              <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">Abono Inicial</label>
              <input type="number" value={formPartial} onChange={e => setFormPartial(e.target.value)} placeholder="$0"
                className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none bg-white text-right" />
            </div>
            <div>
              <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">Saldo Pendiente</label>
              <div className={`border-2 px-2 py-1 text-[10px] font-bold font-mono text-right ${saldo > 0 ? 'border-black bg-red-50 text-red-700' : 'border-green-500 bg-green-50 text-green-700'}`}>
                ${saldo.toLocaleString()}
              </div>
            </div>
          </div>

          {/* 👁️ Toggle Ver Asiento (Zero-COA) */}
          {formAmount && parseFloat(formAmount) > 0 && (
            <div style={{marginBottom: 6}}>
              <button
                type="button"
                onClick={async () => {
                  const next = !showAsiento;
                  setShowAsiento(next);
                  if (next) {
                    try {
                      const cat = formType === 'CXC' ? '__CXC_CREATE__' : '__CXP_CREATE__';
                      const r = await fetch(`${API_BASE}/posting-rules/preview?category=${encodeURIComponent(cat)}&tx_type=${formType}&amount=${parseFloat(formAmount)}`);
                      if (r.ok) setAsientoPreview(await r.json());
                    } catch(e) { setAsientoPreview(null); }
                  }
                }}
                className="w-full text-[9px] font-mono font-bold py-1 border border-dashed border-gray-400 hover:border-black hover:bg-gray-50 transition-all"
                style={{letterSpacing: '0.05em'}}
              >
                {showAsiento ? '🔽 Ocultar Asiento' : '👁️ Ver Asiento Contable'}
              </button>
              {showAsiento && asientoPreview?.found && (
                <div className="border-2 border-black p-2 mt-1" style={{background: '#FFFBE6'}}>
                  <div className="text-[8px] font-mono font-bold mb-1 uppercase" style={{color:'#666'}}>⚖️ Preview Partida Doble — {asientoPreview.rule_name}</div>
                  <table className="w-full text-[9px] font-mono" style={{borderCollapse:'collapse'}}>
                    <thead>
                      <tr style={{borderBottom:'2px solid #000'}}>
                        <th className="text-left py-0.5">Cuenta</th>
                        <th className="text-right py-0.5">Debe</th>
                        <th className="text-right py-0.5">Haber</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr style={{borderBottom:'1px solid #ddd'}}>
                        <td className="py-0.5 font-bold">{asientoPreview.debit.cuenta_codigo}</td>
                        <td className="text-right py-0.5" style={{color:'#c00'}}>${parseFloat(asientoPreview.debit.monto || 0).toLocaleString()}</td>
                        <td className="text-right py-0.5">—</td>
                      </tr>
                      <tr>
                        <td className="py-0.5 font-bold">{asientoPreview.credit.cuenta_codigo}</td>
                        <td className="text-right py-0.5">—</td>
                        <td className="text-right py-0.5" style={{color:'#060'}}>${parseFloat(asientoPreview.credit.monto || 0).toLocaleString()}</td>
                      </tr>
                    </tbody>
                  </table>
                  <div className="text-[7px] font-mono mt-1" style={{color:'#888'}}>{asientoPreview.description}</div>
                  <div className="text-[7px] font-mono font-bold mt-0.5" style={{color: asientoPreview.balanced ? '#090' : '#c00'}}>
                    {asientoPreview.balanced ? '✅ Cuadrado (Débito = Crédito)' : '❌ Descuadrado'}
                  </div>
                </div>
              )}
              {showAsiento && !asientoPreview?.found && (
                <div className="border border-dashed border-gray-300 p-2 mt-1 text-[8px] font-mono text-gray-500">
                  ⚠️ Sin regla contable para este tipo. El asiento se configurará después.
                </div>
              )}
            </div>
          )}

          <button onClick={handleSaveCartera} disabled={saving || !selectedTpId || !formDue || !formAmount}
            className="w-full bg-black text-white border border-black py-1.5 text-[10px] font-bold uppercase hover:bg-brutalGreen hover:text-black disabled:opacity-40 disabled:cursor-not-allowed transition-all">
            {saving ? 'Guardando...' : `Guardar ${formType} en Cartera`}
          </button>
        </div>
      )}
    </div>
  );
}
