/* ============================================================
   useAdminActions.js — Acciones administrativas del dashboard:
   ⚡ Semillar datos sintéticos y ⚠️ Reiniciar base contable.
   Port verbatim de App.jsx (handleSeedSynthetic /
   handleResetDatabase). Se cablea al shell en la Fase 4.
   ============================================================ */
import { API } from '../../config';
import { useEmpresa } from '../engine/EmpresaProvider.jsx';

const API_BASE_URL = API;

export function useAdminActions() {
  const { activePortfolio, fetchAll: fetchData } = useEmpresa();

  const handleSeedSynthetic = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/transactions/seed_synthetic?portfolio=${activePortfolio}`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok) {
        alert("✅ Datos sintéticos creados con éxito. Se indujo un estado de insolvencia para probar alertas.");
        fetchData();
      } else {
        alert(`❌ Error al semillar datos: ${data.detail}`);
      }
    } catch {
      alert("❌ Error de red al semillar datos.");
    }
  };

  const handleResetDatabase = async () => {
    if (!window.confirm("⚠️ ¿Estás seguro de que deseas reiniciar todos los valores contables, perfiles y cuentas a sus valores iniciales? Esta acción no se puede deshacer.")) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/transactions/reset`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok) {
        alert("✅ Base de datos contable y cuentas reiniciadas con éxito.");
        fetchData();
      } else {
        alert(`❌ Error al reiniciar base de datos: ${data.detail}`);
      }
    } catch {
      alert("❌ Error de red al reiniciar base de datos.");
    }
  };

  return { handleSeedSynthetic, handleResetDatabase };
}

export default useAdminActions;
