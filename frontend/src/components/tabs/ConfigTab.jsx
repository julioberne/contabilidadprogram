// ConfigTab.jsx — Extracted from ContextPanel.jsx
import React from 'react';

export default function ConfigTab({
  profile,
  profileEdit,
  activePortfolio,
  activeCompany,
  onCompanyUpdated,
  API_BASE,
  SectionLabel,
}) {
  return (
    <>
      <div className="border border-black p-2 bg-brutalBg space-y-1.5">
        <SectionLabel text="Perfil de usuario activo" />
        {profileEdit.isEditing ? (
          <div className="space-y-1.5">
            <input type="text" value={profileEdit.name||''} onChange={e=>profileEdit.setName?.(e.target.value)} placeholder="Nombre" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
            <input type="email" value={profileEdit.email||''} onChange={e=>profileEdit.setEmail?.(e.target.value)} placeholder="Email" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
            <input type="text" value={profileEdit.role||''} onChange={e=>profileEdit.setRole?.(e.target.value)} placeholder="Rol" className="w-full border border-black px-2 py-1 text-[10px] font-mono outline-none" />
            <div className="flex gap-1">
              <button type="button" onClick={profileEdit.handleSave} className="bg-black text-brutalGreen border border-black px-3 py-1 text-[9px] font-bold uppercase">GUARDAR</button>
              <button type="button" onClick={()=>profileEdit.setIsEditing?.(false)} className="bg-brutalNeutral border border-black px-3 py-1 text-[9px] font-bold uppercase">CANCELAR</button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-brutalGreen border-2 border-black flex items-center justify-center text-sm font-bold">{(profile?.name||'U').charAt(0).toUpperCase()}</div>
              <div>
                <span className="text-xs font-bold block">{profile?.name||'—'}</span>
                <span className="text-[9px] text-gray-400 font-mono">{profile?.email||'—'}</span>
              </div>
            </div>
            <button onClick={()=>{
              profileEdit.setName?.(profile?.name||'');
              profileEdit.setEmail?.(profile?.email||'');
              profileEdit.setRole?.(profile?.role||'');
              profileEdit.setIsEditing?.(true);
            }} className="text-xs border border-black px-1.5 py-0.5 hover:bg-brutalBg">✏️</button>
          </div>
        )}
      </div>
      <div className="grid grid-cols-2 gap-1">
        <div className="border border-gray-200 p-1.5"><span className="text-[8px] text-gray-400 uppercase block">Rol</span><span className="text-[10px] font-bold font-mono">{profile?.role||'—'}</span></div>
        <div className="border border-gray-200 p-1.5"><span className="text-[8px] text-gray-400 uppercase block">Portafolio</span><span className="text-[10px] font-bold font-mono">{activePortfolio}</span></div>
      </div>

      {/* ── Selector de Industria (Fase Config) ── */}
      {activeCompany && (
        <div className="border border-black p-2 bg-brutalBg space-y-1.5 mt-2">
          <SectionLabel text={`Industria · ${activeCompany.name}`} />
          <div className="flex items-center gap-2">
            <span className="text-[8px] font-bold uppercase text-gray-500 font-mono">Sector:</span>
            <select
              value={activeCompany.industry || 'ESTANDAR'}
              onChange={async (e) => {
                const newIndustry = e.target.value;
                try {
                  const res = await fetch(`${API_BASE}/org/entities/${activeCompany.id}/industry`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ industry: newIndustry }),
                  });
                  if (res.ok) {
                    onCompanyUpdated?.({ ...activeCompany, industry: newIndustry });
                  }
                } catch (err) {
                  console.error('Error actualizando industria:', err);
                }
              }}
              className="flex-1 border border-black px-2 py-1 text-[10px] font-mono bg-white outline-none focus:border-brutalGreen"
            >
              <option value="ESTANDAR">Estándar (General)</option>
              <option value="EDUCACION">Educación (Jardín / Colegio)</option>
              <option value="INMOBILIARIA">Inmobiliaria / Bienes Raíces</option>
              <option value="CONSTRUCTORA">Constructora</option>
              <option value="ECOMMERCE">E-commerce / Retail</option>
              <option value="SERVICIOS">Servicios / Consultoría</option>
              <option value="RESTAURANTE">Restaurante / Alimentos</option>
              <option value="SALUD">Salud / Clínica</option>
              <option value="TRANSPORTE">Transporte / Logística</option>
              <option value="APUESTAS">Casa de Apuestas</option>
            </select>
          </div>
          <p className="text-[8px] text-gray-400 font-mono uppercase leading-tight">
            Cambiar la industria activa los widgets, KPIs y labels del template correspondiente.
          </p>
        </div>
      )}
    </>
  );
}
