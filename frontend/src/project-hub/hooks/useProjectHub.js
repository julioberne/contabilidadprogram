/**
 * useProjectHub.js — Estado global del Project Hub
 * Maneja: sesión de usuario, workspace activo, proyecto activo
 */
import { useState, useCallback } from 'react';

const API = 'http://localhost:8000/api/hub';

// ─── Helpers localStorage ────────────────────────────────────────────────────
const getStored = (key) => { try { return JSON.parse(localStorage.getItem(key)); } catch { return null; } };
const setStored = (key, val) => localStorage.setItem(key, JSON.stringify(val));
const clearStored = () => { localStorage.removeItem('hub_user'); localStorage.removeItem('hub_workspace'); };

// ─── Hook principal ──────────────────────────────────────────────────────────
export function useProjectHub() {
  const [user,          setUser]          = useState(() => getStored('hub_user'));
  const [workspace,     setWorkspace]     = useState(() => getStored('hub_workspace'));
  const [workspaces,    setWorkspaces]    = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState(null);

  // ── Auth ───────────────────────────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/users/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Login fallido');
      const u = json.user;
      if (!u || !u.id) throw new Error('Respuesta de login inválida');
      setStored('hub_user', u);
      setUser(u);
      await loadWorkspacesForUser(u.id, u.is_superuser);
      return u;
    } catch (e) { setError(e.message); throw e; }
    finally { setLoading(false); }
  }, []);

  const register = useCallback(async (form) => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/users/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Registro fallido');
      const u = json.user;
      setStored('hub_user', u);
      setUser(u);
      await loadWorkspacesForUser(u.id, u.is_superuser);
      return u;
    } catch (e) { setError(e.message); throw e; }
    finally { setLoading(false); }
  }, []);

  const logout = useCallback(() => {
    clearStored();
    setUser(null); setWorkspace(null); setWorkspaces([]); setActiveProject(null);
  }, []);

  // ── Workspaces ─────────────────────────────────────────────────────────────
  // Carga los workspaces del usuario y selecciona el correcto
  const loadWorkspacesForUser = useCallback(async (userId, isSuperuser) => {
    if (!userId) return [];
    const url = isSuperuser
      ? `${API}/workspaces?all=true`
      : `${API}/workspaces?user_id=${userId}`;
    const res  = await fetch(url);
    const data = await res.json();
    const list = Array.isArray(data) ? data : [];
    setWorkspaces(list);

    if (list.length > 0) {
      // Intentar restaurar el workspace guardado, pero solo si pertenece al usuario
      const saved   = getStored('hub_workspace');
      const inList  = saved && list.find(w => w.id === saved.id);
      const active  = inList ? saved : list[list.length - 1]; // último = más reciente = con datos
      setStored('hub_workspace', active);
      setWorkspace(active);
    } else {
      // Sin workspaces: limpiar
      localStorage.removeItem('hub_workspace');
      setWorkspace(null);
    }
    return list;
  }, []);

  // Alias público para compatibilidad
  const loadWorkspaces = useCallback(async (userId, isSuperuser) => {
    return loadWorkspacesForUser(userId, isSuperuser);
  }, [loadWorkspacesForUser]);

  const switchWorkspace = useCallback((ws) => {
    setStored('hub_workspace', ws);
    setWorkspace(ws);
    setActiveProject(null);
  }, []);

  const createWorkspace = useCallback(async (form) => {
    const res = await fetch(`${API}/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    const json = await res.json();
    const ws   = json.workspace;
    setWorkspaces(prev => [...prev, ws]);
    switchWorkspace(ws);
    return ws;
  }, [switchWorkspace]);

  return {
    user, workspace, workspaces, activeProject, loading, error,
    login, register, logout,
    loadWorkspaces, switchWorkspace, createWorkspace,
    setActiveProject,
    API,
  };
}
