// LibroDiario.jsx — Extracted from App.jsx (Lines 1273-1692)
import React from 'react';

export default function LibroDiario({
  transactions,
  totalTxCount,
  loadingMore,
  loadMoreTransactions,
  expandedTxId, setExpandedTxId,
  editingCell, setEditingCell,
  editValue, setEditValue,
  saveInlineEdit,
  toggleRecurrence,
  accounts,
  coaFlatAccounts,
  onEvidenceClick,
}) {
  const startEditing = (txId, field, currentValue) => {
    setEditingCell({ txId, field });
    setEditValue(currentValue !== null && currentValue !== undefined ? String(currentValue) : "");
  };

  return (
        <div className="w-full">
          <div className="bg-white border-2 border-black p-2 shadow-brutal overflow-hidden flex flex-col">
            <h2 className="text-sm font-bold uppercase border-b-2 border-black pb-1 mb-2">📖 Módulo 02: Libro Diario Inteligente</h2>
            
            {/* Rejilla de Movimientos Históricos */}
            <div className="overflow-x-auto">
              <table className="w-full border-2 border-black text-left text-xs">
                <thead className="bg-black text-white uppercase font-bold">
                  <tr>
                    <th className="p-2 border-r border-black">Tipo</th>
                    <th className="p-2 border-r border-black">Valor Neto</th>
                    <th className="p-2 border-r border-black">Concepto</th>
                    <th className="p-2 border-r border-black">Cuenta COA</th>
                    <th className="p-2 border-r border-black">Tercero NIT/CC</th>
                    <th className="p-2 border-r border-black">Fecha</th>
                    <th className="p-2 border-r border-black">Cuenta</th>
                    <th className="p-2 border-r border-black">Lugar</th>
                    <th className="p-2">Evidencia</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-black bg-white">
                  {transactions.length === 0 ? (
                    <tr>
                      <td colSpan="9" className="p-8 text-center uppercase text-gray-400 font-bold">
                        No hay registros en este portafolio. Agrega uno manual o habla por micrófono.
                      </td>
                    </tr>
                  ) : (
                    transactions.map((tx) => (
                      <React.Fragment key={tx.id}>
                      <tr 
                        className={`hover:bg-brutalBg transition-all cursor-pointer ${expandedTxId === tx.id ? 'bg-brutalBg' : ''}`} 
                        title="Click para ver detalles · Doble clic en celda para editar"
                        onClick={() => setExpandedTxId(expandedTxId === tx.id ? null : tx.id)}
                      >
                        {/* Tipo */}
                        <td className="p-2 border-r border-black font-bold">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "type" ? (
                            <select
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "type")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "type");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="bg-white border border-black p-0.5 text-xs font-mono outline-none"
                              autoFocus
                            >
                              <option value="INGRESO">INGRESO</option>
                              <option value="GASTO">GASTO</option>
                              <option value="TRANSFERENCIA">TRANSFERENCIA</option>
                            </select>
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "type", tx.type)} 
                              className={`px-2 py-0.5 border border-black uppercase text-[10px] font-bold cursor-pointer ${
                                tx.type === "INGRESO" ? "bg-brutalGreen text-black" : tx.type === "GASTO" ? "bg-brutalCrimson text-white" : "bg-black text-white"
                              }`}
                            >
                              {tx.type.substring(0, 3)}
                            </span>
                          )}
                        </td>

                        {/* Valor Neto */}
                        <td className="p-2 border-r border-black font-bold text-right uppercase">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "net_value" ? (
                            <input
                              type="number"
                              step="0.01"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "net_value")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "net_value");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="w-24 bg-white border border-black p-0.5 text-xs font-mono outline-none text-right"
                              autoFocus
                            />
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "net_value", tx.net_value)} 
                              className="cursor-pointer block w-full h-full font-mono text-[11px]"
                            >
                              {tx.transaction_currency === "USD" ? "$" : "$"}
                              {tx.net_value.toLocaleString('es-CO', { minimumFractionDigits: 2 })} {tx.transaction_currency || "COP"}
                            </span>
                          )}
                        </td>

                        {/* Concepto */}
                        <td className="p-2 border-r border-black font-bold uppercase max-w-[150px] truncate">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "concept" ? (
                            <input
                              type="text"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "concept")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "concept");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="w-full bg-white border border-black p-0.5 text-xs font-mono outline-none"
                              autoFocus
                            />
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "concept", tx.concept)} 
                              className="cursor-pointer block w-full h-full"
                            >
                              <div className="flex flex-col">
                                <div className="flex items-center space-x-1.5">
                                  {tx.is_recurring && (
                                    <span 
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        toggleRecurrence(tx.id, tx.is_recurring);
                                      }}
                                      className="bg-brutalAmber text-black text-[9px] px-1 py-0.5 border border-black font-extrabold cursor-pointer uppercase select-none hover:bg-black hover:text-white transition-all"
                                      title="Hacer clic para desactivar recurrencia"
                                    >
                                      REC
                                    </span>
                                  )}
                                  <span>{tx.concept}</span>
                                </div>
                                {tx.is_recurring && (
                                  <div className="text-[9px] text-gray-500 font-mono mt-1 w-full truncate">
                                    🔁 Recurrencia: {tx.recurrence_interval === "PERSONALIZADO" ? `Cada ${tx.recurrence_days} días` : (tx.recurrence_interval || "Mensual").toLowerCase()}{tx.recurrence_max_reps ? ` (Max: ${tx.recurrence_max_reps} reps)` : ""}{tx.recurrence_end_date ? ` (Termina: ${tx.recurrence_end_date})` : ""}
                                  </div>
                                )}
                              </div>
                            </span>
                          )}
                        </td>

                        {/* Cuenta COA */}
                        <td className="p-2 border-r border-black font-semibold text-[11px] max-w-[150px] truncate">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "category" ? (
                            <select
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "category")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "category");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="bg-white border border-black p-0.5 text-xs font-mono outline-none w-full"
                              autoFocus
                            >
                              {coaFlatAccounts.length === 0 ? (
                                <option value={tx.category}>{tx.category}</option>
                              ) : (
                                coaFlatAccounts.map(acc => (
                                  <option key={acc.id} value={`${acc.code} - ${acc.name}`}>
                                    {acc.code} - {acc.name}
                                  </option>
                                ))
                              )}
                            </select>
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "category", tx.category)} 
                              className="cursor-pointer block w-full h-full text-blue-600 font-semibold"
                              title="Doble clic para cambiar cuenta contable"
                            >
                              {tx.category || "-"}
                            </span>
                          )}
                        </td>

                        {/* Tercero NIT/CC */}
                        <td className="p-2 border-r border-black uppercase text-gray-500 font-mono text-[10px]">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "identification_number" ? (
                            <input
                              type="text"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "identification_number")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "identification_number");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="w-full bg-white border-black p-0.5 text-xs font-mono outline-none"
                              autoFocus
                            />
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "identification_number", tx.identification_number)} 
                              className="cursor-pointer block w-full h-full"
                            >
                              {tx.identification_number}
                            </span>
                          )}
                        </td>

                        {/* Fecha */}
                        <td className="p-2 border-r border-black whitespace-nowrap font-mono text-[10px]">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "transaction_date" ? (
                            <input
                              type="date"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "transaction_date")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "transaction_date");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="bg-white border border-black p-0.5 text-xs font-mono outline-none"
                              autoFocus
                            />
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "transaction_date", tx.transaction_date)} 
                              className="cursor-pointer block w-full h-full"
                            >
                              {tx.transaction_date}
                            </span>
                          )}
                        </td>

                        {/* Cuenta */}
                        <td className="p-2 border-r border-black uppercase text-[11px]">
                          {editingCell && editingCell.txId === tx.id && editingCell.field === "account_id" ? (
                            <select
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onBlur={() => saveInlineEdit(tx.id, "account_id")}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") saveInlineEdit(tx.id, "account_id");
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              className="bg-white border border-black p-0.5 text-xs font-mono outline-none"
                              autoFocus
                            >
                              {accounts.map(acc => (
                                    <option key={acc.id} value={acc.id}>{acc.name}</option>
                              ))}
                            </select>
                          ) : (
                            <span 
                              onDoubleClick={() => startEditing(tx.id, "account_id", tx.account_id)} 
                              className="cursor-pointer block w-full h-full"
                            >
                              {tx.type === "TRANSFERENCIA" ? (
                                <span className="font-semibold">{tx.account_name || tx.payment_method} ➜ {tx.dest_account_name || "?"}</span>
                              ) : (
                                <span>{tx.account_name || tx.payment_method}</span>
                              )}
                            </span>
                          )}
                        </td>

                        {/* Lugar */}
                        <td className="p-2 border-r border-black text-center">
                          {tx.geo_maps_link ? (
                            <a 
                              href={tx.geo_maps_link} 
                              target="_blank" 
                              rel="noreferrer"
                              className="bg-brutalNeutral border border-black px-1.5 py-0.5 hover:bg-black hover:text-white transition-all inline-block uppercase text-[10px] font-bold"
                            >
                              [Maps]
                            </a>
                          ) : (
                            <span className="text-gray-300">-</span>
                          )}
                        </td>

                        {/* Evidencia */}
                        <td className="p-2 text-center">
                          <button
                            onClick={() => onEvidenceClick(tx)}
                            className="bg-black text-white border border-black px-1.5 py-0.5 hover:bg-brutalGreen hover:text-black transition-all uppercase text-[10px] font-bold"
                            type="button"
                          >
                            [Ver]
                          </button>
                        </td>
                      </tr>

                      {/* ═══ FILA EXPANDIBLE: Detalles de la Transacción ═══ */}
                      {expandedTxId === tx.id && (
                        <tr>
                          <td colSpan="9" className="p-0 border-t border-black">
                            <div className="bg-brutalBg p-3 border-b-2 border-black">
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[10px] font-mono">

                                {/* Tercero */}
                                {tx.third_party_name && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">👤 Tercero</span>
                                    <span className="font-bold block">{tx.third_party_name}</span>
                                    <span className="text-gray-400 block">{tx.identification_type} {tx.identification_number}</span>
                                  </div>
                                )}

                                {/* CXC/CXP */}
                                {tx.cxc_type && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">📄 {tx.cxc_type === 'CXC' ? 'Cuenta por Cobrar' : 'Cuenta por Pagar'}</span>
                                    <span className={`inline-block px-1.5 py-0.5 text-[9px] font-bold uppercase border ${tx.cxc_type === 'CXC' ? 'bg-brutalGreen border-black text-black' : 'bg-brutalAmber border-black text-black'}`}>
                                      {tx.cxc_type}
                                    </span>
                                    <span className="block">Vence: {tx.cxc_due_date || '-'}</span>
                                    <span className="block">Plazo: {tx.cxc_term || '-'}</span>
                                    {tx.cxc_status && <span className="block">Estado: {tx.cxc_status}</span>}
                                  </div>
                                )}

                                {/* Impuestos */}
                                {(tx.tax_iva_amount > 0 || tx.tax_gmf_amount > 0) && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">📈 Impuestos</span>
                                    {tx.tax_iva_amount > 0 && <span className="block">IVA: ${Number(tx.tax_iva_amount).toLocaleString()}</span>}
                                    {tx.tax_gmf_amount > 0 && <span className="block">GMF: ${Number(tx.tax_gmf_amount).toLocaleString()}</span>}
                                    <span className="block font-bold">Bruto: ${Number(tx.amount).toLocaleString()}</span>
                                  </div>
                                )}

                                {/* Divisa / TRM */}
                                {tx.transaction_currency && tx.transaction_currency !== 'COP' && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">💱 Divisa</span>
                                    <span className="block">{tx.transaction_currency}</span>
                                    {tx.trm && tx.trm !== 1 && <span className="block">TRM: {tx.trm}</span>}
                                  </div>
                                )}

                                {/* Recurrencia */}
                                {tx.is_recurring && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">🔁 Recurrencia</span>
                                    <span className="block">{tx.recurrence_interval || 'MENSUAL'} ({tx.recurrence_days || 30}d)</span>
                                    {tx.recurrence_max_reps && <span className="block">Máx: {tx.recurrence_max_reps} reps</span>}
                                    {tx.recurrence_end_date && <span className="block">Hasta: {tx.recurrence_end_date}</span>}
                                  </div>
                                )}

                                {/* Recurso / Activo */}
                                {tx.asset_name && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">📦 Recurso</span>
                                    <span className="font-bold block">{tx.asset_name}</span>
                                    {tx.asset_tag && <span className="block">Tag: {tx.asset_tag}</span>}
                                    {tx.asset_is_passive && <span className="block text-brutalGreen font-bold">♻ Ingreso pasivo</span>}
                                  </div>
                                )}

                                {/* Geo */}
                                {tx.geo_maps_link && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">📍 Ubicación</span>
                                    <a href={tx.geo_maps_link} target="_blank" rel="noreferrer" className="text-blue-600 underline break-all">
                                      Ver en Maps →
                                    </a>
                                  </div>
                                )}

                                {/* Tags (si existen en el futuro) */}
                                {tx.tags && tx.tags.length > 0 && (
                                  <div className="space-y-0.5">
                                    <span className="font-bold uppercase text-gray-400 block">🏷️ Etiquetas</span>
                                    <div className="flex flex-wrap gap-1">
                                      {tx.tags.map(tag => (
                                        <span key={tag} className="bg-black text-white px-1 py-0.5 text-[8px] font-bold uppercase">{tag}</span>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>

                              {/* Si no hay datos extra */}
                              {!tx.third_party_name && !tx.cxc_type && !tx.tax_iva_amount && !tx.tax_gmf_amount && !tx.is_recurring && !tx.asset_name && !(tx.transaction_currency && tx.transaction_currency !== 'COP') && (
                                <p className="text-[10px] text-gray-300 font-mono uppercase text-center py-2">Sin datos adicionales registrados</p>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                      </React.Fragment>
                    ))
                  )}
                </tbody>
              </table>

              {/* DT-12: Botón "Cargar más" si hay más TXs disponibles */}
              {transactions.length < totalTxCount && (
                <div style={{
                  display: 'flex', justifyContent: 'center', alignItems: 'center',
                  gap: 12, padding: '12px 0', borderTop: '2px solid #000',
                }}>
                  <span style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 10, color: '#888', textTransform: 'uppercase' }}>
                    Mostrando {transactions.length} de {totalTxCount} registros
                  </span>
                  <button
                    onClick={loadMoreTransactions}
                    disabled={loadingMore}
                    style={{
                      fontFamily: 'IBM Plex Mono, monospace', fontSize: 10,
                      textTransform: 'uppercase', letterSpacing: 1,
                      background: '#000', color: '#fff',
                      border: '2px solid #000', padding: '6px 16px',
                      cursor: loadingMore ? 'wait' : 'pointer',
                      opacity: loadingMore ? 0.5 : 1,
                    }}
                  >
                    {loadingMore ? '▓ CARGANDO...' : '↓ CARGAR 50 MÁS'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
  );
}
