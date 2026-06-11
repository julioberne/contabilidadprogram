// useControlTower.js
// Hook de estado global para el módulo Control Tower
import { useState, useEffect, useCallback } from 'react';

const CT_API = 'http://127.0.0.1:8000/api/ct';
const SESSION_KEY = 'ct_session';

export function useControlTower() {
  const [session, setSession] = useState(() => {
    try {
      const s = localStorage.getItem(SESSION_KEY);
      return s ? JSON.parse(s) : null;
    } catch { return null; }
  });

  const [entities, setEntities] = useState([]);
  const [activeEntity, setActiveEntity] = useState(null);
  const [breadcrumb, setBreadcrumb] = useState([]);
  const [kpis, setKpis] = useState(null);
  const [approvals, setApprovals] = useState([]);
  const [members, setMembers] = useState([]);
  const [resources, setResources] = useState([]);
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // ── Session ──────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${CT_API}/users/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      if (!res.ok) throw new Error('Credenciales inválidas');
      const data = await res.json();
      localStorage.setItem(SESSION_KEY, JSON.stringify(data.user));
      setSession(data.user);
      return { ok: true };
    } catch (e) {
      return { ok: false, message: e.message };
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (formData) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${CT_API}/users/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Error al registrar');
      }
      const data = await res.json();
      localStorage.setItem(SESSION_KEY, JSON.stringify(data.user));
      setSession(data.user);
      return { ok: true };
    } catch (e) {
      return { ok: false, message: e.message };
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(SESSION_KEY);
    setSession(null);
    setActiveEntity(null);
    setBreadcrumb([]);
    setKpis(null);
  }, []);

  // ── Entities ─────────────────────────────────────────────
  const fetchEntities = useCallback(async () => {
    try {
      const res = await fetch(`${CT_API}/entities`);
      const data = await res.json();
      setEntities(data);
    } catch (e) {
      console.error('Error cargando entidades:', e);
    }
  }, []);

  const createEntity = useCallback(async (entityData) => {
    const res = await fetch(`${CT_API}/entities`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(entityData)
    });
    if (!res.ok) throw new Error('Error creando entidad');
    await fetchEntities();
    return await res.json();
  }, [fetchEntities]);

  const deleteEntity = useCallback(async (entityId) => {
    await fetch(`${CT_API}/entities/${entityId}`, { method: 'DELETE' });
    await fetchEntities();
    if (activeEntity?.id === entityId) {
      setActiveEntity(null);
      setBreadcrumb([]);
      setKpis(null);
    }
  }, [fetchEntities, activeEntity]);

  // ── Set Active Entity & Build Breadcrumb ─────────────────
  const selectEntity = useCallback((entity, parentChain = []) => {
    setActiveEntity(entity);
    setBreadcrumb([...parentChain, entity]);
  }, []);

  // ── KPIs ─────────────────────────────────────────────────
  const fetchKpis = useCallback(async (entityId) => {
    if (!entityId) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${CT_API}/entities/${entityId}/kpis`);
      const data = await res.json();
      setKpis(data);
    } catch (e) {
      console.error('Error cargando KPIs:', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeEntity?.id) fetchKpis(activeEntity.id);
  }, [activeEntity, fetchKpis]);

  // ── Approvals ─────────────────────────────────────────────
  const fetchApprovals = useCallback(async (entityId = null) => {
    try {
      const url = entityId
        ? `${CT_API}/approvals?entity_id=${entityId}`
        : `${CT_API}/approvals`;
      const res = await fetch(url);
      setApprovals(await res.json());
    } catch (e) {
      console.error('Error cargando aprobaciones:', e);
    }
  }, []);

  const resolveApproval = useCallback(async (approvalId, status, notes = '') => {
    await fetch(`${CT_API}/approvals/${approvalId}/resolve`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, reviewer_id: session?.id || 1, notes })
    });
    await fetchApprovals(activeEntity?.id);
  }, [fetchApprovals, activeEntity, session]);

  const createApproval = useCallback(async (data) => {
    await fetch(`${CT_API}/approvals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...data, entity_id: activeEntity?.id, requested_by: session?.id })
    });
    await fetchApprovals(activeEntity?.id);
  }, [fetchApprovals, activeEntity, session]);

  // ── Resources ─────────────────────────────────────────────
  const fetchResources = useCallback(async (entityId) => {
    if (!entityId) return;
    try {
      const res = await fetch(`${CT_API}/entities/${entityId}/resources`);
      setResources(await res.json());
    } catch (e) { console.error(e); }
  }, []);

  const createResource = useCallback(async (data) => {
    await fetch(`${CT_API}/resources`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...data, entity_id: activeEntity?.id })
    });
    await fetchResources(activeEntity?.id);
  }, [fetchResources, activeEntity]);

  const deleteResource = useCallback(async (rid) => {
    await fetch(`${CT_API}/resources/${rid}`, { method: 'DELETE' });
    await fetchResources(activeEntity?.id);
  }, [fetchResources, activeEntity]);

  // ── Members ───────────────────────────────────────────────
  const fetchMembers = useCallback(async (entityId) => {
    if (!entityId) return;
    try {
      const res = await fetch(`${CT_API}/entities/${entityId}/members`);
      setMembers(await res.json());
    } catch (e) { console.error(e); }
  }, []);

  const fetchUsers = useCallback(async () => {
    try {
      const res = await fetch(`${CT_API}/users`);
      setUsers(await res.json());
    } catch (e) { console.error(e); }
  }, []);

  const inviteMember = useCallback(async (userId, roleLabel, permissions) => {
    await fetch(`${CT_API}/entities/${activeEntity.id}/members`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, role_label: roleLabel, permissions })
    });
    await fetchMembers(activeEntity.id);
  }, [fetchMembers, activeEntity]);

  // ── Quick Transaction ──────────────────────────────────────
  const quickTransaction = useCallback(async (txData) => {
    const res = await fetch(`${CT_API}/quick-transaction`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...txData, entity_id: activeEntity?.id || 1 })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Error en transacción');
    }
    return await res.json();
  }, [activeEntity]);

  // ── Side effects on entity change ─────────────────────────
  useEffect(() => {
    if (activeEntity?.id) {
      fetchApprovals(activeEntity.id);
      fetchResources(activeEntity.id);
      fetchMembers(activeEntity.id);
    }
  }, [activeEntity, fetchApprovals, fetchResources, fetchMembers]);

  // ── On mount ─────────────────────────────────────────────
  useEffect(() => {
    fetchEntities();
    fetchUsers();
    fetchApprovals();
  }, [fetchEntities, fetchUsers, fetchApprovals]);

  return {
    session, login, register, logout,
    entities, fetchEntities, createEntity, deleteEntity,
    activeEntity, selectEntity, breadcrumb,
    kpis, isLoading,
    approvals, resolveApproval, createApproval,
    resources, createResource, deleteResource,
    members, users, inviteMember,
    quickTransaction,
    error
  };
}
