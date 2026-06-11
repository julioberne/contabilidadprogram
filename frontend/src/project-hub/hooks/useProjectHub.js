/**
 * useProjectHub.js — Estado global del Project Hub
 * Maneja: sesión de usuario, workspace activo, proyecto activo
 */
import { useState, useCallback } from 'react';

const API = 'http://localhost:8000/api/hub';

// ─── Hook principal ────────────────────────────────────────────────────────
export function useProjectHub() {
  const [user, setUser]               = useState(() => {
    try { return JSON.parse(localStorage.getItem('hub_user')); } catch { return null; }
  });
  const [workspace, setWorkspace]     = useState(() => {
    try { return JSON.parse(localStorage.getItem('hub_workspace')); } catch { return null; }
  });
  const [workspaces, setWorkspaces]   = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState(null);

  // ── Auth ──────────────────────────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/users/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Login fallido');
      const { user: u } = await res.json();
      localStorage.setItem('hub_user', JSON.stringify(u));
      setUser(u);
      await loadWorkspaces(u.id, u.is_superuser);
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
      if (!res.ok) throw new Error((await res.json()).detail || 'Registro fallido');
      const { user: u } = await res.json();
      localStorage.setItem('hub_user', JSON.stringify(u));
      setUser(u);
      await loadWorkspaces(u.id, u.is_superuser);
      return u;
    } catch (e) { setError(e.message); throw e; }
    finally { setLoading(false); }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('hub_user');
    localStorage.removeItem('hub_workspace');
    setUser(null); setWorkspace(null); setWorkspaces([]);
  }, []);

  // ── Workspaces ────────────────────────────────────────────────────────────
  const loadWorkspaces = useCallback(async (userId, isSuperuser) => {
    const url = isSuperuser
      ? `${API}/workspaces?all=true`
      : `${API}/workspaces?user_id=${userId}`;
    const res = await fetch(url);
    const data = await res.json();
    setWorkspaces(Array.isArray(data) ? data : []);
    if (data.length > 0) {
      const saved = JSON.parse(localStorage.getItem('hub_workspace'));
      const active = saved && data.find(w => w.id === saved.id) ? saved : data[0];
      localStorage.setItem('hub_workspace', JSON.stringify(active));
      setWorkspace(active);
    }
    return data;
  }, []);

  const switchWorkspace = useCallback((ws) => {
    localStorage.setItem('hub_workspace', JSON.stringify(ws));
    setWorkspace(ws);
    setActiveProject(null);
  }, []);

  const createWorkspace = useCallback(async (form) => {
    const res = await fetch(`${API}/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    const { workspace: ws } = await res.json();
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
