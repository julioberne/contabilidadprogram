/* ============================================================
   Organizador.jsx — La carpeta contable de la empresa (13.5-b).
   Mismo patrón que el organizador de RRHH (ruta clicable, buscador,
   cuadrícula/lista, lateral de categorías con conteos, carpetas de
   color, arrastrar y soltar, vista previa, menú por tarjeta) con
   código propio y la paleta clara de Análisis (D-135-07).

   Carpetas AUTOMÁTICAS: Empresa → Año → Mes (todo lo generado cae
   solo en su lugar). Carpetas PROPIAS: "+ Carpeta". Un archivo movido
   a una carpeta propia sigue apareciendo en su lugar automático.
   ============================================================ */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from './api.js';
import {
  AvisoError, DialogoCarpeta, DialogoConfirmar, DialogoElegir, DialogoTexto, btn, btnBlanco, btnNegro,
} from './Dialogos.jsx';
import FileCard from './FileCard.jsx';
import FolderCard from './FolderCard.jsx';
import PreviewModal from './PreviewModal.jsx';
import TiposModal from './TiposModal.jsx';
import UploadModal from './UploadModal.jsx';
import NuevaExportacion from './NuevaExportacion.jsx';
import {
  RAIZ, arbolPlano, armarArbol, carpetasAutomaticas, descendientes, migas, parametrosLista,
  puedeBorrar, queryString, subcarpetas,
} from './organizador.js';

const LIMITE = 50;
const CLAVE_VISTA = 'finsys_organizador_vista';

function leerVista() {
  try { return localStorage.getItem(CLAVE_VISTA) === 'lista' ? 'lista' : 'grid'; } catch { return 'grid'; }
}

function BotonLateral({ activo, onClick, children, n, color, titulo }) {
  return (
    <button type="button" onClick={onClick} title={titulo} aria-pressed={activo}
      className={`w-full flex items-center gap-1 text-left px-1 py-0.5 border-l-4 ${activo ? 'bg-black text-white border-brutalAmber' : 'border-transparent hover:bg-brutalNeutral'}`}>
      {color && <span className="w-2 h-2 border border-black shrink-0" style={{ background: color }} />}
      <span className="truncate min-w-0 flex-1">{children}</span>
      {n !== undefined && <span className={`text-[9px] ${activo ? 'text-white' : 'text-gray-600'}`}>{n}</span>}
    </button>
  );
}

export default function Organizador({ user, resumen, onCambio, paquetes, pedidoNueva, onPedidoAtendido }) {
  const [ubicacion, setUbicacion] = useState(RAIZ);
  const [filtro, setFiltro] = useState(null);
  const [q, setQ] = useState('');
  const [qAplicada, setQAplicada] = useState('');
  const [vista, setVista] = useState(leerVista);
  const [lista, setLista] = useState({ items: [], total: 0, clave: null });
  const [masCargando, setMasCargando] = useState(false);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState(null);           // {tono:'ok'|'error', texto}
  const [tipos, setTipos] = useState([]);
  const [carpetas, setCarpetas] = useState([]);
  const [portfolios, setPortfolios] = useState([]);
  const [preview, setPreview] = useState(null);       // item abierto
  const [version, setVersion] = useState(0);
  const [dialogo, setDialogo] = useState(null);       // elemento JSX del diálogo abierto
  const [subida, setSubida] = useState(null);         // File[] para el modal de subida
  const [verTipos, setVerTipos] = useState(false);
  const [nueva, setNueva] = useState(null);           // {pid, anio, mes, modo, paquete} → modal de Nueva exportación
  const [arrastrando, setArrastrando] = useState(false);
  const inputRef = useRef(null);
  const turno = useRef(0);

  const empresas = useMemo(() => armarArbol(resumen?.arbol), [resumen]);
  const admin = puedeBorrar(user);
  const maxMb = resumen?.max_mb || 10;
  const tipoDe = useCallback((id) => tipos.find((t) => t.id === id), [tipos]);

  useEffect(() => { try { localStorage.setItem(CLAVE_VISTA, vista); } catch { /* sin storage */ } }, [vista]);
  useEffect(() => {
    const t = setTimeout(() => setQAplicada(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  const cargarCatalogos = useCallback(() => Promise.all([
    api.get('/accounting-doc-types').then((d) => setTipos(Array.isArray(d) ? d : [])),
    api.get('/accounting-folders').then((d) => setCarpetas(Array.isArray(d) ? d : [])),
  ]).catch((e) => setError(e.message)), []);

  useEffect(() => {
    cargarCatalogos();
    // Empresas con el nombre del Control Tower (mismo idioma que Contabilidad).
    Promise.all([api.get('/portfolios').catch(() => []), api.get('/org/entities').catch(() => [])])
      .then(([ports, ents]) => {
        const alias = {};
        (Array.isArray(ents) ? ents : []).forEach((e) => {
          if (e?.portfolio_id != null && e?.name) alias[e.portfolio_id] = e.name.trim();
        });
        setPortfolios((Array.isArray(ports) ? ports : []).map((p) => ({ ...p, etiqueta: alias[p.id] || p.name })));
      });
  }, [cargarCatalogos]);

  const params = useMemo(() => parametrosLista({ ubicacion, filtro, q: qAplicada }), [ubicacion, filtro, qAplicada]);
  // "cargando" se deriva: la lista mostrada es de otra consulta que la pedida.
  const clave = useMemo(() => `${queryString(params)}|${version}`, [params, version]);
  const cargando = lista.clave !== clave || masCargando;

  useEffect(() => {
    const mio = ++turno.current;
    api.get(`/accounting-files${queryString({ ...params, limit: LIMITE, offset: 0 })}`)
      .then((r) => { if (mio === turno.current) { setLista({ ...r, clave }); setError(''); } })
      .catch((e) => { if (mio === turno.current) { setLista({ items: [], total: 0, clave }); setError(e.message); } });
  }, [clave, params]);

  const cargarMas = async () => {
    const mio = turno.current;
    setMasCargando(true);
    try {
      const r = await api.get(`/accounting-files${queryString({ ...params, limit: LIMITE, offset: lista.items.length })}`);
      if (mio === turno.current) setLista((prev) => ({ ...r, clave: prev.clave, items: [...prev.items, ...r.items] }));
    } catch (e) {
      avisar(e.message, 'error');
    } finally {
      setMasCargando(false);
    }
  };

  const refrescar = useCallback(() => {
    setVersion((v) => v + 1);
    cargarCatalogos();
    onCambio?.();
  }, [cargarCatalogos, onCambio]);

  const irA = (u) => { setUbicacion(u || RAIZ); setFiltro(null); setQ(''); setQAplicada(''); };
  const aplicarFiltro = (f) => { setFiltro(f); setUbicacion(RAIZ); setQ(''); setQAplicada(''); };
  const cerrarDialogo = () => setDialogo(null);
  const avisar = (texto, tono = 'ok') => setAviso({ texto, tono });

  // ── Acciones sobre un archivo ───────────────────────────────
  const patch = async (item, cambios, texto) => {
    await api.patch(`/accounting-files/${item.id}`, cambios);
    cerrarDialogo();
    avisar(texto);
    refrescar();
  };

  const accion = (clave, item) => {
    switch (clave) {
      case 'ver': setPreview(item); break;
      case 'descargar':
        api.descargar(item.id, item.nombre_archivo)
          .then(() => setVersion((v) => v + 1))
          .catch((e) => avisar(`No se pudo descargar: ${e.message}`, 'error'));
        break;
      case 'fijar':
        api.patch(`/accounting-files/${item.id}`, { fijado: !item.fijado })
          .then(() => { avisar(item.fijado ? `«${item.nombre}» ya no está fijado: vuelve a la retención de ${resumen?.retencion_dias ?? 90} días.` : `📌 «${item.nombre}» fijado: no se purga.`); refrescar(); })
          .catch((e) => avisar(e.message, 'error'));
        break;
      case 'renombrar':
        setDialogo(<DialogoTexto titulo="✎ Renombrar" etiqueta="Nombre visible" inicial={item.nombre}
          onOk={(v) => patch(item, { nombre: v }, 'Nombre actualizado.')} onCerrar={cerrarDialogo} />);
        break;
      case 'nota':
        setDialogo(<DialogoTexto titulo="🗒 Nota" etiqueta="Nota del archivo" inicial={item.nota || ''} multilinea max={2000} obligatorio={false}
          onOk={(v) => patch(item, { nota: v || null }, 'Nota guardada.')} onCerrar={cerrarDialogo} />);
        break;
      case 'mover':
        setDialogo(<DialogoElegir titulo="📁 Mover a carpeta propia" actual={item.folder_id ?? null}
          ayuda="El archivo sigue visible en su lugar automático (empresa › año › mes) y en su tipo documental."
          opciones={[{ valor: null, etiqueta: '— Ninguna (solo su lugar automático) —' },
            ...arbolPlano(carpetas).map((c) => ({ valor: c.id, etiqueta: `📁 ${c.nombre}`, nivel: c.nivel }))]}
          onOk={(v) => patch(item, { folder_id: v }, v ? 'Archivo movido.' : 'Archivo fuera de la carpeta propia.')} onCerrar={cerrarDialogo} />);
        break;
      case 'tipo':
        setDialogo(<DialogoElegir titulo="🏷 Tipo documental" actual={item.tipo_documental_id ?? null}
          opciones={[...tipos.map((t) => ({ valor: t.id, etiqueta: `${t.icono || ''} ${t.nombre}` })), { valor: null, etiqueta: '— Sin tipo —' }]}
          onOk={(v) => patch(item, { tipo_documental_id: v }, 'Tipo documental actualizado.')} onCerrar={cerrarDialogo} />);
        break;
      case 'regenerar':
        setDialogo(<DialogoConfirmar titulo="♻ Regenerar" textoOk="♻ REGENERAR"
          texto={`Se arma de nuevo «${item.nombre}» con los datos de HOY y queda con un folio nuevo.\nEl original ${item.folio} queda intacto: es lo que se entregó.`}
          onOk={async () => {
            const n = await api.post(`/accounting-files/${item.id}/regenerar`, {});
            cerrarDialogo();
            avisar(`♻ Nuevo folio ${n.folio}: reemplaza a ${item.folio}.`);
            refrescar();
            setPreview((p) => (p ? { ...p, id: n.id } : p));
          }} onCerrar={cerrarDialogo} />);
        break;
      case 'eliminar':
        setDialogo(<DialogoConfirmar titulo="✕ Eliminar archivo" textoOk="✕ ELIMINAR" peligro
          texto={`¿Eliminar «${item.nombre}»${item.folio ? ` (${item.folio})` : ''}?\nNo se puede deshacer.${item.origen === 'SUBIDO' ? ' Es un documento subido: FIN-SYS no lo puede volver a crear.' : ''}`}
          onOk={async () => {
            await api.del(`/accounting-files/${item.id}`);
            cerrarDialogo();
            setPreview((p) => (p?.id === item.id ? null : p));
            avisar(`Eliminado «${item.nombre}».`);
            refrescar();
          }} onCerrar={cerrarDialogo} />);
        break;
      default:
    }
  };

  const accionesDe = (item) => [
    { clave: 'ver', etiqueta: '👁 Ver', onClick: () => accion('ver', item) },
    { clave: 'descargar', etiqueta: '↓ Descargar', onClick: () => accion('descargar', item) },
    { clave: 'fijar', etiqueta: item.fijado ? '📌 Desfijar' : '📌 Fijar (no se purga)', onClick: () => accion('fijar', item) },
    { clave: 'renombrar', etiqueta: '✎ Renombrar', onClick: () => accion('renombrar', item) },
    { clave: 'nota', etiqueta: '🗒 Nota', onClick: () => accion('nota', item) },
    { clave: 'mover', etiqueta: '📁 Mover a carpeta…', onClick: () => accion('mover', item) },
    { clave: 'tipo', etiqueta: '🏷 Cambiar tipo…', onClick: () => accion('tipo', item) },
    item.origen === 'GENERADO' && { clave: 'regenerar', etiqueta: '♻ Regenerar', onClick: () => accion('regenerar', item) },
    admin && { clave: 'eliminar', etiqueta: '✕ Eliminar', peligro: true, onClick: () => accion('eliminar', item) },
  ];

  // ── Carpetas propias ────────────────────────────────────────
  const padreActual = ubicacion.nivel === 'carpeta' ? ubicacion.id : null;
  const nuevaCarpeta = () => setDialogo(
    <DialogoCarpeta titulo={padreActual ? '+ Subcarpeta' : '+ Carpeta'} onCerrar={cerrarDialogo}
      onOk={async (v) => {
        await api.post('/accounting-folders', { ...v, parent_id: padreActual });
        cerrarDialogo();
        avisar(`📁 Carpeta «${v.nombre}» creada.`);
        refrescar();
      }} />,
  );
  const accionesCarpeta = (c) => [
    { clave: 'editar', etiqueta: '✎ Nombre y color', onClick: () => setDialogo(
      <DialogoCarpeta titulo="✎ Carpeta" inicial={c} onCerrar={cerrarDialogo}
        onOk={async (v) => { await api.patch(`/accounting-folders/${c.id}`, v); cerrarDialogo(); refrescar(); }} />) },
    { clave: 'mover', etiqueta: '📁 Mover dentro de…', onClick: () => {
      const fuera = descendientes(carpetas, c.id);
      setDialogo(<DialogoElegir titulo={`📁 Mover «${c.nombre}»`} actual={c.parent_id ?? null}
        opciones={[{ valor: null, etiqueta: '— Raíz del archivo —' },
          ...arbolPlano(carpetas).map((x) => ({ valor: x.id, etiqueta: `📁 ${x.nombre}`, nivel: x.nivel, deshabilitada: fuera.has(x.id) }))]}
        onOk={async (v) => { await api.patch(`/accounting-folders/${c.id}`, { parent_id: v }); cerrarDialogo(); refrescar(); }}
        onCerrar={cerrarDialogo} />);
    } },
    admin && { clave: 'eliminar', etiqueta: '✕ Eliminar carpeta', peligro: true, onClick: () => setDialogo(
      <DialogoConfirmar titulo="✕ Eliminar carpeta" textoOk="✕ ELIMINAR" peligro onCerrar={cerrarDialogo}
        texto={`¿Eliminar la carpeta «${c.nombre}» y sus subcarpetas?\nLos archivos NO se borran: siguen en su lugar automático y en su tipo documental.`}
        onOk={async () => {
          await api.del(`/accounting-folders/${c.id}`);
          cerrarDialogo();
          if (ubicacion.nivel === 'carpeta' && descendientes(carpetas, c.id).has(ubicacion.id)) irA(RAIZ);
          refrescar();
        }} />) },
  ];

  // ── Subir (botón o arrastrar y soltar) ──────────────────────
  const abrirSubida = (files) => setSubida([...(files || [])]);
  const alSoltar = (e) => {
    e.preventDefault();
    setArrastrando(false);
    if (e.dataTransfer?.files?.length) abrirSubida(e.dataTransfer.files);
  };

  // ── Qué se muestra ──────────────────────────────────────────
  const buscando = !!qAplicada || !!filtro;
  const autos = buscando ? [] : carpetasAutomaticas(ubicacion, empresas);
  const propias = buscando ? [] : ubicacion.nivel === 'raiz' ? subcarpetas(carpetas, null)
    : ubicacion.nivel === 'carpeta' ? subcarpetas(carpetas, ubicacion.id) : [];
  const ruta = migas({ ubicacion, filtro, q: qAplicada, empresas, carpetas, tipos });
  const porTipo = resumen?.por_tipo || {};
  const tituloArchivos = qAplicada ? 'RESULTADOS' : filtro ? 'ARCHIVOS' : ubicacion.nivel === 'raiz' ? 'RECIENTES' : ubicacion.nivel === 'carpeta' ? 'EN ESTA CARPETA' : 'ARCHIVOS';
  const vacio = !cargando && !error && !autos.length && !propias.length && !lista.items.length;

  return (
    <div className="relative bg-white border-2 border-black"
      onDragOver={(e) => { if (e.dataTransfer?.types?.includes('Files')) { e.preventDefault(); setArrastrando(true); } }}
      onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) setArrastrando(false); }}
      onDrop={alSoltar}>

      {/* Barra superior */}
      <div className="flex flex-wrap items-center gap-1 border-b-2 border-black p-1.5 bg-brutalBg">
        <nav aria-label="Ruta" className="flex flex-wrap items-center gap-0.5 text-[11px] font-bold min-w-0 mr-auto">
          {ruta.map((m, i) => (
            <span key={`${m.etiqueta}-${i}`} className="inline-flex items-center gap-0.5">
              {i > 0 && <span className="text-gray-500">›</span>}
              {m.ubicacion && i < ruta.length - 1
                ? <button type="button" className="underline hover:bg-brutalAmber px-0.5" onClick={() => irA(m.ubicacion)}>{m.etiqueta}</button>
                : <span className="px-0.5 bg-black text-white" aria-current="page">{m.etiqueta}</span>}
            </span>
          ))}
        </nav>
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Buscar en el archivo"
          placeholder="🔍 folio, nombre, nota…" className="border-2 border-black px-1 py-0.5 text-[10px] w-full sm:w-44 bg-white" />
        <div role="group" aria-label="Vista" className="inline-flex">
          <button type="button" aria-pressed={vista === 'grid'} title="Cuadrícula" onClick={() => setVista('grid')}
            className={`${btn} ${vista === 'grid' ? 'bg-black text-white' : 'bg-white hover:bg-brutalNeutral'}`}>▦</button>
          <button type="button" aria-pressed={vista === 'lista'} title="Lista" onClick={() => setVista('lista')}
            className={`${btn} border-l-0 ${vista === 'lista' ? 'bg-black text-white' : 'bg-white hover:bg-brutalNeutral'}`}>☰</button>
          <button type="button" disabled title="Vista de cierres: paquete × mes (llega en 13.5-d)"
            className={`${btn} border-l-0 bg-white`}>🗓</button>
        </div>
        <button type="button" className={btnBlanco} onClick={nuevaCarpeta}
          title={padreActual ? 'Crear una subcarpeta aquí' : 'Crear una carpeta propia (ej. "Para el banco 2026")'}>+ CARPETA</button>
        <button type="button" className={btnBlanco} onClick={() => inputRef.current?.click()}
          title="Subir extractos, declaraciones, certificados (también puedes arrastrarlos)">↑ SUBIR</button>
        <input ref={inputRef} type="file" multiple hidden accept=".pdf,.png,.jpg,.jpeg,.xlsx,.csv"
          onChange={(e) => { abrirSubida(e.target.files); e.target.value = ''; }} />
        <button type="button" className={btnNegro} disabled={!paquetes}
          onClick={() => setNueva({ pid: ubicacion.pid, anio: ubicacion.anio, mes: ubicacion.mes })}
          title="Libros por período (paquetes, empresa, período, filtros) o relación de transacciones elegidas">📥 NUEVA EXPORTACIÓN</button>
      </div>

      <div className="flex flex-col md:flex-row">
        {/* Lateral: tipos documentales, filtros y carpetas propias */}
        <aside className="md:w-52 shrink-0 border-b-2 md:border-b-0 md:border-r-2 border-black p-1.5 space-y-2 text-[10px]">
          <section>
            <h3 className="font-bold text-[9px] tracking-wider text-gray-600 mb-0.5">TIPO DOCUMENTAL</h3>
            <BotonLateral activo={!filtro && !qAplicada && ubicacion.nivel === 'raiz'} onClick={() => irA(RAIZ)} n={resumen?.archivos ?? 0}>
              ▣ Todo el archivo
            </BotonLateral>
            {tipos.map((t) => (
              <BotonLateral key={t.id} activo={filtro?.tipo === t.id} onClick={() => aplicarFiltro({ tipo: t.id })}
                n={porTipo[String(t.id)] || 0} color={t.color} titulo={`Ver todo lo de tipo ${t.nombre}`}>
                {t.icono} {t.nombre}
              </BotonLateral>
            ))}
            {porTipo['0'] > 0 && (
              <BotonLateral activo={filtro?.tipo === 0} onClick={() => aplicarFiltro({ tipo: 0 })} n={porTipo['0']}>— Sin tipo</BotonLateral>
            )}
            <button type="button" className="mt-0.5 underline text-[9px]" onClick={() => setVerTipos(true)}>⚙ tipos documentales…</button>
          </section>
          <section>
            <h3 className="font-bold text-[9px] tracking-wider text-gray-600 mb-0.5">FILTROS</h3>
            <BotonLateral activo={!!filtro?.fijado} onClick={() => aplicarFiltro({ fijado: true })} n={resumen?.fijados ?? 0}
              titulo="Fijados: no se purgan nunca">📌 Fijados</BotonLateral>
            <BotonLateral activo={!!filtro?.cambiaron} onClick={() => aplicarFiltro({ cambiaron: true })} n={resumen?.cambiaron ?? 0}
              titulo="Los libros cambiaron después de exportarlos">⚠ Cambiaron</BotonLateral>
            <BotonLateral activo={!!filtro?.por_vencer} onClick={() => aplicarFiltro({ por_vencer: true })} n={resumen?.por_vencer ?? 0}
              titulo={`Generados sin fijar a punto de cumplir ${resumen?.retencion_dias ?? 90} días`}>⏳ Por vencer</BotonLateral>
          </section>
          <section>
            <h3 className="font-bold text-[9px] tracking-wider text-gray-600 mb-0.5">MIS CARPETAS</h3>
            {arbolPlano(carpetas).map((c) => (
              <div key={c.id} style={{ paddingLeft: `${c.nivel * 10}px` }}>
                <BotonLateral activo={ubicacion.nivel === 'carpeta' && ubicacion.id === c.id && !buscando}
                  onClick={() => irA({ nivel: 'carpeta', id: c.id })} color={c.color}>📁 {c.nombre}</BotonLateral>
              </div>
            ))}
            {!carpetas.length && <div className="text-gray-500 text-[9px]">Aún no hay carpetas propias.</div>}
          </section>
          <div className="text-[9px] text-gray-500 leading-snug border-t border-black/10 pt-1">
            Lo generado y sin fijar se purga a los {resumen?.retencion_dias ?? 90} días; lo fijado y lo subido, nunca.
          </div>
        </aside>

        {/* Principal */}
        <main className="flex-1 min-w-0 p-2 space-y-2">
          {aviso && (
            <div role="status" className={`flex items-start gap-2 border-2 border-black p-1 text-[10px] ${aviso.tono === 'error' ? 'bg-brutalCrimson text-white' : 'bg-brutalGreen/40'}`}>
              <span className="flex-1">{aviso.texto}</span>
              <button type="button" aria-label="Cerrar aviso" onClick={() => setAviso(null)} className="font-bold">✕</button>
            </div>
          )}
          <AvisoError texto={error} />

          {(autos.length > 0 || propias.length > 0) && (
            <section aria-label="Carpetas">
              <h3 className="font-bold text-[9px] tracking-wider text-gray-600 mb-1">CARPETAS</h3>
              <div className="grid gap-1.5 grid-cols-[repeat(auto-fill,minmax(180px,1fr))]">
                {autos.map((c) => (
                  <FolderCard key={c.clave} etiqueta={c.etiqueta} n={c.n} icono={c.icono} color="#000000"
                    titulo="Carpeta automática: se llena sola con lo generado" onAbrir={() => irA(c.ubicacion)} />
                ))}
                {propias.map((c) => (
                  <FolderCard key={`p${c.id}`} etiqueta={c.nombre} n={c.n_archivos} color={c.color}
                    onAbrir={() => irA({ nivel: 'carpeta', id: c.id })} acciones={accionesCarpeta(c)} />
                ))}
              </div>
            </section>
          )}

          <section aria-label="Archivos">
            <h3 className="font-bold text-[9px] tracking-wider text-gray-600 mb-1">
              {tituloArchivos} · {lista.total}{cargando ? ' · cargando…' : ''}
            </h3>
            {lista.items.length > 0 && (
              <div className={vista === 'grid' ? 'grid gap-1.5 grid-cols-[repeat(auto-fill,minmax(170px,1fr))]' : 'space-y-1'}>
                {lista.items.map((it) => (
                  <FileCard key={it.id} item={it} tipo={tipoDe(it.tipo_documental_id)} vista={vista}
                    onAbrir={() => setPreview(it)} acciones={accionesDe(it)} />
                ))}
              </div>
            )}
            {lista.items.length < lista.total && (
              <button type="button" className={`${btnBlanco} mt-1`} disabled={cargando} onClick={cargarMas}>
                CARGAR MÁS ({lista.total - lista.items.length})
              </button>
            )}
            {vacio && (
              <div className="border-2 border-dashed border-black p-4 text-center space-y-1 bg-brutalBg">
                <div className="text-[28px] leading-none">📦</div>
                <div className="font-bold text-[11px]">{buscando ? 'Nada coincide.' : 'Aún no hay archivos aquí.'}</div>
                {!buscando && (
                  <div className="text-[10px] text-gray-700">
                    Arrastra un PDF, imagen, Excel o CSV, o usa ↑ SUBIR. Los libros que genere 📥 Nueva exportación
                    caen solos en Empresa › Año › Mes.
                  </div>
                )}
              </div>
            )}
            {!vacio && !lista.items.length && !cargando && !error && (
              <div className="text-[10px] text-gray-600">No hay archivos sueltos en este nivel: entra a una carpeta.</div>
            )}
          </section>
        </main>
      </div>

      {arrastrando && (
        <div className="absolute inset-0 z-20 bg-brutalAmber/80 border-4 border-dashed border-black flex items-center justify-center pointer-events-none">
          <span className="bg-white border-2 border-black px-3 py-2 font-bold text-[12px]">⬇ Suelta para subir aquí</span>
        </div>
      )}

      {preview && (
        <PreviewModal item={preview} tipos={tipos} admin={admin} version={version}
          onCerrar={() => setPreview(null)} onAccion={accion}
          onAbrirOtro={(id) => setPreview({ id, nombre: '…', mime_type: '' })} />
      )}
      {subida && (
        <UploadModal iniciales={subida} tipos={tipos} carpetas={carpetas} empresas={portfolios}
          ubicacion={ubicacion} maxMb={maxMb} onCerrar={() => setSubida(null)}
          onSubido={(n, parcial) => {
            if (!parcial) setSubida(null);
            avisar(`↑ ${n} documento(s) subido(s).`);
            refrescar();
          }} />
      )}
      {verTipos && <TiposModal tipos={tipos} admin={admin} onCambio={refrescar} onCerrar={() => setVerTipos(false)} />}
      {(nueva || pedidoNueva) && paquetes && (
        <NuevaExportacion paquetes={paquetes} portfolios={portfolios} carpetas={carpetas} inicial={nueva || pedidoNueva}
          onCerrar={() => { setNueva(null); onPedidoAtendido?.(); }}
          onGenerado={(res) => { avisar(`📥 ${res.folio || 'Exportación'} generada: ${res.nombre}`); refrescar(); }} />
      )}
      {dialogo}
    </div>
  );
}
