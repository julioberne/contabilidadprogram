/* Mini App de Telegram (etapa 09.I, v1): borrador + tercero en una pantalla,
   con la misma sesión y los mismos endpoints de la web. */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TelegramTerceroApp from './TelegramTerceroApp.jsx';

const respuesta = (status, body) =>
  Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });

const SESION = { id: 'u1', email: 'andres@finsys.os', name: 'Andrés', role: 'ADMIN', hubRole: 'owner',
                 initials: 'A', raw: { token: 'tok' } };

const BORRADOR = {
  id: 507, status: 'BORRADOR', channel: 'sms', portfolio_name: 'Negocio A', editable: true, chat_channel: 'telegram',
  payload: { type: 'GASTO', amount: 50000, concept: 'Transferencia Bancolombia (SMS)', transaction_date: '2026-09-30',
             payment_method: 'Bancolombia Ahorros 3037', portfolio_name: 'Negocio A',
             third_party: { identification_type: 'NIT', identification_number: '999999999', name: 'Sin especificar' },
             sms: { familia: 'transferencia', destino: '3213795458' } },
};
const TERCEROS = [
  { id: 12, name: 'Leidy Daniela Molina', identification_type: 'CC', identification_number: '1007289007', phone: '3213795458', email: '', address: 'Cra 5', website: '' },
  { id: 13, name: 'Pedro Pérez', identification_type: 'CC', identification_number: '555', phone: '', email: '', address: '', website: '' },
  { id: 14, name: 'Pedro Molano', identification_type: 'CC', identification_number: '556', phone: '', email: '', address: '', website: '' },
];

function stubFetch(llamadas, { borrador = BORRADOR, terceros = TERCEROS } = {}) {
  vi.stubGlobal('fetch', vi.fn((url, opts = {}) => {
    const metodo = opts.method || 'GET';
    llamadas.push([metodo, url, opts.body ? JSON.parse(opts.body) : null]);
    if (url === `/api/bot/drafts/${borrador.id}` && metodo === 'GET') return respuesta(200, borrador);
    if (url === '/api/third-parties' && metodo === 'GET') return respuesta(200, terceros);
    if (url.endsWith('/accounts') && metodo === 'GET') return respuesta(200, []);
    if (url.startsWith('/api/third-parties/') && metodo === 'PUT') return respuesta(200, { status: 'OK', updated: true });
    if (url === `/api/bot/drafts/${borrador.id}` && metodo === 'PUT') {
      const tp = JSON.parse(opts.body).third_party;
      return respuesta(200, { ...borrador, payload: { ...borrador.payload, third_party: tp }, avisar_chat: true });
    }
    return respuesta(404, { detail: 'no' });
  }));
}

describe('TelegramTerceroApp', () => {
  let llamadas;

  beforeEach(() => {
    llamadas = [];
    window.history.replaceState({}, '', '/tg.html?draft=507');
    localStorage.clear();
    stubFetch(llamadas);
  });
  afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

  it('sin sesión pide usuario y clave de la web', () => {
    render(<TelegramTerceroApp />);
    expect(screen.getByText('Entrar a FIN-SYS')).toBeInTheDocument();
    expect(llamadas).toEqual([]);
  });

  it('con sesión muestra el borrador, busca un tercero y lo asigna avisando al chat', async () => {
    localStorage.setItem('finsys_session', JSON.stringify(SESION));
    render(<TelegramTerceroApp />);
    expect(await screen.findByText('Borrador #507')).toBeInTheDocument();
    expect(screen.getByText(/50\.000/)).toBeInTheDocument();
    expect(screen.getByText(/destino 3213795458/)).toBeInTheDocument();
    expect(screen.getByText(/Sin tercero/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Buscar tercero'), { target: { value: 'leidy' } });
    expect(await screen.findByText('Leidy Daniela Molina')).toBeInTheDocument();
    expect(screen.queryByText('Pedro Pérez')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Asignar Leidy Daniela Molina' }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Asignado: Leidy Daniela Molina'));
    const put = llamadas.find(([m, u]) => m === 'PUT' && u === '/api/bot/drafts/507');
    expect(put[2]).toMatchObject({ avisar_chat: true, third_party: { id: 12, identification_number: '1007289007', name: 'Leidy Daniela Molina' } });
    // tras asignar se abre la ficha COMPLETA para completarla (cuentas, celulares, llaves)
    expect(await screen.findByText(/Ficha del tercero · #12/)).toBeInTheDocument();
    expect(screen.getByLabelText('Dirección')).toHaveValue('Cra 5');
  });

  it('guardar la ficha del tercero asignado vuelve a sincronizar el borrador', async () => {
    localStorage.setItem('finsys_session', JSON.stringify(SESION));
    render(<TelegramTerceroApp />);
    await screen.findByText('Borrador #507');
    fireEvent.change(screen.getByLabelText('Buscar tercero'), { target: { value: 'leidy' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Asignar Leidy Daniela Molina' }));
    await screen.findByText(/Ficha del tercero · #12/);
    llamadas.length = 0;
    fireEvent.change(screen.getByLabelText('Número de documento'), { target: { value: '1007289008' } });
    fireEvent.click(screen.getByText('✓ Guardar ficha'));
    await waitFor(() => expect(llamadas.some(([m, u]) => m === 'PUT' && u === '/api/bot/drafts/507')).toBe(true));
    const sync = llamadas.find(([m, u]) => m === 'PUT' && u === '/api/bot/drafts/507');
    expect(sync[2]).toMatchObject({ avisar_chat: true, third_party: { id: 12, identification_number: '1007289008' } });
  });

  it('con varios candidatos cada botón dice a quién asigna', async () => {
    localStorage.setItem('finsys_session', JSON.stringify(SESION));
    render(<TelegramTerceroApp />);
    await screen.findByText('Borrador #507');
    fireEvent.change(screen.getByLabelText('Buscar tercero'), { target: { value: 'pedro' } });
    expect(await screen.findByRole('button', { name: 'Asignar Pedro Pérez' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Asignar Pedro Molano' })).toBeInTheDocument();
  });

  it('busca también por documento o celular', async () => {
    localStorage.setItem('finsys_session', JSON.stringify(SESION));
    render(<TelegramTerceroApp />);
    await screen.findByText('Borrador #507');
    fireEvent.change(screen.getByLabelText('Buscar tercero'), { target: { value: '321379' } });
    expect(await screen.findByText('Leidy Daniela Molina')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Buscar tercero'), { target: { value: '555' } });
    expect(await screen.findByText('Pedro Pérez')).toBeInTheDocument();
  });

  it('crear nuevo prellena el celular del SMS y no pone dígitos como nombre', async () => {
    localStorage.setItem('finsys_session', JSON.stringify(SESION));
    render(<TelegramTerceroApp />);
    await screen.findByText('Borrador #507');
    fireEvent.change(screen.getByLabelText('Buscar tercero'), { target: { value: '3001112233' } });
    fireEvent.click(screen.getByText('➕ Crear tercero nuevo'));
    expect(screen.getByLabelText('Nombre')).toHaveValue('');
    expect(screen.getByLabelText('Teléfono')).toHaveValue('3213795458');
  });

  it('si el tercero asignado ya no está en la lista lo dice en vez de inventar una ficha', async () => {
    localStorage.setItem('finsys_session', JSON.stringify(SESION));
    const conAsignado = { ...BORRADOR, payload: { ...BORRADOR.payload,
      third_party: { id: 99, identification_type: 'CC', identification_number: '777', name: 'Fantasma' } } };
    stubFetch(llamadas, { borrador: conAsignado });
    render(<TelegramTerceroApp />);
    await screen.findByText('Borrador #507');
    expect(await screen.findByText(/ya no existe/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Ficha de Fantasma/ })).not.toBeInTheDocument();
  });

  it('con un borrador ajeno o inexistente explica el error', async () => {
    localStorage.setItem('finsys_session', JSON.stringify(SESION));
    window.history.replaceState({}, '', '/tg.html?draft=999');
    render(<TelegramTerceroApp />);
    expect(await screen.findByRole('alert')).toHaveTextContent('no');
  });
});
