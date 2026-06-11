import React, { useState, useEffect } from 'react';

const API_BASE_URL = "http://127.0.0.1:8000/api";

export default function CoaTest() {
  const [treeData, setTreeData] = useState([]);
  const [currentTemplate, setCurrentTemplate] = useState("NINGUNA");
  const portfolio = "Negocio A"; // Hardcoded for testing

  // Form states for manual entry
  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("ACTIVO");
  const [newParentCode, setNewParentCode] = useState("");
  const [isGroup, setIsGroup] = useState(false);

  const fetchCoa = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/coa?portfolio=${encodeURIComponent(portfolio)}`);
      const data = await res.json();
      if (data.status === "OK") {
        setTreeData(data.data);
      }
    } catch (e) {
      console.error("Error fetching COA:", e);
    }
  };

  useEffect(() => {
    fetchCoa();
  }, []);

  const loadTemplate = async (templateName) => {
    if (templateName === "NINGUNA") {
      setTreeData([]);
      setCurrentTemplate("NINGUNA");
      return;
    }
    
    try {
      const res = await fetch(`${API_BASE_URL}/coa/template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio_name: portfolio, template_name: templateName })
      });
      const data = await res.json();
      if (data.status === "CARGADO") {
        setCurrentTemplate(templateName);
        fetchCoa(); // Reload tree from backend
      } else {
        alert(data.detail || "Error loading template");
      }
    } catch (e) {
      console.error("Error loading template:", e);
    }
  };

  const handleAddAccount = async (e) => {
    e.preventDefault();
    if (!newCode || !newName) return;
    
    try {
      const res = await fetch(`${API_BASE_URL}/coa/account`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          portfolio_name: portfolio,
          code: newCode,
          name: newName,
          type: newType,
          is_group: isGroup,
          parent_code: newParentCode || null
        })
      });
      const data = await res.json();
      if (data.status === "CREADO") {
        setNewCode("");
        setNewName("");
        setNewParentCode("");
        fetchCoa(); // Reload tree
      } else {
        alert(data.detail || "Error al crear cuenta");
      }
    } catch (e) {
      console.error("Error adding account:", e);
    }
  };

  const renderTree = (nodes, level = 0) => {
    return (
      <ul style={{ listStyleType: "none", paddingLeft: level === 0 ? 0 : "20px" }}>
        {nodes.map(node => (
          <li key={node.code} style={{ margin: "5px 0" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "5px", background: "rgba(255,255,255,0.05)", borderRadius: "4px" }}>
              <span style={{ color: node.is_group ? "#4facfe" : "#a8edea", fontWeight: node.is_group ? "bold" : "normal" }}>
                {node.is_group ? "📁" : "📄"} {node.code}
              </span>
              <span>- {node.name}</span>
              <span style={{ fontSize: "0.8em", padding: "2px 6px", background: "rgba(255,255,255,0.1)", borderRadius: "10px" }}>
                {node.account_type}
              </span>
            </div>
            {node.children && node.children.length > 0 && renderTree(node.children, level + 1)}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div style={{ padding: "20px", color: "#fff", background: "#1a1a2e", borderRadius: "10px", minHeight: "80vh" }}>
      <h2>🌐 Test: COA Backend Conectado (Portafolio: {portfolio})</h2>
      
      <div style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
        <button onClick={() => loadTemplate("ESTANDAR")} style={btnStyle}>Cargar ESTANDAR</button>
        <button onClick={() => loadTemplate("INMOBILIARIA")} style={btnStyle}>Cargar INMOBILIARIA</button>
        <button onClick={() => loadTemplate("CONSTRUCTORA")} style={btnStyle}>Cargar CONSTRUCTORA</button>
        <button onClick={() => loadTemplate("RETAIL")} style={btnStyle}>Cargar RETAIL</button>
        <button onClick={() => loadTemplate("NINGUNA")} style={{...btnStyle, background: "#ff4b2b"}}>Limpiar Vista</button>
      </div>

      <div style={{ display: "flex", gap: "20px" }}>
        <div style={{ flex: 1, background: "rgba(0,0,0,0.3)", padding: "15px", borderRadius: "8px" }}>
          <h3>Árbol Contable Real en BD</h3>
          <button onClick={fetchCoa} style={{...btnStyle, padding: "4px 8px", fontSize: "0.8em", marginBottom: "10px", background: "#333"}}>🔄 Refrescar</button>
          {treeData.length === 0 ? <p>No hay cuentas cargadas o BD desconectada.</p> : renderTree(treeData)}
        </div>

        <div style={{ width: "350px", background: "rgba(0,0,0,0.3)", padding: "15px", borderRadius: "8px", alignSelf: "flex-start" }}>
          <h3>Añadir Cuenta Real</h3>
          <form onSubmit={handleAddAccount} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <input placeholder="Código (ej. 110501)" value={newCode} onChange={e=>setNewCode(e.target.value)} style={inputStyle} required />
            <input placeholder="Nombre de la Cuenta" value={newName} onChange={e=>setNewName(e.target.value)} style={inputStyle} required />
            <select value={newType} onChange={e=>setNewType(e.target.value)} style={inputStyle}>
              <option value="ACTIVO">ACTIVO</option>
              <option value="PASIVO">PASIVO</option>
              <option value="PATRIMONIO">PATRIMONIO</option>
              <option value="INGRESO">INGRESO</option>
              <option value="GASTO">GASTO</option>
            </select>
            <input placeholder="Código Padre (ej. 1105)" value={newParentCode} onChange={e=>setNewParentCode(e.target.value)} style={inputStyle} />
            <label style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <input type="checkbox" checked={isGroup} onChange={e=>setIsGroup(e.target.checked)} />
              Es Grupo (Carpeta)
            </label>
            <button type="submit" style={{...btnStyle, width: "100%", marginTop: "10px", background: "#00b09b"}}>Guardar en BD</button>
          </form>
        </div>
      </div>
    </div>
  );
}

const btnStyle = {
  padding: "8px 16px",
  background: "#4facfe",
  border: "none",
  borderRadius: "5px",
  color: "white",
  cursor: "pointer",
  fontWeight: "bold"
};

const inputStyle = {
  padding: "8px",
  borderRadius: "4px",
  border: "1px solid #4facfe",
  background: "rgba(255,255,255,0.1)",
  color: "white"
};
