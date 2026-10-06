/* Casillas del Libro Diario (spec 13.5, CA-135-08/09): la casilla marca sin
   expandir la fila; el clic en la fila sigue expandiendo; la barra muestra lo
   marcado con sus totales y solo existe para los roles del módulo 14. */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';

vi.mock('../../engine/EmpresaProvider.jsx', () => ({ useEmpresa: () => ({ cajaViva: {} }) }));
let modulos = [{ id: 'exportacion' }];
vi.mock('../../../registry/moduleRegistry.js', () => ({ getRenderableModules: () => modulos }));

import LibroDiario from './LibroDiario.jsx';

const TXS = [
  { id: 11, type: 'INGRESO', net_value: 1000, amount: 1000, concept: 'Venta', transaction_currency: 'COP', transaction_date: '2026-09-01' },
  { id: 12, type: 'GASTO', net_value: 400, amount: 400, concept: 'Arriendo', transaction_currency: 'COP', transaction_date: '2026-09-02' },
  { id: 13, type: 'GASTO', net_value: 25, amount: 25, concept: 'Licencia', transaction_currency: 'USD', transaction_date: '2026-09-03' },
];

function montar(extra = {}) {
  const setExpandedTxId = vi.fn();
  render(
    <LibroDiario transactions={TXS} totalTxCount={3} loadingMore={false} loadMoreTransactions={() => {}}
      expandedTxId={null} setExpandedTxId={setExpandedTxId} editingCell={null} setEditingCell={() => {}}
      editValue="" setEditValue={() => {}} saveInlineEdit={() => {}} toggleRecurrence={() => {}}
      accounts={[]} coaFlatAccounts={[]} onEvidenceClick={() => {}} {...extra} />,
  );
  return { setExpandedTxId };
}

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
