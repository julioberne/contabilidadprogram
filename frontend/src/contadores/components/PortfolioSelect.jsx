/* PortfolioSelect — selector de portafolio (empresa/presupuesto) del módulo. */
export default function PortfolioSelect({ portfolios, value, onChange, permitirTodos = true }) {
  return (
    <select
      className="border-2 border-black bg-white px-1 py-0.5 text-[11px] font-mono font-bold"
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
    >
      {permitirTodos && <option value="">TODOS LOS PORTAFOLIOS</option>}
      {(portfolios || []).map((p) => (
        <option key={p.id} value={p.id}>{p.name}</option>
      ))}
    </select>
  );
}
