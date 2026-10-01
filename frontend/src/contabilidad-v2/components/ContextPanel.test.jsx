/* El 🗑 del panel de contexto (👤 Terceros; también Tags, Tasas y Recursos):
   hasta el 30-sep-2026 cualquier fallo del DELETE se tragaba en silencio y el
   botón "no hacía nada". Ahora el `detail` del servidor se muestra en un aviso
   fijo del panel (fuera del área desplazable) y se puede cerrar. */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ContextPanel from './ContextPanel.jsx';

const respuesta = (status, body) =>
  Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });

const TERCEROS = [
  { id: 2, name: 'negre computadores sas', identification_type: 'NIT', identification_number: '100736548' },
  { id: 34, name: 'TERCERO PRUEBA MODAL', identification_type: 'CC', identification_number: '1122334455' },
];

function montar(props = {}) {
  return render(
    <ContextPanel activeTab="terceros" setActiveTab={() => {}}
      allThirdParties={TERCEROS} setAllThirdParties={() => {}} {...props} />
  );
}

function papelera(nombre) {
  // El 🗑 es el segundo botón de la fila del tercero (el primero es ✎)
  const fila = screen.getByText(nombre).closest('tr');
  return fila.querySelectorAll('button')[1];
}

describe('ContextPanel · 🗑 de Terceros', () => {
  let llamadas;
  let deleteResponde;

  beforeEach(() => {
    llamadas = [];
    deleteResponde = () => respuesta(200, { status: 'ELIMINADO', id: 34 });
    vi.stubGlobal('fetch', vi.fn((url, opts = {}) => {
      const metodo = opts.method || 'GET';
      llamadas.push([metodo, url]);
      if (metodo === 'DELETE') return deleteResponde(url);
      return respuesta(200, TERCEROS.filter(t => t.id !== 34));
    }));
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it('muestra el detail del servidor cuando el borrado se rechaza (409)', async () => {
    deleteResponde = () => respuesta(409, {
      detail: 'No se puede eliminar a «negre computadores sas»: tiene 18 transacciones.' });
    montar();
    fireEvent.click(papelera('negre computadores sas'));
    expect(await screen.findByRole('alert')).toHaveTextContent('tiene 18 transacciones');
    expect(llamadas).toEqual([['DELETE', '/api/third-parties/2']]);   // sin refresco
    fireEvent.click(screen.getByLabelText('Cerrar aviso'));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('sin detail (p. ej. 405 de un endpoint inexistente) igual avisa con el código', async () => {
    deleteResponde = () => respuesta(405, {});
    montar();
    fireEvent.click(papelera('TERCERO PRUEBA MODAL'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Error 405 al eliminar');
  });

  it('si no hay red lo dice, en vez de callar', async () => {
    deleteResponde = () => Promise.reject(new TypeError('Failed to fetch'));
    montar();
    fireEvent.click(papelera('TERCERO PRUEBA MODAL'));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor.');
  });

  it('con 200 refresca la lista y no muestra aviso', async () => {
    const setAllThirdParties = vi.fn();
    montar({ setAllThirdParties });
    fireEvent.click(papelera('TERCERO PRUEBA MODAL'));
    await waitFor(() => expect(setAllThirdParties).toHaveBeenCalledWith(TERCEROS.filter(t => t.id !== 34)));
    expect(llamadas).toEqual([['DELETE', '/api/third-parties/34'], ['GET', '/api/third-parties']]);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('si la persona cancela la confirmación no llama al servidor', () => {
    window.confirm.mockReturnValue(false);
    montar();
    fireEvent.click(papelera('TERCERO PRUEBA MODAL'));
    expect(llamadas).toEqual([]);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('el aviso se limpia al cambiar de pestaña', async () => {
    deleteResponde = () => respuesta(409, { detail: 'tiene 1 cuenta de cartera (CXC/CXP).' });
    const { rerender } = montar();
    fireEvent.click(papelera('negre computadores sas'));
    await screen.findByRole('alert');
    rerender(<ContextPanel activeTab="etiquetas" setActiveTab={() => {}}
      allThirdParties={TERCEROS} setAllThirdParties={() => {}} />);
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
  });
});
