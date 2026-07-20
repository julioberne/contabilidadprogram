import React, { useState, useEffect } from 'react';

// ── Tab components (extracted) ──
import CarteraTab from './tabs/CarteraTab';
import TercerosTab from './tabs/TercerosTab';
import ActivosTab from './tabs/ActivosTab';
import EtiquetasTab from './tabs/EtiquetasTab';
import ImpuestosTab from './tabs/ImpuestosTab';
import CuentasTab from './tabs/CuentasTab';
import ConfigTab from './tabs/ConfigTab';
import { API as API_BASE } from '../../config';

const PANEL_TABS = [
  { key: 'terceros',  icon: '👤', label: 'Terceros' },
  { key: 'cartera',   icon: '📄', label: 'Cartera' },
  { key: 'activos',   icon: '📦', label: 'Recursos' },
  { key: 'etiquetas', icon: '🏷️', label: 'Tags' },
  { key: 'impuestos', icon: '📈', label: 'Tasas' },
  { key: 'cuentas',   icon: '💳', label: 'Cuentas' },
  { key: 'usuario',   icon: '⚙', label: 'Config' },
];


/**
 * Panel Contextual v3 — FORM + BD por tab
 * Cada tab muestra: formulario de inputs arriba + tabla CRUD de BD abajo
 */
export default function ContextPanel({

  activeTab, setActiveTab,
  // --- Tercero form ---
  tercero = {},
  // --- Impuestos form ---
  taxes = {},
  // --- Cartera form ---
  cartera = {},
  // --- Activos form ---
  assets: assetForm = {},
  // --- Tags ---
  tagState = {},
  // --- BD data ---
  allThirdParties = [], setAllThirdParties,
  activePortfolio,
  activeCompany = null,     // Entity activa (id, name, industry)
  onCompanyUpdated,         // Callback cuando se actualiza la empresa
  accounts = [],
  profile = {},
  // --- Profile editing ---
  profileEdit = {},
}) {
  // --- Panel DB states ---
  const [panelTags, setPanelTags] = useState([]);
  const [panelTaxes, setPanelTaxes] = useState([]);
  const [panelAssets, setPanelAssets] = useState([]);
  const [panelCartera, setPanelCartera] = useState([]);
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editData, setEditData] = useState({});
  const [newTag, setNewTag] = useState("");
  const [newTaxName, setNewTaxName] = useState("");
  const [newTaxRate, setNewTaxRate] = useState("");
  const [newTaxType, setNewTaxType] = useState("ADDITIVE");
  // Account form
  const [newAccName, setNewAccName] = useState("");
  const [newAccType, setNewAccType] = useState("Ahorros");
  const [newAccCurrency, setNewAccCurrency] = useState("COP");
  const [newAccBalance, setNewAccBalance] = useState("");

  useEffect(() => {
    setSearch(""); setEditingId(null);
    if (activeTab === 'etiquetas') fetchTags();
    if (activeTab === 'impuestos') fetchTaxes();
    if (activeTab === 'activos') fetchAssets();
    if (activeTab === 'cartera') fetchCartera();
  }, [activeTab, activePortfolio]);

  const fetchTags = async () => { try { const r = await fetch(`${API_BASE}/tags`); if (r.ok) setPanelTags(await r.json()); } catch(e) {} };
  const fetchTaxes = async () => { try { const r = await fetch(`${API_BASE}/custom-taxes`); if (r.ok) setPanelTaxes(await r.json()); } catch(e) {} };
  const fetchAssets = async () => { try { const r = await fetch(`${API_BASE}/assets?portfolio=${encodeURIComponent(activePortfolio)}`); if (r.ok) setPanelAssets(await r.json()); } catch(e) {} };
  const fetchCartera = async () => { try { const r = await fetch(`${API_BASE}/cartera`); if (r.ok) setPanelCartera(await r.json()); } catch(e) {} };
  const refreshTP = async () => { const r = await fetch(`${API_BASE}/third-parties`); if (r.ok) setAllThirdParties(await r.json()); };

  const deleteItem = async (ep, id, fn) => { if (!confirm("¿Eliminar?")) return; try { const r = await fetch(`${API_BASE}/${ep}/${id}`, {method:'DELETE'}); if(r.ok) fn(); } catch(e){} };
  const updateItem = async (ep, id, d, fn) => { try { const r = await fetch(`${API_BASE}/${ep}/${id}`, {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)}); if(r.ok){setEditingId(null);fn();}} catch(e){} };

  // --- Helpers ---
  const SectionLabel = ({ text }) => <div className="text-[8px] font-mono text-gray-400 uppercase border-b border-dashed border-gray-200 pb-1 mb-1.5">{text}</div>;

  const handleAddAccount = async (e) => {
    e.preventDefault();
    if (!newAccName.trim()) return;
    try {
      const r = await fetch(`${API_BASE}/user-accounts`, {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ name: newAccName.trim(), type: newAccType, currency: newAccCurrency, initial_balance: parseFloat(newAccBalance) || 0, portfolio: activePortfolio })
      });
      if (r.ok) { setNewAccName(''); setNewAccBalance(''); /* parent will refetch */ }
    } catch(e) { console.error(e); }
  };

  return (
    <div className="lg:col-span-3 border-2 border-black bg-white shadow-brutal flex flex-col overflow-hidden" style={{ maxHeight: 'calc(100vh - 160px)' }}>

      {/* ═══ TABS BAR ═══ */}
      <div className="flex border-b-2 border-black bg-brutalBg overflow-x-auto shrink-0">
        {PANEL_TABS.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`px-2 py-1.5 text-[9px] font-mono font-bold uppercase whitespace-nowrap border-r border-black transition-all ${activeTab === tab.key ? 'bg-black text-white' : 'hover:bg-brutalNeutral text-gray-500'}`}
          >{tab.icon} {tab.label}</button>
        ))}
      </div>

      {/* ═══ CONTENT ═══ */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">

        {/* ════════════════════════════════════════════ */}
        {/* TAB: TERCEROS — Form + BD */}
        {/* ════════════════════════════════════════════ */}
        {activeTab === 'terceros' && <TercerosTab
          search={search} setSearch={setSearch}
          tercero={tercero}
          allThirdParties={allThirdParties}
          editingId={editingId} setEditingId={setEditingId}
          editData={editData} setEditData={setEditData}
          updateItem={updateItem} deleteItem={deleteItem} refreshTP={refreshTP}
          SectionLabel={SectionLabel}
        />}

        {/* ════════════════════════════════════════════ */}
        {/* TAB: CARTERA CXC/CXP — Diseño Completo v2 */}
        {/* ════════════════════════════════════════════ */}
        {activeTab === 'cartera' && <CarteraTab
          cartera={cartera}
          allThirdParties={allThirdParties}
          setAllThirdParties={setAllThirdParties}
          panelCartera={panelCartera}
          fetchCartera={fetchCartera}
          SectionLabel={SectionLabel}
          API_BASE={API_BASE}
          refreshTP={refreshTP}
        />}

        {/* ════════════════════════════════════════════ */}
        {/* TAB: RECURSOS / ACTIVOS — Form + BD */}
        {/* ════════════════════════════════════════════ */}
        {activeTab === 'activos' && <ActivosTab
          assetForm={assetForm}
          panelAssets={panelAssets}
          editingId={editingId} setEditingId={setEditingId}
          editData={editData} setEditData={setEditData}
          deleteItem={deleteItem} fetchAssets={fetchAssets}
          activePortfolio={activePortfolio}
          activeCompany={activeCompany}
          SectionLabel={SectionLabel}
        />}

        {/* ════════════════════════════════════════════ */}
        {/* TAB: ETIQUETAS — Selector + BD */}
        {/* ════════════════════════════════════════════ */}
        {activeTab === 'etiquetas' && <EtiquetasTab
          tagState={tagState}
          panelTags={panelTags}
          editingId={editingId} setEditingId={setEditingId}
          editData={editData} setEditData={setEditData}
          updateItem={updateItem} deleteItem={deleteItem} fetchTags={fetchTags}
          newTag={newTag} setNewTag={setNewTag}
          API_BASE={API_BASE}
          SectionLabel={SectionLabel}
        />}

        {/* ════════════════════════════════════════════ */}
        {/* TAB: IMPUESTOS / TASAS — Form + BD */}
        {/* ════════════════════════════════════════════ */}
        {activeTab === 'impuestos' && <ImpuestosTab
          taxes={taxes}
          panelTaxes={panelTaxes}
          editingId={editingId} setEditingId={setEditingId}
          editData={editData} setEditData={setEditData}
          deleteItem={deleteItem} fetchTaxes={fetchTaxes}
          newTaxName={newTaxName} setNewTaxName={setNewTaxName}
          newTaxRate={newTaxRate} setNewTaxRate={setNewTaxRate}
          newTaxType={newTaxType} setNewTaxType={setNewTaxType}
          API_BASE={API_BASE}
          SectionLabel={SectionLabel}
        />}

        {/* ════════════════════════════════════════════ */}
        {/* TAB: CUENTAS — Form + BD */}
        {/* ════════════════════════════════════════════ */}
        {activeTab === 'cuentas' && <CuentasTab
          accounts={accounts}
          newAccName={newAccName} setNewAccName={setNewAccName}
          newAccType={newAccType} setNewAccType={setNewAccType}
          newAccCurrency={newAccCurrency} setNewAccCurrency={setNewAccCurrency}
          newAccBalance={newAccBalance} setNewAccBalance={setNewAccBalance}
          handleAddAccount={handleAddAccount}
          SectionLabel={SectionLabel}
        />}

        {/* ════════════════════════════════════════════ */}
        {/* TAB: CONFIG / USUARIO */}
        {/* ════════════════════════════════════════════ */}
        {activeTab === 'usuario' && <ConfigTab
          profile={profile}
          profileEdit={profileEdit}
          activePortfolio={activePortfolio}
          activeCompany={activeCompany}
          onCompanyUpdated={onCompanyUpdated}
          API_BASE={API_BASE}
          SectionLabel={SectionLabel}
        />}

      </div>
    </div>
  );
}
