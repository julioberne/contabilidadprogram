/* ============================================================
   TransactionDraftProvider.jsx — Fuente única de verdad del
   borrador de transacción (Módulo 01).

   Port VERBATIM de hooks/useTransactionForm.js (v1): mismos
   nombres de estado y handlers, entregados por Context en vez
   de ~80 props (estándar v2). Absorbe además el estado `drafts`
   de voz que en v1 vivía en App.jsx.

   Mantiene compatibilidad con la superficie v2 previa:
   thirdParty (objeto), setThirdParty, updateThirdParty,
   submitTransaction, resetDraft, isSubmitting.

   Debe montarse DENTRO de <EmpresaProvider> (consume accounts,
   activePortfolio y fetchAll de ahí).
   ============================================================ */
import { createContext, useContext, useState, useEffect } from 'react';
import { API } from '../../config';
import { useEmpresa } from './EmpresaProvider.jsx';
import { buildTransactionPayload, deriveAccountState } from './buildTransactionPayload.js';

const API_BASE_URL = API;

const TransactionDraftContext = createContext(null);

export function TransactionDraftProvider({ children }) {
  const empresa = useEmpresa();
  const { activePortfolio, accounts, fetchAll: fetchData } = empresa;

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
  const [thirdPartyId, setThirdPartyId] = useState(null); // vínculo 🔗 desde TercerosPanel
  const [isThirdPartyModalOpen, setIsThirdPartyModalOpen] = useState(false);

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

  // --- Borradores de voz (en v1 vivían en App.jsx) ---
  const [drafts, setDrafts] = useState([]);

  const [isSubmitting, setIsSubmitting] = useState(false);

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
  const { sourceAcc, destAcc, isCrossCurrency } = deriveAccountState({
    accounts, selectedAccountId, selectedDestAccountId, formType, txCurrency,
  });

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
    } catch {
      alert("❌ Error de conexión al subir comprobante.");
    } finally {
      setIsUploadingEvidence(false);
    }
  };

  // --- Resetear formulario (verbatim de useTransactionForm) ---
  const resetForm = () => {
    setAmount("");
    setConcept("");
    setThirdPartyNumber("");
    setThirdPartyName("");
    setThirdPartyEmail("");
    setThirdPartyPhone("");
    setThirdPartyWebsite("");
    setThirdPartyId(null);
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

  // --- Núcleo del registro (compartido por handleRegister y submitTransaction) ---
  const registerTransaction = async (portfolioName) => {
    if (!amount || !concept) {
      alert("❌ Error: Los campos Importe y Concepto son obligatorios.");
      return false;
    }
    const payload = buildTransactionPayload({
      activePortfolio: portfolioName,
      accounts,
      formType, amount, concept, date, geoMapsLink, paymentMethod, category,
      selectedAccountId, selectedDestAccountId, trmValue, txCurrency,
      thirdPartyType, thirdPartyNumber, thirdPartyName,
      thirdPartyEmail, thirdPartyPhone, thirdPartyWebsite,
      applyIva, applyGmf, applyPropina,
      isRecurring, recurrenceInterval, recurrenceDays, recurrenceMaxReps,
      recurrenceStartDate, recurrenceEndDate,
      cxcCxpEnabled, cxcCxpType, cxcCxpDueDate, cxcCxpTerm, cxcCxpValue,
      assetEnabled, assetName, assetValue, assetTag,
      assetVincularImporte, assetEstablecerActivo, assetRecurrente,
      evidenceFilePath, selectedTags, customTaxesList,
    });

    setIsSubmitting(true);
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
        return true;
      } else {
        const errorDetail = typeof data.detail === 'object' ? JSON.stringify(data.detail) : data.detail;
        alert(`❌ Error del servidor: ${errorDetail}`);
        return false;
      }
    } catch {
      alert("❌ Error al conectar con el servidor.");
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- Envío Manual del Formulario (firma v1: recibe el evento) ---
  const handleRegister = async (e) => {
    e.preventDefault();
    await registerTransaction(activePortfolio);
  };

  // --- Compat v2: envío programático que retorna boolean ---
  const submitTransaction = async (portfolioOverride) => {
    return registerTransaction(portfolioOverride || activePortfolio);
  };

  // --- Auto-llenar formulario desde Borrador de IA (verbatim) ---
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

  // --- Compat v2: tercero como objeto ---
  const thirdParty = {
    id: thirdPartyId,
    identification_type: thirdPartyType,
    identification_number: thirdPartyNumber,
    name: thirdPartyName,
    email: thirdPartyEmail,
    phone: thirdPartyPhone,
    website: thirdPartyWebsite,
  };

  const setThirdParty = (tp) => {
    setThirdPartyId(tp?.id ?? null);
    setThirdPartyType(tp?.identification_type || "NIT");
    setThirdPartyNumber(tp?.identification_number || "");
    setThirdPartyName(tp?.name || "");
    setThirdPartyEmail(tp?.email || "");
    setThirdPartyPhone(tp?.phone || "");
    setThirdPartyWebsite(tp?.website || "");
  };

  const updateThirdParty = (field, value) => {
    const setters = {
      identification_type: setThirdPartyType,
      identification_number: setThirdPartyNumber,
      name: setThirdPartyName,
      email: setThirdPartyEmail,
      phone: setThirdPartyPhone,
      website: setThirdPartyWebsite,
    };
    setters[field]?.(value);
  };

  const contextValue = {
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
    // Terceros (granular v1)
    thirdPartyType, setThirdPartyType,
    thirdPartyNumber, setThirdPartyNumber,
    thirdPartyName, setThirdPartyName,
    thirdPartyEmail, setThirdPartyEmail,
    thirdPartyPhone, setThirdPartyPhone,
    thirdPartyWebsite, setThirdPartyWebsite,
    isThirdPartyModalOpen, setIsThirdPartyModalOpen,
    // Terceros (compat v2: objeto + helpers)
    thirdParty, setThirdParty, updateThirdParty,
    // Lista de terceros (proxy del EmpresaProvider)
    allThirdParties: empresa.allThirdParties,
    setAllThirdParties: empresa.setAllThirdParties,
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
    isUploadingEvidence, setIsUploadingEvidence,
    // Tags
    selectedTags, setSelectedTags,
    tagSearch, setTagSearch,
    // Tasas
    customTaxesList, setCustomTaxesList,
    // Sugerencia IA
    formSuggestion, setFormSuggestion,
    // Borradores de voz
    drafts, setDrafts,
    // Handlers
    handleUploadEvidence,
    handleRegister,
    loadDraftIntoForm,
    resetForm,
    // Compat v2
    resetDraft: resetForm,
    submitTransaction,
    isSubmitting,
  };

  return (
    <TransactionDraftContext.Provider value={contextValue}>
      {children}
    </TransactionDraftContext.Provider>
  );
}

export function useTransactionDraft() {
  const context = useContext(TransactionDraftContext);
  if (!context) {
    throw new Error('useTransactionDraft must be used within a TransactionDraftProvider');
  }
  return context;
}
