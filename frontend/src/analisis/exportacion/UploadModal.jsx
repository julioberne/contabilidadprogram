/* ============================================================
   UploadModal.jsx — Subir documentos externos al organizador 📦:
   extractos, declaraciones presentadas, certificados (§1.3).
   Se valida aquí lo obvio; el backend decide el tipo por el contenido.
   ============================================================ */
import { useRef, useState } from 'react';
import { api } from './api.js';
import { AvisoError, Modal, btnBlanco, btnNegro } from './Dialogos.jsx';
import { MESES, arbolPlano, formatoBytes, periodoSugerido, validarSubida } from './organizador.js';

const campo = 'border-2 border-black px-1 py-0.5 text-[10px] bg-white';

export default function UploadModal({ iniciales = [], tipos, carpetas, empresas, ubicacion, maxMb = 10, onCerrar, onSubido }) {
  const sugerido = periodoSugerido(ubicacion);
  const soportes = tipos.find((t) => t.clave === 'soportes');
  const [archivos, setArchivos] = useState(() => iniciales);
  const [nombre, setNombre] = useState('');
  const [tipoId, setTipoId] = useState(soportes?.id ?? tipos[0]?.id ?? '');
  const [pid, setPid] = useState(ubicacion?.pid ? String(ubicacion.pid) : '');
  const [conPeriodo, setConPeriodo] = useState(true);
  const [anio, setAnio] = useState(String(sugerido.anio));
  const [mes, setMes] = useState(sugerido.mes === '' ? '' : String(sugerido.mes));
  const [folderId, setFolderId] = useState(ubicacion?.nivel === 'carpeta' ? String(ubicacion.id) : '');
  const [nota, setNota] = useState('');
  const [progreso, setProgreso] = useState(null);   // "2/3"
  const [errores, setErrores] = useState([]);
  const [encima, setEncima] = useState(false);
  const inputRef = useRef(null);

  const agregar = (lista) => {
    const nuevos = [...lista];
    setErrores(nuevos.map((f) => validarSubida(f, maxMb)).filter(Boolean));
    setArchivos((prev) => [...prev, ...nuevos.filter((f) => !validarSubida(f, maxMb))]);
  };
  const quitar = (i) => setArchivos((prev) => prev.filter((_, j) => j !== i));
  const invalidos = archivos.map((f) => validarSubida(f, maxMb)).filter(Boolean);

  const subir = async () => {
    const fallos = [];
    const pendientes = [];
    let hechos = 0;
    for (let i = 0; i < archivos.length; i += 1) {
      const f = archivos[i];
      setProgreso(`${i + 1}/${archivos.length}`);
      const fd = new FormData();
      fd.append('archivo', f, f.name);
      if (archivos.length === 1 && nombre.trim()) fd.append('nombre', nombre.trim());
      if (tipoId !== '') fd.append('tipo_documental_id', String(tipoId));
      if (folderId) fd.append('folder_id', folderId);
      if (pid) fd.append('portfolio_id', pid);
      if (conPeriodo && anio) {
        fd.append('anio', anio);
        if (mes) fd.append('mes', mes);
      }
      if (nota.trim()) fd.append('nota', nota.trim());
      try {
        await api.subir(fd);
        hechos += 1;
      } catch (e) {
        fallos.push(`«${f.name}»: ${e.message}`);
        pendientes.push(f);
      }
    }
    setProgreso(null);
    if (!fallos.length) { onSubido(hechos); return; }
    setErrores(fallos);
    setArchivos(pendientes);
    if (hechos) onSubido(hechos, true);
  };

  const anioActual = new Date().getFullYear();
  const anios = Array.from({ length: 8 }, (_, i) => anioActual + 1 - i);
  const ocupado = progreso !== null;

  return (
    <Modal titulo="↑ Subir documentos" onCerrar={ocupado ? () => {} : onCerrar} ancho="max-w-xl" pie={<>
      <button type="button" className={btnBlanco} disabled={ocupado} onClick={onCerrar}>CANCELAR</button>
      <button type="button" className={btnNegro} disabled={ocupado || !archivos.length || invalidos.length > 0} onClick={subir}>
        {ocupado ? `SUBIENDO ${progreso}…` : `↑ SUBIR ${archivos.length || ''}`}
      </button>
    </>}>
      <div className="space-y-2">
        <div
          onDragOver={(e) => { e.preventDefault(); setEncima(true); }}
          onDragLeave={() => setEncima(false)}
          onDrop={(e) => { e.preventDefault(); setEncima(false); agregar(e.dataTransfer.files); }}
          className={`border-2 border-dashed border-black p-2 text-center ${encima ? 'bg-brutalAmber' : 'bg-brutalBg'}`}>
          <div className="text-[10px]">Arrastra aquí PDF, PNG, JPG, XLSX o CSV (máx. {maxMb} MB c/u) o</div>
          <button type="button" className={`${btnBlanco} mt-1`} onClick={() => inputRef.current?.click()}>ELEGIR ARCHIVOS</button>
          <input ref={inputRef} type="file" multiple hidden accept=".pdf,.png,.jpg,.jpeg,.xlsx,.csv"
            onChange={(e) => { agregar(e.target.files); e.target.value = ''; }} />
        </div>

        {archivos.length > 0 && (
          <ul className="border-2 border-black divide-y divide-black/10">
            {archivos.map((f, i) => (
              <li key={`${f.name}-${i}`} className="flex items-center gap-2 px-1 py-0.5 text-[10px]">
                <span className="truncate min-w-0 flex-1 font-bold">{f.name}</span>
                <span className="text-gray-600">{formatoBytes(f.size)}</span>
                <button type="button" disabled={ocupado} onClick={() => quitar(i)} aria-label={`Quitar ${f.name}`}
                  className="border border-black px-1 hover:bg-brutalCrimson hover:text-white">✕</button>
              </li>
            ))}
          </ul>
        )}
        {errores.map((e) => <AvisoError key={e} texto={e} />)}

        {archivos.length === 1 && (
          <label className="block space-y-0.5">
            <span className="font-bold text-[10px]">Nombre visible (opcional)</span>
            <input value={nombre} maxLength={160} onChange={(e) => setNombre(e.target.value)}
              placeholder={archivos[0].name.replace(/\.[^.]+$/, '')} className={`${campo} w-full`} />
          </label>
        )}

        <div>
          <div className="font-bold text-[10px] mb-0.5">Tipo documental</div>
          <div role="radiogroup" aria-label="Tipo documental" className="flex flex-wrap gap-1">
            {tipos.map((t) => (
              <button key={t.id} type="button" role="radio" aria-checked={tipoId === t.id} onClick={() => setTipoId(t.id)}
                style={{ borderColor: tipoId === t.id ? '#000' : t.color }}
                className={`border-2 px-1.5 py-0.5 text-[10px] font-bold ${tipoId === t.id ? 'bg-black text-white' : 'bg-white hover:bg-brutalNeutral'}`}>
                {t.icono} {t.nombre}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-2 sm:grid-cols-2">
          <label className="block space-y-0.5">
            <span className="font-bold text-[10px]">Empresa</span>
            <select value={pid} onChange={(e) => setPid(e.target.value)} className={`${campo} w-full`}>
              <option value="">— General / sin empresa —</option>
              {empresas.map((p) => <option key={p.id} value={p.id}>{p.etiqueta || p.name}</option>)}
            </select>
          </label>
          <label className="block space-y-0.5">
            <span className="font-bold text-[10px]">Carpeta propia</span>
            <select value={folderId} onChange={(e) => setFolderId(e.target.value)} className={`${campo} w-full`}>
              <option value="">— Ninguna (solo su lugar automático) —</option>
              {arbolPlano(carpetas).map((c) => (
                <option key={c.id} value={c.id}>{`${'   '.repeat(c.nivel)}📁 ${c.nombre}`}</option>
              ))}
            </select>
          </label>
        </div>

        <fieldset className="border-2 border-black p-1.5">
          <legend className="font-bold text-[10px] px-1">Período del documento</legend>
          <label className="inline-flex items-center gap-1 text-[10px] mr-2">
            <input type="checkbox" checked={conPeriodo} onChange={(e) => setConPeriodo(e.target.checked)} />
            Corresponde a un período
          </label>
          {conPeriodo && (
            <span className="inline-flex gap-1">
              <select aria-label="Año" value={anio} onChange={(e) => setAnio(e.target.value)} className={campo}>
                {anios.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
              <select aria-label="Mes" value={mes} onChange={(e) => setMes(e.target.value)} className={campo}>
                <option value="">Todo el año</option>
                {MESES.map((m, i) => <option key={m} value={i + 1}>{`${String(i + 1).padStart(2, '0')} ${m}`}</option>)}
              </select>
            </span>
          )}
          <div className="text-[9px] text-gray-600 mt-0.5">Con empresa y período queda solo en Empresa › Año › Mes.</div>
        </fieldset>

        <label className="block space-y-0.5">
          <span className="font-bold text-[10px]">Nota (opcional)</span>
          <textarea value={nota} maxLength={2000} rows={2} onChange={(e) => setNota(e.target.value)}
            placeholder="Ej: extracto enviado por el banco el 3-oct" className={`${campo} w-full`} />
        </label>
        <div className="text-[9px] text-gray-600">Lo subido no se purga: queda hasta que un administrador lo elimine.</div>
      </div>
    </Modal>
  );
}
