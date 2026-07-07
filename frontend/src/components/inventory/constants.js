// constants.js — Extracted from InventoryPanel.jsx
// ── Paleta brutalista ──────────────────────────────────────
export const COLORS = {
  black: '#000000',
  white: '#ffffff',
  bg: '#f5f5f0',
  bgAlt: '#eaeae4',
  green: '#00ff41',
  greenSoft: '#4ade80',
  amber: '#FFB000',
  crimson: '#dc2626',
  gray: '#888888',
  grayLight: '#cccccc',
  headerBg: '#1a1a1a',
  headerText: '#f0f0f0',
};

// ── Categorías y unidades ──────────────────────────────────
export const CATEGORIAS = ['General', 'Uniformes', 'Útiles', 'Alimentos', 'Material Didáctico'];
export const UNIDADES = ['unidad', 'kg', 'litro', 'caja'];

import { API as API_BASE_URL } from '../../config';
export { API_BASE_URL };

// ── Formato moneda COP ─────────────────────────────────────
export const fmtCOP = (v) => {
  if (v == null || isNaN(v)) return '$0';
  return '$' + Number(v).toLocaleString('es-CO', { maximumFractionDigits: 0 });
};
