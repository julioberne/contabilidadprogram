/* lineasUtils.js — validación y payload de las líneas de un asiento
   (separado de LineasEditor.jsx para que el archivo solo exporte el
   componente: react-refresh/only-export-components). */
const num = (v) => (v === '' || v == null ? 0 : Number(v) || 0);

export function lineasValidas(lineas) {
  const con = (lineas || []).filter((l) => l.cuenta_codigo && (num(l.debito) || num(l.credito)));
  if (con.length < 2) return false;
  const td = con.reduce((s, l) => s + num(l.debito), 0);
  const tc = con.reduce((s, l) => s + num(l.credito), 0);
  return Math.round((td - tc) * 100) === 0;
}

export function lineasPayload(lineas) {
  return (lineas || [])
    .filter((l) => l.cuenta_codigo && (num(l.debito) || num(l.credito)))
    .map((l) => ({ cuenta_codigo: l.cuenta_codigo, cuenta_nombre: l.cuenta_nombre || '',
                   debito: num(l.debito), credito: num(l.credito) }));
}
