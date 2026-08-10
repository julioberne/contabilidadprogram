/* ============================================================
   AdvancedSections.jsx — Secciones colapsables del Módulo 01
   Restauradas del monolito original (App.jsx @5ff195e L1707-2131),
   que se perdieron en la unificación (daff300 las "movió" al
   ContextPanel pero varias quedaron sin UI o desconectadas):
     [+] Tercero        (también disponible en el panel derecho)
     [%] Impuestos      (IVA / Propina / GMF / tasas custom)
     [+] Cartera        (CXC / CXP)
     [+] Activos        (incluye "Establecer como Activo" — sin
                         este checkbox el bloque asset SIEMPRE
                         viajaba null al backend)
   Consume el TransactionDraftProvider directamente: todos los
   setters ya existían, solo faltaba la UI.
   ============================================================ */
import { useState } from 'react';
import { useTransactionDraft } from '../../engine/TransactionDraftProvider.jsx';

function Section({ icon, title, badge, open, onToggle, children }) {
  return (
    <div className="border-2 border-black bg-white">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex justify-between items-center px-2 py-1.5 text-xs font-bold uppercase hover:bg-brutalNeutral transition-all"
      >
        <span>{open ? "[-]" : "[+]"} {icon} {title}</span>
        {badge ? (
          <span className="text-[10px] bg-brutalGreen border border-black px-1 font-bold">{badge}</span>
        ) : null}
      </button>
      {open && <div className="border-t-2 border-black p-2 space-y-2 bg-brutalBg">{children}</div>}
    </div>
  );
}

const inputCls = "w-full bg-white border-2 border-black p-1.5 text-xs font-mono outline-none focus:border-brutalGreen";
const labelCls = "text-[10px] font-bold uppercase block mb-0.5";

function Check({ checked, onChange, children }) {
  return (
    <label className="flex items-center gap-2 text-xs font-bold uppercase cursor-pointer select-none">
      <input type="checkbox" checked={!!checked} onChange={e => onChange(e.target.checked)}
             className="w-4 h-4 accent-black" />
      <span>{children}</span>
    </label>
  );
}

export default function AdvancedSections() {
  const d = useTransactionDraft();
  const [open, setOpen] = useState({ tercero: false, impuestos: false, cartera: false, activos: false });
  const toggle = (k) => setOpen(o => ({ ...o, [k]: !o[k] }));

  // Creador inline de tasas custom (port del monolito L1907-1930)
  const [taxName, setTaxName] = useState("");
  const [taxRate, setTaxRate] = useState("");
  const [taxType, setTaxType] = useState("ADDITIVE");
  const addCustomTax = () => {
    const rate = parseFloat(taxRate);
    if (!taxName.trim() || isNaN(rate) || rate <= 0) return;
    d.setCustomTaxesList(prev => [...prev, {
      id: Date.now(), name: taxName.trim().toUpperCase(), rate, type: taxType, checked: true,
    }]);
    setTaxName(""); setTaxRate("");
  };

  const impuestosActivos =
    (d.applyIva ? 1 : 0) + (d.applyPropina ? 1 : 0) + (d.applyGmf ? 1 : 0) +
    (d.customTaxesList || []).filter(t => t.checked).length;

  return (
    <div className="space-y-2">

      {/* ── [+] TERCERO ─────────────────────────────────────── */}
      <Section icon="👤" title="Identificación de Tercero" open={open.tercero} onToggle={() => toggle('tercero')}
               badge={d.thirdPartyName ? d.thirdPartyName : null}>
        <div>
          <label className={labelCls}>Nombre / Razón Social</label>
          <input type="text" value={d.thirdPartyName} onChange={e => d.setThirdPartyName(e.target.value)}
                 placeholder="ej. Juan Pérez / ACME SAS" className={inputCls} />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className={labelCls}>Tipo ID</label>
            <select value={d.thirdPartyType} onChange={e => d.setThirdPartyType(e.target.value)} className={inputCls}>
              <option value="NIT">NIT</option>
              <option value="CC">CC</option>
            </select>
          </div>
          <div>
            <label className={labelCls}>Número de Identificación</label>
            <input type="text" value={d.thirdPartyNumber} onChange={e => d.setThirdPartyNumber(e.target.value)}
                   placeholder="Sin puntos ni guiones" className={inputCls} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className={labelCls}>Correo Electrónico</label>
            <input type="email" value={d.thirdPartyEmail} onChange={e => d.setThirdPartyEmail(e.target.value)}
                   placeholder="opcional" className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Teléfono</label>
            <input type="text" value={d.thirdPartyPhone} onChange={e => d.setThirdPartyPhone(e.target.value)}
                   placeholder="opcional" className={inputCls} />
          </div>
        </div>
        <p className="text-[9px] text-gray-500 uppercase">
          También puedes buscar/vincular terceros existentes en el panel derecho → 👤 Terceros
        </p>
      </Section>

      {/* ── [%] IMPUESTOS Y TASAS ───────────────────────────── */}
      <Section icon="💸" title="Impuestos y Tasas" open={open.impuestos} onToggle={() => toggle('impuestos')}
               badge={impuestosActivos > 0 ? `${impuestosActivos} activo(s)` : null}>
        <Check checked={d.applyIva} onChange={d.setApplyIva}>IVA (19%) — Aditivo</Check>
        <Check checked={d.applyPropina} onChange={d.setApplyPropina}>Propina (10%) — Aditivo</Check>
        <Check checked={d.applyGmf} onChange={d.setApplyGmf}>GMF 4x1000 — Deductivo</Check>

        {(d.customTaxesList || []).length > 0 && (
          <div className="border-t-2 border-dashed border-black pt-2 space-y-1">
            {d.customTaxesList.map(tax => (
              <div key={tax.id} className="flex items-center justify-between gap-2">
                <Check checked={tax.checked}
                       onChange={(v) => d.setCustomTaxesList(prev =>
                         prev.map(t => t.id === tax.id ? { ...t, checked: v } : t))}>
                  {tax.name} ({tax.rate}%) — {tax.type === "ADDITIVE" ? "Aditivo" : "Deductivo"}
                </Check>
                <button type="button"
                        onClick={() => d.setCustomTaxesList(prev => prev.filter(t => t.id !== tax.id))}
                        className="text-[10px] font-bold border border-black px-1 hover:bg-brutalCrimson hover:text-white">✕</button>
              </div>
            ))}
          </div>
        )}

        <div className="border-t-2 border-dashed border-black pt-2">
          <span className="text-[10px] font-bold uppercase text-gray-500 block mb-1">+ Crear tasa personalizada</span>
          <div className="grid grid-cols-3 gap-1">
            <input type="text" value={taxName} onChange={e => setTaxName(e.target.value)}
                   placeholder="Nombre" className={inputCls} />
            <input type="number" value={taxRate} onChange={e => setTaxRate(e.target.value)}
                   placeholder="%" min="0" step="0.1" className={inputCls} />
            <select value={taxType} onChange={e => setTaxType(e.target.value)} className={inputCls}>
              <option value="ADDITIVE">Aditivo</option>
              <option value="DEDUCTIVE">Deductivo</option>
            </select>
          </div>
          <button type="button" onClick={addCustomTax}
                  className="w-full mt-1 bg-black text-white border-2 border-black py-1 text-[10px] font-bold uppercase hover:bg-brutalGreen hover:text-black transition-all">
            Añadir Tasa
          </button>
        </div>
      </Section>

      {/* ── [+] CARTERA (CXC / CXP) ─────────────────────────── */}
      <Section icon="📒" title="Cartera (CxC / CxP)" open={open.cartera} onToggle={() => toggle('cartera')}
               badge={d.cxcCxpEnabled ? d.cxcCxpType : null}>
        <Check checked={d.cxcCxpEnabled} onChange={d.setCxcCxpEnabled}>
          Registrar en cartera (cuenta por cobrar / pagar)
        </Check>
        {d.cxcCxpEnabled && (
          <>
            <div className="grid grid-cols-2 gap-1">
              {["CXC", "CXP"].map(t => (
                <button key={t} type="button" onClick={() => d.setCxcCxpType(t)}
                        className={`py-1.5 text-xs font-bold uppercase border-2 border-black transition-all ${d.cxcCxpType === t ? "bg-black text-white" : "bg-white hover:bg-brutalNeutral"}`}>
                  {t === "CXC" ? "CXC — Me deben" : "CXP — Yo debo"}
                </button>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className={labelCls}>Fecha de Vencimiento*</label>
                <input type="date" value={d.cxcCxpDueDate} onChange={e => d.setCxcCxpDueDate(e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Plazo</label>
                <select value={d.cxcCxpTerm} onChange={e => d.setCxcCxpTerm(e.target.value)} className={inputCls}>
                  <option value="Corto">Corto</option>
                  <option value="Mediano">Mediano</option>
                  <option value="Largo">Largo</option>
                </select>
              </div>
            </div>
            <div>
              <label className={labelCls}>Valor Parcial (opcional — vacío = total)</label>
              <input type="number" value={d.cxcCxpValue} onChange={e => d.setCxcCxpValue(e.target.value)}
                     placeholder="Monto abonado/adeudado" className={inputCls} />
            </div>
          </>
        )}
      </Section>

      {/* ── [+] GESTIÓN DE ACTIVOS ──────────────────────────── */}
      <Section icon="🏗️" title="Gestión de Activos" open={open.activos} onToggle={() => toggle('activos')}
               badge={d.assetEnabled && d.assetEstablecerActivo ? d.assetName || "activo" : null}>
        <Check checked={d.assetEnabled} onChange={d.setAssetEnabled}>
          Esta transacción involucra un activo/recurso
        </Check>
        {d.assetEnabled && (
          <>
            <div>
              <label className={labelCls}>Nombre del Activo</label>
              <input type="text" value={d.assetName} onChange={e => d.setAssetName(e.target.value)}
                     placeholder="ej. Portátil Lenovo, Moto AKT" className={inputCls} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className={labelCls}>Valor de Compra</label>
                <input type="number" value={d.assetValue} onChange={e => d.setAssetValue(e.target.value)}
                       disabled={d.assetVincularImporte} placeholder="Monto"
                       className={inputCls + (d.assetVincularImporte ? " opacity-50" : "")} />
              </div>
              <div>
                <label className={labelCls}>Etiqueta</label>
                <input type="text" value={d.assetTag} onChange={e => d.setAssetTag(e.target.value)}
                       placeholder="ej. TECNOLOGIA" className={inputCls} />
              </div>
            </div>
            <Check checked={d.assetVincularImporte} onChange={d.setAssetVincularImporte}>
              Vincular al importe de la transacción
            </Check>
            <Check checked={d.assetEstablecerActivo} onChange={d.setAssetEstablecerActivo}>
              Establecer como Activo (patrimonio) — requerido para que se registre
            </Check>
            <Check checked={d.assetRecurrente} onChange={d.setAssetRecurrente}>
              Genera ingreso pasivo recurrente
            </Check>
          </>
        )}
      </Section>

    </div>
  );
}
