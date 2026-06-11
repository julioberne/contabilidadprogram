// CTKpiCards.jsx — Tarjetas de rendimiento (Zona 1)
import React from 'react';

const fmt = (n) => new Intl.NumberFormat('es-CO', {
  style: 'currency', currency: 'COP', maximumFractionDigits: 0
}).format(n || 0);

function KpiCard({ icon, label, value, sub, highlight, danger, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`border-2 p-4 text-left w-full transition-all hover:shadow-[4px_4px_0px] group ${
        danger
          ? 'border-red-500 hover:shadow-red-500 bg-red-950/30'
          : highlight
          ? 'border-amber-400 hover:shadow-amber-400 bg-amber-950/30'
          : 'border-amber-400/40 hover:border-amber-400 hover:shadow-amber-400 bg-black'
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <span className="text-2xl">{icon}</span>
        {danger && (
          <span className="text-red-400 text-[9px] font-black uppercase border border-red-400 px-1">
            ALERTA
          </span>
        )}
      </div>
      <p className="text-amber-400/60 text-[10px] font-bold uppercase tracking-widest">{label}</p>
      <p className={`font-black text-lg leading-tight mt-1 ${
        danger ? 'text-red-400' : 'text-white'
      }`}>
        {value}
      </p>
      {sub && (
        <p className="text-amber-400/40 text-[10px] mt-1 font-mono">{sub}</p>
      )}
    </button>
  );
}

function MiniBarChart({ ingresos, gastos }) {
  const max = Math.max(ingresos, gastos, 1);
  const iH = Math.round((ingresos / max) * 40);
  const gH = Math.round((gastos / max) * 40);

  return (
    <div className="flex items-end gap-2 h-12 mt-2">
      <div className="flex flex-col items-center gap-1">
        <div
          className="w-6 bg-amber-400 transition-all duration-500"
          style={{ height: `${iH}px` }}
        />
        <span className="text-[8px] text-amber-400/60 uppercase">ING</span>
      </div>
      <div className="flex flex-col items-center gap-1">
        <div
          className="w-6 bg-red-500 transition-all duration-500"
          style={{ height: `${gH}px` }}
        />
        <span className="text-[8px] text-red-400/60 uppercase">EGR</span>
      </div>
      <div className="ml-2 flex-1">
        <p className="text-[9px] text-white font-bold">{fmt(ingresos)}</p>
        <p className="text-[9px] text-red-400 font-bold">{fmt(gastos)}</p>
      </div>
    </div>
  );
}

export default function CTKpiCards({ kpis, activeEntity, onOpenApprovals }) {
  if (!activeEntity) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 p-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="border-2 border-amber-400/20 p-4 animate-pulse bg-amber-400/5 h-28" />
        ))}
      </div>
    );
  }

  const k = kpis || {};
  const balance = (k.balance_neto || 0);
  const isNegative = balance < 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 p-4">
      {/* Caja Disponible */}
      <KpiCard
        icon="💵"
        label="Caja Disponible"
        value={fmt(balance)}
        sub={`${k.entity_ids_in_scope || 1} entidad(es) en scope`}
        danger={isNegative}
        highlight={!isNegative && balance > 0}
      />

      {/* Ingresos vs Egresos */}
      <div className="border-2 border-amber-400/40 hover:border-amber-400 p-4 bg-black transition-all">
        <span className="text-2xl">📊</span>
        <p className="text-amber-400/60 text-[10px] font-bold uppercase tracking-widest mt-2">
          ING VS EGR
        </p>
        <MiniBarChart ingresos={k.total_ingresos || 0} gastos={k.total_gastos || 0} />
      </div>

      {/* CXC Pendiente */}
      <KpiCard
        icon="⏳"
        label="CXC Pendiente"
        value={fmt(k.total_cxc || 0)}
        sub="Cuentas por cobrar activas"
        highlight={k.total_cxc > 0}
      />

      {/* Centro de Aprobaciones */}
      <KpiCard
        icon="🔔"
        label="Aprobaciones"
        value={`${k.pending_approvals || 0} pendiente(s)`}
        sub="Click para revisar"
        danger={k.pending_approvals > 0}
        onClick={onOpenApprovals}
      />

      {/* Sub-entidades */}
      <KpiCard
        icon="🌐"
        label="Sub-Entidades"
        value={`${k.child_entities || 0} hija(s)`}
        sub={`Tipo: ${activeEntity.type}`}
      />
    </div>
  );
}
