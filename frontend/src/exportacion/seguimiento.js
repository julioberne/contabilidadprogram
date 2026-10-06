/* ============================================================
   seguimiento.js — 📈 Seguimiento del cliente (spec 13.6 §11):
   textos de cada evento, horas, cuánto tardó en abrirlo y el
   refresco "en vivo" (pausa con la pestaña oculta).
   ============================================================ */
import { useEffect } from 'react';

export const REFRESCO_PANEL_MS = 30000;
export const REFRESCO_SEGUIMIENTO_MS = 15000;

/** Qué hizo el cliente, en palabras. */
export function textoEvento(e) {
  const tx = e.concepto ? `"${e.concepto}"` : 'una transacción';
  switch (e.tipo) {
    case 'abrio': return 'abrió el compendio';
    case 'tx': return `abrió ${tx}`;
    case 'comprobante': return `vio el comprobante ${(Number(e.j) || 0) + 1} de ${tx}`;
    case 'pdf': return 'descargó el PDF';
    case 'html': return 'descargó el HTML offline';
    default: return String(e.tipo || '');
  }
}

/** "14:32" si es de hoy; "05/10 14:32" si no. */
export function horaCorta(iso, ahora = new Date()) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  const dos = (n) => String(n).padStart(2, '0');       // a mano: Intl varía entre navegadores ("5/10" vs "05/10")
  const hora = `${dos(d.getHours())}:${dos(d.getMinutes())}`;
  if (d.toDateString() === ahora.toDateString()) return hora;
  return `${dos(d.getDate())}/${dos(d.getMonth() + 1)} ${hora}`;
}

/** horas entre crear el compendio y la 1.ª apertura → "2 h después de crearlo". */
export function tardanza(horas) {
  if (horas == null) return null;
  if (horas < 1) return 'menos de 1 h después de crearlo';
  if (horas < 48) return `${Math.round(horas)} h después de crearlo`;
  return `${Math.round(horas / 24)} días después de crearlo`;
}

/** Llama a `cargar` ya y cada `ms` mientras la pestaña está visible; al volver a ella, refresca. */
export function useRefresco(cargar, ms) {
  useEffect(() => {
    cargar();
    const visible = () => typeof document === 'undefined' || document.visibilityState !== 'hidden';
    const id = setInterval(() => { if (visible()) cargar(); }, ms);
    const alVolver = () => { if (visible()) cargar(); };
    document.addEventListener('visibilitychange', alVolver);
    return () => { clearInterval(id); document.removeEventListener('visibilitychange', alVolver); };
  }, [cargar, ms]);
}
