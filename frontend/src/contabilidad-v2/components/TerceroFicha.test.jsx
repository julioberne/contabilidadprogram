/* Ficha compartida del tercero (etapa 09.I): guardar conserva el SN- de un
   provisional si no se escribe documento, y un 409 ofrece «Usar esa ficha». */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TerceroFicha from './TerceroFicha.jsx';

const respuesta = (status, body) =>
  Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });

const PROVISIONAL = { id: 44, name: 'Leidy Molina', identification_type: 'CC', identification_number: 'SN-abc',
                      email: '', phone: '3213795458', address: 'Calle 1', website: '' };

describe('TerceroFicha', () => {
  let llamadas;
  let putRespuesta;

  beforeEach(() => {
    llamadas = [];
    putRespuesta = respuesta(200, { status: 'OK', updated: true });
    vi.stubGlobal('fetch', vi.fn((url, opts = {}) => {
      const metodo = opts.method || 'GET';
      llamadas.push([metodo, url, opts.body ? JSON.parse(opts.body) : null]);
      if (metodo === 'GET') return respuesta(200, []);          // medios de pago
      if (metodo === 'PUT') return putRespuesta;
      return respuesta(404, {});
    }));
  });
  afterEach(() => vi.unstubAllGlobals());

  it('un provisional sin documento escrito conserva su SN- al guardar', async () => {
    const onGuardado = vi.fn();
    render(<TerceroFicha tercero={PROVISIONAL} onGuardado={onGuardado} />);
    expect(screen.getByLabelText('Número de documento')).toHaveValue('');
    expect(screen.getByText(/Sin documento todavía/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Número de documento'), { target: { value: '12' } });
    fireEvent.change(screen.getByLabelText('Número de documento'), { target: { value: '' } });
    fireEvent.click(screen.getByText('✓ Guardar ficha'));
    await waitFor(() => expect(onGuardado).toHaveBeenCalled());
    const put = llamadas.find(([m]) => m === 'PUT');
    expect(put[1]).toBe('/api/third-parties/44');
    expect(put[2]).toMatchObject({ identification_number: 'SN-abc', address: 'Calle 1', name: 'Leidy Molina' });
  });

  it('formalizar el documento lo envía recortado y lo devuelve al llamador', async () => {
    const onGuardado = vi.fn();
    render(<TerceroFicha tercero={PROVISIONAL} onGuardado={onGuardado} />);
    fireEvent.change(screen.getByLabelText('Número de documento'), { target: { value: ' 1007289007 ' } });
    fireEvent.click(screen.getByText('✓ Guardar ficha'));
    await waitFor(() => expect(onGuardado).toHaveBeenCalled());
    expect(llamadas.find(([m]) => m === 'PUT')[2].identification_number).toBe('1007289007');
    expect(onGuardado.mock.calls[0][0]).toMatchObject({ id: 44, identification_number: '1007289007' });
  });

  it('con 409 muestra a quién pertenece el documento y ofrece usar esa ficha', async () => {
    const onUsar = vi.fn();
    const onGuardado = vi.fn();
    putRespuesta = respuesta(409, { codigo: 'existe', detail: 'Ese documento ya pertenece a «Ana» (CC 1).',
                                    tercero: { id: 9, name: 'Ana', identification_type: 'CC', identification_number: '1' } });
    render(<TerceroFicha tercero={PROVISIONAL} onGuardado={onGuardado} onUsarExistente={onUsar} />);
    fireEvent.change(screen.getByLabelText('Número de documento'), { target: { value: '1' } });
    fireEvent.click(screen.getByText('✓ Guardar ficha'));
    expect(await screen.findByRole('status')).toHaveTextContent('ya pertenece a «Ana»');
    fireEvent.click(screen.getByText('Usar esa ficha'));
    expect(onUsar).toHaveBeenCalledWith(expect.objectContaining({ id: 9 }));
    expect(onGuardado).not.toHaveBeenCalled();
  });

  it('un 404 (ficha borrada en paralelo) no se muestra como guardado', async () => {
    const onGuardado = vi.fn();
    putRespuesta = respuesta(404, { detail: 'Ese tercero ya no existe.' });
    render(<TerceroFicha tercero={PROVISIONAL} onGuardado={onGuardado} />);
    fireEvent.click(screen.getByText('✓ Guardar ficha'));
    expect(await screen.findByRole('alert')).toHaveTextContent('ya no existe');
    expect(onGuardado).not.toHaveBeenCalled();
  });
});
