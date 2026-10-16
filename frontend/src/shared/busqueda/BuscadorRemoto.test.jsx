/* Búsqueda remota única (estándar H3): contrato de URL, debounce, top-N y teclado. */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import BuscadorRemoto from './BuscadorRemoto.jsx';
import { urlBusqueda } from './useBusqueda.js';

const respuesta = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });

describe('urlBusqueda', () => {
  it('arma q, ids o ident y siempre un límite', () => {
    expect(urlBusqueda('terceros', 'café', { limite: 8 })).toBe('/api/buscar/terceros?q=caf%C3%A9&limite=8');
    expect(urlBusqueda('terceros', 'x', { ids: [3, 7] })).toBe('/api/buscar/terceros?ids=3%2C7&limite=8');
    expect(urlBusqueda('cuentas', '', { ident: '900' })).toBe('/api/buscar/cuentas?ident=900&limite=8');
  });
});

describe('BuscadorRemoto', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('no consulta con menos del mínimo; luego pide solo el top-N y avisa si hay más', async () => {
    const llamadas = [];
    vi.stubGlobal('fetch', vi.fn((url) => {
      llamadas.push(url);
      return respuesta({ items: [{ id: 1, name: 'Tatiana café', identification_type: 'CC', identification_number: '10' }], mas: true });
    }));
    const elegir = vi.fn();
    render(<BuscadorRemoto recurso="terceros" etiqueta="Buscar tercero" onElegir={elegir} />);
    const input = screen.getByRole('combobox', { name: 'Buscar tercero' });
    fireEvent.change(input, { target: { value: 'c' } });
    await new Promise((r) => setTimeout(r, 300));
    expect(llamadas).toEqual([]);                       // 1 carácter < mínimo 2
    fireEvent.change(input, { target: { value: 'ca' } });
    fireEvent.change(input, { target: { value: 'caf' } });
    await waitFor(() => expect(screen.getByRole('option')).toBeInTheDocument());
    expect(llamadas).toEqual(['/api/buscar/terceros?q=caf&limite=8']);   // debounce: una sola petición
    expect(screen.getByText(/escribe más para afinar/i)).toBeInTheDocument();
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(elegir).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }));
  });
});
