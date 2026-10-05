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
| `/api/third-parties` | Terceros (CXC/CXP) | GET, POST, PUT, DELETE |
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
> Ver patrón completo en `docs/system_patterns.md → Patrón: Almacenamiento de Documentos HTML`.

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

---

## 5. Bot IA (09) — Webhook de SMS bancarios (`/api/webhooks/sms*`)

> Etapa 09.F · Spec: `docs/specs/09-bot-ia/09.F-sms-bancolombia.md` · Router: `routers/webhooks_sms.py`.
> El webhook solo **encola** (bot_messages, channel `sms`); el poller de Telegram convierte y envía (≤ 45 s).

### `POST /api/webhooks/sms`
- **Auth**: header `X-SMS-Token` (token por teléfono, tabla `sms_ingest_tokens`).
- **Body** (≤ 4096 bytes): `text/plain` — el cuerpo ES el SMS y el remitente va en la cabecera `X-SMS-From` (**lo recomendado desde MacroDroid**: no hay que escapar nada) · `application/json` `{ "from": "85540", "text": "<SMS>", "sentStamp"?: "…" }` · `application/x-www-form-urlencoded` `from=…&text=…` (también acepta `sms_number` / `sms_message`).
- **Respuestas**: `202 {"status":"ACEPTADO","id":n,"chat_vinculado":bool}` · `202 {"status":"DUPLICADO"}` · `400` JSON inválido · `401` sin token / token inválido o revocado · `403` remitente fuera del allowlist · `413` cuerpo > 4 KB · `415` Content-Type no soportado · `422` texto vacío · `429` ≥ 60 SMS/min.

### `POST /api/webhooks/sms/token` (sesión `Bearer`)
- Body opcional `{ "label": "Moto", "remitentes": ["85540"] }` → `201 { id, token, label, remitentes, instrucciones }`. **El token plano solo se devuelve aquí.**

### `GET /api/webhooks/sms/tokens` (sesión) → `[ { id, label, remitentes, created_at, last_seen_at, revoked_at } ]`

### `DELETE /api/webhooks/sms/tokens/{id}` (sesión) → `{"status":"REVOCADO","id"}` · `404` si no existe o ya estaba revocado.

### Cambios en `POST/PUT /api/accounts`
`AccountInput` / `AccountUpdateInput` aceptan `last4_cuenta` y `last4_tarjeta` (4 dígitos; en PUT `""` borra, ausente no toca). `GET /api/accounts` devuelve ambos campos.

---

## 6. Bot IA (09) — Medios de pago de un tercero (`/api/third-parties/{tp_id}/accounts*`)

> Etapa 09.G §10 · Spec: `docs/specs/09-bot-ia/09.G-completar-borrador.md` · Router: `routers/third_party_accounts.py` · Lógica: `fin_sys_core/terceros_cuentas.py` · Tabla: `third_party_accounts`.
> "Medio de pago" = cuenta, celular, llave o nombre con que el banco llama al tercero en sus SMS. El bot lo cruza por igualdad para traer el tercero ya puesto en el borrador. Lo registra una persona (aquí o con el botón 💾 del bot).

Objeto `medio`: `{ id, third_party_id, tipo, valor, banco, etiqueta, origen, created_at, descripcion }` — `tipo` ∈ `celular` · `cuenta` · `llave` · `nombre_banco`; `valor` ya normalizado; `origen` ∈ `web` · `bot`; `descripcion` = texto corto (`cel 3213795458`, `cuenta *91232656625`, `llave 0087671656`, `«SANDRA JIMENEZ»`).

### `GET /api/third-parties/{tp_id}/accounts` (sesión) → `[ medio, … ]`

### `POST /api/third-parties/{tp_id}/accounts` (admin)
- **Body**: `{ "tipo": "celular", "valor": "+57 321 379 5458", "banco"?: "Nequi", "etiqueta"?: "…" }` (el valor se normaliza en el servidor).
- **Respuestas**: `201 {"status":"CREADO","medio":{…}}` · `201 {"status":"YA_EXISTIA","medio":{…}}` (ya estaba en esta ficha) · `409` ya está registrado en la ficha de **otro** tercero (`detail` dice de quién) · `404` el tercero no existe · `422` tipo o valor inválido, o es el tercero genérico.

### `POST /api/third-parties/{tp_id}/accounts/mover` (admin)
- Decisión explícita: el medio deja la ficha donde estaba y pasa a esta. **Body**: `{ "tipo": "cuenta", "valor": "91232656625" }`.
- **Respuestas**: `200 {"status":"MOVIDO","medios":[…]}` · `404` el tercero o el medio no existen · `422` tipo/valor inválido o tercero genérico.

### `DELETE /api/third-parties/{tp_id}/accounts/{medio_id}` (admin) → `{"status":"ELIMINADO","id"}` · `404` si ese medio no está en esta ficha.

---

## 7. Terceros (Contabilidad) — borrar una ficha (`DELETE /api/third-parties/{tp_id}`)

> Desde el 30-sep-2026 · Router: `routers/cartera.py` (junto al `POST`/`PUT` de terceros) · Lógica: `fin_sys_core/terceros_borrado.py` · Consumidor: 👤 Terceros → 🗑 (`ContextPanel.deleteItem`, que muestra el `detail` en el aviso del panel).
> Regla (decisión de Andrés): un tercero **con historia** no se borra; nada se reasigna ni se deja en NULL (`transactions.third_party_id` y `cxp_cxc_ledger.third_party_id` son `NOT NULL` + `ON DELETE RESTRICT`; Regla 5). `database_driver.eliminar_tercero` queda sin usar: intentaba poner esos FK en NULL.

### `DELETE /api/third-parties/{tp_id}` (admin)
- **Respuestas**: `200 {"status":"ELIMINADO","id","name"}` (sus medios de pago `third_party_accounts` caen en cascada) · `404` no existe · `409` es el genérico `999999999` («Sin especificar») · `409` tiene historia: el `detail` dice cuánta, p. ej. `No se puede eliminar a «X»: tiene 18 transacciones y 1 cuenta de cartera (CXC/CXP). …`.
- **Historia** = transacciones, cuentas de cartera (CXC/CXP), movimientos de inventario (el FK los dejaría en NULL en silencio) y **borradores abiertos del bot** (`transaction_drafts` en `BORRADOR`/`PROCESANDO`/`ERROR` cuyo `payload.third_party.identification_number` es el suyo: al confirmarse, el tercero reaparecería solo). Todo en una transacción con la fila bloqueada (`FOR UPDATE`).

## 8. Mini App de Telegram (09.I v1) — borrador + ficha del tercero desde el chat

La Mini App es la misma web (`frontend/tg.html` → `src/tg/`), abierta dentro de Telegram por el botón
`📝 Completar tercero` de cada borrador (`web_app` con URL `https://finsys-andres.duckdns.org/tg.html?draft=N`).
Usa la **misma sesión** de la web (`POST /api/hub/users/login`, token Bearer) y los endpoints existentes de
terceros (`GET /api/third-parties`, `PUT`, `DELETE`, `…/accounts*`). Lo nuevo:

### `GET /api/bot/drafts/{draft_id}` (sesión) → borrador del usuario actual
Mismos campos que la bandeja (`GET /api/bot/drafts`) más `chat_channel` (canal del chat al que pertenece) y
`editable` (`true` si está en BORRADOR o ERROR). `404` si no existe o no es del usuario.

### `PUT /api/bot/drafts/{draft_id}` (sesión) — campo nuevo `avisar_chat`
Igual que antes (`editar_draft`, sin LLM). Con `"avisar_chat": true` en el cuerpo, además deja la marca
`payload.avisar_chat` y la respuesta trae `"avisar_chat": true`. El **poller** (único proceso que habla con
Telegram, D-09F-01) la recoge en su siguiente vuelta (`bot_driver.avisar_chat_pendientes`), quita la marca y
reenvía al chat el resumen actualizado con sus botones (latencia ≤ 45 s). El backend NO necesita el token del bot.

### `POST /api/third-parties` (admin) — cambios de 09.I
- Sin `identification_number` (o vacío) el tercero nace **provisional** `SN-<epoch ms hex>`; antes se guardaba
  `''` y el segundo tercero sin número chocaba con el UNIQUE y salía como un 500 crudo.
- Si el documento ya es de otra ficha: **`409 {"codigo":"existe","detail":"Ese documento ya pertenece a «X» (CC N).","tercero":{id,name,identification_type,identification_number,email,phone}}`**.
  El sistema informa, nunca pisa ni duplica (D-09I-08); el formulario ofrece «Usar esa ficha».
- Respuesta `200`: `{id, name, identification_type, identification_number, provisional, status:"CREADO"}`.
- Tipo de documento fuera del catálogo (`NIT|CC|CE|PP`), valor que no es texto o que no cabe en la tabla → `422` (antes 500 crudo).
  El `tercero` del 409 trae la ficha completa (`email, phone, website, address`).

### `PUT /api/third-parties/{tp_id}` (admin) — mismo contrato que el POST (revisión 1-oct)
Edición deliberada de la ficha (panel Terceros y Mini App). Solo entran los campos presentes en el cuerpo, recortados.
`identification_number` vacío o `999999999` → `400`; documento de otra ficha → `409 {codigo:"existe", tercero}`;
tipo fuera del catálogo o valor demasiado largo → `422`; id inexistente → `404`; nombre vacío → `400`. Respuesta `200 {status:"OK", updated:true}`.

### Confirmar un borrador con la ficha vigente
`bot_driver._ejecutar_confirmacion` relee la ficha por `payload.third_party.id` antes de registrar la transacción: si el documento o el
nombre cambiaron después de asignarla (p. ej. un provisional `SN-` formalizado desde la Mini App) mandan los datos vigentes y no nace otra ficha.
`DELETE /api/third-parties/{id}` cruza los borradores abiertos también por `payload.third_party.id`.

### `tg.html` en Telegram Web
`frontend/nginx.conf` sirve `/tg.html` con `Content-Security-Policy: frame-ancestors 'self' https://web.telegram.org https://webk.telegram.org https://webz.telegram.org`
en lugar del `X-Frame-Options: SAMEORIGIN` global, para que Telegram Web (iframe) también la abra.

---

## 9. Análisis Inteligente (13) — `/api/analytics/*`

> Spec: `docs/specs/13-analisis/` · Router: `routers/analytics.py` · Lógica: `fin_sys_core/metrics_catalog.py`, `analytics_qa.py`, `insight_engine.py`, `analytics_log.py`, `export_xlsx.py`.
> Todos exigen sesión (Bearer). Ninguna cifra nace de una IA (R-13-01) y la empresa la elige el usuario, nunca el LLM (R-13-02).

### `GET /api/analytics/catalog` (sesión) → `{ metricas: [...] }` — el menú whitelisted, con el SQL auditable de cada métrica.
### `POST /api/analytics/metric` (sesión) — `{ metrica, params?, portfolio_id? }` → resultado con sello de origen · `400` métrica o parámetros fuera del catálogo.
### `GET /api/analytics/dataset` (sesión) → `{ esquema, filas, n, generado }` — tabla plana consolidada para Perspective.
### `POST /api/analytics/ask` (sesión) — `{ pregunta, portfolio_id? }` → texto + datos + gráfica PNG · `400` pregunta vacía · `502` falló el traductor.
### `GET /api/analytics/insights?portfolio_id=` (sesión) → tarjetas `{alerta|info|ok}` con sello.
### `GET /api/analytics/preguntas-log` (sesión) → `{ preguntas, retencion_dias }` — bitácora de preguntas sin responder (30 días).

### `GET /api/analytics/export.xlsx` (owner, admin o contador) — libros contables en Excel (spec 13.4)
- **Modo período** (default): `portfolio_id` o `portfolios=1,2` (vacío = consolidado) · `desde`, `hasta` (AAAA-MM-DD; `hasta` por defecto hoy en Colombia) · `hojas=` subconjunto de `caratula, diario, mayor, balance_prueba, estado_resultados, balance_general, movimientos, auxiliar_tercero, cartera, impuestos` (la carátula va siempre) · `nivel_puc=clase|grupo|cuenta|subcuenta` · filtros finos `categorias`, `terceros` (ids), `tipos`, `moneda`, `cuentas_puc` (prefijos para el Mayor). Los filtros solo tocan las hojas de transacciones; los libros oficiales no se filtran (D-134-07).
- **Modo transacciones**: `modo=transacciones&tx_ids=12,15,20` (máx. 5000) `&nombre=` → Relación: carátula, relación, asientos, resumen, soportes.
- **Respuesta `200`**: el `.xlsx` (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`) con `Content-Disposition: attachment; filename="FINSYS_<EMPRESA|CONSOLIDADO|VARIAS-n>_<desde>_<hasta>.xlsx"` (o `FINSYS_RELACION_<nombre>_<fecha>.xlsx`) y las cabeceras `X-FinSys-Transacciones`, `X-FinSys-Asientos`, `X-FinSys-Cuadra` (`1`/`0`), `X-FinSys-Advertencias` (cuántas trae la carátula).
- **Errores**: `401` sin sesión · `403` rol sin permiso · `400` receta inválida (`detail` dice qué: hoja desconocida, fechas al revés, empresa inexistente, transacciones de otra empresa…) · `503` la base de datos no respondió (jamás un libro vacío que en realidad fue un error).
