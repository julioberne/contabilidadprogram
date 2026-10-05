/* ============================================================
   PreviewModal.jsx — Vista previa sin descargar (R-135-02) + ficha.
   xlsx/csv: primeras filas por hoja (el backend lee con openpyxl).
   PDF/imagen: el binario llega con sesión y se muestra desde una URL
   de objeto local (jamás una URL pública, R-135-05).
   ============================================================ */
import { useEffect, useState } from 'react';
import { api } from './api.js';
import { AvisoError, Modal, btnBlanco, btnNegro, btnPeligro } from './Dialogos.jsx';
import {
  esImagen, esPdf, esTabla, estadoVigencia, etiquetaPeriodo, fechaHora, formatoBytes, iconoArchivo,
} from './organizador.js';

const LETRAS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const columna = (i) => (i < 26 ? LETRAS[i] : LETRAS[Math.floor(i / 26) - 1] + LETRAS[i % 26]);

function Celda({ v }) {
  if (typeof v === 'number') {
    return <td className="border border-black/30 px-1 text-right tabular-nums whitespace-nowrap">
      {v.toLocaleString('es-CO', { maximumFractionDigits: 2 })}</td>;
  }
  const s = String(v ?? '');
  if (s.startsWith('=')) {
    return <td className="border border-black/30 px-1 text-gray-500 italic whitespace-nowrap" title="Fórmula: Excel la calcula al abrir">ƒ {s}</td>;
  }
  return <td className="border border-black/30 px-1 whitespace-nowrap max-w-[280px] truncate" title={s.length > 40 ? s : undefined}>{s}</td>;
}

function Tabla({ id }) {
  const [hoja, setHoja] = useState(null);
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let vivo = true;
    const q = hoja ? `?hoja=${encodeURIComponent(hoja)}&limite=60` : '?limite=60';
    api.get(`/accounting-files/${id}/preview${q}`)
      .then((d) => { if (vivo) { setDatos(d); setError(''); } })
      .catch((e) => { if (vivo) setError(e.message); });
    return () => { vivo = false; };
  }, [id, hoja]);
  if (error) return <AvisoError texto={`Sin vista previa: ${error}`} />;
  if (!datos) return <div className="p-4 text-center font-bold text-[11px]">⏳ Leyendo el archivo…</div>;
  return (
    <div className="space-y-1 min-w-0">
      {datos.hojas?.length > 0 && (
        <div role="tablist" aria-label="Hojas" className="flex flex-wrap gap-0.5">
          {datos.hojas.map((h) => (
            <button key={h} type="button" role="tab" aria-selected={h === datos.hoja} onClick={() => setHoja(h)}
              className={`border-2 border-black px-1.5 py-0.5 text-[9px] font-bold ${h === datos.hoja ? 'bg-black text-white' : 'bg-white hover:bg-brutalNeutral'}`}>
              {h}
            </button>
          ))}
        </div>
      )}
      <div className="overflow-auto border-2 border-black max-h-[58vh] bg-white">
        <table className="text-[10px] border-collapse">
          <thead className="sticky top-0 bg-brutalNeutral">
            <tr>
              <th className="border border-black/40 px-1 w-8" />
              {Array.from({ length: datos.columnas }, (_, i) => (
                <th key={i} className="border border-black/40 px-1 font-bold">{columna(i)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {datos.filas.map((fila, r) => (
              <tr key={r}>
                <td className="border border-black/40 px-1 text-right text-gray-500 bg-brutalBg">{r + 1}</td>
                {fila.map((v, c) => <Celda key={c} v={v} />)}
              </tr>
            ))}
          </tbody>
        </table>
        {datos.filas.length === 0 && <div className="p-3 text-center text-[10px]">La hoja está vacía.</div>}
      </div>
      {datos.mas_filas && <div className="text-[9px] text-gray-600">Mostrando las primeras {datos.filas.length} filas. Descarga el archivo para verlo completo.</div>}
    </div>
  );
}

function Binario({ id, mime, nombre }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let vivo = true;
    let creada = null;
    api.urlVistaPrevia(id)
      .then((u) => { creada = u; if (vivo) setUrl(u); else URL.revokeObjectURL(u); })
      .catch((e) => { if (vivo) setError(e.message); });
    return () => { vivo = false; if (creada) URL.revokeObjectURL(creada); };
  }, [id]);
  if (error) return <AvisoError texto={`Sin vista previa: ${error}`} />;
  if (!url) return <div className="p-4 text-center font-bold text-[11px]">⏳ Cargando…</div>;
  if (esImagen(mime)) return <img src={url} alt={nombre} className="max-w-full max-h-[62vh] mx-auto border-2 border-black bg-white" />;
  return <iframe src={url} title={`Vista previa de ${nombre}`} className="w-full h-[62vh] border-2 border-black bg-white" />;
}

function Dato({ k, children }) {
  if (children === null || children === undefined || children === '') return null;
  return (
    <div className="flex gap-1 border-b border-black/10 py-0.5">
      <span className="text-gray-600 w-24 shrink-0">{k}</span>
      <span className="font-bold min-w-0 break-words">{children}</span>
    </div>
  );
}

export default function PreviewModal({ item, tipos, admin, version, onCerrar, onAccion, onAbrirOtro }) {
  const [ficha, setFicha] = useState(null);
  const [error, setError] = useState('');
  const id = item.id;
  useEffect(() => {
    let vivo = true;
    api.get(`/accounting-files/${id}`)
      .then((f) => { if (vivo) { setFicha(f); setError(''); } })
      .catch((e) => { if (vivo) setError(e.message); });
    return () => { vivo = false; };
  }, [id, version]);

  const f = ficha || item;
  const { icono } = iconoArchivo(f.mime_type, f.nombre_archivo);
  const tipo = tipos.find((t) => t.id === f.tipo_documental_id);
  const vig = estadoVigencia(f);
  const generado = f.origen === 'GENERADO';
  const advertencias = ficha?.sello?.advertencias || [];

  return (
    <Modal titulo={`${icono} ${f.nombre}${f.folio ? ` · ${f.folio}` : ''}`} onCerrar={onCerrar} ancho="max-w-6xl" capa="z-[200]"
      pie={<>
        {admin && <button type="button" className={btnPeligro} onClick={() => onAccion('eliminar', f)}>✕ ELIMINAR</button>}
        {generado && <button type="button" className={btnBlanco} onClick={() => onAccion('regenerar', f)} title="Folio nuevo con los datos de hoy; este queda intacto">♻ REGENERAR</button>}
        <button type="button" className={btnBlanco} onClick={() => onAccion('fijar', f)}>{f.fijado ? '📌 DESFIJAR' : '📌 FIJAR'}</button>
        <button type="button" className={btnNegro} onClick={() => onAccion('descargar', f)}>↓ DESCARGAR</button>
      </>}>
      <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_270px]">
        <div className="min-w-0">
          {esTabla(f.mime_type) && <Tabla id={id} />}
          {(esPdf(f.mime_type) || esImagen(f.mime_type)) && <Binario id={id} mime={f.mime_type} nombre={f.nombre} />}
          {!esTabla(f.mime_type) && !esPdf(f.mime_type) && !esImagen(f.mime_type) && (
            <div className="p-4 text-center text-[11px]">Este tipo de archivo no tiene vista previa: descárgalo.</div>
          )}
        </div>
        <aside className="space-y-2 text-[10px] min-w-0">
          <AvisoError texto={error} />
          {vig && (
            <div className={`border-2 border-black p-1.5 ${vig.tono === 'ok' ? 'bg-brutalGreen/30' : 'bg-brutalAmber'}`}>
              <div className="font-bold text-[11px]">{vig.icono} {vig.texto}</div>
              {vig.tono === 'ok'
                ? <div>Los libros no han cambiado desde esta exportación.</div>
                : (
                  <>
                    <ul className="list-disc pl-4">{vig.detalles.map((d) => <li key={d}>{d}</li>)}</ul>
                    <div className="mt-0.5">♻ Regenerar crea un folio nuevo con los datos de hoy; este queda como se entregó.</div>
                  </>
                )}
            </div>
          )}
          <div>
            <Dato k="Folio">{f.folio}</Dato>
            <Dato k="Origen">{generado ? 'Generado por FIN-SYS' : 'Subido'}</Dato>
            <Dato k="Tipo">{tipo ? `${tipo.icono || ''} ${tipo.nombre}` : 'Sin tipo'}</Dato>
            <Dato k="Paquete">{f.paquete}</Dato>
            <Dato k="Empresa">{f.empresa || (generado ? 'Consolidado' : null)}</Dato>
            <Dato k="Período">{f.periodo_hasta ? etiquetaPeriodo(f.periodo_desde, f.periodo_hasta) : null}</Dato>
            <Dato k="Hojas">{f.hojas?.length ? f.hojas.join(' · ') : null}</Dato>
            <Dato k={generado ? 'Generado' : 'Subido'}>{`${fechaHora(f.creado_en)}${f.creado_por ? ` · ${f.creado_por}` : ''}`}</Dato>
            <Dato k="Tamaño">{formatoBytes(f.tamano_bytes)}</Dato>
            <Dato k="Descargas">{`${f.descargas ?? 0}${f.ultima_descarga ? ` · última ${fechaHora(f.ultima_descarga)}` : ''}`}</Dato>
            <Dato k="SHA-256"><span title={f.sha256} className="font-mono">{String(f.sha256 || '').slice(0, 16)}…</span></Dato>
            <Dato k="Retención">{f.fijado ? '📌 Fijado: no se purga' : f.vence_el ? `Se purga el ${f.vence_el}` : 'Para siempre (subido)'}</Dato>
          </div>
          {ficha?.reemplaza && (
            <div>Reemplaza a{' '}
              <button type="button" className="underline font-bold" onClick={() => onAbrirOtro(ficha.reemplaza.id)}>{ficha.reemplaza.folio}</button>
            </div>
          )}
          {ficha?.reemplazado_por?.length > 0 && (
            <div>Reemplazado por{' '}
              {ficha.reemplazado_por.map((r) => (
                <button key={r.id} type="button" className="underline font-bold mr-1" onClick={() => onAbrirOtro(r.id)}>{r.folio}</button>
              ))}
            </div>
          )}
          {advertencias.length > 0 && (
            <details className="border-2 border-black p-1 bg-brutalBg">
              <summary className="font-bold cursor-pointer">⚑ {advertencias.length} advertencia(s) de la carátula</summary>
              <ul className="list-disc pl-4 mt-0.5">{advertencias.map((a) => <li key={a}>{a}</li>)}</ul>
            </details>
          )}
          <div className="border-2 border-black p-1">
            <div className="flex items-center gap-1">
              <span className="font-bold">🗒 Nota</span>
              <button type="button" className="ml-auto underline" onClick={() => onAccion('nota', f)}>{f.nota ? 'editar' : 'agregar'}</button>
            </div>
            {f.nota ? <div className="whitespace-pre-line">{f.nota}</div> : <div className="text-gray-500">Sin nota.</div>}
          </div>
        </aside>
      </div>
    </Modal>
  );
}
