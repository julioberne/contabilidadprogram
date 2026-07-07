import React, { useState, useEffect, useRef } from 'react';
import ThirdPartyModal from './components/ThirdPartyModal';
import ContextPanel from './components/ContextPanel';
import CompanySelector from './components/CompanySelector';
import DashboardPanel from './components/DashboardPanel';
import TransactionForm from './components/TransactionForm';
import LibroDiario from './components/LibroDiario';
import EvidenceModal from './components/EvidenceModal';
import VoiceIngestWidget from './components/VoiceIngestWidget';
import useVoiceRecorder from './hooks/useVoiceRecorder';
import useCalculator from './hooks/useCalculator';
import useAccounts from './hooks/useAccounts';
import useProfile from './hooks/useProfile';
import useTransactionForm from './hooks/useTransactionForm';

import { API } from './config';

const API_BASE_URL = API;

function App() {
  // --- Estados Principales ---
  const [activePortfolio, setActivePortfolio] = useState("Negocio A");
  const [portfolios, setPortfolios] = useState([]);
  const [isNewPortfolioModalOpen, setIsNewPortfolioModalOpen] = useState(false);
  const [newPortfolioName, setNewPortfolioName] = useState("");
  const [newPortfolioIndustry, setNewPortfolioIndustry] = useState("ESTANDAR");
  const [newPortfolioSubIndustry, setNewPortfolioSubIndustry] = useState("");
  // --- Estado de Empresa Activa (entities de Control Tower) ---
  const [activeCompany, setActiveCompany] = useState(null); // { id, name, type, industry, portfolio_id }
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

  // --- Ref estable para romper dependencia circular hooks ↔ fetchData ---
  const fetchDataRef = useRef(null);
  const stableFetchData = useRef((...args) => fetchDataRef.current?.(...args)).current;

  // --- Perfil del Usuario (Hook) ---
  const { profile, setProfile, isEditingProfile, setIsEditingProfile, editProfileName, setEditProfileName, editProfileEmail, setEditProfileEmail, editProfileRole, setEditProfileRole, editProfileAvatar, setEditProfileAvatar, handleUpdateProfile } = useProfile({ fetchData: stableFetchData });

  // --- Gestión de Cuentas Financieras (Hook) ---
  const { accounts, setAccounts, newAccountName, setNewAccountName, newAccountType, setNewAccountType, newAccountCurrency, setNewAccountCurrency, newAccountInitialBalance, setNewAccountInitialBalance, editingAccountId, setEditingAccountId, editAccountName, setEditAccountName, editAccountType, setEditAccountType, editAccountBalance, setEditAccountBalance, handleCreateAccount, handleUpdateAccount, handleDeleteAccount } = useAccounts({ fetchData: stableFetchData });

  // --- Subsecciones del panel izquierdo ---
  const [activeLeftSection, setActiveLeftSection] = useState("registro");

  // --- Formulario de Transacciones (Hook) ---
  const { formType, setFormType, amount, setAmount, concept, setConcept, date, setDate, geoMapsLink, setGeoMapsLink, paymentMethod, setPaymentMethod, category, setCategory, selectedAccountId, setSelectedAccountId, selectedDestAccountId, setSelectedDestAccountId, trmValue, setTrmValue, txCurrency, setTxCurrency, handleAccountChange, sourceAcc, destAcc, isCrossCurrency, thirdPartyType, setThirdPartyType, thirdPartyNumber, setThirdPartyNumber, thirdPartyName, setThirdPartyName, thirdPartyEmail, setThirdPartyEmail, thirdPartyPhone, setThirdPartyPhone, thirdPartyWebsite, setThirdPartyWebsite, isThirdPartyModalOpen, setIsThirdPartyModalOpen, allThirdParties, setAllThirdParties, applyIva, setApplyIva, applyGmf, setApplyGmf, applyPropina, setApplyPropina, isRecurring, setIsRecurring, recurrenceInterval, setRecurrenceInterval, recurrenceDays, setRecurrenceDays, recurrenceMaxReps, setRecurrenceMaxReps, recurrenceStartDate, setRecurrenceStartDate, recurrenceEndDate, setRecurrenceEndDate, cxcCxpEnabled, setCxcCxpEnabled, cxcCxpType, setCxcCxpType, cxcCxpDueDate, setCxcCxpDueDate, cxcCxpTerm, setCxcCxpTerm, cxcCxpValue, setCxcCxpValue, assetEnabled, setAssetEnabled, assetName, setAssetName, assetValue, setAssetValue, assetTag, setAssetTag, assetVincularImporte, setAssetVincularImporte, assetEstablecerActivo, setAssetEstablecerActivo, assetRecurrente, setAssetRecurrente, evidenceFilePath, setEvidenceFilePath, isUploadingEvidence, selectedTags, setSelectedTags, tagSearch, setTagSearch, customTaxesList, setCustomTaxesList, formSuggestion, setFormSuggestion, handleUploadEvidence, handleRegister, loadDraftIntoForm } = useTransactionForm({ activePortfolio, accounts, fetchData: stableFetchData, setDrafts });

  // --- Collapsible sections states (ahora en panel derecho) ---
  const [activeTab, setActiveTab] = useState('terceros');
  const [showVoiceWidget, setShowVoiceWidget] = useState(false);

  // --- Fila expandible Libro Diario ---
  const [expandedTxId, setExpandedTxId] = useState(null);

  // --- Calculadora rápida (Hook) ---
  const { calcOpen, setCalcOpen, calcDisplay, setCalcDisplay, calcPrev, setCalcPrev, calcOp, setCalcOp, calcReset, setCalcReset, calcInput, calcSetOp, calcExecute, calcClear } = useCalculator();

  // --- Grabador de Voz (Hook) ---
  const { isRecording, recordingDuration, isTranscribing, isStructuring, liveTranscript, setLiveTranscript, startRecording, stopRecording, handleStructureTranscript } = useVoiceRecorder({ activePortfolio, setDrafts });
  const [editingCell, setEditingCell] = useState(null); // { txId: number, field: string }
  const [editValue, setEditValue] = useState("");

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
        `${API_BASE_URL}/transactions?limit=50&offset=${offset}${portfolioParam}`
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
  fetchDataRef.current = fetchData;

  // handleAccountChange — ahora en useTransactionForm hook

  // renderCoaSelector — extracted to components/CoaSelector.jsx, used by TransactionForm

  // sourceAcc, destAcc, isCrossCurrency, assetVincularImporte sync — ahora en useTransactionForm hook

  useEffect(() => {
    fetchData();
  }, [activePortfolio]);

  // handleUploadEvidence, handleRegister — ahora en useTransactionForm hook

  // handleUpdateProfile — ahora en useProfile hook
  // handleCreateAccount, handleUpdateAccount, handleDeleteAccount — ahora en useAccounts hook

  // --- Crear Nuevo Portafolio (legacy — ahora se usa CompanySelector) ---
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

  // --- Selección de Empresa desde CompanySelector (bridge entity → portfolio) ---
  const handleSelectCompany = (entity) => {
    setActiveCompany(entity);
    // Bridge: buscar el portfolio asociado a esta entity para mantener compatibilidad
    if (entity.portfolio_id) {
      const matchedPort = portfolios.find(p => p.id === entity.portfolio_id);
      if (matchedPort) {
        setActivePortfolio(matchedPort.name);
        return;
      }
    }
    // Si no hay portfolio_id, mantener el portfolio actual (no pisar con entity.name)
    // El usuario puede cambiar portfolio manualmente desde el DashboardPanel
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

  // startRecording, stopRecording, handleTranscribeAudio, handleStructureTranscript — ahora en useVoiceRecorder hook

  // loadDraftIntoForm — ahora en useTransactionForm hook

  // startEditing — extracted into components/LibroDiario.jsx

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
        {/* Selector de Empresa (CompanySelector — entities de Control Tower) */}
        <CompanySelector
          activeCompanyId={activeCompany?.id}
          onSelectCompany={handleSelectCompany}
          onCompaniesLoaded={(entities) => {
            // Auto-seleccionar la primera empresa si no hay ninguna activa
            if (!activeCompany && entities.length > 0) {
              const firstEmpresa = entities.find(e => e.type === 'EMPRESA') || entities[0];
              handleSelectCompany(firstEmpresa);
            }
          }}
          style={{ flex: 1 }}
        />
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

      {/* Modal de Nueva Empresa — ahora manejado por CompanySelector */}

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
      {/* 📊 DASHBOARD PANEL COLAPSABLE (Fase 2 — reemplaza KPI cards inline) */}
      {/* ============================================================================== */}
      <DashboardPanel
        cajaViva={cajaViva}
        activeCompany={activeCompany}
        activePortfolio={activePortfolio}
        onQuickAction={(action) => {
          if (action === 'registro') setActiveLeftSection('registro');
          if (action === 'tercero') { setActiveTab('terceros'); }
          if (action === 'recurso') { setActiveTab('activos'); }
          if (action === 'balance') { /* scroll to libro diario */ }
        }}
        onSelectCompany={handleSelectCompany}
        onCompaniesChanged={() => {
          // Refrescar el CompanySelector forzando un re-fetch
          // El CompanySelector se refresca solo al montar
        }}
        industryKpis={[]}
        industryData={{}}
      />

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

          {/* Módulo de Voz IA — Widget Colapsable (Extracted) */}
          {activeLeftSection === 'registro' && (
            <VoiceIngestWidget
              showVoiceWidget={showVoiceWidget}
              setShowVoiceWidget={setShowVoiceWidget}
              isRecording={isRecording}
              recordingDuration={recordingDuration}
              isTranscribing={isTranscribing}
              isStructuring={isStructuring}
              liveTranscript={liveTranscript}
              setLiveTranscript={setLiveTranscript}
              startRecording={startRecording}
              stopRecording={stopRecording}
              handleStructureTranscript={handleStructureTranscript}
              drafts={drafts}
              loadDraftIntoForm={loadDraftIntoForm}
            />
          )}

          {/* Formulario Manual Módulo 01 (Extracted) */}
          {activeLeftSection === 'registro' && (
            <TransactionForm
              calcOpen={calcOpen} setCalcOpen={setCalcOpen}
              calcDisplay={calcDisplay} setCalcDisplay={setCalcDisplay}
              calcPrev={calcPrev} setCalcPrev={setCalcPrev}
              calcOp={calcOp} setCalcOp={setCalcOp}
              calcReset={calcReset} setCalcReset={setCalcReset}
              setAmount={setAmount}
              formType={formType} setFormType={setFormType}
              amount={amount} concept={concept} setConcept={setConcept}
              date={date} setDate={setDate}
              geoMapsLink={geoMapsLink} setGeoMapsLink={setGeoMapsLink}
              paymentMethod={paymentMethod} setPaymentMethod={setPaymentMethod}
              category={category} setCategory={setCategory}
              selectedAccountId={selectedAccountId} setSelectedAccountId={setSelectedAccountId}
              selectedDestAccountId={selectedDestAccountId} setSelectedDestAccountId={setSelectedDestAccountId}
              trmValue={trmValue} setTrmValue={setTrmValue}
              txCurrency={txCurrency} setTxCurrency={setTxCurrency}
              handleAccountChange={handleAccountChange}
              sourceAcc={sourceAcc} destAcc={destAcc} isCrossCurrency={isCrossCurrency}
              isRecurring={isRecurring} setIsRecurring={setIsRecurring}
              recurrenceInterval={recurrenceInterval} setRecurrenceInterval={setRecurrenceInterval}
              recurrenceDays={recurrenceDays} setRecurrenceDays={setRecurrenceDays}
              recurrenceMaxReps={recurrenceMaxReps} setRecurrenceMaxReps={setRecurrenceMaxReps}
              recurrenceStartDate={recurrenceStartDate} setRecurrenceStartDate={setRecurrenceStartDate}
              recurrenceEndDate={recurrenceEndDate} setRecurrenceEndDate={setRecurrenceEndDate}
              evidenceFilePath={evidenceFilePath} isUploadingEvidence={isUploadingEvidence} handleUploadEvidence={handleUploadEvidence}
              formSuggestion={formSuggestion} setFormSuggestion={setFormSuggestion}
              handleRegister={handleRegister}
              coaFlatAccounts={coaFlatAccounts} coaSearchQuery={coaSearchQuery} setCoaSearchQuery={setCoaSearchQuery}
              isCoaSearchFocused={isCoaSearchFocused} setIsCoaSearchFocused={setIsCoaSearchFocused}
              handleLoadCoaTemplate={handleLoadCoaTemplate}
              accounts={accounts}
              activeCompany={activeCompany} activePortfolio={activePortfolio} fetchData={fetchData}
            />
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
            activeCompany={activeCompany}
            onCompanyUpdated={(updated) => setActiveCompany(updated)}
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

        {/* ── FILA INFERIOR: Libro Diario ancho completo (Extracted) ── */}
        <LibroDiario
          transactions={transactions}
          totalTxCount={totalTxCount}
          loadingMore={loadingMore}
          loadMoreTransactions={loadMoreTransactions}
          expandedTxId={expandedTxId} setExpandedTxId={setExpandedTxId}
          editingCell={editingCell} setEditingCell={setEditingCell}
          editValue={editValue} setEditValue={setEditValue}
          saveInlineEdit={saveInlineEdit}
          toggleRecurrence={toggleRecurrence}
          accounts={accounts}
          coaFlatAccounts={coaFlatAccounts}
          onEvidenceClick={(tx) => {
            setSelectedEvidenceTx(tx);
            setEvidenceUrl(tx.evidence_file_path || "recibo_demo.png");
          }}
        />

        </div>{/* fin flex-col workspace */}

      {/* 🖼️ EVIDENCE MODAL POPUP (Extracted) */}
      <EvidenceModal
        evidenceUrl={evidenceUrl}
        selectedEvidenceTx={selectedEvidenceTx}
        onClose={() => {
          setEvidenceUrl(null);
          setSelectedEvidenceTx(null);
        }}
        profile={profile}
      />

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
