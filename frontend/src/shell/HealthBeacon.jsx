/* ============================================================
   HealthBeacon.jsx — Semáforo de diagnóstico del header (2026-09-08,
   pedido de Andrés: "cuando no cargan las cuentas, ¿es mi internet o
   Supabase? ¿cómo lo sé en el dashboard?").

   Sondea GET /api/health cada 30s (pausado con la pestaña oculta) y
   distingue TRES culpables, cada uno con su color:
     ● verde  — servidor y base de datos OK
     ⚠ ámbar — el servidor vive pero la BD (Supabase) falla
     ✖ rojo  — el servidor ni responde (o no hay internet)
   Al hacer clic: veredicto en español + chequeo del estado OFICIAL de
   Supabase (status.supabase.com, API pública con CORS) para separar
   "incidente del proveedor" de "problema de tu red/servidor".
   ============================================================ */
import { useState, useEffect, useRef, useCallback } from 'react';
import { API } from '../config';

const MONO = "'IBM Plex Mono', monospace";

async function sondearBackend() {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 6000);
  try {
    const r = await fetch(`${API}/health`, { signal: ctrl.signal, cache: 'no-store' });
    const d = await r.json();
    const db = String(d.db || '');
    if (db === 'connected') return { estado: 'ok', detalle: 'Servidor y base de datos respondiendo.' };
    return { estado: 'db', detalle: db.replace(/^error:\s*/i, '').slice(0, 160) };
  } catch {
    return {
      estado: 'down',
      detalle: navigator.onLine === false
        ? 'Tu computador está SIN INTERNET (ni siquiera hay red local).'
        : 'El servidor de FIN-SYS no responde (¿apagado o caído?).',
    };
  } finally {
    clearTimeout(t);
  }
}

async function sondearSupabase() {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 6000);
    const r = await fetch('https://status.supabase.com/api/v2/status.json',
      { signal: ctrl.signal, cache: 'no-store' });
    clearTimeout(t);
    const d = await r.json();
    return d?.status?.description || d?.status?.indicator || 'desconocido';
  } catch {
    return null;   // sin internet no se puede saber
  }
}

export default function HealthBeacon() {
  const [salud, setSalud] = useState({ estado: 'ok', detalle: '' });
  const [abierto, setAbierto] = useState(false);
  const [proveedor, setProveedor] = useState(undefined); // undefined=no consultado
  const [chequeando, setChequeando] = useState(false);
  const ref = useRef(null);

  const chequear = useCallback(async () => {
    setChequeando(true);
    const s = await sondearBackend();
    setSalud(s);
    if (s.estado !== 'ok') setProveedor(await sondearSupabase());
    setChequeando(false);
  }, []);

  useEffect(() => {
    chequear();
    const id = setInterval(() => {
      if (!document.hidden) chequear();
    }, 30000);
    return () => clearInterval(id);
  }, [chequear]);

  useEffect(() => {
    const fuera = (e) => { if (ref.current && !ref.current.contains(e.target)) setAbierto(false); };
    document.addEventListener('mousedown', fuera);
    return () => document.removeEventListener('mousedown', fuera);
  }, []);

  const C = {
    ok:   { color: '#00e676', icono: '●', label: 'OK' },
    db:   { color: '#FFB000', icono: '⚠', label: 'BD' },
    down: { color: '#ff1744', icono: '✖', label: 'SIN RED' },
  }[salud.estado] || { color: '#666', icono: '?', label: '?' };

  const supabaseCaido = proveedor && !/none|operational|All Systems/i.test(proveedor);

  let veredicto = null;
  if (salud.estado === 'db') {
    veredicto = proveedor === null
      ? 'No pude consultar el estado de Supabase (¿tu internet está fallando también?).'
      : supabaseCaido
        ? `🎯 CULPABLE: SUPABASE (el proveedor de la BD). Su estado oficial: "${proveedor}". No es tu app ni tu internet — solo hay que esperar; todo se recupera solo.`
        : `Supabase se reporta OK ("${proveedor || '—'}") → el problema está entre TU SERVIDOR y la BD (red del servidor, o un incidente que aún no publican). Si persiste 5+ min, avísale a Claude.`;
  } else if (salud.estado === 'down') {
    veredicto = navigator.onLine === false
      ? '🎯 CULPABLE: TU INTERNET. Revisa el wifi/módem.'
      : '🎯 CULPABLE: EL SERVIDOR de FIN-SYS (no responde). En local: arranca el backend. En producción: revisa el panel de Dokploy o dile a Claude "revive el servidor".';
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => { setAbierto(v => !v); if (!abierto) chequear(); }}
        title={salud.estado === 'ok'
          ? 'Sistema OK — clic para detalles'
          : 'Hay un problema — clic para el diagnóstico'}
        style={{
          display: 'flex', alignItems: 'center', gap: 4,
          background: salud.estado === 'ok' ? 'transparent' : '#1a1a1a',
          border: salud.estado === 'ok' ? 'none' : `1px solid ${C.color}`,
          color: C.color, cursor: 'pointer', padding: salud.estado === 'ok' ? 0 : '1px 6px',
          fontSize: 10, fontFamily: MONO, fontWeight: 700, lineHeight: 1.4,
        }}
      >
        <span style={{ fontSize: 9 }}>{C.icono}</span>
        {salud.estado !== 'ok' && <span style={{ fontSize: 8, letterSpacing: 1 }}>{C.label}</span>}
      </button>

      {abierto && (
        <div style={{
          position: 'absolute', right: 0, top: 'calc(100% + 4px)', width: 280,
          background: '#111', border: '2px solid #333', zIndex: 300,
          fontFamily: MONO, padding: 10, boxSizing: 'border-box',
        }}>
          <div style={{ fontSize: 9, fontWeight: 700, color: C.color, textTransform: 'uppercase', marginBottom: 6 }}>
            {C.icono} {salud.estado === 'ok' ? 'TODO EN ORDEN'
              : salud.estado === 'db' ? 'BASE DE DATOS CON PROBLEMAS' : 'SIN CONEXIÓN AL SERVIDOR'}
          </div>
          <div style={{ fontSize: 9, color: '#ccc', lineHeight: 1.5 }}>{salud.detalle}</div>
          {veredicto && (
            <div style={{ fontSize: 9, color: '#fff', lineHeight: 1.5, marginTop: 6,
                          borderTop: '1px solid #333', paddingTop: 6 }}>
              {veredicto}
            </div>
          )}
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <button onClick={chequear} disabled={chequeando}
              style={{ fontSize: 8, fontFamily: MONO, fontWeight: 700, textTransform: 'uppercase',
                       background: '#222', color: '#00e676', border: '1px solid #444',
                       padding: '3px 8px', cursor: 'pointer' }}>
              {chequeando ? '…' : '⟳ Reintentar'}
            </button>
            <a href="https://status.supabase.com" target="_blank" rel="noreferrer"
               style={{ fontSize: 8, fontFamily: MONO, fontWeight: 700, textTransform: 'uppercase',
                        background: '#222', color: '#4fc3f7', border: '1px solid #444',
                        padding: '3px 8px', textDecoration: 'none' }}>
              Estado de Supabase ↗
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
