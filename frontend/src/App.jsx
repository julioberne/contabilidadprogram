import React, { useState, useEffect, useRef } from 'react';
import ThirdPartyModal from './components/ThirdPartyModal';

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

  // --- Estado del Formulario de Registro (Módulo 01) ---
  const [formType, setFormType] = useState("GASTO"); // INGRESO, GASTO, TRANSFERENCIA
  const [amount, setAmount] = useState("");
  const [concept, setConcept] = useState("");
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
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

  // --- Collapsible sections states ---
  const [expandedTercero, setExpandedTercero] = useState(false);
  const [expandedTaxes, setExpandedTaxes] = useState(false);
  const [expandedCartera, setExpandedCartera] = useState(false);
  const [expandedActivos, setExpandedActivos] = useState(false);

  // --- Cartera (CXC / CXP) ---
  const [cxcCxpEnabled, setCxcCxpEnabled] = useState(false);
  const [cxcCxpType, setCxcCxpType] = useState("CXC"); // CXC, CXP
  const [cxcCxpDueDate, setCxcCxpDueDate] = useState("");
  const [cxcCxpTerm, setCxcCxpTerm] = useState("Corto"); // Corto, Mediano, Largo

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

  // --- Cargar Balances y Transacciones ---
  const fetchData = async () => {
    try {
      // 0. Obtener Portafolios
      const resPortfolios = await fetch(`${API_BASE_URL}/portfolios`);
      const dataPortfolios = await resPortfolios.json();
      if (resPortfolios.ok) {
        setPortfolios(dataPortfolios);
      }

      // 1. Obtener Balances Caja Viva
      const resBalance = await fetch(`${API_BASE_URL}/portfolios/balance?portfolio=${activePortfolio}`);
      const dataBalance = await resBalance.json();
      if (resBalance.ok) {
        setCajaViva({
          total_ingresos: dataBalance.total_ingresos,
          total_gastos: dataBalance.total_gastos,
          balance_neto: dataBalance.balance_neto,
          capital_inicial: dataBalance.capital_inicial,
          patrimonio: dataBalance.patrimonio,
          status: dataBalance.status,
          alerts: dataBalance.alerts,
          total_ingresos_cop: dataBalance.total_ingresos_cop,
          total_gastos_cop: dataBalance.total_gastos_cop,
          balance_neto_cop: dataBalance.balance_neto_cop,
          patrimonio_cop: dataBalance.patrimonio_cop,
          total_ingresos_usd: dataBalance.total_ingresos_usd,
          total_gastos_usd: dataBalance.total_gastos_usd,
          balance_neto_usd: dataBalance.balance_neto_usd,
          patrimonio_usd: dataBalance.patrimonio_usd
        });
      }

      // 2. Obtener Historial de Transacciones
      const resTxs = await fetch(`${API_BASE_URL}/transactions?portfolio=${activePortfolio}`);
      const dataTxs = await resTxs.json();
      if (resTxs.ok) {
        setTransactions(dataTxs);
      }

      // 3. Obtener Cuentas
      const resAccounts = await fetch(`${API_BASE_URL}/accounts`);
      const dataAccounts = await resAccounts.json();
      if (resAccounts.ok) {
        setAccounts(dataAccounts);
      }

      // 4. Obtener Perfil
      const resProfile = await fetch(`${API_BASE_URL}/profile`);
      const dataProfile = await resProfile.json();
      if (resProfile.ok) {
        setProfile(dataProfile);
        setEditProfileName(dataProfile.name);
        setEditProfileEmail(dataProfile.email);
        setEditProfileRole(dataProfile.role);
        setEditProfileAvatar(dataProfile.avatar_style);
      }

      // 5. Obtener Catálogo de Cuentas (COA)
      setIsLoadingCoa(true);
      try {
        const resCoa = await fetch(`${API_BASE_URL}/coa?portfolio=${encodeURIComponent(activePortfolio)}`);
        const dataCoa = await resCoa.json();
        if (resCoa.ok && dataCoa.status === "OK") {
          setCoaTree(dataCoa.data);
          const flat = flattenCoa(dataCoa.data);
          const postable = flat.filter(acc => !acc.is_group);
          setCoaFlatAccounts(postable);

          if (postable.length > 0) {
            // Buscar si coincide con la categoría actual
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
        console.error("Error cargando COA:", coaErr);
      } finally {
        setIsLoadingCoa(false);
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
        <div className="border-2 border-black p-3 bg-brutalAmber text-xs font-bold uppercase space-y-2">
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
    if (!amount || !concept || !thirdPartyNumber || !thirdPartyName) {
      alert("❌ Error: Los campos de Importe, Concepto, Identificación y Nombre de Tercero son obligatorios.");
      return;
    }

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
        identification_number: thirdPartyNumber,
        name: thirdPartyName,
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
        term: cxcCxpTerm
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
      evidence_file_path: evidenceFilePath || null
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
        setTrmValue("1.0");
        setSelectedDestAccountId("");
        
        // Reset Cartera / Activos
        setCxcCxpEnabled(false);
        setCxcCxpDueDate("");
        setAssetEnabled(false);
        setAssetName("");
        setAssetValue("");
        setAssetTag("");
        setAssetVincularImporte(false);
        setAssetEstablecerActivo(false);
        setAssetRecurrente(false);
        setEvidenceFilePath("");
        
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
    <div className="min-h-screen bg-brutalBg text-black font-mono p-4 flex flex-col antialiased selection:bg-brutalGreen">
      
      {/* ============================================================================== */}
      {/* 🏛️ APP HEADER TERMINAL STYLE */}
      {/* ============================================================================== */}
      <header className="border-3 border-black bg-white p-4 mb-6 shadow-brutal flex flex-col md:flex-row justify-between items-start md:items-center">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold tracking-tight uppercase">FIN-SYS OS v2.0</h1>
            <span className="bg-brutalGreen border-2 border-black text-black px-2 py-0.5 text-xs font-bold uppercase tracking-wider">
              {cajaViva.status}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1 uppercase">Terminal de Contabilidad Asistida por IA & pgvector RAG</p>
        </div>
        
        {/* Portafolio Activo */}
        <div className="mt-4 md:mt-0 flex flex-col md:items-end">
          <span className="text-xs font-bold uppercase text-gray-400">Portafolio Activo</span>
          <div className="flex bg-brutalBg border-2 border-black p-1 space-x-1 mt-1 items-center flex-wrap">
            {portfolios.map((port) => (
              <button
                key={port.id}
                onClick={() => setActivePortfolio(port.name)}
                className={`px-2 py-1 text-xs font-bold uppercase transition-all mb-1 ${
                  activePortfolio === port.name 
                    ? "bg-black text-white" 
                    : "hover:bg-brutalNeutral"
                }`}
                type="button"
                title={`${port.name} (${port.industry_type}${port.sub_industry_type ? ' - ' + port.sub_industry_type : ''})`}
              >
                {port.name.substring(0, 15)}
              </button>
            ))}
            <button
              onClick={() => setIsNewPortfolioModalOpen(true)}
              className="px-2 py-1 text-xs font-bold uppercase bg-brutalGreen border-2 border-black text-black hover:bg-black hover:text-white transition-all ml-2 mb-1"
              type="button"
            >
              + Agregar Empresa
            </button>
            <button
              onClick={handleSeedSynthetic}
              className="px-2 py-1 text-xs font-bold uppercase bg-brutalAmber border-2 border-black text-black hover:bg-black hover:text-white transition-all ml-2"
              type="button"
              title="Crea datos sintéticos de insolvencia"
            >
              ⚡ Semillar
            </button>
            <button
              onClick={handleResetDatabase}
              className="px-2 py-1 text-xs font-bold uppercase bg-brutalCrimson border-2 border-black text-white hover:bg-black hover:text-white transition-all ml-2"
              type="button"
              title="Borra todas las transacciones y reinicia las cuentas"
            >
              ⚠️ Reiniciar
            </button>

          </div>
        </div>
      </header>

      {/* Modal de Nueva Empresa */}
      {isNewPortfolioModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white border-4 border-black p-6 shadow-brutal max-w-sm w-full">
            <h2 className="text-xl font-bold uppercase mb-4 border-b-2 border-black pb-2">🏢 Agregar Empresa</h2>
            <form onSubmit={handleCreatePortfolio} className="space-y-4">
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
        <div className="bg-brutalCrimson border-3 border-black text-white p-4 mb-6 shadow-brutal flex flex-col space-y-2 uppercase animate-pulse">
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
      <section className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        {/* Tarjeta Ingresos */}
        <div className="bg-white border-3 border-black p-5 shadow-brutal flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase">Total Ingresos</span>
          <div className="mt-2 space-y-1.5">
            <div className="text-base font-bold text-black bg-brutalGreen border-2 border-black py-1 px-2 text-center uppercase tracking-tight font-mono">
              COP {cajaViva.total_ingresos_cop?.toLocaleString('es-CO', { minimumFractionDigits: 2 }) || "0,00"}
            </div>
            <div className="text-base font-bold text-black bg-brutalGreen border-2 border-black py-1 px-2 text-center uppercase tracking-tight font-mono">
              USD {cajaViva.total_ingresos_usd?.toLocaleString('en-US', { minimumFractionDigits: 2 }) || "0.00"}
            </div>
          </div>
        </div>

        {/* Tarjeta Gastos */}
        <div className="bg-white border-3 border-black p-5 shadow-brutal flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase">Total Gastos</span>
          <div className="mt-2 space-y-1.5">
            <div className="text-base font-bold text-black border-2 border-black border-b-brutalCrimson border-b-4 py-1 px-2 text-center tracking-tight font-mono">
              COP {cajaViva.total_gastos_cop?.toLocaleString('es-CO', { minimumFractionDigits: 2 }) || "0,00"}
            </div>
            <div className="text-base font-bold text-black border-2 border-black border-b-brutalCrimson border-b-4 py-1 px-2 text-center tracking-tight font-mono">
              USD {cajaViva.total_gastos_usd?.toLocaleString('en-US', { minimumFractionDigits: 2 }) || "0.00"}
            </div>
          </div>
        </div>

        {/* Tarjeta Balance */}
        <div className="bg-white border-3 border-black p-5 shadow-brutal flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase">Balance Neto</span>
          <div className="mt-2 space-y-1.5">
            <div className="text-base font-bold text-black border-2 border-black bg-brutalNeutral py-1 px-2 text-center tracking-tight font-mono">
              COP {cajaViva.balance_neto_cop?.toLocaleString('es-CO', { minimumFractionDigits: 2 }) || "0,00"}
            </div>
            <div className="text-base font-bold text-black border-2 border-black bg-brutalNeutral py-1 px-2 text-center tracking-tight font-mono">
              USD {cajaViva.balance_neto_usd?.toLocaleString('en-US', { minimumFractionDigits: 2 }) || "0.00"}
            </div>
          </div>
        </div>

        {/* Tarjeta Patrimonio Neto */}
        <div className="bg-white border-3 border-black p-5 shadow-brutal flex flex-col justify-between">
          <div className="flex justify-between items-center">
            <span className="text-xs font-bold text-gray-400 uppercase">Patrimonio Neto</span>
            <span className="text-[9px] text-gray-400 font-bold uppercase">(Capital: 5M COP | 1K USD)</span>
          </div>
          <div className="mt-2 space-y-1.5">
            <div className={`text-base font-bold border-2 border-black py-1 px-2 text-center tracking-tight font-mono ${
              cajaViva.patrimonio_cop < 0 ? "bg-brutalCrimson text-white animate-pulse" : "bg-brutalAmber text-black"
            }`}>
              COP {cajaViva.patrimonio_cop?.toLocaleString('es-CO', { minimumFractionDigits: 2 }) || "0,00"}
            </div>
            <div className={`text-base font-bold border-2 border-black py-1 px-2 text-center tracking-tight font-mono ${
              cajaViva.patrimonio_usd < 0 ? "bg-brutalCrimson text-white animate-pulse" : "bg-brutalAmber text-black"
            }`}>
              USD {cajaViva.patrimonio_usd?.toLocaleString('en-US', { minimumFractionDigits: 2 }) || "0.00"}
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================================== */}
      {/* 💼 SPLIT SCREEN WORKSPACE */}
      {/* ============================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start flex-grow">
        
        {/* ----------------- PANEL IZQUIERDO: REGISTRO & VOZ ----------------- */}
        <div className="lg:col-span-1 space-y-6">
          
          {/* Widget de Perfil de Usuario Principal */}
          <div className="bg-white border-3 border-black p-6 shadow-brutal">
            <h2 className="text-lg font-bold uppercase border-b-2 border-black pb-2 mb-4">👤 Usuario Principal</h2>
            {isEditingProfile ? (
              <form onSubmit={handleUpdateProfile} className="space-y-3">
                <div>
                  <label className="text-xs font-bold uppercase block mb-1">Nombre</label>
                  <input
                    type="text"
                    value={editProfileName}
                    onChange={(e) => setEditProfileName(e.target.value)}
                    required
                    className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase block mb-1">Email</label>
                  <input
                    type="email"
                    value={editProfileEmail}
                    onChange={(e) => setEditProfileEmail(e.target.value)}
                    required
                    className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold uppercase block mb-1">Cargo/Rol</label>
                  <input
                    type="text"
                    value={editProfileRole}
                    onChange={(e) => setEditProfileRole(e.target.value)}
                    required
                    className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                  />
                </div>
                <div className="flex space-x-2 pt-2">
                  <button
                    type="submit"
                    className="flex-1 bg-brutalGreen text-black font-bold border-2 border-black py-1.5 text-xs uppercase hover:bg-black hover:text-white"
                  >
                    Guardar
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsEditingProfile(false)}
                    className="flex-1 bg-brutalCrimson text-white font-bold border-2 border-black py-1.5 text-xs uppercase hover:bg-black"
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            ) : (
              <div className="flex items-center space-x-4">
                {renderPixelAvatar(profile.name)}
                <div className="flex-grow min-w-0">
                  <p className="text-sm font-bold uppercase truncate">{profile.name}</p>
                  <p className="text-[10px] text-gray-500 truncate">{profile.email}</p>
                  <p className="text-xs font-bold text-brutalAmber bg-black px-1.5 py-0.5 mt-1 inline-block uppercase">
                    {profile.role}
                  </p>
                </div>
                <button
                  onClick={() => setIsEditingProfile(true)}
                  className="bg-brutalNeutral border-2 border-black p-1 hover:bg-black hover:text-white transition-all text-xs font-bold"
                  type="button"
                  title="Editar Perfil"
                >
                  ✏️
                </button>
              </div>
            )}
          </div>

          {/* Widget de Gestión de Cuentas */}
          <div className="bg-white border-3 border-black p-6 shadow-brutal">
            <h2 className="text-lg font-bold uppercase border-b-2 border-black pb-2 mb-4">💳 Cuentas Financieras</h2>
            <div className="space-y-2 mb-4 max-h-48 overflow-y-auto">
              {accounts.map((acc) => (
                <div key={acc.id} className="border-2 border-black p-2 flex justify-between items-center bg-brutalBg hover:bg-brutalNeutral">
                  <div>
                    <span className="text-xs font-bold uppercase block">{acc.name}</span>
                    <span className="text-[10px] text-gray-500 uppercase font-mono">{acc.type} ({acc.currency})</span>
                  </div>
                  <span className={`text-xs font-bold font-mono px-2 py-0.5 border border-black ${
                    acc.current_balance < 0 ? "bg-brutalCrimson text-white animate-pulse" : "bg-white text-black"
                  }`}>
                    {acc.currency === "USD" ? "$" : "$"}
                    {acc.current_balance?.toLocaleString('es-CO', { minimumFractionDigits: 2 })}
                  </span>
                </div>
              ))}
            </div>

            {/* Formulario de Agregar Cuenta */}
            <form onSubmit={handleCreateAccount} className="border-2 border-black p-3 bg-white space-y-3">
              <span className="text-xs font-bold uppercase block mb-1 border-b border-black pb-0.5">➕ Agregar Cuenta</span>
              <input
                type="text"
                placeholder="Nombre Cuenta (ej. Bancolombia)"
                value={newAccountName}
                onChange={(e) => setNewAccountName(e.target.value)}
                required
                className="w-full bg-white border border-black p-1.5 text-xs font-mono outline-none focus:border-brutalGreen"
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={newAccountType}
                  onChange={(e) => setNewAccountType(e.target.value)}
                  className="bg-white border border-black p-1 text-xs font-mono outline-none"
                >
                  <option value="Ahorros">Ahorros</option>
                  <option value="Corriente">Corriente</option>
                  <option value="Crédito">Crédito</option>
                  <option value="Crypto">Crypto</option>
                  <option value="Efectivo">Efectivo</option>
                </select>
                <select
                  value={newAccountCurrency}
                  onChange={(e) => setNewAccountCurrency(e.target.value)}
                  className="bg-white border border-black p-1 text-xs font-mono outline-none"
                >
                  <option value="COP">COP</option>
                  <option value="USD">USD</option>
                </select>
              </div>
              <div className="flex space-x-2">
                <input
                  type="number"
                  step="0.01"
                  placeholder="Saldo Inicial"
                  value={newAccountInitialBalance}
                  onChange={(e) => setNewAccountInitialBalance(e.target.value)}
                  className="flex-grow bg-white border border-black p-1 text-xs font-mono outline-none focus:border-brutalGreen"
                />
                <button
                  type="submit"
                  className="bg-black text-white hover:bg-brutalGreen hover:text-black border border-black px-3 font-bold text-xs uppercase"
                >
                  Añadir
                </button>
              </div>
            </form>
          </div>

          {/* Módulo de Grabadora de Voz (Asistencia IA) */}
          <div className="bg-white border-3 border-black p-6 shadow-brutal">
            <h2 className="text-lg font-bold uppercase border-b-2 border-black pb-2 mb-4">🎤 Ingestión por Voz Inteligente</h2>
            <p className="text-xs text-gray-500 uppercase leading-relaxed mb-4">
              Presiona el micrófono y registra libremente. Llama 3.3 y RAG autocompletarán los datos recurrentes como borradores.
            </p>

            <div className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-black bg-brutalBg">
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
            <div className="mt-4 border-2 border-black bg-brutalBg p-3 space-y-2">
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
                <div className="space-y-3 max-h-48 overflow-y-auto">
                  {drafts.map((d, index) => (
                    <div 
                      key={index}
                      onClick={() => loadDraftIntoForm(d)}
                      className="border-2 border-black bg-white p-3 hover:bg-brutalNeutral cursor-pointer flex flex-col justify-between transition-all"
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

          {/* Formulario Manual Módulo 01 */}
          <div className="bg-white border-3 border-black p-6 shadow-brutal">
            <h2 className="text-lg font-bold uppercase border-b-2 border-black pb-2 mb-4">📝 Módulo 01: Registro Contable</h2>
            
            <form onSubmit={handleRegister} className="space-y-4">
              
              {/* Sugerencia Informativa de Campos Faltantes */}
              {formSuggestion && (
                <div className="bg-brutalAmber border-2 border-black p-3 text-xs font-bold uppercase space-y-2">
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
              <div className="grid grid-cols-2 gap-4">
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
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
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
                  <div className="grid grid-cols-2 gap-4">
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
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
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
                  <div className="grid grid-cols-2 gap-4">
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
                <div className="border-2 border-black p-3 bg-brutalAmber space-y-2">
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

              {/* Sección Colapsable: Identificación de Tercero (MANDATORIO) */}
              <div className="border-2 border-black bg-brutalBg shadow-brutal">
                <div 
                  onClick={() => setExpandedTercero(!expandedTercero)}
                  className="p-2.5 flex justify-between items-center cursor-pointer select-none font-bold text-xs uppercase"
                >
                  <span>{expandedTercero ? "[-] IDENTIFICACIÓN DE TERCERO" : "[+] IDENTIFICACIÓN DE TERCERO"}</span>
                  <span className="font-extrabold">{expandedTercero ? "—" : "+"}</span>
                </div>
                {expandedTercero && (
                  <div className="border-t-2 border-black p-3 bg-white space-y-3">
                    <div>
                      <label className="text-[10px] font-bold uppercase block mb-1">Nombre / Tercero</label>
                      <input
                        type="text"
                        value={thirdPartyName}
                        onChange={(e) => setThirdPartyName(e.target.value)}
                        required
                        placeholder="Nombre Completo / Empresa"
                        className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] font-bold uppercase block mb-1">Tipo Identificación</label>
                        <select
                          value={thirdPartyType}
                          onChange={(e) => setThirdPartyType(e.target.value)}
                          className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none"
                        >
                          <option value="NIT">NIT</option>
                          <option value="CC">CC</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-[10px] font-bold uppercase block mb-1">Número ID</label>
                        <input
                          type="text"
                          value={thirdPartyNumber}
                          onChange={(e) => setThirdPartyNumber(e.target.value)}
                          required
                          placeholder="23"
                          className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] font-bold uppercase block mb-1">Correo Electrónico</label>
                        <input
                          type="email"
                          value={thirdPartyEmail}
                          onChange={(e) => setThirdPartyEmail(e.target.value)}
                          placeholder="mail@ejemplo.com"
                          className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold uppercase block mb-1">Número de Contacto</label>
                        <input
                          type="text"
                          value={thirdPartyPhone}
                          onChange={(e) => setThirdPartyPhone(e.target.value)}
                          placeholder="300 123 4567"
                          className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase block mb-1">Web</label>
                      <input
                        type="text"
                        value={thirdPartyWebsite}
                        onChange={(e) => setThirdPartyWebsite(e.target.value)}
                        placeholder="https://www.ejemplo.com"
                        className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                      />
                    </div>
                    
                    <button
                      type="button"
                      onClick={() => setExpandedTercero(false)}
                      className="w-full bg-black text-brutalGreen hover:bg-brutalGreen hover:text-black border-2 border-black py-2 text-xs font-extrabold uppercase transition-all shadow-brutal active:translate-y-0.5"
                    >
                      GUARDAR
                    </button>
                  </div>
                )}
              </div>

              {/* Sección Colapsable: Impuestos y Tasas Ocultas */}
              <div className="border-2 border-black bg-white shadow-brutal">
                <div 
                  onClick={() => setExpandedTaxes(!expandedTaxes)}
                  className="p-2.5 flex justify-between items-center bg-brutalBg cursor-pointer select-none font-bold text-xs uppercase"
                >
                  <span>{expandedTaxes ? "[—] IMPUESTOS Y TASAS OCULTAS" : "[%] IMPUESTOS Y TASAS OCULTAS"}</span>
                  <span className="font-extrabold">{expandedTaxes ? "—" : "+"}</span>
                </div>
                {expandedTaxes && (
                  <div className="border-t-2 border-black p-3 bg-white space-y-4">
                    <div className="space-y-2 border-b-2 border-dashed border-black pb-3">
                      <label className="flex items-center text-xs uppercase font-bold cursor-pointer">
                        <input 
                          type="checkbox"
                          checked={applyIva}
                          onChange={(e) => setApplyIva(e.target.checked)}
                          className="mr-2 h-4 w-4 border-2 border-black rounded-none outline-none accent-black" 
                        />
                        [{applyIva ? "X" : " "}] IVA (19%) - ADITIVO
                      </label>
                      <label className="flex items-center text-xs uppercase font-bold cursor-pointer">
                        <input 
                          type="checkbox"
                          checked={applyPropina}
                          onChange={(e) => setApplyPropina(e.target.checked)}
                          className="mr-2 h-4 w-4 border-2 border-black rounded-none outline-none accent-black" 
                        />
                        [{applyPropina ? "X" : " "}] PROPINA (10%) - ADITIVO
                      </label>
                      <label className="flex items-center text-xs uppercase font-bold cursor-pointer">
                        <input 
                          type="checkbox"
                          checked={applyGmf}
                          onChange={(e) => setApplyGmf(e.target.checked)}
                          className="mr-2 h-4 w-4 border-2 border-black rounded-none outline-none accent-black" 
                        />
                        [{applyGmf ? "X" : " "}] GMF 4X1000 - DEDUCTIVO
                      </label>
                      
                      {customTaxesList.map((tax) => (
                        <label key={tax.id} className="flex items-center text-xs uppercase font-bold cursor-pointer">
                          <input 
                            type="checkbox"
                            checked={tax.checked}
                            onChange={(e) => {
                              const checkedVal = e.target.checked;
                              setCustomTaxesList(prev => prev.map(t => t.id === tax.id ? { ...t, checked: checkedVal } : t));
                            }}
                            className="mr-2 h-4 w-4 border-2 border-black rounded-none outline-none accent-black" 
                          />
                          [{tax.checked ? "X" : " "}] {tax.name} ({tax.rate}%) - {tax.type === "ADDITIVE" ? "ADITIVO" : "DEDUCTIVO"}
                        </label>
                      ))}
                    </div>
                    
                    <div className="space-y-2">
                      <h4 className="text-[10px] font-extrabold uppercase tracking-wider text-black">ADMINISTRADOR DE TASAS PERSONALIZADAS</h4>
                      
                      <div 
                        onClick={() => setIsAddingTaxOpen(!isAddingTaxOpen)}
                        className="border-2 border-black p-2 text-center font-bold text-[10px] uppercase bg-brutalBg cursor-pointer select-none hover:bg-brutalNeutral transition-all"
                      >
                        {isAddingTaxOpen ? "CERRAR FORMULARIO (—)" : "AGREGAR TASA (+)"}
                      </div>
                      
                      {isAddingTaxOpen && (
                        <div className="border-2 border-black p-3 bg-brutalBg space-y-3 text-xs shadow-brutal">
                          <div>
                            <label className="text-[9px] font-bold uppercase block mb-1">Nombre de la Tasa</label>
                            <input
                              type="text"
                              value={newTaxName}
                              onChange={(e) => setNewTaxName(e.target.value)}
                              placeholder="Ej. ICA"
                              className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none"
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="text-[9px] font-bold uppercase block mb-1">Porcentaje (%)</label>
                              <input
                                type="number"
                                step="0.01"
                                value={newTaxRate}
                                onChange={(e) => setNewTaxRate(e.target.value)}
                                placeholder="0.0"
                                className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none"
                              />
                            </div>
                            <div>
                              <label className="text-[9px] font-bold uppercase block mb-1">Tipo</label>
                              <select
                                value={newTaxType}
                                onChange={(e) => setNewTaxType(e.target.value)}
                                className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none"
                              >
                                <option value="ADDITIVE">Aditivo</option>
                                <option value="DEDUCTIVE">Deductivo</option>
                              </select>
                            </div>
                          </div>
                          
                          <button
                            type="button"
                            onClick={() => {
                              if (!newTaxName || !newTaxRate) {
                                alert("❌ Completa el nombre y el porcentaje de la tasa.");
                                return;
                              }
                              const rateVal = parseFloat(newTaxRate);
                              if (isNaN(rateVal)) return;
                              
                              const newTax = {
                                id: String(Date.now()),
                                name: newTaxName.toUpperCase(),
                                rate: rateVal,
                                type: newTaxType,
                                checked: true
                              };
                              setCustomTaxesList(prev => [...prev, newTax]);
                              setNewTaxName("");
                              setNewTaxRate("");
                              setIsAddingTaxOpen(false);
                            }}
                            className="w-full bg-black text-brutalGreen hover:bg-brutalGreen hover:text-black border-2 border-black py-2 text-xs font-extrabold uppercase transition-all"
                          >
                            GUARDAR
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Sección Colapsable: Cartera (CXC / CXP) */}
              <div className="border-2 border-black bg-white shadow-brutal">
                <div 
                  onClick={() => setExpandedCartera(!expandedCartera)}
                  className="p-2.5 flex justify-between items-center bg-brutalBg cursor-pointer select-none font-bold text-xs uppercase"
                >
                  <span>{cxcCxpEnabled ? "[x] CARTERA (CXC / CXP)" : "[+] CARTERA (CXC / CXP)"}</span>
                  <span className="font-extrabold">{expandedCartera ? "—" : "+"}</span>
                </div>
                {expandedCartera && (
                  <div className="p-3 bg-white space-y-3 border-t-2 border-black">
                    <div className="flex items-center space-x-6 py-1">
                      <label className="flex items-center text-xs uppercase font-extrabold cursor-pointer">
                        <input 
                          type="radio"
                          name="cxcCxpType"
                          value="CXC"
                          checked={cxcCxpType === "CXC"}
                          onChange={() => setCxcCxpType("CXC")}
                          className="mr-2 h-4 w-4 border-2 border-black accent-black"
                        />
                        CUENTAS POR COBRAR (CXC)
                      </label>
                      <label className="flex items-center text-xs uppercase font-extrabold cursor-pointer">
                        <input 
                          type="radio"
                          name="cxcCxpType"
                          value="CXP"
                          checked={cxcCxpType === "CXP"}
                          onChange={() => setCxcCxpType("CXP")}
                          className="mr-2 h-4 w-4 border-2 border-black accent-black"
                        />
                        CUENTAS POR PAGAR (CXP)
                      </label>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] font-bold uppercase block mb-1">Fecha*</label>
                        <input
                          type="date"
                          value={cxcCxpDueDate}
                          onChange={(e) => setCxcCxpDueDate(e.target.value)}
                          className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold uppercase block mb-1">Plazo</label>
                        <select
                          value={cxcCxpTerm}
                          onChange={(e) => setCxcCxpTerm(e.target.value)}
                          className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none"
                        >
                          <option value="Corto">Corto</option>
                          <option value="Mediano">Mediano</option>
                          <option value="Largo">Largo</option>
                        </select>
                      </div>
                    </div>
                    
                    <div>
                      <label className="text-[10px] font-bold uppercase block mb-1">Tercero</label>
                      <input
                        type="text"
                        value={thirdPartyName || "Ninguno"}
                        readOnly
                        placeholder="Nombre del Tercero"
                        className="w-full bg-brutalNeutral border-2 border-black p-2 text-xs font-mono outline-none cursor-not-allowed"
                      />
                      <button
                        type="button"
                        onClick={() => setIsThirdPartyModalOpen(true)}
                        className="mt-2 w-full bg-yellow-200 text-black border-2 border-black py-1.5 text-[10px] font-black uppercase hover:bg-yellow-400 transition-all"
                      >
                        {thirdPartyName ? "CAMBIAR TERCERO" : "🔍 ASIGNAR TERCERO"}
                      </button>
                    </div>
                    
                    <button
                      type="button"
                      onClick={() => {
                        if (!cxcCxpDueDate) {
                          alert("❌ Completa la fecha de vencimiento para guardar en cartera.");
                          return;
                        }
                        setCxcCxpEnabled(true);
                        setExpandedCartera(false);
                      }}
                      className="w-full bg-black text-brutalGreen hover:bg-brutalGreen hover:text-black border-2 border-black py-2 text-xs font-extrabold uppercase transition-all shadow-brutal active:translate-y-0.5"
                    >
                      GUARDAR EN CARTERA
                    </button>
                  </div>
                )}
              </div>

              {/* Sección Colapsable: Gestión de Activos */}
              <div className="border-2 border-black bg-white shadow-brutal">
                <div 
                  onClick={() => setExpandedActivos(!expandedActivos)}
                  className="p-2.5 flex justify-between items-center bg-brutalBg cursor-pointer select-none font-bold text-xs uppercase"
                >
                  <span>{assetEnabled && assetEstablecerActivo ? "[x] GESTIÓN DE ACTIVOS" : "[+] GESTIÓN DE ACTIVOS"}</span>
                  <span className="font-extrabold">{expandedActivos ? "—" : "+"}</span>
                </div>
                {expandedActivos && (
                  <div className="p-3 bg-white space-y-3 border-t-2 border-black">
                    <div>
                      <label className="text-[10px] font-bold uppercase block mb-1">Nombre del Activo</label>
                      <input
                        type="text"
                        value={assetName}
                        onChange={(e) => setAssetName(e.target.value)}
                        placeholder="Ej. Equipo de Cómputo"
                        className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] font-bold uppercase block mb-1">Valor</label>
                        <input
                          type="number"
                          value={assetValue}
                          onChange={(e) => setAssetValue(e.target.value)}
                          disabled={assetVincularImporte}
                          placeholder="0.00"
                          className={`w-full border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen ${
                            assetVincularImporte ? "bg-brutalNeutral cursor-not-allowed" : "bg-white"
                          }`}
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold uppercase block mb-1">Etiqueta</label>
                        <input
                          type="text"
                          value={assetTag}
                          onChange={(e) => setAssetTag(e.target.value)}
                          placeholder="Ej. IT"
                          className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
                        />
                      </div>
                    </div>
                    
                    <div className="space-y-1.5 py-1">
                      <label className="flex items-center text-xs uppercase font-extrabold cursor-pointer">
                        <input 
                          type="checkbox"
                          checked={assetVincularImporte}
                          onChange={(e) => setAssetVincularImporte(e.target.checked)}
                          className="mr-2 h-4 w-4 border-2 border-black rounded-none outline-none accent-black" 
                        />
                        [{assetVincularImporte ? "X" : " "}] VINCULAR AL IMPORTE
                      </label>
                      <label className="flex items-center text-xs uppercase font-extrabold cursor-pointer">
                        <input 
                          type="checkbox"
                          checked={assetEstablecerActivo}
                          onChange={(e) => setAssetEstablecerActivo(e.target.checked)}
                          className="mr-2 h-4 w-4 border-2 border-black rounded-none outline-none accent-black" 
                        />
                        [{assetEstablecerActivo ? "X" : " "}] ESTABLECER COMO ACTIVO
                      </label>
                    </div>

                    <div className="border-t border-dashed border-black pt-2 pb-2">
                      <label className="flex items-center text-xs uppercase font-extrabold cursor-pointer">
                        <input 
                          type="checkbox"
                          checked={assetRecurrente}
                          onChange={(e) => setAssetRecurrente(e.target.checked)}
                          className="mr-2 h-4 w-4 border-2 border-black rounded-none outline-none accent-black" 
                        />
                        [{assetRecurrente ? "X" : " "}] VOLVER RECURRENTE
                      </label>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        if (!assetName) {
                          alert("❌ Completa el nombre del activo para guardar.");
                          return;
                        }
                        if (!assetVincularImporte && !assetValue) {
                          alert("❌ Completa el valor del activo o vincúlalo al importe.");
                          return;
                        }
                        setAssetEnabled(true);
                        setAssetEstablecerActivo(true);
                        setExpandedActivos(false);
                      }}
                      className="w-full bg-black text-brutalGreen hover:bg-brutalGreen hover:text-black border-2 border-black py-2 text-xs font-extrabold uppercase transition-all shadow-brutal active:translate-y-0.5"
                    >
                      GUARDAR ACTIVO
                    </button>
                  </div>
                )}
              </div>

              {/* Sección Evidencia / Subir Archivo - Integrada a Módulo 01 */}
              <div className="border-2 border-black p-3 bg-white space-y-2 shadow-brutal">
                <label className="text-[10px] font-bold uppercase block mb-1">EVIDENCIA / COMPROBANTE DE TRANSACCIÓN</label>
                <label className="flex flex-col items-center justify-center border-2 border-dashed border-black p-4 bg-gray-50 cursor-pointer hover:bg-brutalBg transition-all select-none">
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
        </div>

        {/* ----------------- PANEL DERECHO: LIBRO DIARIO DETALLADO ----------------- */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white border-3 border-black p-6 shadow-brutal overflow-hidden flex flex-col">
            <h2 className="text-lg font-bold uppercase border-b-2 border-black pb-2 mb-4">📖 Módulo 02: Libro Diario Inteligente</h2>
            
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
                      <tr key={tx.id} className="hover:bg-brutalBg transition-all" title="Doble clic en una celda para editar (estilo Excel)">
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
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

      </div>

      {/* ============================================================================== */}
      {/* 🖼️ EVIDENCE MODAL POPUP */}
      {/* ============================================================================== */}
      {evidenceUrl && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-white border-3 border-black p-6 max-w-lg w-full shadow-brutal my-8 font-mono">
            <div className="flex justify-between items-center border-b-2 border-black pb-2 mb-4">
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
              <div className="space-y-4">
                {/* Brutalist Simulated Receipt Visualizer */}
                <div className="border-2 border-black p-4 bg-brutalBg text-xs space-y-3 uppercase">
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
                <div className="border-2 border-black p-3 bg-white space-y-2 uppercase text-[10px]">
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
                  <div className="border-2 border-black p-3 bg-white space-y-2 uppercase text-[10px]">
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
