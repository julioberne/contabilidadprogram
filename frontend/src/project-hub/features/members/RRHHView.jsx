/* ============================================================
   RRHHView.jsx — Vista RRHH dedicada en menú principal
   Módulo 08c — Zero-Impact — nuevo componente
   ============================================================
   Incluye:
   - Mapa de Empresas (tabla/matriz empresa-empleados) ADMIN only
   - Se actualiza en tiempo real tras asignar/desvincular
   - FIX: load() se llama después de cada mutación con await
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import CompanyMapTab from './CompanyMapTab';

const API = 'http://localhost:8000/api/hub';
const FF  = '"IBM Plex Mono", monospace';
const C   = { bg: '#0a0a0a', border: '#1e1e1e', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };

export default function RRHHView({ workspace, user }) {
  const isAdmin = user?.role === 'owner' || user?.role === 'admin' || user?.is_superuser;
  const [members,  setMembers]  = useState([]);
  const [loading,  setLoading]  = useState(false);
  const [activeTab, setActiveTab] = useState('map');

  const loadMembers = useCallback(() => {
    if (!workspace?.id) return;
    setLoading(true);
    fetch(`${API}/users?workspace_id=${workspace.id}`)
      .then(r => r.json())
      .then(d => setMembers(Array.isArray(d) ? d : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [workspace?.id]);

  useEffect(() => { loadMembers(); }, [loadMembers]);

  if (!workspace) return (
    <div style={{ ...S.center, flex: 1 }}>
      <span style={{ color: C.dim, fontSize: '13px', fontFamily: FF }}>Selecciona un workspace</span>
    </div>
  );

  if (!isAdmin) return (
    <div style={{ ...S.center, flex: 1 }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '32px', opacity: .15, marginBottom: '12px' }}>◐</div>
        <span style={{ color: C.dim, fontSize: '13px', fontFamily: FF }}>Solo ADMIN / OWNER pueden acceder a RRHH</span>
      </div>
    </div>
  );

  return (
    <div style={S.root}>
      {/* Header */}
      <div style={S.header}>
        <div>
          <div style={S.title}>◐ RECURSOS HUMANOS</div>
          <div style={S.subtitle}>{workspace.name} · {members.length} empleado{members.length !== 1 ? 's' : ''}</div>
        </div>
      </div>

      {/* Tabs */}
      <div style={S.tabs}>
        <button style={{ ...S.tab, ...(activeTab === 'map' ? S.tabActive : {}) }} onClick={() => setActiveTab('map')}>
          ◈ Mapa de Empresas
        </button>
        {/* Extensible: más pestañas RRHH aquí */}
      </div>

      {/* Contenido */}
      <div style={S.body}>
        {loading && (
          <div style={S.loading}>Cargando empleados...</div>
        )}
        {!loading && activeTab === 'map' && (
          <CompanyMapTab
            workspace={workspace}
            currentUser={user}
            members={members}
          />
        )}
      </div>
    </div>
  );
}

const S = {
  root:    { display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', background: C.bg, fontFamily: FF },
  center:  { display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, background: C.bg, fontFamily: FF },
  header:  { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', padding: '20px 24px 12px', borderBottom: `2px solid ${C.border}`, flexShrink: 0 },
  title:   { color: C.accent, fontSize: '17px', letterSpacing: '3px', fontWeight: 700, marginBottom: '4px' },
  subtitle:{ color: C.dim, fontSize: '12px' },
  tabs:    { display: 'flex', borderBottom: `1px solid ${C.border}`, flexShrink: 0, padding: '0 12px' },
  tab:     { background: 'transparent', border: 'none', borderBottom: '2px solid transparent', color: C.dim, padding: '10px 16px', cursor: 'pointer', fontSize: '11px', fontFamily: FF, letterSpacing: '1px', transition: 'color .15s' },
  tabActive:{ color: C.accent, borderBottomColor: C.accent },
  body:    { flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' },
  loading: { color: C.dim, fontSize: '11px', padding: '20px 24px', fontFamily: FF },
};
