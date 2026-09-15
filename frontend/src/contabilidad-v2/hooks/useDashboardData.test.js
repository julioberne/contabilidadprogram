/* ============================================================
   useDashboardData.test.js — Plan cimientos A5 (2026-09-15)
   Mutaciones locales (prepend/patch/remove), páginas preservadas
   en el refresco, refreshBalance liviano y sondeo que respeta
   una mutación reciente. fetch mockeado: sin backend.
   ============================================================ */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useDashboardData } from './useDashboardData.js';

const tx = (id, extra = {}) => ({ id, type: 'GASTO', concept: `tx ${id}`, net_value: 10, ...extra });

function dashboardResponse(url) {
  const u = new URL(url, 'http://x');
  const limit = Number(u.searchParams.get('limit') || 50);
  const offset = Number(u.searchParams.get('offset') || 0);
  const all = Array.from({ length: 120 }, (_, i) => tx(120 - i));
  return {
    portfolios: [{ id: 1, name: 'Negocio A' }],
    balance: { total_ingresos: 5, patrimonio: 99 },
    transactions: all.slice(offset, offset + limit),
    total_tx_count: 120,
    accounts: [{ id: 1, name: 'Caja', currency: 'COP', current_balance: 1 }],
    profile: { name: 'A', email: '', role: '', avatar_style: '' },
    coa: { status: 'OK', data: [{ id: 1, code: '1', name: 'Activo', is_group: true, children: [{ id: 2, code: '11', name: 'Caja', is_group: false, children: [] }] }] },
  };
}

let llamadas;
function instalarFetch() {
  llamadas = [];
  globalThis.fetch = vi.fn(async (url) => {
    llamadas.push(String(url));
    const s = String(url);
    let body;
    if (s.includes('/dashboard-data/balance')) {
      body = { balance: { patrimonio: 123 }, accounts: [{ id: 1, name: 'Caja', current_balance: 2 }], total_tx_count: 121, portfolios: [] };
    } else if (s.includes('/dashboard-data')) {
      body = dashboardResponse(s);
    } else if (s.includes('/third-parties')) {
      body = [{ id: 7, name: 'Tercero' }];
    } else {
      body = {};
    }
    return { ok: true, json: async () => body };
  });
}

describe('useDashboardData (plan A5)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    instalarFetch();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('carga inicial: primera página, KPIs, cuentas y COA aplanado', async () => {
    const { result } = renderHook(() => useDashboardData('Negocio A'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.transactions).toHaveLength(50);
    expect(result.current.totalTxCount).toBe(120);
    expect(result.current.cajaViva.patrimonio).toBe(99);
    expect(result.current.coaFlatAccounts.map((n) => n.code)).toEqual(['11']);
    expect(llamadas[0]).toContain('portfolio=Negocio%20A');
    expect(llamadas[0]).toContain('limit=50');
  });

  it('prepend / patch / remove actualizan la lista sin pedir el dashboard', async () => {
    const { result } = renderHook(() => useDashboardData('Negocio A'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    const antes = llamadas.length;

    act(() => result.current.prependTransaction(tx(999, { concept: 'nueva' })));
    expect(result.current.transactions[0].id).toBe(999);
    expect(result.current.totalTxCount).toBe(121);

    act(() => result.current.patchTransaction(999, { note: 'ok' }));
    expect(result.current.transactions[0].note).toBe('ok');
    expect(result.current.transactions[0].concept).toBe('nueva');

    act(() => result.current.removeTransaction(999));
    expect(result.current.transactions.some((t) => t.id === 999)).toBe(false);
    expect(result.current.totalTxCount).toBe(120);

    // prepend duplicado reemplaza, no duplica
    act(() => result.current.prependTransaction(tx(120, { concept: 'reemplazada' })));
    expect(result.current.transactions.filter((t) => t.id === 120)).toHaveLength(1);
    expect(result.current.transactions.find((t) => t.id === 120).concept).toBe('reemplazada');

    expect(llamadas.length).toBe(antes);
  });

  it('refreshBalance pide solo /dashboard-data/balance y actualiza KPIs y cuentas', async () => {
    const { result } = renderHook(() => useDashboardData('Negocio A'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => { await result.current.refreshBalance(); });
    expect(llamadas.at(-1)).toContain('/dashboard-data/balance?portfolio=Negocio%20A');
    expect(result.current.cajaViva.patrimonio).toBe(123);
    expect(result.current.cajaViva.total_ingresos).toBe(5); // lo no enviado se conserva
    expect(result.current.accounts[0].current_balance).toBe(2);
    expect(result.current.totalTxCount).toBe(121);
  });

  it('fetchAll conserva las páginas cargadas con "Cargar más"', async () => {
    const { result } = renderHook(() => useDashboardData('Negocio A'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => { await result.current.loadMoreTransactions(50); });
    expect(result.current.transactions).toHaveLength(100);
    await act(async () => { await result.current.fetchAll(true); });
    expect(llamadas.at(-2)).toContain('limit=100');
    expect(result.current.transactions).toHaveLength(100);
  });

  it('el sondeo de 60 s se salta si hubo una mutación local reciente', async () => {
    const { result } = renderHook(() => useDashboardData('Negocio A'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    const base = llamadas.length;
    act(() => result.current.prependTransaction(tx(555)));
    await act(async () => { await vi.advanceTimersByTimeAsync(60000); });
    expect(llamadas.length).toBe(base);            // se saltó
    await act(async () => { await vi.advanceTimersByTimeAsync(60000); });
    expect(llamadas.length).toBeGreaterThan(base); // ya pasó el minuto: refresca
  });
});
