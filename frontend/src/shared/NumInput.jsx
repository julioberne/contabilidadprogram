/* ============================================================
   NumInput.jsx — input numérico con puntuación es-CO en vivo
   Muestra "1.234.567,89" mientras se digita; emite el valor
   crudo ("1234567.89") con la MISMA forma de evento que un
   <input> nativo ({ target: { value } }), así el reemplazo de
   <input type="number"> es de una línea y el estado/backend no
   cambian. maxDecimals default 2 (dinero); subirlo para tasas.
   ============================================================ */
import { useState, useEffect } from 'react';

/* display "1.234.567,89" -> raw "1234567.89" (string, como e.target.value) */
export const toRaw = (display, maxDecimals = 2) => {
  let s = String(display ?? '').replace(/[^\d,.-]/g, '');
  const neg = s.startsWith('-') ? '-' : '';
  s = s.replace(/-/g, '').replace(/\./g, '');          // puntos = miles: fuera
  const firstComma = s.indexOf(',');
  let int = firstComma === -1 ? s : s.slice(0, firstComma);
  let dec = firstComma === -1 ? null : s.slice(firstComma + 1).replace(/,/g, '').slice(0, maxDecimals);
  int = int.replace(/\D/g, '').replace(/^0+(?=\d)/, '');
  if (int === '' && (dec === null || dec === '')) return neg === '-' ? '-' : '';
  return neg + (int || '0') + (dec !== null && dec !== '' ? '.' + dec : '');
};

/* raw "1234567.89" -> display "1.234.567,89". Conserva la coma final
   mientras el usuario está digitando los decimales. */
export const toDisplay = (raw, { trailingComma = false } = {}) => {
  if (raw === '' || raw === null || raw === undefined) return '';
  const s = String(raw);
  if (s === '-') return '-';   // el usuario apenas va a digitar un negativo
  const neg = s.startsWith('-') ? '-' : '';
  const [int = '', dec] = s.replace('-', '').split('.');
  const intFmt = (int || '0').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  if (dec !== undefined && dec !== '') return `${neg}${intFmt},${dec}`;
  return `${neg}${intFmt}${trailingComma ? ',' : ''}`;
};

export default function NumInput({ value, onChange, maxDecimals = 2, ...rest }) {
  const [display, setDisplay] = useState(() => toDisplay(value));

  /* Sincroniza cambios externos (reset del form, carga de datos) sin
     pisar lo que el usuario está digitando. */
  useEffect(() => {
    const rawActual = toRaw(display, maxDecimals);
    const rawExterno = value === null || value === undefined ? '' : String(value);
    if (Number(rawActual || 'x') !== Number(rawExterno || 'x') &&
        !(rawActual === '' && rawExterno === '')) {
      setDisplay(toDisplay(rawExterno));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const handleChange = (e) => {
    const text = e.target.value;
    const raw = toRaw(text, maxDecimals);
    const endsInComma = /,\s*$/.test(text) && maxDecimals > 0;
    setDisplay(toDisplay(raw, { trailingComma: endsInComma }));
    onChange?.({ target: { value: raw } });
  };

  return (
    <input
      type="text"
      inputMode="decimal"
      autoComplete="off"
      value={display}
      onChange={handleChange}
      {...rest}
    />
  );
}
