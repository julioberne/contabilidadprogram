import { useTransactionDraft } from '../../engine/TransactionDraftProvider';
import { API } from '../../../config';

export default function RegistroForm({ accounts = [], onRegister }) {
  const draft = useTransactionDraft();
  
  // Destructure for easier reading
  const {
    formType, setFormType,
    amount, setAmount,
    date, setDate,
    concept, setConcept,
    selectedAccountId, setSelectedAccountId,
    txCurrency, setTxCurrency,
    evidenceFilePath, isUploadingEvidence, setIsUploadingEvidence, setEvidenceFilePath,
    isSubmitting
  } = draft;

  const handleAccountChange = (e) => {
    const accId = e.target.value;
    setSelectedAccountId(accId);
    const acc = accounts.find(a => String(a.id) === accId);
    if (acc) setTxCurrency(acc.currency);
  };

  const handleUploadEvidence = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setIsUploadingEvidence(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API}/upload-evidence`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setEvidenceFilePath(data.file_path);
      } else {
        alert("❌ Error al subir comprobante");
      }
    } catch {
      alert("❌ Error de conexión al subir comprobante.");
    } finally {
      setIsUploadingEvidence(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onRegister) {
      onRegister(draft);
    }
  };

  return (
    <div style={{ background: '#fff', border: '2px solid #000', padding: 8, boxShadow: '3px 3px 0 #000' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '2px solid #000', paddingBottom: 4, marginBottom: 8 }}>
        <h2 style={{ fontSize: 14, fontWeight: 700, textTransform: 'uppercase', margin: 0, fontFamily: "'IBM Plex Mono', monospace" }}>
          📝 Módulo 01: Registro Contable
        </h2>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* TIPO DE REGISTRO */}
        <div>
          <label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', display: 'block', marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
            Tipo de Registro
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', border: '2px solid #000', background: '#f5f5f0', padding: 2 }}>
            {["INGRESO", "GASTO", "TRANSFERENCIA"].map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setFormType(t)}
                style={{
                  padding: '6px 0',
                  fontSize: 10,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  border: 'none',
                  borderRight: t !== 'TRANSFERENCIA' ? '1px solid #000' : 'none',
                  fontFamily: "'IBM Plex Mono', monospace",
                  cursor: 'pointer',
                  background: formType === t 
                    ? (t === "INGRESO" ? "#00e676" : t === "GASTO" ? "#ff3333" : "#000")
                    : "transparent",
                  color: formType === t 
                    ? (t === "INGRESO" ? "#000" : "#fff") 
                    : "#000"
                }}
              >
                {t.substring(0, 5)}
              </button>
            ))}
          </div>
        </div>

        {/* IMPORTE Y FECHA */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <div>
            <label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', display: 'block', marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
              Importe ($)*
            </label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
              placeholder="Monto"
              style={{ width: '100%', background: '#fff', border: '2px solid #000', padding: 8, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace", outline: 'none' }}
            />
          </div>
          <div>
            <label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', display: 'block', marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
              Fecha*
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
              style={{ width: '100%', background: '#fff', border: '2px solid #000', padding: 8, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace", outline: 'none' }}
            />
          </div>
        </div>

        {/* CONCEPTO */}
        <div>
          <label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', display: 'block', marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
            Concepto*
          </label>
          <input
            type="text"
            value={concept}
            onChange={(e) => setConcept(e.target.value)}
            required
            placeholder="ej. Honorarios consultoría"
            style={{ width: '100%', background: '#fff', border: '2px solid #000', padding: 8, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace", outline: 'none' }}
          />
        </div>

        {/* CUENTA Y DIVISA */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <div>
            <label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', display: 'block', marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
              Cuenta*
            </label>
            <select 
              value={selectedAccountId}
              onChange={handleAccountChange}
              required
              style={{ width: '100%', background: '#fff', border: '2px solid #000', padding: 8, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace", outline: 'none' }}
            >
              <option value="">Seleccione...</option>
              {accounts.map(acc => (
                <option key={acc.id} value={acc.id}>{acc.name} ({acc.currency})</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', display: 'block', marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
              Divisa
            </label>
            <select 
              value={txCurrency}
              onChange={(e) => setTxCurrency(e.target.value)}
              style={{ width: '100%', background: '#fff', border: '2px solid #000', padding: 8, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace", outline: 'none' }}
            >
              <option value="COP">COP</option>
              <option value="USD">USD</option>
            </select>
          </div>
        </div>

        {/* EVIDENCIA */}
        <div style={{ border: '2px solid #000', padding: 8, background: '#fff', marginTop: 4 }}>
          <label style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', display: 'block', marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
            EVIDENCIA / COMPROBANTE
          </label>
          <label style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            border: '2px dashed #000', padding: 12, background: '#fafaf5', cursor: 'pointer'
          }}>
            <span style={{ fontSize: 20, marginBottom: 4 }}>📷</span>
            <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', fontFamily: "'IBM Plex Mono', monospace", textAlign: 'center' }}>
              {isUploadingEvidence 
                ? "SUBIENDO..." 
                : evidenceFilePath 
                  ? `✅ SUBIDO: ${evidenceFilePath.split('/').pop()}` 
                  : "SUBIR COMPROBANTE"}
            </span>
            <input 
              type="file" 
              accept="image/*,application/pdf"
              onChange={handleUploadEvidence}
              style={{ display: 'none' }} 
            />
          </label>
        </div>

        {/* TERCERO VINCULADO (Muestra visual si hay uno) */}
        {draft.thirdParty?.id && (
          <div style={{ background: '#e8ffe8', border: '2px dashed #00e676', padding: 8, fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>
            🔗 <strong>Tercero vinculado:</strong> {draft.thirdParty.name} ({draft.thirdParty.identification_type} {draft.thirdParty.identification_number})
          </div>
        )}

        {/* BOTON REGISTRAR */}
        <button
          type="submit"
          disabled={isSubmitting}
          style={{
            width: '100%', background: '#000', color: '#00e676', border: '3px solid #000', 
            padding: 12, fontSize: 14, fontWeight: 800, textTransform: 'uppercase',
            fontFamily: "'IBM Plex Mono', monospace", cursor: isSubmitting ? 'not-allowed' : 'pointer', marginTop: 4,
            boxShadow: '3px 3px 0 #000', opacity: isSubmitting ? 0.7 : 1
          }}
        >
          {isSubmitting ? "REGISTRANDO..." : "REGISTRAR ✔"}
        </button>
      </form>
    </div>
  );
}
