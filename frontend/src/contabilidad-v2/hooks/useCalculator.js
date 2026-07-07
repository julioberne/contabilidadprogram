import { useState, useCallback } from 'react';

export function useCalculator() {
  const [open, setOpen] = useState(false);
  const [display, setDisplay] = useState('0');
  const [prev, setPrev] = useState(null);
  const [op, setOp] = useState(null);
  const [shouldReset, setShouldReset] = useState(false);

  const input = useCallback((digit) => {
    setDisplay((cur) => {
      if (shouldReset || cur === '0') {
        setShouldReset(false);
        return String(digit);
      }
      return cur + String(digit);
    });
  }, [shouldReset]);

  const setOperation = useCallback((nextOp) => {
    setDisplay((cur) => {
      setPrev(parseFloat(cur) || 0);
      setOp(nextOp);
      setShouldReset(true);
      return cur;
    });
  }, []);

  const calculate = useCallback(() => {
    setDisplay((cur) => {
      const current = parseFloat(cur) || 0;
      if (prev == null || op == null) return cur;

      let result = 0;
      switch (op) {
        case '+': result = prev + current; break;
        case '-': result = prev - current; break;
        case '*': result = prev * current; break;
        case '/': result = current !== 0 ? prev / current : 0; break;
        default: result = current;
      }

      setPrev(null);
      setOp(null);
      setShouldReset(true);
      return String(result);
    });
  }, [prev, op]);

  const clear = useCallback(() => {
    setDisplay('0');
    setPrev(null);
    setOp(null);
    setShouldReset(false);
  }, []);

  const toggle = useCallback(() => {
    setOpen((v) => !v);
  }, []);

  const transferToAmount = useCallback(() => {
    return parseFloat(display) || 0;
  }, [display]);

  return {
    open,
    display,
    input,
    setOperation,
    calculate,
    clear,
    toggle,
    transferToAmount,
  };
}

export default useCalculator;
