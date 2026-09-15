// EvidenceModal.jsx — Extracted from App.jsx (Lines 1696-1976)
// 2026-09-09 (pedido de Andrés): el comprobante es un AUDITOR ACTIVO — los
// datos pendientes que él mismo señala se completan aquí mismo (revincular
// tercero registrado, completar su contacto, pegar la geolocalización).
import React from 'react';
import { API } from '../../config';
import { useEmpresa } from '../engine/EmpresaProvider.jsx';

export default function EvidenceModal({
  evidenceUrl,
  selectedEvidenceTx,
  onClose,
  profile,
}) {
  const { fetchAll, patchTransaction, refreshTerceros } = useEmpresa();
  // Parche local: lo corregido se refleja al instante sin cerrar el modal.
  // Plan A5: el mismo parche se aplica a la fila del diario (patchTransaction)
  // en vez de recargar el dashboard completo tras cada campo.
  const [parche, setParche] = React.useState({});
  const parcharDiario = React.useCallback((campos) => {
    const id = selectedEvidenceTx?.id;
    if (id != null && patchTransaction) patchTransaction(id, campos);
    else fetchAll?.(true);
  }, [selectedEvidenceTx?.id, patchTransaction, fetchAll]);
  const [editTp, setEditTp] = React.useState(false);
  const [terceros, setTerceros] = React.useState(null);
  const [tpSel, setTpSel] = React.useState('');
  const [tpBusca, setTpBusca] = React.useState('');
  const [tpForm, setTpForm] = React.useState({ name: '', phone: '', email: '', address: '',
    identification_type: 'NIT', identification_number: '' });
  const [geoInput, setGeoInput] = React.useState('');
  const [guardando, setGuardando] = React.useState(false);
  // 🏷️ Edición de etiquetas de la TX (fuente: tag_definitions del módulo web)
  const [editTags, setEditTags] = React.useState(false);
  const [tagsDefs, setTagsDefs] = React.useState(null);
  const [tagsSel, setTagsSel] = React.useState([]);
  // 📝 Nota breve del comprobante (opcional, máx. 280)
  const [editNota, setEditNota] = React.useState(false);
  const [notaTxt, setNotaTxt] = React.useState('');
  // 📎 Adjuntar evidencias olvidadas (2026-09-11, pedido de Andrés: "si se
  // me olvida agregar el archivo adjunto ya no se puede"). Mismo camino del
  // formulario: navegador → bucket de Supabase → POST de las URLs.
  const [subiendoEv, setSubiendoEv] = React.useState(false);
  const inputEvRef = React.useRef(null);
  const EVIDENCIA_MAX_MB = 5;
  const adjuntarEvidencias = async (e) => {
    const lista = Array.from(e.target.files || []);
    e.target.value = '';
    if (!lista.length || !txv.id) return;
    setSubiendoEv(true);
    try {
      const { supabase, SUPABASE_URL } = await import('../../project-hub/lib/supabaseClient.js');
      const urls = [];
      for (const file of lista) {
        if (file.size > EVIDENCIA_MAX_MB * 1024 * 1024) {
          alert(`❌ "${file.name}" pesa más de ${EVIDENCIA_MAX_MB}MB — se omite. Comprímelo e inténtalo de nuevo.`);
          continue;
        }
        const seguro = file.name.normalize('NFD').replace(/[̀-ͯ]/g, '')
          .replace(/[^a-zA-Z0-9._-]+/g, '_').slice(-60);
        const ruta = `evidence/${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}_${seguro}`;
        const { error } = await supabase.storage.from('hr-docs')
          .upload(ruta, file, { contentType: file.type || 'application/octet-stream', upsert: false });
        if (error) throw error;
        urls.push(`${SUPABASE_URL}/storage/v1/object/public/hr-docs/${ruta}`);
      }
      if (!urls.length) return;
      const r = await fetch(`${API}/transactions/${txv.id}/evidences`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: urls }),
      });
      if (!r.ok) throw new Error('No se pudo registrar la evidencia en la transacción');
      const data = await r.json();
      const campos = {
        evidences: data.evidences,
        evidence_file_path: txv.evidence_file_path || data.evidences[0],
      };
      setParche(p => ({ ...p, ...campos }));
      parcharDiario(campos);
    } catch (err) {
      alert('❌ ' + (err.message || 'Error adjuntando la evidencia.'));
    } finally {
      setSubiendoEv(false);
    }
  };
  React.useEffect(() => {
    setParche({}); setEditTp(false); setTpSel(''); setTpBusca('');
    setGeoInput(''); setEditTags(false); setEditNota(false);
  }, [selectedEvidenceTx?.id]);

  const txv = { ...(selectedEvidenceTx || {}), ...parche };

  // SOLO el 999999999 es el genérico compartido (jamás se renombra). Un
  // "Sin especificar" con NIT real es un tercero PROPIO mal nombrado: a ese
  // sí se le pone nombre normal (caso ferretería, 2026-09-09 — la 1ª versión
  // intentaba CREAR uno nuevo y chocaba con el número único).
  const esGenerico = String(txv.identification_number) === '999999999';

  const abrirEdicionTp = async () => {
    setEditTp(v => !v);
    setTpForm({
      name: esGenerico ? '' : (txv.third_party_name || ''),
      phone: txv.tp_phone || '', email: txv.tp_email || '', address: txv.tp_address || '',
      identification_type: txv.identification_type || 'NIT',
      identification_number: (txv.identification_number && txv.identification_number !== '999999999')
        ? txv.identification_number : '' });
    // UNA sola petición: el buscador filtra EN MEMORIA (cero requests por
    // tecla — con miles de terceros sigue siendo instantáneo).
    if (terceros === null) {
      try {
        const r = await fetch(`${API}/third-parties`);
        if (r.ok) setTerceros(await r.json());
      } catch { setTerceros([]); }
    }
  };

  const abrirEdicionTags = async () => {
    setEditTags(v => !v);
    setTagsSel([...(txv.tags || [])]);
    if (tagsDefs === null) {
      try {
        const r = await fetch(`${API}/tags`);
        if (r.ok) setTagsDefs(await r.json());
      } catch { setTagsDefs([]); }
    }
  };

  const guardarTags = async () => {
    setGuardando(true);
    try {
      const r = await fetch(`${API}/transactions/${txv.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags: tagsSel }),
      });
      if (!r.ok) throw new Error('No se pudieron guardar las etiquetas');
      setParche(p => ({ ...p, tags: [...tagsSel] }));
      setEditTags(false);
      parcharDiario({ tags: [...tagsSel] });
    } catch (e) {
      alert('❌ ' + (e.message || 'Error guardando.'));
    } finally {
      setGuardando(false);
    }
  };

  const guardarTercero = async () => {
    setGuardando(true);
    // Campos del tercero que cambiaron: se aplican al parche local Y a la
    // fila del diario (plan A5), sin recargar el dashboard.
    let camposTp = null;
    const parchar = (campos) => { camposTp = campos; setParche(p => ({ ...p, ...campos })); };
    try {
      if (tpSel && Number(tpSel) !== txv.third_party_id) {
        // Revincular la transacción a un tercero YA registrado
        const r = await fetch(`${API}/transactions/${txv.id}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ third_party_id: Number(tpSel) }),
        });
        if (!r.ok) throw new Error('No se pudo revincular el tercero');
        const t = (terceros || []).find(x => x.id === Number(tpSel)) || {};
        parchar({ third_party_id: t.id, third_party_name: t.name,
          identification_type: t.identification_type, identification_number: t.identification_number,
          tp_phone: t.phone, tp_email: t.email, tp_address: t.address });
      } else if (esGenerico && (tpForm.name || '').trim()) {
        // El actual es el genérico compartido: se CREA un tercero nuevo con
        // lo escrito y se vincula SOLO esta transacción (renombrar al
        // genérico cambiaría todas las TXs "Sin especificar").
        // Si el número escrito YA pertenece a un tercero registrado, se
        // REUTILIZA ese en vez de chocar con el número único.
        const numero = (tpForm.identification_number || '').trim();
        let nuevo = numero
          ? (terceros || []).find(t => String(t.identification_number) === numero)
          : null;
        if (!nuevo) {
          const rc = await fetch(`${API}/third-parties`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              name: tpForm.name.trim(),
              identification_type: tpForm.identification_type || 'NIT',
              identification_number: numero || `SN-${Date.now().toString(36)}`,
            }),
          });
          if (!rc.ok) {
            const det = await rc.json().catch(() => ({}));
            throw new Error(/unique|duplicate|llave duplicada/i.test(String(det.detail))
              ? 'Ese número ya pertenece a otro tercero — búscalo en la lista de arriba.'
              : 'No se pudo crear el tercero');
          }
          nuevo = await rc.json();
        } else {
          // Reutilizado: actualizar su nombre al escrito
          await fetch(`${API}/third-parties/${nuevo.id}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: tpForm.name.trim() }),
          });
        }
        const contacto = {};
        for (const k of ['phone', 'email', 'address']) {
          if ((tpForm[k] || '').trim()) contacto[k] = tpForm[k].trim();
        }
        if (Object.keys(contacto).length) {
          await fetch(`${API}/third-parties/${nuevo.id}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(contacto),
          });
        }
        const rv = await fetch(`${API}/transactions/${txv.id}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ third_party_id: nuevo.id }),
        });
        if (!rv.ok) throw new Error('Tercero creado pero no se pudo vincular');
        parchar({ third_party_id: nuevo.id, third_party_name: tpForm.name.trim(),
          identification_type: tpForm.identification_type || 'NIT',
          identification_number: (tpForm.identification_number || '').trim() || '999999999',
          tp_phone: contacto.phone, tp_email: contacto.email, tp_address: contacto.address });
      } else if (txv.third_party_id) {
        // Completar NOMBRE, contacto e identificación del tercero actual
        // (módulo de Terceros = fuente de la verdad)
        const cuerpo = {};
        for (const k of ['name', 'phone', 'email', 'address', 'identification_number']) {
          if ((tpForm[k] || '').trim()) cuerpo[k] = tpForm[k].trim();
        }
        if (cuerpo.name && cuerpo.name === (txv.third_party_name || '').trim()) delete cuerpo.name;
        if (cuerpo.identification_number) {
          cuerpo.identification_type = tpForm.identification_type || 'NIT';
        }
        if (Object.keys(cuerpo).length) {
          const r = await fetch(`${API}/third-parties/${txv.third_party_id}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cuerpo),
          });
          if (!r.ok) throw new Error('No se pudo actualizar el tercero');
          parchar({ third_party_name: cuerpo.name ?? txv.third_party_name,
            tp_phone: cuerpo.phone ?? txv.tp_phone,
            tp_email: cuerpo.email ?? txv.tp_email, tp_address: cuerpo.address ?? txv.tp_address,
            identification_number: cuerpo.identification_number ?? txv.identification_number,
            identification_type: cuerpo.identification_type ?? txv.identification_type });
        }
      }
      setEditTp(false);
      // El tercero cambió: la fila del diario y la lista de terceros se
      // actualizan sin recargar el dashboard entero.
      if (camposTp) parcharDiario(camposTp);
      refreshTerceros?.();
    } catch (e) {
      alert('❌ ' + (e.message || 'Error guardando.'));
    } finally {
      setGuardando(false);
    }
  };

  const guardarNota = async () => {
    setGuardando(true);
    try {
      const r = await fetch(`${API}/transactions/${txv.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: notaTxt.trim().slice(0, 280) }),
      });
      if (!r.ok) throw new Error('No se pudo guardar la nota');
      setParche(p => ({ ...p, note: notaTxt.trim().slice(0, 280) }));
      setEditNota(false);
      parcharDiario({ note: notaTxt.trim().slice(0, 280) });
    } catch (e) {
      alert('❌ ' + (e.message || 'Error guardando.'));
    } finally {
      setGuardando(false);
    }
  };

  const guardarGeo = async () => {
    const link = (geoInput || '').trim();
    if (!link) return;
    setGuardando(true);
    try {
      const r = await fetch(`${API}/transactions/${txv.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ geo_maps_link: link }),
      });
      if (!r.ok) throw new Error('No se pudo guardar la ubicación');
      setParche(p => ({ ...p, geo_maps_link: link }));
      setGeoInput('');
      parcharDiario({ geo_maps_link: link });
    } catch (e) {
      alert('❌ ' + (e.message || 'Error guardando.'));
    } finally {
      setGuardando(false);
    }
  };
  // El archivo puede NO existir en este entorno: la BD es compartida
  // local↔prod pero /uploads es disco local de cada uno (2026-09-08).
  // Antes un placeholder negro "EVIDENCIA FÍSICA" tapaba el error.
  const [imgRota, setImgRota] = React.useState({});
  React.useEffect(() => { setImgRota({}); }, [selectedEvidenceTx?.id]);
  // Cerrar con Escape (2026-09-09: el comprobante largo obligaba a hacer
  // zoom-out para alcanzar el botón — ahora hay 3 salidas: botón fijo,
  // Escape y clic fuera del recibo)
  React.useEffect(() => {
    if (!evidenceUrl) return;
    const esc = (e) => { if (e.key === 'Escape') onClose?.(); };
    document.addEventListener('keydown', esc);
    return () => document.removeEventListener('keydown', esc);
  }, [evidenceUrl, onClose]);
  if (!evidenceUrl) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center p-2 z-50"
         onClick={onClose}>
      {/* El recibo NUNCA supera la pantalla: alto máximo 94vh con scroll
          INTERNO — el encabezado con CERRAR queda siempre visible. */}
      <div className="print-area bg-white border-2 border-black p-2 max-w-lg w-full shadow-brutal font-mono flex flex-col max-h-[94vh]"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center border-b-2 border-black pb-1 mb-2 shrink-0">
          <span className="text-sm font-bold uppercase">📂 Visualizador de Evidencia</span>
          <div className="flex gap-1">
            <button
              onClick={() => window.print()}
              title="Imprimir el comprobante (o guardarlo como PDF desde el diálogo)"
              className="bg-black text-white border border-black px-2 py-0.5 font-bold uppercase hover:bg-brutalGreen hover:text-black"
            >
              🖨 Imprimir
            </button>
            <button
              onClick={onClose}
              className="bg-brutalCrimson text-white border border-black px-2 py-0.5 font-bold uppercase hover:bg-black"
            >
              Cerrar [X]
            </button>
          </div>
        </div>

        {selectedEvidenceTx ? (
          <div className="space-y-2 overflow-y-auto flex-1 pr-1">
            {/* Brutalist Simulated Receipt Visualizer */}
            <div className="border-2 border-black p-2 bg-brutalBg text-xs space-y-2 uppercase">
              <div className="text-center font-bold border-b border-black pb-2 text-sm">
                *** CERTIFICADO / RECIBO DE CAJA ***
                <br />
                <span className="text-[11px] font-black uppercase text-blue-600 block mt-1">
                  🏢 EMPRESA: {txv.portfolio_name || "ESTÁNDAR"}
                </span>
                <span className="text-[9px] font-bold text-gray-500 block mb-1">
                  💼 SECTOR: {txv.portfolio_industry || "ESTÁNDAR"}
                  {txv.portfolio_sub_industry ? ` (${txv.portfolio_sub_industry})` : ""}
                </span>
                <span className="text-[9px] text-gray-400 font-normal block">AUDITORÍA ACTIVA SUPABASE POSTGRES</span>
                <span className="text-[10px] bg-black text-white px-2 py-0.5 mt-1.5 inline-block">ID TX: #{txv.id}</span>
              </div>
              
              <div className="grid grid-cols-2 gap-2 border-b border-black pb-2">
                <div>
                  <span className="font-bold text-gray-500 block text-[9px]">TIPO OPERACIÓN:</span>
                  <div className="mt-1">
                    <span className={`px-2 py-0.5 border border-black font-extrabold text-[10px] ${
                      txv.type === "INGRESO" 
                        ? "bg-brutalGreen text-black" 
                        : txv.type === "GASTO" 
                          ? "bg-brutalCrimson text-white" 
                          : "bg-black text-white"
                    }`}>
                      {txv.type}
                    </span>
                  </div>
                </div>
                <div>
                  <span className="font-bold text-gray-500 block text-[9px]">FECHA REGISTRO:</span>
                  <div className="mt-1 font-bold">{txv.transaction_date}</div>
                </div>
              </div>

              <div className="space-y-1.5 border-b border-black pb-2">
                <div className="flex justify-between">
                  <span className="font-bold text-gray-500">CONCEPTO:</span>
                  <span className="font-bold text-right break-all max-w-[200px]">{txv.concept}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-bold text-gray-500">CUENTA COA:</span>
                  <span className="font-bold text-blue-600">{txv.category || "SIN ASIGNAR"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-bold text-gray-500">MEDIO DE PAGO:</span>
                  <span className="font-bold">
                    {txv.type === "TRANSFERENCIA" 
                      ? `${txv.account_name || txv.payment_method || "EFECTIVO"} ➜ ${txv.dest_account_name || "?"}`
                      : (txv.account_name || txv.payment_method || "EFECTIVO")
                    }
                  </span>
                </div>
              </div>

              <div className="space-y-1.5 border-b border-black pb-2">
                <div className="flex justify-between text-[11px]">
                  <span className="font-bold text-gray-500">PERSONA (TERCERO):</span>
                  <span className="font-bold text-right">
                    {txv.third_party_name || "N/A"}
                    <button onClick={abrirEdicionTp} title="Completar datos o vincular otro tercero registrado"
                            className="ml-1.5 px-1 border border-black bg-white text-black text-[9px] font-bold hover:bg-black hover:text-white">✎</button>
                  </span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="font-bold text-gray-500">IDENTIFICACIÓN:</span>
                  <span className="font-bold">
                    {txv.identification_type || "CC"}: {txv.identification_number || "N/A"}
                  </span>
                </div>
                {(txv.tp_phone || txv.tp_email || txv.tp_address) && (
                  <div className="text-[10px] font-normal normal-case text-gray-600 text-right leading-snug">
                    {txv.tp_phone && <span>📞 {txv.tp_phone} </span>}
                    {txv.tp_email && <span>· ✉ {txv.tp_email} </span>}
                    {txv.tp_address && <div>🏠 {txv.tp_address}</div>}
                  </div>
                )}
                {editTp && (() => {
                  const q = tpBusca.trim().toLowerCase();
                  const filtrados = (terceros || []).filter(t => !q
                    || (t.name || '').toLowerCase().includes(q)
                    || String(t.identification_number || '').includes(q));
                  const visibles = filtrados.slice(0, 30);
                  return (
                  <div className="border-2 border-dashed border-black bg-yellow-50 p-2 space-y-1 normal-case">
                    <div className="text-[9px] font-bold uppercase">Vincular a un tercero YA registrado:</div>
                    <input value={tpBusca} onChange={e => { setTpBusca(e.target.value); setTpSel(''); }}
                           placeholder="🔍 Buscar por nombre o número… (filtra al instante, sin peticiones)"
                           className="w-full border border-black px-1 py-0.5 text-[10px] bg-white" />
                    <select value={tpSel} onChange={e => setTpSel(e.target.value)} size={Math.min(Math.max(visibles.length + 1, 2), 5)}
                            className="w-full border border-black px-1 py-0.5 text-[10px] bg-white">
                      <option value="">— mantener el actual —</option>
                      {visibles.map(t => (
                        <option key={t.id} value={t.id}>
                          {t.name} ({t.identification_type} {t.identification_number})
                        </option>
                      ))}
                    </select>
                    {filtrados.length > 30 && (
                      <div className="text-[8px] text-gray-500">Mostrando 30 de {filtrados.length} — afina la búsqueda</div>
                    )}
                    {!tpSel && (
                      <>
                        <div className="text-[9px] font-bold uppercase pt-1">…o completar datos del actual:</div>
                        {esGenerico && (
                          <div className="text-[8px] text-amber-700 leading-snug">
                            El actual es "Sin especificar" (genérico compartido): al guardar con
                            nombre se creará un tercero NUEVO solo para esta transacción.
                          </div>
                        )}
                        <div className="grid grid-cols-3 gap-1">
                          <input value={tpForm.name} onChange={e => setTpForm(f => ({ ...f, name: e.target.value }))}
                                 placeholder="Nombre / Razón Social" className="col-span-3 border border-black px-1 py-0.5 text-[10px]" />
                          <select value={tpForm.identification_type}
                                  onChange={e => setTpForm(f => ({ ...f, identification_type: e.target.value }))}
                                  className="border border-black px-1 py-0.5 text-[10px] bg-white">
                            <option value="NIT">NIT</option>
                            <option value="CC">CC</option>
                          </select>
                          <input value={tpForm.identification_number}
                                 onChange={e => setTpForm(f => ({ ...f, identification_number: e.target.value }))}
                                 placeholder="Nº identificación" className="col-span-2 border border-black px-1 py-0.5 text-[10px]" />
                          <input value={tpForm.phone} onChange={e => setTpForm(f => ({ ...f, phone: e.target.value }))}
                                 placeholder="Teléfono" className="border border-black px-1 py-0.5 text-[10px]" />
                          <input value={tpForm.email} onChange={e => setTpForm(f => ({ ...f, email: e.target.value }))}
                                 placeholder="Correo" className="col-span-2 border border-black px-1 py-0.5 text-[10px]" />
                          <input value={tpForm.address} onChange={e => setTpForm(f => ({ ...f, address: e.target.value }))}
                                 placeholder="Dirección" className="col-span-3 border border-black px-1 py-0.5 text-[10px]" />
                        </div>
                      </>
                    )}
                    <div className="flex gap-1 pt-1">
                      <button onClick={guardarTercero} disabled={guardando}
                              className="flex-1 bg-black text-white border border-black py-0.5 text-[9px] font-bold uppercase hover:bg-brutalGreen hover:text-black disabled:opacity-40">
                        {guardando ? 'Guardando…' : '💾 Guardar'}
                      </button>
                      <button onClick={() => setEditTp(false)}
                              className="px-2 border border-black bg-white text-[9px] font-bold uppercase hover:bg-black hover:text-white">✕</button>
                    </div>
                  </div>
                  );
                })()}
              </div>

              <div className="space-y-1 border-b border-black pb-2">
                <div className="flex justify-between">
                  <span className="font-bold text-gray-500">VALOR BASE:</span>
                  <span className="font-bold">
                    ${Number(txv.amount || 0).toLocaleString('es-CO', { minimumFractionDigits: 2 })} {txv.transaction_currency || "COP"}
                  </span>
                </div>
                
                {txv.trm && Number(txv.trm) !== 1 && (
                  <div className="flex justify-between text-gray-500 text-[10px]">
                    <span>TASA DE CAMBIO (TRM):</span>
                    <span>1 USD = ${Number(txv.trm).toLocaleString('es-CO', { minimumFractionDigits: 2 })} COP</span>
                  </div>
                )}

                {txv.tax_iva_amount > 0 && (
                  <div className="flex justify-between text-gray-500">
                    <span>+ IVA (19%):</span>
                    <span>${Number(txv.tax_iva_amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                  </div>
                )}

                {txv.tax_gmf_amount > 0 && (
                  <div className="flex justify-between text-gray-500">
                    <span>+ GMF (4X1000):</span>
                    <span>${Number(txv.tax_gmf_amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                  </div>
                )}

                {txv.custom_tax_amount > 0 && (
                  <div className="flex justify-between text-gray-500">
                    <span>+ IMPUESTOS ADICIONALES:</span>
                    <span>${Number(txv.custom_tax_amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                  </div>
                )}

                <div className="flex justify-between border-t border-black pt-1 text-[13px] font-black bg-yellow-100 p-1 mt-1">
                  <span>VALOR NETO:</span>
                  <span>
                    ${Number(txv.net_value || 0).toLocaleString('es-CO', { minimumFractionDigits: 2 })} {txv.transaction_currency || "COP"}
                  </span>
                </div>
              </div>

              {/* CXC / CXP Link Details */}
              {txv.cxc_type && (
                <div className="border-b border-black pb-2 space-y-1">
                  <span className="font-bold text-gray-500 block text-[9px]">GESTIONADO EN CARTERA ({txv.cxc_type}):</span>
                  <div className="bg-black text-white p-1.5 font-mono text-[9px] flex justify-between items-center uppercase">
                    <span>VENCE: {txv.cxc_due_date}</span>
                    <span>PLAZO: {txv.cxc_term}</span>
                    <span className="bg-brutalAmber text-black px-1 font-extrabold">{txv.cxc_status || "PENDIENTE"}</span>
                  </div>
                </div>
              )}

              {/* Capitalized Asset Link Details */}
              {txv.asset_name && (
                <div className="border-b border-black pb-2 space-y-1">
                  <span className="font-bold text-gray-500 block text-[9px]">ACTIVO CAPITALIZADO EN GESTIÓN:</span>
                  <div className="bg-blue-50 border border-blue-500 text-blue-900 p-2 font-mono text-[9px] uppercase space-y-1">
                    <div className="flex justify-between font-extrabold">
                      <span>ACTIVO: {txv.asset_name}</span>
                      <span>TAG: {txv.asset_tag || "GENERAL"}</span>
                    </div>
                    {txv.asset_is_passive && (
                      <div className="text-[8px] text-blue-700 font-extrabold leading-tight">
                        🔁 ACTIVO GENERADOR DE RENTAS RECURRENTES:
                        <br />
                        ${Number(txv.amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })} COP / CADA {txv.recurrence_days || 30} DÍAS
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Etiquetas asignadas — editables desde el comprobante (2026-09-09) */}
              <div className="border-b border-black pb-2">
                <span className="font-bold text-gray-500 block text-[9px] mb-1">
                  🏷️ ETIQUETAS:
                  <button onClick={abrirEdicionTags} title="Poner o quitar etiquetas de esta transacción"
                          className="ml-1.5 px-1 border border-black bg-white text-black text-[9px] font-bold hover:bg-black hover:text-white">✎</button>
                </span>
                <div className="flex flex-wrap gap-1">
                  {(txv.tags || []).map(tag => (
                    <span key={tag} className="bg-black text-white px-1.5 py-0.5 text-[9px] font-bold uppercase border border-black">{tag}</span>
                  ))}
                  {!(txv.tags || []).length && <span className="text-[9px] text-gray-400">— sin etiquetas —</span>}
                </div>
                {editTags && (
                  <div className="border-2 border-dashed border-black bg-yellow-50 p-2 mt-1 space-y-1 normal-case">
                    <div className="text-[9px] font-bold uppercase">Toca para poner/quitar (módulo 🏷️ = fuente):</div>
                    <div className="flex flex-wrap gap-1">
                      {(tagsDefs || []).map(t => {
                        const nombre = String(t.name || '').trim();
                        const puesta = tagsSel.includes(nombre);
                        return (
                          <button key={t.id}
                                  onClick={() => setTagsSel(s => puesta ? s.filter(x => x !== nombre) : [...s, nombre])}
                                  className={`px-1.5 py-0.5 text-[9px] font-bold uppercase border border-black ${puesta ? 'bg-black text-white' : 'bg-white text-black hover:bg-brutalNeutral'}`}>
                            {puesta ? '✓ ' : ''}{nombre}
                          </button>
                        );
                      })}
                      {tagsDefs !== null && !tagsDefs.length && (
                        <span className="text-[9px] text-gray-500">No hay etiquetas creadas — créalas en el módulo 🏷️ TAGS.</span>
                      )}
                    </div>
                    <div className="flex gap-1 pt-1">
                      <button onClick={guardarTags} disabled={guardando}
                              className="flex-1 bg-black text-white border border-black py-0.5 text-[9px] font-bold uppercase hover:bg-brutalGreen hover:text-black disabled:opacity-40">
                        {guardando ? 'Guardando…' : '💾 Guardar etiquetas'}
                      </button>
                      <button onClick={() => setEditTags(false)}
                              className="px-2 border border-black bg-white text-[9px] font-bold uppercase hover:bg-black hover:text-white">✕</button>
                    </div>
                  </div>
                )}
              </div>

              {/* 📝 Nota breve del comprobante (opcional, máx. 280) */}
              <div className="border-b border-black pb-2">
                <span className="font-bold text-gray-500 block text-[9px] mb-1">
                  📝 NOTA:
                  <button onClick={() => { setEditNota(v => !v); setNotaTxt(txv.note || ''); }}
                          title="Escribir o editar una breve descripción (opcional)"
                          className="ml-1.5 px-1 border border-black bg-white text-black text-[9px] font-bold hover:bg-black hover:text-white">✎</button>
                </span>
                {!editNota && (
                  txv.note
                    ? <div className="text-[10px] normal-case leading-snug whitespace-pre-wrap">{txv.note}</div>
                    : <span className="text-[9px] text-gray-400">— sin nota —</span>
                )}
                {editNota && (
                  <div className="border-2 border-dashed border-black bg-yellow-50 p-2 space-y-1 normal-case">
                    <textarea value={notaTxt} maxLength={280} rows={3}
                              onChange={e => setNotaTxt(e.target.value)}
                              placeholder="Breve descripción u observación (opcional)…"
                              className="w-full border border-black px-1 py-0.5 text-[10px] bg-white resize-none" />
                    <div className="flex items-center gap-1">
                      <button onClick={guardarNota} disabled={guardando}
                              className="flex-1 bg-black text-white border border-black py-0.5 text-[9px] font-bold uppercase hover:bg-brutalGreen hover:text-black disabled:opacity-40">
                        {guardando ? 'Guardando…' : '💾 Guardar nota'}
                      </button>
                      <button onClick={() => setEditNota(false)}
                              className="px-2 border border-black bg-white text-[9px] font-bold uppercase hover:bg-black hover:text-white">✕</button>
                      <span className="text-[8px] text-gray-500">{notaTxt.length}/280</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Auditor / Issuer Information */}
              <div className="border-b border-black pb-2 flex justify-between text-[10px] font-bold uppercase">
                <span className="text-gray-500">AUDITOR FIRMANTE:</span>
                <span>{profile?.name || "ANDRÉS"} ({profile?.role || "ADMINISTRADOR CONTABLE"})</span>
              </div>

              <div className="text-[10px] space-y-1">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-gray-500">GEOLOCALIZACIÓN:</span>
                  {txv.geo_maps_link ? (
                    <a
                      href={txv.geo_maps_link}
                      target="_blank"
                      rel="noreferrer"
                      className="bg-black text-white px-2 py-0.5 border border-black hover:bg-brutalGreen hover:text-black font-bold uppercase transition-all"
                    >
                      [VER EN MAPAS]
                    </a>
                  ) : (
                    <span className="text-gray-400 font-bold">SIN COORDENADAS</span>
                  )}
                </div>
                {!txv.geo_maps_link && (
                  <div className="flex gap-1 normal-case">
                    <input value={geoInput} onChange={e => setGeoInput(e.target.value)}
                           placeholder="Pega aquí el link de Google Maps…"
                           className="flex-1 border border-black px-1 py-0.5 text-[10px] bg-white" />
                    <button onClick={guardarGeo} disabled={guardando || !geoInput.trim()}
                            className="px-2 border border-black bg-black text-white text-[9px] font-bold uppercase hover:bg-brutalGreen hover:text-black disabled:opacity-40">💾</button>
                  </div>
                )}
              </div>
            </div>

            {/* Sección de Auditoría / Advertencias */}
            <div className="border-2 border-black p-2 bg-white space-y-1 uppercase text-[10px]">
              <div className="font-bold border-b border-black pb-1 text-gray-600">
                🔍 CONTROL INTERNO Y AUDITORÍA DE SOPORTES
              </div>
              
              {(() => {
                const nameUpper = (txv.third_party_name || "").toUpperCase().trim();
                const warnings = [];
                if (!txv.third_party_name || ["VARIOS", "N/A", "SD", "S/D", "GENERICO", "GENÉRICO", "VARIOS EMPLEADOS"].includes(nameUpper) || txv.third_party_name.length < 3) {
                  warnings.push("Tercero / Persona es genérico o no está plenamente identificado.");
                }
                const idStr = (txv.identification_number || "").toString().trim();
                if (!idStr || idStr === "0" || idStr === "999999999" || idStr.toLowerCase() === "n/a") {
                  warnings.push("Número de identificación (NIT/CC) inválido o faltante.");
                }
                if (!txv.evidence_file_path) {
                  warnings.push("Falta archivo digital o soporte de factura adjunto.");
                }
                if (!txv.geo_maps_link) {
                  warnings.push("Falta registro de geolocalización de la operación.");
                }
                if (!txv.category || txv.category === "-") {
                  warnings.push("No se ha asignado una categoría o cuenta COA válida.");
                }

                if (warnings.length > 0) {
                  return (
                     <div className="space-y-2">
                       <div className="bg-brutalCrimson text-white px-2 py-1 font-bold flex items-center gap-1 border border-black">
                         <span>⚠️ COMPROBANTE CON INCONSISTENCIAS ({warnings.length} OBS.)</span>
                       </div>
                       <ul className="list-disc pl-4 space-y-1 font-mono text-[9px] text-red-600">
                         {warnings.map((w, idx) => (
                           <li key={idx} className="font-bold">{w}</li>
                         ))}
                       </ul>
                     </div>
                  );
                } else {
                  return (
                    <div className="bg-brutalGreen text-black px-2 py-1.5 font-bold flex items-center gap-1 border border-black">
                      <span>✅ COMPROBANTE COMPLETADO SIN OBSERVACIONES</span>
                    </div>
                  );
                }
              })()}
            </div>

            {/* Evidencias físicas (Etapa E.3: pueden ser VARIAS — fotos y PDF).
                2026-09-11: la sección se muestra SIEMPRE — con 📎 para
                adjuntar lo que se olvidó al registrar. */}
            {(() => {
              const lista = (txv.evidences?.length
                ? txv.evidences
                : [txv.evidence_file_path])
                .filter(f => f && f !== "recibo_demo.png");
              const urlDe = (f) => (f.startsWith("http") ? f : `/${f}`);
              const esPdf = (f) => f.toLowerCase().split("?")[0].endsWith(".pdf");
              const esAudio = (f) => /\.(ogg|webm|mp3|opus)(\?|$)/i.test(f);
              return (
              <div className="border-2 border-black p-2 bg-white space-y-1 uppercase text-[10px]">
                <div className="font-bold border-b border-black pb-1 flex justify-between items-center">
                  <span>📂 {lista.length > 1 ? `${lista.length} ARCHIVOS DE SOPORTE ADJUNTOS` : "ARCHIVO DE SOPORTE ADJUNTO"}</span>
                  <span>
                    <input ref={inputEvRef} type="file" multiple accept="image/*,application/pdf"
                           className="hidden" onChange={adjuntarEvidencias} />
                    <button onClick={() => inputEvRef.current?.click()} disabled={subiendoEv}
                            title="Adjuntar fotos o PDF a este comprobante (se puede más de uno)"
                            className="px-1.5 py-0.5 border border-black bg-white text-black text-[9px] font-bold hover:bg-black hover:text-white disabled:opacity-40">
                      {subiendoEv ? 'SUBIENDO…' : '📎 ADJUNTAR'}
                    </button>
                  </span>
                </div>
                {lista.length === 0 && (
                  <p className="text-[9px] text-gray-400 normal-case py-1">
                    — Sin soporte adjunto — usa 📎 para agregar fotos o PDF ahora.
                  </p>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {lista.map((f, i) => (
                    <div key={i} className="flex flex-col items-center justify-center p-2 bg-gray-50 border border-black">
                      {esPdf(f) ? (
                        <div className="text-3xl mb-1" title="Documento PDF">📄</div>
                      ) : esAudio(f) ? (
                        <audio controls src={urlDe(f)} className="w-full mb-1" />
                      ) : imgRota[i] ? (
                        <div className="w-full border-2 border-brutalCrimson bg-red-50 p-2 mb-1 text-center normal-case">
                          <div className="font-bold text-red-700 text-[10px] uppercase">⚠ No disponible en este entorno</div>
                          <div className="text-[8px] text-red-700 font-mono mt-1 leading-snug">
                            Quedó en el disco del computador donde se subió (los archivos de <b>/uploads</b> no se comparten). Re-adjúntalo si lo necesitas aquí.
                          </div>
                        </div>
                      ) : (
                        <img src={urlDe(f)} alt={`Respaldo ${i + 1}`}
                             className="max-h-40 object-contain border border-black shadow-brutal mb-1"
                             onError={() => setImgRota(r => ({ ...r, [i]: true }))} />
                      )}
                      <a href={urlDe(f)} target="_blank" rel="noreferrer"
                         className="bg-black text-white text-[9px] font-bold px-2 py-1 hover:bg-brutalGreen hover:text-black border border-black transition-all">
                        ABRIR {lista.length > 1 ? `#${i + 1}` : "ARCHIVO"} EN PESTAÑA NUEVA
                      </a>
                    </div>
                  ))}
                </div>
              </div>
              );
            })()}
          </div>
        ) : (
          <div className="text-center font-bold py-4">No se han cargado detalles del comprobante.</div>
        )}
      </div>
    </div>
  );
}
