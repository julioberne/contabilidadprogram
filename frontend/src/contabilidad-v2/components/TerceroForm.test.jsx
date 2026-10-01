/* Alta de tercero compartida (etapa 09.I): los mismos campos de la web, con
   el 409 «ese documento ya pertenece a X» convertido en «Usar esa ficha». */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TerceroForm from './TerceroForm.jsx';

const respuesta = (status, body) =>
  Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });

describe('TerceroForm', () => {
  let llamadas;
  let siguiente;

  beforeEach(() => {
    llamadas = [];
    siguiente = respuesta(200, { id: 44, identification_type: 'CC', identification_number: 'SN-abc', provisional: true, status: 'CREADO' });
    vi.stubGlobal('fetch', vi.fn((url, opts = {}) => {
      llamadas.push([opts.method || 'GET', url, opts.body ? JSON.parse(opts.body) : null]);
      return siguiente;
    }));
  });
  afterEach(() => vi.unstubAllGlobals());

  it('exige el nombre y no llama a la API sin él', async () => {
    render(<TerceroForm />);
    fireEvent.click(screen.getByText('✓ Crear tercero'));
    expect(await screen.findByRole('alert')).toHaveTextContent('El nombre es obligatorio.');
    expect(llamadas).toEqual([]);
  });

  it('crea con los campos de la web y devuelve el tercero creado', async () => {
    const onCreado = vi.fn();
    render(<TerceroForm inicial={{ phone: '3213795458' }} onCreado={onCreado} />);
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: '  Leidy Molina ' } });
    fireEvent.click(screen.getByText('✓ Crear tercero'));
    await waitFor(() => expect(onCreado).toHaveBeenCalled());
    const [metodo, url, cuerpo] = llamadas[0];
    expect([metodo, url]).toEqual(['POST', '/api/third-parties']);
    expect(cuerpo).toMatchObject({ name: 'Leidy Molina', identification_type: 'CC', identification_number: '', phone: '3213795458' });
    expect(onCreado.mock.calls[0][0]).toMatchObject({ id: 44, name: 'Leidy Molina', identification_number: 'SN-abc', phone: '3213795458' });
  });

  it('con 409 muestra la ficha dueña del documento y ofrece usarla', async () => {
    const onUsar = vi.fn();
    const onCreado = vi.fn();
    siguiente = respuesta(409, { codigo: 'existe', detail: 'Ese documento ya pertenece a «Leidy Molina» (CC 1007289007).',
                                 tercero: { id: 12, name: 'Leidy Molina', identification_type: 'CC', identification_number: '1007289007' } });
    render(<TerceroForm onCreado={onCreado} onUsarExistente={onUsar} />);
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Leidy D' } });
    fireEvent.change(screen.getByLabelText('Número de documento'), { target: { value: '1007289007' } });
    fireEvent.click(screen.getByText('✓ Crear tercero'));
    expect(await screen.findByRole('status')).toHaveTextContent('ya pertenece a «Leidy Molina»');
    fireEvent.click(screen.getByText('Usar esa ficha'));
    expect(onUsar).toHaveBeenCalledWith(expect.objectContaining({ id: 12 }));
    expect(onCreado).not.toHaveBeenCalled();
  });

  it('muestra el error del servidor sin crear nada', async () => {
    const onCreado = vi.fn();
    siguiente = respuesta(500, { detail: 'se cayó la base' });
    render(<TerceroForm onCreado={onCreado} />);
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Ana' } });
    fireEvent.click(screen.getByText('✓ Crear tercero'));
    expect(await screen.findByRole('alert')).toHaveTextContent('se cayó la base');
    expect(onCreado).not.toHaveBeenCalled();
  });
});
