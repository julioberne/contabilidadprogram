/* El ✎/🗑 del panel de contexto (👤 Terceros, 🏷️ Tags, 📈 Tasas, 📦 Recursos):
   hasta el 30-sep-2026 cualquier fallo del DELETE/PUT se tragaba en silencio y
   los botones "no hacían nada". Ahora el `detail` del servidor se muestra en un
   aviso fijo del panel (fuera del área desplazable) y se puede cerrar; las
   etiquetas en uso piden una segunda confirmación (?forzar=1); Tasas tiene
   fila de edición. */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import ContextPanel from './ContextPanel.jsx';

const respuesta = (status, body) =>
  Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });

const TERCEROS = [
  { id: 2, name: 'negre computadores sas', identification_type: 'NIT', identification_number: '100736548' },
  { id: 34, name: 'TERCERO PRUEBA MODAL', identification_type: 'CC', identification_number: '1122334455' },
];
const TAGS = [
  { id: 5, name: 'Oficina', color: '#2196F3' },
  { id: 1, name: 'dfghj', color: '#000000' },
];
const TASAS = [{ id: 3, name: 'ReteICA', rate: '0.9660', type: 'DEDUCTIVE' }];

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

describe('ContextPanel · avisos del panel', () => {
  let llamadas;
  let responder;   // (metodo, url, body) => Promise<respuesta>

  beforeEach(() => {
    llamadas = [];
    responder = (metodo, url) => {
      if (metodo === 'GET' && url.endsWith('/third-parties')) return respuesta(200, TERCEROS.filter(t => t.id !== 34));
      if (metodo === 'GET' && url.endsWith('/tags')) return respuesta(200, TAGS);
      if (metodo === 'GET' && url.endsWith('/custom-taxes')) return respuesta(200, TASAS);
      return respuesta(200, { status: 'OK' });
    };
    vi.stubGlobal('fetch', vi.fn((url, opts = {}) => {
      const metodo = opts.method || 'GET';
      const body = opts.body ? JSON.parse(opts.body) : null;
      llamadas.push([metodo, url, body]);
      return responder(metodo, url, body);
    }));
    vi.spyOn(window, 'confirm').mockReturnValue(true);
  });

  afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  const mutaciones = () => llamadas.filter(l => l[0] !== 'GET');

  describe('🗑 de Terceros', () => {
    it('muestra el detail del servidor cuando el borrado se rechaza (409)', async () => {
      const base = responder;
      responder = (m, u, b) => m === 'DELETE'
        ? respuesta(409, { detail: 'No se puede eliminar a «negre computadores sas»: tiene 18 transacciones.' })
        : base(m, u, b);
      montar();
      fireEvent.click(papelera('negre computadores sas'));
      expect(await screen.findByRole('alert')).toHaveTextContent('tiene 18 transacciones');
      expect(mutaciones()).toEqual([['DELETE', '/api/third-parties/2', null]]);   // sin refresco
      fireEvent.click(screen.getByLabelText('Cerrar aviso'));
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('sin detail (p. ej. 405 de un endpoint inexistente) igual avisa con el código', async () => {
      const base = responder;
      responder = (m, u, b) => m === 'DELETE' ? respuesta(405, {}) : base(m, u, b);
      montar();
      fireEvent.click(papelera('TERCERO PRUEBA MODAL'));
      expect(await screen.findByRole('alert')).toHaveTextContent('Error 405 al eliminar');
    });

    it('si no hay red lo dice, en vez de callar', async () => {
      const base = responder;
      responder = (m, u, b) => m === 'DELETE' ? Promise.reject(new TypeError('Failed to fetch')) : base(m, u, b);
      montar();
      fireEvent.click(papelera('TERCERO PRUEBA MODAL'));
      expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo conectar con el servidor.');
    });

    it('con 200 refresca la lista y no muestra aviso', async () => {
      const setAllThirdParties = vi.fn();
      montar({ setAllThirdParties });
      fireEvent.click(papelera('TERCERO PRUEBA MODAL'));
      await waitFor(() => expect(setAllThirdParties).toHaveBeenCalledWith(TERCEROS.filter(t => t.id !== 34)));
      expect(llamadas.map(l => [l[0], l[1]])).toEqual([['DELETE', '/api/third-parties/34'], ['GET', '/api/third-parties']]);
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
      const base = responder;
      responder = (m, u, b) => m === 'DELETE' ? respuesta(409, { detail: 'tiene 1 cuenta de cartera (CXC/CXP).' }) : base(m, u, b);
      const { rerender } = montar();
      fireEvent.click(papelera('negre computadores sas'));
      await screen.findByRole('alert');
      rerender(<ContextPanel activeTab="etiquetas" setActiveTab={() => {}}
        allThirdParties={TERCEROS} setAllThirdParties={() => {}} />);
      await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    });
  });

  describe('🏷️ Etiquetas', () => {
    // El nombre aparece dos veces (selector de arriba y lista de la BD): la fila
    // editable es la de la lista (`.group`, con ✎ y 🗑)
    const filaTag = async (nombre) =>
      (await screen.findAllByText(nombre)).map(n => n.closest('.group')).find(Boolean);

    it('en uso: 409 → segunda confirmación con el texto del servidor → DELETE ?forzar=1', async () => {
      const base = responder;
      responder = (m, u, b) => {
        if (m === 'DELETE' && u === '/api/tags/5') {
          return respuesta(409, { detail: 'La etiqueta «Oficina» está en 2 transacciones y 1 borrador abierto del bot (#236).' });
        }
        if (m === 'DELETE' && u === '/api/tags/5?forzar=1') {
          return respuesta(200, { status: 'ELIMINADO', id: 5, transacciones_actualizadas: 2, borradores_actualizados: 1 });
        }
        return base(m, u, b);
      };
      montar({ activeTab: 'etiquetas' });
      fireEvent.click(within(await filaTag('Oficina')).getByTitle('Eliminar la etiqueta'));
      await waitFor(() => expect(mutaciones().map(l => l[1])).toEqual(['/api/tags/5', '/api/tags/5?forzar=1']));
      expect(window.confirm).toHaveBeenCalledTimes(2);
      expect(window.confirm.mock.calls[1][0]).toContain('está en 2 transacciones y 1 borrador abierto del bot (#236).');
      expect(window.confirm.mock.calls[1][0]).toContain('¿Quitarla también de ahí y borrarla?');
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(llamadas.filter(l => l[0] === 'GET' && l[1].endsWith('/tags')).length).toBe(2);   // refresco
    });

    it('si rechaza la segunda confirmación no fuerza nada ni avisa', async () => {
      const base = responder;
      responder = (m, u, b) => (m === 'DELETE' ? respuesta(409, { detail: 'La etiqueta «Oficina» está en 2 transacciones.' }) : base(m, u, b));
      window.confirm.mockReturnValueOnce(true).mockReturnValueOnce(false);
      montar({ activeTab: 'etiquetas' });
      fireEvent.click(within(await filaTag('Oficina')).getByTitle('Eliminar la etiqueta'));
      await waitFor(() => expect(window.confirm).toHaveBeenCalledTimes(2));
      expect(mutaciones().map(l => l[1])).toEqual(['/api/tags/5']);
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('sin uso se borra con la confirmación normal', async () => {
      montar({ activeTab: 'etiquetas' });
      fireEvent.click(within(await filaTag('dfghj')).getByTitle('Eliminar la etiqueta'));
      await waitFor(() => expect(mutaciones().map(l => l[1])).toEqual(['/api/tags/1']));
      expect(window.confirm).toHaveBeenCalledTimes(1);
    });

    it('el ✓ de edición manda el PUT, cierra la fila si va bien y avisa si no', async () => {
      const base = responder;
      let putStatus = 409;
      responder = (m, u, b) => (m === 'PUT' ? respuesta(putStatus, putStatus === 200 ? { status: 'OK' } : { detail: 'Ya existe una etiqueta llamada «Operativo».' }) : base(m, u, b));
      montar({ activeTab: 'etiquetas' });
      fireEvent.click(within(await filaTag('Oficina')).getByText('✎'));
      const input = screen.getByDisplayValue('Oficina');
      fireEvent.change(input, { target: { value: 'Operativo' } });
      fireEvent.click(screen.getByText('✓'));
      expect(await screen.findByRole('alert')).toHaveTextContent('Ya existe una etiqueta llamada «Operativo».');
      expect(screen.getByDisplayValue('Operativo')).toBeInTheDocument();          // la fila sigue abierta
      expect(mutaciones()).toEqual([['PUT', '/api/tags/5', { name: 'Operativo', color: '#2196F3' }]]);

      putStatus = 200;
      fireEvent.click(screen.getByText('✓'));
      await waitFor(() => expect(screen.queryByDisplayValue('Operativo')).not.toBeInTheDocument());
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  describe('📈 Tasas', () => {
    it('el ✎ abre la fila de edición y el ✓ manda el PUT con nombre, tasa y tipo', async () => {
      montar({ activeTab: 'impuestos' });
      const fila = (await screen.findByText('ReteICA')).closest('tr');
      fireEvent.click(within(fila).getByTitle('Editar la tasa'));
      expect(screen.getByLabelText('Nombre de la tasa')).toHaveValue('ReteICA');
      fireEvent.change(screen.getByLabelText('Tasa %'), { target: { value: '1,2' } });
      fireEvent.change(screen.getByLabelText('Tipo de tasa'), { target: { value: 'ADDITIVE' } });
      fireEvent.click(screen.getByTitle('Guardar'));
      await waitFor(() => expect(mutaciones()).toEqual([['PUT', '/api/custom-taxes/3', { name: 'ReteICA', rate: 1.2, type: 'ADDITIVE' }]]));
      await waitFor(() => expect(screen.queryByLabelText('Nombre de la tasa')).not.toBeInTheDocument());
    });

    it('el 🗑 de una tasa muestra el error del servidor', async () => {
      const base = responder;
      responder = (m, u, b) => (m === 'DELETE' ? respuesta(404, { detail: 'Esa tasa no existe.' }) : base(m, u, b));
      montar({ activeTab: 'impuestos' });
      const fila = (await screen.findByText('ReteICA')).closest('tr');
      fireEvent.click(within(fila).getByTitle('Eliminar la tasa'));
      expect(await screen.findByRole('alert')).toHaveTextContent('Esa tasa no existe.');
    });
  });
});
