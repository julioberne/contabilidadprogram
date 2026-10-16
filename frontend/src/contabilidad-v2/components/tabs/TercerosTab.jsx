// TercerosTab.jsx — Extracted from ContextPanel.jsx
import React, { useState } from 'react';
import TerceroMediosPago from '../TerceroMediosPago';
import { useBusqueda, usePaginaTerceros } from '../../../shared/busqueda/useBusqueda.js';

export default function TercerosTab({
  search, setSearch,
  tercero,
  editingId, setEditingId,
  editData, setEditData,
  updateItem, deleteItem, createItem, refreshTP,
  SectionLabel,
}) {
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  // H3 (estándar de consultas): nada de catálogo completo. El selector busca en
  // el servidor (top-5) y la tabla de gestión se pagina de a 50 con su propio
  // filtro; tras crear/editar/borrar se recarga (version).
  const [version, setVersion] = useState(0);
  const [filtroTabla, setFiltroTabla] = useState('');
  const refrescar = () => { refreshTP?.(); setVersion((v) => v + 1); };
  const { items: sugeridos } = useBusqueda('terceros', search, { minimo: 2, limite: 5, version });
  const pagina = usePaginaTerceros(filtroTabla, { tamano: 50, version });

  const handleCreate = async () => {
    if (!tercero.name?.trim()) { setCreateError('El nombre es obligatorio.'); return; }
    setCreating(true);
    setCreateError('');
    try {
      await createItem('third-parties', {
        name: tercero.name,
        identification_type: tercero.idType || 'NIT',
        identification_number: tercero.idNumber || '',
        email: tercero.email || '',
        phone: tercero.phone || '',
        // La dirección va a `address` (antes se enviaba por error en `website`)
        address: tercero.address || '',
      }, refrescar);
    } catch (e) {
      setCreateError(e.message || 'Error al crear el tercero.');
    } finally {
      setCreating(false);
    }
  };

  const setCampo = (campo) => (e) => setEditData({ ...editData, [campo]: e.target.value });

  return (
    <>
      {/* --- Form: Identificación de Tercero --- */}
      <div className="border border-black p-2 bg-brutalBg space-y-1.5">
        <SectionLabel text="Vincular tercero a transacción" />
        <input type="text" value={search} onChange={e => { setSearch(e.target.value); }}
          placeholder="🔍 Buscar tercero existente..."
          className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen" />
        {search.length >= 2 && (
          <div className="border border-black bg-white max-h-24 overflow-y-auto">
            {sugeridos.map(tp => (
              <div key={tp.id} onClick={() => {
                if (tercero.setName) tercero.setName(tp.name || '');
                if (tercero.setIdType) tercero.setIdType(tp.identification_type || 'NIT');
                if (tercero.setIdNumber) tercero.setIdNumber(tp.identification_number || '');
                if (tercero.setEmail) tercero.setEmail(tp.email || '');
                if (tercero.setPhone) tercero.setPhone(tp.phone || '');
                if (tercero.setAddress) tercero.setAddress(tp.address || '');
                setSearch('');
              }} className="px-2 py-1 text-[10px] font-mono hover:bg-brutalGreen cursor-pointer border-b border-gray-100">
                <span className="font-bold">{tp.name}</span> <span className="text-gray-400">· {tp.identification_type} {tp.identification_number}</span>
              </div>
            ))}
          </div>
        )}
        <div className="text-[8px] text-gray-300 uppercase font-mono border-t border-dashed border-gray-200 pt-1">O crear nuevo:</div>
        <div className="grid grid-cols-2 gap-1">
          <input type="text" value={tercero.name || ''} onChange={e => tercero.setName?.(e.target.value)} placeholder="Nombre / Razón Social" className="col-span-2 border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen" />
          <select value={tercero.idType || 'NIT'} onChange={e => tercero.setIdType?.(e.target.value)} className="border border-black px-1 py-1 text-[10px] font-mono">
            <option value="NIT">NIT</option><option value="CC">CC</option><option value="CE">CE</option><option value="PP">Pasaporte</option>
          </select>
          <input type="text" value={tercero.idNumber || ''} onChange={e => tercero.setIdNumber?.(e.target.value)} placeholder="Número" className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
          <input type="email" value={tercero.email || ''} onChange={e => tercero.setEmail?.(e.target.value)} placeholder="Email" className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
          <input type="tel" value={tercero.phone || ''} onChange={e => tercero.setPhone?.(e.target.value)} placeholder="Teléfono" className="border border-black px-2 py-1 text-[10px] font-mono outline-none" />
          <input type="text" value={tercero.address || ''} onChange={e => tercero.setAddress?.(e.target.value)} placeholder="Dirección" className="col-span-2 border border-black px-2 py-1 text-[10px] font-mono outline-none" />
        </div>
        <button type="button" onClick={handleCreate} disabled={creating}
          className="w-full border border-black bg-brutalGreen px-2 py-1 text-[10px] font-bold uppercase hover:bg-black hover:text-white transition-all disabled:opacity-50">
          {creating ? 'Creando…' : '✓ Crear Tercero'}
        </button>
        {createError && <div className="text-[9px] text-red-600 font-mono">{createError}</div>}
      </div>
      {/* --- BD: third_parties --- */}
      <SectionLabel text={`third_parties · ${pagina.total} registros`} />
      <input type="search" value={filtroTabla} onChange={(e) => setFiltroTabla(e.target.value)}
        placeholder="Filtrar la tabla por nombre o documento…" aria-label="Filtrar la tabla de terceros"
        className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none focus:border-brutalGreen mb-1" />
      <table className="w-full text-[10px] font-mono border border-black">
        <thead className="bg-black text-white uppercase"><tr>
          <th className="p-1 border-r border-black text-left">Nombre</th>
          <th className="p-1 border-r border-black">Tipo</th>
          <th className="p-1 border-r border-black">NIT/CC</th>
          <th className="p-1 border-r border-black">Email</th>
          <th className="p-1">Acc.</th>
        </tr></thead>
        <tbody className="divide-y divide-gray-200">
          {pagina.items.map(tp => (
            <React.Fragment key={tp.id}>
              <tr className="hover:bg-brutalBg">
                {editingId === tp.id ? (<>
                  <td className="p-0.5 border-r border-black"><input type="text" value={editData.name||''} onChange={setCampo('name')} className="w-full border border-black px-1 py-0.5 text-[10px] font-mono outline-none" /></td>
                  <td className="p-0.5 border-r border-black"><select value={editData.identification_type||'NIT'} onChange={setCampo('identification_type')} className="border border-black px-0.5 py-0.5 text-[10px] font-mono"><option>NIT</option><option>CC</option></select></td>
                  <td className="p-0.5 border-r border-black"><input type="text" value={editData.identification_number||''} onChange={setCampo('identification_number')} className="w-full border border-black px-1 py-0.5 text-[10px] font-mono outline-none" /></td>
                  <td className="p-0.5 border-r border-black"><input type="text" value={editData.email||''} onChange={setCampo('email')} className="w-full border border-black px-1 py-0.5 text-[10px] font-mono outline-none" /></td>
                  <td className="p-0.5 text-center">
                    <button onClick={()=>updateItem('third-parties',tp.id,editData,refrescar)} title="Guardar la ficha" className="bg-brutalGreen border border-black px-1 py-0.5 text-[8px] font-bold mr-0.5">✓</button>
                    <button onClick={()=>setEditingId(null)} title="Cerrar" className="bg-gray-200 border border-black px-1 py-0.5 text-[8px] font-bold">✕</button>
                  </td>
                </>) : (<>
                  <td className="p-1 border-r border-black font-bold truncate max-w-[100px]">{tp.name}</td>
                  <td className="p-1 border-r border-black text-center text-[8px]">{tp.identification_type}</td>
                  <td className="p-1 border-r border-black">{tp.identification_number}</td>
                  <td className="p-1 border-r border-black text-gray-400 truncate max-w-[80px]">{tp.email||'—'}</td>
                  <td className="p-1 text-center whitespace-nowrap">
                    <button onClick={()=>{setEditingId(tp.id);setEditData({...tp});}} title="Abrir la ficha: todos los campos y sus cuentas / celulares / llaves" className="text-[9px] text-gray-400 hover:text-black font-bold">✎</button>
                    <button onClick={()=>deleteItem('third-parties',tp.id,refrescar)} className="text-[9px] text-gray-300 hover:text-red-500 font-bold ml-1">🗑</button>
                  </td>
                </>)}
              </tr>
              {/* Ficha completa (etapa 09.G §10): los campos que no caben en la fila
                  + los medios de pago con los que el bot reconoce a este tercero */}
              {editingId === tp.id && (
                <tr className="bg-yellow-50">
                  <td colSpan={5} className="p-1.5 space-y-1">
                    <div className="grid grid-cols-2 gap-1">
                      <input type="tel" value={editData.phone||''} onChange={setCampo('phone')} placeholder="Teléfono de contacto" aria-label="Teléfono" className="border border-black px-1 py-0.5 text-[10px] font-mono outline-none" />
                      <input type="text" value={editData.website||''} onChange={setCampo('website')} placeholder="Sitio web" aria-label="Sitio web" className="border border-black px-1 py-0.5 text-[10px] font-mono outline-none" />
                      <input type="text" value={editData.address||''} onChange={setCampo('address')} placeholder="Dirección" aria-label="Dirección" className="col-span-2 border border-black px-1 py-0.5 text-[10px] font-mono outline-none" />
                    </div>
                    <div className="text-[8px] font-mono text-gray-500">
                      Los cambios de la ficha se guardan con ✓. Los medios de pago de abajo se guardan al agregarlos.
                    </div>
                    <TerceroMediosPago terceroId={tp.id} />
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
      {!pagina.cargando && pagina.items.length===0 && <p className="text-center text-[10px] text-gray-300 font-mono uppercase py-2">Sin terceros</p>}
      {pagina.error && <p role="alert" className="text-[9px] text-red-600 font-mono">{pagina.error}</p>}
      {pagina.hayMas && (
        <button type="button" onClick={pagina.cargarMas} disabled={pagina.cargando}
          className="w-full mt-1 border border-black bg-black text-white text-[9px] font-bold uppercase py-1 disabled:opacity-50">
          {pagina.cargando ? 'Cargando…' : `↓ Cargar 50 más (${pagina.items.length} de ${pagina.total})`}
        </button>
      )}
    </>
  );
}
