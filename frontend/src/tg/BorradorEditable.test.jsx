/* Mini App (9-oct-2026): mensaje original, concepto y monto editables y
   «recordar el dato del SMS en la ficha» (al asignar o con 💾). */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TelegramTerceroApp from './TelegramTerceroApp.jsx';
import { parseMonto, describirMedio } from './BorradorEditable.jsx';

const respuesta = (status, body) =>
  Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });

const SESION = { id: 'u1', email: 'andres@finsys.os', name: 'Andrés', role: 'ADMIN', hubRole: 'owner',
                 initials: 'A', raw: { token: 'tok' } };
const SMS = 'Bancolombia: Compraste $12.100,00 en PARKING INTERNATIONA con tu T.Deb *1775, el 09/10/2026 a las 14:30.';
const BORRADOR = {
  id: 635, status: 'BORRADOR', channel: 'sms', portfolio_name: 'Negocio A', editable: true, raw_text: SMS,
  payload: { type: 'GASTO', amount: 12100, concept: 'Compra en PARKING INTERNATIONA con T.Deb *1775 (SMS)',
             transaction_date: '2026-10-09', payment_method: 'Bancolombia T.Deb 1775', portfolio_name: 'Negocio A',
             missing_fields: [],
             third_party: { identification_type: 'NIT', identification_number: '999999999', name: 'Sin especificar' },
             sms: { familia: 'compra_tarjeta', contraparte: 'PARKING INTERNATIONA',
                    medio: { tipo: 'nombre_banco', valor: 'PARKING INTERNATIONA' } } },
};
const TERCEROS = [
  { id: 40, name: 'Parking International SAS', identification_type: 'NIT', identification_number: '900123456',
    phone: '', email: '', address: '', website: '' },
];

function stubFetch(llamadas, { borrador = BORRADOR, medios = [], postMedio = 201 } = {}) {
  vi.stubGlobal('fetch', vi.fn((url, opts = {}) => {
    const metodo = opts.method || 'GET';
    const body = opts.body ? JSON.parse(opts.body) : null;
    llamadas.push([metodo, url, body]);
    if (url === `/api/bot/drafts/${borrador.id}` && metodo === 'GET') return respuesta(200, borrador);
    if (url === '/api/third-parties' && metodo === 'GET') return respuesta(200, TERCEROS);
    if (url.endsWith('/accounts') && metodo === 'GET') return respuesta(200, medios);
    if (url.endsWith('/accounts/mover') && metodo === 'POST') return respuesta(200, { status: 'MOVIDO', medios: [] });
    if (url.endsWith('/accounts') && metodo === 'POST') {
      return postMedio === 409 ? respuesta(409, { detail: '«PARKING INTERNATIONA» ya está registrado en la ficha de Otro.' })
        : respuesta(201, { status: 'CREADO', medio: { id: 1, ...body } });
    }
    if (url === `/api/bot/drafts/${borrador.id}` && metodo === 'PUT') {
      const { avisar_chat: _a, ...cambios } = body;
      const payload = { ...borrador.payload, ...cambios };
      if (cambios.third_party) payload.third_party = cambios.third_party;
      return respuesta(200, { ...borrador, payload, avisar_chat: true });
    }
    return respuesta(404, { detail: 'no' });
  }));
}

describe('parseMonto y describirMedio', () => {
  it('lee los montos como el bot', () => {
    expect(parseMonto('50000')).toBe(50000);
    expect(parseMonto('$50.000')).toBe(50000);
    expect(parseMonto('50.000,00')).toBe(50000);
    expect(parseMonto('12,100.00')).toBe(12100);
    expect(parseMonto('2,5')).toBe(2.5);
    expect(parseMonto('abc')).toBeNull();
    expect(parseMonto('0')).toBeNull();
    expect(parseMonto('')).toBeNull();
  });
  it('describe el medio como el bot', () => {
    expect(describirMedio({ tipo: 'nombre_banco', valor: 'DIDI' })).toBe('«DIDI»');
    expect(describirMedio({ tipo: 'cuenta', valor: '3193301184' })).toBe('cuenta *3193301184');
  });
});

describe('Mini App: completar el borrador', () => {
  let llamadas;
  beforeEach(() => {
    llamadas = [];
    window.history.replaceState({}, '', '/tg.html?draft=635');
    localStorage.clear();
    localStorage.setItem('finsys_session', JSON.stringify(SESION));
  });
  afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

  it('muestra el mensaje original completo del SMS', async () => {
    stubFetch(llamadas);
    render(<TelegramTerceroApp />);
    expect(await screen.findByText(/Mensaje original/)).toBeInTheDocument();
    expect(screen.getByText(SMS)).toBeInTheDocument();
  });

  it('guarda concepto y monto en el borrador y avisa al chat', async () => {
    stubFetch(llamadas);
    render(<TelegramTerceroApp />);
    await screen.findByText('Borrador #635');
    const boton = screen.getByRole('button', { name: 'Guardar concepto y monto' });
    expect(boton).toBeDisabled();                                   // sin cambios no hay nada que guardar
    fireEvent.change(screen.getByLabelText('Concepto'), { target: { value: 'Parqueadero obra Armenia' } });
    fireEvent.change(screen.getByLabelText('Monto'), { target: { value: '13.500' } });
    fireEvent.click(boton);
    await waitFor(() => expect(llamadas.some(([m, u]) => m === 'PUT' && u === '/api/bot/drafts/635')).toBe(true));
    const put = llamadas.find(([m, u]) => m === 'PUT' && u === '/api/bot/drafts/635');
    expect(put[2]).toEqual({ concept: 'Parqueadero obra Armenia', amount: 13500, avisar_chat: true });
    expect(await screen.findByText(/Guardado\. El bot te manda/)).toBeInTheDocument();
  });

  it('un monto ilegible no se envía', async () => {
    stubFetch(llamadas);
    render(<TelegramTerceroApp />);
    await screen.findByText('Borrador #635');
    fireEvent.change(screen.getByLabelText('Monto'), { target: { value: 'doce mil' } });
    expect(screen.getByRole('alert')).toHaveTextContent('Escribe solo el valor');
    expect(screen.getByRole('button', { name: 'Guardar concepto y monto' })).toBeDisabled();
  });

  it('al asignar con la casilla marcada guarda el nombre del banco en la ficha', async () => {
    stubFetch(llamadas);
    render(<TelegramTerceroApp />);
    await screen.findByText('Borrador #635');
    expect(screen.getByLabelText('Recordar el dato del SMS al asignar')).toBeChecked();
    fireEvent.change(screen.getByLabelText('Buscar tercero'), { target: { value: 'parking' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Asignar Parking International SAS' }));
    await waitFor(() => expect(llamadas.some(([m, u]) => m === 'POST' && u === '/api/third-parties/40/accounts')).toBe(true));
    const post = llamadas.find(([m, u]) => m === 'POST' && u === '/api/third-parties/40/accounts');
    expect(post[2]).toEqual({ tipo: 'nombre_banco', valor: 'PARKING INTERNATIONA' });
    expect(await screen.findByText(/quedó en su ficha/)).toBeInTheDocument();
  });

  it('con la casilla desmarcada no guarda nada en la ficha', async () => {
    stubFetch(llamadas);
    render(<TelegramTerceroApp />);
    await screen.findByText('Borrador #635');
    fireEvent.click(screen.getByLabelText('Recordar el dato del SMS al asignar'));
    fireEvent.change(screen.getByLabelText('Buscar tercero'), { target: { value: 'parking' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Asignar Parking International SAS' }));
    await screen.findByText(/Asignado: Parking International SAS/);
    expect(llamadas.some(([m, u]) => m === 'POST' && u.endsWith('/accounts'))).toBe(false);
  });

  it('con el tercero ya asignado ofrece 💾 y, si el dato es de otra ficha, moverlo', async () => {
    const asignado = { ...BORRADOR, payload: { ...BORRADOR.payload,
      third_party: { id: 40, identification_type: 'NIT', identification_number: '900123456', name: 'Parking International SAS' } } };
    stubFetch(llamadas, { borrador: asignado, postMedio: 409 });
    render(<TelegramTerceroApp />);
    fireEvent.click(await screen.findByRole('button', { name: /Recordar en la ficha de Parking/ }));
    expect(await screen.findByText(/ya está registrado en la ficha de Otro/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Moverlo a Parking/ }));
    await waitFor(() => expect(llamadas.some(([m, u]) => m === 'POST' && u === '/api/third-parties/40/accounts/mover')).toBe(true));
    expect(await screen.findByText(/ya está en la ficha de/)).toBeInTheDocument();
  });

  it('si la ficha ya tiene el dato solo lo confirma', async () => {
    const asignado = { ...BORRADOR, payload: { ...BORRADOR.payload,
      third_party: { id: 40, identification_type: 'NIT', identification_number: '900123456', name: 'Parking International SAS' } } };
    stubFetch(llamadas, { borrador: asignado, medios: [{ id: 1, tipo: 'nombre_banco', valor: 'PARKING INTERNATIONA' }] });
    render(<TelegramTerceroApp />);
    expect(await screen.findByText(/ya está en la ficha de/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Recordar en la ficha/ })).not.toBeInTheDocument();
  });

  it('crear tercero arranca con el nombre que escribe el banco', async () => {
    stubFetch(llamadas);
    render(<TelegramTerceroApp />);
    await screen.findByText('Borrador #635');
    fireEvent.click(screen.getByText('➕ Crear tercero nuevo'));
    expect(screen.getByLabelText('Nombre')).toHaveValue('PARKING INTERNATIONA');
  });
});
