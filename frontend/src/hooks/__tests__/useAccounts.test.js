/* ============================================================
   useAccounts.test.js — Tests del hook de cuentas financieras.
   Verifica estados iniciales y setters del CRUD.
   ============================================================ */
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useAccounts from '../useAccounts';

const mockFetchData = () => {};

describe('useAccounts', () => {
  it('inicia con array de cuentas vacío', () => {
    const { result } = renderHook(() => useAccounts({ fetchData: mockFetchData }));
    expect(result.current.accounts).toEqual([]);
  });

  it('permite setear cuentas', () => {
    const { result } = renderHook(() => useAccounts({ fetchData: mockFetchData }));
    const mockAccounts = [
      { id: 1, name: "Efectivo", type: "Ahorros", currency: "COP", current_balance: 100000 },
      { id: 2, name: "Bancolombia", type: "Corriente", currency: "COP", current_balance: 500000 },
    ];
    act(() => result.current.setAccounts(mockAccounts));
    expect(result.current.accounts).toHaveLength(2);
    expect(result.current.accounts[0].name).toBe("Efectivo");
  });

  it('campos de nueva cuenta inician vacíos', () => {
    const { result } = renderHook(() => useAccounts({ fetchData: mockFetchData }));
    expect(result.current.newAccountName).toBe("");
    expect(result.current.newAccountType).toBe("Ahorros");
    expect(result.current.newAccountCurrency).toBe("COP");
    expect(result.current.newAccountInitialBalance).toBe("");
  });

  it('permite editar campos de nueva cuenta', () => {
    const { result } = renderHook(() => useAccounts({ fetchData: mockFetchData }));
    act(() => result.current.setNewAccountName("Nequi"));
    act(() => result.current.setNewAccountType("Digital"));
    act(() => result.current.setNewAccountCurrency("USD"));
    act(() => result.current.setNewAccountInitialBalance("1000"));
    
    expect(result.current.newAccountName).toBe("Nequi");
    expect(result.current.newAccountType).toBe("Digital");
    expect(result.current.newAccountCurrency).toBe("USD");
    expect(result.current.newAccountInitialBalance).toBe("1000");
  });

  it('editingAccountId inicia null', () => {
    const { result } = renderHook(() => useAccounts({ fetchData: mockFetchData }));
    expect(result.current.editingAccountId).toBeNull();
  });

  it('permite activar modo edición', () => {
    const { result } = renderHook(() => useAccounts({ fetchData: mockFetchData }));
    act(() => {
      result.current.setEditingAccountId(3);
      result.current.setEditAccountName("Davivienda");
      result.current.setEditAccountType("Corriente");
      result.current.setEditAccountBalance("250000");
    });
    expect(result.current.editingAccountId).toBe(3);
    expect(result.current.editAccountName).toBe("Davivienda");
  });
});
