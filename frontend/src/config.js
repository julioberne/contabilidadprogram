// frontend/src/config.js
// FIN-SYS OS — Configuración centralizada de API
// En desarrollo: http://127.0.0.1:8000/api (via .env.development)
// En producción: /api (mismo origen, Nginx proxya al backend)

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export const API = API_BASE;
export const API_CT = `${API_BASE}/ct`;
export const API_HUB = `${API_BASE}/hub`;
export const API_HR = `${API_BASE}/hr`;
export const API_CARTERA = `${API_BASE}/cartera`;

// Para URLs de uploads (archivos subidos)
// En dev: http://127.0.0.1:8000, en prod: '' (mismo origen)
export const UPLOADS_BASE = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace('/api', '')
  : '';

export default API_BASE;
