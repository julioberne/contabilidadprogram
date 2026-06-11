---
name: multi-currency-ledger-setup
description: Guía de aprovisionamiento e integración de perfiles de usuario, cuentas financieras multi-moneda (COP/USD), TRM manual, recálculos contables en Python y edición interactiva por celda (tipo Excel) en React.
license: MIT
metadata:
  author: Antigravity
  version: "1.0.0"
  date: June 2026
  abstract: Este skill provee esquemas SQL, algoritmos en Python y patrones en React para implementar la gestión de cuentas multi-moneda con recálculo determinista, control de insolvencia y edición inline directa (doble clic) en caliente.
---

# Multi-Currency Ledger & User Profile Setup

Este skill enseña a los agentes de codificación cómo aprovisionar e integrar un sistema contable multi-moneda dinámico con perfiles de usuario y edición interactiva estilo Excel en caliente utilizando FastAPI y React.

---

## 📂 Esquema de Base de Datos (PostgreSQL)

Para dar soporte a usuarios, cuentas individuales y transacciones multi-moneda, se deben aprovisionar las siguientes tablas y columnas:

```sql
-- 1. Perfil del Usuario Principal
CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL DEFAULT 'Andrés',
    email VARCHAR(100) NOT NULL DEFAULT 'admin@finsys.os',
    role VARCHAR(50) NOT NULL DEFAULT 'Administrador Contable',
    avatar_style VARCHAR(50) NOT NULL DEFAULT 'pixel-grid',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Cuentas Financieras del Usuario
CREATE TABLE IF NOT EXISTS user_accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL, -- 'Ahorros', 'Corriente', 'Crédito', 'Crypto'
    currency VARCHAR(10) NOT NULL DEFAULT 'COP', -- 'COP', 'USD'
    initial_balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    current_balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Modificaciones a la Tabla de Transacciones
-- Asegurar que existan estas columnas para vincular transacciones a cuentas y manejar tasas de cambio:
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES user_accounts(id);
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS dest_account_id INTEGER REFERENCES user_accounts(id); -- Para transferencias cruzadas
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS trm DECIMAL(12, 4) DEFAULT 1.0000; -- Tasa de cambio manual (ej. 1 USD = X COP)
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS transaction_currency VARCHAR(10) DEFAULT 'COP';
```

---

## 🧮 Motor de Recálculo de Saldos (Python / Backend)

Para evitar desajustes por operaciones de incremento/decremento concurrentes, los saldos de las cuentas deben recalcularse dinámicamente escaneando el historial de transacciones en orden cronológico.

```python
def recalcular_saldos_cuentas(db_connection):
    """
    Recalcula desde cero el saldo actual (current_balance) de todas las cuentas 
    recorriendo el historial de transacciones de forma cronológica.
    """
    # 1. Obtener todas las cuentas y mapear sus saldos al valor inicial
    cuentas = db_connection.execute("SELECT id, initial_balance, currency FROM user_accounts").fetchall()
    saldos = {c['id']: {"balance": float(c['initial_balance']), "currency": c['currency']} for c in cuentas}
    
    # 2. Cargar todas las transacciones confirmadas en orden cronológico
    txs = db_connection.execute(
        "SELECT id, type, value, account_id, dest_account_id, trm, transaction_currency "
        "FROM transactions WHERE status = 'CONFIRMADA' ORDER BY date ASC, id ASC"
    ).fetchall()
    
    # 3. Aplicar cada transacción según su tipo
    for tx in txs:
        val = float(tx['value'])
        acc_id = tx['account_id']
        dest_id = tx['dest_account_id']
        trm_val = float(tx['trm'] or 1.0)
        tx_curr = tx['transaction_currency']
        
        if tx['type'] == 'Ingreso' and acc_id in saldos:
            acc_curr = saldos[acc_id]['currency']
            # Convertir valor si la moneda de la transacción difiere de la cuenta
            converted_val = val
            if tx_curr != acc_curr:
                converted_val = val * trm_val if acc_curr == 'COP' else val / trm_val
            saldos[acc_id]['balance'] += converted_val
            
        elif tx['type'] == 'Gasto' and acc_id in saldos:
            acc_curr = saldos[acc_id]['currency']
            converted_val = val
            if tx_curr != acc_curr:
                converted_val = val * trm_val if acc_curr == 'COP' else val / trm_val
            saldos[acc_id]['balance'] -= converted_val
            
        elif tx['type'] == 'Transferencia' and acc_id in saldos:
            # Origen (Debita de la cuenta emisora en su divisa)
            src_curr = saldos[acc_id]['currency']
            converted_src = val
            if tx_curr != src_curr:
                converted_src = val * trm_val if src_curr == 'COP' else val / trm_val
            saldos[acc_id]['balance'] -= converted_src
            
            # Destino (Acredita en la cuenta receptora convirtiendo con TRM si difieren)
            if dest_id and dest_id in saldos:
                dest_curr = saldos[dest_id]['currency']
                converted_dest = val
                # Si la moneda de la transacción difiere del destino, convertir usando la TRM manual
                if tx_curr != dest_curr:
                    converted_dest = val * trm_val if dest_curr == 'COP' else val / trm_val
                saldos[dest_id]['balance'] += converted_dest

    # 4. Persistir los saldos recalculados en la base de datos
    for acc_id, data in saldos.items():
        db_connection.execute(
            "UPDATE user_accounts SET current_balance = %s WHERE id = %s",
            (data['balance'], acc_id)
        )
```

---

## 💱 Entrada de TRM Manual (React / Frontend)

Al crear o editar una transacción de tipo **Transferencia** o un movimiento cruzado donde las monedas de la cuenta origen y destino difieren, la interfaz debe solicitar dinámicamente un valor de **TRM Manual**.

```javascript
// Ejemplo de lógica en el formulario React
const shouldShowTRM = () => {
  if (formData.type === 'Transferencia') {
    const srcAccount = accounts.find(a => a.id === parseInt(formData.account_id));
    const destAccount = accounts.find(a => a.id === parseInt(formData.dest_account_id));
    return srcAccount && destAccount && srcAccount.currency !== destAccount.currency;
  }
  return false;
};

// Renderizado condicional en JSX:
{shouldShowTRM() && (
  <div className="form-group border-2 border-black p-2 bg-yellow-100">
    <label className="font-mono text-xs block uppercase font-bold">
      Tasa de Cambio Manual (TRM: 1 USD = X COP)
    </label>
    <input
      type="number"
      step="0.0001"
      name="trm"
      value={formData.trm}
      onChange={handleInputChange}
      className="w-full bg-white font-mono p-1 border-2 border-black focus:outline-none"
      required
    />
  </div>
)}
```

---

## 📊 Consolidación de Caja Viva Apilada

Las métricas principales de Caja Viva no deben sumarse arbitrariamente. Deben agruparse por divisa y renderizarse en formato apilado:

```javascript
// Componente de Métrica Brutalista
const MetricCard = ({ title, values }) => {
  // values = { COP: 1500000, USD: 350 }
  return (
    <div className="border-4 border-black p-4 bg-white shadow-[4px_4px_0px_0px_#000]">
      <h3 className="font-mono text-sm uppercase text-gray-500">{title}</h3>
      <div className="mt-2 space-y-1">
        {values.COP !== undefined && (
          <p className="font-mono text-2xl font-bold text-green-600">
            ${values.COP.toLocaleString('es-CO')} <span className="text-sm">COP</span>
          </p>
        )}
        {values.USD !== undefined && (
          <p className="font-mono text-2xl font-bold text-blue-600">
            ${values.USD.toLocaleString('en-US', { minimumFractionDigits: 2 })} <span className="text-sm">USD</span>
          </p>
        )}
      </div>
    </div>
  );
};
```

---

## 📝 Edición tipo Excel Directa (Inline Cell Editing)

La tabla del Libro Diario debe permitir la edición directa en caliente de celdas clave (Concepto, Valor, Fecha, Categoría) al hacer doble clic, con sincronización automática en el backend mediante un llamado `PATCH`.

```javascript
// Componente de celda editable en React (Diario.jsx / App.jsx)
const EditableCell = ({ value, onSave, type = "text" }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [tempValue, setTempValue] = useState(value);
  const inputRef = useRef(null);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isEditing]);

  const handleBlur = () => {
    setIsEditing(false);
    if (tempValue !== value) {
      onSave(tempValue);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      setIsEditing(false);
      if (tempValue !== value) {
        onSave(tempValue);
      }
    } else if (e.key === 'Escape') {
      setIsEditing(false);
      setTempValue(value);
    }
  };

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        type={type}
        value={tempValue}
        onChange={(e) => setTempValue(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className="w-full bg-yellow-100 font-mono p-1 border border-black focus:outline-none"
      />
    );
  }

  return (
    <div 
      onDoubleClick={() => setIsEditing(true)} 
      className="cursor-pointer hover:bg-gray-100 p-1 font-mono select-none"
      title="Doble clic para editar"
    >
      {type === "number" ? parseFloat(value).toLocaleString() : value}
    </div>
  );
};
```

El backend debe capturar este evento con un endpoint de actualización parcial:
```python
@app.patch("/api/transactions/{tx_id}")
async def patch_transaction(tx_id: int, updates: dict):
    # 1. Aplicar actualizaciones parciales en la base de datos
    # 2. Ejecutar recalcular_saldos_cuentas(db)
    # 3. Devolver estado de éxito y los nuevos balances consolidados
    pass
```

---

## 🚨 Control de Insolvencia y Sobregiro

Si el patrimonio neto consolidado o el saldo de una cuenta cae por debajo de los límites estipulados:
1. ** Backend **: Agregar claves de diagnóstico en la respuesta de Caja Viva (ej. `{"insolvente": true, "alertas": ["Cupo excedido en Davivienda"]}`).
2. ** Frontend **:
   * Dibujar un banner de advertencia rojo brutalista animado en la parte superior.
   * Pintar de color rojo de alerta (`#FF3333`) las tarjetas de las cuentas o métricas afectadas.

---

## 🔌 Modo Simulación Fallback (Mock)

En caso de desconexión o fallo en el driver de base de datos PostgreSQL, el sistema debe degradarse graciosamente y levantar listas en memoria temporal para garantizar la disponibilidad local:

```python
MOCK_ACCOUNTS = [
    {"id": 1, "name": "Bancolombia Ahorros", "type": "Ahorros", "currency": "COP", "initial_balance": 1000000.0, "current_balance": 1000000.0},
    {"id": 2, "name": "Davivienda Crédito", "type": "Crédito", "currency": "COP", "initial_balance": 0.0, "current_balance": 0.0},
    {"id": 3, "name": "Binance Crypto", "type": "Crypto", "currency": "USD", "initial_balance": 500.0, "current_balance": 500.0}
]

MOCK_TRANSACTIONS = []
```
Las operaciones de lectura/escritura operarán sobre estas listas en memoria volátil si la base de datos se encuentra inaccesible.
