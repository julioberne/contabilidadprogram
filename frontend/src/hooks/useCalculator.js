/* ============================================================
   useCalculator.js — Calculadora rápida inline.
   Extraído de App.jsx (estados L132-136)
   ============================================================ */
import { useState } from 'react';

export default function useCalculator() {
  const [calcOpen, setCalcOpen] = useState(false);
  const [calcDisplay, setCalcDisplay] = useState("0");
  const [calcPrev, setCalcPrev] = useState(null);
  const [calcOp, setCalcOp] = useState(null);
  const [calcReset, setCalcReset] = useState(false);

  const calcInput = (val) => {
    if (calcReset) {
      setCalcDisplay(val);
      setCalcReset(false);
    } else {
      setCalcDisplay(prev => (prev === "0" ? val : prev + val));
    }
  };

  const calcSetOp = (op) => {
    setCalcPrev(parseFloat(calcDisplay));
    setCalcOp(op);
    setCalcReset(true);
  };

  const calcExecute = () => {
    if (calcPrev === null || !calcOp) return;
    const current = parseFloat(calcDisplay);
    let result;
    switch (calcOp) {
      case '+': result = calcPrev + current; break;
      case '-': result = calcPrev - current; break;
      case '×': result = calcPrev * current; break;
      case '÷': result = current !== 0 ? calcPrev / current : 0; break;
      default: result = current;
    }
    setCalcDisplay(String(result));
    setCalcPrev(null);
    setCalcOp(null);
    setCalcReset(true);
  };

  const calcClear = () => {
    setCalcDisplay("0");
    setCalcPrev(null);
    setCalcOp(null);
    setCalcReset(false);
  };

  return {
    calcOpen, setCalcOpen,
    calcDisplay, setCalcDisplay,
    calcPrev, setCalcPrev,
    calcOp, setCalcOp,
    calcReset, setCalcReset,
    calcInput,
    calcSetOp,
    calcExecute,
    calcClear,
  };
}
