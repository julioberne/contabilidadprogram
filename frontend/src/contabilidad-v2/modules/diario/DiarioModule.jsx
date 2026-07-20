/* ============================================================
   DiarioModule.jsx — Adapter del Libro Diario (Módulo 02)
   Monta LibroDiario de v1 VERBATIM (import transitorio) con
   estado de useLibroDiario + datos del EmpresaProvider.
   onEvidenceClick lo inyecta el shell (abre EvidenceModal).
   ============================================================ */
import LibroDiario from './LibroDiario.jsx';
import { useEmpresa } from '../../engine/EmpresaProvider.jsx';
import { useLibroDiario } from './useLibroDiario.js';

export default function DiarioModule({ onEvidenceClick }) {
  const empresa = useEmpresa();
  const diario = useLibroDiario();

  return (
    <LibroDiario
      transactions={empresa.transactions}
      totalTxCount={empresa.totalTxCount}
      loadingMore={diario.loadingMore}
      loadMoreTransactions={diario.loadMoreTransactions}
      expandedTxId={diario.expandedTxId} setExpandedTxId={diario.setExpandedTxId}
      editingCell={diario.editingCell} setEditingCell={diario.setEditingCell}
      editValue={diario.editValue} setEditValue={diario.setEditValue}
      saveInlineEdit={diario.saveInlineEdit}
      toggleRecurrence={diario.toggleRecurrence}
      accounts={empresa.accounts}
      coaFlatAccounts={empresa.coaFlatAccounts}
      onEvidenceClick={onEvidenceClick}
    />
  );
}
