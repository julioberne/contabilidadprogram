/* Medios de pago de un tercero (Bot IA, etapa 09.G §10): la sección de la
   ficha donde se ven y se registran las cuentas, celulares y llaves con las
   que el bot reconoce a un tercero en los SMS del banco. */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TerceroMediosPago from './TerceroMediosPago.jsx';

const respuesta = (status, body) =>
  Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });

describe('TerceroMediosPago', () => {
  let medios;
  let llamadas;

  beforeEach(() => {
    medios = [{ id: 1, tipo: 'celular', valor: '3213795458', banco: 'Nequi', etiqueta: null,
                origen: 'bot', descripcion: 'cel 3213795458' }];
    llamadas = [];
    vi.stubGlobal('fetch', vi.fn((url, opts = {}) => {
      const metodo = opts.method || 'GET';
      llamadas.push([metodo, url, opts.body ? JSON.parse(opts.body) : null]);
      if (metodo === 'GET') return respuesta(200, medios);
      if (metodo === 'DELETE') {
        medios = medios.filter(m => !url.endsWith(`/${m.id}`));
        return respuesta(200, { status: 'ELIMINADO' });
      }
      const cuerpo = JSON.parse(opts.body);
      if (url.endsWith('/mover')) {
        medios = [...medios, { id: 3, tipo: cuerpo.tipo, valor: cuerpo.valor, origen: 'web',
                               descripcion: `cuenta *${cuerpo.valor}` }];
        return respuesta(200, { status: 'MOVIDO' });
      }
      if (cuerpo.valor === '91232656625') {
        return respuesta(409, { detail: 'cuenta *91232656625 ya está registrado en la ficha de Ana.' });
      }
      if (cuerpo.valor === '123') {
        return respuesta(422, { detail: 'Valor inválido para celular: se espera 10 dígitos que empiezan por 3.' });
      }
      medios = [...medios, { id: 2, tipo: cuerpo.tipo, valor: cuerpo.valor, banco: cuerpo.banco,
                             origen: 'web', descripcion: cuerpo.valor }];
      return respuesta(201, { status: 'CREADO' });
    }));
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it('lista los medios de ESE tercero y muestra de dónde salió cada uno', async () => {
    render(<TerceroMediosPago terceroId={7} />);
    expect(await screen.findByText('3213795458')).toBeInTheDocument();
    expect(screen.getByText('· Nequi')).toBeInTheDocument();
    expect(screen.getByText('🤖 bot')).toBeInTheDocument();
    expect(llamadas[0][0]).toBe('GET');
    expect(llamadas[0][1]).toMatch(/\/third-parties\/7\/accounts$/);
  });

  it('sin medios explica cómo se registran', async () => {
    medios = [];
    render(<TerceroMediosPago terceroId={7} />);
    expect(await screen.findByText(/Sin medios de pago/)).toBeInTheDocument();
  });

  it('agrega un medio con su tipo y refresca la lista', async () => {
    render(<TerceroMediosPago terceroId={7} />);
    await screen.findByText('3213795458');
    fireEvent.change(screen.getByLabelText('Tipo de medio de pago'), { target: { value: 'llave' } });
    fireEvent.change(screen.getByLabelText('Valor del medio de pago'), { target: { value: ' 0087671656 ' } });
    fireEvent.click(screen.getByText('＋ Agregar'));
    expect(await screen.findByText('0087671656')).toBeInTheDocument();
    const post = llamadas.find(l => l[0] === 'POST');
    expect(post[2]).toEqual({ tipo: 'llave', valor: '0087671656', banco: null });
    expect(screen.getByLabelText('Valor del medio de pago')).toHaveValue('');
  });

  it('muestra el error de validación que responde el servidor', async () => {
    render(<TerceroMediosPago terceroId={7} />);
    await screen.findByText('3213795458');
    fireEvent.change(screen.getByLabelText('Valor del medio de pago'), { target: { value: '123' } });
    fireEvent.click(screen.getByText('＋ Agregar'));
    expect(await screen.findByRole('alert')).toHaveTextContent('10 dígitos');
    expect(screen.queryByText('Traerlo a esta ficha')).not.toBeInTheDocument();
  });

  it('si el medio ya es de otro tercero, ofrece traerlo aquí (decisión explícita)', async () => {
    render(<TerceroMediosPago terceroId={7} />);
    await screen.findByText('3213795458');
    fireEvent.change(screen.getByLabelText('Tipo de medio de pago'), { target: { value: 'cuenta' } });
    fireEvent.change(screen.getByLabelText('Valor del medio de pago'), { target: { value: '91232656625' } });
    fireEvent.click(screen.getByText('＋ Agregar'));
    expect(await screen.findByRole('alert')).toHaveTextContent('ficha de Ana');
    fireEvent.click(screen.getByText('Traerlo a esta ficha'));
    expect(await screen.findByText('91232656625')).toBeInTheDocument();
    const mover = llamadas.find(l => l[1].endsWith('/mover'));
    expect(mover[2]).toEqual({ tipo: 'cuenta', valor: '91232656625' });
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
  });

  it('quita un medio tras confirmar', async () => {
    render(<TerceroMediosPago terceroId={7} />);
    await screen.findByText('3213795458');
    fireEvent.click(screen.getByLabelText('Quitar cel 3213795458'));
    await waitFor(() => expect(screen.queryByText('3213795458')).not.toBeInTheDocument());
    expect(window.confirm).toHaveBeenCalled();
    expect(llamadas.some(l => l[0] === 'DELETE' && l[1].endsWith('/accounts/1'))).toBe(true);
  });

  it('al cambiar de tercero vuelve a cargar los suyos', async () => {
    const { rerender } = render(<TerceroMediosPago terceroId={7} />);
    await screen.findByText('3213795458');
    rerender(<TerceroMediosPago terceroId={8} />);
    await waitFor(() => expect(llamadas.some(l => l[1].endsWith('/third-parties/8/accounts'))).toBe(true));
  });
});
