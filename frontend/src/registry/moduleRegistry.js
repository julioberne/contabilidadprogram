/* ============================================================
   moduleRegistry.js — Source of Truth de módulos FIN-SYS OS
   Agregar módulo = 1 entrada aquí. Sidebar, HomeDashboard y
   main.jsx consumen de este archivo automáticamente.
   ============================================================ */
import { lazy } from 'react';

const modules = [
  // ── INICIO ──
  { id: 'home', label: 'Home', icon: '⌂', group: 'INICIO',
    accent: 'green', active: true, order: 0,
    desc: '', showInLaunchpad: false },

  // ── FINANCIERO ──
  { id: 'contabilidad', label: 'Contabilidad', icon: '≡', group: 'FINANCIERO',
    accent: 'green', active: true, order: 1,
    desc: 'Transacciones · CoA · Balances\nPortafolios · Activos · IVA · GMF',
    // Módulo unificado: UI v1 sobre arquitectura modular (providers + adapters)
    component: lazy(() => import('../contabilidad-v2/ContabilidadApp.jsx')),
    wrapStyle: { minHeight: '100%', width: '100%' } },

  { id: 'contadores', label: 'Contadores', icon: '⊟', group: 'FINANCIERO',
    accent: 'green', active: true, order: 2,
    desc: 'Bandeja de asientos · Contabilizar\nPlan de cuentas · Reglas · Reportes · Cierres',
    // Módulo 12 (2026-09-15): visible solo para estos roles del hub. El
    // backend lo protege con require_contador; esto solo oculta la UI.
    roles: ['owner', 'admin', 'contador'],
    component: lazy(() => import('../contadores/ContadoresApp.jsx')),
    wrapStyle: { minHeight: '100%', width: '100%' } },

  { id: 'tesoreria', label: 'Tesorería', icon: '⊕', group: 'FINANCIERO',
    accent: 'green', active: false, order: 3 },

  { id: 'facturacion', label: 'Facturación', icon: '▦', group: 'FINANCIERO',
    accent: 'green', active: false, order: 4 },

  // ── GESTIÓN ──
  { id: 'rrhh', label: 'RRHH', icon: '⊙', group: 'GESTIÓN',
    accent: 'blue', active: true, order: 5,
    desc: 'Empleados · Nómina · Documentos\nHistorial · Perfiles · Empresas',
    component: lazy(() => import('../project-hub/ProjectHubApp.jsx')),
    noScroll: true,
    wrapStyle: { height: '100%', position: 'relative', overflow: 'hidden' },
    extraProps: { embeddedMode: true, onExit: '__SET_HOME__' } },

  { id: 'tower', label: 'Control Tower', icon: '⬡', group: 'GESTIÓN',
    accent: 'amber', active: true, order: 6,
    desc: 'Holding · Empresas · Balance\nConsolidado · Árbol Corporativo',
    component: lazy(() => import('../control-tower/ControlTowerApp.jsx')),
    noScroll: true,
    wrapStyle: { height: '100%', display: 'flex', flexDirection: 'column' },
    extraProps: { embeddedMode: true, onGoBack: '__SET_HOME__' } },

  { id: 'organigrama', label: 'Organigrama', icon: '⊞', group: 'GESTIÓN',
    accent: 'green', active: false, order: 7 },

  // ── OPERACIONES ──
  { id: 'ventas', label: 'Ventas & CRM', icon: '◈', group: 'OPERACIONES',
    accent: 'green', active: false, order: 8,
    desc: 'CRM · Cotizaciones · Facturas\nPipeline · Comisiones · Metas' },

  { id: 'compras', label: 'Compras', icon: '⊡', group: 'OPERACIONES',
    accent: 'green', active: false, order: 9,
    desc: 'Proveedores · POs · CxP\nRecepciones · Evaluaciones' },

  { id: 'logistica', label: 'Logística', icon: '⊜', group: 'OPERACIONES',
    accent: 'green', active: false, order: 10 },

  { id: 'bot', label: 'Bot IA', icon: '◉', group: 'OPERACIONES',
    accent: 'green', active: false, order: 11,
    desc: 'Bandeja de borradores · Telegram\nVoz · Estructuración · Confirmación',
    // Etapa C: bandeja de borradores. El flag remoto 'bot' lo enciende.
    component: lazy(() => import('../bot/BotApp.jsx')),
    wrapStyle: { minHeight: '100%', width: '100%' } },

  // ── SISTEMA ──
  { id: 'config', label: 'Configuración', icon: '⚙', group: 'SISTEMA',
    accent: 'green', active: false, order: 12 },

  { id: 'auditoria', label: 'Auditoría', icon: '◎', group: 'SISTEMA',
    accent: 'green', active: false, order: 13 },
];

export default modules;

// ── Helpers derivados ──

/**
 * Rol del hub del usuario en sesión (owner|admin|member|viewer|contador) y
 * si es superusuario. Se lee de la sesión persistida (misma fuente que
 * shell/authHeaders.js) para que Sidebar/Home/main.jsx no cambien de firma.
 */
function sesionActual() {
  try {
    const s = JSON.parse(localStorage.getItem('finsys_session'));
    const hubUser = s?.raw?.user || {};
    return {
      role: (s?.hubRole || hubUser.role || 'member').toLowerCase(),
      su: !!(hubUser.is_superuser),
    };
  } catch {
    return { role: 'member', su: false };
  }
}

/** ¿El módulo es visible para el rol en sesión? (sin `roles` = para todos) */
function visiblePorRol(m) {
  if (!m.roles || !m.roles.length) return true;
  const { role, su } = sesionActual();
  return su || m.roles.includes(role);
}

/**
 * Aplica feature flags remotos sobre el registry local.
 * Retorna un Set de module_ids que están habilitados.
 * @param {Array} flags — [{module_id, enabled}, ...]
 * @returns {Set<string>} — IDs de módulos habilitados
 */
export function applyFlags(flags = []) {
  // Empezar con los módulos activos por defecto del registry
  const enabled = new Set(modules.filter(m => m.active).map(m => m.id));
  
  // Aplicar overrides de flags remotos
  flags.forEach(f => {
    if (f.enabled) {
      enabled.add(f.module_id);
    } else {
      enabled.delete(f.module_id);
    }
  });

  // Home siempre visible
  enabled.add('home');
  return enabled;
}

/** Módulos agrupados por grupo (para Sidebar) */
export function getNavGroups(enabledIds = null) {
  const groups = {};
  modules.filter(visiblePorRol).forEach(m => {
    if (!groups[m.group]) groups[m.group] = { group: m.group, items: [] };
    const isActive = enabledIds ? enabledIds.has(m.id) : m.active;
    groups[m.group].items.push({
      id: m.id, icon: m.icon, label: m.label,
      accent: m.accent, soon: !isActive && m.id !== 'home',
    });
  });
  return Object.values(groups);
}

/** Módulos para el launchpad (HomeDashboard) */
export function getLaunchpadModules(enabledIds = null) {
  return modules
    .filter(m => m.desc && m.id !== 'home' && visiblePorRol(m))
    .map(m => ({
      id: m.id, icon: m.icon, name: m.label,
      desc: m.desc, accent: m.accent,
      active: enabledIds ? enabledIds.has(m.id) : m.active,
    }));
}

/** Mapa id → label (para breadcrumbs) */
export function getModuleLabels() {
  return Object.fromEntries(modules.map(m => [m.id, m.label]));
}

/** IDs de módulos que necesitan overflow:hidden */
export function getNoScrollIds() {
  return modules.filter(m => m.noScroll).map(m => m.id);
}

/** Módulos renderizables (con componente + habilitados) */
export function getRenderableModules(enabledIds = null) {
  return modules.filter(m => {
    if (!m.component || !visiblePorRol(m)) return false;
    return enabledIds ? enabledIds.has(m.id) : m.active;
  });
}

