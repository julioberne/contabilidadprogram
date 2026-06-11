import React, { useState, useEffect } from 'react';

const ThirdPartyModal = ({ isOpen, onClose, onSelect }) => {
  const [thirdParties, setThirdParties] = useState([]);
  const [search, setSearch] = useState("");
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // New Third Party Form State
  const [newType, setNewType] = useState("NIT");
  const [newNumber, setNewNumber] = useState("");
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [newWebsite, setNewWebsite] = useState("");

  useEffect(() => {
    if (isOpen) {
      fetchThirdParties();
      setIsCreatingNew(false);
      setSearch("");
    }
  }, [isOpen]);

  const fetchThirdParties = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("http://127.0.0.1:8000/api/third-parties");
      const data = await response.json();
      setThirdParties(data);
    } catch (err) {
      console.error("Error fetching third parties:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredParties = thirdParties.filter(tp => 
    tp.name.toLowerCase().includes(search.toLowerCase()) || 
    tp.identification_number.includes(search)
  );

  const handleSelect = (tp) => {
    onSelect({
      identification_type: tp.identification_type,
      identification_number: tp.identification_number,
      name: tp.name,
      email: tp.email || "",
      phone: tp.phone || "",
      website: tp.website || ""
    });
    onClose();
  };

  const handleCreateNew = () => {
    if (!newName || !newNumber) {
      alert("Nombre e Identificación son obligatorios para el nuevo tercero.");
      return;
    }
    
    // As we just want to select it to put it into the form, 
    // the backend will handle the actual creation on transaction submit.
    onSelect({
      identification_type: newType,
      identification_number: newNumber,
      name: newName,
      email: newEmail,
      phone: newPhone,
      website: newWebsite
    });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center p-4 z-[60] overflow-y-auto">
      <div className="bg-white border-4 border-black p-6 max-w-2xl w-full shadow-brutal my-8 font-mono relative">
        <div className="flex justify-between items-center border-b-4 border-black pb-2 mb-4">
          <span className="text-lg font-black uppercase">🏢 GESTIÓN DE TERCEROS</span>
          <button 
            onClick={onClose}
            className="bg-brutalCrimson text-white border-2 border-black px-3 py-1 font-bold uppercase hover:bg-black transition-all"
          >
            Cerrar [X]
          </button>
        </div>

        {!isCreatingNew ? (
          <div className="space-y-4">
            <div className="flex space-x-2">
              <input 
                type="text" 
                placeholder="🔍 Buscar por nombre o NIT/CC..." 
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-brutalNeutral border-2 border-black p-2 text-sm font-bold uppercase outline-none focus:bg-white"
              />
              <button 
                onClick={() => setIsCreatingNew(true)}
                className="bg-brutalGreen text-black border-2 border-black px-4 py-2 font-black uppercase hover:bg-black hover:text-white transition-all shrink-0"
              >
                + NUEVO TERCERO
              </button>
            </div>

            <div className="border-2 border-black max-h-64 overflow-y-auto bg-gray-50">
              {isLoading ? (
                <div className="p-4 text-center font-bold">Cargando terceros...</div>
              ) : filteredParties.length === 0 ? (
                <div className="p-4 text-center font-bold text-gray-500">No se encontraron terceros. Crea uno nuevo.</div>
              ) : (
                <table className="w-full text-left text-xs uppercase">
                  <thead className="bg-black text-white sticky top-0">
                    <tr>
                      <th className="p-2 border-r border-gray-700">Identificación</th>
                      <th className="p-2 border-r border-gray-700">Nombre</th>
                      <th className="p-2 text-center">Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredParties.map((tp, idx) => (
                      <tr key={idx} className="border-b border-black hover:bg-yellow-100 transition-colors">
                        <td className="p-2 border-r border-black font-bold">
                          {tp.identification_type} {tp.identification_number}
                        </td>
                        <td className="p-2 border-r border-black font-bold">
                          {tp.name}
                        </td>
                        <td className="p-2 text-center">
                          <button 
                            onClick={() => handleSelect(tp)}
                            className="bg-black text-white px-3 py-1 font-bold hover:bg-brutalGreen hover:text-black transition-colors"
                          >
                            SELECCIONAR
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-4 bg-brutalBg p-4 border-2 border-black">
            <div className="font-black border-b-2 border-black pb-2 uppercase text-sm">
              ✨ REGISTRO DE NUEVO TERCERO
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold uppercase block mb-1">Tipo Identificación*</label>
                <select 
                  value={newType} 
                  onChange={(e) => setNewType(e.target.value)}
                  className="w-full border-2 border-black p-2 font-bold uppercase"
                >
                  <option value="NIT">NIT</option>
                  <option value="CC">Cédula (CC)</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-bold uppercase block mb-1">Número ID*</label>
                <input 
                  type="text" 
                  value={newNumber}
                  onChange={(e) => setNewNumber(e.target.value)}
                  placeholder="Ej: 900.123.456-1"
                  className="w-full border-2 border-black p-2 font-bold"
                />
              </div>
              <div className="col-span-2">
                <label className="text-xs font-bold uppercase block mb-1">Razón Social / Nombre Completo*</label>
                <input 
                  type="text" 
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Nombre de la empresa o persona"
                  className="w-full border-2 border-black p-2 font-bold uppercase"
                />
              </div>
              <div>
                <label className="text-xs font-bold uppercase block mb-1">Email</label>
                <input 
                  type="email" 
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="opcional@correo.com"
                  className="w-full border-2 border-black p-2 font-bold"
                />
              </div>
              <div>
                <label className="text-xs font-bold uppercase block mb-1">Teléfono</label>
                <input 
                  type="text" 
                  value={newPhone}
                  onChange={(e) => setNewPhone(e.target.value)}
                  placeholder="Opcional"
                  className="w-full border-2 border-black p-2 font-bold"
                />
              </div>
            </div>

            <div className="flex space-x-2 pt-2">
              <button 
                onClick={() => setIsCreatingNew(false)}
                className="w-1/3 bg-gray-300 text-black border-2 border-black py-2 font-black uppercase hover:bg-black hover:text-white transition-all"
              >
                CANCELAR
              </button>
              <button 
                onClick={handleCreateNew}
                className="w-2/3 bg-black text-brutalGreen border-2 border-black py-2 font-black uppercase hover:bg-brutalGreen hover:text-black transition-all"
              >
                ASIGNAR A TRANSACCIÓN
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ThirdPartyModal;
