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
  // Plan de pagos (Fase 1 — opcional): cuota mínima por corte + interés simple
  const [planOpen, setPlanOpen] = React.useState(false);
  const [formMinPayment, setFormMinPayment] = React.useState('');
  const [interestOn, setInterestOn] = React.useState(false);
  const [formInterestRate, setFormInterestRate] = React.useState('');
  const [formInterestPeriod, setFormInterestPeriod] = React.useState('MENSUAL');
  const [saving, setSaving] = React.useState(false);
  // Sub-tabs filter + sort + buscador
  const [subTab, setSubTab] = React.useState('TODAS');
  const [sortBy, setSortBy] = React.useState('urgente');
  const [searchQ, setSearchQ] = React.useState('');
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
          payment_frequency: freq,
          min_payment: planOpen && parseFloat(formMinPayment) > 0 ? parseFloat(formMinPayment) : null,
          interest_rate: planOpen && interestOn && parseFloat(formInterestRate) > 0 ? parseFloat(formInterestRate) : null,
          interest_period: formInterestPeriod
        })
      });
      if (r.ok) {
        setFormAmount(''); setFormPartial(''); setFormDue('');
        setFormStartDate(todayStr); setFormFrequency('30'); setFormFreqCustom('');
        setPlanOpen(false); setFormMinPayment(''); setInterestOn(false); setFormInterestRate('');
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
          payment_frequency: freq,
          min_payment: planOpen && parseFloat(formMinPayment) > 0 ? parseFloat(formMinPayment) : null,
          interest_rate: planOpen && interestOn && parseFloat(formInterestRate) > 0 ? parseFloat(formInterestRate) : null,
          interest_period: formInterestPeriod
        })
      });
      if (rSave.ok) {
        setFormAmount(''); setFormPartial(''); setFormDue('');
        setFormStartDate(todayStr); setFormFrequency('30'); setFormFreqCustom('');
        setPlanOpen(false); setFormMinPayment(''); setInterestOn(false); setFormInterestRate('');
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

  // Refresco sin colapsar el detalle (para cuota rápida y edición de plan)
  const refreshLedger = async (id) => {
    const list = await fetch(`${API_BASE}/cartera`).then(r2 => r2.ok ? r2.json() : []);
    const led = list.find(c => c.id === id);
    if (led) setSelectedLedger(led);
    try {
      const rp = await fetch(`${API_BASE}/cartera/${id}/payments`);
      if (rp.ok) setPayments(await rp.json());
    } catch(e) {}
    fetchCartera();
  };

  // ⚡ Cuota rápida: registra un abono por la cuota mínima en un clic
  const handleQuickCuota = async (ledger) => {
    const cuota = ledger?.plan?.cuota_minima;
    if (!cuota) return;
    if (!window.confirm(`¿Registrar abono de $${Number(cuota).toLocaleString('es-CO')} (cuota mínima) a ${ledger.third_party_name}?`)) return;
    const r = await fetch(`${API_BASE}/cartera/${ledger.id}/payment`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ amount: cuota, payment_date: todayStr,
                             note: `Cuota mínima c/${ledger.payment_frequency || 30}d` })
    });
    if (r.ok) await refreshLedger(ledger.id);
    else alert('No se pudo registrar la cuota.');
  };

  // 📐 Definir/editar el plan de una cuenta existente
  const handleSavePlan = async (ledgerId, plan) => {
    const r = await fetch(`${API_BASE}/cartera/${ledgerId}/plan`, {
      method: 'PUT', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(plan)
    });
    if (r.ok) { await refreshLedger(ledgerId); return true; }
    alert('No se pudo guardar el plan.');
    return false;
  };

  // Bind getDueSemaforo to today
  const getDueSemaforoToday = (dueDateStr) => getDueSemaforo(dueDateStr, today);

  const saldo = Math.max(0, parseFloat(formAmount || 0) - parseFloat(formPartial || 0));
  const filteredTps = allThirdParties.filter(tp =>
    !tpSearch || tp.name.toLowerCase().includes(tpSearch.toLowerCase()) || (tp.identification_number||'').includes(tpSearch)
  ).slice(0, 6);

  // Sub-tab filtering + buscador (tercero, NIT/CC, concepto)
  const q = searchQ.trim().toLowerCase();
  const typeFiltered = panelCartera.filter(c => {
    if (subTab === 'CXC' && c.type !== 'CXC') return false;
    if (subTab === 'CXP' && c.type !== 'CXP') return false;
    if (!q) return true;
    return (c.third_party_name || '').toLowerCase().includes(q)
        || (c.identification_number || '').includes(q)
        || (c.concept || '').toLowerCase().includes(q);
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
        searchQ={searchQ} setSearchQ={setSearchQ}
        handleQuickCuota={handleQuickCuota} handleSavePlan={handleSavePlan}
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
        planOpen={planOpen} setPlanOpen={setPlanOpen}
        formMinPayment={formMinPayment} setFormMinPayment={setFormMinPayment}
        interestOn={interestOn} setInterestOn={setInterestOn}
        formInterestRate={formInterestRate} setFormInterestRate={setFormInterestRate}
        formInterestPeriod={formInterestPeriod} setFormInterestPeriod={setFormInterestPeriod}
        saldo={saldo}
        showAsiento={showAsiento} setShowAsiento={setShowAsiento}
        asientoPreview={asientoPreview} setAsientoPreview={setAsientoPreview}
        handleSaveCartera={handleSaveCartera} saving={saving}
        API_BASE={API_BASE}
      />

    </div>
  );
}
