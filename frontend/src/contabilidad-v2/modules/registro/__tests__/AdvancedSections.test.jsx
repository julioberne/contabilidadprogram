/* Buscador de terceros registrados en el formulario de registro
   (2026-09-11, pedido de Andrés: poder REUTILIZAR un tercero ya
   registrado en vez de volver a agregarlo con cada ingreso/gasto). */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AdvancedSections from '../AdvancedSections.jsx';
import { useTransactionDraft } from '../../../engine/TransactionDraftProvider.jsx';

vi.mock('../../../engine/TransactionDraftProvider.jsx', () => ({
  useTransactionDraft: vi.fn(),
}));

const TERCEROS = [
  { id: 5, name: 'KEVIN MATEO GONZÁLEZ AGUDELO', identification_type: 'CC',
    identification_number: '1031645976', phone: '301563048', email: 'mateo@mail.com',
    address: 'Cra 109 # 151C-25' },
  { id: 9, name: 'Ferretería El Tornillo', identification_type: 'NIT',
    identification_number: '100736548' },
  { id: 1, name: 'Sin especificar', identification_type: 'NIT',
    identification_number: '999999999' },
];

function draftFake(extra = {}) {
  return {
    thirdPartyName: '', setThirdPartyName: vi.fn(),
    thirdPartyType: 'NIT', setThirdPartyType: vi.fn(),
    thirdPartyNumber: '', setThirdPartyNumber: vi.fn(),
    thirdPartyEmail: '', setThirdPartyEmail: vi.fn(),
    thirdPartyPhone: '', setThirdPartyPhone: vi.fn(),
    thirdPartyAddress: '', setThirdPartyAddress: vi.fn(),
    allThirdParties: TERCEROS,
    applyIva: false, setApplyIva: vi.fn(),
    applyPropina: false, setApplyPropina: vi.fn(),
    applyGmf: false, setApplyGmf: vi.fn(),
    customTaxesList: [], setCustomTaxesList: vi.fn(),
    selectedTags: [], setSelectedTags: vi.fn(),
    tagSearch: '', setTagSearch: vi.fn(),
    ...extra,
  };
}

function abrirSeccionTercero() {
  fireEvent.click(screen.getByText(/Identificación de Tercero/i));
}

beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
});

describe('AdvancedSections — buscador de terceros registrados', () => {
  it('filtra en memoria y excluye al genérico 999999999', () => {
    useTransactionDraft.mockReturnValue(draftFake());
    render(<AdvancedSections />);
    abrirSeccionTercero();

    const buscador = screen.getByPlaceholderText(/Nombre o número/i);
    fireEvent.change(buscador, { target: { value: 'kev' } });
    expect(screen.getByText('KEVIN MATEO GONZÁLEZ AGUDELO')).toBeInTheDocument();

    // el genérico jamás aparece como elegible (no identifica a nadie)
    fireEvent.change(buscador, { target: { value: '999999999' } });
    expect(screen.queryByText('Sin especificar')).not.toBeInTheDocument();
    expect(screen.getByText(/Sin coincidencias/i)).toBeInTheDocument();
  });

  it('elegir un resultado llena todos los campos del tercero', () => {
    const d = draftFake();
    useTransactionDraft.mockReturnValue(d);
    render(<AdvancedSections />);
    abrirSeccionTercero();

    fireEvent.change(screen.getByPlaceholderText(/Nombre o número/i), { target: { value: '10316' } });
    fireEvent.click(screen.getByText('KEVIN MATEO GONZÁLEZ AGUDELO'));

    expect(d.setThirdPartyName).toHaveBeenCalledWith('KEVIN MATEO GONZÁLEZ AGUDELO');
    expect(d.setThirdPartyType).toHaveBeenCalledWith('CC');
    expect(d.setThirdPartyNumber).toHaveBeenCalledWith('1031645976');
    expect(d.setThirdPartyPhone).toHaveBeenCalledWith('301563048');
    expect(d.setThirdPartyEmail).toHaveBeenCalledWith('mateo@mail.com');
    expect(d.setThirdPartyAddress).toHaveBeenCalledWith('Cra 109 # 151C-25');
  });

  it('el formulario tiene el campo Dirección (opcional)', () => {
    useTransactionDraft.mockReturnValue(draftFake());
    render(<AdvancedSections />);
    abrirSeccionTercero();
    expect(screen.getByText('Dirección')).toBeInTheDocument();
  });

  it('semáforo: número ya registrado ⇒ "se reutilizará"', () => {
    useTransactionDraft.mockReturnValue(draftFake({ thirdPartyNumber: '100736548' }));
    render(<AdvancedSections />);
    abrirSeccionTercero();
    expect(screen.getByText(/se reutilizará, no se duplica/i)).toBeInTheDocument();
  });

  it('semáforo: solo nombre ya registrado ⇒ reutiliza (caso del reporte)', () => {
    useTransactionDraft.mockReturnValue(draftFake({ thirdPartyName: '  ferretería el tornillo ' }));
    render(<AdvancedSections />);
    abrirSeccionTercero();
    expect(screen.getByText(/Ya existe con este nombre/i)).toBeInTheDocument();
  });

  it('semáforo: nombre nuevo sin número ⇒ avisa número provisional', () => {
    useTransactionDraft.mockReturnValue(draftFake({ thirdPartyName: 'Proveedor Nuevo SAS' }));
    render(<AdvancedSections />);
    abrirSeccionTercero();
    expect(screen.getByText(/número provisional/i)).toBeInTheDocument();
  });
});
