/* 🏷️ Etiquetas en la Mini App (24-oct-2026): fichas, búsqueda en el servidor, crear y guardar. */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import EtiquetasBorrador from './EtiquetasBorrador.jsx';

const respuesta = (status, body) =>
  Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });

const TODAS = ['Bonaire obra', 'Casa Armenia', 'Comida', 'Oficina', 'Operativo', 'Recurrente'];
const DRAFT = { id: 635, editable: true, status: 'BORRADOR', payload: { tags: ['Comida'] } };

function stub(llamadas) {
  vi.stubGlobal('fetch', vi.fn((url, opts = {}) => {
    const metodo = opts.method || 'GET';
    const body = opts.body ? JSON.parse(opts.body) : null;
    llamadas.push([metodo, url, body]);
    if (url.startsWith('/api/buscar/etiquetas')) {
      const q = new URL(url, 'http://x').searchParams.get('q') || '';
      const items = TODAS.filter(n => n.toLowerCase().includes(q.toLowerCase())).map((name, i) => ({ id: i + 1, name }));
      return respuesta(200, { items, mas: false });
    }
    if (url === '/api/tags' && metodo === 'POST') return respuesta(201, { id: 99, name: body.name });
    if (url === '/api/bot/drafts/635' && metodo === 'PUT') {
      return respuesta(200, { ...DRAFT, payload: { ...DRAFT.payload, tags: body.tags } });
    }
    return respuesta(404, {});
  }));
}

describe('EtiquetasBorrador', () => {
  let llamadas;
  beforeEach(() => { llamadas = []; stub(llamadas); });
  afterEach(() => vi.unstubAllGlobals());

  it('muestra todas (incluidas las que el chat no alcanzaba) y marca las puestas', async () => {
    render(<EtiquetasBorrador draft={DRAFT} onGuardado={() => {}} logout={() => {}} />);
    // primera prueba del archivo: el entorno arranca lento y hay 200 ms de debounce
    expect(await screen.findByRole('button', { name: 'Poner etiqueta Oficina' }, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Quitar etiqueta Comida' })).toHaveAttribute('aria-pressed', 'true');
    expect(llamadas[0][1]).toBe('/api/buscar/etiquetas?limite=30');     // top-N, nunca el catálogo entero
  });

  it('busca en el servidor, pone y guarda con avisar_chat', async () => {
    const onGuardado = vi.fn();
    render(<EtiquetasBorrador draft={DRAFT} onGuardado={onGuardado} logout={() => {}} />);
    fireEvent.change(screen.getByLabelText('Buscar etiqueta'), { target: { value: 'obra' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Poner etiqueta Bonaire obra' }));
    fireEvent.click(screen.getByRole('button', { name: 'Guardar etiquetas' }));
    await waitFor(() => expect(onGuardado).toHaveBeenCalled());
    const put = llamadas.find(([m]) => m === 'PUT');
    expect(put[2]).toEqual({ tags: ['Comida', 'Bonaire obra'], avisar_chat: true });
    expect(llamadas.some(([, u]) => u.includes('q=obra'))).toBe(true);
  });

  it('crea la que no existe y la deja marcada', async () => {
    render(<EtiquetasBorrador draft={DRAFT} onGuardado={() => {}} logout={() => {}} />);
    fireEvent.change(screen.getByLabelText('Buscar etiqueta'), { target: { value: 'Viaje Cali' } });
    fireEvent.click(await screen.findByRole('button', { name: '➕ Crear «Viaje Cali»' }));
    expect(await screen.findByRole('button', { name: 'Quitar etiqueta Viaje Cali' })).toBeInTheDocument();
    expect(llamadas.find(([m]) => m === 'POST')[2]).toEqual({ name: 'Viaje Cali' });
  });

  it('no ofrece crear una que ya existe con otra forma de escribirla', async () => {
    render(<EtiquetasBorrador draft={DRAFT} onGuardado={() => {}} logout={() => {}} />);
    fireEvent.change(screen.getByLabelText('Buscar etiqueta'), { target: { value: 'oficina' } });
    expect(await screen.findByRole('button', { name: 'Poner etiqueta Oficina' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Crear/ })).not.toBeInTheDocument();
  });

  it('sin cambios no hay nada que guardar; un borrador cerrado solo se ve', async () => {
    const { unmount } = render(<EtiquetasBorrador draft={DRAFT} onGuardado={() => {}} logout={() => {}} />);
    expect(screen.getByRole('button', { name: 'Guardar etiquetas' })).toBeDisabled();
    unmount();
    render(<EtiquetasBorrador draft={{ ...DRAFT, editable: false }} onGuardado={() => {}} logout={() => {}} />);
    expect(screen.getByRole('button', { name: 'Quitar etiqueta Comida' })).toBeDisabled();
    expect(screen.queryByLabelText('Buscar etiqueta')).not.toBeInTheDocument();
  });
});
