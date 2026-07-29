/* ============================================================
   useRoute.js — Router mínimo de FIN-SYS OS
   Sin dependencias: History API + popstate.

   Las rutas se derivan del moduleRegistry (SSOT), así que
   agregar un módulo sigue siendo 1 sola entrada allí.

     /                → home
     /contabilidad    → módulo contabilidad
     /modulos         → panel de feature flags
     /<lo-que-sea>    → home (fallback)

   Nginx (nginx.conf:53) y server.py:149 ya sirven index.html
   para cualquier path, así que un F5 en /contabilidad funciona.
   ============================================================ */
import { useState, useEffect, useCallback } from 'react';
import modules from '../registry/moduleRegistry';

/** Vistas del shell que no son módulos del registry */
const SHELL_ROUTES = {
  'module-settings': 'modulos',
  'admin':           'admin',
  'mi-cuenta':       'mi-cuenta',
  'usuarios':        'usuarios',
};

/** view id → segmento de URL */
export function viewToPath(view) {
  if (!view || view === 'home') return '/';
  if (SHELL_ROUTES[view]) return `/${SHELL_ROUTES[view]}`;
  return `/${view}`;
}

/** segmento de URL → view id (fallback: home) */
export function pathToView(pathname) {
  const seg = (pathname || '/').split('/').filter(Boolean)[0];
  if (!seg) return 'home';

  const shellHit = Object.keys(SHELL_ROUTES).find(k => SHELL_ROUTES[k] === seg);
  if (shellHit) return shellHit;

  return modules.some(m => m.id === seg) ? seg : 'home';
}

/**
 * Estado de navegación sincronizado con la URL.
 * @returns {[string, (view: string, opts?: {replace?: boolean}) => void]}
 */
export function useRoute() {
  const [view, setView] = useState(() => pathToView(window.location.pathname));

  // Botón atrás/adelante del navegador
  useEffect(() => {
    const onPop = () => setView(pathToView(window.location.pathname));
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  // Normaliza la URL si se entró por un path desconocido (/foo → /)
  useEffect(() => {
    const canonical = viewToPath(pathToView(window.location.pathname));
    if (window.location.pathname !== canonical) {
      window.history.replaceState({ view }, '', canonical + window.location.search);
    }
    // Solo al montar: después, navigate() mantiene la URL en sync.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const navigate = useCallback((next, opts = {}) => {
    const path = viewToPath(next);
    // Al cambiar de módulo se descarta el query del módulo anterior
    const url = path + (opts.search || '');
    if (window.location.pathname + window.location.search !== url) {
      const method = opts.replace ? 'replaceState' : 'pushState';
      window.history[method]({ view: next }, '', url);
    }
    setView(next);
  }, []);

  return [view, navigate];
}

/**
 * Sub-estado de un módulo persistido en el query string.
 * Ej: useQueryParam('tab', 'terceros') → /contabilidad?tab=cuentas
 */
export function useQueryParam(key, fallback) {
  const read = () => new URLSearchParams(window.location.search).get(key) || fallback;
  const [value, setValue] = useState(read);

  useEffect(() => {
    const onPop = () => setValue(read());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, fallback]);

  const set = useCallback((next) => {
    const params = new URLSearchParams(window.location.search);
    if (next && next !== fallback) params.set(key, next);
    else params.delete(key);
    const qs = params.toString();
    window.history.replaceState(
      window.history.state, '',
      window.location.pathname + (qs ? `?${qs}` : '')
    );
    setValue(next);
  }, [key, fallback]);

  return [value, set];
}
