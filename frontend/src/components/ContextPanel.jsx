import React, { useState, useEffect } from 'react';

const API_BASE = "http://127.0.0.1:8000/api";

const PANEL_TABS = [
  { key: 'terceros',  icon: '👤', label: 'Terceros' },
  { key: 'cartera',   icon: '📄', label: 'Cartera' },
  { key: 'activos',   icon: '📦', label: 'Recursos' },
  { key: 'etiquetas', icon: '🏷️', label: 'Tags' },
  { key: 'impuestos', icon: '📈', label: 'Tasas' },
  { key: 'cuentas',   icon: '💳', label: 'Cuentas' },
  { key: 'usuario',   icon: '⚙', label: 'Config' },
];

// ══════════════════════════════════════════════════════
// CarteraTab — Componente completo CXC/CXP v2
// ══════════════════════════════════════════════════════
function CarteraTab({ cartera, allThirdParties, setAllThirdParties, panelCartera, fetchCartera, SectionLabel, API_BASE, refreshTP }) {
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

  // Semáforo de vencimiento
  const getDueSemaforo = (dueDateStr) => {
    if (!dueDateStr) return { dot: '⚪', label: '—', cls: 'text-gray-400' };
    const due = new Date(dueDateStr);
    const diffDays = Math.round((due - today) / 86400000);
    if (diffDays < 0) return { dot: '🔴', label: `${Math.abs(diffDays)}d vencido`, cls: 'text-red-600 font-bold' };
    if (diffDays <= 7) return { dot: '🟡', label: `${diffDays}d`, cls: 'text-amber-600 font-bold' };
    return { dot: '🟢', label: `${diffDays}d`, cls: 'text-green-700' };
  };

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

  // Sorting logic
  const sortFns = {
    'urgente': (a, b) => {
      // VENCIDO first, then by due_date ascending (most urgent)
      const sp = { VENCIDO: 0, PENDIENTE: 1, PAGADO: 2 };
      const sa = sp[a.status] ?? 1, sb = sp[b.status] ?? 1;
      if (sa !== sb) return sa - sb;
      return new Date(a.due_date || '2099-01-01') - new Date(b.due_date || '2099-01-01');
    },
    'monto-desc': (a, b) => (b.original_amount || 0) - (a.original_amount || 0),
    'monto-asc': (a, b) => (a.original_amount || 0) - (b.original_amount || 0),
    'reciente': (a, b) => new Date(b.start_date || b.created_at || 0) - new Date(a.start_date || a.created_at || 0),
    'vence-prox': (a, b) => new Date(a.due_date || '2099-01-01') - new Date(b.due_date || '2099-01-01'),
    'progreso': (a, b) => {
      const pa = a.original_amount ? ((a.original_amount - (a.remaining_balance || 0)) / a.original_amount) : 0;
      const pb = b.original_amount ? ((b.original_amount - (b.remaining_balance || 0)) / b.original_amount) : 0;
      return pb - pa;
    },
  };
  const filteredCartera = [...typeFiltered].sort(sortFns[sortBy] || sortFns['urgente']);

  const cxcCount = panelCartera.filter(c => c.type === 'CXC').length;
  const cxpCount = panelCartera.filter(c => c.type === 'CXP').length;

  const SORT_OPTIONS = [
    { key: 'urgente', icon: '🔥', label: 'Urgente' },
    { key: 'monto-desc', icon: '↓', label: 'Mayor $' },
    { key: 'monto-asc', icon: '↑', label: 'Menor $' },
    { key: 'reciente', icon: '🕐', label: 'Recientes' },
    { key: 'vence-prox', icon: '📅', label: 'Vence pronto' },
    { key: 'progreso', icon: '📊', label: '% Pagado' },
  ];

  return (
    <div className="space-y-2">

      {/* ─── KPI MINI-RESUMEN ─── */}
      <div className="border border-black">
        <button onClick={() => setKpiOpen(p => !p)}
          className="w-full flex justify-between items-center px-2 py-1 bg-black text-white hover:bg-gray-800 transition-all">
          <span className="text-[9px] font-bold uppercase font-mono">📊 Resumen Cartera</span>
          <span className="text-[9px] font-mono text-gray-400">{kpiOpen ? '▲' : '▼'}</span>
        </button>
        {kpiOpen && kpi && (
          <div className="grid grid-cols-4 divide-x divide-black border-t border-black">
            {[
              { label: 'CXC', value: kpi.cxc_total, cls: 'text-green-700', bg: 'bg-green-50' },
              { label: 'CXP', value: kpi.cxp_total, cls: 'text-amber-700', bg: 'bg-amber-50' },
              { label: 'Vencido', value: kpi.vencido_total, cls: 'text-red-700', bg: 'bg-red-50' },
              { label: '< 7d', value: kpi.proximo_total, cls: 'text-yellow-700', bg: 'bg-yellow-50' },
            ].map(k => (
              <div key={k.label} className={`p-1.5 text-center ${k.bg}`}>
                <div className="text-[7px] text-gray-500 uppercase font-mono font-bold">{k.label}</div>
                <div className={`text-[10px] font-bold font-mono ${k.cls}`}>${Number(k.value).toLocaleString('es-CO', {maximumFractionDigits:0})}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ─── ALERTAS CARTERA ─── */}
      {alerts.length > 0 && (
        <div className="border border-black">
          <button onClick={() => setAlertsOpen(p => !p)}
            className="w-full flex justify-between items-center px-2 py-1 bg-red-900 text-white hover:bg-red-800 transition-all">
            <span className="text-[9px] font-bold uppercase font-mono">🔔 Alertas ({alerts.length})</span>
            <span className="text-[9px] font-mono text-red-300">{alertsOpen ? '▲' : '▼'}</span>
          </button>
          {alertsOpen && (
            <div className="max-h-36 overflow-y-auto">
              {alerts.map((a, i) => (
                <div key={i} className={`flex items-start gap-1.5 px-2 py-1 border-b border-gray-200 text-[9px] font-mono ${
                  a.severity === 'critical' ? 'bg-red-50' :
                  a.severity === 'warning' ? 'bg-amber-50' :
                  a.severity === 'success' ? 'bg-green-50' : 'bg-orange-50'
                }`}>
                  <span className="text-[11px] flex-shrink-0 mt-0.5">{a.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1">
                      <span className={`px-0.5 text-[7px] font-bold border ${
                        a.severity === 'critical' ? 'bg-red-100 border-red-500 text-red-800' :
                        a.severity === 'warning' ? 'bg-amber-100 border-amber-500 text-amber-800' :
                        a.severity === 'success' ? 'bg-green-100 border-green-500 text-green-800' :
                        'bg-orange-100 border-orange-500 text-orange-800'
                      }`}>{a.type}</span>
                      <span className="font-bold">{a.account_type}</span>
                      <span className="text-gray-500 truncate">{a.third_party}</span>
                    </div>
                    <div className={`text-[8px] ${
                      a.severity === 'critical' ? 'text-red-600 font-bold' :
                      a.severity === 'warning' ? 'text-amber-600' :
                      a.severity === 'success' ? 'text-green-600' : 'text-orange-600'
                    }`}>
                      {a.message}
                    </div>
                    {a.next_payment && (
                      <div className="text-[7px] text-blue-500 mt-0.5">
                        📅 Prox corte: {a.next_payment} · c/{a.frequency}d
                      </div>
                    )}
                  </div>
                  <span className="text-[8px] text-gray-400 flex-shrink-0">{a.due_date}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ─── SUB-TABS: TODAS / CXC / CXP ─── */}
      <div className="flex border border-black overflow-hidden">
        {[
          { key: 'TODAS', label: `TODAS (${panelCartera.length})` },
          { key: 'CXC', label: `📥 CXC (${cxcCount})` },
          { key: 'CXP', label: `📤 CXP (${cxpCount})` },
        ].map(st => (
          <button key={st.key} onClick={() => { setSubTab(st.key); setSelectedLedger(null); setPayments([]); }}
            className={`flex-1 py-1 text-[9px] font-bold uppercase font-mono border-r border-black last:border-r-0 transition-all ${
              subTab === st.key ? 'bg-black text-white' : 'bg-brutalBg text-gray-500 hover:bg-brutalNeutral'
            }`}>{st.label}</button>
        ))}
      </div>

      {/* ─── SORT BAR ─── */}
      <div className="flex items-center gap-0 border border-black border-t-0 bg-brutalBg overflow-x-auto">
        <span className="px-2 py-1 text-[8px] font-bold uppercase text-gray-400 whitespace-nowrap">⇅ Ordenar:</span>
        {SORT_OPTIONS.map(s => (
          <button key={s.key} onClick={() => setSortBy(s.key)}
            className={`px-2 py-1 text-[8px] font-bold uppercase font-mono whitespace-nowrap border-l border-black transition-all ${
              sortBy === s.key ? 'bg-black text-white' : 'text-gray-500 hover:bg-brutalNeutral'
            }`}>{s.icon} {s.label}</button>
        ))}
      </div>

      {/* ─── ZONA 1: CUENTAS ACTIVAS ─── */}
      <div className="border border-black overflow-hidden">
        <table className="w-full text-[10px] font-mono">
          <thead className="bg-black text-white uppercase">
            <tr>
              <th className="p-1 border-r border-gray-700 text-left" style={{width:'28%'}}>Tercero</th>
              <th className="p-1 border-r border-gray-700 text-right" style={{width:'18%'}}>Monto</th>
              <th className="p-1 border-r border-gray-700 text-center" style={{width:'30%'}}>Progreso</th>
              <th className="p-1 border-r border-gray-700 text-center" style={{width:'14%'}}>Vence</th>
              <th className="p-1 text-center" style={{width:'10%'}}>Est.</th>
            </tr>
          </thead>
          <tbody>
            {filteredCartera.map(c => {
              const sem = getDueSemaforo(c.due_date);
              const isSelected = selectedLedger?.id === c.id;
              const orig = Number(c.original_amount || 0);
              const rem = Number(c.remaining_balance || 0);
              const paid = orig - rem;
              const pct = orig > 0 ? Math.round((paid / orig) * 100) : 0;
              const startStr = c.start_date ? new Date(c.start_date).toLocaleDateString('es-CO', {day:'2-digit',month:'short'}) : '—';

              return (
                <React.Fragment key={c.id}>
                  <tr onClick={() => loadPayments(c)}
                    className={`cursor-pointer transition-colors border-b border-gray-200 ${isSelected ? 'bg-black text-white' : 'hover:bg-brutalBg'}`}>
                    <td className="p-1 border-r border-gray-200">
                      <div className="flex items-center gap-1">
                        <span className={`text-[7px] font-bold px-0.5 border ${isSelected ? 'border-white' : c.type==='CXC'?'bg-green-100 border-green-500 text-green-800':'bg-amber-100 border-amber-500 text-amber-800'}`}>{c.type}</span>
                        <span className="font-bold truncate max-w-[80px]">{c.third_party_name||'—'}</span>
                      </div>
                      <div className="text-[8px] text-gray-400 mt-0.5 flex items-center gap-1">
                        <span>{startStr} → {c.due_date ? new Date(c.due_date).toLocaleDateString('es-CO', {day:'2-digit',month:'short'}) : '—'}</span>
                        {c.payment_frequency && (
                          <span className={`px-0.5 text-[6px] font-bold border ${isSelected ? 'border-gray-400 text-gray-300' : 'border-blue-300 bg-blue-50 text-blue-600'}`}>c/{c.payment_frequency}d</span>
                        )}
                      </div>
                    </td>
                    <td className="p-1 border-r border-gray-200 text-right">
                      <div className="font-bold">${orig.toLocaleString()}</div>
                      <div className={`text-[8px] ${isSelected ? 'text-gray-300' : 'text-red-500'}`}>Debe: ${rem.toLocaleString()}</div>
                    </td>
                    <td className="p-1 border-r border-gray-200">
                      {/* Progress bar */}
                      <div className="flex items-center gap-1">
                        <div className="flex-1 h-2 bg-gray-200 border border-gray-300 overflow-hidden" style={{minWidth:'40px'}}>
                          <div className={`h-full transition-all ${pct >= 100 ? 'bg-green-500' : pct >= 50 ? 'bg-blue-500' : 'bg-amber-400'}`}
                            style={{width:`${Math.min(pct, 100)}%`}} />
                        </div>
                        <span className={`text-[8px] font-bold ${isSelected ? '' : pct >= 100 ? 'text-green-600' : 'text-gray-600'}`}>{pct}%</span>
                      </div>
                      <div className={`text-[8px] mt-0.5 ${isSelected ? 'text-gray-300' : 'text-gray-400'}`}>
                        Abonado: ${paid.toLocaleString()}
                      </div>
                    </td>
                    <td className="p-1 border-r border-gray-200 text-center">
                      <span className={isSelected ? 'text-white text-[9px]' : `text-[9px] ${sem.cls}`}>{sem.dot}</span>
                      <div className={`text-[8px] ${isSelected ? 'text-gray-300' : sem.cls}`}>{sem.label}</div>
                    </td>
                    <td className="p-1 text-center">
                      <span className={`px-1 py-0.5 text-[7px] font-bold border ${
                        isSelected ? 'border-white text-white' :
                        c.status==='PAGADO'?'bg-green-100 border-green-500 text-green-700':
                        c.status==='VENCIDO'?'bg-red-100 border-red-500 text-red-700':
                        'bg-yellow-100 border-yellow-500 text-yellow-700'
                      }`}>{c.status === 'PENDIENTE' ? 'PEND' : c.status === 'PAGADO' ? '✓' : c.status || 'PEND'}</span>
                    </td>
                  </tr>

                  {/* ─── ZONA 2: HISTORIAL EXPANDIBLE ─── */}
                  {isSelected && (
                    <tr>
                      <td colSpan={5} className="p-0">
                        <div className="border-t-2 border-black bg-white">
                          {/* Header */}
                          <div className="flex items-center justify-between px-2 py-1 bg-gray-50 border-b border-gray-200">
                            <span className="text-[9px] font-bold uppercase font-mono">
                              Historial de Abonos · {c.third_party_name}
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="text-[8px] font-mono text-gray-500">
                                ${paid.toLocaleString()} de ${orig.toLocaleString()}
                              </span>
                              {/* Mini progress */}
                              <div className="w-12 h-1.5 bg-gray-200 border border-gray-300 overflow-hidden">
                                <div className={`h-full ${pct >= 100 ? 'bg-green-500' : 'bg-blue-500'}`} style={{width:`${Math.min(pct,100)}%`}} />
                              </div>
                              <span className="text-[8px] font-bold font-mono">{pct}%</span>
                            </div>
                          </div>

                          {loadingPay ? (
                            <p className="text-center text-[10px] text-gray-400 font-mono py-3 uppercase">Cargando...</p>
                          ) : (
                            <>
                              {/* Payment history table */}
                              {payments.length > 0 ? (
                                <table className="w-full text-[10px] font-mono">
                                  <thead className="bg-gray-100 uppercase text-gray-400 text-[8px]">
                                    <tr>
                                      <th className="p-1 border-r border-gray-200 text-left">Fecha</th>
                                      <th className="p-1 border-r border-gray-200 text-right">Abono</th>
                                      <th className="p-1 border-r border-gray-200 text-right">Saldo</th>
                                      <th className="p-1 text-left">Nota</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-gray-100">
                                    {payments.map(p => (
                                      <React.Fragment key={p.id}>
                                        <tr className="hover:bg-brutalBg cursor-pointer" onClick={() => setExpandedNote(expandedNote === p.id ? null : p.id)}>
                                          <td className="p-1 border-r border-gray-200">{p.payment_date}</td>
                                          <td className="p-1 border-r border-gray-200 text-right font-bold text-green-700">+${Number(p.amount).toLocaleString()}</td>
                                          <td className="p-1 border-r border-gray-200 text-right">{p.balance_after!=null ? `$${Number(p.balance_after).toLocaleString()}` : '—'}</td>
                                          <td className="p-1 text-gray-400">
                                            <div className="flex items-center justify-between">
                                              <span className={expandedNote === p.id ? '' : 'truncate max-w-[70px]'}>{p.note||'—'}</span>
                                              {p.note && p.note.length > 12 && (
                                                <span className="text-[7px] text-gray-300 flex-shrink-0 ml-1">{expandedNote === p.id ? '▲' : '▼'}</span>
                                              )}
                                            </div>
                                          </td>
                                        </tr>
                                        {expandedNote === p.id && p.note && (
                                          <tr>
                                            <td colSpan={4} className="px-2 py-1 bg-gray-50 border-b border-gray-200">
                                              <div className="text-[9px] font-mono text-gray-600 whitespace-pre-wrap">{p.note}</div>
                                            </td>
                                          </tr>
                                        )}
                                      </React.Fragment>
                                    ))}
                                  </tbody>
                                </table>
                              ) : (
                                <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-2">Sin abonos</p>
                              )}

                              {/* Abono form */}
                              <div className="border-t border-black p-2">
                                {!abonoOpen ? (
                                  <button onClick={() => setAbonoOpen(true)}
                                    className="w-full py-1 text-[9px] font-bold uppercase font-mono bg-brutalBg border border-black hover:bg-black hover:text-white transition-all">
                                    + Registrar Abono
                                  </button>
                                ) : (
                                  <div className="space-y-1">
                                    <div className="text-[8px] font-bold uppercase font-mono text-gray-500 flex justify-between">
                                      <span>Nuevo abono</span>
                                      <span className="text-red-500">Pendiente: ${rem.toLocaleString()}</span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-1">
                                      <input type="number" value={abonoAmt} onChange={e => setAbonoAmt(e.target.value)}
                                        placeholder="$ Monto" max={rem}
                                        className="border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen" autoFocus />
                                      <input type="date" value={abonoDate} onChange={e => setAbonoDate(e.target.value)}
                                        className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                                    </div>
                                    <input type="text" value={abonoNote} onChange={e => setAbonoNote(e.target.value)}
                                      placeholder="Nota (ej: Cuota #3, transferencia Bancolombia...)"
                                      className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                                    <div className="flex gap-1">
                                      <button onClick={handleAbono} disabled={!abonoAmt || parseFloat(abonoAmt) <= 0}
                                        className="flex-1 bg-black text-white border border-black py-1 text-[9px] font-bold uppercase hover:bg-brutalGreen hover:text-black disabled:opacity-40 transition-all">
                                        Confirmar Abono
                                      </button>
                                      <button onClick={() => { setAbonoOpen(false); setAbonoAmt(''); setAbonoNote(''); }}
                                        className="border border-black px-3 py-1 text-[9px] font-bold hover:bg-brutalBg">✕</button>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
        {filteredCartera.length === 0 && (
          <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-3">
            {subTab === 'TODAS' ? 'Sin cuentas activas' : `Sin cuentas ${subTab}`}
          </p>
        )}
      </div>

      {/* ─── FORMULARIO NUEVA CUENTA (colapsable) ─── */}
      <div className="border border-black">
        <button onClick={() => setFormOpen(p => !p)}
          className="w-full flex justify-between items-center px-2 py-1.5 bg-brutalBg hover:bg-brutalNeutral transition-all border-b border-black">
          <span className="text-[9px] font-bold uppercase font-mono">✚ Nueva Cuenta CXC / CXP</span>
          <span className="text-[9px] font-mono text-gray-500">{formOpen ? '▲' : '▼'}</span>
        </button>

        {formOpen && (
          <div className="p-2 space-y-1.5">
            {/* Tipo + Plazo */}
            <div className="grid grid-cols-2 gap-1">
              <select value={formType} onChange={e => setFormType(e.target.value)} className="border border-black px-2 py-1 text-[10px] font-mono bg-white">
                <option value="CXC">📥 CXC — Por Cobrar</option>
                <option value="CXP">📤 CXP — Por Pagar</option>
              </select>
              <select value={formTerm} onChange={e => setFormTerm(e.target.value)} className="border border-black px-2 py-1 text-[10px] font-mono bg-white">
                <option value="Corto">Corto Plazo</option>
                <option value="Mediano">Mediano Plazo</option>
                <option value="Largo">Largo Plazo</option>
              </select>
            </div>

            {/* Tercero: búsqueda */}
            <div>
              <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">
                {formType === 'CXC' ? '¿A quién le vas a cobrar?' : '¿A quién le tienes que pagar?'}
              </label>
              {selectedTpId ? (
                <div className="flex items-center justify-between border border-black px-2 py-1 bg-white">
                  <span className="text-[10px] font-bold font-mono">{selectedTpLabel}</span>
                  <button onClick={() => { setSelectedTpId(''); setSelectedTpLabel(''); setTpSearch(''); }}
                    className="text-[9px] text-gray-400 hover:text-red-500 font-bold">✕</button>
                </div>
              ) : (
                <>
                  <input type="text" value={tpSearch} onChange={e => setTpSearch(e.target.value)}
                    placeholder="🔍 Buscar tercero..." autoComplete="off"
                    className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen bg-white" />
                  {tpSearch.length >= 1 && (
                    <div className="border border-t-0 border-black bg-white max-h-28 overflow-y-auto z-10 relative">
                      {filteredTps.length === 0 ? (
                        <div className="px-2 py-1 text-[10px] text-gray-400 font-mono italic">Sin resultados</div>
                      ) : filteredTps.map(tp => (
                        <div key={tp.id} onClick={() => {
                          setSelectedTpId(String(tp.id));
                          setSelectedTpLabel(`${tp.name} · ${tp.identification_type} ${tp.identification_number}`);
                          setTpSearch('');
                        }} className="px-2 py-1 text-[10px] font-mono hover:bg-brutalGreen cursor-pointer border-b border-gray-100 flex justify-between">
                          <span className="font-bold">{tp.name}</span>
                          <span className="text-gray-400">{tp.identification_type} {tp.identification_number}</span>
                        </div>
                      ))}
                      <div onClick={() => { setShowTpCreate(true); setTpSearch(''); }}
                        className="px-2 py-1 text-[10px] font-mono hover:bg-black hover:text-white cursor-pointer font-bold text-center border-t border-black">
                        + Crear nuevo tercero
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Crear tercero inline */}
            {showTpCreate && (
              <div className="border border-black p-2 bg-white space-y-1">
                <div className="text-[8px] font-bold uppercase font-mono text-gray-500">Nuevo Tercero</div>
                <input type="text" value={newTpName} onChange={e => setNewTpName(e.target.value)} placeholder="Nombre / Razón Social"
                  className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" autoFocus />
                <div className="grid grid-cols-3 gap-1">
                  <select value={newTpIdType} onChange={e => setNewTpIdType(e.target.value)} className="border border-black px-1 py-1 text-[10px] font-mono">
                    <option value="NIT">NIT</option><option value="CC">CC</option><option value="CE">CE</option>
                  </select>
                  <input type="text" value={newTpIdNum} onChange={e => setNewTpIdNum(e.target.value)} placeholder="Número"
                    className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                  <input type="email" value={newTpEmail} onChange={e => setNewTpEmail(e.target.value)} placeholder="Email"
                    className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                </div>
                <div className="flex gap-1">
                  <button onClick={handleCreateTp} className="flex-1 bg-black text-white border border-black px-2 py-1 text-[9px] font-bold hover:bg-brutalGreen hover:text-black">Crear y Seleccionar</button>
                  <button onClick={() => setShowTpCreate(false)} className="border border-black px-2 py-1 text-[9px] font-bold hover:bg-brutalBg">Cancelar</button>
                </div>
              </div>
            )}

            {/* Fechas: Inicio → Vencimiento */}
            <div className="grid grid-cols-2 gap-1">
              <div>
                <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">📅 Fecha Inicio</label>
                <input type="date" value={formStartDate} onChange={e => setFormStartDate(e.target.value)}
                  className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none bg-white" />
              </div>
              <div>
                <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">🏁 Fecha Vencimiento</label>
                <input type="date" value={formDue} onChange={e => setFormDue(e.target.value)}
                  className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none bg-white" />
              </div>
            </div>

            {/* Frecuencia de corte */}
            <div>
              <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">🔄 Frecuencia de Corte</label>
              <div className="flex gap-0.5">
                {[{v:'15',l:'C/15d'},{v:'20',l:'C/20d'},{v:'30',l:'C/30d'},{v:'custom',l:'✏️'}].map(opt => (
                  <button key={opt.v} type="button"
                    onClick={() => setFormFrequency(opt.v)}
                    className={`flex-1 py-1 text-[9px] font-mono font-bold border border-black transition-all ${
                      formFrequency === opt.v ? 'bg-black text-white' : 'bg-white text-black hover:bg-brutalNeutral'
                    }`}>{opt.l}</button>
                ))}
              </div>
              {formFrequency === 'custom' && (
                <input type="number" value={formFreqCustom} onChange={e => setFormFreqCustom(e.target.value)}
                  placeholder="Días entre cortes (ej: 7, 10, 45)"
                  className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none bg-white mt-0.5" />
              )}
            </div>

            {formStartDate && formDue && new Date(formDue) > new Date(formStartDate) && (() => {
              const plazo = Math.round((new Date(formDue) - new Date(formStartDate)) / 86400000);
              const freq = formFrequency === 'custom' ? (parseInt(formFreqCustom) || 30) : parseInt(formFrequency);
              const cortes = Math.floor(plazo / freq);
              return (
                <div className="text-[8px] font-mono text-gray-400 text-right flex justify-between">
                  <span>📅 {cortes} cortes cada {freq}d</span>
                  <span>Plazo: {plazo} días</span>
                </div>
              );
            })()}

            {/* Importe total */}
            <div>
              <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">Importe Total</label>
              <input type="number" value={formAmount} onChange={e => setFormAmount(e.target.value)} placeholder="$0"
                className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none bg-white text-right" />
            </div>

            {/* Abono inicial + Saldo */}
            <div className="grid grid-cols-2 gap-1">
              <div>
                <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">Abono Inicial</label>
                <input type="number" value={formPartial} onChange={e => setFormPartial(e.target.value)} placeholder="$0"
                  className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none bg-white text-right" />
              </div>
              <div>
                <label className="text-[8px] font-bold uppercase font-mono block mb-0.5">Saldo Pendiente</label>
                <div className={`border-2 px-2 py-1 text-[10px] font-bold font-mono text-right ${saldo > 0 ? 'border-black bg-red-50 text-red-700' : 'border-green-500 bg-green-50 text-green-700'}`}>
                  ${saldo.toLocaleString()}
                </div>
              </div>
            </div>

            {/* 👁️ Toggle Ver Asiento (Zero-COA) */}
            {formAmount && parseFloat(formAmount) > 0 && (
              <div style={{marginBottom: 6}}>
                <button
                  type="button"
                  onClick={async () => {
                    const next = !showAsiento;
                    setShowAsiento(next);
                    if (next) {
                      try {
                        const cat = formType === 'CXC' ? '__CXC_CREATE__' : '__CXP_CREATE__';
                        const r = await fetch(`${API_BASE}/posting-rules/preview?category=${encodeURIComponent(cat)}&tx_type=${formType}&amount=${parseFloat(formAmount)}`);
                        if (r.ok) setAsientoPreview(await r.json());
                      } catch(e) { setAsientoPreview(null); }
                    }
                  }}
                  className="w-full text-[9px] font-mono font-bold py-1 border border-dashed border-gray-400 hover:border-black hover:bg-gray-50 transition-all"
                  style={{letterSpacing: '0.05em'}}
                >
                  {showAsiento ? '🔽 Ocultar Asiento' : '👁️ Ver Asiento Contable'}
                </button>
                {showAsiento && asientoPreview?.found && (
                  <div className="border-2 border-black p-2 mt-1" style={{background: '#FFFBE6'}}>
                    <div className="text-[8px] font-mono font-bold mb-1 uppercase" style={{color:'#666'}}>⚖️ Preview Partida Doble — {asientoPreview.rule_name}</div>
                    <table className="w-full text-[9px] font-mono" style={{borderCollapse:'collapse'}}>
                      <thead>
                        <tr style={{borderBottom:'2px solid #000'}}>
                          <th className="text-left py-0.5">Cuenta</th>
                          <th className="text-right py-0.5">Debe</th>
                          <th className="text-right py-0.5">Haber</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr style={{borderBottom:'1px solid #ddd'}}>
                          <td className="py-0.5 font-bold">{asientoPreview.debit.cuenta_codigo}</td>
                          <td className="text-right py-0.5" style={{color:'#c00'}}>${parseFloat(asientoPreview.debit.monto || 0).toLocaleString()}</td>
                          <td className="text-right py-0.5">—</td>
                        </tr>
                        <tr>
                          <td className="py-0.5 font-bold">{asientoPreview.credit.cuenta_codigo}</td>
                          <td className="text-right py-0.5">—</td>
                          <td className="text-right py-0.5" style={{color:'#060'}}>${parseFloat(asientoPreview.credit.monto || 0).toLocaleString()}</td>
                        </tr>
                      </tbody>
                    </table>
                    <div className="text-[7px] font-mono mt-1" style={{color:'#888'}}>{asientoPreview.description}</div>
                    <div className="text-[7px] font-mono font-bold mt-0.5" style={{color: asientoPreview.balanced ? '#090' : '#c00'}}>
                      {asientoPreview.balanced ? '✅ Cuadrado (Débito = Crédito)' : '❌ Descuadrado'}
                    </div>
                  </div>
                )}
                {showAsiento && !asientoPreview?.found && (
                  <div className="border border-dashed border-gray-300 p-2 mt-1 text-[8px] font-mono text-gray-500">
                    ⚠️ Sin regla contable para este tipo. El asiento se configurará después.
                  </div>
                )}
              </div>
            )}

            <button onClick={handleSaveCartera} disabled={saving || !selectedTpId || !formDue || !formAmount}
              className="w-full bg-black text-white border border-black py-1.5 text-[10px] font-bold uppercase hover:bg-brutalGreen hover:text-black disabled:opacity-40 disabled:cursor-not-allowed transition-all">
              {saving ? 'Guardando...' : `Guardar ${formType} en Cartera`}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}


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
        {activeTab === 'terceros' && (<>
          {/* --- Form: Identificación de Tercero --- */}
          <div className="border border-black p-2 bg-brutalBg space-y-1.5">
            <SectionLabel text="Vincular tercero a transacción" />
            <input type="text" value={search} onChange={e => { setSearch(e.target.value); }}
              placeholder="🔍 Buscar tercero existente..."
              className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen" />
            {search.length >= 2 && (
              <div className="border border-black bg-white max-h-24 overflow-y-auto">
                {allThirdParties.filter(tp => (tp.name||'').toLowerCase().includes(search.toLowerCase()) || (tp.identification_number||'').includes(search)).slice(0,5).map(tp => (
                  <div key={tp.id} onClick={() => {
                    if (tercero.setName) tercero.setName(tp.name || '');
                    if (tercero.setIdType) tercero.setIdType(tp.identification_type || 'NIT');
                    if (tercero.setIdNumber) tercero.setIdNumber(tp.identification_number || '');
                    if (tercero.setEmail) tercero.setEmail(tp.email || '');
                    if (tercero.setPhone) tercero.setPhone(tp.phone || '');
                    if (tercero.setAddress) tercero.setAddress(tp.address || '');
                    setSearch('');
                  }} className="px-2 py-1 text-[10px] font-mono hover:bg-brutalGreen cursor-pointer border-b border-gray-100">
                    <span className="font-bold">{tp.name}</span> <span className="text-gray-400">· {tp.identification_type} {tp.identification_number}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="text-[8px] text-gray-300 uppercase font-mono border-t border-dashed border-gray-200 pt-1">O crear nuevo:</div>
            <div className="grid grid-cols-2 gap-1">
              <input type="text" value={tercero.name || ''} onChange={e => tercero.setName?.(e.target.value)} placeholder="Nombre / Razón Social" className="col-span-2 border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen" />
              <select value={tercero.idType || 'NIT'} onChange={e => tercero.setIdType?.(e.target.value)} className="border border-black px-1 py-1 text-[10px] font-mono">
                <option value="NIT">NIT</option><option value="CC">CC</option><option value="CE">CE</option><option value="PP">Pasaporte</option>
              </select>
              <input type="text" value={tercero.idNumber || ''} onChange={e => tercero.setIdNumber?.(e.target.value)} placeholder="Número" className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
              <input type="email" value={tercero.email || ''} onChange={e => tercero.setEmail?.(e.target.value)} placeholder="Email" className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
              <input type="tel" value={tercero.phone || ''} onChange={e => tercero.setPhone?.(e.target.value)} placeholder="Teléfono" className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
              <input type="text" value={tercero.address || ''} onChange={e => tercero.setAddress?.(e.target.value)} placeholder="Dirección" className="col-span-2 border border-black px-2 py-1 text-[10px] font-mono outline-none" />
            </div>
          </div>
          {/* --- BD: third_parties --- */}
          <SectionLabel text={`third_parties · ${allThirdParties.length} registros`} />
          <table className="w-full text-[10px] font-mono border border-black">
            <thead className="bg-black text-white uppercase"><tr>
              <th className="p-1 border-r border-black text-left">Nombre</th>
              <th className="p-1 border-r border-black">Tipo</th>
              <th className="p-1 border-r border-black">NIT/CC</th>
              <th className="p-1 border-r border-black">Email</th>
              <th className="p-1">Acc.</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-200">
              {allThirdParties.map(tp => (
                <tr key={tp.id} className="hover:bg-brutalBg">
                  {editingId === tp.id ? (<>
                    <td className="p-0.5 border-r border-black"><input type="text" value={editData.name||''} onChange={e=>setEditData({...editData,name:e.target.value})} className="w-full border border-black px-1 py-0.5 text-[10px] font-mono outline-none" /></td>
                    <td className="p-0.5 border-r border-black"><select value={editData.identification_type||'NIT'} onChange={e=>setEditData({...editData,identification_type:e.target.value})} className="border border-black px-0.5 py-0.5 text-[10px] font-mono"><option>NIT</option><option>CC</option></select></td>
                    <td className="p-0.5 border-r border-black"><input type="text" value={editData.identification_number||''} onChange={e=>setEditData({...editData,identification_number:e.target.value})} className="w-full border border-black px-1 py-0.5 text-[10px] font-mono outline-none" /></td>
                    <td className="p-0.5 border-r border-black"><input type="text" value={editData.email||''} onChange={e=>setEditData({...editData,email:e.target.value})} className="w-full border border-black px-1 py-0.5 text-[10px] font-mono outline-none" /></td>
                    <td className="p-0.5 text-center">
                      <button onClick={()=>updateItem('third-parties',tp.id,editData,refreshTP)} className="bg-brutalGreen border border-black px-1 py-0.5 text-[8px] font-bold mr-0.5">✓</button>
                      <button onClick={()=>setEditingId(null)} className="bg-gray-200 border border-black px-1 py-0.5 text-[8px] font-bold">✕</button>
                    </td>
                  </>) : (<>
                    <td className="p-1 border-r border-black font-bold truncate max-w-[100px]">{tp.name}</td>
                    <td className="p-1 border-r border-black text-center text-[8px]">{tp.identification_type}</td>
                    <td className="p-1 border-r border-black">{tp.identification_number}</td>
                    <td className="p-1 border-r border-black text-gray-400 truncate max-w-[80px]">{tp.email||'—'}</td>
                    <td className="p-1 text-center whitespace-nowrap">
                      <button onClick={()=>{setEditingId(tp.id);setEditData({...tp});}} className="text-[9px] text-gray-400 hover:text-black font-bold">✎</button>
                      <button onClick={()=>deleteItem('third-parties',tp.id,refreshTP)} className="text-[9px] text-gray-300 hover:text-red-500 font-bold ml-1">🗑</button>
                    </td>
                  </>)}
                </tr>
              ))}
            </tbody>
          </table>
          {allThirdParties.length===0 && <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-2">Sin terceros</p>}
        </>)}

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
        {activeTab === 'activos' && (<>
          <div className="border border-black p-2 bg-brutalBg space-y-1.5">
            <SectionLabel text="Vincular recurso/activo a transacción" />
            <div className="flex items-center gap-2 mb-1">
              <label className="flex items-center gap-1 cursor-pointer">
                <input type="checkbox" checked={assetForm.enabled || false} onChange={e => assetForm.setEnabled?.(e.target.checked)} className="accent-black" />
                <span className="text-[10px] font-bold uppercase font-mono">Establecer Recurso</span>
              </label>
            </div>
            {assetForm.enabled && (
              <div className="space-y-1.5">
                <input type="text" value={assetForm.name || ''} onChange={e => assetForm.setName?.(e.target.value)} placeholder="Nombre del recurso" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                <div className="grid grid-cols-3 gap-1">
                  <div>
                    <label className="text-[8px] font-bold uppercase block mb-0.5">Stock</label>
                    <input type="number" min="1" defaultValue="1" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                  </div>
                  <div>
                    <label className="text-[8px] font-bold uppercase block mb-0.5">Valor</label>
                    <input type="number" value={assetForm.value || ''} onChange={e => assetForm.setValue?.(e.target.value)} placeholder="$" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                  </div>
                  <div>
                    <label className="text-[8px] font-bold uppercase block mb-0.5">Tag</label>
                    <input type="text" value={assetForm.tag || ''} onChange={e => assetForm.setTag?.(e.target.value)} placeholder="Etiqueta" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                  </div>
                </div>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input type="checkbox" checked={assetForm.passive || false} onChange={e => assetForm.setPassive?.(e.target.checked)} className="accent-black" />
                  <span className="text-[10px] font-mono">♻ Genera ingreso pasivo</span>
                </label>
              </div>
            )}
          </div>
          {/* --- BD: assets --- */}
          <SectionLabel text={`assets · ${panelAssets.length} registros`} />
          <table className="w-full text-[10px] font-mono border border-black">
            <thead className="bg-black text-white uppercase"><tr>
              <th className="p-1 border-r border-black text-left">Nombre</th>
              <th className="p-1 border-r border-black text-right">Valor</th>
              <th className="p-1 border-r border-black">Tag</th>
              <th className="p-1">Acc.</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-200">
              {panelAssets.map(a => (
                <tr key={a.id} className="hover:bg-brutalBg">
                  <td className="p-1 border-r border-black font-bold">{a.name}</td>
                  <td className="p-1 border-r border-black text-right">${Number(a.purchase_value||0).toLocaleString()}</td>
                  <td className="p-1 border-r border-black">{a.custom_tag||'—'}</td>
                  <td className="p-1 text-center whitespace-nowrap">
                    <button onClick={()=>{setEditingId(a.id);setEditData({name:a.name,purchase_value:a.purchase_value,custom_tag:a.custom_tag});}} className="text-[9px] text-gray-400 hover:text-black font-bold">✎</button>
                    <button onClick={()=>deleteItem('assets',a.id,fetchAssets)} className="text-[9px] text-gray-300 hover:text-red-500 font-bold ml-1">🗑</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {panelAssets.length===0 && <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-2">Sin recursos</p>}
        </>)}

        {/* ════════════════════════════════════════════ */}
        {/* TAB: ETIQUETAS — Selector + BD */}
        {/* ════════════════════════════════════════════ */}
        {activeTab === 'etiquetas' && (<>
          <div className="border border-black p-2 bg-brutalBg space-y-1.5">
            <SectionLabel text="Seleccionar etiquetas para transacción" />
            <input type="text" value={tagState.search || ''} onChange={e => tagState.setSearch?.(e.target.value)}
              placeholder="🔍 Filtrar etiquetas..." className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen" />
            <div className="max-h-24 overflow-y-auto space-y-0.5">
              {panelTags.filter(t => !tagState.search || t.name.toLowerCase().includes((tagState.search||'').toLowerCase())).map(tag => {
                const sel = (tagState.selected || []).includes(tag.name);
                return (
                  <div key={tag.id} onClick={() => {
                    if (!tagState.setSelected) return;
                    tagState.setSelected(prev => sel ? prev.filter(t => t !== tag.name) : [...prev, tag.name]);
                  }} className={`flex items-center gap-1.5 px-2 py-1 cursor-pointer border ${sel ? 'border-black bg-brutalGreen' : 'border-gray-200 hover:bg-brutalBg'}`}>
                    <span className="text-[10px] font-mono">{sel ? '☑' : '☐'}</span>
                    <span className="w-2.5 h-2.5 border border-black" style={{ backgroundColor: tag.color || '#000' }}></span>
                    <span className="text-[10px] font-bold uppercase font-mono">{tag.name}</span>
                  </div>
                );
              })}
            </div>
            {(tagState.selected||[]).length > 0 && (
              <div className="flex flex-wrap gap-1 border-t border-dashed border-gray-200 pt-1">
                {(tagState.selected||[]).map(t => (
                  <span key={t} className="bg-black text-white px-1.5 py-0.5 text-[8px] font-bold uppercase inline-flex items-center gap-1">
                    {t} <button onClick={() => tagState.setSelected?.(prev => prev.filter(x => x !== t))} className="text-gray-400 hover:text-red-300">×</button>
                  </span>
                ))}
              </div>
            )}
          </div>
          {/* --- BD: tag_definitions --- */}
          <SectionLabel text={`tag_definitions · ${panelTags.length} registros`} />
          <div className="space-y-0.5">
            {panelTags.map(tag => (
              <div key={tag.id} className="flex items-center justify-between border border-gray-200 px-2 py-1 hover:bg-brutalBg group">
                {editingId === tag.id ? (
                  <div className="flex items-center gap-1 flex-1">
                    <input type="text" value={editData.name||''} onChange={e=>setEditData({...editData,name:e.target.value})} className="flex-1 border border-black px-1 py-0.5 text-[10px] font-mono outline-none" autoFocus />
                    <input type="color" value={editData.color||'#000000'} onChange={e=>setEditData({...editData,color:e.target.value})} className="w-5 h-5 border border-black cursor-pointer" />
                    <button onClick={()=>updateItem('tags',tag.id,editData,fetchTags)} className="bg-brutalGreen border border-black px-1 py-0.5 text-[8px] font-bold">✓</button>
                    <button onClick={()=>setEditingId(null)} className="bg-gray-200 border border-black px-1 py-0.5 text-[8px] font-bold">✕</button>
                  </div>
                ) : (<>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 border border-black" style={{backgroundColor:tag.color||'#000'}}></span>
                    <span className="text-[10px] font-bold uppercase font-mono">{tag.name}</span>
                  </div>
                  <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={()=>{setEditingId(tag.id);setEditData({name:tag.name,color:tag.color});}} className="text-[9px] text-gray-400 hover:text-black font-bold">✎</button>
                    <button onClick={()=>deleteItem('tags',tag.id,fetchTags)} className="text-[9px] text-gray-300 hover:text-red-500 font-bold">🗑</button>
                  </div>
                </>)}
              </div>
            ))}
          </div>
          <div className="flex gap-1 border-t border-black pt-1.5">
            <input type="text" value={newTag} onChange={e=>setNewTag(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&newTag.trim()){fetch(`${API_BASE}/tags`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:newTag.trim()})}).then(()=>{setNewTag('');fetchTags()});}}} placeholder="+ Nueva etiqueta..." className="flex-grow bg-brutalBg border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen" />
            <button onClick={()=>{if(newTag.trim()){fetch(`${API_BASE}/tags`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:newTag.trim()})}).then(()=>{setNewTag('');fetchTags()});}}} className="bg-black text-white border border-black px-2 py-1 text-[8px] font-bold hover:bg-brutalGreen hover:text-black">+</button>
          </div>
        </>)}

        {/* ════════════════════════════════════════════ */}
        {/* TAB: IMPUESTOS / TASAS — Form + BD */}
        {/* ════════════════════════════════════════════ */}
        {activeTab === 'impuestos' && (<>
          <div className="border border-black p-2 bg-brutalBg space-y-1.5">
            <SectionLabel text="Vincular impuesto a transacción" />
            <label className="flex items-center gap-1 cursor-pointer mb-1">
              <input type="checkbox" checked={taxes.enabled || false} onChange={e => taxes.setEnabled?.(e.target.checked)} className="accent-black" />
              <span className="text-[10px] font-bold uppercase font-mono">Aplicar Impuesto</span>
            </label>
            {taxes.enabled && (
              <div className="grid grid-cols-2 gap-1">
                <select value={taxes.type || 'IVA_19'} onChange={e => taxes.setType?.(e.target.value)} className="border border-black px-2 py-1 text-[10px] font-mono">
                  <option value="IVA_19">IVA 19%</option>
                  <option value="IVA_5">IVA 5%</option>
                  <option value="RETEFUENTE">ReteFuente</option>
                  <option value="RETEICA">ReteICA</option>
                  <option value="GMF">GMF (4x1000)</option>
                  <option value="CUSTOM">Custom</option>
                </select>
                {taxes.type === 'CUSTOM' && (
                  <input type="number" step="0.01" value={taxes.customRate || ''} onChange={e => taxes.setCustomRate?.(e.target.value)} placeholder="% Tasa" className="border border-black px-2 py-1 text-[10px] font-mono outline-none text-right" />
                )}
              </div>
            )}
          </div>
          {/* --- BD: custom_taxes_templates --- */}
          <SectionLabel text={`custom_taxes_templates · ${panelTaxes.length} registros`} />
          <table className="w-full text-[10px] font-mono border border-black">
            <thead className="bg-black text-white uppercase"><tr>
              <th className="p-1 border-r border-black text-left">Nombre</th>
              <th className="p-1 border-r border-black text-right">Tasa</th>
              <th className="p-1 border-r border-black">Tipo</th>
              <th className="p-1">Acc.</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-200">
              {panelTaxes.map(t => (
                <tr key={t.id} className="hover:bg-brutalBg">
                  <td className="p-1 border-r border-black font-bold">{t.name}</td>
                  <td className="p-1 border-r border-black text-right">{Number(t.rate).toFixed(2)}%</td>
                  <td className="p-1 border-r border-black text-center"><span className={`px-1 py-0.5 text-[7px] font-bold border ${t.type==='ADDITIVE'?'bg-green-50 border-green-400':'bg-red-50 border-red-400'}`}>{t.type==='ADDITIVE'?'+ADD':'−DED'}</span></td>
                  <td className="p-1 text-center whitespace-nowrap">
                    <button onClick={()=>{setEditingId(t.id);setEditData({name:t.name,rate:t.rate,type:t.type});}} className="text-[9px] text-gray-400 hover:text-black font-bold">✎</button>
                    <button onClick={()=>deleteItem('custom-taxes',t.id,fetchTaxes)} className="text-[9px] text-gray-300 hover:text-red-500 font-bold ml-1">🗑</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {panelTaxes.length===0 && <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-2">Sin tasas</p>}
          <div className="grid grid-cols-4 gap-1 border-t border-black pt-1.5">
            <input type="text" value={newTaxName} onChange={e=>setNewTaxName(e.target.value)} placeholder="Nombre" className="bg-brutalBg border border-black px-1 py-1 text-[10px] font-mono outline-none" />
            <input type="number" step="0.01" value={newTaxRate} onChange={e=>setNewTaxRate(e.target.value)} placeholder="%" className="bg-brutalBg border border-black px-1 py-1 text-[10px] font-mono outline-none text-right" />
            <select value={newTaxType} onChange={e=>setNewTaxType(e.target.value)} className="bg-brutalBg border border-black px-1 py-1 text-[10px] font-mono"><option value="ADDITIVE">ADITIVO</option><option value="DEDUCTIVE">DED</option></select>
            <button onClick={()=>{if(newTaxName.trim()&&newTaxRate){fetch(`${API_BASE}/custom-taxes`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:newTaxName.trim(),rate:parseFloat(newTaxRate),type:newTaxType})}).then(()=>{setNewTaxName('');setNewTaxRate('');fetchTaxes()});}}} className="bg-black text-white border border-black px-1 py-1 text-[8px] font-bold hover:bg-brutalGreen hover:text-black">+</button>
          </div>
        </>)}

        {/* ════════════════════════════════════════════ */}
        {/* TAB: CUENTAS — Form + BD */}
        {/* ════════════════════════════════════════════ */}
        {activeTab === 'cuentas' && (<>
          <div className="border border-black p-2 bg-brutalBg space-y-1.5">
            <SectionLabel text="Agregar nueva cuenta financiera" />
            <form onSubmit={handleAddAccount} className="space-y-1">
              <input type="text" value={newAccName} onChange={e => setNewAccName(e.target.value)} placeholder="Nombre (ej: Bancolombia)" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" required />
              <div className="grid grid-cols-2 gap-1">
                <select value={newAccType} onChange={e => setNewAccType(e.target.value)} className="border border-black px-2 py-1 text-[10px] font-mono">
                  <option>Ahorros</option><option>Corriente</option><option>Crédito</option><option>Efectivo</option><option>Billetera</option><option>Crypto</option>
                </select>
                <select value={newAccCurrency} onChange={e => setNewAccCurrency(e.target.value)} className="border border-black px-2 py-1 text-[10px] font-mono">
                  <option>COP</option><option>USD</option><option>EUR</option>
                </select>
              </div>
              <div className="flex gap-1">
                <input type="number" value={newAccBalance} onChange={e => setNewAccBalance(e.target.value)} placeholder="Saldo Inicial" className="flex-grow border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                <button type="submit" className="bg-black text-white border border-black px-3 py-1 text-[8px] font-bold uppercase hover:bg-brutalGreen hover:text-black">Añadir</button>
              </div>
            </form>
          </div>
          {/* --- BD: user_accounts --- */}
          <SectionLabel text={`user_accounts · ${accounts.length} registros`} />
          <table className="w-full text-[10px] font-mono border border-black">
            <thead className="bg-black text-white uppercase"><tr>
              <th className="p-1 border-r border-black text-left">Cuenta</th>
              <th className="p-1 border-r border-black">Tipo</th>
              <th className="p-1 border-r border-black">Moneda</th>
              <th className="p-1 text-right">Saldo</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-200">
              {accounts.map(acc => (
                <tr key={acc.id} className="hover:bg-brutalBg">
                  <td className="p-1 border-r border-black font-bold">{acc.name}</td>
                  <td className="p-1 border-r border-black text-center text-[9px]">{acc.type}</td>
                  <td className="p-1 border-r border-black text-center">{acc.currency||'COP'}</td>
                  <td className="p-1 text-right font-bold">${Number(acc.current_balance||0).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {accounts.length===0 && <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-2">Sin cuentas</p>}
        </>)}

        {/* ════════════════════════════════════════════ */}
        {/* TAB: CONFIG / USUARIO */}
        {/* ════════════════════════════════════════════ */}
        {activeTab === 'usuario' && (<>
          <div className="border border-black p-2 bg-brutalBg space-y-1.5">
            <SectionLabel text="Perfil de usuario activo" />
            {profileEdit.isEditing ? (
              <div className="space-y-1.5">
                <input type="text" value={profileEdit.name||''} onChange={e=>profileEdit.setName?.(e.target.value)} placeholder="Nombre" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                <input type="email" value={profileEdit.email||''} onChange={e=>profileEdit.setEmail?.(e.target.value)} placeholder="Email" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                <input type="text" value={profileEdit.role||''} onChange={e=>profileEdit.setRole?.(e.target.value)} placeholder="Rol" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
                <div className="flex gap-1">
                  <button type="button" onClick={profileEdit.handleSave} className="bg-black text-brutalGreen border border-black px-3 py-1 text-[9px] font-bold uppercase">GUARDAR</button>
                  <button type="button" onClick={()=>profileEdit.setIsEditing?.(false)} className="bg-brutalNeutral border border-black px-3 py-1 text-[9px] font-bold uppercase">CANCELAR</button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 bg-brutalGreen border-2 border-black flex items-center justify-center text-sm font-bold">{(profile?.name||'U').charAt(0).toUpperCase()}</div>
                  <div>
                    <span className="text-xs font-bold block">{profile?.name||'—'}</span>
                    <span className="text-[9px] text-gray-400 font-mono">{profile?.email||'—'}</span>
                  </div>
                </div>
                <button onClick={()=>{
                  profileEdit.setName?.(profile?.name||'');
                  profileEdit.setEmail?.(profile?.email||'');
                  profileEdit.setRole?.(profile?.role||'');
                  profileEdit.setIsEditing?.(true);
                }} className="text-xs border border-black px-1.5 py-0.5 hover:bg-brutalBg">✏️</button>
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-1">
            <div className="border border-gray-200 p-1.5"><span className="text-[8px] text-gray-400 uppercase block">Rol</span><span className="text-[10px] font-bold font-mono">{profile?.role||'—'}</span></div>
            <div className="border border-gray-200 p-1.5"><span className="text-[8px] text-gray-400 uppercase block">Portafolio</span><span className="text-[10px] font-bold font-mono">{activePortfolio}</span></div>
          </div>
        </>)}

      </div>
    </div>
  );
}
