/* ============================================================
   ReportesTab.jsx — Libro mayor · Balance de prueba · Balance
   general · P&G, calculados SOLO con asientos en libros
   (contabilizados; los anulados los cancela su espejo).
   Export CSV en cliente.
   ============================================================ */
import { useCallback, useEffect, useState } from 'react';
import { api } from '../useContadoresApi.js';
import PeriodoPicker from '../components/PeriodoPicker.jsx';
import CuentaSelect from '../components/CuentaSelect.jsx';
import { fmt, fmtFecha } from '../fmt.js';

const SUB = [['mayor', 'LIBRO MAYOR'], ['prueba', 'BALANCE DE PRUEBA'], ['general', 'BALANCE GENERAL'], ['pyg', 'P&G']];

/* Bloque de cuentas de un reporte (componente de módulo, no se recrea). */
function GrupoReporte({ titulo, g }) {
  return (
    <div className="bg-white border-2 border-black shadow-brutal">
      <div className="bg-black text-white px-1 text-[10px] font-bold flex justify-between"><span>{titulo}</span><span>{fmt(g.total)}</span></div>
      <table className="w-full text-[10px] font-mono">
        <tbody>
          {g.cuentas.map((c) => (
            <tr key={c.cuenta_codigo} className="border-b border-black"><td className="px-1 font-bold">{c.cuenta_codigo}</td><td className="px-1">{c.cuenta_nombre}</td><td className="px-1 text-right">{fmt(c.saldo)}</td></tr>
          ))}
          {!g.cuentas.length && <tr><td className="px-1 text-gray-500" colSpan={3}>sin movimientos</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function csv(filas, nombre) {
  if (!filas?.length) return;
  const cols = Object.keys(filas[0]);
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const texto = [cols.join(','), ...filas.map((f) => cols.map((c) => esc(f[c])).join(','))].join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([texto], { type: 'text/csv;charset=utf-8' }));
  a.download = `${nombre}.csv`; a.click(); URL.revokeObjectURL(a.href);
}

export default function ReportesTab({ portfolioId, portfolios, cuentas }) {
  const [sub, setSub] = useState('prueba');
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const [cuenta, setCuenta] = useState('');
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const nombre = portfolioId != null ? (portfolios || []).find((p) => p.id === portfolioId)?.name : 'CONSOLIDADO';
  const btn = 'border border-black px-1.5 py-0.5 text-[10px] font-bold hover:bg-black hover:text-white disabled:opacity-40';
  const th = 'px-1 text-left'; const tr = 'px-1 text-right';

  const cargar = useCallback(async () => {
    setError(''); setData(null);
    if (sub === 'mayor' && !cuenta) return;
    setLoading(true);
    try {
      const p = new URLSearchParams();
      if (portfolioId != null) p.set('portfolio_id', portfolioId);
      if (desde) p.set('desde', desde);
      if (hasta) p.set('hasta', hasta);
      if (sub === 'mayor') p.set('cuenta', cuenta);
      const ruta = { mayor: 'libro-mayor', prueba: 'balance-prueba', general: 'balance-general', pyg: 'pyg' }[sub];
      setData(await api.get(`/contadores/reportes/${ruta}?${p}`));
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [sub, portfolioId, desde, hasta, cuenta]);
  useEffect(() => { cargar(); }, [cargar]);

  const Grupo = GrupoReporte;

  return (
    <div className="space-y-2">
      <div className="bg-white border-2 border-black p-2 shadow-brutal space-y-1 text-[10px]">
        <div className="flex flex-wrap gap-1 items-center">
          {SUB.map(([k, l]) => <button key={k} className={`${btn} ${sub === k ? 'bg-black text-white' : ''}`} onClick={() => setSub(k)}>{l}</button>)}
          <b className="ml-2">{nombre}</b>
          <span className="text-gray-600">· solo asientos en libros (contabilizados)</span>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          {sub !== 'general' && <PeriodoPicker desde={desde} hasta={hasta} onChange={(a, b) => { setDesde(a || ''); setHasta(b || ''); }} />}
          {sub === 'general' && <label>Hasta <input type="date" className="border border-black px-1 py-0.5 text-[10px] font-mono bg-white" value={hasta} onChange={(e) => setHasta(e.target.value)} /></label>}
          {sub === 'mayor' && <label>Cuenta <CuentaSelect cuentas={cuentas} value={cuenta} listId="coa-mayor" onChange={setCuenta} /></label>}
          <button className={btn} onClick={cargar} disabled={loading}>↻</button>
        </div>
      </div>
      {error && <div className="bg-brutalCrimson text-white border-2 border-black p-1 text-[10px]">{error}</div>}
      {loading && <div className="text-[10px]">▓ Calculando…</div>}

      {sub === 'prueba' && data && (
        <div className="bg-white border-2 border-black shadow-brutal overflow-x-auto">
          <div className="flex items-center gap-2 p-1 text-[10px]">
            <b className={data.cuadra ? 'text-green-700' : 'text-brutalCrimson'}>{data.cuadra ? '✔ CUADRA' : '✖ NO CUADRA'}</b>
            <button className={`${btn} ml-auto`} onClick={() => csv(data.cuentas, 'balance_prueba')}>CSV</button>
          </div>
          <table className="w-full text-[10px] font-mono">
            <thead><tr className="bg-black text-white"><th className={th}>CUENTA</th><th className={th}>NOMBRE</th><th className={tr}>INI DB</th><th className={tr}>INI CR</th><th className={tr}>MOV DB</th><th className={tr}>MOV CR</th><th className={tr}>FIN DB</th><th className={tr}>FIN CR</th></tr></thead>
            <tbody>
              {data.cuentas.map((c) => (
                <tr key={c.cuenta_codigo} className="border-b border-black">
                  <td className="px-1 font-bold">{c.cuenta_codigo}</td><td className="px-1">{c.cuenta_nombre}</td>
                  <td className={tr}>{fmt(c.saldo_inicial_db)}</td><td className={tr}>{fmt(c.saldo_inicial_cr)}</td>
                  <td className={tr}>{fmt(c.mov_debito)}</td><td className={tr}>{fmt(c.mov_credito)}</td>
                  <td className={tr}>{fmt(c.saldo_final_db)}</td><td className={tr}>{fmt(c.saldo_final_cr)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot><tr className="font-bold bg-brutalNeutral"><td className="px-1" colSpan={2}>TOTALES</td>
              {['saldo_inicial_db', 'saldo_inicial_cr', 'mov_debito', 'mov_credito', 'saldo_final_db', 'saldo_final_cr'].map((k) => <td key={k} className={tr}>{fmt(data.totales[k])}</td>)}</tr></tfoot>
          </table>
        </div>
      )}

      {sub === 'mayor' && !cuenta && <div className="text-[10px] bg-white border-2 border-black p-2">Elige una cuenta.</div>}
      {sub === 'mayor' && data && (
        <div className="bg-white border-2 border-black shadow-brutal overflow-x-auto">
          <div className="flex items-center gap-2 p-1 text-[10px]">
            <b>{data.cuenta_codigo} {data.cuenta_nombre}</b> <span className="border border-black px-1">{data.cuenta_tipo}</span>
            <span>saldo inicial {fmt(data.saldo_inicial)} · final <b>{fmt(data.saldo_final)}</b></span>
            <button className={`${btn} ml-auto`} onClick={() => csv(data.movimientos, `mayor_${data.cuenta_codigo}`)}>CSV</button>
          </div>
          <table className="w-full text-[10px] font-mono">
            <thead><tr className="bg-black text-white"><th className={th}>FECHA</th><th className={th}>ASIENTO</th><th className={th}>REF</th><th className={th}>DESCRIPCIÓN</th><th className={tr}>DÉBITO</th><th className={tr}>CRÉDITO</th><th className={tr}>SALDO</th></tr></thead>
            <tbody>
              {data.movimientos.map((m) => (
                <tr key={m.id} className={`border-b border-black ${m.estado === 'ANULADO' ? 'line-through text-gray-500' : ''}`}>
                  <td className="px-1">{fmtFecha(m.fecha)}</td><td className="px-1">{m.entry_group_id}</td><td className="px-1">{m.referencia}</td>
                  <td className="px-1 truncate max-w-xs">{m.descripcion}</td>
                  <td className={tr}>{Number(m.debito) ? fmt(m.debito) : ''}</td><td className={tr}>{Number(m.credito) ? fmt(m.credito) : ''}</td>
                  <td className={`${tr} font-bold`}>{fmt(m.saldo_acumulado)}</td>
                </tr>
              ))}
              {!data.movimientos.length && <tr><td className="p-1" colSpan={7}>Sin movimientos en el periodo.</td></tr>}
            </tbody>
            <tfoot><tr className="font-bold bg-brutalNeutral"><td className="px-1" colSpan={4}>TOTALES</td><td className={tr}>{fmt(data.total_debito)}</td><td className={tr}>{fmt(data.total_credito)}</td><td className={tr}>{fmt(data.saldo_final)}</td></tr></tfoot>
          </table>
        </div>
      )}

      {sub === 'general' && data && (
        <div className="space-y-2">
          <div className={`text-[10px] font-bold border-2 border-black p-1 ${data.ecuacion_contable ? 'bg-brutalGreen' : 'bg-brutalCrimson text-white'}`}>
            {data.ecuacion_contable ? '✔' : '✖'} Activo {fmt(data.activos.total)} = Pasivo {fmt(data.pasivos.total)} + Patrimonio {fmt(data.patrimonio.total)} + Utilidad {fmt(data.utilidad_ejercicio)}
            {!data.ecuacion_contable && ` · diferencia ${fmt(data.diferencia)}`}
          </div>
          <div className="grid md:grid-cols-2 gap-2">
            <Grupo titulo="ACTIVOS" g={data.activos} />
            <div className="space-y-2">
              <Grupo titulo="PASIVOS" g={data.pasivos} />
              <Grupo titulo="PATRIMONIO" g={data.patrimonio} />
              <div className="bg-white border-2 border-black shadow-brutal text-[10px] px-1 flex justify-between"><b>UTILIDAD DEL EJERCICIO</b><b>{fmt(data.utilidad_ejercicio)}</b></div>
            </div>
          </div>
        </div>
      )}

      {sub === 'pyg' && data && (
        <div className="space-y-2">
          <div className={`text-[10px] font-bold border-2 border-black p-1 ${data.utilidad_neta >= 0 ? 'bg-brutalGreen' : 'bg-brutalCrimson text-white'}`}>
            UTILIDAD NETA {fmt(data.utilidad_neta)} = Ingresos {fmt(data.ingresos.total)} − Gastos {fmt(data.gastos.total)}
          </div>
          <div className="grid md:grid-cols-2 gap-2">
            <Grupo titulo="INGRESOS" g={data.ingresos} />
            <Grupo titulo="GASTOS" g={data.gastos} />
          </div>
        </div>
      )}
    </div>
  );
}
