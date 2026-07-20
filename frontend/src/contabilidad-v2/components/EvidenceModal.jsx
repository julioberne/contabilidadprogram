// EvidenceModal.jsx — Extracted from App.jsx (Lines 1696-1976)
import React from 'react';

export default function EvidenceModal({
  evidenceUrl,
  selectedEvidenceTx,
  onClose,
  profile,
}) {
  if (!evidenceUrl) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center p-2 z-50 overflow-y-auto">
      <div className="bg-white border-2 border-black p-2 max-w-lg w-full shadow-brutal my-8 font-mono">
        <div className="flex justify-between items-center border-b-2 border-black pb-1 mb-2">
          <span className="text-sm font-bold uppercase">📂 Visualizador de Evidencia</span>
          <button 
            onClick={onClose}
            className="bg-brutalCrimson text-white border border-black px-2 py-0.5 font-bold uppercase hover:bg-black"
          >
            Cerrar [X]
          </button>
        </div>
        
        {selectedEvidenceTx ? (
          <div className="space-y-2">
            {/* Brutalist Simulated Receipt Visualizer */}
            <div className="border-2 border-black p-2 bg-brutalBg text-xs space-y-2 uppercase">
              <div className="text-center font-bold border-b border-black pb-2 text-sm">
                *** CERTIFICADO / RECIBO DE CAJA ***
                <br />
                <span className="text-[11px] font-black uppercase text-blue-600 block mt-1">
                  🏢 EMPRESA: {selectedEvidenceTx.portfolio_name || "ESTÁNDAR"}
                </span>
                <span className="text-[9px] font-bold text-gray-500 block mb-1">
                  💼 SECTOR: {selectedEvidenceTx.portfolio_industry || "ESTÁNDAR"}
                  {selectedEvidenceTx.portfolio_sub_industry ? ` (${selectedEvidenceTx.portfolio_sub_industry})` : ""}
                </span>
                <span className="text-[9px] text-gray-400 font-normal block">AUDITORÍA ACTIVA SUPABASE POSTGRES</span>
                <span className="text-[10px] bg-black text-white px-2 py-0.5 mt-1.5 inline-block">ID TX: #{selectedEvidenceTx.id}</span>
              </div>
              
              <div className="grid grid-cols-2 gap-2 border-b border-black pb-2">
                <div>
                  <span className="font-bold text-gray-500 block text-[9px]">TIPO OPERACIÓN:</span>
                  <div className="mt-1">
                    <span className={`px-2 py-0.5 border border-black font-extrabold text-[10px] ${
                      selectedEvidenceTx.type === "INGRESO" 
                        ? "bg-brutalGreen text-black" 
                        : selectedEvidenceTx.type === "GASTO" 
                          ? "bg-brutalCrimson text-white" 
                          : "bg-black text-white"
                    }`}>
                      {selectedEvidenceTx.type}
                    </span>
                  </div>
                </div>
                <div>
                  <span className="font-bold text-gray-500 block text-[9px]">FECHA REGISTRO:</span>
                  <div className="mt-1 font-bold">{selectedEvidenceTx.transaction_date}</div>
                </div>
              </div>

              <div className="space-y-1.5 border-b border-black pb-2">
                <div className="flex justify-between">
                  <span className="font-bold text-gray-500">CONCEPTO:</span>
                  <span className="font-bold text-right break-all max-w-[200px]">{selectedEvidenceTx.concept}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-bold text-gray-500">CUENTA COA:</span>
                  <span className="font-bold text-blue-600">{selectedEvidenceTx.category || "SIN ASIGNAR"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-bold text-gray-500">MEDIO DE PAGO:</span>
                  <span className="font-bold">
                    {selectedEvidenceTx.type === "TRANSFERENCIA" 
                      ? `${selectedEvidenceTx.account_name || selectedEvidenceTx.payment_method || "EFECTIVO"} ➜ ${selectedEvidenceTx.dest_account_name || "?"}`
                      : (selectedEvidenceTx.account_name || selectedEvidenceTx.payment_method || "EFECTIVO")
                    }
                  </span>
                </div>
              </div>

              <div className="space-y-1.5 border-b border-black pb-2">
                <div className="flex justify-between text-[11px]">
                  <span className="font-bold text-gray-500">PERSONA (TERCERO):</span>
                  <span className="font-bold text-right">{selectedEvidenceTx.third_party_name || "N/A"}</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="font-bold text-gray-500">IDENTIFICACIÓN:</span>
                  <span className="font-bold">
                    {selectedEvidenceTx.identification_type || "CC"}: {selectedEvidenceTx.identification_number || "N/A"}
                  </span>
                </div>
              </div>

              <div className="space-y-1 border-b border-black pb-2">
                <div className="flex justify-between">
                  <span className="font-bold text-gray-500">VALOR BASE:</span>
                  <span className="font-bold">
                    ${Number(selectedEvidenceTx.amount || 0).toLocaleString('es-CO', { minimumFractionDigits: 2 })} {selectedEvidenceTx.transaction_currency || "COP"}
                  </span>
                </div>
                
                {selectedEvidenceTx.trm && Number(selectedEvidenceTx.trm) !== 1 && (
                  <div className="flex justify-between text-gray-500 text-[10px]">
                    <span>TASA DE CAMBIO (TRM):</span>
                    <span>1 USD = ${Number(selectedEvidenceTx.trm).toLocaleString('es-CO', { minimumFractionDigits: 2 })} COP</span>
                  </div>
                )}

                {selectedEvidenceTx.tax_iva_amount > 0 && (
                  <div className="flex justify-between text-gray-500">
                    <span>+ IVA (19%):</span>
                    <span>${Number(selectedEvidenceTx.tax_iva_amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                  </div>
                )}

                {selectedEvidenceTx.tax_gmf_amount > 0 && (
                  <div className="flex justify-between text-gray-500">
                    <span>+ GMF (4X1000):</span>
                    <span>${Number(selectedEvidenceTx.tax_gmf_amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                  </div>
                )}

                {selectedEvidenceTx.custom_tax_amount > 0 && (
                  <div className="flex justify-between text-gray-500">
                    <span>+ IMPUESTOS ADICIONALES:</span>
                    <span>${Number(selectedEvidenceTx.custom_tax_amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })}</span>
                  </div>
                )}

                <div className="flex justify-between border-t border-black pt-1 text-[13px] font-black bg-yellow-100 p-1 mt-1">
                  <span>VALOR NETO:</span>
                  <span>
                    ${Number(selectedEvidenceTx.net_value || 0).toLocaleString('es-CO', { minimumFractionDigits: 2 })} {selectedEvidenceTx.transaction_currency || "COP"}
                  </span>
                </div>
              </div>

              {/* CXC / CXP Link Details */}
              {selectedEvidenceTx.cxc_type && (
                <div className="border-b border-black pb-2 space-y-1">
                  <span className="font-bold text-gray-500 block text-[9px]">GESTIONADO EN CARTERA ({selectedEvidenceTx.cxc_type}):</span>
                  <div className="bg-black text-white p-1.5 font-mono text-[9px] flex justify-between items-center uppercase">
                    <span>VENCE: {selectedEvidenceTx.cxc_due_date}</span>
                    <span>PLAZO: {selectedEvidenceTx.cxc_term}</span>
                    <span className="bg-brutalAmber text-black px-1 font-extrabold">{selectedEvidenceTx.cxc_status || "PENDIENTE"}</span>
                  </div>
                </div>
              )}

              {/* Capitalized Asset Link Details */}
              {selectedEvidenceTx.asset_name && (
                <div className="border-b border-black pb-2 space-y-1">
                  <span className="font-bold text-gray-500 block text-[9px]">ACTIVO CAPITALIZADO EN GESTIÓN:</span>
                  <div className="bg-blue-50 border border-blue-500 text-blue-900 p-2 font-mono text-[9px] uppercase space-y-1">
                    <div className="flex justify-between font-extrabold">
                      <span>ACTIVO: {selectedEvidenceTx.asset_name}</span>
                      <span>TAG: {selectedEvidenceTx.asset_tag || "GENERAL"}</span>
                    </div>
                    {selectedEvidenceTx.asset_is_passive && (
                      <div className="text-[8px] text-blue-700 font-extrabold leading-tight">
                        🔁 ACTIVO GENERADOR DE RENTAS RECURRENTES:
                        <br />
                        ${Number(selectedEvidenceTx.amount).toLocaleString('es-CO', { minimumFractionDigits: 2 })} COP / CADA {selectedEvidenceTx.recurrence_days || 30} DÍAS
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Auditor / Issuer Information */}
              <div className="border-b border-black pb-2 flex justify-between text-[10px] font-bold uppercase">
                <span className="text-gray-500">AUDITOR FIRMANTE:</span>
                <span>{profile?.name || "ANDRÉS"} ({profile?.role || "ADMINISTRADOR CONTABLE"})</span>
              </div>

              <div className="flex justify-between text-[10px] items-center">
                <span className="font-bold text-gray-500">GEOLOCALIZACIÓN:</span>
                {selectedEvidenceTx.geo_maps_link ? (
                  <a 
                    href={selectedEvidenceTx.geo_maps_link} 
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
            </div>

            {/* Sección de Auditoría / Advertencias */}
            <div className="border-2 border-black p-2 bg-white space-y-1 uppercase text-[10px]">
              <div className="font-bold border-b border-black pb-1 text-gray-600">
                🔍 CONTROL INTERNO Y AUDITORÍA DE SOPORTES
              </div>
              
              {(() => {
                const nameUpper = (selectedEvidenceTx.third_party_name || "").toUpperCase().trim();
                const warnings = [];
                if (!selectedEvidenceTx.third_party_name || ["VARIOS", "N/A", "SD", "S/D", "GENERICO", "GENÉRICO", "VARIOS EMPLEADOS"].includes(nameUpper) || selectedEvidenceTx.third_party_name.length < 3) {
                  warnings.push("Tercero / Persona es genérico o no está plenamente identificado.");
                }
                const idStr = (selectedEvidenceTx.identification_number || "").toString().trim();
                if (!idStr || idStr === "0" || idStr === "999999999" || idStr.toLowerCase() === "n/a") {
                  warnings.push("Número de identificación (NIT/CC) inválido o faltante.");
                }
                if (!selectedEvidenceTx.evidence_file_path) {
                  warnings.push("Falta archivo digital o soporte de factura adjunto.");
                }
                if (!selectedEvidenceTx.geo_maps_link) {
                  warnings.push("Falta registro de geolocalización de la operación.");
                }
                if (!selectedEvidenceTx.category || selectedEvidenceTx.category === "-") {
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

            {/* Evidencia física real (si existe) */}
            {selectedEvidenceTx.evidence_file_path && selectedEvidenceTx.evidence_file_path !== "recibo_demo.png" && (
              <div className="border-2 border-black p-2 bg-white space-y-1 uppercase text-[10px]">
                <div className="font-bold border-b border-black pb-1">
                  📂 ARCHIVO DE SOPORTE ADJUNTO
                </div>
                <div className="flex flex-col items-center justify-center p-2 bg-gray-50 border border-black">
                  <img 
                    src={
                      selectedEvidenceTx.evidence_file_path.startsWith("http")
                        ? selectedEvidenceTx.evidence_file_path
                        : `/${selectedEvidenceTx.evidence_file_path}`
                    } 
                    alt="Respaldo Físico" 
                    className="max-h-40 object-contain border border-black shadow-brutal mb-2"
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = "https://placehold.co/400x200/000000/ffffff?text=EVIDENCIA+F%C3%8DSICA";
                    }}
                  />
                  <a
                    href={
                      selectedEvidenceTx.evidence_file_path.startsWith("http")
                        ? selectedEvidenceTx.evidence_file_path
                        : `/${selectedEvidenceTx.evidence_file_path}`
                    }
                    target="_blank"
                    rel="noreferrer"
                    className="bg-black text-white text-[9px] font-bold px-2 py-1 hover:bg-brutalGreen hover:text-black border border-black transition-all"
                  >
                    ABRIR ARCHIVO EN PESTAÑA NUEVA
                  </a>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center font-bold py-4">No se han cargado detalles del comprobante.</div>
        )}
      </div>
    </div>
  );
}
