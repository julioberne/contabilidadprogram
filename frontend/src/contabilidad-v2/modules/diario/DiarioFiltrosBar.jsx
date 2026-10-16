/* ============================================================
   DiarioFiltrosBar.jsx — Búsqueda, filtros, orden, agrupación,
   chips activos, vistas guardadas y exportación CSV del Libro
   Diario (16-oct-2026). Solo arma los filtros: el servidor filtra.
   ============================================================ */
import React from 'react';
import { API } from '../../../config';
import {
  AGRUPACIONES, BANDERAS, FILTROS_VACIOS, ORDENES, RANGOS, TIPOS,
  chipsActivos, filtrosActivos, rangoRapido,
} from './diarioFiltros.js';

const btn = 'border-2 border-black px-2 py-0.5 text-[10px] font-bold uppercase hover:bg-black hover:text-white transition-all disabled:opacity-40';
const campo = 'border-2 border-black px-1.5 py-0.5 text-[10px] font-mono bg-white outline-none';
const titulo = 'text-[9px] font-bold uppercase text-gray-500 block mb-0.5';
const CLAVE_VISTAS = 'finsys_diario_vistas';

function leerVistas() {
  try { return JSON.parse(localStorage.getItem(CLAVE_VISTAS) || '[]'); } catch { return []; }
}
function guardarVistas(v) {
  try { localStorage.setItem(CLAVE_VISTAS, JSON.stringify(v)); } catch { /* sin almacenamiento */ }
}

/** Lista de casillas con buscador (terceros, cuentas, categorías, etiquetas). */
function MultiLista({ etiqueta, opciones, valor, onCambio, aId = (o) => o.id, aTexto = (o) => o.name, aSub }) {
  const [busca, setBusca] = React.useState('');
  const norm = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const visibles = (opciones || []).filter((o) => !busca || norm(`${aTexto(o)} ${aSub?.(o) || ''}`).includes(norm(busca)));
  const marcado = new Set(valor);
  const alternar = (id) => onCambio(marcado.has(id) ? valor.filter((x) => x !== id) : [...valor, id]);
  return (
    <div>
      <span className={titulo}>{etiqueta}{valor.length ? ` (${valor.length})` : ''}</span>
      {(opciones || []).length > 6 && (
        <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar…"
          className={`${campo} w-full mb-0.5`} aria-label={`Buscar en ${etiqueta}`} />
      )}
      <div className="border-2 border-black bg-white max-h-32 overflow-y-auto">
        {visibles.length === 0 && <div className="p-1 text-[9px] text-gray-400 uppercase">Sin opciones</div>}
        {visibles.map((o) => (
          <label key={aId(o)} className="flex items-center gap-1 px-1 py-0.5 text-[10px] font-mono hover:bg-brutalBg cursor-pointer">
            <input type="checkbox" checked={marcado.has(aId(o))} onChange={() => alternar(aId(o))} />
            <span className="truncate flex-1" title={aTexto(o)}>{aTexto(o)}</span>
            {aSub && <span className="text-gray-400 text-[9px]">{aSub(o)}</span>}
            {o.n != null && <span className="text-gray-400 text-[9px]">{o.n}</span>}
          </label>
        ))}
      </div>
    </div>
  );
}

export default function DiarioFiltrosBar({
  filtros, setFiltros, orden, setOrden, agrupar, setAgrupar,
  activePortfolio, total, cargando, onExportarCsv, onMarcarTodo, exportando,
}) {
  const [abierto, setAbierto] = React.useState(false);
  const [opciones, setOpciones] = React.useState({});
  const [vistas, setVistas] = React.useState(leerVistas);
  const [verVistas, setVerVistas] = React.useState(false);
  const [q, setQ] = React.useState(filtros.q);
  // Si la búsqueda cambia desde fuera (chip ✕, vista, Limpiar) el campo la sigue.
  const [qExterno, setQExterno] = React.useState(filtros.q);
  if (filtros.q !== qExterno) { setQExterno(filtros.q); setQ(filtros.q); }

  // La búsqueda viaja al servidor 300 ms después de dejar de escribir.
  React.useEffect(() => {
    if (q === filtros.q) return undefined;
    const t = setTimeout(() => setFiltros((f) => ({ ...f, q })), 300);
    return () => clearTimeout(t);
  }, [q]); // eslint-disable-line react-hooks/exhaustive-deps

  // Opciones de los selectores: solo valores que existen en las empresas elegidas.
  React.useEffect(() => {
    const p = new URLSearchParams();
    if (activePortfolio) p.set('portfolio', activePortfolio);
    if (filtros.empresas) p.set('empresas', filtros.empresas);
    let vivo = true;
    fetch(`${API}/diario/opciones?${p}`).then((r) => (r.ok ? r.json() : {}))
      .then((d) => { if (vivo) setOpciones(d || {}); }).catch(() => {});
    return () => { vivo = false; };
  }, [activePortfolio, filtros.empresas]);

  const set = (k, v) => setFiltros((f) => ({ ...f, [k]: v }));
  const alternarLista = (k, v) => setFiltros((f) => ({ ...f, [k]: f[k].includes(v) ? f[k].filter((x) => x !== v) : [...f[k], v] }));
  const ponerRango = (clave) => setFiltros((f) => (
    f.rango === clave ? { ...f, rango: '', desde: '', hasta: '' } : { ...f, rango: clave, ...rangoRapido(clave) }
  ));

  const chips = chipsActivos(filtros, opciones);
  const nPanel = chips.filter((c) => c.id !== 'q').length;
  const activos = filtrosActivos(filtros);

  const guardarVista = () => {
    const nombre = window.prompt('Nombre de la vista (ej. "Obra Bonaire · este mes"):');
    if (!nombre?.trim()) return;
    const nuevas = [...vistas.filter((v) => v.nombre !== nombre.trim()), { nombre: nombre.trim(), filtros, orden, agrupar }];
    setVistas(nuevas); guardarVistas(nuevas); setVerVistas(false);
  };
  const aplicarVista = (v) => {
    // Una vista con rango rápido se recalcula hoy ("este mes" sigue siendo este mes).
    const f = { ...FILTROS_VACIOS, ...v.filtros };
    if (f.rango) Object.assign(f, rangoRapido(f.rango));
    setFiltros(f); setOrden(v.orden || 'fecha_desc'); setAgrupar(v.agrupar || ''); setVerVistas(false);
  };
  const borrarVista = (nombre) => { const n = vistas.filter((v) => v.nombre !== nombre); setVistas(n); guardarVistas(n); };

  return (
    <div className="mb-2 space-y-1" onClick={(e) => e.stopPropagation()}>
      {/* Fila principal */}
      <div className="flex flex-wrap items-center gap-1">
        <div className="relative flex-1 min-w-[200px]">
          <input value={q} onChange={(e) => setQ(e.target.value)} aria-label="Buscar en el Libro Diario"
            onKeyDown={(e) => { if (e.key === 'Escape') setQ(''); }}
            placeholder="🔍 Buscar concepto, tercero, NIT, nota, etiqueta, cuenta, monto o #id…"
            className={`${campo} w-full pr-6 py-1`} />
          {q && <button type="button" onClick={() => setQ('')} aria-label="Borrar búsqueda"
            className="absolute right-1 top-1/2 -translate-y-1/2 text-[10px] font-bold">✕</button>}
        </div>
        <select value={filtros.rango} onChange={(e) => (e.target.value ? ponerRango(e.target.value) : setFiltros((f) => ({ ...f, rango: '', desde: '', hasta: '' })))}
          className={campo} aria-label="Periodo">
          <option value="">📅 Todo el tiempo</option>
          {RANGOS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        <select value={orden} onChange={(e) => setOrden(e.target.value)} className={campo} aria-label="Ordenar por">
          {ORDENES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        <select value={agrupar} onChange={(e) => setAgrupar(e.target.value)} className={campo} aria-label="Agrupar por">
          {AGRUPACIONES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        <button type="button" onClick={() => setAbierto((a) => !a)} aria-expanded={abierto}
          className={`${btn} ${abierto || nPanel ? 'bg-black text-white' : 'bg-white'}`}>
          ⚙ Filtros{nPanel ? ` (${nPanel})` : ''}
        </button>
        <div className="relative">
          <button type="button" onClick={() => setVerVistas((v) => !v)} className={`${btn} bg-white`}>⭐ Vistas</button>
          {verVistas && (
            <div className="absolute right-0 z-30 mt-1 w-64 bg-white border-2 border-black shadow-brutal p-1 space-y-1">
              {vistas.length === 0 && <div className="text-[9px] text-gray-400 uppercase p-1">Aún no hay vistas guardadas</div>}
              {vistas.map((v) => (
                <div key={v.nombre} className="flex items-center gap-1">
                  <button type="button" onClick={() => aplicarVista(v)}
                    className="flex-1 text-left text-[10px] font-bold px-1 py-0.5 hover:bg-black hover:text-white truncate">⭐ {v.nombre}</button>
                  <button type="button" onClick={() => borrarVista(v.nombre)} aria-label={`Borrar vista ${v.nombre}`}
                    className="text-[10px] px-1 hover:text-brutalCrimson">✕</button>
                </div>
              ))}
              <button type="button" onClick={guardarVista} disabled={!activos && !agrupar && orden === 'fecha_desc'}
                className={`${btn} w-full bg-brutalAmber`}>＋ Guardar vista actual</button>
            </div>
          )}
        </div>
        <button type="button" onClick={onExportarCsv} disabled={!total || exportando} className={`${btn} bg-white`}
          title="Descarga en CSV TODO lo filtrado (no solo lo cargado)">⬇ CSV</button>
        {onMarcarTodo && (
          <button type="button" onClick={onMarcarTodo} disabled={!total || exportando} className={`${btn} bg-white`}
            title="Marca todas las transacciones filtradas para exportar o editar en lote">☑ Marcar {total}</button>
        )}
      </div>

      {/* Panel de filtros */}
      {abierto && (
        <div className="border-2 border-black bg-brutalBg p-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
          <div className="space-y-2">
            <div>
              <span className={titulo}>Tipo</span>
              <div className="flex flex-wrap gap-1">
                {TIPOS.map(([k, l]) => (
                  <button key={k} type="button" onClick={() => alternarLista('tipos', k)} aria-pressed={filtros.tipos.includes(k)}
                    className={`${btn} ${filtros.tipos.includes(k) ? (k === 'INGRESO' ? 'bg-brutalGreen text-black' : k === 'GASTO' ? 'bg-brutalCrimson text-white' : 'bg-black text-white') : 'bg-white'}`}>
                    {l}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <span className={titulo}>Fecha</span>
              <div className="flex flex-wrap gap-1 mb-1">
                {RANGOS.map(([k, l]) => (
                  <button key={k} type="button" onClick={() => ponerRango(k)}
                    className={`${btn} ${filtros.rango === k ? 'bg-black text-white' : 'bg-white'}`}>{l}</button>
                ))}
              </div>
              <div className="flex items-center gap-1">
                <input type="date" value={filtros.desde} onChange={(e) => setFiltros((f) => ({ ...f, desde: e.target.value, rango: '' }))}
                  className={campo} aria-label="Desde" />
                <span className="text-[10px]">→</span>
                <input type="date" value={filtros.hasta} onChange={(e) => setFiltros((f) => ({ ...f, hasta: e.target.value, rango: '' }))}
                  className={campo} aria-label="Hasta" />
              </div>
            </div>
            <div>
              <span className={titulo}>Monto (valor neto)</span>
              <div className="flex items-center gap-1">
                <input type="number" min="0" value={filtros.monto_min} onChange={(e) => set('monto_min', e.target.value)}
                  placeholder="Mínimo" className={`${campo} w-24`} aria-label="Monto mínimo" />
                <span className="text-[10px]">–</span>
                <input type="number" min="0" value={filtros.monto_max} onChange={(e) => set('monto_max', e.target.value)}
                  placeholder="Máximo" className={`${campo} w-24`} aria-label="Monto máximo" />
              </div>
            </div>
            <div>
              <span className={titulo}>Empresa</span>
              <select value={filtros.empresas} onChange={(e) => set('empresas', e.target.value)} className={`${campo} w-full`} aria-label="Empresa">
                <option value="">Empresa activa ({activePortfolio || '—'})</option>
                <option value="*">Todas las empresas (consolidado)</option>
                {(opciones.empresas || []).filter((e) => e.valor !== activePortfolio).map((e) => (
                  <option key={e.id} value={e.valor}>{e.valor}</option>
                ))}
              </select>
            </div>
          </div>

          <MultiLista etiqueta="Tercero" opciones={opciones.terceros} valor={filtros.terceros}
            onCambio={(v) => set('terceros', v)} aSub={(o) => (o.ident && !String(o.ident).startsWith('SN-') ? o.ident : '')} />

          <div className="space-y-2">
            <MultiLista etiqueta="Medio de pago / cuenta" opciones={opciones.cuentas} valor={filtros.cuentas}
              onCambio={(v) => set('cuentas', v)} />
            <MultiLista etiqueta="Cuenta COA" opciones={opciones.categorias} valor={filtros.categorias}
              onCambio={(v) => set('categorias', v)} aId={(o) => o.valor} aTexto={(o) => o.valor} />
          </div>

          <div className="space-y-2">
            <MultiLista etiqueta="Etiqueta / proyecto" opciones={opciones.etiquetas} valor={filtros.etiquetas}
              onCambio={(v) => set('etiquetas', v)} aId={(o) => o.valor} aTexto={(o) => o.valor} />
            <div className="flex gap-1">
              <div className="flex-1">
                <span className={titulo}>Moneda</span>
                <select value={filtros.moneda} onChange={(e) => set('moneda', e.target.value)} className={`${campo} w-full`} aria-label="Moneda">
                  <option value="">Todas</option><option value="COP">COP</option><option value="USD">USD</option>
                </select>
              </div>
              <div className="flex-1">
                <span className={titulo}>Cartera</span>
                <select value={filtros.cartera} onChange={(e) => setFiltros((f) => ({ ...f, cartera: e.target.value, cartera_estado: '' }))}
                  className={`${campo} w-full`} aria-label="Cartera">
                  <option value="">Todas</option><option value="CXC">Por cobrar</option>
                  <option value="CXP">Por pagar</option><option value="NINGUNA">Sin cartera</option>
                </select>
              </div>
            </div>
            {(filtros.cartera === 'CXC' || filtros.cartera === 'CXP') && (
              <select value={filtros.cartera_estado} onChange={(e) => set('cartera_estado', e.target.value)}
                className={`${campo} w-full`} aria-label="Estado de cartera">
                <option value="">Cualquier estado</option><option value="PENDIENTE">Pendiente</option>
                <option value="VENCIDO">Vencido</option><option value="PAGADO">Pagado</option>
              </select>
            )}
            <div>
              <span className={titulo}>Calidad del dato</span>
              <div className="flex flex-wrap gap-1">
                {BANDERAS.map(([k, l]) => (
                  <button key={k} type="button" onClick={() => alternarLista('banderas', k)} aria-pressed={filtros.banderas.includes(k)}
                    className={`${btn} !px-1 ${filtros.banderas.includes(k) ? 'bg-brutalAmber text-black' : 'bg-white'}`}>{l}</button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Chips de filtros activos */}
      {chips.length > 0 && (
        <div className="flex flex-wrap items-center gap-1" aria-label="Filtros activos">
          {chips.map((c) => (
            <button key={c.id} type="button" onClick={() => setFiltros(c.quitar)} title="Quitar este filtro"
              className="border border-black bg-white px-1.5 py-0.5 text-[9px] font-bold font-mono hover:bg-brutalCrimson hover:text-white">
              {c.texto} ✕
            </button>
          ))}
          <button type="button" onClick={() => { setFiltros({ ...FILTROS_VACIOS }); setQ(''); }}
            className="border border-black bg-black text-white px-1.5 py-0.5 text-[9px] font-bold uppercase hover:bg-brutalCrimson">
            ✕ Limpiar todo
          </button>
          <span className="text-[9px] font-mono text-gray-500 uppercase">
            {cargando ? '▓ filtrando…' : `${total} resultado${total === 1 ? '' : 's'}`}
          </span>
        </div>
      )}
    </div>
  );
}
