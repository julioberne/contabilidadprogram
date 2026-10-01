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
  { id: 12, name: 'Leidy Daniela Molina', identification_type: 'CC', identification_number: '1007289007', phone: '3213795458', email: '' },
  { id: 13, name: 'Pedro Pérez', identification_type: 'CC', identification_number: '555', phone: '', email: '' },
];

describe('TelegramTerceroApp', () => {
  let llamadas;

  beforeEach(() => {
    llamadas = [];
    window.history.replaceState({}, '', '/tg.html?draft=507');
    localStorage.clear();
    vi.stubGlobal('fetch', vi.fn((url, opts = {}) => {
      const metodo = opts.method || 'GET';
      llamadas.push([metodo, url, opts.body ? JSON.parse(opts.body) : null]);
      if (url === '/api/bot/drafts/507' && metodo === 'GET') return respuesta(200, BORRADOR);
      if (url === '/api/third-parties' && metodo === 'GET') return respuesta(200, TERCEROS);
      if (url.endsWith('/accounts') && metodo === 'GET') return respuesta(200, []);
      if (url === '/api/bot/drafts/507' && metodo === 'PUT') {
        const tp = JSON.parse(opts.body).third_party;
        return respuesta(200, { ...BORRADOR, payload: { ...BORRADOR.payload, third_party: tp }, avisar_chat: true });
      }
      return respuesta(404, { detail: 'no' });
    }));
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

    fireEvent.click(screen.getByText('Asignar'));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Asignado: Leidy Daniela Molina'));
    const put = llamadas.find(([m, u]) => m === 'PUT' && u === '/api/bot/drafts/507');
    expect(put[2]).toMatchObject({ avisar_chat: true, third_party: { id: 12, identification_number: '1007289007', name: 'Leidy Daniela Molina' } });
    // tras asignar se abre la ficha para completarla (cuentas, celulares, llaves)
    expect(await screen.findByText(/Ficha del tercero · #12/)).toBeInTheDocument();
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

  it('abre el formulario de crear con el celular del SMS prellenado', async () => {
    localStorage.setItem('finsys_session', JSON.stringify(SESION));
    render(<TelegramTerceroApp />);
    await screen.findByText('Borrador #507');
    fireEvent.click(screen.getByText('➕ Crear tercero nuevo'));
    expect(screen.getByLabelText('Teléfono')).toHaveValue('3213795458');
  });

  it('con un borrador ajeno o inexistente explica el error', async () => {
    localStorage.setItem('finsys_session', JSON.stringify(SESION));
    window.history.replaceState({}, '', '/tg.html?draft=999');
    render(<TelegramTerceroApp />);
    expect(await screen.findByRole('alert')).toHaveTextContent('no');
  });
});
