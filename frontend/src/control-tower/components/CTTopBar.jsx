// CTTopBar.jsx — Barra superior con selector de entidad + breadcrumb + usuario
import React, { useState } from 'react';

const ENTITY_ICONS = {
  HOLDING: '🏢',
  EMPRESA: '🏭',
  SUB_EMPRESA: '🏗️',
  PROYECTO: '📁',
  TAREA: '📄',
};

const STATUS_COLORS = {
  'AL DIA': 'text-green-400',
  'ALERTA': 'text-amber-400',
  'CRITICO': 'text-red-400',
};

function BreadcrumbNav({ breadcrumb, onNavigate }) {
  const MAX_VISIBLE = 3;
  const showEllipsis = breadcrumb.length > MAX_VISIBLE + 1;

  let visible = breadcrumb;
  if (showEllipsis) {
    visible = [breadcrumb[0], null, ...breadcrumb.slice(-2)];
  }

  return (
    <nav className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider overflow-hidden">
      {visible.map((crumb, idx) =>
        crumb === null ? (
          <span key="ellipsis" className="text-amber-400/40">···</span>
        ) : (
          <React.Fragment key={crumb.id}>
            {idx > 0 && <span className="text-amber-400/40">›</span>}
            <button
              onClick={() => idx < visible.length - 1 && onNavigate(crumb)}
              className={`px-1 py-0.5 transition-colors ${
                idx === visible.length - 1
                  ? 'text-white cursor-default'
                  : 'text-amber-400/70 hover:text-amber-400 cursor-pointer'
              }`}
            >
              {ENTITY_ICONS[crumb.type] || '📌'} {crumb.name}
            </button>
          </React.Fragment>
        )
      )}
    </nav>
  );
}

export default function CTTopBar({
  session, onLogout, onGoBack,
  activeEntity, entities, onSelectEntity,
  breadcrumb, onNavigate,
  onGoHome
}) {
  const [showEntityMenu, setShowEntityMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [search, setSearch] = useState('');

  // Flatten entities for search
  const flatEntities = [];
  const flatten = (nodes, depth = 0) => {
    nodes.forEach(n => {
      flatEntities.push({ ...n, depth });
      if (n.children?.length) flatten(n.children, depth + 1);
    });
  };
  flatten(entities);

  const filtered = flatEntities.filter(e =>
    e.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <header className="bg-black border-b-4 border-amber-400 flex items-center justify-between px-4 h-14 relative z-50 flex-shrink-0">
      {/* LEFT: Logo + Entity Selector */}
      <div className="flex items-center gap-4">
        {/* Logo/Home */}
        <button
          onClick={onGoHome}
          className="text-amber-400 font-black text-lg tracking-widest hover:text-white transition-colors flex-shrink-0"
          title="Ir al inicio del Control Tower"
        >
          ⬡ CT
        </button>

        <div className="w-px h-8 bg-amber-400/30" />

        {/* Entity Selector */}
        <div className="relative">
          <button
            onClick={() => { setShowEntityMenu(p => !p); setSearch(''); }}
            className="flex items-center gap-2 border border-amber-400/50 px-3 py-1.5 text-xs font-bold uppercase text-amber-400 hover:border-amber-400 hover:bg-amber-400/10 transition-all"
          >
            {activeEntity ? (
              <>
                <span>{ENTITY_ICONS[activeEntity.type] || '📌'}</span>
                <span className="max-w-[120px] truncate">{activeEntity.name}</span>
                <span className={`text-[9px] ${STATUS_COLORS[activeEntity.status] || 'text-white'}`}>
                  ●
                </span>
              </>
            ) : (
              <span className="text-amber-400/60">SELECCIONAR ENTIDAD ▾</span>
            )}
            <span className="text-amber-400/40 ml-1">▾</span>
          </button>

          {showEntityMenu && (
            <div className="absolute top-full left-0 mt-1 w-72 bg-black border-2 border-amber-400 shadow-[4px_4px_0px_#fbbf24] z-50">
              <div className="p-2 border-b border-amber-400/30">
                <input
                  autoFocus
                  type="text"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="🔍 Buscar entidad..."
                  className="w-full bg-black border border-amber-400/50 text-white text-xs p-1.5 outline-none focus:border-amber-400"
                />
              </div>
              <div className="max-h-64 overflow-y-auto">
                {filtered.length === 0 ? (
                  <p className="text-amber-400/40 text-[10px] p-3 text-center uppercase">Sin resultados</p>
                ) : (
                  filtered.map(e => (
                    <button
                      key={e.id}
                      onClick={() => { onSelectEntity(e); setShowEntityMenu(false); }}
                      className={`w-full text-left px-3 py-2 text-xs font-bold uppercase flex items-center gap-2 hover:bg-amber-400 hover:text-black transition-colors ${
                        activeEntity?.id === e.id ? 'bg-amber-400/20 text-amber-400' : 'text-white'
                      }`}
                      style={{ paddingLeft: `${12 + e.depth * 16}px` }}
                    >
                      <span>{ENTITY_ICONS[e.type] || '📌'}</span>
                      <span className="truncate">{e.name}</span>
                      <span className={`ml-auto text-[9px] ${STATUS_COLORS[e.status] || ''}`}>
                        {e.status === 'AL DIA' ? '✓' : e.status === 'ALERTA' ? '⚠' : '✕'}
                      </span>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* CENTER: Breadcrumb */}
      <div className="hidden md:flex flex-1 justify-center px-4">
        {breadcrumb.length > 0 ? (
          <BreadcrumbNav breadcrumb={breadcrumb} onNavigate={onNavigate} />
        ) : (
          <span className="text-amber-400/30 text-[10px] uppercase tracking-widest">
            MI PORTAFOLIO // SELECCIONA UNA ENTIDAD
          </span>
        )}
      </div>

      {/* RIGHT: User Badge */}
      <div className="relative">
        <button
          onClick={() => setShowUserMenu(p => !p)}
          className="flex items-center gap-2 border border-amber-400/50 px-3 py-1.5 hover:border-amber-400 hover:bg-amber-400/10 transition-all"
        >
          <div className="w-6 h-6 bg-amber-400 text-black text-[10px] font-black flex items-center justify-center">
            {session?.name?.[0]?.toUpperCase() || 'U'}
          </div>
          <div className="text-left hidden sm:block">
            <p className="text-white text-[10px] font-black uppercase leading-none">
              {session?.name?.split(' ')[0] || 'Usuario'}
            </p>
            <p className="text-amber-400/60 text-[9px] uppercase leading-none mt-0.5">
              {session?.role_label || 'Colaborador'}
            </p>
          </div>
          <span className="text-amber-400/40 text-[10px]">▾</span>
        </button>

        {showUserMenu && (
          <div className="absolute top-full right-0 mt-1 w-48 bg-black border-2 border-amber-400 shadow-[4px_4px_0px_#fbbf24] z-50">
            <div className="p-3 border-b border-amber-400/30">
              <p className="text-white text-xs font-black uppercase">{session?.name}</p>
              <p className="text-amber-400/60 text-[10px]">{session?.email}</p>
            </div>
            <button
              onClick={() => { setShowUserMenu(false); onGoBack && onGoBack(); }}
              className="w-full text-left px-3 py-2 text-xs text-white hover:bg-amber-400/10 font-bold uppercase"
            >
              ← VOLVER A FIN-SYS
            </button>
            <button
              onClick={() => { setShowUserMenu(false); onLogout(); }}
              className="w-full text-left px-3 py-2 text-xs text-red-400 hover:bg-red-400/10 font-bold uppercase"
            >
              ✕ CERRAR SESIÓN
            </button>
          </div>
        )}
      </div>

      {/* Close menus on outside click overlay */}
      {(showEntityMenu || showUserMenu) && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => { setShowEntityMenu(false); setShowUserMenu(false); }}
        />
      )}
    </header>
  );
}
