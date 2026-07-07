/* ============================================================
   constants.js — Extracted from DocumentsTab.jsx
   Constants, URL helpers, and formatting utilities
   ============================================================ */
import { API_HR } from '../../../../../config';

const API    = API_HR;
const MAX_MB = 50;
const MAX_B  = MAX_MB * 1024 * 1024;
const SB_URL = 'https://sciorfjvdqxvcwgvnmbv.supabase.co';

// Genera URL pública correcta (bucket público)
const publicUrl = (path) => `${SB_URL}/storage/v1/object/public/hr-docs/${path}`;

// Descarga forzada via blob (evita el 404 de open-in-tab en Supabase)
const downloadFile = async (url, fileName) => {
  try {
    let blobUrl;
    if (url?.startsWith('data:')) {
      const comma = url.indexOf(',');
      const b64   = url.slice(comma + 1);
      const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      const blob  = new Blob([bytes], { type: 'text/html' });
      blobUrl = URL.createObjectURL(blob);
    } else {
      const res = await fetch(url);
      if (!res.ok) throw new Error('No se pudo descargar el archivo');
      const blob = await res.blob();
      blobUrl = URL.createObjectURL(blob);
    }
    const a    = document.createElement('a');
    a.href     = blobUrl;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(blobUrl); a.remove(); }, 1000);
  } catch (e) {
    window.open(url, '_blank');
  }
};

// Categorías por defecto (usadas como fallback si no hay BD)
const DEFAULT_CATEGORIES = [
  { id: 'contrato',     label: 'Contrato laboral',    color: '#0EA5E9' },
  { id: 'cedula',       label: 'Cédula / ID',          color: '#10B981' },
  { id: 'hoja_vida',    label: 'Hoja de vida',         color: '#8B5CF6' },
  { id: 'fotos',        label: 'Fotos',                color: '#F59E0B' },
  { id: 'clinico',      label: 'Historial clínico',    color: '#EF4444' },
  { id: 'certificados', label: 'Certificados',         color: '#06B6D4' },
  { id: 'nomina',       label: 'Desprendibles nómina', color: '#84CC16' },
  { id: 'financiero',   label: 'Info financiera',      color: '#F97316' },
  { id: 'paz_salvo',    label: 'Paz y salvos',         color: '#EC4899' },
  { id: 'cartas',       label: 'Cartas / Notas',       color: '#A78BFA' },
  { id: 'general',      label: 'General',              color: '#64748b' },
];
const FOLDER_COLORS = ['#0EA5E9','#10B981','#F59E0B','#EF4444','#8B5CF6','#F97316','#06B6D4','#64748b'];
const FILE_ICONS  = { 'application/pdf':'📄', 'image/jpeg':'🖼','image/jpg':'🖼','image/png':'🖼', 'application/vnd.ms-excel':'📊', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'📊', 'text/html':'📄', 'application/octet-stream':'📄', 'application/msword':'📝', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':'📝' };
const FILE_EXT    = { 'application/pdf':'PDF','image/jpeg':'JPG','image/jpg':'JPG','image/png':'PNG','application/vnd.ms-excel':'XLS','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'XLSX','text/html':'HTML','application/octet-stream':'FILE','application/msword':'DOC','application/vnd.openxmlformats-officedocument.wordprocessingml.document':'DOCX' };

// Estas funciones usan el array dinámico de categorías (reciben el array como parámetro)
const catLabelFrom = (cats, id) => cats.find(c => c.id === id)?.label || id;
const catColorFrom = (cats, id) => cats.find(c => c.id === id)?.color || '#64748b';
// Compatibilidad hacia atrás con funciones sin parámetro (usan DEFAULT)
const catLabel = id => DEFAULT_CATEGORIES.find(c => c.id === id)?.label || id;
const catColor = id => DEFAULT_CATEGORIES.find(c => c.id === id)?.color || '#64748b';
const fmtSize  = b => !b ? '—' : b < 1048576 ? `${(b/1024).toFixed(0)} KB` : `${(b/1048576).toFixed(1)} MB`;
const fmtDate  = s => s ? new Date(s).toLocaleDateString('es-CO',{day:'2-digit',month:'short',year:'numeric'}) : '—';

export {
  API, MAX_MB, MAX_B, SB_URL,
  publicUrl, downloadFile,
  DEFAULT_CATEGORIES, FOLDER_COLORS, FILE_ICONS, FILE_EXT,
  catLabelFrom, catColorFrom, catLabel, catColor,
  fmtSize, fmtDate,
};
