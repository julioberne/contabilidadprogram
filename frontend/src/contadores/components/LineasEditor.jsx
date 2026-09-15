/* LineasEditor — tabla editable de líneas de un asiento con Σ en vivo. */
import CuentaSelect from './CuentaSelect.jsx';
import { fmt } from '../fmt.js';

const vacia = () => ({ cuenta_codigo: '', cuenta_nombre: '', debito: '', credito: '' });

export default function LineasEditor({ lineas, onChange, cuentas, listId = 'coa-list' }) {
  const filas = lineas && lineas.length ? lineas : [vacia(), vacia()];
  const set = (i, campo, v) => {
    const n = filas.map((l, j) => (j === i ? { ...l, [campo]: v } : l));
    if (campo === 'cuenta_codigo') {
      const c = (cuentas || []).find((x) => x.code === v);
      if (c) n[i].cuenta_nombre = c.name;
    }
    onChange(n);
  };
  const quitar = (i) => onChange(filas.filter((_, j) => j !== i));
  const agregar = () => onChange([...filas, vacia()]);
  const num = (v) => (v === '' || v == null ? 0 : Number(v) || 0);
  const td = filas.reduce((s, l) => s + num(l.debito), 0);
  const tc = filas.reduce((s, l) => s + num(l.credito), 0);
  const dif = Math.round((td - tc) * 100) / 100;
  const inp = 'border border-black px-1 py-0.5 text-[10px] font-mono bg-white w-full text-right';

  return (
    <div className="space-y-1">
      <table className="w-full text-[10px] font-mono border-collapse">
        <thead>
          <tr className="bg-black text-white">
            <th className="px-1 text-left">CUENTA</th>
            <th className="px-1 text-left">NOMBRE</th>
            <th className="px-1 text-right w-28">DÉBITO</th>
            <th className="px-1 text-right w-28">CRÉDITO</th>
            <th className="w-6"></th>
          </tr>
        </thead>
        <tbody>
          {filas.map((l, i) => (
            <tr key={i} className="border-b border-black">
              <td className="px-1 py-0.5">
                <CuentaSelect cuentas={cuentas} value={l.cuenta_codigo} listId={listId}
                              onChange={(v) => set(i, 'cuenta_codigo', v)} />
              </td>
              <td className="px-1 py-0.5">
                <input className="border border-black px-1 py-0.5 text-[10px] font-mono bg-white w-full"
                       value={l.cuenta_nombre || ''} onChange={(e) => set(i, 'cuenta_nombre', e.target.value)} />
              </td>
              <td className="px-1 py-0.5">
                <input type="number" min="0" step="0.01" className={inp} value={l.debito ?? ''}
                       onChange={(e) => set(i, 'debito', e.target.value)} />
              </td>
              <td className="px-1 py-0.5">
                <input type="number" min="0" step="0.01" className={inp} value={l.credito ?? ''}
                       onChange={(e) => set(i, 'credito', e.target.value)} />
              </td>
              <td className="text-center">
                <button type="button" className="text-brutalCrimson font-bold" title="Quitar línea"
                        onClick={() => quitar(i)}>✕</button>
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="font-bold">
            <td className="px-1 py-0.5" colSpan={2}>
              <button type="button" className="border border-black px-1 hover:bg-black hover:text-white"
                      onClick={agregar}>+ LÍNEA</button>
            </td>
            <td className="px-1 text-right">{fmt(td)}</td>
            <td className="px-1 text-right">{fmt(tc)}</td>
            <td></td>
          </tr>
        </tfoot>
      </table>
      <div className={`text-[10px] font-bold ${dif === 0 ? 'text-green-700' : 'text-brutalCrimson'}`}>
        {dif === 0 ? '✔ CUADRA' : `✖ DESCUADRE ${fmt(dif)}`}
      </div>
    </div>
  );
}

export function lineasValidas(lineas) {
  const num = (v) => (v === '' || v == null ? 0 : Number(v) || 0);
  const con = (lineas || []).filter((l) => l.cuenta_codigo && (num(l.debito) || num(l.credito)));
  if (con.length < 2) return false;
  const td = con.reduce((s, l) => s + num(l.debito), 0);
  const tc = con.reduce((s, l) => s + num(l.credito), 0);
  return Math.round((td - tc) * 100) === 0;
}

export function lineasPayload(lineas) {
  const num = (v) => (v === '' || v == null ? 0 : Number(v) || 0);
  return (lineas || [])
    .filter((l) => l.cuenta_codigo && (num(l.debito) || num(l.credito)))
    .map((l) => ({ cuenta_codigo: l.cuenta_codigo, cuenta_nombre: l.cuenta_nombre || '',
                   debito: num(l.debito), credito: num(l.credito) }));
}
