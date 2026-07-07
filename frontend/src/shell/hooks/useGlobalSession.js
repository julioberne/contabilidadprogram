/* useGlobalSession.js — Estado de sesión global del shell FIN-SYS OS */
import { useState, useCallback, useEffect } from 'react';
import { API } from '../../config';

const SESSION_KEY = 'finsys_session';

const DEMO_USER = {
  id:       1,
  email:    'andres@finsys.os',
  name:     'Andrés',
  role:     'ADMIN',
  initials: 'A',
};

export function useGlobalSession() {
  // Restore session from localStorage on mount
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem(SESSION_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch { return null; }
  });
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  // Persist session to localStorage whenever user changes
  useEffect(() => {
    if (user) {
      localStorage.setItem(SESSION_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(SESSION_KEY);
    }
  }, [user]);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    setError('');
    try {
      // Intentar autenticar contra la API del Hub (hub_users)
      const res = await fetch(`${API}/hub/users/login`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email, password }),
      });

      if (res.ok) {
        const data = await res.json();
        const hubUser = data.user;
        setUser({
          id:       hubUser?.id || data.id,
          email:    hubUser?.email || data.email || email,
          name:     hubUser?.name || data.name || email.split('@')[0],
          role:     hubUser?.is_superuser ? 'ADMIN' : 'USER',
          initials: (hubUser?.name || email)[0].toUpperCase(),
          raw:      data,
        });
        // ── SSO: Propagate Hub session so ProjectHub finds its user ──
        if (hubUser) {
          localStorage.setItem('hub_user', JSON.stringify(hubUser));
        }
        return;
      }

      // Fallback: credenciales de App.jsx (sin auth real → demo user)
      if (email === 'andres@finsys.os' && password === 'admin123') {
        setUser({ ...DEMO_USER, email });
        return;
      }

      setError('Credenciales incorrectas. Verifica email y contraseña.');
    } catch (e) {
      // Si el backend no responde, permitir demo login
      if (email === 'andres@finsys.os' && password === 'admin123') {
        setUser(DEMO_USER);
      } else {
        setError('Sin conexión al servidor. Usa andres@finsys.os / admin123');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    // Clear all module sessions too (SSO cleanup)
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem('ct_session');
    localStorage.removeItem('hub_user');
    localStorage.removeItem('hub_workspace');
  }, []);

  return { user, loading, error, login, logout };
}
