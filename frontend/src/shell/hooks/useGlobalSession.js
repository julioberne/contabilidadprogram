/* useGlobalSession.js — Estado de sesión global del shell FIN-SYS OS */
import { useState, useCallback } from 'react';

const API = 'http://127.0.0.1:8000/api';

const DEMO_USER = {
  id:       1,
  email:    'andres@finsys.os',
  name:     'Andrés',
  role:     'ADMIN',
  initials: 'A',
};

export function useGlobalSession() {
  const [user,    setUser]    = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');

  const login = useCallback(async (email, password) => {
    setLoading(true);
    setError('');
    try {
      // Intentar autenticar contra la API del Hub (workspace_users)
      const res = await fetch(`${API}/hub/auth/login`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email, password }),
      });

      if (res.ok) {
        const data = await res.json();
        setUser({
          id:       data.user?.id || data.id,
          email:    data.user?.email || data.email || email,
          name:     data.user?.name || data.name || email.split('@')[0],
          role:     data.user?.is_superuser ? 'ADMIN' : 'USER',
          initials: (data.user?.name || email)[0].toUpperCase(),
          raw:      data,
        });
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

  const logout = useCallback(() => setUser(null), []);

  return { user, loading, error, login, logout };
}
