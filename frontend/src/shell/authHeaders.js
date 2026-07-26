/* ============================================================
   authHeaders.js — Header Authorization para endpoints protegidos.
   El token lo emite POST /api/hub/users/login y queda dentro de
   la sesión que useGlobalSession persiste en localStorage.
   ============================================================ */

const SESSION_KEY = 'finsys_session';

/** Devuelve { Authorization } si hay sesión con token; {} si no. */
export function authHeaders() {
  try {
    const session = JSON.parse(localStorage.getItem(SESSION_KEY));
    const token = session?.raw?.token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}
