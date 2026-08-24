/* ============================================================
   RegistroModule.jsx — Adapter del Módulo 01 (Registro Contable)
   Monta el TransactionForm de v1 VERBATIM (import transitorio
   desde components/) mapeando el contexto (draft + empresa) a
   las props que el form espera. La paridad de UI es por
   construcción: el componente es el archivo v1 real.
   El import transitorio se vuelve interno en la Fase 7 (mudanza).
   ============================================================ */
import { useState, useEffect } from 'react';
import TransactionForm from './TransactionForm.jsx';
import useCalculator from '../../hooks/useCalculator.js';
import { API } from '../../../config';
import { useEmpresa } from '../../engine/EmpresaProvider.jsx';
import { useTransactionDraft } from '../../engine/TransactionDraftProvider.jsx';

const API_BASE_URL = API;

export default function RegistroModule() {
  const empresa = useEmpresa();
  const draft = useTransactionDraft();

  // Calculadora rápida (hook v1 — TransactionForm espera su API exacta)
  const calc = useCalculator();

  // Estados de búsqueda del COA (en v1 vivían en App.jsx)
  const [coaSearchQuery, setCoaSearchQuery] = useState("");
  const [isCoaSearchFocused, setIsCoaSearchFocused] = useState(false);

  // --- Cargar plantilla COA (port verbatim de App.jsx) ---
  const handleLoadCoaTemplate = async (templateName) => {
    try {
      const res = await fetch(`${API_BASE_URL}/coa/template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio_name: empresa.activePortfolio, template_name: templateName })
      });
      const data = await res.json();
      if (res.ok && data.status === "CARGADO") {
        empresa.fetchAll();
      } else {
        alert(data.detail || "Error cargando plantilla COA");
      }
    } catch (e) {
      console.error("Error loading template:", e);
    }
  };

  // El selector COA se retiró del Módulo 01 (irá en el módulo de contadores);
  // la categoría ahora es un select simple alineado con posting_rules, así que
  // ya no se normaliza contra el COA.

  return (
    <TransactionForm
      calcOpen={calc.calcOpen} setCalcOpen={calc.setCalcOpen}
      calcDisplay={calc.calcDisplay} setCalcDisplay={calc.setCalcDisplay}
      calcPrev={calc.calcPrev} setCalcPrev={calc.setCalcPrev}
      calcOp={calc.calcOp} setCalcOp={calc.setCalcOp}
      calcReset={calc.calcReset} setCalcReset={calc.setCalcReset}
      setAmount={draft.setAmount}
      formType={draft.formType} setFormType={draft.setFormType}
      amount={draft.amount} concept={draft.concept} setConcept={draft.setConcept}
      date={draft.date} setDate={draft.setDate}
      geoMapsLink={draft.geoMapsLink} setGeoMapsLink={draft.setGeoMapsLink}
      paymentMethod={draft.paymentMethod} setPaymentMethod={draft.setPaymentMethod}
      category={draft.category} setCategory={draft.setCategory}
      selectedAccountId={draft.selectedAccountId} setSelectedAccountId={draft.setSelectedAccountId}
      selectedDestAccountId={draft.selectedDestAccountId} setSelectedDestAccountId={draft.setSelectedDestAccountId}
      trmValue={draft.trmValue} setTrmValue={draft.setTrmValue}
      txCurrency={draft.txCurrency} setTxCurrency={draft.setTxCurrency}
      handleAccountChange={draft.handleAccountChange}
      sourceAcc={draft.sourceAcc} destAcc={draft.destAcc} isCrossCurrency={draft.isCrossCurrency}
      isRecurring={draft.isRecurring} setIsRecurring={draft.setIsRecurring}
      recurrenceInterval={draft.recurrenceInterval} setRecurrenceInterval={draft.setRecurrenceInterval}
      recurrenceDays={draft.recurrenceDays} setRecurrenceDays={draft.setRecurrenceDays}
      recurrenceMaxReps={draft.recurrenceMaxReps} setRecurrenceMaxReps={draft.setRecurrenceMaxReps}
      recurrenceStartDate={draft.recurrenceStartDate} setRecurrenceStartDate={draft.setRecurrenceStartDate}
      recurrenceEndDate={draft.recurrenceEndDate} setRecurrenceEndDate={draft.setRecurrenceEndDate}
      evidenceFilePath={draft.evidenceFilePath} isUploadingEvidence={draft.isUploadingEvidence} handleUploadEvidence={draft.handleUploadEvidence}
      formSuggestion={draft.formSuggestion} setFormSuggestion={draft.setFormSuggestion}
      handleRegister={draft.handleRegister}
      coaFlatAccounts={empresa.coaFlatAccounts} coaSearchQuery={coaSearchQuery} setCoaSearchQuery={setCoaSearchQuery}
      isCoaSearchFocused={isCoaSearchFocused} setIsCoaSearchFocused={setIsCoaSearchFocused}
      handleLoadCoaTemplate={handleLoadCoaTemplate}
      accounts={empresa.accounts}
      activeCompany={empresa.activeCompany} activePortfolio={empresa.activePortfolio} fetchData={empresa.fetchAll}
    />
  );
}
