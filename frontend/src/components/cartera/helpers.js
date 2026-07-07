// helpers.js — Shared constants and utility functions for Cartera module

/**
 * getDueSemaforo — Semáforo de vencimiento
 * Returns dot emoji, label text, and CSS class based on days until due date.
 */
export function getDueSemaforo(dueDateStr, today) {
  if (!dueDateStr) return { dot: '⚪', label: '—', cls: 'text-gray-400' };
  const due = new Date(dueDateStr);
  const diffDays = Math.round((due - today) / 86400000);
  if (diffDays < 0) return { dot: '🔴', label: `${Math.abs(diffDays)}d vencido`, cls: 'text-red-600 font-bold' };
  if (diffDays <= 7) return { dot: '🟡', label: `${diffDays}d`, cls: 'text-amber-600 font-bold' };
  return { dot: '🟢', label: `${diffDays}d`, cls: 'text-green-700' };
}

/**
 * SORT_OPTIONS — Available sort options for the sort bar
 */
export const SORT_OPTIONS = [
  { key: 'urgente', icon: '🔥', label: 'Urgente' },
  { key: 'monto-desc', icon: '↓', label: 'Mayor $' },
  { key: 'monto-asc', icon: '↑', label: 'Menor $' },
  { key: 'reciente', icon: '🕐', label: 'Recientes' },
  { key: 'vence-prox', icon: '📅', label: 'Vence pronto' },
  { key: 'progreso', icon: '📊', label: '% Pagado' },
];

/**
 * sortFns — Sorting comparator functions keyed by sort option
 */
export const sortFns = {
  'urgente': (a, b) => {
    // VENCIDO first, then by due_date ascending (most urgent)
    const sp = { VENCIDO: 0, PENDIENTE: 1, PAGADO: 2 };
    const sa = sp[a.status] ?? 1, sb = sp[b.status] ?? 1;
    if (sa !== sb) return sa - sb;
    return new Date(a.due_date || '2099-01-01') - new Date(b.due_date || '2099-01-01');
  },
  'monto-desc': (a, b) => (b.original_amount || 0) - (a.original_amount || 0),
  'monto-asc': (a, b) => (a.original_amount || 0) - (b.original_amount || 0),
  'reciente': (a, b) => new Date(b.start_date || b.created_at || 0) - new Date(a.start_date || a.created_at || 0),
  'vence-prox': (a, b) => new Date(a.due_date || '2099-01-01') - new Date(b.due_date || '2099-01-01'),
  'progreso': (a, b) => {
    const pa = a.original_amount ? ((a.original_amount - (a.remaining_balance || 0)) / a.original_amount) : 0;
    const pb = b.original_amount ? ((b.original_amount - (b.remaining_balance || 0)) / b.original_amount) : 0;
    return pb - pa;
  },
};
