/* ============================================================
   buildTransactionPayload.js — Construcción PURA del payload
   de POST /transactions.
   Port VERBATIM de handleRegister en hooks/useTransactionForm.js
   (v1, líneas 167-233). Extraído como función pura para poder
   testearlo contra fixtures del comportamiento v1.
   NO tocar la semántica sin actualizar los tests.
   ============================================================ */

/**
 * Deriva cuenta origen/destino y si la TX es cross-currency.
 * Semántica exacta de useTransactionForm.js:104-109.
 */
export function deriveAccountState({ accounts, selectedAccountId, selectedDestAccountId, formType, txCurrency }) {
  const sourceAcc = accounts.find(a => String(a.id) === selectedAccountId);
  const destAcc = accounts.find(a => String(a.id) === selectedDestAccountId);
  const isCrossCurrency =
    formType === "TRANSFERENCIA"
      ? (sourceAcc && destAcc && sourceAcc.currency !== destAcc.currency)
      : (sourceAcc && txCurrency !== sourceAcc.currency);
  return { sourceAcc, destAcc, isCrossCurrency };
}

/**
 * Construye el payload completo de una transacción.
 * Asume que la validación (amount/concept obligatorios) ya ocurrió.
 * @param {object} s — estado plano del formulario + activePortfolio + accounts
 */
export function buildTransactionPayload(s) {
  const { sourceAcc, isCrossCurrency } = deriveAccountState(s);

  const finalThirdPartyNumber = s.thirdPartyNumber || "999999999";
  const finalThirdPartyName = s.thirdPartyName || "Sin especificar";

  const customTaxesPayload = [];
  if (s.applyPropina) {
    customTaxesPayload.push({ name: "Propina (10%)", rate: 0.10, type: "ADDITIVE" });
  }
  s.customTaxesList.forEach(tax => {
    if (tax.checked) {
      customTaxesPayload.push({ name: tax.name, rate: tax.rate / 100, type: tax.type });
    }
  });

  return {
    portfolio_name: s.activePortfolio,
    type: s.formType,
    amount: parseFloat(s.amount),
    concept: s.concept,
    payment_method: sourceAcc ? sourceAcc.name : s.paymentMethod,
    category: s.category,
    third_party: {
      identification_type: s.thirdPartyType,
      identification_number: finalThirdPartyNumber,
      name: finalThirdPartyName,
      email: s.thirdPartyEmail || null,
      phone: s.thirdPartyPhone || null,
      website: s.thirdPartyWebsite || null
    },
    transaction_date: s.date,
    apply_iva: s.applyIva,
    apply_gmf: s.applyGmf,
    account_id: s.selectedAccountId ? parseInt(s.selectedAccountId) : null,
    dest_account_id: s.formType === "TRANSFERENCIA" && s.selectedDestAccountId ? parseInt(s.selectedDestAccountId) : null,
    trm: isCrossCurrency ? parseFloat(s.trmValue) : 1.0,
    transaction_currency: s.txCurrency,
    is_recurring: s.isRecurring,
    recurrence_interval: s.isRecurring ? s.recurrenceInterval : null,
    recurrence_days: s.isRecurring && s.recurrenceInterval === "PERSONALIZADO" ? parseInt(s.recurrenceDays) || 30 : null,
    recurrence_max_reps: s.isRecurring && s.recurrenceMaxReps ? parseInt(s.recurrenceMaxReps) : null,
    recurrence_start_date: s.isRecurring ? s.recurrenceStartDate : null,
    recurrence_end_date: s.isRecurring && s.recurrenceEndDate ? s.recurrenceEndDate : null,
    custom_taxes: customTaxesPayload.length > 0 ? customTaxesPayload : null,
    cxc_cxp: s.cxcCxpEnabled ? {
      type: s.cxcCxpType,
      due_date: s.cxcCxpDueDate,
      term: s.cxcCxpTerm,
      partial_value: s.cxcCxpValue ? parseFloat(s.cxcCxpValue) : null
    } : null,
    asset: s.assetEnabled && s.assetEstablecerActivo ? {
      name: s.assetName,
      purchase_value: s.assetVincularImporte ? parseFloat(s.amount || 0) : parseFloat(s.assetValue || 0),
      custom_tag: s.assetTag || null,
      establish_as_asset: s.assetEstablecerActivo,
      is_passive_income_generator: s.assetRecurrente,
      recurrence_interval_days: 30,
      recurrence_amount: s.assetVincularImporte ? parseFloat(s.amount || 0) : parseFloat(s.assetValue || 0)
    } : null,
    evidence_file_path: s.evidenceFilePath || null,
    geo_maps_link: s.geoMapsLink || null,
    tags: s.selectedTags.length > 0 ? s.selectedTags : null
  };
}
