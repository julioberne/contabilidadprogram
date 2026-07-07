// CarteraTab.jsx — Orchestrator (state + handlers)
// Extracted components: CarteraKpiBar, CarteraLedgerTable, CarteraNewForm
import React from 'react';
import { getDueSemaforo, SORT_OPTIONS, sortFns } from '../cartera/helpers';
import CarteraKpiBar from '../cartera/CarteraKpiBar';
import CarteraLedgerTable from '../cartera/CarteraLedgerTable';
import CarteraNewForm from '../cartera/CarteraNewForm';

// ══════════════════════════════════════════════════════
// CarteraTab — Componente completo CXC/CXP v2
// ══════════════════════════════════════════════════════
export default function CarteraTab({ cartera, allThirdParties, setAllThirdParties, panelCartera, fetchCartera, SectionLabel, API_BASE, refreshTP }) {
  const today = new Date();
  const todayStr = today.toISOString().split('T')[0];
  const [kpiOpen, setKpiOpen] = React.useState(true);
  const [kpi, setKpi] = React.useState(null);
  const [tpSearch, setTpSearch] = React.useState('');
  const [selectedTpId, setSelectedTpId] = React.useState('');
  const [selectedTpLabel, setSelectedTpLabel] = React.useState('');
  const [showTpCreate, setShowTpCreate] = React.useState(false);
  const [newTpName, setNewTpName] = React.useState('');
  const [newTpIdType, setNewTpIdType] = React.useState('NIT');
  const [newTpIdNum, setNewTpIdNum] = React.useState('');
  const [newTpEmail, setNewTpEmail] = React.useState('');
  const [formType, setFormType] = React.useState('CXC');
  const [formTerm, setFormTerm] = React.useState('Corto');
  const [formStartDate, setFormStartDate] = React.useState(todayStr);
  const [formDue, setFormDue] = React.useState('');
  const [formAmount, setFormAmount] = React.useState('');
  const [formPartial, setFormPartial] = React.useState('');
  const [formFrequency, setFormFrequency] = React.useState('30');
  const [formFreqCustom, setFormFreqCustom] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  // Sub-tabs filter + sort
  const [subTab, setSubTab] = React.useState('TODAS');
  const [sortBy, setSortBy] = React.useState('urgente');
  // Zona 1 → 2 selection
  const [selectedLedger, setSelectedLedger] = React.useState(null);
  const [payments, setPayments] = React.useState([]);
  const [loadingPay, setLoadingPay] = React.useState(false);
  // Abono form
  const [abonoAmt, setAbonoAmt] = React.useState('');
  const [abonoDate, setAbonoDate] = React.useState(todayStr);
  const [abonoNote, setAbonoNote] = React.useState('');
  const [abonoOpen, setAbonoOpen] = React.useState(false);
  // Form collapsed
  const [formOpen, setFormOpen] = React.useState(false);
  // Journal entry preview (Zero-COA)
  const [showAsiento, setShowAsiento] = React.useState(false);
  const [asientoPreview, setAsientoPreview] = React.useState(null);
  // Alerts
  const [alerts, setAlerts] = React.useState([]);
  const [alertsOpen, setAlertsOpen] = React.useState(true);
  // Expanded note
  const [expandedNote, setExpandedNote] = React.useState(null);

  React.useEffect(() => {
    fetch(`${API_BASE}/cartera/summary`).then(r => r.ok ? r.json() : null).then(d => d && setKpi(d)).catch(() => {});
    fetch(`${API_BASE}/cartera/alerts`).then(r => r.ok ? r.json() : null).then(d => d && setAlerts(d.alerts || [])).catch(() => {});
  }, [panelCartera]);

  const loadPayments = async (ledger) => {
    if (selectedLedger?.id === ledger.id) { setSelectedLedger(null); setPayments([]); return; }
    setSelectedLedger(ledger); setLoadingPay(true); setAbonoOpen(false);
    try {
      const r = await fetch(`${API_BASE}/cartera/${ledger.id}/payments`);
      if (r.ok) setPayments(await r.json());
    } catch(e) {} finally { setLoadingPay(false); }
  };

  const handleSaveCartera = async () => {
    if (!selectedTpId || !formDue || !formAmount) return;
    setSaving(true);
    const freq = formFrequency === 'custom' ? parseInt(formFreqCustom) || 30 : parseInt(formFrequency);
    try {
      const r = await fetch(`${API_BASE}/cartera`, {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          third_party_id: parseInt(selectedTpId), type: formType, term: formTerm,
          original_amount: parseFloat(formAmount), due_date: formDue,
          start_date: formStartDate,
          partial_payment: parseFloat(formPartial) || 0,
          payment_frequency: freq
        })
      });
      if (r.ok) {
        setFormAmount(''); setFormPartial(''); setFormDue('');
        setFormStartDate(todayStr); setFormFrequency('30'); setFormFreqCustom('');
        setSelectedTpId(''); setSelectedTpLabel('');
        setFormOpen(false);
        fetchCartera();
      }
    } catch(e) {} finally { setSaving(false); }
  };

  const handleCreateTp = async () => {
    if (!newTpName.trim()) return;
    try {
      const r = await fetch(`${API_BASE}/third-parties`, {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ name: newTpName.trim(), identification_type: newTpIdType,
          identification_number: newTpIdNum, email: newTpEmail })
      });
      if (!r.ok) return;
      const created = await r.json();
      const newId = String(created.id || '');
      const newLabel = `${newTpName.trim()} · ${newTpIdType} ${newTpIdNum}`;

      // Actualizar estado de tercero
      await refreshTP();
      setSelectedTpId(newId);
      setSelectedTpLabel(newLabel);
      setShowTpCreate(false); setNewTpName(''); setNewTpIdNum(''); setNewTpEmail('');

      // Guardar cuenta CXC/CXP directamente usando el id recién creado (no depender de state async)
      if (!formDue || !formAmount) return; // Sin monto/fecha no guardamos
      setSaving(true);
      const freq = formFrequency === 'custom' ? parseInt(formFreqCustom) || 30 : parseInt(formFrequency);
      const rSave = await fetch(`${API_BASE}/cartera`, {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          third_party_id: parseInt(newId), type: formType, term: formTerm,
          original_amount: parseFloat(formAmount), due_date: formDue,
          start_date: formStartDate,
          partial_payment: parseFloat(formPartial) || 0,
          payment_frequency: freq
        })
      });
      if (rSave.ok) {
        setFormAmount(''); setFormPartial(''); setFormDue('');
        setFormStartDate(todayStr); setFormFrequency('30'); setFormFreqCustom('');
        setSelectedTpId(''); setSelectedTpLabel('');
        setFormOpen(false);
        fetchCartera();
        // Refrescar KPIs y alertas
        fetch(`${API_BASE}/cartera/summary`).then(r2 => r2.ok ? r2.json() : null).then(d => d && setKpi(d)).catch(()=>{});
      } else {
        // Si falla la cuenta, avisar pero el tercero ya quedó creado
        console.error('Tercero creado pero falló al guardar la cuenta:', await rSave.text());
      }
    } catch(e) {
      console.error('Error en Crear y Seleccionar:', e);
    } finally {
      setSaving(false);
    }
  };

  const handleAbono = async () => {
    if (!abonoAmt || !selectedLedger) return;
    const r = await fetch(`${API_BASE}/cartera/${selectedLedger.id}/payment`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ amount: parseFloat(abonoAmt), payment_date: abonoDate, note: abonoNote })
    });
    if (r.ok) {
      setAbonoAmt(''); setAbonoNote('');
      // Re-fetch to get updated balance
      const updatedList = await fetch(`${API_BASE}/cartera`).then(r2 => r2.ok ? r2.json() : []);
      const updatedLedger = updatedList.find(c => c.id === selectedLedger.id);
      if (updatedLedger) setSelectedLedger(updatedLedger);
      await loadPayments(updatedLedger || selectedLedger);
      fetchCartera();
    }
  };

  // Bind getDueSemaforo to today
  const getDueSemaforoToday = (dueDateStr) => getDueSemaforo(dueDateStr, today);

  const saldo = Math.max(0, parseFloat(formAmount || 0) - parseFloat(formPartial || 0));
  const filteredTps = allThirdParties.filter(tp =>
    !tpSearch || tp.name.toLowerCase().includes(tpSearch.toLowerCase()) || (tp.identification_number||'').includes(tpSearch)
  ).slice(0, 6);

  // Sub-tab filtering
  const typeFiltered = panelCartera.filter(c => {
    if (subTab === 'CXC') return c.type === 'CXC';
    if (subTab === 'CXP') return c.type === 'CXP';
    return true;
  });

  const filteredCartera = [...typeFiltered].sort(sortFns[sortBy] || sortFns['urgente']);

  const cxcCount = panelCartera.filter(c => c.type === 'CXC').length;
  const cxpCount = panelCartera.filter(c => c.type === 'CXP').length;

  return (
    <div className="space-y-2">

      <CarteraKpiBar
        kpi={kpi} kpiOpen={kpiOpen} setKpiOpen={setKpiOpen}
        alerts={alerts} alertsOpen={alertsOpen} setAlertsOpen={setAlertsOpen}
      />

      <CarteraLedgerTable
        filteredCartera={filteredCartera} subTab={subTab} setSubTab={setSubTab}
        sortBy={sortBy} setSortBy={setSortBy} panelCartera={panelCartera}
        cxcCount={cxcCount} cxpCount={cxpCount} SORT_OPTIONS={SORT_OPTIONS}
        selectedLedger={selectedLedger} loadPayments={loadPayments}
        payments={payments} loadingPay={loadingPay}
        expandedNote={expandedNote} setExpandedNote={setExpandedNote}
        getDueSemaforo={getDueSemaforoToday}
        abonoOpen={abonoOpen} setAbonoOpen={setAbonoOpen}
        abonoAmt={abonoAmt} setAbonoAmt={setAbonoAmt}
        abonoDate={abonoDate} setAbonoDate={setAbonoDate}
        abonoNote={abonoNote} setAbonoNote={setAbonoNote}
        handleAbono={handleAbono}
        setSelectedLedger={setSelectedLedger} setPayments={setPayments}
      />

      <CarteraNewForm
        formOpen={formOpen} setFormOpen={setFormOpen}
        formType={formType} setFormType={setFormType}
        formTerm={formTerm} setFormTerm={setFormTerm}
        selectedTpId={selectedTpId} selectedTpLabel={selectedTpLabel}
        setSelectedTpId={setSelectedTpId} setSelectedTpLabel={setSelectedTpLabel}
        tpSearch={tpSearch} setTpSearch={setTpSearch}
        filteredTps={filteredTps}
        showTpCreate={showTpCreate} setShowTpCreate={setShowTpCreate}
        newTpName={newTpName} setNewTpName={setNewTpName}
        newTpIdType={newTpIdType} setNewTpIdType={setNewTpIdType}
        newTpIdNum={newTpIdNum} setNewTpIdNum={setNewTpIdNum}
        newTpEmail={newTpEmail} setNewTpEmail={setNewTpEmail}
        handleCreateTp={handleCreateTp}
        formStartDate={formStartDate} setFormStartDate={setFormStartDate}
        formDue={formDue} setFormDue={setFormDue}
        formFrequency={formFrequency} setFormFrequency={setFormFrequency}
        formFreqCustom={formFreqCustom} setFormFreqCustom={setFormFreqCustom}
        formAmount={formAmount} setFormAmount={setFormAmount}
        formPartial={formPartial} setFormPartial={setFormPartial}
        saldo={saldo}
        showAsiento={showAsiento} setShowAsiento={setShowAsiento}
        asientoPreview={asientoPreview} setAsientoPreview={setAsientoPreview}
        handleSaveCartera={handleSaveCartera} saving={saving}
        API_BASE={API_BASE}
      />

    </div>
  );
}
