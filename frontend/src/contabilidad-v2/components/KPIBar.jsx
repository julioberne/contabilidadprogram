import React from 'react';

const formatMoney = (n) =>
  '$' + Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 0 });

const formatUSD = (n) =>
  'USD ' + Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 });

const STATUS_STYLES = {
  NOMINAL:   'bg-green-100 text-green-800',
  'DÉFICIT': 'bg-red-100 text-red-800',
  SUPERÁVIT: 'bg-blue-100 text-blue-800',
};

function KPICell({ label, value, colorClass }) {
  return (
    <div className="border-r-2 border-black px-3 py-2 last:border-r-0">
      <div className="text-[9px] font-mono uppercase tracking-wider text-neutral-500 mb-0.5">
        {label}
      </div>
      <div className={`text-[12px] font-mono font-bold uppercase ${colorClass}`}>
        {value}
      </div>
    </div>
  );
}

export function KPIBar({ cajaViva }) {
  if (!cajaViva) return null;

  const {
    balance_neto_cop = 0,
    total_ingresos_cop = 0,
    total_gastos_cop = 0,
    patrimonio_cop = 0,
    balance_neto_usd = 0,
    status = 'NOMINAL',
    alerts = [],
  } = cajaViva;

  const balanceCopColor = balance_neto_cop >= 0 ? 'text-green-700' : 'text-red-600';
  const balanceUsdColor = balance_neto_usd >= 0 ? 'text-green-700' : 'text-red-600';
  const statusStyle = STATUS_STYLES[status] || STATUS_STYLES.NOMINAL;

  return (
    <div className="w-full font-mono">
      {/* ── KPI CELLS ── */}
      <div
        className="grid border-2 border-black bg-white"
        style={{
          gridTemplateColumns: 'repeat(6, 1fr)',
          boxShadow: '3px 3px 0 #000',
        }}
      >
        <KPICell
          label="INGRESOS COP"
          value={formatMoney(total_ingresos_cop)}
          colorClass="text-green-700"
        />
        <KPICell
          label="GASTOS COP"
          value={formatMoney(total_gastos_cop)}
          colorClass="text-red-600"
        />
        <KPICell
          label="BALANCE COP"
          value={formatMoney(balance_neto_cop)}
          colorClass={balanceCopColor}
        />
        <KPICell
          label="PATRIMONIO COP"
          value={formatMoney(patrimonio_cop)}
          colorClass="text-black font-extrabold"
        />
        <KPICell
          label="BALANCE USD"
          value={formatUSD(balance_neto_usd)}
          colorClass={balanceUsdColor}
        />

        {/* STATUS CELL */}
        <div className="px-3 py-2 flex flex-col justify-center">
          <div className="text-[9px] font-mono uppercase tracking-wider text-neutral-500 mb-1">
            STATUS
          </div>
          <span
            className={`inline-block border-2 border-black px-2 py-0.5 font-bold text-[8px] uppercase tracking-wide w-fit ${statusStyle}`}
          >
            {status}
          </span>
        </div>
      </div>

      {/* ── ALERTS STRIP ── */}
      {alerts.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1 px-1">
          {alerts.map((alert, i) => (
            <span
              key={i}
              className="inline-block border border-black bg-[#FFB000] text-black text-[8px] font-mono font-bold uppercase px-2 py-0.5"
            >
              {alert}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default KPIBar;
