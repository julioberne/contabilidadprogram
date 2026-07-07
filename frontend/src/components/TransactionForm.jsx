// TransactionForm.jsx — Extracted from App.jsx (Lines 745-1217)
import React from 'react';
import CoaSelector from './CoaSelector';
import IndustryWidgets from './IndustryWidgets';

export default function TransactionForm({
  // Calculator state
  calcOpen, setCalcOpen,
  calcDisplay, setCalcDisplay,
  calcPrev, setCalcPrev,
  calcOp, setCalcOp,
  calcReset, setCalcReset,
  // Calculator actions — inline in original, passed as helpers
  setAmount,
  // Form state from useTransactionForm
  formType, setFormType,
  amount, concept, setConcept,
  date, setDate,
  geoMapsLink, setGeoMapsLink,
  paymentMethod, setPaymentMethod,
  category, setCategory,
  selectedAccountId, setSelectedAccountId,
  selectedDestAccountId, setSelectedDestAccountId,
  trmValue, setTrmValue,
  txCurrency, setTxCurrency,
  handleAccountChange,
  sourceAcc, destAcc, isCrossCurrency,
  // Recurrence
  isRecurring, setIsRecurring,
  recurrenceInterval, setRecurrenceInterval,
  recurrenceDays, setRecurrenceDays,
  recurrenceMaxReps, setRecurrenceMaxReps,
  recurrenceStartDate, setRecurrenceStartDate,
  recurrenceEndDate, setRecurrenceEndDate,
  // Evidence
  evidenceFilePath, isUploadingEvidence, handleUploadEvidence,
  // Form suggestion
  formSuggestion, setFormSuggestion,
  // Submit
  handleRegister,
  // COA
  coaFlatAccounts, coaSearchQuery, setCoaSearchQuery,
  isCoaSearchFocused, setIsCoaSearchFocused,
  handleLoadCoaTemplate,
  // Data
  accounts,
  // Industry widgets
  activeCompany, activePortfolio, fetchData,
}) {
  const renderCoaSelector = () => (
    <CoaSelector
      coaFlatAccounts={coaFlatAccounts}
      coaSearchQuery={coaSearchQuery}
      setCoaSearchQuery={setCoaSearchQuery}
      isCoaSearchFocused={isCoaSearchFocused}
      setIsCoaSearchFocused={setIsCoaSearchFocused}
      setCategory={setCategory}
      handleLoadCoaTemplate={handleLoadCoaTemplate}
    />
  );

  return (
          <div className="bg-white border-2 border-black p-2 shadow-brutal">
            <div className="flex justify-between items-center border-b-2 border-black pb-1 mb-2">
              <h2 className="text-sm font-bold uppercase">📝 Módulo 01: Registro Contable</h2>
              <button
                type="button"
                onClick={() => setCalcOpen(!calcOpen)}
                className={`px-2 py-0.5 text-[10px] font-bold uppercase border-2 border-black transition-all ${
                  calcOpen ? 'bg-brutalGreen text-black' : 'bg-black text-white hover:bg-brutalGreen hover:text-black'
                }`}
                title="Calculadora rápida"
              >
                🧮 CALC
              </button>
            </div>

            {/* ═══ CALCULADORA RÁPIDA EXPANDIBLE ═══ */}
            {calcOpen && (
              <div className="border-2 border-black bg-brutalBg p-2 mb-2 shadow-brutal">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-[9px] font-bold uppercase text-gray-400">Calculadora</span>
                  <button type="button" onClick={() => { setCalcDisplay("0"); setCalcPrev(null); setCalcOp(null); }} className="text-[9px] font-bold uppercase bg-brutalCrimson text-white border border-black px-1.5 py-0.5 hover:bg-black">CE</button>
                </div>
                <div className="bg-white border-2 border-black p-2 text-right text-sm font-bold font-mono mb-1 overflow-hidden">
                  {calcPrev !== null && <span className="text-[9px] text-gray-400 block">{calcPrev} {calcOp}</span>}
                  {calcDisplay}
                </div>
                <div className="grid grid-cols-4 gap-0.5">
                  {['7','8','9','÷','4','5','6','×','1','2','3','−','0','.','±','+'].map(btn => (
                    <button
                      key={btn}
                      type="button"
                      onClick={() => {
                        const ops = {'÷':'/','×':'*','−':'-','+':'+'};
                        if (ops[btn]) {
                          const curr = parseFloat(calcDisplay) || 0;
                          if (calcPrev !== null && calcOp) {
                            const r = calcOp === '+' ? calcPrev+curr : calcOp === '-' ? calcPrev-curr : calcOp === '*' ? calcPrev*curr : calcPrev/curr;
                            setCalcPrev(r); setCalcDisplay(String(r));
                          } else { setCalcPrev(curr); }
                          setCalcOp(ops[btn]); setCalcReset(true);
                        } else if (btn === '±') {
                          setCalcDisplay(d => String(parseFloat(d) * -1));
                        } else if (btn === '.') {
                          setCalcDisplay(d => d.includes('.') ? d : d + '.');
                        } else {
                          setCalcDisplay(d => (d === '0' || calcReset) ? btn : d + btn);
                          setCalcReset(false);
                        }
                      }}
                      className={`p-1.5 text-xs font-bold font-mono border border-black transition-all ${
                        '÷×−+'.includes(btn)
                          ? 'bg-brutalAmber text-black hover:bg-black hover:text-white'
                          : 'bg-white hover:bg-brutalNeutral'
                      }`}
                    >
                      {btn}
                    </button>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-0.5 mt-0.5">
                  <button
                    type="button"
                    onClick={() => {
                      if (calcPrev !== null && calcOp) {
                        const curr = parseFloat(calcDisplay) || 0;
                        const r = calcOp === '+' ? calcPrev+curr : calcOp === '-' ? calcPrev-curr : calcOp === '*' ? calcPrev*curr : calcPrev/curr;
                        setCalcDisplay(String(Math.round(r * 100) / 100));
                        setCalcPrev(null); setCalcOp(null); setCalcReset(true);
                      }
                    }}
                    className="p-1.5 text-xs font-bold font-mono border border-black bg-brutalGreen text-black hover:bg-black hover:text-white"
                  >=</button>
                  <button
                    type="button"
                    onClick={() => { setAmount(calcDisplay); setCalcOpen(false); }}
                    className="p-1.5 text-[9px] font-bold font-mono uppercase border border-black bg-black text-white hover:bg-brutalGreen hover:text-black"
                    title="Usar este resultado como importe"
                  >→ IMPORTE</button>
                </div>
              </div>
            )}
            
            <form onSubmit={handleRegister} className="space-y-2">
              
              {/* Sugerencia Informativa de Campos Faltantes */}
              {formSuggestion && (
                <div className="bg-brutalAmber border-2 border-black p-2 text-xs font-bold uppercase space-y-1">
                  <div className="flex justify-between items-start">
                    <span className="text-black">💡 CAMPOS FALTANTES EN AUDIO</span>
                    <button 
                      type="button" 
                      onClick={() => setFormSuggestion(null)}
                      className="bg-black text-white px-1.5 py-0.5 hover:bg-brutalCrimson text-[9px] font-bold border border-black"
                    >
                      OCULTAR [X]
                    </button>
                  </div>
                  <p className="leading-relaxed text-black normal-case font-mono font-medium">
                    Falta completar: <strong className="uppercase">{formSuggestion.fields.join(", ")}</strong> en lo capturado por audio. 
                    Puedes agregarlo en el formulario ahora, o dejarlo así y modificarlo luego desde el libro diario.
                  </p>
                </div>
              )}
              
              {/* Selector de Tipo (Triple Toggle) */}
              <div>
                <label className="text-xs font-bold uppercase block mb-1">Tipo de Registro</label>
                <div className="grid grid-cols-3 border-2 border-black p-0.5 bg-brutalBg">
                  {["INGRESO", "GASTO", "TRANSFERENCIA"].map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setFormType(t)}
                      className={`py-1.5 text-xs font-bold uppercase border-r last:border-r-0 border-black transition-all ${
                        formType === t 
                          ? t === "INGRESO" ? "bg-brutalGreen text-black font-extrabold" : t === "GASTO" ? "bg-brutalCrimson text-white font-extrabold" : "bg-black text-white" 
                          : "hover:bg-brutalNeutral"
                      }`}
                    >
                      {t.substring(0, 5)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Importe y Concepto */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs font-bold uppercase block mb-1">Importe ($)*</label>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    required
                    placeholder="Monto"
                    className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase block mb-1">Fecha*</label>
                  <input
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    required
                    className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold uppercase block mb-1">Concepto*</label>
                <input
                  type="text"
                  value={concept}
                  onChange={(e) => setConcept(e.target.value)}
                  required
                  placeholder="ej. Honorarios consultoría, Compra papelería"
                  className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                />
              </div>

              {/* Cuentas, Categoría y Conversión */}
              {formType === "TRANSFERENCIA" ? (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs font-bold uppercase block mb-1">Cuenta Origen*</label>
                      <select 
                        value={selectedAccountId}
                        onChange={(e) => handleAccountChange(e.target.value)}
                        className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none"
                        required
                      >
                        {accounts.map(acc => (
                          <option key={acc.id} value={acc.id}>{acc.name} ({acc.currency})</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-bold uppercase block mb-1">Cuenta Destino*</label>
                      <select 
                        value={selectedDestAccountId}
                        onChange={(e) => setSelectedDestAccountId(e.target.value)}
                        className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none"
                        required
                      >
                        <option value="">Seleccionar destino</option>
                        {accounts.filter(acc => String(acc.id) !== selectedAccountId).map(acc => (
                          <option key={acc.id} value={acc.id}>{acc.name} ({acc.currency})</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs font-bold uppercase block mb-1">Cuenta Contable (COA)</label>
                      {renderCoaSelector()}
                    </div>
                    <div className="flex flex-col justify-end">
                      <label className="flex items-center text-xs uppercase font-bold cursor-pointer pb-2.5">
                        <input 
                          type="checkbox"
                          checked={isRecurring}
                          onChange={(e) => setIsRecurring(e.target.checked)}
                          className="mr-2 h-4 w-4 border-2 border-black rounded-none outline-none accent-black" 
                        />
                        [{isRecurring ? "X" : " "}] VOLVER RECURRENTE
                      </label>
                      {isRecurring && (
                        <div className="mt-1 border-2 border-black p-2 bg-brutalBg space-y-2">
                          <label className="text-[10px] font-bold uppercase block mb-1">Frecuencia</label>
                          <select
                            value={recurrenceInterval}
                            onChange={(e) => {
                              setRecurrenceInterval(e.target.value);
                              if (e.target.value === "MENSUAL") setRecurrenceDays(30);
                              else if (e.target.value === "QUINCENAL") setRecurrenceDays(15);
                              else if (e.target.value === "SEMANAL") setRecurrenceDays(7);
                              else if (e.target.value === "DIARIO") setRecurrenceDays(1);
                              else if (e.target.value === "ANUAL") setRecurrenceDays(365);
                            }}
                            className="w-full bg-white border border-black p-1 text-xs font-mono outline-none"
                          >
                            <option value="MENSUAL">Mensual</option>
                            <option value="QUINCENAL">Quincenal</option>
                            <option value="SEMANAL">Semanal</option>
                            <option value="DIARIO">Diario</option>
                            <option value="ANUAL">Anual</option>
                            <option value="PERSONALIZADO">Personalizado (días)</option>
                          </select>
                          {recurrenceInterval === "PERSONALIZADO" && (
                            <div>
                              <label className="text-[9px] font-bold uppercase block mb-1 mt-1">Cada cuántos días*</label>
                              <input
                                type="number"
                                min="1"
                                value={recurrenceDays}
                                onChange={(e) => setRecurrenceDays(e.target.value)}
                                className="w-full bg-white border border-black p-1 text-xs font-mono outline-none"
                                required
                              />
                            </div>
                          )}
                          <div>
                            <label className="text-[9px] font-bold uppercase block mb-1 mt-1">Límite de Repeticiones (Opcional)</label>
                            <input
                              type="number"
                              min="1"
                              placeholder="Ej. 12"
                              value={recurrenceMaxReps}
                              onChange={(e) => setRecurrenceMaxReps(e.target.value)}
                              className="w-full bg-white border border-black p-1 text-xs font-mono outline-none"
                            />
                          </div>
                          <div>
                            <label className="text-[9px] font-bold uppercase block mb-1 mt-1">Fecha de Inicio*</label>
                            <input
                              type="date"
                              value={recurrenceStartDate}
                              onChange={(e) => setRecurrenceStartDate(e.target.value)}
                              className="w-full bg-white border border-black p-1 text-xs font-mono outline-none"
                              required={isRecurring}
                            />
                          </div>
                          <div>
                            <label className="text-[9px] font-bold uppercase block mb-1 mt-1">Fecha de Terminación (Opcional)</label>
                            <input
                              type="date"
                              value={recurrenceEndDate}
                              onChange={(e) => setRecurrenceEndDate(e.target.value)}
                              className="w-full bg-white border border-black p-1 text-xs font-mono outline-none"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs font-bold uppercase block mb-1">Cuenta*</label>
                      <select 
                        value={selectedAccountId}
                        onChange={(e) => handleAccountChange(e.target.value)}
                        className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none"
                        required
                      >
                        {accounts.map(acc => (
                          <option key={acc.id} value={acc.id}>{acc.name} ({acc.currency})</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs font-bold uppercase block mb-1">Cuenta Contable (COA)</label>
                      {renderCoaSelector()}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs font-bold uppercase block mb-1">Divisa Transacción</label>
                      <select 
                        value={txCurrency}
                        onChange={(e) => setTxCurrency(e.target.value)}
                        className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none"
                      >
                        <option value="COP">COP</option>
                        <option value="USD">USD</option>
                      </select>
                    </div>
                    <div className="flex flex-col justify-end">
                      <label className="flex items-center text-xs uppercase font-bold cursor-pointer pb-2.5">
                        <input 
                          type="checkbox"
                          checked={isRecurring}
                          onChange={(e) => setIsRecurring(e.target.checked)}
                          className="mr-2 h-4 w-4 border-2 border-black rounded-none outline-none accent-black" 
                        />
                        [{isRecurring ? "X" : " "}] VOLVER RECURRENTE
                      </label>
                      {isRecurring && (
                        <div className="mt-1 border-2 border-black p-2 bg-brutalBg space-y-2">
                          <label className="text-[10px] font-bold uppercase block mb-1">Frecuencia</label>
                          <select
                            value={recurrenceInterval}
                            onChange={(e) => {
                              setRecurrenceInterval(e.target.value);
                              if (e.target.value === "MENSUAL") setRecurrenceDays(30);
                              else if (e.target.value === "QUINCENAL") setRecurrenceDays(15);
                              else if (e.target.value === "SEMANAL") setRecurrenceDays(7);
                              else if (e.target.value === "DIARIO") setRecurrenceDays(1);
                              else if (e.target.value === "ANUAL") setRecurrenceDays(365);
                            }}
                            className="w-full bg-white border border-black p-1 text-xs font-mono outline-none"
                          >
                            <option value="MENSUAL">Mensual</option>
                            <option value="QUINCENAL">Quincenal</option>
                            <option value="SEMANAL">Semanal</option>
                            <option value="DIARIO">Diario</option>
                            <option value="ANUAL">Anual</option>
                            <option value="PERSONALIZADO">Personalizado (días)</option>
                          </select>
                          {recurrenceInterval === "PERSONALIZADO" && (
                            <div>
                              <label className="text-[9px] font-bold uppercase block mb-1 mt-1">Cada cuántos días*</label>
                              <input
                                type="number"
                                min="1"
                                value={recurrenceDays}
                                onChange={(e) => setRecurrenceDays(e.target.value)}
                                className="w-full bg-white border border-black p-1 text-xs font-mono outline-none"
                                required
                              />
                            </div>
                          )}
                          <div>
                            <label className="text-[9px] font-bold uppercase block mb-1 mt-1">Límite de Repeticiones (Opcional)</label>
                            <input
                              type="number"
                              min="1"
                              placeholder="Ej. 12"
                              value={recurrenceMaxReps}
                              onChange={(e) => setRecurrenceMaxReps(e.target.value)}
                              className="w-full bg-white border border-black p-1 text-xs font-mono outline-none"
                            />
                          </div>
                          <div>
                            <label className="text-[9px] font-bold uppercase block mb-1 mt-1">Fecha de Inicio*</label>
                            <input
                              type="date"
                              value={recurrenceStartDate}
                              onChange={(e) => setRecurrenceStartDate(e.target.value)}
                              className="w-full bg-white border border-black p-1 text-xs font-mono outline-none"
                              required={isRecurring}
                            />
                          </div>
                          <div>
                            <label className="text-[9px] font-bold uppercase block mb-1 mt-1">Fecha de Terminación (Opcional)</label>
                            <input
                              type="date"
                              value={recurrenceEndDate}
                              onChange={(e) => setRecurrenceEndDate(e.target.value)}
                              className="w-full bg-white border border-black p-1 text-xs font-mono outline-none"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* TRM Manual si es Cross-Currency */}
              {isCrossCurrency && (
                <div className="border-2 border-black p-2 bg-brutalAmber space-y-1">
                  <label className="text-xs font-bold uppercase block mb-1 text-black font-mono">💹 TRM Manual Requerida*</label>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-black font-mono">1 USD =</span>
                    <input
                      type="number"
                      step="0.01"
                      value={trmValue}
                      onChange={(e) => setTrmValue(e.target.value)}
                      required
                      placeholder="ej. 4000"
                      className="flex-grow bg-white border border-black p-1 text-xs font-mono outline-none text-right font-bold focus:border-black"
                    />
                    <span className="text-xs font-bold text-black font-mono">COP</span>
                  </div>
                  <span className="text-[10px] text-black font-mono block mt-1">
                    Se requiere tasa de cambio manual para ejecutar la conversión multi-moneda.
                  </span>
                </div>
              )}

              {/* Ubicación / Geolocalización */}
              <div className="mt-2">
                <label className="text-[10px] font-bold uppercase block mb-1">📍 Ubicación (Google Maps Link)</label>
                <input
                  type="url"
                  value={geoMapsLink}
                  onChange={(e) => setGeoMapsLink(e.target.value)}
                  placeholder="https://maps.google.com/..."
                  className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                />
              </div>

              {/* ═══ Secciones colapsables movidas al ContextPanel (panel derecho) ═══ */}

              {/* Sección Evidencia / Subir Archivo - Integrada a Módulo 01 */}
              <div className="border-2 border-black p-2 bg-white space-y-1 shadow-brutal">
                <label className="text-[10px] font-bold uppercase block mb-1">EVIDENCIA / COMPROBANTE DE TRANSACCIÓN</label>
                <label className="flex flex-col items-center justify-center border-2 border-dashed border-black p-2 bg-gray-50 cursor-pointer hover:bg-brutalBg transition-all select-none">
                  <span className="text-xl mb-1">📷</span>
                  <span className="text-[10px] font-bold uppercase font-mono text-center">
                    {isUploadingEvidence 
                      ? "SUBIENDO..." 
                      : evidenceFilePath 
                        ? `✅ COMPROBANTE SUBIDO: ${evidenceFilePath.split('/').pop()}` 
                        : "SUBIR COMPROBANTE (JPG/PNG/PDF)"}
                  </span>
                  <input 
                    type="file" 
                    accept="image/*,application/pdf"
                    onChange={(e) => {
                      const file = e.target.files[0];
                      if (file) handleUploadEvidence(file);
                    }}
                    className="hidden" 
                  />
                </label>
              </div>

              {/* Registrar Botón */}
              <button
                type="submit"
                className="w-full bg-black text-brutalGreen hover:bg-brutalGreen hover:text-black border-3 border-black py-3 text-sm font-extrabold uppercase transition-all shadow-brutal hover:translate-y-0.5 active:translate-y-1"
              >
                REGISTRAR ✔
              </button>
            </form>

            {/* ── Widgets de Industria (Fase 3 — debajo del formulario) ── */}
            <IndustryWidgets
              activeCompany={activeCompany}
              activePortfolio={activePortfolio}
              onTransactionCreated={() => fetchData()}
            />
          </div>
  );
}
