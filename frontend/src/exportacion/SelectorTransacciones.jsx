/* ============================================================
   SelectorTransacciones.jsx — Pestaña "Transacciones" de Nueva
   exportación (13.5-c): buscar y filtrar el Libro Diario, marcar
   a mano o "todas las filtradas", y exportar la relación (modo
   transacciones del motor 13.4, máx. 5000). La selección vive en
   el padre para que el pie (revisar/generar) la use.
   ============================================================ */
import { useMemo, useState } from 'react';
import { btnBlanco } from './Dialogos.jsx';
import { filtrarTransacciones, distintos, totalesPorMoneda, TIPOS_TX, MAX_TX } from './paquetes.js';

const pesos = (n, moneda = 'COP') => `${moneda === 'COP' ? '$' : `${moneda} `}${Number(n || 0).toLocaleString('es-CO', { maximumFractionDigits: 2 })}`;
const campo = 'border-2 border-black px-1 py-0.5 text-[10px] bg-white';

export default function SelectorTransacciones({ txs, cargando, error, seleccion, onSeleccion, nombre, onNombre }) {
  const [f, setF] = useState({ q: '', desde: '', hasta: '', empresa: '', tipo: '', categoria: '', tercero: '' });
  const [soloMarcadas, setSoloMarcadas] = useState(false);
  const cambiar = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));

  const filtradas = useMemo(() => filtrarTransacciones(txs, f), [txs, f]);
  const visibles = soloMarcadas ? filtradas.filter((t) => seleccion.has(t.id)) : filtradas;
  const marcadas = useMemo(() => (txs || []).filter((t) => seleccion.has(t.id)), [txs, seleccion]);
  const empresas = useMemo(() => distintos(txs, 'portfolio_name'), [txs]);
  const categorias = useMemo(() => distintos(txs, 'category'), [txs]);
  const terceros = useMemo(() => {
    const m = new Map();
    (txs || []).forEach((t) => { if (t.third_party_id != null) m.set(t.third_party_id, t.third_party_name || `#${t.third_party_id}`); });
    return [...m.entries()].sort((a, b) => String(a[1]).localeCompare(String(b[1]), 'es'));
  }, [txs]);

  const todasFiltradasMarcadas = filtradas.length > 0 && filtradas.every((t) => seleccion.has(t.id));
  const alternar = (id) => {
    const s = new Set(seleccion);
    if (s.has(id)) s.delete(id); else s.add(id);
    onSeleccion(s);
  };
  const marcarFiltradas = (marcar) => {
    const s = new Set(seleccion);
    filtradas.forEach((t) => (marcar ? s.add(t.id) : s.delete(t.id)));
    onSeleccion(s);
  };
  const limpiarFiltros = () => setF({ q: '', desde: '', hasta: '', empresa: '', tipo: '', categoria: '', tercero: '' });
  const totales = totalesPorMoneda(marcadas);

  if (cargando) return <div className="p-4 text-center font-bold">⏳ Cargando el Libro Diario…</div>;
  if (error) return <div className="p-2 bg-brutalCrimson text-white">{error}</div>;

  return (
    <div className="space-y-2">
      <p className="text-[10px] text-gray-700">
        Busca y filtra como en el Libro Diario; marca a mano o todas las filtradas. Se exporta una
        <b> Relación de transacciones</b> (carátula con sello, relación, asientos, resumen y soportes).
      </p>

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-1 border-2 border-black p-1 bg-brutalBg">
        <input type="search" value={f.q} onChange={cambiar('q')} placeholder="🔍 concepto, tercero, categoría, #id…"
          aria-label="Buscar transacciones" className={`${campo} flex-1 min-w-[180px]`} />
        <input type="date" value={f.desde} onChange={cambiar('desde')} aria-label="Desde" className={campo} />
        <span className="text-[10px]">a</span>
        <input type="date" value={f.hasta} onChange={cambiar('hasta')} aria-label="Hasta" className={campo} />
        <select value={f.empresa} onChange={cambiar('empresa')} aria-label="Empresa" className={campo}>
          <option value="">Todas las empresas</option>
          {empresas.map((e) => <option key={e} value={e}>{e}</option>)}
        </select>
        <select value={f.tipo} onChange={cambiar('tipo')} aria-label="Tipo" className={campo}>
          <option value="">Todo tipo</option>
          {TIPOS_TX.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={f.categoria} onChange={cambiar('categoria')} aria-label="Categoría" className={campo}>
          <option value="">Toda categoría</option>
          {categorias.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={f.tercero} onChange={cambiar('tercero')} aria-label="Tercero" className={`${campo} max-w-[160px]`}>
          <option value="">Todo tercero</option>
          {terceros.map(([id, n]) => <option key={id} value={id}>{n}</option>)}
        </select>
        <button type="button" className={btnBlanco} onClick={limpiarFiltros}>LIMPIAR</button>
      </div>

      {/* Barra de selección */}
      <div className="flex flex-wrap items-center gap-1 text-[10px]">
        <b>{filtradas.length}</b> filtradas · <b>{seleccion.size}</b> marcadas
        {Object.entries(totales).map(([m, v]) => (
          <span key={m} className="border border-black px-1 bg-white">Σ {pesos(v, m)}</span>
        ))}
        <span className="ml-auto flex flex-wrap gap-1">
          <button type="button" className={btnBlanco} disabled={!filtradas.length || todasFiltradasMarcadas}
            onClick={() => marcarFiltradas(true)}>☑ MARCAR LAS {filtradas.length} FILTRADAS</button>
          <button type="button" className={btnBlanco} disabled={!seleccion.size} onClick={() => onSeleccion(new Set())}>
            QUITAR MARCAS</button>
          <label className="inline-flex items-center gap-1 border-2 border-black px-1 bg-white">
            <input type="checkbox" checked={soloMarcadas} onChange={(e) => setSoloMarcadas(e.target.checked)} /> solo marcadas
          </label>
        </span>
      </div>
      {seleccion.size > MAX_TX && (
        <div className="bg-brutalAmber border-2 border-black p-1 text-[10px] font-bold">
          Máximo {MAX_TX} transacciones por relación ({seleccion.size} marcadas).
        </div>
      )}

      {/* Tabla */}
      <div className="border-2 border-black max-h-[38vh] overflow-auto bg-white">
        <table className="w-full text-[10px]">
          <thead className="sticky top-0 bg-brutalNeutral">
            <tr className="text-left">
              <th className="p-1 w-6">
                <input type="checkbox" aria-label="Marcar todas las filtradas" checked={todasFiltradasMarcadas}
                  onChange={(e) => marcarFiltradas(e.target.checked)} />
              </th>
              <th className="p-1">Fecha</th><th className="p-1">#</th><th className="p-1">Empresa</th>
              <th className="p-1">Tercero</th><th className="p-1">Concepto</th><th className="p-1">Categoría</th>
              <th className="p-1">Tipo</th><th className="p-1 text-right">Monto</th>
            </tr>
          </thead>
          <tbody>
            {visibles.map((t) => (
              <tr key={t.id} onClick={() => alternar(t.id)}
                className={`border-t border-black/20 cursor-pointer ${seleccion.has(t.id) ? 'bg-brutalAmber/30' : 'hover:bg-brutalBg'}`}>
                <td className="p-1" onClick={(e) => e.stopPropagation()}>
                  <input type="checkbox" aria-label={`Marcar transacción ${t.id}`} checked={seleccion.has(t.id)}
                    onChange={() => alternar(t.id)} />
                </td>
                <td className="p-1 whitespace-nowrap">{String(t.transaction_date || '').slice(0, 10)}</td>
                <td className="p-1">{t.id}</td>
                <td className="p-1 truncate max-w-[110px]">{t.portfolio_name}</td>
                <td className="p-1 truncate max-w-[120px]">{t.third_party_name}</td>
                <td className="p-1 truncate max-w-[220px]" title={t.concept}>{t.concept}</td>
                <td className="p-1 truncate max-w-[110px]">{t.category}</td>
                <td className="p-1">{t.type}</td>
                <td className="p-1 text-right whitespace-nowrap">{pesos(t.amount, t.transaction_currency || 'COP')}</td>
              </tr>
            ))}
            {!visibles.length && (
              <tr><td colSpan={9} className="p-3 text-center text-gray-600">Nada coincide con los filtros.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <label className="flex flex-wrap items-center gap-1 text-[10px]">
        <span className="font-bold">Nombre de la relación (opcional)</span>
        <input value={nombre} onChange={(e) => onNombre(e.target.value)} maxLength={120}
          placeholder="Ej.: Soportes para el banco — septiembre" className={`${campo} flex-1 min-w-[200px]`} />
      </label>
    </div>
  );
}
