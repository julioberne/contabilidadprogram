/* ============================================================
   useLibroDiario.js — Estado y acciones del Libro Diario (M02)
   Port verbatim de App.jsx: saveInlineEdit (L336-365),
   toggleRecurrence (L367-383), estados de edición inline y
   fila expandible. La paginación usa empresa.loadMoreTransactions
   (vía /dashboard-data — en v1 el "Cargar más" estaba roto
   porque leía data.items de un endpoint que no pagina).
   ============================================================ */
import { useState } from 'react';
import { API } from '../../../config';
import { useEmpresa } from '../../engine/EmpresaProvider.jsx';

const API_BASE_URL = API;

export function useLibroDiario() {
  const empresa = useEmpresa();
  const { fetchAll: fetchData } = empresa;

  // --- Fila expandible + edición inline (en v1 vivían en App.jsx) ---
  const [expandedTxId, setExpandedTxId] = useState(null);
  const [editingCell, setEditingCell] = useState(null); // { txId, field }
  const [editValue, setEditValue] = useState("");
  const [loadingMore, setLoadingMore] = useState(false);

  const saveInlineEdit = async (txId, field) => {
    if (!editingCell) return;

    let valueToSave = editValue;
    if (field === "net_value" || field === "amount") {
      valueToSave = parseFloat(editValue);
      if (isNaN(valueToSave)) valueToSave = 0.0;
    }

    const payload = {
      [field]: valueToSave
    };

    try {
      const res = await fetch(`${API_BASE_URL}/transactions/${txId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setEditingCell(null);
        fetchData();
      } else {
        const data = await res.json();
        alert(`❌ Error al actualizar: ${data.detail}`);
      }
    } catch {
      alert("❌ Error al conectar con el servidor.");
    }
  };

  const toggleRecurrence = async (txId, currentVal) => {
    try {
      const res = await fetch(`${API_BASE_URL}/transactions/${txId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_recurring: !currentVal })
      });
      if (res.ok) {
        fetchData();
      } else {
        const data = await res.json();
        alert(`❌ Error al cambiar recurrencia: ${data.detail}`);
      }
    } catch (error) {
      console.error("Error toggling recurrence:", error);
    }
  };

  const loadMoreTransactions = async () => {
    setLoadingMore(true);
    try {
      await empresa.loadMoreTransactions(empresa.transactions.length);
    } finally {
      setLoadingMore(false);
    }
  };

  return {
    expandedTxId, setExpandedTxId,
    editingCell, setEditingCell,
    editValue, setEditValue,
    loadingMore,
    saveInlineEdit,
    toggleRecurrence,
    loadMoreTransactions,
  };
}

export default useLibroDiario;
