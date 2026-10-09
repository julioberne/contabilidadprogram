/* 📓 Bitácora del Bot IA (9-oct-2026): tabla literal de anomalías, filtros y «revisada». */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BotBitacoraPanel from './BotBitacoraPanel.jsx';
import BotApp from './BotApp.jsx';

const respuesta = (status, body) =>
  Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });

const TIPOS = { sms_traslado_sin_destino: 'Traslado entre cuentas sin cuenta destino (p. ej. ahorro a un bolsillo)',
                borrador_descartado: 'Borrador descartado' };
const ITEMS = [
  { id: 2, created_at: '2026-10-09T15:00:00+00:00', tipo: 'sms_traslado_sin_destino', canal: 'sms', draft_id: 640,
    detalle: 'ahorro_bolsillo: falta la cuenta destino (bolsillo «Personal»)', revisada: false,
    texto: 'Bancolombia: ANDRES, tu ahorro de $400.000 ya lo tienes en tu bolsillo Personal de tu cuenta de ahorros *3037',
    datos: { familia: 'ahorro_bolsillo' } },
  { id: 1, created_at: '2026-10-08T10:00:00+00:00', tipo: 'borrador_descartado', canal: 'telegram', draft_id: 575,
    detalle: 'Origen: telegram', revisada: true, texto: 'Compra comida peruana', datos: null },
];

function stub(llamadas, cuerpo = { disponible: true, dias: 30, tipos: TIPOS,
  resumen: { sms_traslado_sin_destino: { total: 1, abiertas: 1 }, borrador_descartado: { total: 1, abiertas: 0 } },
  items: ITEMS }) {
  vi.stubGlobal('fetch', vi.fn((url, opts = {}) => {
    const metodo = opts.method || 'GET';
    llamadas.push([metodo, url, opts.body ? JSON.parse(opts.body) : null]);
    if (url.startsWith('/api/bot/anomalias?') && metodo === 'GET') return respuesta(200, cuerpo);
    if (url.startsWith('/api/bot/anomalias/') && metodo === 'PUT') return respuesta(200, { id: 2, revisada: true });
    if (url.startsWith('/api/bot/drafts')) return respuesta(200, []);
    return respuesta(200, []);
  }));
}

describe('BotBitacoraPanel', () => {
  let llamadas;
  beforeEach(() => { llamadas = []; stub(llamadas); });
  afterEach(() => vi.unstubAllGlobals());

  it('muestra cada registro tal cual con su borrador y el texto original al abrirlo', async () => {
    render(<BotBitacoraPanel />);
    expect(await screen.findByText('ahorro_bolsillo: falta la cuenta destino (bolsillo «Personal»)')).toBeInTheDocument();
    expect(screen.getByText('#640')).toBeInTheDocument();
    expect(screen.getAllByText('Traslado sin destino').length).toBeGreaterThan(0);
    expect(llamadas[0][1]).toBe('/api/bot/anomalias?dias=30&estado=abiertas&tipo=');
    fireEvent.click(screen.getByRole('button', { name: 'Ver registro 2' }));
    expect(screen.getByText(/tu ahorro de \$400\.000 ya lo tienes en tu bolsillo Personal de tu cuenta de ahorros \*3037$/))
      .toBeInTheDocument();
  });

  it('filtra por tipo desde el resumen y por días', async () => {
    render(<BotBitacoraPanel />);
    await screen.findByText('#640');
    fireEvent.click(screen.getByRole('button', { name: /Traslado sin destino: 1 \/ 1/ }));
    await waitFor(() => expect(llamadas.at(-1)[1]).toContain('tipo=sms_traslado_sin_destino'));
    fireEvent.change(screen.getByLabelText('Días'), { target: { value: '7' } });
    await waitFor(() => expect(llamadas.at(-1)[1]).toContain('dias=7'));
  });

  it('marcar revisada hace PUT y recarga', async () => {
    render(<BotBitacoraPanel />);
    await screen.findByText('#640');
    fireEvent.click(screen.getByRole('button', { name: 'Marcar revisada' }));
    await waitFor(() => expect(llamadas.some(([m, u]) => m === 'PUT' && u === '/api/bot/anomalias/2')).toBe(true));
    const put = llamadas.find(([m]) => m === 'PUT');
    expect(put[2]).toEqual({ revisada: true });
  });

  it('antes del despliegue avisa que la bitácora aún no existe', async () => {
    stub(llamadas, { disponible: false, dias: 30, tipos: TIPOS, resumen: {}, items: [] });
    render(<BotBitacoraPanel />);
    expect(await screen.findByText(/se activa con el próximo despliegue/)).toBeInTheDocument();
  });
});

describe('BotApp', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('tiene las pestañas Borradores y Bitácora', async () => {
    const llamadas = [];
    stub(llamadas);
    render(<BotApp />);
    expect(screen.getByRole('tab', { name: '🗂 Borradores' })).toHaveAttribute('aria-selected', 'true');
    fireEvent.click(screen.getByRole('tab', { name: '📓 Bitácora' }));
    expect(await screen.findByText('📓 Bitácora del bot')).toBeInTheDocument();
  });
});
