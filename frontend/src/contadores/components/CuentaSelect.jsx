/* CuentaSelect — código de cuenta con lista filtrable (datalist) sobre el
   plan de cuentas del portafolio. Acepta cualquier código: el backend valida
   contra chart_of_accounts ∪ posting_rules. */
export default function CuentaSelect({ cuentas, value, onChange, listId = 'coa-list', className = '' }) {
  return (
    <>
      <input
        list={listId}
        className={`border border-black px-1 py-0.5 text-[10px] font-mono bg-white w-28 ${className}`}
        value={value || ''}
        placeholder="código"
        onChange={(e) => onChange(e.target.value.trim())}
      />
      <datalist id={listId}>
        {(cuentas || []).map((c) => (
          <option key={c.code} value={c.code}>{c.name}</option>
        ))}
      </datalist>
    </>
  );
}
