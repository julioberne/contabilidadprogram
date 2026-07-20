/* ============================================================
   useCalculator.test.js — Tests del hook de calculadora.
   Ejecutar: npm test
   ============================================================ */
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useCalculator from './useCalculator';

describe('useCalculator', () => {
  it('inicia con display "0" y cerrada', () => {
    const { result } = renderHook(() => useCalculator());
    expect(result.current.calcDisplay).toBe("0");
    expect(result.current.calcOpen).toBe(false);
  });

  it('acepta input numérico', () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.calcInput("5"));
    expect(result.current.calcDisplay).toBe("5");
    act(() => result.current.calcInput("3"));
    expect(result.current.calcDisplay).toBe("53");
  });

  it('reemplaza "0" inicial al ingresar dígito', () => {
    const { result } = renderHook(() => useCalculator());
    expect(result.current.calcDisplay).toBe("0");
    act(() => result.current.calcInput("7"));
    expect(result.current.calcDisplay).toBe("7");
  });

  it('suma correctamente', () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.calcInput("1"));
    act(() => result.current.calcInput("0"));
    act(() => result.current.calcSetOp("+"));
    act(() => result.current.calcInput("5"));
    act(() => result.current.calcExecute());
    expect(result.current.calcDisplay).toBe("15");
  });

  it('resta correctamente', () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.calcInput("2"));
    act(() => result.current.calcInput("0"));
    act(() => result.current.calcSetOp("-"));
    act(() => result.current.calcInput("8"));
    act(() => result.current.calcExecute());
    expect(result.current.calcDisplay).toBe("12");
  });

  it('multiplica correctamente', () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.calcInput("6"));
    act(() => result.current.calcSetOp("×"));
    act(() => result.current.calcInput("7"));
    act(() => result.current.calcExecute());
    expect(result.current.calcDisplay).toBe("42");
  });

  it('divide correctamente', () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.calcInput("2"));
    act(() => result.current.calcInput("0"));
    act(() => result.current.calcSetOp("÷"));
    act(() => result.current.calcInput("4"));
    act(() => result.current.calcExecute());
    expect(result.current.calcDisplay).toBe("5");
  });

  it('maneja división por cero', () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.calcInput("1"));
    act(() => result.current.calcInput("0"));
    act(() => result.current.calcSetOp("÷"));
    act(() => result.current.calcInput("0"));
    act(() => result.current.calcExecute());
    expect(result.current.calcDisplay).toBe("0");
  });

  it('clear resetea todo', () => {
    const { result } = renderHook(() => useCalculator());
    act(() => result.current.calcInput("9"));
    act(() => result.current.calcInput("9"));
    act(() => result.current.calcSetOp("+"));
    act(() => result.current.calcClear());
    expect(result.current.calcDisplay).toBe("0");
    expect(result.current.calcOp).toBe(null);
  });

  it('toggle open/close', () => {
    const { result } = renderHook(() => useCalculator());
    expect(result.current.calcOpen).toBe(false);
    act(() => result.current.setCalcOpen(true));
    expect(result.current.calcOpen).toBe(true);
  });
});
