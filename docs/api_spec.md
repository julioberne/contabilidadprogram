# 🔌 FIN-SYS OS v2.0 — Especificación de la API REST

> **Motor**: FastAPI (Python 3.10+) · **Puerto**: `8000`
> **Última actualización**: 09 Junio 2026

---

## Resumen de Rutas

| Prefijo | Área | Endpoints |
|---|---|---|
| `/api/portfolios` | Portafolios / Negocios | GET |
| `/api/transactions` | Libro Diario | GET, POST, PUT, DELETE |
| `/api/transactions/voice` | Ingestión por Voz | POST |
| `/api/accounts` | Cuentas Bancarias | GET, POST, PUT |
| `/api/profile` | Perfil de Usuario | GET, PUT |
| `/api/third-parties` | Terceros (CXC/CXP) | GET, POST |
| `/api/cxc` | Cartera CXC/CXP | GET, POST, PUT |
| `/api/assets` | Activos Patrimoniales | GET, POST |
| `/api/balance` | Caja Viva Consolidada | GET |
| **`/api/ct/users`** | **CT: Usuarios** | GET, POST |
| **`/api/ct/users/login`** | **CT: Autenticación** | POST |
| **`/api/ct/entities`** | **CT: Árbol Entidades** | GET, POST, PATCH, DELETE |
| **`/api/ct/entities/{id}/kpis`** | **CT: KPIs Consolidados** | GET |
| **`/api/ct/entities/{id}/members`** | **CT: Colaboradores** | GET, POST |
| **`/api/ct/resources`** | **CT: Resource IDs** | GET, POST, DELETE |
| **`/api/ct/approvals`** | **CT: Aprobaciones** | GET, POST |
| **`/api/ct/approvals/{id}/resolve`** | **CT: Resolver Aprobación** | PATCH |
| **`/api/ct/quick-transaction`** | **CT: TX Rápida** | POST |

---

## 1. Módulos Principales (App)

### `POST /api/transactions/voice`
Recibe audio del navegador, transcribe con Groq Whisper, estructura con Llama 3.3 y guarda como BORRADOR.

**Request**: `multipart/form-data`
- `audio_file`: blob de audio (WebM Opus / OGG)
- `portfolio_name`: nombre del portafolio destino

**Response `200 OK`**:
```json
{
  "status": "BORRADOR",
  "transcript": "Pago a Kelly Durán por valor de cincuenta mil pesos",
  "parsed_data": {
    "type": "GASTO",
    "amount": 50000.00,
    "concept": "Pago servicios",
    "payment_method": null,
    "category": "Servicios",
    "third_party_name": "Kelly Durán",
    "third_party_id_type": null,
    "third_party_id_number": null
  },
  "missing_fields": ["payment_method", "third_party_id_number"],
  "transaction_id": 42
}
```

---

### `GET /api/transactions`
Lista el libro diario con filtros opcionales.

**Query params**:
- `portfolio` — filtra por portafolio
- `category` — filtra por categoría
- `start_date` / `end_date` — rango de fechas
- `limit` — default 100

**Response `200 OK`**: Array de transacciones con datos de tercero, cuenta, impuestos y CXC.

---

### `POST /api/transactions`
Registra una transacción manual.

**Request Body**:
```json
{
  "portfolio_name": "Negocio A",
  "type": "GASTO",
  "amount": 150000.00,
  "concept": "Pago arriendo oficina",
  "payment_method": "Bancolombia Ahorros",
  "category": "Infraestructura",
  "transaction_date": "2026-06-09",
  "account_id": 2,
  "apply_iva": false,
  "apply_gmf": true,
  "third_party_name": "Inmobiliaria Central",
  "third_party_id_type": "NIT",
  "third_party_id_number": "900.234.567-1",
  "evidence_file_path": "/uploads/recibo_arriendo.pdf"
}
```

**Response `201 Created`**:
```json
{ "status": "EXITOSO", "transaction_id": 19, "net_value": 149400.0 }
```

---

### `PUT /api/transactions/{id}`
Edita una celda del libro diario (edición inline estilo Excel).

```json
{ "field": "concept", "value": "Pago arriendo julio 2026" }
```

---

### `GET /api/balance`
Devuelve el consolidado de Caja Viva en tiempo real.

**Response `200 OK`**:
```json
{
  "cop": { "ingresos": 68575000.0, "gastos": 26352500.0, "balance": 42222500.0 },
  "usd": { "ingresos": 100.0,     "gastos": 0.0,         "balance": 100.0 },
  "patrimonio_neto": 47222500.0,
  "alertas": []
}
```

---

## 2. Control Tower API (`/api/ct/*`)

### `POST /api/ct/users/register`
Registra un nuevo workspace_user.

```json
{
  "name": "María Contadora",
  "email": "maria@finsys.os",
  "password": "maria2024",
  "role_label": "Contador Externo",
  "permissions": { "ledger": true, "reports": true, "users": false, "approvals": true }
}
```

**Response `201`**: `{ "status": "OK", "user": { "id": 2, "name": "...", ... } }`

---

### `POST /api/ct/users/login`
Autentica un workspace_user.

```json
{ "email": "andres@finsys.os", "password": "admin123" }
```

**Response `200`**: `{ "status": "OK", "user": { "id": 1, "role_label": "Super-Contador", "permissions": {...} } }`

---

### `GET /api/ct/entities`
Retorna el árbol completo de entidades en formato anidado (children recursivos).

**Response `200`**: Array con estructura `{ id, name, type, parent_id, portfolio_id, status, children: [...] }`

---

### `POST /api/ct/entities`
Crea una nueva entidad en el árbol.

```json
{
  "name": "Constructora Norte SAS",
  "type": "EMPRESA",
  "parent_id": 1,
  "portfolio_id": 4,
  "industry": "CONSTRUCCION",
  "sub_industry": "Vivienda VIS",
  "status": "ALERTA"
}
```

---

### `GET /api/ct/entities/{entity_id}/kpis`
Calcula KPIs consolidados de una entidad y toda su jerarquía descendiente.

**Response `200`**:
```json
{
  "total_ingresos": 68575000.0,
  "total_gastos": 26352500.0,
  "balance_neto": 42222500.0,
  "total_cxc": 7500000.0,
  "pending_approvals": 4,
  "child_entities": 3,
  "entity_ids_in_scope": 7
}
```
*Nota: usa CTE recursivo para sumar portfolios de toda la sub-jerarquía.*

---

### `POST /api/ct/entities/{entity_id}/members`
Asigna un colaborador a una entidad con rol y permisos.

```json
{
  "user_id": 2,
  "role_label": "Contadora Principal",
  "permissions": { "ledger": true, "reports": true, "users": false, "approvals": true }
}
```

---

### `GET /api/ct/resources?entity_id={id}`
Lista los resource_ids de una entidad.

**Response `200`**: Array `{ id, label, value, category, expires_at, notes }`

---

### `POST /api/ct/resources`
Registra un ID/documento para una entidad.

```json
{
  "entity_id": 2,
  "label": "Licencia Operación MEN",
  "value": "LIC-MEN-2024-001234",
  "category": "LEGAL",
  "expires_at": "2025-06-30",
  "notes": "⚠️ Renovar urgente"
}
```

---

### `POST /api/ct/approvals`
Crea una solicitud de aprobación de gasto.

```json
{
  "entity_id": 2,
  "description": "Pago nómina educadoras julio 2026",
  "amount": 8500000,
  "requested_by": 1
}
```

---

### `PATCH /api/ct/approvals/{id}/resolve`
Aprueba o rechaza una solicitud.

```json
{
  "status": "APROBADO",
  "reviewer_id": 1,
  "notes": "Aprobado — presupuesto disponible confirmado"
}
```

---

### `POST /api/ct/quick-transaction`
Registra una transacción rápida desde el Control Tower.

```json
{
  "entity_id": 2,
  "portfolio_name": "EMPRESA INFANTIL PEGASUS",
  "type": "INGRESO",
  "amount": 3800000,
  "concept": "Matrícula alumnos nuevos julio 2026",
  "category": "Ventas",
  "payment_method": "Transferencia",
  "third_party_name": "Familias Nuevas Grupo 2026",
  "third_party_id_number": "N/A",
  "third_party_id_type": "NIT"
}
```

**Response `201`**: `{ "status": "EXITOSO", "transaction_id": 17 }`

---

## 3. Esquemas Pydantic Principales

```python
class TransactionInput(BaseModel):
    portfolio_name: str
    type: str                    # 'INGRESO' | 'GASTO' | 'TRANSFERENCIA'
    amount: float
    concept: str
    payment_method: Optional[str] = None
    category: Optional[str] = "General"
    transaction_date: Optional[str] = None
    account_id: Optional[int] = None
    dest_account_id: Optional[int] = None
    transaction_currency: Optional[str] = "COP"
    trm: Optional[float] = 1.0
    apply_iva: bool = False
    apply_gmf: bool = False
    third_party_name: Optional[str] = None
    third_party_id_type: Optional[str] = None
    third_party_id_number: Optional[str] = None
    evidence_file_path: Optional[str] = None
    is_recurring: bool = False
    recurrence_interval: Optional[str] = "MENSUAL"
    # CXC / CXP
    cxc_type: Optional[str] = None         # 'CXC' | 'CXP'
    cxc_due_date: Optional[str] = None
    cxc_term: Optional[str] = None         # 'Corto' | 'Mediano' | 'Largo'
    # Activos
    asset_name: Optional[str] = None
    asset_tag: Optional[str] = None
    asset_is_passive: bool = False
    asset_recurrence_amount: Optional[float] = None
```
