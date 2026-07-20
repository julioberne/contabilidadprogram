import { createContext, useContext, useState, useCallback } from 'react';
import { API } from '../../config';

const TransactionDraftContext = createContext(null);

export function TransactionDraftProvider({ children }) {
  // --- Core Fields ---
  const [formType, setFormType] = useState('GASTO'); // INGRESO, GASTO, TRANSFERENCIA
  const [amount, setAmount] = useState('');
  const [concept, setConcept] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [geoMapsLink, setGeoMapsLink] = useState('');
  
  // --- Account & Currency ---
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [txCurrency, setTxCurrency] = useState('COP');
  const [trmValue, setTrmValue] = useState('1.0');
  
  // --- Categorization ---
  const [category, setCategory] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('Efectivo');
  
  // --- Third Party (Injected from ContextPanel) ---
  const [thirdParty, setThirdParty] = useState({
    identification_type: 'NIT',
    identification_number: '',
    name: '',
    email: '',
    phone: '',
    website: ''
  });

  // --- Evidence ---
  const [evidenceFilePath, setEvidenceFilePath] = useState('');
  const [isUploadingEvidence, setIsUploadingEvidence] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);

  // --- Helpers ---
  const resetDraft = useCallback(() => {
    setAmount('');
    setConcept('');
    setGeoMapsLink('');
    setThirdParty({
      identification_type: 'NIT',
      identification_number: '',
      name: '',
      email: '',
      phone: '',
      website: ''
    });
    setEvidenceFilePath('');
    setTrmValue('1.0');
  }, []);

  const updateThirdParty = useCallback((field, value) => {
    setThirdParty(prev => ({ ...prev, [field]: value }));
  }, []);

  const submitTransaction = useCallback(async (activePortfolio) => {
    if (!amount || !concept) {
      alert("❌ Error: Los campos Importe y Concepto son obligatorios.");
      return false;
    }
    
    setIsSubmitting(true);
    const payload = {
      portfolio_name: activePortfolio,
      type: formType,
      amount: parseFloat(amount),
      concept,
      payment_method: paymentMethod,
      category: category || 'Sin Categoría',
      third_party: {
        identification_type: thirdParty.identification_type || 'NIT',
        identification_number: thirdParty.identification_number || '999999999',
        name: thirdParty.name || 'Sin especificar',
        email: thirdParty.email || null,
        phone: thirdParty.phone || null,
        website: thirdParty.website || null
      },
      transaction_date: date,
      account_id: selectedAccountId ? parseInt(selectedAccountId) : null,
      transaction_currency: txCurrency,
      trm: parseFloat(trmValue),
      evidence_file_path: evidenceFilePath || null,
      geo_maps_link: geoMapsLink || null,
    };

    try {
      const res = await fetch(`${API}/transactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        resetDraft();
        return true; // Success
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
  }, [amount, concept, formType, paymentMethod, category, thirdParty, date, selectedAccountId, txCurrency, trmValue, evidenceFilePath, geoMapsLink, resetDraft]);

  const contextValue = {
    formType, setFormType,
    amount, setAmount,
    concept, setConcept,
    date, setDate,
    geoMapsLink, setGeoMapsLink,
    selectedAccountId, setSelectedAccountId,
    txCurrency, setTxCurrency,
    trmValue, setTrmValue,
    category, setCategory,
    paymentMethod, setPaymentMethod,
    thirdParty, setThirdParty,
    updateThirdParty,
    evidenceFilePath, setEvidenceFilePath,
    isUploadingEvidence, setIsUploadingEvidence,
    resetDraft, submitTransaction, isSubmitting
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
