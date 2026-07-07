/* ============================================================
   useAccounts.js — Gestión de cuentas financieras (CRUD).
   Extraído de App.jsx (estados L56-64, funciones L625-676)
   ============================================================ */
import { useState } from 'react';
import { API } from '../config';

const API_BASE_URL = API;

export default function useAccounts({ fetchData }) {
  // --- Estados de cuentas ---
  const [accounts, setAccounts] = useState([]);
  const [newAccountName, setNewAccountName] = useState("");
  const [newAccountType, setNewAccountType] = useState("Ahorros");
  const [newAccountCurrency, setNewAccountCurrency] = useState("COP");
  const [newAccountInitialBalance, setNewAccountInitialBalance] = useState("");
  const [editingAccountId, setEditingAccountId] = useState(null);
  const [editAccountName, setEditAccountName] = useState("");
  const [editAccountType, setEditAccountType] = useState("Ahorros");
  const [editAccountBalance, setEditAccountBalance] = useState("");

  // --- Crear Nueva Cuenta ---
  const handleCreateAccount = async (e) => {
    e.preventDefault();
    if (!newAccountName) {
      alert("❌ Nombre de cuenta es obligatorio.");
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/accounts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newAccountName,
          type: newAccountType,
          currency: newAccountCurrency,
          initial_balance: parseFloat(newAccountInitialBalance || "0.0")
        })
      });
      if (res.ok) {
        setNewAccountName("");
        setNewAccountInitialBalance("");
        fetchData();
      } else {
        const errData = await res.json();
        alert(`❌ Error al crear cuenta: ${errData.detail}`);
      }
    } catch (error) {
      alert("❌ Error al conectar con el servidor.");
    }
  };

  const handleUpdateAccount = async (accountId) => {
    if (!editAccountName.trim()) { alert("❌ El nombre no puede estar vacío."); return; }
    try {
      const res = await fetch(`${API_BASE_URL}/accounts/${accountId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: editAccountName, type: editAccountType, current_balance: parseFloat(editAccountBalance) || 0 })
      });
      if (res.ok) { setEditingAccountId(null); fetchData(); }
      else { const d = await res.json(); alert(`❌ ${d.detail}`); }
    } catch { alert("❌ Error al conectar con el servidor."); }
  };

  const handleDeleteAccount = async (accountId, accountName) => {
    if (!window.confirm(`¿Eliminar la cuenta "${accountName}"?\nLas transacciones vinculadas quedarán sin cuenta asignada.`)) return;
    try {
      const res = await fetch(`${API_BASE_URL}/accounts/${accountId}`, { method: "DELETE" });
      if (res.ok) { fetchData(); }
      else { const d = await res.json(); alert(`❌ ${d.detail}`); }
    } catch { alert("❌ Error al conectar con el servidor."); }
  };

  return {
    accounts, setAccounts,
    newAccountName, setNewAccountName,
    newAccountType, setNewAccountType,
    newAccountCurrency, setNewAccountCurrency,
    newAccountInitialBalance, setNewAccountInitialBalance,
    editingAccountId, setEditingAccountId,
    editAccountName, setEditAccountName,
    editAccountType, setEditAccountType,
    editAccountBalance, setEditAccountBalance,
    handleCreateAccount,
    handleUpdateAccount,
    handleDeleteAccount,
  };
}
