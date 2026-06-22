/* ============================================================
   HRProfileTab.jsx — Ficha RRHH expandida v2
   Módulo 08c — Zero-Impact
   ============================================================
   Nuevos campos: rol/funciones, email, contrato, banco (3 campos),
   EPS, pensión, seguridad social, país/ciudad, estado civil,
   educación, skills (texto libre), avatar (upload real)
   ============================================================ */
import { useState, useEffect, useRef } from 'react';
import { supabase } from '../../../lib/supabaseClient';

const API    = 'http://localhost:8000/api/hr';
const SB_URL = 'https://sciorfjvdqxvcwgvnmbv.supabase.co';

const STATUS_OPTS = [
  { id: 'active',     label: 'ACTIVO',    color: '#10B981' },
  { id: 'leave',      label: 'LICENCIA',  color: '#F59E0B' },
  { id: 'terminated', label: 'TERMINADO', color: '#EF4444' },
];
const CONTRACT_TYPES = [
  'Término fijo', 'Término indefinido', 'Obra-labor',
  'Prestación de servicios', 'Aprendizaje', 'Temporal',
];
const MARITAL_OPTS   = ['Soltero/a', 'Casado/a', 'Unión libre', 'Divorciado/a', 'Viudo/a'];
const EDUCATION_OPTS = ['Bachiller', 'Técnico', 'Tecnólogo', 'Profesional', 'Especialización', 'Maestría', 'Doctorado'];
const BANK_TYPES     = ['Cuenta de Ahorros', 'Cuenta Corriente', 'Nómina'];

// ── Avatar con upload ────────────────────────────────────────────────────────
function Avatar({ name, avatarUrl, userId, workspaceId, canEdit, onUpdate }) {
  const ref    = useRef(null);
  const [uploading, setUploading] = useState(false);
  const initials = (name || 'NN').split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();

  const handleAvatarUpload = async (file) => {
    if (!file || !file.type.startsWith('image/')) return;
    setUploading(true);
    try {
      const path = `avatars/${userId}/${Date.now()}_${file.name}`;
      const { error } = await supabase.storage.from('hr-docs').upload(path, file, { contentType: file.type, upsert: true });
      if (error) throw error;
      const url = `${SB_URL}/storage/v1/object/public/hr-docs/${path}`;
      await fetch(`${API}/profile/${userId}?workspace_id=${workspaceId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ avatar_url: url }),
      });
      onUpdate(url);
    } finally { setUploading(false); }
  };

  return (
    <div style={AV.wrap}>
      <div style={{ ...AV.circle, ...(canEdit ? AV.circleHover : {}) }}
        onClick={() => canEdit && ref.current?.click()}
        title={canEdit ? 'Click para cambiar foto' : ''}>
        {avatarUrl
          ? <img src={avatarUrl} alt={name} style={AV.img} onError={e => { e.target.style.display = 'none'; }} />
          : <span style={AV.initials}>{initials}</span>
        }
        {canEdit && (
          <div style={AV.overlay}>
            <span style={{ fontSize: '18px' }}>{uploading ? '⟳' : '📷'}</span>
          </div>
        )}
      </div>
      {canEdit && <input ref={ref} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => handleAvatarUpload(e.target.files[0])} />}
    </div>
  );
}

const AV = {
  wrap:        { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' },
  circle:      { width: '80px', height: '80px', borderRadius: '50%', background: '#1a2a3a', border: '2px solid #1e3a5f', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden', flexShrink: 0 },
  circleHover: { cursor: 'pointer' },
  img:         { width: '100%', height: '100%', objectFit: 'cover' },
  initials:    { color: '#0EA5E9', fontSize: '22px', fontWeight: 700, fontFamily: '"IBM Plex Mono", monospace', letterSpacing: '1px' },
  overlay:     { position: 'absolute', inset: 0, background: 'rgba(0,0,0,.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0, transition: 'opacity .2s' },
};

// ── Componente principal ──────────────────────────────────────────────────────
export default function HRProfileTab({ member, workspace, currentUser }) {
  const canEdit = currentUser?.role === 'owner' || currentUser?.role === 'admin' || currentUser?.is_superuser;
  const avatarRef = useRef(null);

  const [profile,   setProfile]   = useState(null);
  const [companies, setCompanies] = useState([]);
  const [entities,  setEntities]  = useState([]);
  const [editing,   setEditing]   = useState(false);
  const [form,      setForm]      = useState({});
  const [saving,    setSaving]    = useState(false);
  const [addCoForm, setAddCoForm] = useState({ entity_id: '', role_in_company: '', start_date: '' });
  const [showAddCo, setShowAddCo] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState('');

  useEffect(() => {
    if (!member?.id || !workspace?.id) return;
    loadProfile(); loadCompanies(); loadEntities();
  }, [member?.id, workspace?.id]);

  const loadProfile = () =>
    fetch(`${API}/profile/${member.id}?workspace_id=${workspace.id}`)
      .then(r => r.json())
      .then(d => { setProfile(d); setForm(d); setAvatarUrl(d.avatar_url || ''); })
      .catch(() => {});

  const loadCompanies = () =>
    fetch(`${API}/companies/${member.id}`)
      .then(r => r.json())
      .then(d => setCompanies(Array.isArray(d) ? d : []))
      .catch(() => {});

  const loadEntities = () =>
    fetch('http://localhost:8000/api/ct/entities')
      .then(r => r.json())
      .then(d => setEntities(Array.isArray(d) ? d : []))
      .catch(() => {});

  const handleSave = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/profile/${member.id}?workspace_id=${workspace.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const d = await r.json();
      setProfile(d); setEditing(false);
    } finally { setSaving(false); }
  };

  const handleAddCompany = async (e) => {
    e.preventDefault();
    if (!addCoForm.entity_id) return;
    const selected = entities.find(en => String(en.id) === String(addCoForm.entity_id));
    await fetch(`${API}/companies/${member.id}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        entity_id:      parseInt(addCoForm.entity_id),
        entity_name:    selected?.name || '',
        role_in_company: addCoForm.role_in_company || null,
        start_date:     addCoForm.start_date || null,
      }),
    });
    setAddCoForm({ entity_id: '', role_in_company: '', start_date: '' });
    setShowAddCo(false); loadCompanies();
  };

  const handleRemoveCompany = async (linkId) => {
    if (!confirm('¿Desvincular empresa?')) return;
    await fetch(`${API}/companies/${member.id}/${linkId}`, { method: 'DELETE' });
    loadCompanies();
  };

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const statusColor = STATUS_OPTS.find(s => s.id === (profile?.status || 'active'))?.color || '#10B981';

  if (!profile) return <div style={S.loading}>CARGANDO PERFIL...</div>;

  return (
    <div style={S.root}>

      {/* ── ENCABEZADO: Avatar + nombre + estado ─────────────────── */}
      <div style={S.profileHeader}>
        <Avatar
          name={member?.name} avatarUrl={avatarUrl}
          userId={member?.id} workspaceId={workspace?.id}
          canEdit={canEdit}
          onUpdate={url => setAvatarUrl(url)}
        />
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <span style={S.sectionTitle}>FICHA PERSONAL</span>
            <span style={{ ...S.statusBadge, borderColor: statusColor, color: statusColor }}>
              {STATUS_OPTS.find(s => s.id === (profile.status || 'active'))?.label}
            </span>
            {profile.job_title && <span style={S.jobBadge}>◈ {profile.job_title}</span>}
          </div>
          <div style={{ color: '#64748b', fontSize: '11px', marginTop: '4px', fontFamily: '"IBM Plex Mono", monospace' }}>
            {member?.email || member?.name}
            {profile.department && ` · ${profile.department}`}
          </div>
        </div>
        {canEdit && (
          <div style={{ display: 'flex', gap: '8px' }}>
            {editing ? (
              <>
                <button style={S.btnSave} onClick={handleSave} disabled={saving}>{saving ? 'GUARDANDO...' : '✓ GUARDAR'}</button>
                <button style={S.btnCancel} onClick={() => { setEditing(false); setForm(profile); }}>CANCELAR</button>
              </>
            ) : (
              <button style={S.btnEdit} onClick={() => setEditing(true)}>✎ EDITAR</button>
            )}
          </div>
        )}
      </div>

      {/* ── BLOQUE 1: IDENTIFICACIÓN ─────────────────────────────── */}
      <Section title="IDENTIFICACIÓN" accent="#0EA5E9">
        <div style={S.grid3}>
          <Field label="CÉDULA / DOC. IDENTIDAD" value={form.cedula} editing={editing} onChange={v => set('cedula', v)} placeholder="1006374890" />
          <Field label="TELÉFONO" value={form.phone} editing={editing} onChange={v => set('phone', v)} placeholder="+57 313 577 293" />
          <Field label="CORREO LABORAL" value={form.email} editing={editing} onChange={v => set('email', v)} placeholder="nombre@empresa.com" />
          <Field label="FECHA DE NACIMIENTO" value={form.birth_date} type="date" editing={editing} onChange={v => set('birth_date', v)} />
          <Field label="ESTADO CIVIL" value={form.marital_status} editing={editing} onChange={v => set('marital_status', v)}
            type="select" options={MARITAL_OPTS} placeholder="Seleccionar..." />
          <Field label="NIVEL EDUCATIVO" value={form.education_level} editing={editing} onChange={v => set('education_level', v)}
            type="select" options={EDUCATION_OPTS} placeholder="Seleccionar..." />
        </div>
        <Field label="DIRECCIÓN" value={form.address} editing={editing} onChange={v => set('address', v)} placeholder="Calle 1 # 2-3" fullWidth />
        <div style={S.grid2}>
          <Field label="PAÍS" value={form.country} editing={editing} onChange={v => set('country', v)} placeholder="Colombia" />
          <Field label="CIUDAD" value={form.city} editing={editing} onChange={v => set('city', v)} placeholder="Bogotá" />
        </div>
      </Section>

      {/* ── BLOQUE 2: CARGO & ROL ─────────────────────────────────── */}
      <Section title="CARGO Y ROL EN LA EMPRESA" accent="#8B5CF6">
        <div style={S.grid2}>
          <Field label="CARGO / POSICIÓN" value={form.job_title} editing={editing} onChange={v => set('job_title', v)} placeholder="Ej: Gerente de Proyectos" />
          <Field label="DEPARTAMENTO / ÁREA" value={form.department} editing={editing} onChange={v => set('department', v)} placeholder="Ej: Tecnología" />
          <Field label="TIPO DE CONTRATO" value={form.contract_type} editing={editing} onChange={v => set('contract_type', v)}
            type="select" options={CONTRACT_TYPES} placeholder="Seleccionar..." />
          <Field label="FECHA DE INGRESO" value={form.hire_date} type="date" editing={editing} onChange={v => set('hire_date', v)} />
        </div>
        <Field label="ROL / FUNCIONES QUE DESEMPEÑA" value={form.role_description}
          type="textarea" editing={editing} onChange={v => set('role_description', v)}
          placeholder="Describe las funciones, responsabilidades y actividades principales del trabajador..." fullWidth />
        <Field label="HABILIDADES / COMPETENCIAS" value={form.skills} editing={editing} onChange={v => set('skills', v)}
          placeholder="Ej: Excel avanzado, AutoCAD, Gestión de proyectos, Licitaciones..." fullWidth />
      </Section>

      {/* ── BLOQUE 3: SEGURIDAD SOCIAL ──────────────────────────── */}
      <Section title="SEGURIDAD SOCIAL" accent="#10B981">
        <div style={S.grid3}>
          <Field label="EPS / ENTIDAD DE SALUD" value={form.eps} editing={editing} onChange={v => set('eps', v)} placeholder="Ej: Sura, Sanitas, Colmédica" />
          <Field label="FONDO DE PENSIONES" value={form.pension_fund} editing={editing} onChange={v => set('pension_fund', v)} placeholder="Ej: Porvenir, Protección" />
          <Field label="N° AFILIACIÓN / CÉDULA SS" value={form.social_security_no} editing={editing} onChange={v => set('social_security_no', v)} placeholder="N° de afiliación" />
        </div>
      </Section>

      {/* ── BLOQUE 4: CUENTA BANCARIA ─────────────────────────────── */}
      <Section title="CUENTA BANCARIA (NÓMINA)" accent="#F59E0B">
        <div style={S.grid3}>
          <Field label="BANCO" value={form.bank_name} editing={editing} onChange={v => set('bank_name', v)} placeholder="Ej: Bancolombia, Davivienda" />
          <Field label="TIPO DE CUENTA" value={form.bank_account_type} editing={editing} onChange={v => set('bank_account_type', v)}
            type="select" options={BANK_TYPES} placeholder="Seleccionar..." />
          <Field label="NÚMERO DE CUENTA" value={form.bank_account_number} editing={editing} onChange={v => set('bank_account_number', v)} placeholder="000-000000-00" />
        </div>
      </Section>

      {/* ── BLOQUE 5: DATOS ADICIONALES ──────────────────────────── */}
      <Section title="DATOS ADICIONALES" accent="#64748b">
        <Field label="CONTACTO DE EMERGENCIA" value={form.emergency_contact} editing={editing} onChange={v => set('emergency_contact', v)}
          placeholder="Nombre — Teléfono — Relación" fullWidth />
        {editing && (
          <div style={S.fieldWrap}>
            <label style={S.label}>ESTADO LABORAL</label>
            <div style={{ display: 'flex', gap: '8px' }}>
              {STATUS_OPTS.map(s => (
                <button key={s.id}
                  style={{ ...S.statusBtn, borderColor: form.status === s.id ? s.color : '#333', color: form.status === s.id ? s.color : '#64748b', background: form.status === s.id ? `${s.color}15` : 'transparent' }}
                  onClick={() => set('status', s.id)}>{s.label}</button>
              ))}
            </div>
          </div>
        )}
        <Field label="NOTAS INTERNAS (RRHH)" value={form.notes} type="textarea" editing={editing}
          onChange={v => set('notes', v)} placeholder="Observaciones del área de RRHH..." fullWidth />
      </Section>

      {/* ── EMPRESAS VINCULADAS ──────────────────────────────────── */}
      <div style={{ ...S.sectionHeader, marginTop: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ ...S.sectionTitle, color: '#0EA5E9' }}>EMPRESAS VINCULADAS</span>
          <span style={{ color: '#334155', fontSize: '10px', fontFamily: '"IBM Plex Mono", monospace' }}>
            {companies.length} empresa{companies.length !== 1 ? 's' : ''}
          </span>
        </div>
        {canEdit && (
          <button style={S.btnEdit} onClick={() => setShowAddCo(v => !v)}>
            {showAddCo ? 'CANCELAR' : '+ VINCULAR EMPRESA'}
          </button>
        )}
      </div>

      {showAddCo && canEdit && (
        <form style={S.addCoForm} onSubmit={handleAddCompany}>
          <div style={{ color: '#64748b', fontSize: '10px', letterSpacing: '1px', fontFamily: '"IBM Plex Mono", monospace', marginBottom: '4px' }}>
            Selecciona la entidad del Control Tower a la que pertenece este trabajador
          </div>
          <div style={S.grid3}>
            <div style={{ ...S.fieldWrap, gridColumn: '1 / -1' }}>
              <label style={S.label}>ENTIDAD / EMPRESA (CONTROL TOWER)</label>
              <select style={S.input} value={addCoForm.entity_id}
                onChange={e => setAddCoForm(f => ({ ...f, entity_id: e.target.value }))}>
                <option value="">Seleccionar entidad...</option>
                {entities.map(en => (
                  <option key={en.id} value={en.id}>
                    {en.level && en.level > 0 ? '  '.repeat(en.level - 1) + '└─ ' : ''}{en.name}
                  </option>
                ))}
              </select>
            </div>
            <div style={S.fieldWrap}>
              <label style={S.label}>ROL EN ESTA EMPRESA</label>
              <input style={S.input} placeholder="Ej: Director Técnico"
                value={addCoForm.role_in_company}
                onChange={e => setAddCoForm(f => ({ ...f, role_in_company: e.target.value }))} />
            </div>
            <div style={S.fieldWrap}>
              <label style={S.label}>FECHA DE INICIO</label>
              <input style={S.input} type="date" value={addCoForm.start_date}
                onChange={e => setAddCoForm(f => ({ ...f, start_date: e.target.value }))} />
            </div>
          </div>
          <button type="submit" style={S.btnSave}>◈ VINCULAR EMPRESA</button>
        </form>
      )}

      <div style={S.companiesList}>
        {companies.length === 0 && (
          <div style={S.companyEmpty}>
            Sin empresas vinculadas.
            {canEdit && <span style={{ color: '#1e3a5f' }}> Usa + VINCULAR EMPRESA para asignar.</span>}
          </div>
        )}
        {companies.map((co, i) => (
          <div key={co.id} style={{ ...S.companyCard, borderLeftColor: '#0EA5E9' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={S.companyDot} />
                <span style={S.companyName}>{co.entity_name}</span>
                {co.role_in_company && <span style={S.companyRole}>· {co.role_in_company}</span>}
              </div>
              {co.start_date && (
                <span style={S.companyMeta}>
                  Desde {new Date(co.start_date).toLocaleDateString('es-CO', { year: 'numeric', month: 'long' })}
                </span>
              )}
            </div>
            {canEdit && (
              <button style={S.removeBtn} onClick={() => handleRemoveCompany(co.id)} title="Desvincular">✕</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Section wrapper ───────────────────────────────────────────────────────────
function Section({ title, accent, children }) {
  return (
    <div style={S.section}>
      <div style={{ ...S.sectionHeader, borderBottomColor: `${accent}40` }}>
        <span style={{ ...S.sectionTitle, color: accent }}>{title}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', paddingTop: '4px' }}>
        {children}
      </div>
    </div>
  );
}

// ── Field component ───────────────────────────────────────────────────────────
function Field({ label, value, editing, onChange, type = 'text', placeholder = '', fullWidth = false, options = [] }) {
  const style = { ...(fullWidth ? { gridColumn: '1 / -1' } : {}) };
  return (
    <div style={{ ...S.fieldWrap, ...style }}>
      <label style={S.label}>{label}</label>
      {editing ? (
        type === 'textarea' ? (
          <textarea style={{ ...S.input, height: '80px', resize: 'vertical' }}
            value={value || ''} onChange={e => onChange(e.target.value)} placeholder={placeholder} />
        ) : type === 'select' ? (
          <select style={S.input} value={value || ''} onChange={e => onChange(e.target.value)}>
            <option value="">{placeholder}</option>
            {options.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        ) : (
          <input style={S.input} type={type} value={value || ''} onChange={e => onChange(e.target.value)} placeholder={placeholder} />
        )
      ) : (
        <span style={S.value}>{value || <span style={{ color: '#2a2a2a' }}>—</span>}</span>
      )}
    </div>
  );
}

// ── Estilos ───────────────────────────────────────────────────────────────────
const C  = { bg: '#0a0a0a', card: '#111', border: '#1e1e1e', text: '#e2e8f0', dim: '#64748b', accent: '#0EA5E9' };
const FF = '"IBM Plex Mono", monospace';

const S = {
  root:          { display: 'flex', flexDirection: 'column', gap: '0px', flex: 1, overflowY: 'auto', overflowX: 'hidden', fontFamily: FF },
  loading:       { color: C.dim, fontSize: '13px', padding: '24px', fontFamily: FF },
  profileHeader: { display: 'flex', alignItems: 'center', gap: '16px', padding: '16px', background: '#0d0d0d', borderBottom: `2px solid ${C.border}`, flexWrap: 'wrap' },
  jobBadge:      { color: '#64748b', fontSize: '10px', border: '1px solid #1e1e1e', padding: '2px 8px', letterSpacing: '0.5px' },
  section:       { padding: '14px 16px', borderBottom: `1px solid ${C.border}` },
  sectionHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${C.border}`, paddingBottom: '8px', marginBottom: '12px' },
  sectionTitle:  { color: C.accent, fontSize: '10px', letterSpacing: '2px', fontWeight: 700 },
  statusBadge:   { border: '1px solid', padding: '2px 8px', fontSize: '10px', letterSpacing: '1px' },
  grid2:         { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' },
  grid3:         { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '12px' },
  fieldWrap:     { display: 'flex', flexDirection: 'column', gap: '4px' },
  label:         { color: C.dim, fontSize: '9px', letterSpacing: '2px', fontWeight: 700 },
  value:         { color: C.text, fontSize: '13px', padding: '4px 0', lineHeight: 1.5 },
  input:         { background: '#111', border: `1px solid #2a2a2a`, color: C.text, padding: '8px 10px', fontSize: '12px', fontFamily: FF, outline: 'none', width: '100%', boxSizing: 'border-box' },
  statusBtn:     { flex: 1, padding: '7px', border: '2px solid', cursor: 'pointer', fontSize: '10px', letterSpacing: '1px', fontFamily: FF, transition: 'all .15s', background: 'transparent' },
  btnEdit:       { background: 'transparent', border: `1px solid ${C.border}`, color: C.dim, padding: '5px 12px', cursor: 'pointer', fontSize: '10px', letterSpacing: '1px', fontFamily: FF },
  btnSave:       { background: C.accent, border: 'none', color: '#000', padding: '7px 16px', cursor: 'pointer', fontSize: '11px', fontWeight: 700, letterSpacing: '1px', fontFamily: FF },
  btnCancel:     { background: 'transparent', border: `1px solid #333`, color: C.dim, padding: '6px 12px', cursor: 'pointer', fontSize: '11px', fontFamily: FF },
  addCoForm:     { background: '#0a0f0f', border: `1px solid #1a2a2a`, padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '12px', margin: '0 0 8px' },
  companiesList: { display: 'flex', flexDirection: 'column', gap: '4px', padding: '8px 16px 16px' },
  companyCard:   { display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px', background: '#0d0d0d', borderLeft: '3px solid #0EA5E9' },
  companyDot:    { width: '6px', height: '6px', background: C.accent, flexShrink: 0 },
  companyName:   { color: C.text, fontSize: '13px', fontWeight: 600, fontFamily: FF },
  companyRole:   { color: '#64748b', fontSize: '11px', fontFamily: FF },
  companyMeta:   { color: '#334155', fontSize: '10px', fontFamily: FF, paddingLeft: '14px' },
  companyEmpty:  { color: '#334155', fontSize: '12px', fontFamily: FF, fontStyle: 'italic', padding: '8px 0' },
  removeBtn:     { background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '14px', padding: '2px 6px', flexShrink: 0 },
};
