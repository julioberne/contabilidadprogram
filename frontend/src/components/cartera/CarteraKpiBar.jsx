// CarteraKpiBar.jsx — KPI mini-resumen + Alertas section
import React from 'react';

export default function CarteraKpiBar({ kpi, kpiOpen, setKpiOpen, alerts, alertsOpen, setAlertsOpen }) {
  return (
    <>
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
    </>
  );
}
