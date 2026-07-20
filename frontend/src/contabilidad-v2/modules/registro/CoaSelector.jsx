// CoaSelector.jsx — Extracted from App.jsx (Lines 249-330)
import React from 'react';

export default function CoaSelector({
  coaFlatAccounts,
  coaSearchQuery,
  setCoaSearchQuery,
  isCoaSearchFocused,
  setIsCoaSearchFocused,
  setCategory,
  handleLoadCoaTemplate,
}) {
  if (coaFlatAccounts.length === 0) {
    return (
      <div className="border-2 border-black p-2 bg-brutalAmber text-xs font-bold uppercase space-y-1">
        <p className="text-black font-mono">⚠️ No hay Catálogo de Cuentas (COA) en este portafolio.</p>
        <div className="flex flex-wrap gap-1">
          <button 
            type="button"
            onClick={() => handleLoadCoaTemplate("ESTANDAR")}
            className="bg-black text-white px-2 py-1 border border-black hover:bg-white hover:text-black text-[10px] font-bold tracking-wider uppercase transition-all"
          >
            Cargar ESTÁNDAR
          </button>
          <button 
            type="button"
            onClick={() => handleLoadCoaTemplate("INMOBILIARIA")}
            className="bg-black text-white px-2 py-1 border border-black hover:bg-white hover:text-black text-[10px] font-bold tracking-wider uppercase transition-all"
          >
            Cargar INMOBILIARIA
          </button>
          <button 
            type="button"
            onClick={() => handleLoadCoaTemplate("CONSTRUCTORA")}
            className="bg-black text-white px-2 py-1 border border-black hover:bg-white hover:text-black text-[10px] font-bold tracking-wider uppercase transition-all"
          >
            Cargar CONSTRUCTORA
          </button>
        </div>
      </div>
    );
  }

  const filtered = coaFlatAccounts.filter(acc => 
    acc.code.toLowerCase().includes(coaSearchQuery.toLowerCase()) || 
    acc.name.toLowerCase().includes(coaSearchQuery.toLowerCase())
  );

  return (
    <div className="relative">
      <input
        type="text"
        placeholder="Buscar cuenta COA (ej. 110505)..."
        value={coaSearchQuery}
        onChange={(e) => {
          setCoaSearchQuery(e.target.value);
          setCategory(e.target.value); // El payload enviará el query actual
        }}
        onFocus={() => setIsCoaSearchFocused(true)}
        onBlur={() => {
          // Retraso para que haga efecto el click de la lista antes de que se oculte
          setTimeout(() => setIsCoaSearchFocused(false), 200);
        }}
        className="w-full bg-white border-2 border-black p-2 text-xs font-mono outline-none focus:border-brutalGreen"
      />
      {isCoaSearchFocused && (
        <div className="absolute left-0 right-0 top-full mt-1 bg-white border-2 border-black shadow-brutal max-h-60 overflow-y-auto z-50">
          {filtered.length === 0 ? (
            <div className="p-2 text-xs text-gray-500 font-mono uppercase bg-gray-50">Sin resultados contables. Se guardará "{coaSearchQuery}".</div>
          ) : (
            filtered.map((acc) => (
              <button
                key={acc.id}
                type="button"
                onClick={() => {
                  const val = `${acc.code} - ${acc.name}`;
                  setCategory(val);
                  setCoaSearchQuery(val);
                  setIsCoaSearchFocused(false);
                }}
                className="w-full text-left p-2 text-xs font-mono hover:bg-brutalGreen hover:text-black border-b border-gray-100 block truncate"
              >
                <span className="font-bold text-blue-600 mr-2">{acc.code}</span>
                <span>{acc.name}</span>
                <span className="float-right text-[9px] bg-gray-100 text-gray-600 px-1 border border-gray-300 uppercase font-bold">{acc.account_type}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
