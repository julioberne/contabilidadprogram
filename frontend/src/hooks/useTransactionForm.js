/* ============================================================
   useTransactionForm.js — Estados y lógica del formulario de
   registro de transacciones (Módulo 01).
   Extraído de App.jsx: estados del formulario, terceros,
   impuestos, cartera, activos, evidencia, y handleRegister.
   ============================================================ */
import { useState, useEffect } from 'react';
import { API } from '../config';

const API_BASE_URL = API;

export default function useTransactionForm({ activePortfolio, accounts, fetchData, setDrafts }) {
  // --- Tipo y campos principales ---
  const [formType, setFormType] = useState("GASTO");
  const [amount, setAmount] = useState("");
  const [concept, setConcept] = useState("");
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [geoMapsLink, setGeoMapsLink] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("Efectivo");
  const [category, setCategory] = useState("Ventas");

  // --- Cuenta origen / destino + TRM ---
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [selectedDestAccountId, setSelectedDestAccountId] = useState("");
  const [trmValue, setTrmValue] = useState("1.0");
  const [txCurrency, setTxCurrency] = useState("COP");

  // --- Terceros ---
  const [thirdPartyType, setThirdPartyType] = useState("NIT");
  const [thirdPartyNumber, setThirdPartyNumber] = useState("");
  const [thirdPartyName, setThirdPartyName] = useState("");
  const [thirdPartyEmail, setThirdPartyEmail] = useState("");
  const [thirdPartyPhone, setThirdPartyPhone] = useState("");
  const [thirdPartyWebsite, setThirdPartyWebsite] = useState("");
  const [isThirdPartyModalOpen, setIsThirdPartyModalOpen] = useState(false);
  const [allThirdParties, setAllThirdParties] = useState([]);

  // --- Impuestos ---
  const [applyIva, setApplyIva] = useState(false);
  const [applyGmf, setApplyGmf] = useState(false);
  const [applyPropina, setApplyPropina] = useState(false);
  const [isRecurring, setIsRecurring] = useState(false);
  const [recurrenceInterval, setRecurrenceInterval] = useState("MENSUAL");
  const [recurrenceDays, setRecurrenceDays] = useState(30);
  const [recurrenceMaxReps, setRecurrenceMaxReps] = useState("");
  const [recurrenceStartDate, setRecurrenceStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [recurrenceEndDate, setRecurrenceEndDate] = useState("");

  // --- Cartera (CXC / CXP) ---
  const [cxcCxpEnabled, setCxcCxpEnabled] = useState(false);
  const [cxcCxpType, setCxcCxpType] = useState("CXC");
  const [cxcCxpDueDate, setCxcCxpDueDate] = useState("");
  const [cxcCxpTerm, setCxcCxpTerm] = useState("Corto");
  const [cxcCxpValue, setCxcCxpValue] = useState("");

  // --- Gestión de Activos ---
  const [assetEnabled, setAssetEnabled] = useState(false);
  const [assetName, setAssetName] = useState("");
  const [assetValue, setAssetValue] = useState("");
  const [assetTag, setAssetTag] = useState("");
  const [assetVincularImporte, setAssetVincularImporte] = useState(false);
  const [assetEstablecerActivo, setAssetEstablecerActivo] = useState(false);
  const [assetRecurrente, setAssetRecurrente] = useState(false);
  const [evidenceFilePath, setEvidenceFilePath] = useState("");
  const [isUploadingEvidence, setIsUploadingEvidence] = useState(false);

  // --- Etiquetas / Tags ---
  const [selectedTags, setSelectedTags] = useState([]);
  const [tagSearch, setTagSearch] = useState("");

  // --- Tasas Personalizadas ---
  const [customTaxesList, setCustomTaxesList] = useState([]);

  // --- Sugerencia de formulario (IA) ---
  const [formSuggestion, setFormSuggestion] = useState(null);

  // --- Sincronizar valor del activo con importe ---
  useEffect(() => {
    if (assetVincularImporte) {
      setAssetValue(amount);
    }
  }, [amount, assetVincularImporte]);

  // --- Inicializar Cuenta al cargar cuentas ---
  useEffect(() => {
    if (accounts.length > 0) {
      const exists = accounts.some(a => String(a.id) === selectedAccountId);
      if (!selectedAccountId || !exists) {
        setSelectedAccountId(String(accounts[0].id));
        setTxCurrency(accounts[0].currency);
      }
    }
  }, [accounts, selectedAccountId]);

  const handleAccountChange = (accId) => {
    setSelectedAccountId(accId);
    const acc = accounts.find(a => String(a.id) === accId);
    if (acc) {
      setTxCurrency(acc.currency);
    }
  };

  // --- Derivados ---
  const sourceAcc = accounts.find(a => String(a.id) === selectedAccountId);
  const destAcc = accounts.find(a => String(a.id) === selectedDestAccountId);
  const isCrossCurrency =
    formType === "TRANSFERENCIA"
      ? (sourceAcc && destAcc && sourceAcc.currency !== destAcc.currency)
      : (sourceAcc && txCurrency !== sourceAcc.currency);

  // --- Subir Archivo de Evidencia ---
  const handleUploadEvidence = async (file) => {
    if (!file) return;
    setIsUploadingEvidence(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE_URL}/upload-evidence`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setEvidenceFilePath(data.file_path);
      } else {
        alert("❌ Error al subir comprobante");
      }
    } catch (error) {
      alert("❌ Error de conexión al subir comprobante.");
    } finally {
      setIsUploadingEvidence(false);
    }
  };

  // --- Resetear formulario ---
  const resetForm = () => {
    setAmount("");
    setConcept("");
    setThirdPartyNumber("");
    setThirdPartyName("");
    setThirdPartyEmail("");
    setThirdPartyPhone("");
    setThirdPartyWebsite("");
    setApplyIva(false);
    setApplyGmf(false);
    setApplyPropina(false);
    setIsRecurring(false);
    setFormSuggestion(null);
    setGeoMapsLink("");
    setTrmValue("1.0");
    setSelectedDestAccountId("");
    setCxcCxpEnabled(false);
    setCxcCxpDueDate("");
    setCxcCxpValue("");
    setAssetEnabled(false);
    setAssetName("");
    setAssetValue("");
    setAssetTag("");
    setAssetVincularImporte(false);
    setAssetEstablecerActivo(false);
    setAssetRecurrente(false);
    setEvidenceFilePath("");
    setSelectedTags([]);
  };

  // --- Envío Manual del Formulario ---
  const handleRegister = async (e) => {
    e.preventDefault();
    if (!amount || !concept) {
      alert("❌ Error: Los campos Importe y Concepto son obligatorios.");
      return;
    }
    const finalThirdPartyNumber = thirdPartyNumber || "999999999";
    const finalThirdPartyName = thirdPartyName || "Sin especificar";

    const customTaxesPayload = [];
    if (applyPropina) {
      customTaxesPayload.push({ name: "Propina (10%)", rate: 0.10, type: "ADDITIVE" });
    }
    customTaxesList.forEach(tax => {
      if (tax.checked) {
        customTaxesPayload.push({ name: tax.name, rate: tax.rate / 100, type: tax.type });
      }
    });

    const payload = {
      portfolio_name: activePortfolio,
      type: formType,
      amount: parseFloat(amount),
      concept,
      payment_method: sourceAcc ? sourceAcc.name : paymentMethod,
      category,
      third_party: {
        identification_type: thirdPartyType,
        identification_number: finalThirdPartyNumber,
        name: finalThirdPartyName,
        email: thirdPartyEmail || null,
        phone: thirdPartyPhone || null,
        website: thirdPartyWebsite || null
      },
      transaction_date: date,
      apply_iva: applyIva,
      apply_gmf: applyGmf,
      account_id: selectedAccountId ? parseInt(selectedAccountId) : null,
      dest_account_id: formType === "TRANSFERENCIA" && selectedDestAccountId ? parseInt(selectedDestAccountId) : null,
      trm: isCrossCurrency ? parseFloat(trmValue) : 1.0,
      transaction_currency: txCurrency,
      is_recurring: isRecurring,
      recurrence_interval: isRecurring ? recurrenceInterval : null,
      recurrence_days: isRecurring && recurrenceInterval === "PERSONALIZADO" ? parseInt(recurrenceDays) || 30 : null,
      recurrence_max_reps: isRecurring && recurrenceMaxReps ? parseInt(recurrenceMaxReps) : null,
      recurrence_start_date: isRecurring ? recurrenceStartDate : null,
      recurrence_end_date: isRecurring && recurrenceEndDate ? recurrenceEndDate : null,
      custom_taxes: customTaxesPayload.length > 0 ? customTaxesPayload : null,
      cxc_cxp: cxcCxpEnabled ? {
        type: cxcCxpType,
        due_date: cxcCxpDueDate,
        term: cxcCxpTerm,
        partial_value: cxcCxpValue ? parseFloat(cxcCxpValue) : null
      } : null,
      asset: assetEnabled && assetEstablecerActivo ? {
        name: assetName,
        purchase_value: assetVincularImporte ? parseFloat(amount || 0) : parseFloat(assetValue || 0),
        custom_tag: assetTag || null,
        establish_as_asset: assetEstablecerActivo,
        is_passive_income_generator: assetRecurrente,
        recurrence_interval_days: 30,
        recurrence_amount: assetVincularImporte ? parseFloat(amount || 0) : parseFloat(assetValue || 0)
      } : null,
      evidence_file_path: evidenceFilePath || null,
      geo_maps_link: geoMapsLink || null,
      tags: selectedTags.length > 0 ? selectedTags : null
    };

    try {
      const res = await fetch(`${API_BASE_URL}/transactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        const savedConcept = concept;
        resetForm();
        fetchData();
        setDrafts(prev => prev.filter(d => d.concept !== savedConcept));
      } else {
        const errorDetail = typeof data.detail === 'object' ? JSON.stringify(data.detail) : data.detail;
        alert(`❌ Error del servidor: ${errorDetail}`);
      }
    } catch (error) {
      alert("❌ Error al conectar con el servidor.");
    }
  };

  // --- Auto-llenar formulario desde Borrador de IA ---
  const loadDraftIntoForm = (draft) => {
    const p = draft.parsed_data;
    const cleanStr = (val, defaultVal = "") => {
      if (!val || val === "null" || val === "None" || val === "undefined") return defaultVal;
      return val.trim();
    };

    setFormType(p.type || "GASTO");
    setAmount(p.amount || "");
    setConcept(cleanStr(p.concept));
    setPaymentMethod(cleanStr(p.payment_method, "Efectivo"));
    setCategory(cleanStr(p.category, "Ventas"));

    if (p.third_party) {
      setThirdPartyType(cleanStr(p.third_party.identification_type, "NIT"));
      setThirdPartyNumber(cleanStr(p.third_party.identification_number));
      setThirdPartyName(cleanStr(p.third_party.name));
    }

    setApplyIva(draft.calculation_results?.tax_iva_amount > 0);
    setApplyGmf(draft.calculation_results?.tax_gmf_amount > 0);
    setIsRecurring(p.is_recurring || false);

    // Inferencia de campos faltantes
    const missing = [];
    const checkAmount = parseFloat(p.amount);
    if (!p.amount || isNaN(checkAmount) || checkAmount <= 0) missing.push("Importe/Valor");
    if (!cleanStr(p.payment_method)) missing.push("Método de Pago");
    if (!cleanStr(p.category)) missing.push("Categoría");
    const cleanThirdName = p.third_party ? cleanStr(p.third_party.name) : "";
    if (!cleanThirdName) missing.push("Nombre de Tercero");
    const cleanThirdId = p.third_party ? cleanStr(p.third_party.identification_number) : "";
    if (!cleanThirdId) missing.push("Identificación (NIT/CC)");

    setFormSuggestion(missing.length > 0 ? { fields: missing } : null);
  };

  return {
    // Tipo y campos principales
    formType, setFormType,
    amount, setAmount,
    concept, setConcept,
    date, setDate,
    geoMapsLink, setGeoMapsLink,
    paymentMethod, setPaymentMethod,
    category, setCategory,
    // Cuenta origen/destino + TRM
    selectedAccountId, setSelectedAccountId,
    selectedDestAccountId, setSelectedDestAccountId,
    trmValue, setTrmValue,
    txCurrency, setTxCurrency,
    handleAccountChange,
    sourceAcc, destAcc, isCrossCurrency,
    // Terceros
    thirdPartyType, setThirdPartyType,
    thirdPartyNumber, setThirdPartyNumber,
    thirdPartyName, setThirdPartyName,
    thirdPartyEmail, setThirdPartyEmail,
    thirdPartyPhone, setThirdPartyPhone,
    thirdPartyWebsite, setThirdPartyWebsite,
    isThirdPartyModalOpen, setIsThirdPartyModalOpen,
    allThirdParties, setAllThirdParties,
    // Impuestos + recurrencia
    applyIva, setApplyIva,
    applyGmf, setApplyGmf,
    applyPropina, setApplyPropina,
    isRecurring, setIsRecurring,
    recurrenceInterval, setRecurrenceInterval,
    recurrenceDays, setRecurrenceDays,
    recurrenceMaxReps, setRecurrenceMaxReps,
    recurrenceStartDate, setRecurrenceStartDate,
    recurrenceEndDate, setRecurrenceEndDate,
    // Cartera
    cxcCxpEnabled, setCxcCxpEnabled,
    cxcCxpType, setCxcCxpType,
    cxcCxpDueDate, setCxcCxpDueDate,
    cxcCxpTerm, setCxcCxpTerm,
    cxcCxpValue, setCxcCxpValue,
    // Activos
    assetEnabled, setAssetEnabled,
    assetName, setAssetName,
    assetValue, setAssetValue,
    assetTag, setAssetTag,
    assetVincularImporte, setAssetVincularImporte,
    assetEstablecerActivo, setAssetEstablecerActivo,
    assetRecurrente, setAssetRecurrente,
    evidenceFilePath, setEvidenceFilePath,
    isUploadingEvidence,
    // Tags
    selectedTags, setSelectedTags,
    tagSearch, setTagSearch,
    // Tasas
    customTaxesList, setCustomTaxesList,
    // Sugerencia IA
    formSuggestion, setFormSuggestion,
    // Handlers
    handleUploadEvidence,
    handleRegister,
    loadDraftIntoForm,
  };
}
