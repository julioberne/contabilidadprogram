/* PeriodoPicker — desde/hasta con atajos. */
function rango(tipo) {
  const d = new Date();
  const y = d.getFullYear(), m = d.getMonth();
  const iso = (x) => x.toISOString().slice(0, 10);
  if (tipo === 'mes') return [iso(new Date(y, m, 1)), iso(new Date(y, m + 1, 0))];
  if (tipo === 'anterior') return [iso(new Date(y, m - 1, 1)), iso(new Date(y, m, 0))];
  if (tipo === 'anio') return [`${y}-01-01`, `${y}-12-31`];
  return ['', ''];
}

export default function PeriodoPicker({ desde, hasta, onChange }) {
  const inp = 'border border-black px-1 py-0.5 text-[10px] font-mono bg-white';
  const btn = 'border border-black px-1 text-[9px] hover:bg-black hover:text-white';
  return (
    <div className="flex flex-wrap items-center gap-1">
      <input type="date" className={inp} value={desde || ''} onChange={(e) => onChange(e.target.value, hasta)} />
      <span className="text-[10px]">→</span>
      <input type="date" className={inp} value={hasta || ''} onChange={(e) => onChange(desde, e.target.value)} />
      {[['mes', 'ESTE MES'], ['anterior', 'MES ANTERIOR'], ['anio', 'AÑO'], ['todo', 'TODO']].map(([k, l]) => (
        <button key={k} type="button" className={btn} onClick={() => onChange(...rango(k))}>{l}</button>
      ))}
    </div>
  );
}
