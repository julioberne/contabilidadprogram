/* ============================================================
   SalaryTab.jsx — Calculadora Salarial Laboral Colombiana 2025
   Módulo 08c RRHH — Calculadora premium tipo internet
   ============================================================
   Modos:
   1. NÓMINA MENSUAL  — calcula neto, aportes y costo empresa
   2. LIQUIDACIÓN     — cesantías, intereses, vacaciones, prima
   3. HISTORIAL       — pagos registrados + comprobante PDF
   
   Valores 2025 (Colombia):
   - SMLV: $1,423,500 COP
   - Auxilio transporte: $200,000 COP (si base < 2 SMLV)
   - ARL: I=0.522%  II=1.044%  III=2.436%  IV=4.350%  V=6.960%
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../../../lib/supabaseClient';
import { API_HR as API_HR_BASE } from '../../../../config';

// ── Constantes Colombia 2025 ──────────────────────────────────────────────────
const SMLV_2025    = 1_423_500;
const AUX_TRANSP   = 200_000;
const ARL_RISKS    = [
  { id: 'I',   label: 'I — Riesgo Mínimo',     pct: 0.522  },
  { id: 'II',  label: 'II — Riesgo Bajo',       pct: 1.044  },
  { id: 'III', label: 'III — Riesgo Medio',     pct: 2.436  },
  { id: 'IV',  label: 'IV — Riesgo Alto',       pct: 4.350  },
  { id: 'V',   label: 'V — Riesgo Máximo',      pct: 6.960  },
];

// ── Formato moneda ────────────────────────────────────────────────────────────
const fmt = (n, showSign = false) => {
  const num = Math.round(parseFloat(n) || 0);
  const s = Math.abs(num).toLocaleString('es-CO');
  if (showSign && num < 0) return `−$${s}`;
  if (showSign && num > 0) return `+$${s}`;
  return `$${s}`;
};

// ── Cálculo nómina mensual ────────────────────────────────────────────────────
function calcNomina(f) {
  const base       = parseFloat(f.base)        || 0;
  const days       = parseFloat(f.days)        || 30;
  const bonuses    = parseFloat(f.bonuses)     || 0;
  const commissions= parseFloat(f.commissions) || 0;
  const taxRet     = parseFloat(f.taxRet)      || 0;
  const volDed     = parseFloat(f.volDed)      || 0;
  const arlPct     = ARL_RISKS.find(r => r.id === f.arl)?.pct || 0.522;
  const isIntegral = f.salaryType === 'integral';

  // Salario proporcional (si días < 30)
  const baseProp = base * (days / 30);

  // Auxilio transporte: solo si base <= 2 SMLV y no es integral
  const auxTransp = (!isIntegral && base <= 2 * SMLV_2025) ? AUX_TRANSP * (days / 30) : 0;

  // Devengado total
  const devengado = baseProp + auxTransp + bonuses + commissions;

  // Deducciones empleado (% sobre base proporcional)
  const saludEmp   = baseProp * 0.04;
  const pensionEmp = baseProp * 0.04;
  const totalDed   = saludEmp + pensionEmp + taxRet + volDed;

  // Neto empleado
  const neto = devengado - totalDed;

  // Aportes empleador (% sobre base proporcional)
  const saludEr   = baseProp * (isIntegral ? 0 : 0.085);
  const pensionEr = baseProp * (isIntegral ? 0 : 0.12);
  const arl       = baseProp * arlPct / 100;
  const caja      = isIntegral ? 0 : baseProp * 0.04;
  const icbf      = isIntegral ? 0 : baseProp * 0.03;
  const sena      = isIntegral ? 0 : baseProp * 0.02;
  const totalEr   = saludEr + pensionEr + arl + caja + icbf + sena;
  const costoTotal = neto + totalEr;

  return {
    baseProp, auxTransp, bonuses, commissions, devengado,
    saludEmp, pensionEmp, taxRet, volDed, totalDed,
    neto,
    saludEr, pensionEr, arl, caja, icbf, sena, totalEr,
    costoTotal, arlPct,
    isIntegral,
  };
}

// ── Cálculo liquidación laboral ───────────────────────────────────────────────
function calcLiquidacion(f) {
  const base    = parseFloat(f.liqBase)  || 0;
  const inicio  = f.liqStart ? new Date(f.liqStart) : null;
  const fin     = f.liqEnd   ? new Date(f.liqEnd)   : null;
  if (!inicio || !fin || fin <= inicio) return null;

  const diffMs  = fin - inicio;
  const diffDays= Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const years   = diffDays / 365;

  // Cesantías: 1 mes de salario por año trabajado
  const cesantias = (base / 360) * diffDays;

  // Intereses sobre cesantías: 12% anual sobre cesantías
  const intereses = cesantias * 0.12 * years;

  // Vacaciones: 15 días hábiles por año (se pagan como $base/24 * años)
  const vacaciones = (base / 24) * years;

  // Prima de servicios: 1 mes por año (se paga semestralmente)
  const prima = (base / 12) * diffDays / 30;

  const total = cesantias + intereses + vacaciones + prima;

  return { diffDays, years, cesantias, intereses, vacaciones, prima, total };
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function SalaryTab({ member, workspace, currentUser }) {
  const canEdit = currentUser?.role === 'owner' || currentUser?.role === 'admin' || currentUser?.is_superuser;
  const API_HR  = API_HR_BASE;
  const SB_URL  = 'https://sciorfjvdqxvcwgvnmbv.supabase.co';

  const [mode,   setMode]   = useState('nomina');
  const [saving, setSaving] = useState(false);
  const [saved,  setSaved]  = useState(false);
  // HISTORIAL
  const [payments,       setPayments]       = useState([]);
  const [generatingVoucher, setGeneratingVoucher] = useState(null);
  const [registeringPay,    setRegisteringPay]    = useState(false);
  const [showHistory,       setShowHistory]       = useState(false); // kept for compatibility
  const [f, setF] = useState({
    base: '',
    salaryType: 'base',
    days: '30',
    arl: 'I',
    bonuses: '',
    commissions: '',
    taxRet: '',
    volDed: '',
    // Liquidación
    liqBase: '',
    liqStart: '',
    liqEnd: '',
  });

  // Cargar salario guardado al montar
  useEffect(() => {
    if (!member?.id || !workspace?.id) return;
    fetch(`${API_HR}/salary/${member.id}?workspace_id=${workspace.id}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data) return;
        setF(prev => ({
          ...prev,
          base:        data.base_amount   ? String(data.base_amount)   : prev.base,
          salaryType:  data.salary_type   || prev.salaryType,
          bonuses:     data.bonuses       ? String(data.bonuses)       : prev.bonuses,
          commissions: data.commissions   ? String(data.commissions)   : prev.commissions,
          taxRet:      data.tax_withholding ? String(data.tax_withholding) : prev.taxRet,
          volDed:      data.voluntary_deductions ? String(data.voluntary_deductions) : prev.volDed,
          arl:         (() => {
            const pct = parseFloat(data.arl_pct);
            const lvl = ARL_RISKS.find(r => Math.abs(r.pct - pct) < 0.01);
            return lvl ? lvl.id : 'I';
          })(),
        }));
      })
      .catch(() => {});
    loadPayments();
  }, [member?.id, workspace?.id]);

  const loadPayments = () => {
    if (!member?.id || !workspace?.id) return;
    fetch(`${API_HR}/payments/${member.id}?workspace_id=${workspace.id}`)
      .then(r => r.ok ? r.json() : [])
      .then(d => setPayments(Array.isArray(d) ? d : []))
      .catch(() => {});
  };

  const handleSave = async () => {
    if (!canEdit) return;
    setSaving(true);
    const arlPct = ARL_RISKS.find(r => r.id === f.arl)?.pct || 0.522;
    try {
      await fetch(`${API_HR}/salary/${member.id}?workspace_id=${workspace.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          salary_type:           f.salaryType,
          base_amount:           parseFloat(f.base)        || 0,
          bonuses:               parseFloat(f.bonuses)     || 0,
          commissions:           parseFloat(f.commissions) || 0,
          tax_withholding:       parseFloat(f.taxRet)      || 0,
          voluntary_deductions:  parseFloat(f.volDed)      || 0,
          arl_pct:               arlPct,
          transport_allowance:   (f.salaryType === 'base' && parseFloat(f.base) <= 2 * SMLV_2025)
                                   ? AUX_TRANSP : 0,
        }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch {}
    finally { setSaving(false); }
  };

  const setField = (k, v) => setF(prev => ({ ...prev, [k]: v }));

  const nom = mode === 'nomina' ? calcNomina(f) : null;
  const liq = mode === 'liquidacion' ? calcLiquidacion(f) : null;
  const hasResult = mode === 'nomina'
    ? (parseFloat(f.base) > 0)
    : (liq !== null);

  return (
    <div style={S.root}>

      {/* ── HEADER ───────────────────────────────────────────── */}
      <div style={S.header}>
        <div>
          <div style={S.title}>CALCULADORA SALARIAL</div>
          <div style={S.subtitle}>Colombia 2025 · SMLV ${SMLV_2025.toLocaleString('es-CO')}</div>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          {mode === 'nomina' && canEdit && parseFloat(f.base) > 0 && (
            <button style={{ ...S.saveBtn, ...(saved ? S.saveBtnOk : {}) }}
              onClick={handleSave} disabled={saving}>
              {saving ? '...' : saved ? '✓ GUARDADO' : '↓ GUARDAR REF.'}
            </button>
          )}
          <div style={S.modeToggle}>
            <button style={{ ...S.modeBtn, ...(mode === 'nomina' ? S.modeBtnActive : {}) }}
              onClick={() => setMode('nomina')}>◈ NÓMINA MENSUAL</button>
            <button style={{ ...S.modeBtn, ...(mode === 'liquidacion' ? S.modeBtnActive : {}) }}
              onClick={() => setMode('liquidacion')}>◉ LIQUIDACIÓN</button>
          </div>
        </div>
      </div>

      <div style={S.body}>

        {/* ════════════════════════════════════════════════════ */}
        {/* PANEL IZQUIERDO — ENTRADAS                          */}
        {/* ════════════════════════════════════════════════════ */}
        <div style={S.inputPanel}>

          {/* ── NÓMINA INPUTS ── */}
          {mode === 'nomina' && (
            <>
              <Section title="SALARIO BASE">
                <InputRow label="SALARIO BASE (COP)">
                  <MoneyInput id="base" value={f.base} onChange={v => setField('base', v)} placeholder="Ej: 3000000" />
                </InputRow>
                <InputRow label="TIPO DE SALARIO">
                  <div style={{ display: 'flex', gap: '6px' }}>
                    {['base', 'integral'].map(t => (
                      <button key={t}
                        style={{ ...S.typeBtn, ...(f.salaryType === t ? S.typeBtnActive : {}) }}
                        onClick={() => setField('salaryType', t)}>
                        {t === 'base' ? 'BASE' : 'INTEGRAL'}
                      </button>
                    ))}
                  </div>
                  {f.salaryType === 'integral' && (
                    <div style={S.infoNote}>⚠ Salario integral: sin auxilio de transporte ni parafiscales del empleador</div>
                  )}
                </InputRow>
                <InputRow label="DÍAS TRABAJADOS">
                  <input style={S.input} type="number" min="1" max="30"
                    value={f.days} onChange={e => setField('days', e.target.value)} />
                </InputRow>
                {/* Auxilio transporte auto */}
                {f.base && parseFloat(f.base) <= 2 * SMLV_2025 && f.salaryType === 'base' && (
                  <div style={S.autoCalc}>
                    ✓ Auxilio de transporte aplicado: {fmt(AUX_TRANSP * (parseFloat(f.days) || 30) / 30)} (automático)
                  </div>
                )}
              </Section>

              <Section title="INGRESOS ADICIONALES">
                <InputRow label="BONOS / OTROS INGRESOS">
                  <MoneyInput id="bonuses" value={f.bonuses} onChange={v => setField('bonuses', v)} />
                </InputRow>
                <InputRow label="COMISIONES VARIABLES">
                  <MoneyInput id="commissions" value={f.commissions} onChange={v => setField('commissions', v)} />
                </InputRow>
              </Section>

              <Section title="DEDUCCIONES EMPLEADO">
                <InputRow label="RETENCIÓN EN LA FUENTE">
                  <MoneyInput id="taxRet" value={f.taxRet} onChange={v => setField('taxRet', v)} />
                </InputRow>
                <InputRow label="DESCUENTOS VOLUNTARIOS">
                  <MoneyInput id="volDed" value={f.volDed} onChange={v => setField('volDed', v)} />
                </InputRow>
              </Section>

              <Section title="NIVEL RIESGO ARL (EMPLEADOR)">
                <select style={{ ...S.input, width: '100%' }}
                  value={f.arl} onChange={e => setField('arl', e.target.value)}>
                  {ARL_RISKS.map(r => (
                    <option key={r.id} value={r.id}>{r.label} ({r.pct}%)</option>
                  ))}
                </select>
              </Section>
            </>
          )}

          {/* ── LIQUIDACIÓN INPUTS ── */}
          {mode === 'liquidacion' && (
            <>
              <Section title="DATOS DEL EMPLEADO">
                <InputRow label="ÚLTIMO SALARIO BASE (COP)">
                  <MoneyInput id="liqBase" value={f.liqBase} onChange={v => setField('liqBase', v)} placeholder="Ej: 3000000" />
                </InputRow>
                <InputRow label="FECHA DE INICIO">
                  <input style={S.input} type="date"
                    value={f.liqStart} onChange={e => setField('liqStart', e.target.value)} />
                </InputRow>
                <InputRow label="FECHA DE RETIRO">
                  <input style={S.input} type="date"
                    value={f.liqEnd} onChange={e => setField('liqEnd', e.target.value)} />
                </InputRow>
                {f.liqStart && f.liqEnd && liq && (
                  <div style={S.autoCalc}>
                    ✓ Tiempo laborado: {liq.diffDays} días ({liq.years.toFixed(2)} años)
                  </div>
                )}
                {f.liqStart && f.liqEnd && !liq && (
                  <div style={{ ...S.autoCalc, color: '#EF4444' }}>
                    ✗ La fecha de retiro debe ser posterior a la de inicio
                  </div>
                )}
              </Section>

              <div style={S.liqInfo}>
                <div style={S.liqInfoTitle}>¿Qué incluye esta liquidación?</div>
                <ul style={S.liqInfoList}>
                  <li><span style={{ color: '#10B981' }}>◈</span> Cesantías (1 mes/año laborado)</li>
                  <li><span style={{ color: '#0EA5E9' }}>◈</span> Intereses sobre cesantías (12%/año)</li>
                  <li><span style={{ color: '#F59E0B' }}>◈</span> Vacaciones (15 días/año)</li>
                  <li><span style={{ color: '#A78BFA' }}>◈</span> Prima de servicios (1 mes/año)</li>
                </ul>
                <div style={{ color: '#334155', fontSize: '10px', marginTop: '8px' }}>
                  * No incluye indemnizaciones ni sanciones. Cálculo referencial.
                </div>
              </div>
            </>
          )}
        </div>

        {/* ════════════════════════════════════════════════════ */}
        {/* PANEL DERECHO — RESULTADOS                          */}
        {/* ════════════════════════════════════════════════════ */}
        <div style={S.resultPanel}>

          {!hasResult && (
            <div style={S.placeholder}>
              <div style={S.placeholderIcon}>◈</div>
              <div style={S.placeholderText}>
                {mode === 'nomina'
                  ? 'Ingresa el salario base para calcular'
                  : 'Ingresa el salario y las fechas para calcular la liquidación'}
              </div>
            </div>
          )}

          {/* ── RESULTADO NÓMINA ── */}
          {hasResult && nom && (
            <>
              {/* Neto — el número más importante */}
              <div style={S.netoBig}>
                <div style={S.netoBigLabel}>NETO A PAGAR</div>
                <div style={S.netoBigValue}>{fmt(nom.neto)}</div>
                <div style={S.netoBigSub}>COP · {f.days} días trabajados</div>
              </div>

              {/* Desglose */}
              <div style={S.resultSection}>
                <div style={S.resultSectionTitle}>◈ DEVENGADO</div>
                <ResultRow label={`Salario base${parseFloat(f.days) < 30 ? ` (${f.days} días)` : ''}`} value={nom.baseProp} />
                {nom.auxTransp > 0 && <ResultRow label="Auxilio de transporte" value={nom.auxTransp} accent="#10B981" />}
                {nom.bonuses > 0  && <ResultRow label="Bonos" value={nom.bonuses} />}
                {nom.commissions > 0 && <ResultRow label="Comisiones" value={nom.commissions} />}
                <ResultRow label="TOTAL DEVENGADO" value={nom.devengado} bold accent="#10B981" />
              </div>

              <div style={S.resultSection}>
                <div style={S.resultSectionTitle}>◉ DEDUCCIONES EMPLEADO</div>
                <ResultRow label={`Salud empleado (4%)`} value={-nom.saludEmp} accent="#EF4444" />
                <ResultRow label={`Pensión empleado (4%)`} value={-nom.pensionEmp} accent="#EF4444" />
                {nom.taxRet > 0 && <ResultRow label="Retención en la fuente" value={-nom.taxRet} accent="#EF4444" />}
                {nom.volDed > 0 && <ResultRow label="Descuentos voluntarios" value={-nom.volDed} accent="#EF4444" />}
                <ResultRow label="TOTAL DEDUCCIONES" value={-nom.totalDed} bold accent="#EF4444" />
              </div>

              <div style={{ ...S.resultSection, borderColor: '#0EA5E9' }}>
                <ResultRow label="══ NETO A PAGAR" value={nom.neto} bold accent="#0EA5E9" large />
              </div>

              {!nom.isIntegral && (
                <div style={S.resultSection}>
                  <div style={S.resultSectionTitle}>◬ APORTES EMPLEADOR</div>
                  <ResultRow label={`Salud empleador (8.5%)`} value={nom.saludEr} accent="#F59E0B" />
                  <ResultRow label={`Pensión empleador (12%)`} value={nom.pensionEr} accent="#F59E0B" />
                  <ResultRow label={`ARL (${nom.arlPct}%)`} value={nom.arl} accent="#F59E0B" />
                  <ResultRow label="Caja compensación (4%)" value={nom.caja} accent="#F59E0B" />
                  <ResultRow label="ICBF (3%)" value={nom.icbf} accent="#F59E0B" />
                  <ResultRow label="SENA (2%)" value={nom.sena} accent="#F59E0B" />
                  <ResultRow label="TOTAL APORTES EMPLEADOR" value={nom.totalEr} bold accent="#F59E0B" />
                </div>
              )}

              <div style={{ ...S.resultSection, borderColor: '#A78BFA', background: '#0d0d0d' }}>
                <ResultRow label="COSTO TOTAL EMPRESA" value={nom.costoTotal} bold accent="#A78BFA" large />
              </div>
            </>
          )}

          {/* ── RESULTADO LIQUIDACIÓN ── */}
          {hasResult && liq && mode === 'liquidacion' && (
            <>
              <div style={S.netoBig}>
                <div style={S.netoBigLabel}>TOTAL LIQUIDACIÓN</div>
                <div style={S.netoBigValue}>{fmt(liq.total)}</div>
                <div style={S.netoBigSub}>{liq.diffDays} días · {liq.years.toFixed(2)} años</div>
              </div>

              <div style={S.resultSection}>
                <ResultRow label="Cesantías (1 mes/año)" value={liq.cesantias} accent="#10B981" />
                <div style={S.liqFormula}>
                  = ${(parseFloat(f.liqBase)||0).toLocaleString('es-CO')} / 360 × {liq.diffDays} días
                </div>

                <ResultRow label="Intereses s/ cesantías (12%/año)" value={liq.intereses} accent="#0EA5E9" />
                <div style={S.liqFormula}>
                  = {fmt(liq.cesantias)} × 12% × {liq.years.toFixed(2)} años
                </div>

                <ResultRow label="Vacaciones (15 días/año)" value={liq.vacaciones} accent="#F59E0B" />
                <div style={S.liqFormula}>
                  = ${(parseFloat(f.liqBase)||0).toLocaleString('es-CO')} / 24 × {liq.years.toFixed(2)} años
                </div>

                <ResultRow label="Prima de servicios (1 mes/año)" value={liq.prima} accent="#A78BFA" />
                <div style={S.liqFormula}>
                  = ${(parseFloat(f.liqBase)||0).toLocaleString('es-CO')} / 12 × {liq.diffDays}/30 meses
                </div>
              </div>

              <div style={{ ...S.resultSection, borderColor: '#10B981', background: '#0d0d0d' }}>
                <ResultRow label="TOTAL A PAGAR" value={liq.total} bold accent="#10B981" large />
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── HISTORIAL DE PAGOS ───────────────────────────────── */}
      {showHistory && (
        <div style={SH.panel}>
          <div style={SH.header}>
            <div>
              <span style={SH.title}>◉ HISTORIAL DE PAGOS</span>
              <span style={{ color: '#334155', fontSize: '10px', marginLeft: '10px' }}>
                {payments.length} registro{payments.length !== 1 ? 's' : ''}
              </span>
            </div>
            {canEdit && mode === 'nomina' && parseFloat(f.base) > 0 && (
              <button style={SH.regBtn} disabled={registeringPay}
                onClick={() => handleRegisterPayment()}>
                {registeringPay ? 'Registrando...' : '+ REGISTRAR PAGO ACTUAL'}
              </button>
            )}
          </div>

          {payments.length === 0 ? (
            <div style={SH.empty}>Sin registros de pago aún.</div>
          ) : (
            <div style={SH.tableWrap}>
              <table style={SH.table}>
                <thead>
                  <tr>
                    {['PERÍODO','SALARIO BASE','DEVENGADO','DEDUCCIONES','NETO A PAGAR','COSTO EMPRESA','FECHA PAGO','COMPROBANTE'].map(h => (
                      <th key={h} style={SH.th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {payments.map(p => (
                    <tr key={p.id} style={SH.tr}>
                      <td style={{ ...SH.td, color: '#0EA5E9', fontWeight: 700 }}>{p.period_label}</td>
                      <td style={SH.td}>{fmt(p.base_amount)}</td>
                      <td style={{ ...SH.td, color: '#10B981' }}>{fmt(p.devengado_total)}</td>
                      <td style={{ ...SH.td, color: '#EF4444' }}>{fmt(p.deduccion_empleado)}</td>
                      <td style={{ ...SH.td, color: '#0EA5E9', fontWeight: 700 }}>{fmt(p.neto_a_pagar)}</td>
                      <td style={{ ...SH.td, color: '#F59E0B' }}>{fmt(p.costo_empleador)}</td>
                      <td style={{ ...SH.td, color: '#64748b' }}>
                        {p.payment_date ? new Date(p.payment_date).toLocaleDateString('es-CO') : '—'}
                      </td>
                      <td style={SH.td}>
                        {p.voucher_document_id ? (
                          <span style={{ color: '#10B981', fontSize: '10px' }}>✓ Generado</span>
                        ) : (
                          <button style={SH.voucherBtn}
                            disabled={generatingVoucher === p.id}
                            onClick={() => handleGenerateVoucher(p)}>
                            {generatingVoucher === p.id ? '...' : '◈ Generar'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );

  // ── Registrar pago actual ──────────────────────────────────────────────
  async function handleRegisterPayment() {
    if (!nom) return;
    const now = new Date();
    const monthNames = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
    setRegisteringPay(true);
    try {
      await fetch(`${API_HR}/payments/${member.id}?workspace_id=${workspace.id}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          period_label:       `${monthNames[now.getMonth()]} ${now.getFullYear()}`,
          period_month:       now.getMonth() + 1,
          period_year:        now.getFullYear(),
          base_amount:        nom.baseProp,
          devengado_total:    nom.devengado,
          deduccion_empleado: nom.totalDed,
          neto_a_pagar:       nom.neto,
          costo_empleador:    nom.totalEr,
          payment_date:       now.toISOString().slice(0, 10),
        }),
      });
      loadPayments();
    } finally { setRegisteringPay(false); }
  }

  // ── Generar comprobante HTML y subir a documentos ──────────────────────
  async function handleGenerateVoucher(payment) {
    setGeneratingVoucher(payment.id);
    try {
      const html = buildVoucherHTML(payment, member?.name || 'Empleado');
      const blob = new Blob([html], { type: 'text/html' });
      const fileName = `comprobante_nomina_${payment.period_label.replace(' ', '_')}.html`;
      const storagePath = `${workspace.id}/${member.id}/${Date.now()}_${fileName}`;

      // Subir a Supabase storage
      const { error: sErr } = await supabase.storage.from('hr-docs').upload(storagePath, blob, { contentType: 'text/html', upsert: false });
      if (sErr) throw new Error(sErr.message);

      const fileUrl = `${SB_URL}/storage/v1/object/public/hr-docs/${storagePath}`;

      // Guardar en hr_documents con categoría 'nomina'
      const docRes = await fetch(`${API_HR}/documents/${member.id}?workspace_id=${workspace.id}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_name:   fileName,
          file_url:    fileUrl,
          file_size:   blob.size,
          mime_type:   'text/html',
          category:    'nomina',
          folder_id:   null,
          uploaded_by: currentUser?.id,
        }),
      });
      const doc = await docRes.json();

      // Vincular comprobante al registro de pago
      await fetch(`${API_HR}/payments/${member.id}/${payment.id}/voucher?doc_id=${doc.id}`, { method: 'PUT' });
      loadPayments();
    } catch (e) {
      alert('Error generando comprobante: ' + e.message);
    } finally {
      setGeneratingVoucher(null);
    }
  }
}

// ── Sub-componentes ───────────────────────────────────────────────────────────
function Section({ title, children }) {
  return (
    <div style={SS.section}>
      <div style={SS.sectionTitle}>{title}</div>
      {children}
    </div>
  );
}

function InputRow({ label, children }) {
  return (
    <div style={SS.row}>
      <label style={SS.label}>{label}</label>
      {children}
    </div>
  );
}

function MoneyInput({ id, value, onChange, placeholder = '0' }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
      <span style={{ color: '#64748b', fontSize: '13px', fontFamily: '"IBM Plex Mono", monospace' }}>$</span>
      <input
        id={id} type="number" min="0" step="1000"
        value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{ ...S.input, flex: 1 }}
      />
    </div>
  );
}

function ResultRow({ label, value, bold = false, accent = '#e2e8f0', large = false }) {
  const num = Math.round(parseFloat(value) || 0);
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '5px 0', borderBottom: '1px solid #0f0f0f' }}>
      <span style={{ color: bold ? '#94a3b8' : '#64748b', fontSize: bold ? '11px' : '10px', letterSpacing: '0.5px', fontFamily: '"IBM Plex Mono", monospace' }}>
        {label}
      </span>
      <span style={{ color: accent, fontWeight: bold ? 700 : 400, fontSize: large ? '16px' : bold ? '14px' : '13px', fontFamily: '"IBM Plex Mono", monospace', flexShrink: 0 }}>
        {num < 0 ? `−${fmt(Math.abs(num))}` : fmt(num)}
      </span>
    </div>
  );
}

// ── Estilos ───────────────────────────────────────────────────────────────────
const C = { bg: '#0a0a0a', card: '#111', border: '#1e1e1e', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

const S = {
  root:    { display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', fontFamily: '"IBM Plex Mono", monospace', background: C.bg },
  header:  { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px', borderBottom: `2px solid ${C.border}`, flexShrink: 0, flexWrap: 'wrap', gap: '10px' },
  title:   { color: C.accent, fontSize: '13px', fontWeight: 700, letterSpacing: '2px' },
  subtitle:{ color: C.dim, fontSize: '10px', marginTop: '2px' },
  modeToggle: { display: 'flex', border: `2px solid ${C.border}` },
  modeBtn: { background: 'transparent', border: 'none', color: C.dim, padding: '6px 14px', cursor: 'pointer', fontSize: '11px', letterSpacing: '0.5px', fontFamily: '"IBM Plex Mono", monospace', transition: 'all .15s' },
  modeBtnActive: { background: C.accent, color: '#000', fontWeight: 700 },
  body:    { flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 },
  saveBtn: { background: 'transparent', border: '2px solid #0EA5E9', color: '#0EA5E9', padding: '6px 14px', cursor: 'pointer', fontSize: '11px', fontWeight: 700, letterSpacing: '0.5px', fontFamily: '"IBM Plex Mono", monospace', transition: 'all .2s' },
  saveBtnOk: { background: '#10B98120', borderColor: '#10B981', color: '#10B981' },

  // Input panel
  inputPanel:   { width: '300px', minWidth: '260px', borderRight: `2px solid ${C.border}`, overflowY: 'auto', overflowX: 'hidden', padding: '16px', display: 'flex', flexDirection: 'column', gap: '4px', flexShrink: 0 },
  input:        { background: '#1a1a1a', border: `2px solid #2a2a2a`, color: C.text, padding: '8px 10px', fontSize: '13px', fontFamily: '"IBM Plex Mono", monospace', outline: 'none', width: '100%', boxSizing: 'border-box', transition: 'border-color .15s' },
  typeBtn:      { flex: 1, padding: '7px 0', border: `2px solid #2a2a2a`, background: 'transparent', color: C.dim, cursor: 'pointer', fontSize: '11px', letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace', transition: 'all .15s' },
  typeBtnActive:{ borderColor: C.accent, color: C.accent, background: 'rgba(14,165,233,0.1)' },
  autoCalc:     { color: '#10B981', fontSize: '10px', padding: '6px 8px', background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)', marginTop: '4px' },
  infoNote:     { color: '#F59E0B', fontSize: '10px', marginTop: '6px', lineHeight: 1.4 },
  liqInfo:      { background: '#0f0f0f', border: `1px solid ${C.border}`, padding: '12px', marginTop: '8px' },
  liqInfoTitle: { color: C.dim, fontSize: '10px', letterSpacing: '1px', marginBottom: '8px' },
  liqInfoList:  { color: '#94a3b8', fontSize: '11px', lineHeight: '1.8', margin: 0, paddingLeft: '16px' },

  // Result panel
  resultPanel:  { flex: 1, overflowY: 'auto', overflowX: 'hidden', padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px', minWidth: 0 },
  placeholder:  { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px', padding: '40px', color: C.dim },
  placeholderIcon: { fontSize: '32px', opacity: 0.3 },
  placeholderText: { fontSize: '12px', textAlign: 'center', maxWidth: '220px', lineHeight: 1.6 },

  // Neto banner
  netoBig:      { background: 'linear-gradient(135deg, #0d1117 0%, #0a1628 100%)', border: `2px solid #0EA5E9`, padding: '20px', textAlign: 'center' },
  netoBigLabel: { color: C.dim, fontSize: '10px', letterSpacing: '3px', marginBottom: '6px' },
  netoBigValue: { color: '#0EA5E9', fontSize: '28px', fontWeight: 700, letterSpacing: '-1px' },
  netoBigSub:   { color: C.dim, fontSize: '10px', marginTop: '4px' },

  // Result sections
  resultSection: { border: `1px solid ${C.border}`, padding: '10px 14px', background: '#0b0b0b' },
  resultSectionTitle: { color: C.dim, fontSize: '9px', letterSpacing: '2px', marginBottom: '8px', fontWeight: 700 },
  liqFormula:   { color: '#334155', fontSize: '10px', padding: '2px 0 6px', fontStyle: 'italic' },
};

const SS = {
  section:     { marginBottom: '12px' },
  sectionTitle:{ color: C.dim, fontSize: '9px', letterSpacing: '2px', padding: '6px 0', borderBottom: `1px solid ${C.border}`, marginBottom: '10px', fontWeight: 700 },
  row:         { display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '10px' },
  label:       { color: C.dim, fontSize: '10px', letterSpacing: '1px' },
};

// ── Estilos historial de pagos ─────────────────────────────────────────────────
const SH = {
  panel:      { borderTop: '2px solid #1e2e3e', background: '#07070a', flexShrink: 0, maxHeight: '320px', display: 'flex', flexDirection: 'column' },
  header:     { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 18px', borderBottom: '1px solid #1a1a1a', flexShrink: 0 },
  title:      { color: '#0EA5E9', fontSize: '11px', letterSpacing: '2px', fontWeight: 700, fontFamily: '"IBM Plex Mono", monospace' },
  regBtn:     { background: '#10B98115', border: '1px solid #10B981', color: '#10B981', padding: '5px 12px', cursor: 'pointer', fontSize: '10px', fontWeight: 700, fontFamily: '"IBM Plex Mono", monospace', letterSpacing: '0.5px' },
  tableWrap:  { flex: 1, overflowY: 'auto', overflowX: 'auto' },
  table:      { width: '100%', borderCollapse: 'collapse', fontFamily: '"IBM Plex Mono", monospace', fontSize: '11px' },
  th:         { color: '#334155', fontSize: '9px', letterSpacing: '1.5px', padding: '6px 12px', textAlign: 'left', borderBottom: '1px solid #1a1a1a', fontWeight: 700, whiteSpace: 'nowrap', background: '#0a0a0a', position: 'sticky', top: 0 },
  tr:         { borderBottom: '1px solid #0f0f0f' },
  td:         { color: '#94a3b8', padding: '7px 12px', whiteSpace: 'nowrap', fontFamily: '"IBM Plex Mono", monospace' },
  voucherBtn: { background: 'transparent', border: '1px solid #0EA5E9', color: '#0EA5E9', padding: '3px 8px', cursor: 'pointer', fontSize: '10px', fontFamily: '"IBM Plex Mono", monospace' },
  empty:      { color: '#334155', fontSize: '11px', padding: '24px 18px', fontFamily: '"IBM Plex Mono", monospace' },
};

// ── Generador de comprobante HTML ──────────────────────────────────────────────
function buildVoucherHTML(payment, employeeName) {
  const fmt2 = n => `$${Math.round(parseFloat(n)||0).toLocaleString('es-CO')}`;
  const now   = new Date().toLocaleDateString('es-CO', { year:'numeric', month:'long', day:'numeric' });
  return `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Comprobante de Nómina — ${payment.period_label}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'IBM Plex Mono', 'Courier New', monospace; background: #0a0a0a; color: #e2e8f0; padding: 40px; }
    .header { border-bottom: 2px solid #0EA5E9; padding-bottom: 18px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; }
    .company { font-size: 20px; font-weight: 700; color: #0EA5E9; letter-spacing: 3px; }
    .subtitle { color: #64748b; font-size: 11px; margin-top: 4px; }
    .badge { background: #0EA5E920; border: 1px solid #0EA5E9; color: #0EA5E9; padding: 6px 14px; font-size: 11px; letter-spacing: 1px; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 24px; margin-bottom: 24px; }
    .info-row { display: flex; justify-content: space-between; border-bottom: 1px solid #1e1e1e; padding: 4px 0; font-size: 12px; }
    .info-label { color: #64748b; }
    .info-value { color: #e2e8f0; font-weight: 600; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    th { background: #0f0f0f; color: #64748b; font-size: 9px; letter-spacing: 2px; padding: 8px 12px; text-align: left; border-bottom: 2px solid #1e1e1e; }
    td { padding: 9px 12px; font-size: 12px; border-bottom: 1px solid #0f0f0f; }
    .dev { color: #10B981; }
    .ded { color: #EF4444; }
    .emp { color: #F59E0B; }
    .net { color: #0EA5E9; font-size: 18px; font-weight: 700; }
    .total-row td { border-top: 2px solid #1e1e1e; padding-top: 12px; }
    .footer { color: #334155; font-size: 10px; margin-top: 24px; border-top: 1px solid #1e1e1e; padding-top: 16px; text-align: center; }
    @media print { body { background: #fff; color: #000; } .company { color: #0055cc; } .badge { border-color: #0055cc; color: #0055cc; } }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <div class="company">◈ FIN-SYS OS</div>
      <div class="subtitle">SISTEMA DE GESTIÓN EMPRESARIAL · MÓDULO RRHH</div>
      <div class="subtitle" style="margin-top:8px;">Comprobante de Pago de Nómina</div>
    </div>
    <div>
      <div class="badge">PERÍODO: ${payment.period_label.toUpperCase()}</div>
      <div class="subtitle" style="margin-top:8px; text-align:right;">Generado: ${now}</div>
    </div>
  </div>

  <div class="info-grid">
    <div>
      <div class="info-row"><span class="info-label">EMPLEADO</span><span class="info-value">${employeeName}</span></div>
      <div class="info-row"><span class="info-label">PERÍODO</span><span class="info-value">${payment.period_label}</span></div>
      <div class="info-row"><span class="info-label">FECHA PAGO</span><span class="info-value">${payment.payment_date ? new Date(payment.payment_date).toLocaleDateString('es-CO') : '—'}</span></div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>CONCEPTO</th>
        <th>VALOR</th>
        <th>TIPO</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>Salario Base</td><td>${fmt2(payment.base_amount)}</td><td style="color:#64748b;font-size:10px;">DEVENGADO</td></tr>
      <tr><td class="dev">Total Devengado</td><td class="dev">${fmt2(payment.devengado_total)}</td><td style="color:#64748b;font-size:10px;">DEVENGADO</td></tr>
      <tr><td class="ded">Total Deducciones Empleado</td><td class="ded">- ${fmt2(payment.deduccion_empleado)}</td><td style="color:#64748b;font-size:10px;">DEDUCCIÓN</td></tr>
      <tr class="total-row">
        <td><strong>NETO A PAGAR</strong></td>
        <td class="net">${fmt2(payment.neto_a_pagar)}</td>
        <td></td>
      </tr>
      <tr><td class="emp">Costo Total Empresa</td><td class="emp">${fmt2(payment.costo_empleador)}</td><td style="color:#64748b;font-size:10px;">COSTO EMPLEADOR</td></tr>
    </tbody>
  </table>

  <div class="footer">
    Este comprobante fue generado automáticamente por FIN-SYS OS · Módulo RRHH · ${now}
    <br>Conserve este documento para sus registros contables.
  </div>
</body>
</html>`;
}
