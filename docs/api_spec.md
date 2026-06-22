# 🔌 FIN-SYS OS v2.0 — Especificación de la API REST

> **Motor**: FastAPI (Python 3.10+) · **Puerto**: `8000`
> **Última actualización**: 18 Junio 2026
> **NOTA DE DUPLICIDAD**: Algunos flujos de uso de estos endpoints también se describen en `docs/walkthrough.md`. Este archivo es la **fuente autoritativa** de los contratos de API (request/response schemas). Para guía de uso interactivo, ver `walkthrough.md`.

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
| **`/api/hr/profile/{user_id}`** | **RRHH: Perfil** | GET, PUT |
| **`/api/hr/salary/{user_id}`** | **RRHH: Salario** | GET, PUT |
| **`/api/hr/companies/{user_id}`** | **RRHH: Empresas** | GET, POST, PUT, DELETE |
| **`/api/hr/folders/{workspace_id}`** | **RRHH: Carpetas** | GET, POST, PUT, DELETE |
| **`/api/hr/documents/{user_id}`** | **RRHH: Documentos** | GET, POST, PUT, DELETE |
| **`/api/hr/categories/{workspace_id}`** | **RRHH: Categorías** | GET, POST, PUT, DELETE |
| **`/api/hr/payments/{user_id}`** | **RRHH: Pagos** | GET, POST |
| **`/api/hr/payments/{user_id}/{rec}/voucher`** | **RRHH: Vincular Comprobante** | PUT |
| **`/api/hr/company-links`** | **RRHH: Links Empresa** | GET |

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

---

## 4. Módulo RRHH / Empresas (08c) — `/api/hr/*`

> **28 endpoints** gestionados por `fin_sys_core/hr_driver.py` y `fin_sys_core/hr_documents_driver.py`.

### 4.1 Perfil de Miembro

#### `GET /api/hr/profile/{user_id}`
Retorna el perfil RRHH de un miembro (nombre, cargo, departamento, fecha ingreso, etc.).

**Response `200`**:
```json
{ "id": 1, "full_name": "Andres", "position": "Director", "department": "Gerencia", "hire_date": "2024-01-01", "status": "ACTIVO" }
```

#### `PUT /api/hr/profile/{user_id}`
Actualiza campos del perfil. Solo los campos enviados se modifican.

```json
{ "position": "CEO", "department": "Dirección" }
```

---

### 4.2 Salario

#### `GET /api/hr/salary/{user_id}`
Retorna la estructura salarial: salario base, auxilio transporte, deducciones y neto calculado.

**Response `200`**:
```json
{
  "salario_base": 3500000,
  "auxilio_transporte": 162000,
  "salud_empleado": 140000,
  "pension_empleado": 140000,
  "neto": 3382000
}
```

#### `PUT /api/hr/salary/{user_id}`
Actualiza los campos de salario. Recalcula el neto en backend.

```json
{ "salario_base": 4000000 }
```

> **Endpoints huérfanos relacionados** (existen, no se usan):
> - `POST /api/hr/salary/calculate` — el cálculo ocurre localmente en `SalaryTab.jsx`
> - `PUT /api/hr/salary/v2/{user_id}` — versión beta, sin consumidor en frontend

---

### 4.3 Empresas / Company Links

#### `GET /api/hr/companies/{user_id}`
Listado de todas las asociaciones empresa↔miembro del usuario.

**Response `200`**: Array `{ id, user_id, company_name, role, start_date, end_date, is_current }`

#### `POST /api/hr/companies/{user_id}`
Crea una nueva asociación empresa↔miembro.

```json
{ "company_name": "Pegasus SAS", "role": "Socio", "start_date": "2024-01-01", "is_current": true }
```

#### `PUT /api/hr/companies/{user_id}/{link_id}`
Actualiza un vínculo empresa existente.

#### `DELETE /api/hr/companies/{user_id}/{link_id}`
Elimina un vínculo empresa (soft delete recomendado).

#### `GET /api/hr/company-links`
Listado global de todos los company-links (sin filtro por usuario). Uso administrativo.

---

### 4.4 Carpetas de Documentos

#### `GET /api/hr/folders/{workspace_id}`
Retorna todas las carpetas de documentos del workspace.

**Response `200`**: Array `{ id, workspace_id, name, color, created_at }`

#### `POST /api/hr/folders/{workspace_id}`
Crea una carpeta nueva.

```json
{ "name": "Contratos 2026", "color": "#00FF88" }
```

#### `PUT /api/hr/folders/{workspace_id}/{folder_id}`
Renombra o cambia color de una carpeta.

#### `DELETE /api/hr/folders/{workspace_id}/{folder_id}`
Elimina la carpeta (y sus documentos si la FK es CASCADE).

---

### 4.5 Documentos

#### `GET /api/hr/documents/{user_id}`
Retorna todos los documentos de un miembro. Incluye `file_url` (puede ser data URL base64 para HTMLs).

**Response `200`**: Array `{ id, user_id, folder_id, category_id, name, file_url, created_at }`

#### `POST /api/hr/documents/{user_id}`
Sube metadatos de un documento. El archivo se referencia vía `file_url`.

```json
{
  "name": "Comprobante Pago Jun 2026",
  "folder_id": 2,
  "category_id": 1,
  "file_url": "data:text/html;base64,PHRtbC4uLg=="
}
```

> **Nota**: Para comprobantes HTML, `file_url` es una data URL base64 (no una ruta de Storage).
> Ver patrón completo en `memory-bank/systemPatterns.md → Patrón: Almacenamiento de Documentos HTML`.

#### `PUT /api/hr/documents/{user_id}/{doc_id}`
Actualiza metadatos de un documento (nombre, carpeta, categoría).

#### `DELETE /api/hr/documents/{user_id}/{doc_id}`
Elimina un documento y su referencia.

> **Endpoint huérfano relacionado**:
> - `POST /api/hr/storage/sign-upload` — reemplazado por data URL. No usar hasta resolver MIME restrictions.

---

### 4.6 Categorías de Documentos

#### `GET /api/hr/categories/{workspace_id}`
Listado de categorías disponibles en el workspace (ej: Contrato, Certificado, Comprobante).

**Response `200`**: Array `{ id, workspace_id, name, color }`

#### `POST /api/hr/categories/{workspace_id}`
Crea una categoría nueva.

```json
{ "name": "Comprobante de Pago", "color": "#FFB000" }
```

#### `PUT /api/hr/categories/{workspace_id}/{cat_id}`
Edita nombre o color de una categoría.

#### `DELETE /api/hr/categories/{workspace_id}/{cat_id}`
Elimina una categoría (solo si no tiene documentos asignados).

---

### 4.7 Pagos / Historial

#### `GET /api/hr/payments/{user_id}`
Historial completo de pagos del miembro, con datos del comprobante vinculado si existe.

**Response `200`**:
```json
[
  {
    "id": 1,
    "user_id": 1,
    "period": "2026-06",
    "amount": 3382000,
    "payment_date": "2026-06-01",
    "payment_method": "Transferencia",
    "status": "PAGADO",
    "voucher_doc_id": 5,
    "notes": null
  }
]
```

#### `POST /api/hr/payments/{user_id}`
Registra un nuevo pago de nómina.

```json
{
  "period": "2026-06",
  "amount": 3382000,
  "payment_date": "2026-06-18",
  "payment_method": "Transferencia",
  "status": "PAGADO",
  "notes": "Pago nomina junio"
}
```

**Response `201`**: `{ "id": 1, "status": "OK" }`

#### `PUT /api/hr/payments/{user_id}/{record_id}/voucher`
Vincula un documento existente como comprobante de un pago.

**Query params**: `?doc_id={id}`

**Response `200`**: `{ "status": "OK", "voucher_doc_id": 5 }`

> Este endpoint es el paso final del flujo de generación de comprobantes en `HistorialTab.jsx`.
