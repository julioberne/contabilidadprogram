import React, { useState, useEffect, useRef } from 'react';
import ThirdPartyModal from './components/ThirdPartyModal';
import ContextPanel from './components/ContextPanel';

const API_BASE_URL = "http://127.0.0.1:8000/api";

function App() {
  // --- Estados Principales ---
  const [activePortfolio, setActivePortfolio] = useState("Negocio A");
  const [portfolios, setPortfolios] = useState([]);
  const [isNewPortfolioModalOpen, setIsNewPortfolioModalOpen] = useState(false);
  const [newPortfolioName, setNewPortfolioName] = useState("");
  const [newPortfolioIndustry, setNewPortfolioIndustry] = useState("ESTANDAR");
  const [newPortfolioSubIndustry, setNewPortfolioSubIndustry] = useState("");
  const [transactions, setTransactions] = useState([]);
  const [totalTxCount, setTotalTxCount] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const [drafts, setDrafts] = useState([]);
  const [cajaViva, setCajaViva] = useState({
    total_ingresos: 0.0,
    total_gastos: 0.0,
    balance_neto: 0.0,
    capital_inicial: 5000000.0,
    patrimonio: 5000000.0,
    status: "NOMINAL",
    alerts: [],
    total_ingresos_cop: 0.0,
    total_gastos_cop: 0.0,
    balance_neto_cop: 0.0,
    patrimonio_cop: 5000000.0,
    total_ingresos_usd: 0.0,
    total_gastos_usd: 0.0,
    balance_neto_usd: 0.0,
    patrimonio_usd: 1000.0
  });

  // --- Perfil del Usuario Principal ---
  const [profile, setProfile] = useState({
    name: "Andrés",
    email: "andres@finsys.os",
    role: "Administrador Contable",
    avatar_style: "pixel-grid"
  });
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [editProfileName, setEditProfileName] = useState("");
  const [editProfileEmail, setEditProfileEmail] = useState("");
  const [editProfileRole, setEditProfileRole] = useState("");
  const [editProfileAvatar, setEditProfileAvatar] = useState("pixel-grid");

  // --- Gestión de Cuentas Financieras ---
  const [accounts, setAccounts] = useState([]);
  const [newAccountName, setNewAccountName] = useState("");
  const [newAccountType, setNewAccountType] = useState("Ahorros");
  const [newAccountCurrency, setNewAccountCurrency] = useState("COP");
  const [newAccountInitialBalance, setNewAccountInitialBalance] = useState("");
  const [editingAccountId, setEditingAccountId] = useState(null);
  const [editAccountName, setEditAccountName] = useState("");
  const [editAccountType, setEditAccountType] = useState("Ahorros");
  const [editAccountBalance, setEditAccountBalance] = useState("");

  // --- Subsecciones del panel izquierdo ---
  const [activeLeftSection, setActiveLeftSection] = useState("registro");

  // --- Estado del Formulario de Registro (Módulo 01) ---
  const [formType, setFormType] = useState("GASTO"); // INGRESO, GASTO, TRANSFERENCIA
  const [amount, setAmount] = useState("");
  const [concept, setConcept] = useState("");
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [geoMapsLink, setGeoMapsLink] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("Efectivo");
  const [category, setCategory] = useState("Ventas");
  
  // Módulo de Cuentas y TRM
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [selectedDestAccountId, setSelectedDestAccountId] = useState("");
  const [trmValue, setTrmValue] = useState("1.0");
  const [txCurrency, setTxCurrency] = useState("COP");

  // Terceros
  const [thirdPartyType, setThirdPartyType] = useState("NIT");
  const [thirdPartyNumber, setThirdPartyNumber] = useState("");
  const [thirdPartyName, setThirdPartyName] = useState("");
  const [thirdPartyEmail, setThirdPartyEmail] = useState("");
  const [thirdPartyPhone, setThirdPartyPhone] = useState("");
  const [thirdPartyWebsite, setThirdPartyWebsite] = useState("");
  const [isThirdPartyModalOpen, setIsThirdPartyModalOpen] = useState(false);
  const [thirdPartySearch, setThirdPartySearch] = useState("");
  const [thirdPartyResults, setThirdPartyResults] = useState([]);
  const [allThirdParties, setAllThirdParties] = useState([]);

  // Impuestos
  const [applyIva, setApplyIva] = useState(false);
  const [applyGmf, setApplyGmf] = useState(false);
  const [applyPropina, setApplyPropina] = useState(false);
  const [isRecurring, setIsRecurring] = useState(false);
  const [recurrenceInterval, setRecurrenceInterval] = useState("MENSUAL");
  const [recurrenceDays, setRecurrenceDays] = useState(30);
  const [recurrenceMaxReps, setRecurrenceMaxReps] = useState("");
  const [recurrenceStartDate, setRecurrenceStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [recurrenceEndDate, setRecurrenceEndDate] = useState("");

  // --- Collapsible sections states (ahora en panel derecho) ---
  const [activeTab, setActiveTab] = useState('terceros');
  const [showVoiceWidget, setShowVoiceWidget] = useState(false);

  // --- Cartera (CXC / CXP) ---
  const [cxcCxpEnabled, setCxcCxpEnabled] = useState(false);
  const [cxcCxpType, setCxcCxpType] = useState("CXC"); // CXC, CXP
  const [cxcCxpDueDate, setCxcCxpDueDate] = useState("");
  const [cxcCxpTerm, setCxcCxpTerm] = useState("Corto"); // Corto, Mediano, Largo
  const [cxcCxpValue, setCxcCxpValue] = useState(""); // Valor parcial / abono

  // --- Fila expandible Libro Diario ---
  const [expandedTxId, setExpandedTxId] = useState(null);

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

  // --- Calculadora rápida ---
  const [calcOpen, setCalcOpen] = useState(false);
  const [calcDisplay, setCalcDisplay] = useState("0");
  const [calcPrev, setCalcPrev] = useState(null);
  const [calcOp, setCalcOp] = useState(null);
  const [calcReset, setCalcReset] = useState(false);

  // --- Etiquetas / Tags ---
  const DEFAULT_TAGS = ["Urgente", "Personal", "Empresa", "Recurrente", "Proyecto", "Fiscal"];
  const [availableTags, setAvailableTags] = useState(DEFAULT_TAGS);
  const [selectedTags, setSelectedTags] = useState([]);
  const [newTagInput, setNewTagInput] = useState("");
  const [editingTagIdx, setEditingTagIdx] = useState(null);
  const [editTagValue, setEditTagValue] = useState("");
  // expandedTags eliminado - ahora en ContextPanel
  const [tagSearch, setTagSearch] = useState("");

  // --- Administrador de Tasas Personalizadas ---
  const [customTaxesList, setCustomTaxesList] = useState([]); // array of { id, name, rate, type, checked }
  const [newTaxName, setNewTaxName] = useState("");
  const [newTaxRate, setNewTaxRate] = useState("");
  const [newTaxType, setNewTaxType] = useState("ADDITIVE"); // ADDITIVE, DEDUCTIVE
  const [isAddingTaxOpen, setIsAddingTaxOpen] = useState(false);

  // --- Estados del Grabador de Voz ---
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isStructuring, setIsStructuring] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [formSuggestion, setFormSuggestion] = useState(null);
  const [editingCell, setEditingCell] = useState(null); // { txId: number, field: string }
  const [editValue, setEditValue] = useState("");
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  // --- Estado del Modal de Comprobante ---
  const [evidenceUrl, setEvidenceUrl] = useState(null);
  const [selectedEvidenceTx, setSelectedEvidenceTx] = useState(null);

  // --- Estados del Catálogo de Cuentas (COA) ---
  const [coaTree, setCoaTree] = useState([]);
  const [coaFlatAccounts, setCoaFlatAccounts] = useState([]); // Aplanado y filtrado (solo is_group === false)
  const [isLoadingCoa, setIsLoadingCoa] = useState(false);
  const [isCoaSearchFocused, setIsCoaSearchFocused] = useState(false);
  const [coaSearchQuery, setCoaSearchQuery] = useState("");

  const flattenCoa = (nodes) => {
    let flat = [];
    const traverse = (node) => {
      flat.push(node);
      if (node.children && node.children.length > 0) {
        node.children.forEach(traverse);
      }
    };
    if (nodes && Array.isArray(nodes)) {
      nodes.forEach(traverse);
    }
    return flat;
  };

  const handleLoadCoaTemplate = async (templateName) => {
    try {
      const res = await fetch(`${API_BASE_URL}/coa/template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio_name: activePortfolio, template_name: templateName })
      });
      const data = await res.json();
      if (res.ok && data.status === "CARGADO") {
        fetchData();
      } else {
        alert(data.detail || "Error cargando plantilla COA");
      }
    } catch (e) {
      console.error("Error loading template:", e);
    }
  };

  // --- Auto-refresh cada 30s para mantener Balance/Patrimonio actualizados ---
  useEffect(() => {
    const interval = setInterval(() => { fetchData(); }, 30000);
    return () => clearInterval(interval);
  }, [activePortfolio]);

  // --- DT-12: Cargar más transacciones (paginación) ---
  const loadMoreTransactions = async () => {
    setLoadingMore(true);
    try {
      const offset = transactions.length;
      const portfolioParam = activePortfolio ? `&portfolio=${encodeURIComponent(activePortfolio)}` : '';
      const res = await fetch(
        `http://127.0.0.1:8000/api/transactions?limit=50&offset=${offset}${portfolioParam}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.items && data.items.length > 0) {
        setTransactions(prev => [...prev, ...data.items]);
        setTotalTxCount(data.total_count);
      }
    } catch (e) {
      console.error('Error loading more transactions:', e);
    } finally {
      setLoadingMore(false);
    }
  };

  // --- Cargar Balances y Transacciones (SOL-04A: endpoint consolidado) ---
  const fetchData = async () => {
    try {
      // SOL-04A: 1 solo request reemplaza 6 calls secuenciales
      const res = await fetch(
        `${API_BASE_URL}/dashboard-data?portfolio=${encodeURIComponent(activePortfolio)}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Portafolios
      if (data.portfolios) setPortfolios(data.portfolios);

      // Balance (Caja Viva)
      if (data.balance) {
        setCajaViva({
          total_ingresos: data.balance.total_ingresos,
          total_gastos: data.balance.total_gastos,
          balance_neto: data.balance.balance_neto,
          capital_inicial: data.balance.capital_inicial,
          patrimonio: data.balance.patrimonio,
          status: data.balance.status,
          alerts: data.balance.alerts,
          total_ingresos_cop: data.balance.total_ingresos_cop,
          total_gastos_cop: data.balance.total_gastos_cop,
          balance_neto_cop: data.balance.balance_neto_cop,
          patrimonio_cop: data.balance.patrimonio_cop,
          total_ingresos_usd: data.balance.total_ingresos_usd,
          total_gastos_usd: data.balance.total_gastos_usd,
          balance_neto_usd: data.balance.balance_neto_usd,
          patrimonio_usd: data.balance.patrimonio_usd
        });
      }

      // Transacciones (DT-12: paginadas, primeras 50)
      if (data.transactions) setTransactions(data.transactions);
      if (data.total_tx_count !== undefined) setTotalTxCount(data.total_tx_count);

      // Cuentas
      if (data.accounts) setAccounts(data.accounts);

      // Perfil
      if (data.profile) {
        setProfile(data.profile);
        setEditProfileName(data.profile.name);
        setEditProfileEmail(data.profile.email);
        setEditProfileRole(data.profile.role);
        setEditProfileAvatar(data.profile.avatar_style);
      }

      // COA (Catálogo de Cuentas)
      if (data.coa) {
        setIsLoadingCoa(true);
        try {
          if (data.coa.status === "OK") {
            setCoaTree(data.coa.data);
            const flat = flattenCoa(data.coa.data);
            const postable = flat.filter(acc => !acc.is_group);
            setCoaFlatAccounts(postable);

            if (postable.length > 0) {
              const matched = postable.find(acc => `${acc.code} - ${acc.name}` === category || acc.code === category);
              if (matched) {
                const fullVal = `${matched.code} - ${matched.name}`;
                setCategory(fullVal);
                setCoaSearchQuery(fullVal);
              } else {
                const defaultVal = `${postable[0].code} - ${postable[0].name}`;
                setCategory(defaultVal);
                setCoaSearchQuery(defaultVal);
              }
            } else {
              setCoaSearchQuery("");
            }
          }
        } catch (coaErr) {
          console.error("Error procesando COA:", coaErr);
        } finally {
          setIsLoadingCoa(false);
        }
      }

      // Terceros (para búsqueda inline)
      try {
        const tpRes = await fetch(`${API_BASE_URL}/third-parties`);
        if (tpRes.ok) {
          const tpData = await tpRes.json();
          setAllThirdParties(tpData);
        }
      } catch (tpErr) {
        console.error("Error cargando terceros:", tpErr);
      }
    } catch (error) {
      console.error("⚠️ Error al conectar con el servidor backend:", error);
    }
  };

  // --- Inicializar Cuenta Pago al cargar cuentas ---
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

  const renderCoaSelector = () => {
    if (coaFlatAccounts.length === 0) {
      return (
        <div className="border-2 border-black p-2 bg-brutalAmber text-xs font-bold uppercase space-y-1">
          <p className="text-black font-mono">⚠️ No hay Catálogo de Cuentas (COA) en este portafolio.</p>
          <div className="flex flex-wrap gap-1">
            <button 
              type="button"
              onClick={() => handleLoadCoaTemplate("ESTANDAR")}
              className="bg-black text-white px-2 py-1 border border-black hover:bg-white hover:text-black text-[10px] font-bold tracking-wider uppercase transition-all"
            >
              Cargar ESTÁNDAR
            </button>
            <button 
              type="button"
              onClick={() => handleLoadCoaTemplate("INMOBILIARIA")}
              className="bg-black text-white px-2 py-1 border border-black hover:bg-white hover:text-black text-[10px] font-bold tracking-wider uppercase transition-all"
            >
              Cargar INMOBILIARIA
            </button>
            <button 
              type="button"
              onClick={() => handleLoadCoaTemplate("CONSTRUCTORA")}
              className="bg-black text-white px-2 py-1 border border-black hover:bg-white hover:text-black text-[10px] font-bold tracking-wider uppercase transition-all"
            >
              Cargar CONSTRUCTORA
            </button>
          </div>
        </div>
      );
    }

    const filtered = coaFlatAccounts.filter(acc => 
      acc.code.toLowerCase().includes(coaSearchQuery.toLowerCase()) || 
      acc.name.toLowerCase().includes(coaSearchQuery.toLowerCase())
    );

    return (
      <div className="relative">
        <input
          type="text"
          placeholder="Buscar cuenta COA (ej. 110505)..."
          value={coaSearchQuery}
          onChange={(e) => {
            setCoaSearchQuery(e.target.value);
            setCategory(e.target.value); // El payload enviará el query actual
          }}
          onFocus={() => setIsCoaSearchFocused(true)}
          onBlur={() => {
            // Retraso para que haga efecto el click de la lista antes de que se oculte
            setTimeout(() => setIsCoaSearchFocused(false), 200);
          }}
          className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
        />
        {isCoaSearchFocused && (
          <div className="absolute left-0 right-0 top-full mt-1 bg-white border-2 border-black shadow-brutal max-h-60 overflow-y-auto z-50">
            {filtered.length === 0 ? (
              <div className="p-2 text-xs text-gray-500 font-mono uppercase bg-gray-50">Sin resultados contables. Se guardará "{coaSearchQuery}".</div>
            ) : (
              filtered.map((acc) => (
                <button
                  key={acc.id}
                  type="button"
                  onClick={() => {
                    const val = `${acc.code} - ${acc.name}`;
                    setCategory(val);
                    setCoaSearchQuery(val);
                    setIsCoaSearchFocused(false);
                  }}
                  className="w-full text-left p-2 text-xs font-mono hover:bg-brutalGreen hover:text-black border-b border-gray-100 block truncate"
                >
                  <span className="font-bold text-blue-600 mr-2">{acc.code}</span>
                  <span>{acc.name}</span>
                  <span className="float-right text-[9px] bg-gray-100 text-gray-600 px-1 border border-gray-300 uppercase font-bold">{acc.account_type}</span>
                </button>
              ))
            )}
          </div>
        )}
      </div>
    );
  };

  const sourceAcc = accounts.find(a => String(a.id) === selectedAccountId);
  const destAcc = accounts.find(a => String(a.id) === selectedDestAccountId);
  const isCrossCurrency = 
    formType === "TRANSFERENCIA" 
      ? (sourceAcc && destAcc && sourceAcc.currency !== destAcc.currency)
      : (sourceAcc && txCurrency !== sourceAcc.currency);

  // Sincronizar el valor del activo con el importe de la transacción si está vinculado
  useEffect(() => {
    if (assetVincularImporte) {
      setAssetValue(amount);
    }
  }, [amount, assetVincularImporte]);

  useEffect(() => {
    fetchData();
  }, [activePortfolio]);

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

  // --- Envío Manual del Formulario ---
  const handleRegister = async (e) => {
    e.preventDefault();
    if (!amount || !concept) {
      alert("❌ Error: Los campos Importe y Concepto son obligatorios.");
      return;
    }
    // Si no se ingresa tercero, usar valores por defecto
    const finalThirdPartyNumber = thirdPartyNumber || "999999999";
    const finalThirdPartyName = thirdPartyName || "Sin especificar";

    const customTaxesPayload = [];
    if (applyPropina) {
      customTaxesPayload.push({
        name: "Propina (10%)",
        rate: 0.10,
        type: "ADDITIVE"
      });
    }
    customTaxesList.forEach(tax => {
      if (tax.checked) {
        customTaxesPayload.push({
          name: tax.name,
          rate: tax.rate / 100,
          type: tax.type
        });
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
        // Limpiar formulario y recargar datos
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
        
        // Reset Cartera / Activos
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
        
        fetchData();
        
        // Si la transacción venía de un borrador, removerlo
        setDrafts(prev => prev.filter(d => d.concept !== concept));
      } else {
        const errorDetail = typeof data.detail === 'object' ? JSON.stringify(data.detail) : data.detail;
        alert(`❌ Error del servidor: ${errorDetail}`);
      }
    } catch (error) {
      alert("❌ Error al conectar con el servidor.");
    }
  };

  // --- Actualizar Perfil de Usuario ---
  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE_URL}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editProfileName,
          email: editProfileEmail,
          role: editProfileRole,
          avatar_style: editProfileAvatar
        })
      });
      if (res.ok) {
        setIsEditingProfile(false);
        fetchData();
      } else {
        alert("❌ Error al actualizar el perfil.");
      }
    } catch (error) {
      alert("❌ Error al conectar con el servidor.");
    }
  };

  // --- Crear Nueva Cuenta ---
  const handleCreateAccount = async (e) => {
    e.preventDefault();
    if (!newAccountName) {
      alert("❌ Nombre de cuenta es obligatorio.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/accounts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newAccountName,
          type: newAccountType,
          currency: newAccountCurrency,
          initial_balance: parseFloat(newAccountInitialBalance || "0.0")
        })
      });
      if (res.ok) {
        setNewAccountName("");
        setNewAccountInitialBalance("");
        fetchData();
      } else {
        const errData = await res.json();
        alert(`❌ Error al crear cuenta: ${errData.detail}`);
      }
    } catch (error) {
      alert("❌ Error al conectar con el servidor.");
    }
  };

  const handleUpdateAccount = async (accountId) => {
    if (!editAccountName.trim()) { alert("❌ El nombre no puede estar vacío."); return; }
    try {
      const res = await fetch(`${API_BASE_URL}/accounts/${accountId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: editAccountName, type: editAccountType, current_balance: parseFloat(editAccountBalance) || 0 })
      });
      if (res.ok) { setEditingAccountId(null); fetchData(); }
      else { const d = await res.json(); alert(`❌ ${d.detail}`); }
    } catch { alert("❌ Error al conectar con el servidor."); }
  };

  const handleDeleteAccount = async (accountId, accountName) => {
    if (!window.confirm(`¿Eliminar la cuenta "${accountName}"?\nLas transacciones vinculadas quedarán sin cuenta asignada.`)) return;
    try {
      const res = await fetch(`${API_BASE_URL}/accounts/${accountId}`, { method: "DELETE" });
      if (res.ok) { fetchData(); }
      else { const d = await res.json(); alert(`❌ ${d.detail}`); }
    } catch { alert("❌ Error al conectar con el servidor."); }
  };

  // --- Crear Nuevo Portafolio ---
  const handleCreatePortfolio = async (e) => {
    e.preventDefault();
    if (!newPortfolioName) {
      alert("❌ El nombre de la empresa es obligatorio.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/portfolios`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newPortfolioName,
          industry_type: newPortfolioIndustry,
          sub_industry_type: newPortfolioSubIndustry
        })
      });
      if (res.ok) {
        setNewPortfolioName("");
        setNewPortfolioIndustry("ESTANDAR");
        setNewPortfolioSubIndustry("");
        setIsNewPortfolioModalOpen(false);
        setActivePortfolio(newPortfolioName);
        fetchData();
      } else {
        const errData = await res.json();
        alert(`❌ Error al crear empresa: ${errData.detail}`);
      }
    } catch (error) {
      alert("❌ Error de red al crear empresa.");
    }
  };

  // --- Renderizador de Avatar Retro-Brutalista ---
  const renderPixelAvatar = (name) => {
    const hash = name ? name.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0) : 42;
    return (
      <div className="w-16 h-16 border-3 border-black bg-brutalGreen flex-shrink-0 flex flex-wrap p-1 gap-0.5">
        {[...Array(16)].map((_, i) => {
          const fill = (hash >> i) & 1;
          return (
            <div key={i} className={`w-3 h-3 border border-black ${fill ? "bg-black" : "bg-white"}`} />
          );
        })}
      </div>
    );
  };

  // --- Lógica del Grabador de Voz ---
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      
      // Intentar usar un tipo MIME robusto compatible
      let options = { mimeType: 'audio/webm;codecs=opus' };
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options = { mimeType: 'audio/webm' };
      }
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options = { mimeType: 'audio/ogg;codecs=opus' };
      }
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options = {}; // Dejar que el navegador elija por defecto
      }
      
      mediaRecorderRef.current = new MediaRecorder(stream, options);
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const mimeTypeUsed = mediaRecorderRef.current.mimeType || 'audio/webm';
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeTypeUsed });
        
        // Evitar enviar audios vacíos (menos de 1000 bytes)
        if (audioBlob.size < 1000) {
          alert("⚠️ Grabación demasiado corta o vacía. Asegúrate de hablar claramente frente al micrófono.");
        } else {
          await handleTranscribeAudio(audioBlob);
        }
        stream.getTracks().forEach(track => track.stop());
      };

      // Iniciar grabación con timeslice de 250ms para emitir tramas de audio continuamente
      mediaRecorderRef.current.start(250);
      setIsRecording(true);
      setRecordingDuration(0);
      timerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);
    } catch (err) {
      alert("❌ Error al acceder al micrófono. Asegúrate de otorgar los permisos necesarios.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      clearInterval(timerRef.current);
    }
  };

  const handleTranscribeAudio = async (audioBlob) => {
    setIsTranscribing(true);
    // NOTA: No limpiamos el liveTranscript anterior para permitir concatenar múltiples grabaciones consecutivas.
    const formData = new FormData();
    formData.append("audio_file", audioBlob, "grabacion.webm");

    try {
      const res = await fetch(`${API_BASE_URL}/transactions/transcribe`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      
      if (res.ok && data.transcript) {
        setLiveTranscript(prev => {
          const newText = data.transcript.trim();
          if (!prev) return newText;
          const separator = prev.endsWith(" ") ? "" : " ";
          return prev + separator + newText;
        });
      } else {
        const errorMsg = data?.detail || "Error al transcribir.";
        alert(`⚠️ No se pudo transcribir el audio. Detalle: ${errorMsg}`);
      }
    } catch (error) {
      alert("❌ Error al conectar con el servidor para transcribir.");
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleStructureTranscript = async () => {
    if (!liveTranscript.trim()) {
      alert("⚠️ Escribe o graba algo de texto antes de procesar.");
      return;
    }
    
    setIsStructuring(true);
    try {
      const res = await fetch(`${API_BASE_URL}/transactions/structure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript: liveTranscript,
          portfolio_name: activePortfolio
        })
      });
      const data = await res.json();
      
      if (res.ok && data.status === "BORRADOR") {
        setDrafts(prev => [data, ...prev]);
        setLiveTranscript(""); // Limpiar la consola de transcripción tras un procesado exitoso
      } else {
        const errorDetail = typeof data.detail === 'object' ? JSON.stringify(data.detail) : data.detail;
        alert(`⚠️ No se pudo estructurar el texto. Detalle: ${errorDetail || "Verifica tu API Key."}`);
      }
    } catch (error) {
      alert("❌ Error al estructurar el texto en el servidor.");
    } finally {
      setIsStructuring(false);
    }
  };

  // --- Auto-llenar formulario al hacer clic en un Borrador ---
  const loadDraftIntoForm = (draft) => {
    const p = draft.parsed_data;
    
    // Función auxiliar para limpiar cadenas "null", "None" o vacías devueltas por la IA
    const cleanStr = (val, defaultVal = "") => {
      if (!val || val === "null" || val === "None" || val === "undefined") {
        return defaultVal;
      }
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
    
    // Inferencia de checks de impuestos
    setApplyIva(draft.calculation_results?.tax_iva_amount > 0);
    setApplyGmf(draft.calculation_results?.tax_gmf_amount > 0);
    setIsRecurring(p.is_recurring || false);

    // --- Inferencia de campos faltantes para sugerencia informativa ---
    const missing = [];
    const checkAmount = parseFloat(p.amount);
    if (!p.amount || isNaN(checkAmount) || checkAmount <= 0) {
      missing.push("Importe/Valor");
    }
    const cleanPay = cleanStr(p.payment_method);
    if (!cleanPay) {
      missing.push("Método de Pago");
    }
    const cleanCat = cleanStr(p.category);
    if (!cleanCat) {
      missing.push("Categoría");
    }
    const cleanThirdName = p.third_party ? cleanStr(p.third_party.name) : "";
    if (!cleanThirdName) {
      missing.push("Nombre de Tercero");
    }
    const cleanThirdId = p.third_party ? cleanStr(p.third_party.identification_number) : "";
    if (!cleanThirdId) {
      missing.push("Identificación (NIT/CC)");
    }

    if (missing.length > 0) {
      setFormSuggestion({
        fields: missing
      });
    } else {
      setFormSuggestion(null);
    }
  };

  // --- Lógica de Edición Excel-like Inline ---
  const startEditing = (txId, field, currentValue) => {
    setEditingCell({ txId, field });
    setEditValue(currentValue !== null && currentValue !== undefined ? String(currentValue) : "");
  };

  const saveInlineEdit = async (txId, field) => {
    if (!editingCell) return;

    let valueToSave = editValue;
    if (field === "net_value" || field === "amount") {
      valueToSave = parseFloat(editValue);
      if (isNaN(valueToSave)) valueToSave = 0.0;
    }

    const payload = {
      [field]: valueToSave
    };

    try {
      const res = await fetch(`${API_BASE_URL}/transactions/${txId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setEditingCell(null);
        fetchData();
      } else {
        const data = await res.json();
        alert(`❌ Error al actualizar: ${data.detail}`);
      }
    } catch (error) {
      alert("❌ Error al conectar con el servidor.");
    }
  };
  
  const toggleRecurrence = async (txId, currentVal) => {
    try {
      const res = await fetch(`${API_BASE_URL}/transactions/${txId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_recurring: !currentVal })
      });
      if (res.ok) {
        fetchData();
      } else {
        const data = await res.json();
        alert(`❌ Error al cambiar recurrencia: ${data.detail}`);
      }
    } catch (error) {
      console.error("Error toggling recurrence:", error);
    }
  };

  const handleSeedSynthetic = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/transactions/seed_synthetic?portfolio=${activePortfolio}`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok) {
        alert("✅ Datos sintéticos creados con éxito. Se indujo un estado de insolvencia para probar alertas.");
        fetchData();
      } else {
        alert(`❌ Error al semillar datos: ${data.detail}`);
      }
    } catch (error) {
      alert("❌ Error de red al semillar datos.");
    }
  };

  const handleResetDatabase = async () => {
    if (!window.confirm("⚠️ ¿Estás seguro de que deseas reiniciar todos los valores contables, perfiles y cuentas a sus valores iniciales? Esta acción no se puede deshacer.")) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/transactions/reset`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok) {
        alert("✅ Base de datos contable y cuentas reiniciadas con éxito.");
        fetchData();
      } else {
        alert(`❌ Error al reiniciar base de datos: ${data.detail}`);
      }
    } catch (error) {
      alert("❌ Error de red al reiniciar base de datos.");
    }
  };


  return (
    <div className="min-h-screen bg-brutalBg text-black font-mono p-2 flex flex-col antialiased selection:bg-brutalGreen">
      
      {/* ============================================================================== */}
      {/* 🏛️ BARRA DE PORTAFOLIOS — compacta, sin duplicar el título del shell */}
      {/* ============================================================================== */}
      <header className="border-2 border-black bg-white px-2 py-1 mb-2 shadow-brutal flex items-center justify-between flex-wrap gap-1">
        {/* Selector de portafolio */}
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-[10px] font-bold uppercase text-gray-400 mr-1 tracking-widest">Portafolio:</span>
          {portfolios.map((port) => (
            <button
              key={port.id}
              onClick={() => setActivePortfolio(port.name)}
              className={`px-2 py-0.5 text-[10px] font-bold uppercase transition-all border ${
                activePortfolio === port.name
                  ? "bg-black text-white border-black"
                  : "border-gray-300 hover:border-black hover:bg-brutalNeutral"
              }`}
              type="button"
              title={`${port.name} (${port.industry_type})`}
            >
              {port.name.substring(0, 14)}
            </button>
          ))}
          <button
            onClick={() => setIsNewPortfolioModalOpen(true)}
            className="px-2 py-0.5 text-[10px] font-bold uppercase bg-brutalGreen border border-black text-black hover:bg-black hover:text-white transition-all"
            type="button"
          >+ Empresa</button>
        </div>
        {/* Acciones rápidas + estado */}
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 border ${
            cajaViva.status === 'NOMINAL' ? 'bg-brutalGreen border-black text-black' :
            cajaViva.status === 'INSOLVENTE' ? 'bg-brutalCrimson border-black text-white animate-pulse' :
            'bg-brutalAmber border-black text-black'
          }`}>{cajaViva.status || 'CARGANDO'}</span>
          <button onClick={handleSeedSynthetic} className="px-2 py-0.5 text-[10px] font-bold uppercase bg-brutalAmber border border-black text-black hover:bg-black hover:text-white transition-all" type="button" title="Datos sintéticos">⚡ Semillar</button>
          <button onClick={handleResetDatabase} className="px-2 py-0.5 text-[10px] font-bold uppercase bg-brutalCrimson border border-black text-white hover:bg-black transition-all" type="button" title="Reiniciar BD">⚠️ Reiniciar</button>
        </div>
      </header>

      {/* Modal de Nueva Empresa */}
      {isNewPortfolioModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white border-4 border-black p-2 shadow-brutal max-w-sm w-full">
            <h2 className="text-xl font-bold uppercase mb-2 border-b-2 border-black pb-2">🏢 Agregar Empresa</h2>
            <form onSubmit={handleCreatePortfolio} className="space-y-2">
              <div>
                <label className="text-xs font-bold uppercase block mb-1">Nombre de Empresa</label>
                <input
                  type="text"
                  value={newPortfolioName}
                  onChange={(e) => setNewPortfolioName(e.target.value)}
                  placeholder="ej. Jardín Infantil Sol"
                  required
                  className="w-full bg-white border-2 border-black p-2 text-sm font-mono outline-none focus:border-brutalGreen"
                />
              </div>
              <div>
                <label className="text-xs font-bold uppercase block mb-1">Sector de Negocio</label>
                <select
                  value={newPortfolioIndustry}
                  onChange={(e) => setNewPortfolioIndustry(e.target.value)}
                  className="w-full bg-white border-2 border-black p-2 text-sm font-mono outline-none focus:border-brutalGreen"
                >
                  <option value="ESTANDAR">Estándar (General)</option>
                  <option value="INMOBILIARIA">Inmobiliaria / Bienes Raíces</option>
                  <option value="CONSTRUCTORA">Constructora</option>
                  <option value="ECOMMERCE">E-commerce / Retail</option>
                  <option value="JARDIN">Jardín Infantil / Educativo</option>
                </select>
                <p className="text-[10px] text-gray-500 mt-1 uppercase leading-tight">
                  Al crear, el sistema inicializará automáticamente el catálogo de cuentas (COA) específico de este sector en la base de datos.
                </p>
              </div>
              <div>
                <label className="text-xs font-bold uppercase block mb-1">Subcategoría / Enfoque</label>
                <input
                  type="text"
                  value={newPortfolioSubIndustry}
                  onChange={(e) => setNewPortfolioSubIndustry(e.target.value)}
                  placeholder="ej. Venta de Calzado"
                  className="w-full bg-white border-2 border-black p-2 text-sm font-mono outline-none focus:border-brutalGreen"
                />
              </div>
              <div className="flex space-x-3 pt-4 border-t-2 border-black">
                <button
                  type="submit"
                  className="flex-1 bg-brutalGreen text-black hover:bg-black hover:text-white border-2 border-black font-bold uppercase py-2 text-sm transition-all"
                >
                  Crear
                </button>
                <button
                  type="button"
                  onClick={() => setIsNewPortfolioModalOpen(false)}
                  className="flex-1 bg-brutalCrimson text-white hover:bg-black border-2 border-black font-bold uppercase py-2 text-sm transition-all"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Alert Banner for Financial Risk */}
      {cajaViva.alerts && cajaViva.alerts.length > 0 && (
        <div className="bg-brutalCrimson border-2 border-black text-white p-2 mb-2 shadow-brutal flex flex-col space-y-1 uppercase animate-pulse">
          <span className="font-extrabold text-sm tracking-widest flex items-center">
            🚨 ALERTA DE RIESGO FINANCIERO Y PATRIMONIAL DETECTADA 🚨
          </span>
          <div className="text-xs space-y-1 normal-case font-mono font-medium">
            {cajaViva.alerts.map((alertText, index) => (
              <p key={index}>• {alertText}</p>
            ))}
          </div>
        </div>
      )}

      {/* ============================================================================== */}
      {/* 📊 CAJA VIVA METRICS BAR */}
      {/* ============================================================================== */}
      <section className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-2">
        {/* Tarjeta Ingresos */}
        <div className="bg-white border-2 border-black p-2 shadow-brutal flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase">Total Ingresos</span>
          <div className="mt-1 space-y-1">
            <div className="text-sm font-bold text-black bg-brutalGreen border-2 border-black py-0.5 px-2 text-center uppercase tracking-tight font-mono">
              COP {cajaViva.total_ingresos_cop?.toLocaleString('es-CO', { minimumFractionDigits: 2 }) || "0,00"}
            </div>
            <div className="text-sm font-bold text-black bg-brutalGreen border-2 border-black py-0.5 px-2 text-center uppercase tracking-tight font-mono">
              USD {cajaViva.total_ingresos_usd?.toLocaleString('en-US', { minimumFractionDigits: 2 }) || "0.00"}
            </div>
          </div>
        </div>

        {/* Tarjeta Gastos */}
        <div className="bg-white border-2 border-black p-2 shadow-brutal flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase">Total Gastos</span>
          <div className="mt-1 space-y-1">
            <div className="text-sm font-bold text-black border-2 border-black border-b-brutalCrimson border-b-4 py-0.5 px-2 text-center tracking-tight font-mono">
              COP {cajaViva.total_gastos_cop?.toLocaleString('es-CO', { minimumFractionDigits: 2 }) || "0,00"}
            </div>
            <div className="text-sm font-bold text-black border-2 border-black border-b-brutalCrimson border-b-4 py-0.5 px-2 text-center tracking-tight font-mono">
              USD {cajaViva.total_gastos_usd?.toLocaleString('en-US', { minimumFractionDigits: 2 }) || "0.00"}
            </div>
          </div>
        </div>

        {/* Tarjeta Balance */}
        <div className="bg-white border-2 border-black p-2 shadow-brutal flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase">Balance Neto</span>
          <div className="mt-1 space-y-1">
            <div className={`text-sm font-bold border-2 border-black py-0.5 px-2 text-center tracking-tight font-mono ${
              (cajaViva.balance_neto_cop ?? 0) >= 0 ? 'bg-brutalGreen text-black' : 'bg-brutalCrimson text-white animate-pulse'
            }`}>
              COP {cajaViva.balance_neto_cop?.toLocaleString('es-CO', { minimumFractionDigits: 2 }) || "0,00"}
            </div>
            <div className={`text-sm font-bold border-2 border-black py-0.5 px-2 text-center tracking-tight font-mono ${
              (cajaViva.balance_neto_usd ?? 0) >= 0 ? 'bg-brutalGreen text-black' : 'bg-brutalCrimson text-white animate-pulse'
            }`}>
              USD {cajaViva.balance_neto_usd?.toLocaleString('en-US', { minimumFractionDigits: 2 }) || "0.00"}
            </div>
          </div>
        </div>

        {/* Tarjeta Patrimonio Neto — dinámico: Activos − Pasivos */}
        <div className="bg-white border-2 border-black p-2 shadow-brutal flex flex-col justify-between">
          <div className="flex justify-between items-center">
            <span className="text-xs font-bold text-gray-400 uppercase">Patrimonio Neto</span>
            <span className="text-[8px] text-gray-400 font-bold uppercase">Activos − Pasivos</span>
          </div>
          <div className="mt-1 space-y-1">
            <div className={`text-sm font-bold border-2 border-black py-0.5 px-2 text-center tracking-tight font-mono ${
              (cajaViva.patrimonio_cop ?? 0) < 0 ? "bg-brutalCrimson text-white animate-pulse" : "bg-brutalAmber text-black"
            }`}>
              COP {cajaViva.patrimonio_cop?.toLocaleString('es-CO', { minimumFractionDigits: 2 }) || "0,00"}
            </div>
            <div className={`text-sm font-bold border-2 border-black py-0.5 px-2 text-center tracking-tight font-mono ${
              (cajaViva.patrimonio_usd ?? 0) < 0 ? "bg-brutalCrimson text-white animate-pulse" : "bg-brutalAmber text-black"
            }`}>
              USD {cajaViva.patrimonio_usd?.toLocaleString('en-US', { minimumFractionDigits: 2 }) || "0.00"}
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================================== */}
      {/* 💼 SPLIT SCREEN WORKSPACE */}
      {/* ============================================================================== */}
      <div className="flex flex-col gap-2 flex-grow">

        {/* ── FILA SUPERIOR ── */}
        <div className="grid grid-cols-5 gap-2 items-start">

          {/* PANEL IZQUIERDO VERTICAL (col-span-2) */}
          <div className="lg:col-span-2 col-span-5 space-y-2">

          {/* ═══ NAV SUBSECCIONES ═══ */}
          <div className="bg-white border-2 border-black p-1.5 shadow-brutal">
            <div className="flex flex-wrap gap-1">
              {[
                { id: 'registro', label: '📝 Registro', icon: '' },
                { id: 'facturacion', label: '🧾 Facturación', icon: '' },
              ].map((sec) => (
                <button
                  key={sec.id}
                  type="button"
                  onClick={() => setActiveLeftSection(sec.id)}
                  className={`px-2 py-0.5 text-[9px] font-bold uppercase border transition-all ${
                    activeLeftSection === sec.id
                      ? 'bg-black text-white border-black'
                      : 'border-gray-300 hover:border-black hover:bg-brutalNeutral'
                  }`}
                >{sec.label}</button>
              ))}
            </div>
          </div>

          {/* Widgets de Usuario y Cuentas movidos al formulario Registro como colapsables */}

          {/* ═══ FACTURACIÓN (subsección nueva) ═══ */}
          {activeLeftSection === 'facturacion' && (
            <div className="bg-white border-2 border-black p-2 shadow-brutal">
              <h2 className="text-sm font-bold uppercase border-b-2 border-black pb-1 mb-2">🧾 Facturación</h2>
              <div className="space-y-2">
                <p className="text-[10px] text-gray-500 uppercase">Módulo de facturación electrónica en desarrollo.</p>
                <div className="grid grid-cols-2 gap-1">
                  <button type="button" className="border-2 border-black bg-brutalBg p-2 text-[10px] font-bold uppercase hover:bg-brutalNeutral transition-all text-left">
                    📄 Nueva Factura
                  </button>
                  <button type="button" className="border-2 border-black bg-brutalBg p-2 text-[10px] font-bold uppercase hover:bg-brutalNeutral transition-all text-left">
                    📋 Historial
                  </button>
                  <button type="button" className="border-2 border-black bg-brutalBg p-2 text-[10px] font-bold uppercase hover:bg-brutalNeutral transition-all text-left">
                    📊 Reportes
                  </button>
                  <button type="button" className="border-2 border-black bg-brutalBg p-2 text-[10px] font-bold uppercase hover:bg-brutalNeutral transition-all text-left">
                    ⚙️ Configuración
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Módulo de Voz IA — Widget Colapsable */}
          {activeLeftSection === 'registro' && (
          <div className="border-2 border-black bg-white shadow-brutal">
            <div
              onClick={() => setShowVoiceWidget(prev => !prev)}
              className="p-2 cursor-pointer flex justify-between items-center hover:bg-brutalBg transition-all"
            >
              <span className="text-[10px] font-bold uppercase font-mono">
                {showVoiceWidget ? '[x] 🎤 VOZ IA — INGESTIÓN INTELIGENTE' : '[+] 🎤 VOZ IA — INGESTIÓN INTELIGENTE'}
              </span>
              <span className="text-[9px] font-mono text-gray-400">
                {isRecording ? '🔴 Grabando...' : drafts.length > 0 ? `${drafts.length} borradores` : 'Click para grabar'}
              </span>
            </div>
            {showVoiceWidget && (
          <div className="bg-white border-2 border-black p-2 shadow-brutal">
            <h2 className="text-sm font-bold uppercase border-b-2 border-black pb-1 mb-2">🎤 Ingestión por Voz Inteligente</h2>
            <p className="text-xs text-gray-500 uppercase leading-relaxed mb-2">
              Presiona el micrófono y registra libremente. Llama 3.3 y RAG autocompletarán los datos recurrentes como borradores.
            </p>

            <div className="flex flex-col items-center justify-center p-2 border-2 border-dashed border-black bg-brutalBg">
              {!isRecording ? (
                <button
                  onClick={startRecording}
                  disabled={isTranscribing || isStructuring}
                  className="w-16 h-16 rounded-full bg-brutalGreen border-3 border-black flex items-center justify-center shadow-brutal hover:translate-y-0.5 active:translate-y-1 transition-all disabled:opacity-50"
                  type="button"
                >
                  <span className="text-2xl">🎙️</span>
                </button>
              ) : (
                <button
                  onClick={stopRecording}
                  className="w-16 h-16 rounded-full bg-brutalCrimson border-3 border-black flex items-center justify-center animate-pulse shadow-brutal"
                  type="button"
                >
                  <span className="text-white text-2xl">⏹️</span>
                </button>
              )}

              <span className="text-sm font-bold uppercase mt-3 tracking-wider">
                {isRecording ? `Grabando: ${recordingDuration}s` : isTranscribing ? "Transcribiendo audio..." : isStructuring ? "IA Estructurando..." : "Listo para grabar"}
              </span>

              {(isTranscribing || isStructuring) && (
                <div className="w-full bg-gray-200 border-2 border-black h-4 mt-4 overflow-hidden relative">
                  <div className="bg-brutalGreen border-r-2 border-black h-full w-1/2 animate-ping"></div>
                </div>
              )}
            </div>

            {/* Consola de Transcripción Editable */}
            <div className="mt-2 border-2 border-black bg-brutalBg p-2 space-y-1">
              <span className="text-xs font-bold uppercase text-gray-500 block">📝 Consola de Transcripción (Editable)</span>
              <textarea
                value={liveTranscript}
                onChange={(e) => setLiveTranscript(e.target.value)}
                placeholder="Presiona el micrófono y habla, o escribe directamente aquí para estructurar..."
                className="w-full h-24 bg-white border-2 border-black p-2 text-xs font-mono outline-none resize-none focus:border-brutalGreen"
                disabled={isTranscribing || isStructuring}
              />
              <button
                type="button"
                onClick={handleStructureTranscript}
                disabled={isTranscribing || isStructuring || !liveTranscript.trim()}
                className="w-full bg-brutalGreen text-black hover:bg-black hover:text-white border-2 border-black py-2 text-xs font-bold uppercase transition-all disabled:opacity-50"
              >
                {isStructuring ? "PROCESANDO CON IA..." : "⚡ PROCESAR CON IA"}
              </button>
            </div>

            {/* Bandeja de Borradores de Voz (Draft Inbox) */}
            {drafts.length > 0 && (
              <div className="mt-6 border-t-2 border-black pt-4">
                <span className="text-xs font-bold uppercase text-gray-400 block mb-2">📥 Borradores de Voz Pendientes</span>
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {drafts.map((d, index) => (
                    <div 
                      key={index}
                      onClick={() => loadDraftIntoForm(d)}
                      className="border-2 border-black bg-white p-2 hover:bg-brutalNeutral cursor-pointer flex flex-col justify-between transition-all"
                    >
                      <div className="flex justify-between items-start">
                        <span className="text-xs bg-brutalAmber border border-black px-1 py-0.5 font-bold uppercase text-black">
                          {d.inferred_fields?.length > 0 ? "Borrador Incompleto" : "Completo"}
                        </span>
                        <span className="text-xs font-bold">${d.parsed_data?.amount}</span>
                      </div>
                      <p className="text-xs font-bold uppercase mt-2 line-clamp-1">"{d.parsed_data?.concept}"</p>
                      
                      {/* Mostrar transcripción raw completa en la tarjeta */}
                      {d.raw_transcript && (
                        <p className="text-[10px] text-gray-500 mt-1 italic border-l-2 border-black pl-1.5 line-clamp-2">
                          "{d.raw_transcript}"
                        </p>
                      )}

                      {d.inferred_fields?.length > 0 && (
                        <span className="text-[10px] text-brutalCrimson font-bold uppercase mt-1">
                          ⚠️ Falta: {d.inferred_fields.join(", ")}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
            )}
          </div>
          )}

          {/* Formulario Manual Módulo 01 */}
          {activeLeftSection === 'registro' && (
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
          </div>
          )}
        </div>{/* fin panel izquierdo */}

          {/* PANEL DERECHO — FORM + BD POR TAB */}
          <ContextPanel
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            tercero={{
              name: thirdPartyName, setName: setThirdPartyName,
              idType: thirdPartyType, setIdType: setThirdPartyType,
              idNumber: thirdPartyNumber, setIdNumber: setThirdPartyNumber,
              email: thirdPartyEmail, setEmail: setThirdPartyEmail,
              phone: thirdPartyPhone, setPhone: setThirdPartyPhone,
              address: thirdPartyWebsite, setAddress: setThirdPartyWebsite,
            }}
            taxes={{
              enabled: applyIva, setEnabled: setApplyIva,
              type: 'IVA_19', setType: () => {},
              customRate: '', setCustomRate: () => {},
            }}
            cartera={{
              enabled: cxcCxpEnabled, setEnabled: setCxcCxpEnabled,
              type: cxcCxpType, setType: setCxcCxpType,
              dueDate: cxcCxpDueDate, setDueDate: setCxcCxpDueDate,
              term: cxcCxpTerm, setTerm: setCxcCxpTerm,
              partialValue: cxcCxpValue, setPartialValue: setCxcCxpValue,
              totalAmount: amount,
            }}
            assets={{
              enabled: assetEnabled, setEnabled: setAssetEnabled,
              name: assetName, setName: setAssetName,
              value: assetValue, setValue: setAssetValue,
              tag: assetTag, setTag: setAssetTag,
            }}
            tagState={{
              selected: selectedTags, setSelected: setSelectedTags,
              search: tagSearch, setSearch: setTagSearch,
            }}
            allThirdParties={allThirdParties}
            setAllThirdParties={setAllThirdParties}
            activePortfolio={activePortfolio}
            accounts={accounts}
            profile={profile}
            profileEdit={{
              isEditing: isEditingProfile, setIsEditing: setIsEditingProfile,
              name: editProfileName, setName: setEditProfileName,
              email: editProfileEmail, setEmail: setEditProfileEmail,
              role: editProfileRole, setRole: setEditProfileRole,
              handleSave: handleUpdateProfile,
            }}
          />

        </div>{/* fin fila superior */}

        {/* ── FILA INFERIOR: Libro Diario ancho completo ── */}
        <div className="w-full">
          <div className="bg-white border-2 border-black p-2 shadow-brutal overflow-hidden flex flex-col">
            <h2 className="text-sm font-bold uppercase border-b-2 border-black pb-1 mb-2">📖 Módulo 02: Libro Diario Inteligente</h2>
            
            {/* Rejilla de Movimientos Históricos */}
            <div className="overflow-x-auto">
              <table className="w-full border-2 border-black text-left text-xs">
                <thead className="bg-black text-white uppercase font-bold">
                  <tr>
                    <th className="p-2 border-r border-black">Tipo</th>
                    <th className="p-2 border-r border-black">Valor Neto</th>
                    <th className="p-2 border-r border-black">Concepto</th>
                    <th className="p-2 border-r border-black">Cuenta COA</th>
                    <th className="p-2 border-r border-black">Tercero NIT/CC</th>
                    <th className="p-2 border-r border-black">Fecha</th>
                    <th className="p-2 border-r border-black">Cuenta</th>
                    <th className="p-2 border-r border-black">Lugar</th>
                    <th className="p-2">Evidencia</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-black bg-white">
                  {transactions.length === 0 ? (
                    <tr>
                      <td colSpan="9" className="p-8 text-center uppercase text-gray-400 font-bold">
                        No hay registros en este portafolio. Agrega uno manual o habla por micrófono.
                      </td>
                    </tr>
                  ) : (
                    transactions.map((tx) => (
                      <React.Fragment key={tx.id}>
                      <tr 
                        className={`hover:bg-brutalBg transition-all cursor-pointer ${expandedTxId === tx.id ? 'bg-brutalBg' : ''}`} 
                        title="Click para ver detalles · Doble clic en celda para editar"
                        onClick={() => setExpandedTxId(expandedTxId === tx.id ? null : tx.id)}
                      >
                        {/* Tipo */}
                        <td className="p-2 border-r border-black font-bold">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "type" ? (
                            <select
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "type")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "type");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="bg-white border border-black p-0.5 text-xs font-mono outline-none"
                              autoFocus
                            >
                              <option value="INGRESO">INGRESO</option>
                              <option value="GASTO">GASTO</option>
                              <option value="TRANSFERENCIA">TRANSFERENCIA</option>
                            </select>
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "type", tx.type)} 
                              className={`px-2 py-0.5 border border-black uppercase text-[10px] font-bold cursor-pointer ${
                                tx.type === "INGRESO" ? "bg-brutalGreen text-black" : tx.type === "GASTO" ? "bg-brutalCrimson text-white" : "bg-black text-white"
                              }`}
                            >
                              {tx.type.substring(0, 3)}
                            </span>
                          )}
                        </td>

                        {/* Valor Neto */}
                        <td className="p-2 border-r border-black font-bold text-right uppercase">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "net_value" ? (
                            <input
                              type="number"
                              step="0.01"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "net_value")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "net_value");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="w-24 bg-white border border-black p-0.5 text-xs font-mono outline-none text-right"
                              autoFocus
                            />
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "net_value", tx.net_value)} 
                              className="cursor-pointer block w-full h-full font-mono text-[11px]"
                            >
                              {tx.transaction_currency === "USD" ? "$" : "$"}
                              {tx.net_value.toLocaleString('es-CO', { minimumFractionDigits: 2 })} {tx.transaction_currency || "COP"}
                            </span>
                          )}
                        </td>

                        {/* Concepto */}
                        <td className="p-2 border-r border-black font-bold uppercase max-w-[150px] truncate">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "concept" ? (
                            <input
                              type="text"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "concept")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "concept");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="w-full bg-white border border-black p-0.5 text-xs font-mono outline-none"
                              autoFocus
                            />
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "concept", tx.concept)} 
                              className="cursor-pointer block w-full h-full"
                            >
                              <div className="flex flex-col">
                                <div className="flex items-center space-x-1.5">
                                  {tx.is_recurring && (
                                    <span 
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        toggleRecurrence(tx.id, tx.is_recurring);
                                      }}
                                      className="bg-brutalAmber text-black text-[9px] px-1 py-0.5 border border-black font-extrabold cursor-pointer uppercase select-none hover:bg-black hover:text-white transition-all"
                                      title="Hacer clic para desactivar recurrencia"
                                    >
                                      REC
                                    </span>
                                  )}
                                  <span>{tx.concept}</span>
                                </div>
                                {tx.is_recurring && (
                                  <div className="text-[9px] text-gray-500 font-mono mt-1 w-full truncate">
                                    🔁 Recurrencia: {tx.recurrence_interval === "PERSONALIZADO" ? `Cada ${tx.recurrence_days} días` : (tx.recurrence_interval || "Mensual").toLowerCase()}{tx.recurrence_max_reps ? ` (Max: ${tx.recurrence_max_reps} reps)` : ""}{tx.recurrence_end_date ? ` (Termina: ${tx.recurrence_end_date})` : ""}
                                  </div>
                                )}
                              </div>
                            </span>
                          )}
                        </td>

                        {/* Cuenta COA */}
                        <td className="p-2 border-r border-black font-semibold text-[11px] max-w-[150px] truncate">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "category" ? (
                            <select
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "category")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "category");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="bg-white border border-black p-0.5 text-xs font-mono outline-none w-full"
                              autoFocus
                            >
                              {coaFlatAccounts.length === 0 ? (
                                <option value={tx.category}>{tx.category}</option>
                              ) : (
                                coaFlatAccounts.map(acc => (
                                  <option key={acc.id} value={`${acc.code} - ${acc.name}`}>
                                    {acc.code} - {acc.name}
                                  </option>
                                ))
                              )}
                            </select>
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "category", tx.category)} 
                              className="cursor-pointer block w-full h-full text-blue-600 font-semibold"
                              title="Doble clic para cambiar cuenta contable"
                            >
                              {tx.category || "-"}
                            </span>
                          )}
                        </td>

                        {/* Tercero NIT/CC */}
                        <td className="p-2 border-r border-black uppercase text-gray-500 font-mono text-[10px]">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "identification_number" ? (
                            <input
                              type="text"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "identification_number")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "identification_number");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="w-full bg-white border-black p-0.5 text-xs font-mono outline-none"
                              autoFocus
                            />
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "identification_number", tx.identification_number)} 
                              className="cursor-pointer block w-full h-full"
                            >
                              {tx.identification_number}
                            </span>
                          )}
                        </td>

                        {/* Fecha */}
                        <td className="p-2 border-r border-black whitespace-nowrap font-mono text-[10px]">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "transaction_date" ? (
                            <input
                              type="date"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "transaction_date")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "transaction_date");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="bg-white border border-black p-0.5 text-xs font-mono outline-none"
                              autoFocus
                            />
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "transaction_date", tx.transaction_date)} 
                              className="cursor-pointer block w-full h-full"
                            >
                              {tx.transaction_date}
                            </span>
                          )}
                        </td>

                        {/* Cuenta */}
                        <td className="p-2 border-r border-black uppercase text-[11px]">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "account_id" ? (
                            <select
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "account_id")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "account_id");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="bg-white border border-black p-0.5 text-xs font-mono outline-none"
                              autoFocus
                            >
                              {accounts.map(acc => (
                                    <option key={acc.id} value={acc.id}>{acc.name}</option>
                              ))}
                            </select>
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "account_id", tx.account_id)} 
                              className="cursor-pointer block w-full h-full"
                            >
                              {tx.type === "TRANSFERENCIA" ? (
                                <span className="font-semibold">{tx.account_name || tx.payment_method} ➜ {tx.dest_account_name || "?"}</span>
                              ) : (
                                <span>{tx.account_name || tx.payment_method}</span>
                              )}
                            </span>
                          )}
                        </td>

                        {/* Lugar */}
                        <td className="p-2 border-r border-black text-center">
                          {tx.geo_maps_link ? (
                            <a 
                              href={tx.geo_maps_link} 
                              target="_blank" 
                              rel="noreferrer"
                              className="bg-brutalNeutral border border-black px-1.5 py-0.5 hover:bg-black hover:text-white transition-all inline-block uppercase text-[10px] font-bold"
                            >
                              [Maps]
                            </a>
                          ) : (
                            <span className="text-gray-300">-</span>
                          )}
                        </td>

                        {/* Evidencia */}
                        <td className="p-2 text-center">
                          <button
                            onClick={() => {
                              setSelectedEvidenceTx(tx);
                              setEvidenceUrl(tx.evidence_file_path || "recibo_demo.png");
                            }}
                            className="bg-black text-white border border-black px-1.5 py-0.5 hover:bg-brutalGreen hover:text-black transition-all uppercase text-[10px] font-bold"
                            type="button"
                          >
                            [Ver]
                          </button>
                        </td>
                      </tr>

                      {/* ═══ FILA EXPANDIBLE: Detalles de la Transacción ═══ */}
                      {expandedTxId === tx.id && (
                        <tr>
                          <td colSpan="9" className="p-0 border-t border-black">
                            <div className="bg-brutalBg p-3 border-b-2 border-black">
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[10px] font-mono">

                                {/* Tercero */}
                                {tx.third_party_name && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">👤 Tercero</span>
                                    <span className="font-bold block">{tx.third_party_name}</span>
                                    <span className="text-gray-400 block">{tx.identification_type} {tx.identification_number}</span>
                                  </div>
                                )}

                                {/* CXC/CXP */}
                                {tx.cxc_type && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">📄 {tx.cxc_type === 'CXC' ? 'Cuenta por Cobrar' : 'Cuenta por Pagar'}</span>
                                    <span className={`inline-block px-1.5 py-0.5 text-[9px] font-bold uppercase border ${tx.cxc_type === 'CXC' ? 'bg-brutalGreen border-black text-black' : 'bg-brutalAmber border-black text-black'}`}>
                                      {tx.cxc_type}
                                    </span>
                                    <span className="block">Vence: {tx.cxc_due_date || '-'}</span>
                                    <span className="block">Plazo: {tx.cxc_term || '-'}</span>
                                    {tx.cxc_status && <span className="block">Estado: {tx.cxc_status}</span>}
                                  </div>
                                )}

                                {/* Impuestos */}
                                {(tx.tax_iva_amount > 0 || tx.tax_gmf_amount > 0) && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">📈 Impuestos</span>
                                    {tx.tax_iva_amount > 0 && <span className="block">IVA: ${Number(tx.tax_iva_amount).toLocaleString()}</span>}
                                    {tx.tax_gmf_amount > 0 && <span className="block">GMF: ${Number(tx.tax_gmf_amount).toLocaleString()}</span>}
                                    <span className="block font-bold">Bruto: ${Number(tx.amount).toLocaleString()}</span>
                                  </div>
                                )}

                                {/* Divisa / TRM */}
                                {tx.transaction_currency && tx.transaction_currency !== 'COP' && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">💱 Divisa</span>
                                    <span className="block">{tx.transaction_currency}</span>
                                    {tx.trm && tx.trm !== 1 && <span className="block">TRM: {tx.trm}</span>}
                                  </div>
                                )}

                                {/* Recurrencia */}
                                {tx.is_recurring && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">🔁 Recurrencia</span>
                                    <span className="block">{tx.recurrence_interval || 'MENSUAL'} ({tx.recurrence_days || 30}d)</span>
                                    {tx.recurrence_max_reps && <span className="block">Máx: {tx.recurrence_max_reps} reps</span>}
                                    {tx.recurrence_end_date && <span className="block">Hasta: {tx.recurrence_end_date}</span>}
                                  </div>
                                )}

                                {/* Recurso / Activo */}
                                {tx.asset_name && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">📦 Recurso</span>
                                    <span className="font-bold block">{tx.asset_name}</span>
                                    {tx.asset_tag && <span className="block">Tag: {tx.asset_tag}</span>}
                                    {tx.asset_is_passive && <span className="block text-brutalGreen font-bold">♻ Ingreso pasivo</span>}
                                  </div>
                                )}

                                {/* Geo */}
                                {tx.geo_maps_link && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">📍 Ubicación</span>
                                    <a href={tx.geo_maps_link} target="_blank" rel="noreferrer" className="text-blue-600 underline break-all">
                                      Ver en Maps →
                                    </a>
                                  </div>
                                )}

                                {/* Tags (si existen en el futuro) */}
                                {tx.tags && tx.tags.length > 0 && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">🏷️ Etiquetas</span>
                                    <div className="flex flex-wrap gap-1">
                                      {tx.tags.map(tag => (
                                        <span key={tag} className="bg-black text-white px-1 py-0.5 text-[8px] font-bold uppercase">{tag}</span>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>

                              {/* Si no hay datos extra */}
                              {!tx.third_party_name && !tx.cxc_type && !tx.tax_iva_amount && !tx.tax_gmf_amount && !tx.is_recurring && !tx.asset_name && !(tx.transaction_currency && tx.transaction_currency !== 'COP') && (
                                <p className="text-[10px] text-gray-300 font-mono uppercase text-center py-2">Sin datos adicionales registrados</p>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                      </React.Fragment>
                    ))
                  )}
                </tbody>
              </table>

              {/* DT-12: Botón "Cargar más" si hay más TXs disponibles */}
              {transactions.length < totalTxCount && (
                <div style={{
                  display: 'flex', justifyContent: 'center', alignItems: 'center',
                  gap: 12, padding: '12px 0', borderTop: '2px solid #000',
                }}>
                  <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 10, color: '#888', textTransform: 'uppercase' }}>
                    Mostrando {transactions.length} de {totalTxCount} registros
                  </span>
                  <button
                    onClick={loadMoreTransactions}
                    disabled={loadingMore}
                    style={{
                      fontFamily: 'IBM Plex Mono, monospace', fontSize: 10,
                      textTransform: 'uppercase', letterSpacing: 1,
                      background: '#000', color: '#fff',
                      border: '2px solid #000', padding: '6px 16px',
                      cursor: loadingMore ? 'wait' : 'pointer',
                      opacity: loadingMore ? 0.5 : 1,
                    }}
                  >
                    {loadingMore ? '▓ CARGANDO...' : '↓ CARGAR 50 MÁS'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

      </div>

      {/* ============================================================================== */}
      {/* 🖼️ EVIDENCE MODAL POPUP */}
      {/* ============================================================================== */}
      {evidenceUrl && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center p-2 z-50 overflow-y-auto">
          <div className="bg-white border-2 border-black p-2 max-w-lg w-full shadow-brutal my-8 font-mono">
            <div className="flex justify-between items-center border-b-2 border-black pb-1 mb-2">
              <span className="text-sm font-bold uppercase">📂 Visualizador de Evidencia</span>
              <button 
                onClick={() => {
                  setEvidenceUrl(null);
                  setSelectedEvidenceTx(null);
                }}
                className="bg-brutalCrimson text-white border border-black px-2 py-0.5 font-bold uppercase hover:bg-black"
              >
                Cerrar [X]
              </button>
            </div>
            
            {selectedEvidenceTx ? (
              <div className="space-y-2">
                {/* Brutalist Simulated Receipt Visualizer */}
                <div className="border-2 border-black p-2 bg-brutalBg text-xs space-y-2 uppercase">
                  <div className="text-center font-bold border-b border-black pb-2 text-sm">
                    *** CERTIFICADO / RECIBO DE CAJA ***
                    <br />
                    <span className="text-[11px] font-black uppercase text-blue-600 block mt-1">
                      🏢 EMPRESA: {selectedEvidenceTx.portfolio_name || "ESTÁNDAR"}
                    </span>
                    <span className="text-[9px] font-bold text-gray-500 block mb-1">
                      💼 SECTOR: {selectedEvidenceTx.portfolio_industry || "ESTÁNDAR"}
                      {selectedEvidenceTx.portfolio_sub_industry ? ` (${selectedEvidenceTx.portfolio_sub_industry})` : ""}
                    </span>
                    <span className="text-[9px] text-gray-400 font-normal block">AUDITORÍA ACTIVA SUPABASE POSTGRES</span>
                    <span className="text-[10px] bg-black text-white px-2 py-0.5 mt-1.5 inline-block">ID TX: #{selectedEvidenceTx.id}</span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2 border-b border-black pb-2">
                    <div>
                      <span className="font-bold text-gray-500 block text-[9px]">TIPO OPERACIÓN:</span>
                      <div className="mt-1">
                        <span className={`px-2 py-0.5 border border-black font-extrabold text-[10px] ${
                          selectedEvidenceTx.type === "INGRESO" 
                            ? "bg-brutalGreen text-black" 
                            : selectedEvidenceTx.type === "GASTO" 
                              ? "bg-brutalCrimson text-white" 
                              : "bg-black text-white"
                        }`}>
                          {selectedEvidenceTx.type}
                        </span>
                      </div>
                    </div>
                    <div>
                      <span className="font-bold text-gray-500 block text-[9px]">FECHA REGISTRO:</span>
                      <div className="mt-1 font-bold">{selectedEvidenceTx.transaction_date}</div>
                    </div>
                  </div>

                  <div className="space-y-1.5 border-b border-black pb-2">
                    <div className="flex justify-between">
                      <span className="font-bold text-gray-500">CONCEPTO:</span>
                      <span className="font-bold text-right break-all max-w-[200px]">{selectedEvidenceTx.concept}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-bold text-gray-500">CUENTA COA:</span>
                      <span className="font-bold text-blue-600">{selectedEvidenceTx.category || "SIN ASIGNAR"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-bold text-gray-500">MEDIO DE PAGO:</span>
                      <span className="font-bold">
                        {selectedEvidenceTx.type === "TRANSFERENCIA" 
                          ? `${selectedEvidenceTx.account_name || selectedEvidenceTx.payment_method || "EFECTIVO"} ➜ ${selectedEvidenceTx.dest_account_name || "?"}`
                          : (selectedEvidenceTx.account_name || selectedEvidenceTx.payment_method || "EFECTIVO")
                        }
                      </span>
                    </div>
                  </div>

                  <div className="space-y-1.5 border-b border-black pb-2">
                    <div className="flex justify-between text-[11px]">
                      <span className="font-bold text-gray-500">PERSONA (TERCERO):</span>
                      <span className="font-bold text-right">{selectedEvidenceTx.third_party_name || "N/A"}</span>
                    </div>
                    <div className="flex justify-between text-[11px]">
                      <span className="font-bold text-gray-500">IDENTIFICACIÓN:</span>
                      <span className="font-bold">
                        {selectedEvidenceTx.identification_type || "CC"}: {selectedEvidenceTx.identification_number || "N/A"}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-1 border-b border-black pb-2">
                    <div className="flex justify-between">
                      <span className="font-bold text-gray-500">VALOR BASE:</span>
                      <span className="font-bold">
                        ${Number(selectedEvidenceTx.amount || 0).toLocaleString('es-CO', { minimumFractionDigits: 2 })} {selectedEvidenceTx.transaction_currency || "COP"}
                      </span>
                    </div>
                    
                    {selectedEvidenceTx.trm && Number(selectedEvidenceTx.trm) !== 1 && (
                      <div className="flex justify-between text-gray-500 text-[10px]">
                        <span>TASA DE CAMBIO (TRM):</span>
                        <span>1 USD = ${Number(selectedEvidenceTx.trm).toLocaleString('es-CO', { minimumFractionDigits: 2 })} COP</span>
                      </div>
                    )}

                    {selectedEvidenceTx.tax_iva_amount > 0 && (
                      <div className="flex justify-between text-gray-500">
                        <span>+ IVA (19%):</span>
                        <span>${Number(selectedEvidenceTx.tax_iva_amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                      </div>
                    )}

                    {selectedEvidenceTx.tax_gmf_amount > 0 && (
                      <div className="flex justify-between text-gray-500">
                        <span>+ GMF (4X1000):</span>
                        <span>${Number(selectedEvidenceTx.tax_gmf_amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                      </div>
                    )}

                    {selectedEvidenceTx.custom_tax_amount > 0 && (
                      <div className="flex justify-between text-gray-500">
                        <span>+ IMPUESTOS ADICIONALES:</span>
                        <span>${Number(selectedEvidenceTx.custom_tax_amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                      </div>
                    )}

                    <div className="flex justify-between border-t border-black pt-1 text-[13px] font-black bg-yellow-100 p-1 mt-1">
                      <span>VALOR NETO:</span>
                      <span>
                        ${Number(selectedEvidenceTx.net_value || 0).toLocaleString('es-CO', { minimumFractionDigits: 2 })} {selectedEvidenceTx.transaction_currency || "COP"}
                      </span>
                    </div>
                  </div>

                  {/* CXC / CXP Link Details */}
                  {selectedEvidenceTx.cxc_type && (
                    <div className="border-b border-black pb-2 space-y-1">
                      <span className="font-bold text-gray-500 block text-[9px]">GESTIONADO EN CARTERA ({selectedEvidenceTx.cxc_type}):</span>
                      <div className="bg-black text-white p-1.5 font-mono text-[9px] flex justify-between items-center uppercase">
                        <span>VENCE: {selectedEvidenceTx.cxc_due_date}</span>
                        <span>PLAZO: {selectedEvidenceTx.cxc_term}</span>
                        <span className="bg-brutalAmber text-black px-1 font-extrabold">{selectedEvidenceTx.cxc_status || "PENDIENTE"}</span>
                      </div>
                    </div>
                  )}

                  {/* Capitalized Asset Link Details */}
                  {selectedEvidenceTx.asset_name && (
                    <div className="border-b border-black pb-2 space-y-1">
                      <span className="font-bold text-gray-500 block text-[9px]">ACTIVO CAPITALIZADO EN GESTIÓN:</span>
                      <div className="bg-blue-50 border border-blue-500 text-blue-900 p-2 font-mono text-[9px] uppercase space-y-1">
                        <div className="flex justify-between font-extrabold">
                          <span>ACTIVO: {selectedEvidenceTx.asset_name}</span>
                          <span>TAG: {selectedEvidenceTx.asset_tag || "GENERAL"}</span>
                        </div>
                        {selectedEvidenceTx.asset_is_passive && (
                          <div className="text-[8px] text-blue-700 font-extrabold leading-tight">
                            🔁 ACTIVO GENERADOR DE RENTAS RECURRENTES:
                            <br />
                            ${Number(selectedEvidenceTx.amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })} COP / CADA {selectedEvidenceTx.recurrence_days || 30} DÍAS
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Auditor / Issuer Information */}
                  <div className="border-b border-black pb-2 flex justify-between text-[10px] font-bold uppercase">
                    <span className="text-gray-500">AUDITOR FIRMANTE:</span>
                    <span>{profile?.name || "ANDRÉS"} ({profile?.role || "ADMINISTRADOR CONTABLE"})</span>
                  </div>

                  <div className="flex justify-between text-[10px] items-center">
                    <span className="font-bold text-gray-500">GEOLOCALIZACIÓN:</span>
                    {selectedEvidenceTx.geo_maps_link ? (
                      <a 
                        href={selectedEvidenceTx.geo_maps_link} 
                        target="_blank" 
                        rel="noreferrer"
                        className="bg-black text-white px-2 py-0.5 border border-black hover:bg-brutalGreen hover:text-black font-bold uppercase transition-all"
                      >
                        [VER EN MAPAS]
                      </a>
                    ) : (
                      <span className="text-gray-400 font-bold">SIN COORDENADAS</span>
                    )}
                  </div>
                </div>

                {/* Sección de Auditoría / Advertencias */}
                <div className="border-2 border-black p-2 bg-white space-y-1 uppercase text-[10px]">
                  <div className="font-bold border-b border-black pb-1 text-gray-600">
                    🔍 CONTROL INTERNO Y AUDITORÍA DE SOPORTES
                  </div>
                  
                  {(() => {
                    const nameUpper = (selectedEvidenceTx.third_party_name || "").toUpperCase().trim();
                    const warnings = [];
                    if (!selectedEvidenceTx.third_party_name || ["VARIOS", "N/A", "SD", "S/D", "GENERICO", "GENÉRICO", "VARIOS EMPLEADOS"].includes(nameUpper) || selectedEvidenceTx.third_party_name.length < 3) {
                      warnings.push("Tercero / Persona es genérico o no está plenamente identificado.");
                    }
                    const idStr = (selectedEvidenceTx.identification_number || "").toString().trim();
                    if (!idStr || idStr === "0" || idStr === "999999999" || idStr.toLowerCase() === "n/a") {
                      warnings.push("Número de identificación (NIT/CC) inválido o faltante.");
                    }
                    if (!selectedEvidenceTx.evidence_file_path) {
                      warnings.push("Falta archivo digital o soporte de factura adjunto.");
                    }
                    if (!selectedEvidenceTx.geo_maps_link) {
                      warnings.push("Falta registro de geolocalización de la operación.");
                    }
                    if (!selectedEvidenceTx.category || selectedEvidenceTx.category === "-") {
                      warnings.push("No se ha asignado una categoría o cuenta COA válida.");
                    }

                    if (warnings.length > 0) {
                      return (
                         <div className="space-y-2">
                           <div className="bg-brutalCrimson text-white px-2 py-1 font-bold flex items-center gap-1 border border-black">
                             <span>⚠️ COMPROBANTE CON INCONSISTENCIAS ({warnings.length} OBS.)</span>
                           </div>
                           <ul className="list-disc pl-4 space-y-1 font-mono text-[9px] text-red-600">
                             {warnings.map((w, idx) => (
                               <li key={idx} className="font-bold">{w}</li>
                             ))}
                           </ul>
                         </div>
                      );
                    } else {
                      return (
                        <div className="bg-brutalGreen text-black px-2 py-1.5 font-bold flex items-center gap-1 border border-black">
                          <span>✅ COMPROBANTE COMPLETADO SIN OBSERVACIONES</span>
                        </div>
                      );
                    }
                  })()}
                </div>

                {/* Evidencia física real (si existe) */}
                {selectedEvidenceTx.evidence_file_path && selectedEvidenceTx.evidence_file_path !== "recibo_demo.png" && (
                  <div className="border-2 border-black p-2 bg-white space-y-1 uppercase text-[10px]">
                    <div className="font-bold border-b border-black pb-1">
                      📂 ARCHIVO DE SOPORTE ADJUNTO
                    </div>
                    <div className="flex flex-col items-center justify-center p-2 bg-gray-50 border border-black">
                      <img 
                        src={
                          selectedEvidenceTx.evidence_file_path.startsWith("http")
                            ? selectedEvidenceTx.evidence_file_path
                            : `http://127.0.0.1:8000/${selectedEvidenceTx.evidence_file_path}`
                        } 
                        alt="Respaldo Físico" 
                        className="max-h-40 object-contain border border-black shadow-brutal mb-2"
                        onError={(e) => {
                          e.target.onerror = null;
                          e.target.src = "https://placehold.co/400x200/000000/ffffff?text=EVIDENCIA+F%C3%8DSICA";
                        }}
                      />
                      <a
                        href={
                          selectedEvidenceTx.evidence_file_path.startsWith("http")
                            ? selectedEvidenceTx.evidence_file_path
                            : `http://127.0.0.1:8000/${selectedEvidenceTx.evidence_file_path}`
                        }
                        target="_blank"
                        rel="noreferrer"
                        className="bg-black text-white text-[9px] font-bold px-2 py-1 hover:bg-brutalGreen hover:text-black border border-black transition-all"
                      >
                        ABRIR ARCHIVO EN PESTAÑA NUEVA
                      </a>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center font-bold py-4">No se han cargado detalles del comprobante.</div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="mt-8 text-center text-xs text-gray-400 uppercase tracking-widest">
        FIN-SYS OS v2.0 // NOMINAL OPERATION MODE // LOCALHOST DEPLOY
      </footer>
    
      <ThirdPartyModal 
        isOpen={isThirdPartyModalOpen}
        onClose={() => setIsThirdPartyModalOpen(false)}
        onSelect={(tp) => {
          setThirdPartyType(tp.identification_type);
          setThirdPartyNumber(tp.identification_number);
          setThirdPartyName(tp.name);
          setThirdPartyEmail(tp.email);
          setThirdPartyPhone(tp.phone);
          setThirdPartyWebsite(tp.website);
        }}
      />
    </div>
  );
}

export default App;
