/* ============================================================
   organizador.js — Lógica pura del organizador contable 📦 (13.5-b).
   Sin React ni red: formatos, árbol automático Empresa → Año → Mes,
   migas, parámetros de la lista y estado de vigencia. Con vitest.
   ============================================================ */

export const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
  'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
export const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

// Colores de carpeta propia (los mismos 8 que ofrece "+ Carpeta").
export const COLORES_CARPETA = ['#1d4ed8', '#0f766e', '#b45309', '#15803d', '#7c3aed', '#be123c', '#64748b', '#000000'];

export const EXT_SUBIBLES = ['pdf', 'png', 'jpg', 'jpeg', 'xlsx', 'csv'];

/** 3276800 → "3,1 MB" (coma decimal colombiana). */
export function formatoBytes(n) {
  const b = Number(n) || 0;
  if (b < 1024) return `${b} B`;
  const unidades = ['KB', 'MB', 'GB'];
  let v = b / 1024;
  let i = 0;
  while (v >= 1024 && i < unidades.length - 1) { v /= 1024; i += 1; }
  const txt = v >= 100 ? String(Math.round(v)) : v.toFixed(1).replace('.', ',').replace(/,0$/, '');
  return `${txt} ${unidades[i]}`;
}

/** Icono y extensión visibles a partir del MIME (y del nombre como respaldo). */
export function iconoArchivo(mime, nombre = '') {
  const m = String(mime || '').toLowerCase();
  if (m.includes('spreadsheetml')) return { icono: '📗', ext: 'XLSX' };
  if (m === 'application/pdf') return { icono: '📕', ext: 'PDF' };
  if (m === 'image/png') return { icono: '🖼', ext: 'PNG' };
  if (m === 'image/jpeg') return { icono: '🖼', ext: 'JPG' };
  if (m === 'text/csv') return { icono: '📄', ext: 'CSV' };
  const ext = String(nombre).split('.').pop();
  return { icono: '📄', ext: ext && ext !== nombre ? ext.toUpperCase() : '?' };
}

export const esTabla = (mime) => /spreadsheetml|text\/csv/.test(String(mime || ''));
export const esImagen = (mime) => /^image\//.test(String(mime || ''));
export const esPdf = (mime) => String(mime || '') === 'application/pdf';

function fecha(iso) {
  if (!iso) return null;
  const [a, m, d] = String(iso).slice(0, 10).split('-').map(Number);
  return a && m && d ? { a, m, d } : null;
}

const ultimoDia = (a, m) => new Date(Date.UTC(a, m, 0)).getUTCDate();
const dmy = (f) => `${String(f.d).padStart(2, '0')}/${String(f.m).padStart(2, '0')}/${f.a}`;

/** Igual que el backend: "sep 2026", "año 2026", "T3 2026" o el rango. */
export function etiquetaPeriodo(desde, hasta) {
  const h = fecha(hasta);
  if (!h) return 'sin período';
  const d = fecha(desde);
  if (d && d.d === 1 && h.d === ultimoDia(h.a, h.m)) {
    if (d.a === h.a && d.m === h.m) return `${MESES_CORTOS[h.m - 1]} ${h.a}`;
    if (d.a === h.a && d.m === 1 && h.m === 12) return `año ${h.a}`;
    if (d.a === h.a && d.m % 3 === 1 && h.m === d.m + 2) return `T${Math.floor((h.m + 2) / 3)} ${h.a}`;
  }
  return d ? `${dmy(d)} – ${dmy(h)}` : `hasta ${dmy(h)}`;
}

const COLOMBIA_MS = -5 * 3600 * 1000;   // UTC−5 fijo: Colombia no tiene horario de verano

/** "2026-10-05T09:30:00" → "05/10/2026 09:30". Si trae zona ("+00:00", "Z") se
    pasa a la hora de Colombia: la BD responde timestamptz en UTC. */
export function fechaHora(iso) {
  if (!iso) return '';
  let s = String(iso);
  if (s.length > 10 && /(Z|[+-]\d\d:?\d\d)$/i.test(s)) {
    const t = Date.parse(s);
    if (!Number.isNaN(t)) s = new Date(t + COLOMBIA_MS).toISOString();
  }
  const f = fecha(s);
  if (!f) return s;
  const hora = s.length > 10 ? s.slice(11, 16) : '';
  return `${dmy(f)}${hora ? ` ${hora}` : ''}`;
}

/** resumen.arbol (filas empresa/año/mes) → [{pid, empresa, n, anios:[{anio, n, meses:[{mes, n}]}]}].
    pid 0 = consolidado / sin empresa (portfolio_id null en la BD). */
export function armarArbol(arbol) {
  const empresas = new Map();
  (arbol || []).forEach((f) => {
    const pid = f.portfolio_id ?? 0;
    if (!empresas.has(pid)) {
      empresas.set(pid, { pid, empresa: f.empresa || (pid ? `Empresa ${pid}` : 'Consolidado'), n: 0, anios: new Map(), sinPeriodo: 0 });
    }
    const e = empresas.get(pid);
    const n = Number(f.n) || 0;
    e.n += n;
    if (f.anio == null) { e.sinPeriodo += n; return; }
    if (!e.anios.has(f.anio)) e.anios.set(f.anio, { anio: f.anio, n: 0, meses: [] });
    const a = e.anios.get(f.anio);
    a.n += n;
    if (f.mes != null) a.meses.push({ mes: f.mes, n });
  });
  return [...empresas.values()]
    .map((e) => ({
      ...e,
      anios: [...e.anios.values()]
        .map((a) => ({ ...a, meses: a.meses.sort((x, y) => y.mes - x.mes) }))
        .sort((x, y) => y.anio - x.anio),
    }))
    .sort((x, y) => (x.pid === 0) - (y.pid === 0) || x.empresa.localeCompare(y.empresa, 'es'));
}

/** Cadena de carpetas propias desde la raíz hasta `id` (para las migas). */
export function rutaCarpeta(carpetas, id) {
  const por = new Map((carpetas || []).map((c) => [c.id, c]));
  const ruta = [];
  const vistos = new Set();
  let actual = por.get(id);
  while (actual && !vistos.has(actual.id)) {
    vistos.add(actual.id);
    ruta.unshift(actual);
    actual = actual.parent_id != null ? por.get(actual.parent_id) : null;
  }
  return ruta;
}

export const subcarpetas = (carpetas, parentId) => (carpetas || [])
  .filter((c) => (c.parent_id ?? null) === (parentId ?? null));

/** Árbol de carpetas propias aplanado en orden de lectura: [{id, nombre, color, nivel}]. */
export function arbolPlano(carpetas) {
  const out = [];
  const visitar = (padre, nivel, vistos) => {
    subcarpetas(carpetas, padre)
      .slice()
      .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
      .forEach((c) => {
        if (vistos.has(c.id)) return;
        vistos.add(c.id);
        out.push({ id: c.id, nombre: c.nombre, color: c.color, nivel });
        visitar(c.id, nivel + 1, vistos);
      });
  };
  visitar(null, 0, new Set());
  return out;
}

/** Ids de `id` y todas sus subcarpetas (no se puede mover una carpeta dentro de ellas). */
export function descendientes(carpetas, id) {
  const fuera = new Set([id]);
  let crecio = true;
  while (crecio) {
    crecio = false;
    (carpetas || []).forEach((c) => {
      if (c.parent_id != null && fuera.has(c.parent_id) && !fuera.has(c.id)) { fuera.add(c.id); crecio = true; }
    });
  }
  return fuera;
}

/* ── Ubicación ─────────────────────────────────────────────────
   {nivel:'raiz'} · {nivel:'empresa', pid} · {nivel:'anio', pid, anio}
   · {nivel:'mes', pid, anio, mes} · {nivel:'carpeta', id}
   Filtro global (como las categorías de RRHH): {tipo} | {fijado} | {cambiaron} | {por_vencer}. */

export const RAIZ = { nivel: 'raiz' };

export function parametrosLista({ ubicacion = RAIZ, filtro = null, q = '' } = {}) {
  const texto = String(q || '').trim();
  if (texto) return { q: texto };
  if (filtro) return { ...filtro };
  const u = ubicacion || RAIZ;
  if (u.nivel === 'carpeta') return { folder_id: u.id };
  const p = {};
  if (u.nivel === 'empresa' || u.nivel === 'anio' || u.nivel === 'mes') p.portfolio_id = u.pid;
  if (u.nivel === 'anio' || u.nivel === 'mes') p.anio = u.anio;
  if (u.nivel === 'mes') p.mes = u.mes;
  return p;
}

/** {a:1, b:null, c:false, d:''} → "?a=1" (descarta vacíos y falsos). */
export function queryString(params) {
  const qs = Object.entries(params || {})
    .filter(([, v]) => v !== null && v !== undefined && v !== '' && v !== false)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v === true ? 'true' : v)}`)
    .join('&');
  return qs ? `?${qs}` : '';
}

const FILTROS = {
  fijado: '📌 Fijados', cambiaron: '⚠ Cambiaron', por_vencer: '⏳ Por vencer',
};

/** Migas clicables: [{etiqueta, ubicacion|null}] (la última es donde está). */
export function migas({ ubicacion = RAIZ, filtro = null, q = '', empresas = [], carpetas = [], tipos = [] } = {}) {
  const out = [{ etiqueta: 'Archivo', ubicacion: RAIZ }];
  const texto = String(q || '').trim();
  if (texto) return [...out, { etiqueta: `🔍 «${texto}»`, ubicacion: null }];
  if (filtro) {
    if (filtro.tipo != null) {
      const t = tipos.find((x) => x.id === filtro.tipo);
      return [...out, { etiqueta: t ? `${t.icono || '🏷'} ${t.nombre}` : 'Sin tipo', ubicacion: null }];
    }
    const k = Object.keys(filtro)[0];
    return [...out, { etiqueta: FILTROS[k] || k, ubicacion: null }];
  }
  const u = ubicacion || RAIZ;
  if (u.nivel === 'carpeta') {
    return [...out, ...rutaCarpeta(carpetas, u.id).map((c) => ({
      etiqueta: `📁 ${c.nombre}`, ubicacion: { nivel: 'carpeta', id: c.id },
    }))];
  }
  if (u.nivel === 'raiz') return out;
  const e = empresas.find((x) => x.pid === u.pid);
  out.push({ etiqueta: e ? e.empresa : (u.pid ? `Empresa ${u.pid}` : 'Consolidado'), ubicacion: { nivel: 'empresa', pid: u.pid } });
  if (u.nivel === 'anio' || u.nivel === 'mes') out.push({ etiqueta: String(u.anio), ubicacion: { nivel: 'anio', pid: u.pid, anio: u.anio } });
  if (u.nivel === 'mes') out.push({ etiqueta: `${String(u.mes).padStart(2, '0')} ${MESES[u.mes - 1]}`, ubicacion: u });
  return out;
}

/** Carpetas automáticas del nivel actual: [{clave, etiqueta, n, ubicacion}]. */
export function carpetasAutomaticas(ubicacion, empresas) {
  const u = ubicacion || RAIZ;
  if (u.nivel === 'raiz') {
    return empresas.map((e) => ({ clave: `e${e.pid}`, etiqueta: e.empresa, n: e.n, icono: e.pid ? '🏢' : '∑', ubicacion: { nivel: 'empresa', pid: e.pid } }));
  }
  const e = empresas.find((x) => x.pid === u.pid);
  if (!e) return [];
  if (u.nivel === 'empresa') {
    return e.anios.map((a) => ({ clave: `a${a.anio}`, etiqueta: String(a.anio), n: a.n, icono: '🗂', ubicacion: { nivel: 'anio', pid: u.pid, anio: a.anio } }));
  }
  if (u.nivel === 'anio') {
    const a = e.anios.find((x) => x.anio === u.anio);
    return (a?.meses || []).map((m) => ({
      clave: `m${m.mes}`, etiqueta: `${String(m.mes).padStart(2, '0')} ${MESES[m.mes - 1]}`, n: m.n, icono: '🗓',
      ubicacion: { nivel: 'mes', pid: u.pid, anio: u.anio, mes: m.mes },
    }));
  }
  return [];
}

/** Insignia de vigencia de un archivo (los subidos no tienen). */
export function estadoVigencia(item) {
  const v = item?.vigencia;
  if (!v) return null;
  if (v.estado === 'VIGENTE') return { icono: '✅', texto: 'VIGENTE', tono: 'ok', detalles: [] };
  if (v.estado === 'CAMBIO') return { icono: '⚠', texto: 'CAMBIÓ', tono: 'alerta', detalles: v.detalles || [] };
  return null;
}

/** Días que le quedan a un generado no fijado antes de la purga, solo si son ≤ aviso. */
export function diasParaVencer(item, hoy = new Date(), aviso = 15) {
  const f = fecha(item?.vence_el);
  if (!f || item?.fijado) return null;
  const h = Date.UTC(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
  const dias = Math.round((Date.UTC(f.a, f.m - 1, f.d) - h) / 86400000);
  return dias <= aviso ? Math.max(dias, 0) : null;
}

/** Período que propone "Subir" según dónde está el usuario (si no, el mes actual). */
export function periodoSugerido(ubicacion, hoy = new Date()) {
  const u = ubicacion || RAIZ;
  if (u.nivel === 'mes') return { anio: u.anio, mes: u.mes };
  if (u.nivel === 'anio') return { anio: u.anio, mes: '' };
  return { anio: hoy.getFullYear(), mes: hoy.getMonth() + 1 };
}

/** Valida en el navegador lo mismo que el backend (que igual decide por el contenido). */
export function validarSubida(file, maxMb = 10) {
  const ext = String(file?.name || '').split('.').pop().toLowerCase();
  if (!EXT_SUBIBLES.includes(ext)) return `«${file?.name}»: solo PDF, PNG, JPG, XLSX o CSV.`;
  if ((file?.size || 0) > maxMb * 1024 * 1024) return `«${file.name}» pesa ${formatoBytes(file.size)}; el tope es ${maxMb} MB.`;
  if (!file?.size) return `«${file?.name}» está vacío.`;
  return null;
}

/** filename* (UTF-8) o filename de un Content-Disposition. */
export function nombreDescarga(disposition, respaldo = 'archivo') {
  const s = String(disposition || '');
  const ext = /filename\*=UTF-8''([^;]+)/i.exec(s);
  if (ext) { try { return decodeURIComponent(ext[1].trim()); } catch { /* sigue */ } }
  const simple = /filename="?([^";]+)"?/i.exec(s);
  return simple ? simple[1].trim() : respaldo;
}

export const puedeBorrar = (user) => !!user && (user.is_superuser || ['owner', 'admin'].includes(String(user.role || '').toLowerCase()));
