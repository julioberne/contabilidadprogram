/* ============================================================
   AdvancedSections.jsx — Secciones colapsables del Módulo 01
   Restauradas del monolito original (App.jsx @5ff195e):
     [+] Tercero      (nombre, NIT/CC, contacto)
     [%] Impuestos    (IVA / Propina / GMF / tasas custom)
     [+] Etiquetas    (tag_definitions — mismas del panel derecho)
   Cartera y Activos se retiraron del formulario por decisión del
   usuario (2026-08-10): no se evidencian en el libro mayor; sus
   flujos viven en el panel derecho (📒 Cartera / 📦 Recursos).
   Consume el TransactionDraftProvider directamente.
   ============================================================ */
import { useEffect, useState } from 'react';
import { useTransactionDraft } from '../../engine/TransactionDraftProvider.jsx';
import { API } from '../../../config';
import NumInput from '../../../shared/NumInput';

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
  const [open, setOpen] = useState({ tercero: false, impuestos: false, etiquetas: false });
  const toggle = (k) => setOpen(o => ({ ...o, [k]: !o[k] }));

  // Creador inline de tasas custom (port del monolito)
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

  // Etiquetas: mismas tag_definitions del panel derecho (GET /api/tags)
  const [allTags, setAllTags] = useState([]);
  const [newTag, setNewTag] = useState("");
  const fetchTags = () => {
    fetch(`${API}/tags`).then(r => r.ok ? r.json() : []).then(data => {
      setAllTags(Array.isArray(data) ? data : []);
    }).catch(() => {});
  };
  useEffect(() => { fetchTags(); }, []);
  const createTag = () => {
    const name = newTag.trim();
    if (!name) return;
    fetch(`${API}/tags`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    }).then(() => {
      setNewTag("");
      fetchTags();
      d.setSelectedTags(prev => prev.includes(name) ? prev : [...prev, name]);
    }).catch(() => {});
  };

  const impuestosActivos =
    (d.applyIva ? 1 : 0) + (d.applyPropina ? 1 : 0) + (d.applyGmf ? 1 : 0) +
    (d.customTaxesList || []).filter(t => t.checked).length;

  const tagsFiltradas = allTags.filter(t =>
    !d.tagSearch || t.name.toLowerCase().includes(d.tagSearch.toLowerCase()));

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
            <NumInput value={taxRate} onChange={e => setTaxRate(e.target.value)}
                   placeholder="%" className={inputCls} />
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

      {/* ── [+] ETIQUETAS ───────────────────────────────────── */}
      <Section icon="🏷️" title="Etiquetas" open={open.etiquetas} onToggle={() => toggle('etiquetas')}
               badge={(d.selectedTags || []).length > 0 ? `${d.selectedTags.length} sel.` : null}>
        <input type="text" value={d.tagSearch || ""} onChange={e => d.setTagSearch(e.target.value)}
               placeholder="🔍 Filtrar etiquetas..." className={inputCls} />
        <div className="max-h-28 overflow-y-auto space-y-0.5">
          {tagsFiltradas.length === 0 && (
            <p className="text-[10px] text-gray-500 uppercase">Sin etiquetas — crea la primera abajo</p>
          )}
          {tagsFiltradas.map(tag => {
            const sel = (d.selectedTags || []).includes(tag.name);
            return (
              <div key={tag.id}
                   onClick={() => d.setSelectedTags(prev =>
                     sel ? prev.filter(t => t !== tag.name) : [...prev, tag.name])}
                   className={`flex items-center gap-1.5 px-2 py-1 cursor-pointer border ${sel ? 'border-black bg-brutalGreen' : 'border-gray-300 bg-white hover:bg-brutalNeutral'}`}>
                <span className="text-[10px] font-mono">{sel ? '☑' : '☐'}</span>
                <span className="w-2.5 h-2.5 border border-black" style={{ backgroundColor: tag.color || '#000' }}></span>
                <span className="text-[10px] font-bold uppercase font-mono">{tag.name}</span>
              </div>
            );
          })}
        </div>
        {(d.selectedTags || []).length > 0 && (
          <div className="flex flex-wrap gap-1 border-t-2 border-dashed border-black pt-1">
            {d.selectedTags.map(t => (
              <span key={t} className="bg-black text-white px-1.5 py-0.5 text-[9px] font-bold uppercase inline-flex items-center gap-1">
                {t}
                <button type="button" onClick={() => d.setSelectedTags(prev => prev.filter(x => x !== t))}
                        className="text-gray-400 hover:text-red-300">×</button>
              </span>
            ))}
          </div>
        )}
        <div className="flex gap-1 border-t-2 border-dashed border-black pt-1.5">
          <input type="text" value={newTag} onChange={e => setNewTag(e.target.value)}
                 onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); createTag(); } }}
                 placeholder="+ Nueva etiqueta..." className={inputCls} />
          <button type="button" onClick={createTag}
                  className="bg-black text-white border-2 border-black px-3 text-[10px] font-bold uppercase hover:bg-brutalGreen hover:text-black transition-all">+</button>
        </div>
      </Section>

    </div>
  );
}
