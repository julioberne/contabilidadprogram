/* Casillas del Libro Diario (spec 13.5, CA-135-08/09): la casilla marca sin
   expandir la fila; el clic en la fila sigue expandiendo; la barra muestra lo
   marcado con sus totales y solo existe para los roles del módulo 14. */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';

vi.mock('../../engine/EmpresaProvider.jsx', () => ({ useEmpresa: () => ({ cajaViva: {} }) }));
let modulos = [{ id: 'exportacion' }];
vi.mock('../../../registry/moduleRegistry.js', () => ({ getRenderableModules: () => modulos }));
vi.mock('../../../exportacion/ExportarSeleccion.jsx', () => ({
  default: ({ txIds }) => <div>exportando {txIds.join(',')}</div>,
}));

import LibroDiario from './LibroDiario.jsx';

const TXS = [
  { id: 11, type: 'INGRESO', net_value: 1000, amount: 1000, concept: 'Venta', transaction_currency: 'COP', transaction_date: '2026-09-01' },
  { id: 12, type: 'GASTO', net_value: 400, amount: 400, concept: 'Arriendo', transaction_currency: 'COP', transaction_date: '2026-09-02' },
  { id: 13, type: 'GASTO', net_value: 25, amount: 25, concept: 'Licencia', transaction_currency: 'USD', transaction_date: '2026-09-03' },
];

function montar(extra = {}) {
  const setExpandedTxId = vi.fn();
  const vista = (mas = {}) => (
    <LibroDiario transactions={TXS} totalTxCount={3} loadingMore={false} loadMoreTransactions={() => {}}
      expandedTxId={null} setExpandedTxId={setExpandedTxId} editingCell={null} setEditingCell={() => {}}
      editValue="" setEditValue={() => {}} saveInlineEdit={() => {}} toggleRecurrence={() => {}}
      accounts={[]} coaFlatAccounts={[]} onEvidenceClick={() => {}} {...extra} {...mas} />
  );
  const { rerender } = render(vista());
  return { setExpandedTxId, cambiar: (mas) => rerender(vista(mas)) };
}

describe('Libro Diario — «Marcar todo» por filtro (H8.3)', () => {
  beforeEach(() => { modulos = [{ id: 'exportacion' }]; });
  const barra = ({ onMarcarTodo }) => <button type="button" onClick={onMarcarTodo}>marcar todo</button>;
  const props = (traerSeleccion) => ({
    traerSeleccion, renderBarra: barra, totalTxCount: 500, filtroActual: 'portfolio=A',
    totalesTodo: { ingresos_cop: 900000, gastos_cop: 100000, ingresos_usd: 0, gastos_usd: 0 },
  });

  it('marcar no baja ninguna fila: usa el conteo y los totales que ya hay', () => {
    const traer = vi.fn();
    montar(props(traer));
    fireEvent.click(screen.getByText('marcar todo'));
    const region = screen.getByRole('region', { name: 'Selección para exportar' });
    expect(within(region).getByText('☑ 500 seleccionadas')).toBeInTheDocument();
    expect(within(region).getByText(/ING \$900\.000/)).toBeInTheDocument();
    expect(screen.getByLabelText('Marcar transacción 11')).toBeChecked();
    expect(screen.getByLabelText('Marcar todas las visibles')).toBeChecked();
    expect(traer).not.toHaveBeenCalled();
  });

  it('desmarcar una fila la resta del conteo y de los totales', () => {
    montar(props(vi.fn()));
    fireEvent.click(screen.getByText('marcar todo'));
    fireEvent.click(screen.getByLabelText('Marcar transacción 12'));
    expect(screen.getByLabelText('Marcar transacción 12')).not.toBeChecked();
    expect(screen.getByText('☑ 499 seleccionadas')).toBeInTheDocument();
    expect(screen.getByText(/GAS \$99\.600/)).toBeInTheDocument();
  });

  it('al exportar pide ese filtro y deja fuera lo desmarcado', async () => {
    const traer = vi.fn().mockResolvedValue([{ id: 11 }, { id: 12 }, { id: 90 }]);
    montar(props(traer));
    fireEvent.click(screen.getByText('marcar todo'));
    fireEvent.click(screen.getByLabelText('Marcar transacción 12'));
    fireEvent.click(screen.getByRole('button', { name: /Exportar selección/ }));
    expect(await screen.findByText('exportando 11,90')).toBeInTheDocument();
    expect(traer).toHaveBeenCalledWith('portfolio=A');
  });

  it('si cambia el filtro, la selección se limpia', () => {
    const { cambiar } = montar(props(vi.fn()));
    fireEvent.click(screen.getByText('marcar todo'));
    cambiar({ filtroActual: 'portfolio=B' });
    expect(screen.queryByRole('region', { name: 'Selección para exportar' })).toBeNull();
    expect(screen.getByLabelText('Marcar transacción 11')).not.toBeChecked();
  });

  it('por encima del tope avisa y no marca a medias', () => {
    const aviso = vi.spyOn(window, 'alert').mockImplementation(() => {});
    montar({ ...props(vi.fn()), totalTxCount: 20001 });
    fireEvent.click(screen.getByText('marcar todo'));
    expect(aviso).toHaveBeenCalledOnce();
    expect(screen.queryByRole('region', { name: 'Selección para exportar' })).toBeNull();
    aviso.mockRestore();
  });
});

describe('Libro Diario — casillas para exportar', () => {
  beforeEach(() => { modulos = [{ id: 'exportacion' }]; });

  it('la casilla marca sin expandir la fila; el clic en la fila sí expande (CA-135-09)', () => {
    const { setExpandedTxId } = montar();
    fireEvent.click(screen.getByLabelText('Marcar transacción 12'));
    expect(setExpandedTxId).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Marcar transacción 12')).toBeChecked();
    fireEvent.click(screen.getByText('Arriendo'));
    expect(setExpandedTxId).toHaveBeenCalledWith(12);
  });

  it('la barra aparece con lo marcado y totales por moneda; Limpiar la quita (CA-135-08)', () => {
    montar();
    expect(screen.queryByRole('region', { name: 'Selección para exportar' })).toBeNull();
    fireEvent.click(screen.getByLabelText('Marcar transacción 11'));
    fireEvent.click(screen.getByLabelText('Marcar transacción 13'));
    const barra = screen.getByRole('region', { name: 'Selección para exportar' });
    expect(within(barra).getByText('☑ 2 seleccionadas')).toBeInTheDocument();
    expect(within(barra).getByText(/ING \$1\.000/)).toBeInTheDocument();
    expect(within(barra).getByText(/GAS USD 25/)).toBeInTheDocument();
    expect(within(barra).getByRole('button', { name: /Exportar selección/ })).toBeInTheDocument();
    fireEvent.click(within(barra).getByRole('button', { name: /Limpiar/ }));
    expect(screen.queryByRole('region', { name: 'Selección para exportar' })).toBeNull();
  });

  it('"todas las visibles" marca y desmarca todo lo cargado', () => {
    montar();
    const todas = screen.getByLabelText('Marcar todas las visibles');
    fireEvent.click(todas);
    expect(screen.getByText('☑ 3 seleccionadas')).toBeInTheDocument();
    fireEvent.click(todas);
    expect(screen.queryByRole('region', { name: 'Selección para exportar' })).toBeNull();
  });

  it('sin el módulo Exportación (otro rol) no hay casillas', () => {
    modulos = [];
    montar();
    expect(screen.queryByLabelText('Marcar todas las visibles')).toBeNull();
    expect(screen.queryByLabelText('Marcar transacción 11')).toBeNull();
  });
});
