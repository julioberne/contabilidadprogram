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

  // 🔍 Buscador de terceros registrados (2026-09-11, pedido de Andrés:
  // "por si el tercero que estamos guardando ya lo tenemos"). Mismo patrón
  // del comprobante: filtro EN MEMORIA sobre allThirdParties (ya se
  // refresca con cada fetchAll) — cero peticiones por tecla. El genérico
  // 999999999 se excluye: elegirlo no identifica a nadie.
  const [tpBusca, setTpBusca] = useState("");
  const normTp = (x) => (x || '').trim().toLowerCase().replace(/\s+/g, ' ');
  const tercerosReg = (d.allThirdParties || []).filter(t => String(t.identification_number) !== '999999999');
  const qTp = tpBusca.trim().toLowerCase();
  const tpFiltrados = qTp ? tercerosReg.filter(t =>
    (t.name || '').toLowerCase().includes(qTp) || String(t.identification_number || '').includes(qTp)) : [];
  const tpVisibles = tpFiltrados.slice(0, 30);
  const elegirTercero = (t) => {
    d.setThirdPartyName(t.name || '');
    d.setThirdPartyType(t.identification_type || 'NIT');
    d.setThirdPartyNumber(String(t.identification_number || ''));
    if (t.email) d.setThirdPartyEmail(t.email);
    if (t.phone) d.setThirdPartyPhone(t.phone);
    setTpBusca('');
  };
  // Semáforo de reutilización: que se VEA si este registro reusa o crea
  const numeroTp = (d.thirdPartyNumber || '').trim();
  const regPorNumero = numeroTp ? tercerosReg.find(t => String(t.identification_number) === numeroTp) : null;
  const regPorNombre = (!numeroTp && d.thirdPartyName.trim())
    ? tercerosReg.find(t => normTp(t.name) === normTp(d.thirdPartyName)) : null;

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
          <label className={labelCls}>🔍 Buscar tercero registrado</label>
          <input type="text" value={tpBusca} onChange={e => setTpBusca(e.target.value)}
                 placeholder="Nombre o número… (elige y llena los campos)" className={inputCls} />
          {qTp && (
            <div className="border-2 border-black border-t-0 bg-white max-h-32 overflow-y-auto">
              {tpVisibles.length === 0 && (
                <p className="px-2 py-1 text-[10px] text-gray-500 uppercase">Sin coincidencias — se creará como nuevo</p>
              )}
              {tpVisibles.map(t => (
                <button type="button" key={t.id} onClick={() => elegirTercero(t)}
                        className="w-full text-left px-2 py-1 text-[10px] font-mono border-b border-gray-200 hover:bg-brutalGreen">
                  <span className="font-bold">{t.name}</span>
                  <span className="text-gray-500"> · {t.identification_type} {t.identification_number}</span>
                </button>
              ))}
              {tpFiltrados.length > 30 && (
                <p className="px-2 py-1 text-[9px] text-gray-500">Mostrando 30 de {tpFiltrados.length} — afina la búsqueda</p>
              )}
            </div>
          )}
        </div>
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
        {regPorNumero && (
          <p className="text-[9px] text-green-700 font-bold uppercase">
            ✓ Registrado: {regPorNumero.name} — se reutilizará, no se duplica
          </p>
        )}
        {regPorNombre && (
          <p className="text-[9px] text-green-700 font-bold uppercase">
            ↻ Ya existe con este nombre ({regPorNombre.identification_type} {regPorNombre.identification_number}) — se reutilizará
          </p>
        )}
        {!numeroTp && d.thirdPartyName.trim() && !regPorNombre && (
          <p className="text-[9px] text-amber-700 uppercase">
            ✳ Tercero nuevo — se creará con número provisional; complétalo luego en el comprobante
          </p>
        )}
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
