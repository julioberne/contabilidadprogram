# 🗄️ FIN-SYS OS v2.0 — Esquema de Base de Datos

> **Motor**: PostgreSQL 17 en Supabase (proyecto `FIN-SYS OS v2.0`, us-east-2)
> **Última actualización**: 18 Junio 2026

---

## Diagrama de Entidades (Vista General)

```
[workspace_users] ──────────────────────────────────────┐
                                                         │
[portfolios] ──(1:N)──> [transactions] ──(N:1)──> [third_parties]
                              │
                              ├──> [pockets]           (Muros Virtuales)
                              ├──> [cxp_cxc_ledger]   (Cartera)
                              ├──> [assets]            (Activos Patrimoniales)
                              └──> [user_accounts]     (Cuentas Bancarias)

[entities] ──(árbol auto-referencial, 5 niveles)──> [portfolios]
    │
    ├──> [entity_members]   ──(N:1)──> [workspace_users]
    ├──> [resource_ids]
    └──> [approvals_queue]  ──(N:1)──> [workspace_users]
```

---

## MÓDULOS PRINCIPALES (Contabilidad App)

### A. `portfolios` — Portafolios / Negocios
```sql
CREATE TABLE portfolios (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(50)  NOT NULL UNIQUE,   -- 'Negocio A', 'EMPRESA INFANTIL PEGASUS'
    industry_type   VARCHAR(50)  DEFAULT 'ESTANDAR',
    sub_industry_type VARCHAR(100),
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
```

### B. `third_parties` — Terceros (Contactos Fiscales)
```sql
CREATE TABLE third_parties (
    id                      SERIAL PRIMARY KEY,
    identification_type     VARCHAR(10)  NOT NULL,  -- 'NIT' | 'CC'
    identification_number   VARCHAR(30)  NOT NULL UNIQUE,
    name                    VARCHAR(100) NOT NULL,
    email                   VARCHAR(100),
    phone                   VARCHAR(30),
    website                 VARCHAR(150),
    created_at              TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
```

### C. `user_accounts` — Cuentas Bancarias / Financieras
```sql
CREATE TABLE user_accounts (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    type            VARCHAR(30)  NOT NULL,  -- 'Ahorros', 'Corriente', 'Crédito', 'Crypto', 'Efectivo', 'Billetera'
    currency        VARCHAR(5)   NOT NULL DEFAULT 'COP',  -- 'COP' | 'USD'
    initial_balance DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    current_balance DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
```

### D. `transactions` — Libro Diario (Núcleo del Sistema)
```sql
CREATE TABLE transactions (
    id                   SERIAL PRIMARY KEY,
    portfolio_id         INTEGER      NOT NULL REFERENCES portfolios(id),
    type                 VARCHAR(15)  NOT NULL,   -- 'INGRESO' | 'GASTO' | 'TRANSFERENCIA'
    amount               DECIMAL(15,2) NOT NULL,
    concept              VARCHAR(255) NOT NULL,
    transaction_date     DATE         NOT NULL,
    payment_method       VARCHAR(100),
    category             VARCHAR(100),

    -- Motor de Impuestos
    tax_iva_amount       DECIMAL(15,2) DEFAULT 0.00,
    tax_gmf_amount       DECIMAL(15,2) DEFAULT 0.00,
    net_value            DECIMAL(15,2) NOT NULL,

    -- Cuentas y Multi-Moneda
    account_id           INTEGER      REFERENCES user_accounts(id),
    dest_account_id      INTEGER      REFERENCES user_accounts(id),  -- solo TRANSFERENCIA
    transaction_currency VARCHAR(5)   DEFAULT 'COP',
    trm                  DECIMAL(15,4) DEFAULT 1.0,

    -- Tercero
    identification_type  VARCHAR(10),
    identification_number VARCHAR(30),
    third_party_name     VARCHAR(100),

    -- Georreferencia y Auditoría
    geo_maps_link        TEXT,
    evidence_file_path   TEXT,

    -- Recurrencia
    is_recurring         BOOLEAN DEFAULT FALSE,
    recurrence_interval  VARCHAR(20),  -- 'MENSUAL', 'SEMANAL', etc.
    recurrence_days      INTEGER DEFAULT 30,
    recurrence_max_reps  INTEGER,
    recurrence_start_date DATE,
    recurrence_end_date   DATE,

    -- Estado (Borradores de Voz)
    status               VARCHAR(20) DEFAULT 'COMPLETO',  -- 'BORRADOR' | 'COMPLETO'

    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### E. `pockets` — Bolsillos Virtuales (Muros de Capital)
```sql
CREATE TABLE pockets (
    id               SERIAL PRIMARY KEY,
    portfolio_id     INTEGER NOT NULL REFERENCES portfolios(id),
    name             VARCHAR(50) NOT NULL,
    allocated_budget DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    current_balance  DECIMAL(15,2) NOT NULL DEFAULT 0.00
);
```

### F. `cxp_cxc_ledger` — Cuentas por Cobrar / Pagar
```sql
CREATE TABLE cxp_cxc_ledger (
    id                SERIAL PRIMARY KEY,
    transaction_id    INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
    third_party_id    INTEGER REFERENCES third_parties(id),
    type              VARCHAR(10) NOT NULL,    -- 'CXC' | 'CXP'
    original_amount   DECIMAL(15,2) NOT NULL,
    remaining_balance DECIMAL(15,2) NOT NULL,
    due_date          DATE NOT NULL,
    term              VARCHAR(20) NOT NULL,    -- 'Corto' | 'Mediano' | 'Largo'
    status            VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### G. `assets` — Activos Patrimoniales
```sql
CREATE TABLE assets (
    id                          SERIAL PRIMARY KEY,
    portfolio_id                INTEGER NOT NULL REFERENCES portfolios(id),
    transaction_id              INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
    name                        VARCHAR(100) NOT NULL,
    purchase_value              DECIMAL(15,2) NOT NULL,
    purchase_date               DATE NOT NULL,
    custom_tag                  VARCHAR(50),
    is_passive_income_generator BOOLEAN DEFAULT FALSE,
    recurrence_interval_days    INTEGER,
    recurrence_amount           DECIMAL(15,2),
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### H. `user_profiles` — Perfil de Usuario Principal
```sql
CREATE TABLE user_profiles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(100),
    role        VARCHAR(100),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### I. `voice_ingestion_logs` — Logs de Voz (Auditoría IA)
```sql
CREATE TABLE voice_ingestion_logs (
    id              SERIAL PRIMARY KEY,
    audio_file_url  TEXT,
    raw_transcript  TEXT,
    parsed_json     TEXT,
    status          VARCHAR(30) NOT NULL,  -- 'EXITOSO' | 'FALLO_TRANSCRIPCION' | 'FALLO_PARSER'
    error_message   TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### J. `chart_of_accounts` — Catálogo de Cuentas (COA)
```sql
CREATE TABLE chart_of_accounts (
    id           SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id),
    code         VARCHAR(50) NOT NULL,
    name         VARCHAR(150) NOT NULL,
    account_type VARCHAR(20) NOT NULL,  -- 'ACTIVO' | 'PASIVO' | 'PATRIMONIO' | 'INGRESO' | 'GASTO'
    parent_id    INTEGER REFERENCES chart_of_accounts(id),
    is_group     BOOLEAN NOT NULL DEFAULT FALSE,
    description  TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (portfolio_id, code)
);
```

---

## MÓDULO CONTROL TOWER (Tablas Nuevas — Zero-Impact)

### K. `workspace_users` — Usuarios del Control Tower
```sql
CREATE TABLE workspace_users (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    email          VARCHAR(100) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    role_label     VARCHAR(100) NOT NULL DEFAULT 'Colaborador',
    permissions    JSONB DEFAULT '{"ledger": true, "reports": true, "users": false, "approvals": false}'::jsonb,
    parent_user_id INTEGER REFERENCES workspace_users(id) ON DELETE SET NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Seed: andres@finsys.os / admin123 (Super-Contador)
```

### L. `entities` — Árbol Jerárquico de Entidades (5 Niveles)
```sql
CREATE TABLE entities (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(150) NOT NULL,
    type         VARCHAR(20)  NOT NULL DEFAULT 'EMPRESA',
                 -- 'HOLDING' | 'EMPRESA' | 'SUB_EMPRESA' | 'PROYECTO' | 'TAREA'
    parent_id    INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    portfolio_id INTEGER REFERENCES portfolios(id) ON DELETE SET NULL,
                 -- Vinculación a datos contables reales
    industry     VARCHAR(100),
    sub_industry VARCHAR(100),
    status       VARCHAR(20) NOT NULL DEFAULT 'AL DIA',  -- 'AL DIA' | 'ALERTA' | 'MOROSO'
    created_by   INTEGER REFERENCES workspace_users(id) ON DELETE SET NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
*Datos actuales (Junio 2026)*:
| ID | Nombre | Tipo | portfolio_id |
|---|---|---|---|
| 1 | Mi Holding Principal | HOLDING | null |
| 2 | Jardín Infantil Pegasus | EMPRESA | 2 |
| 3 | Consultora Digital SAS | EMPRESA | 1 |
| 4 | Constructora Norte SAS | EMPRESA | 4 |
| 5 | Sede Norte — Pegasus | SUB_EMPRESA | 2 |
| 6 | Proyecto ERP — Cliente Minero | PROYECTO | null |
| 7 | Fase 1: Levantamiento de Requisitos | TAREA | null |

### M. `entity_members` — Colaboradores por Entidad
```sql
CREATE TABLE entity_members (
    id         SERIAL PRIMARY KEY,
    entity_id  INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES workspace_users(id) ON DELETE CASCADE,
    role_label VARCHAR(100) NOT NULL DEFAULT 'Colaborador',
    permissions JSONB DEFAULT '{"ledger": true, "reports": true}'::jsonb,
    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(entity_id, user_id)  -- Un usuario: un rol por entidad
);
```

### N. `resource_ids` — Inventario de IDs y Documentos
```sql
CREATE TABLE resource_ids (
    id         SERIAL PRIMARY KEY,
    entity_id  INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    label      VARCHAR(100) NOT NULL,   -- 'NIT', 'RUT', 'Licencia MEN', 'Contrato Arrend.'
    value      VARCHAR(255) NOT NULL,
    category   VARCHAR(50) NOT NULL DEFAULT 'FISCAL',
               -- 'FISCAL' | 'LEGAL' | 'BANCARIO' | 'COMERCIAL' | 'OTRO'
    expires_at DATE,                    -- NULL = no vence; fecha pasada = VENCIDO ⚠
    notes      TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### O. `approvals_queue` — Cola de Aprobaciones
```sql
CREATE TABLE approvals_queue (
    id             SERIAL PRIMARY KEY,
    entity_id      INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
    requested_by   INTEGER REFERENCES workspace_users(id) ON DELETE SET NULL,
    description    VARCHAR(255),
    amount         DECIMAL(15,2),
    status         VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
                   -- 'PENDIENTE' | 'APROBADO' | 'RECHAZADO'
    reviewed_by    INTEGER REFERENCES workspace_users(id) ON DELETE SET NULL,
    notes          TEXT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Índices de Rendimiento

```sql
-- App principal
CREATE INDEX idx_transactions_portfolio ON transactions(portfolio_id);
CREATE INDEX idx_transactions_date      ON transactions(transaction_date);
CREATE INDEX idx_transactions_status    ON transactions(status);
CREATE INDEX idx_third_parties_nit      ON third_parties(identification_number);
CREATE INDEX idx_cxp_due_date           ON cxp_cxc_ledger(due_date);
CREATE INDEX idx_assets_portfolio       ON assets(portfolio_id);

-- Control Tower
CREATE INDEX idx_entities_parent        ON entities(parent_id);
CREATE INDEX idx_entities_portfolio     ON entities(portfolio_id);
CREATE INDEX idx_members_entity         ON entity_members(entity_id);
CREATE INDEX idx_approvals_entity       ON approvals_queue(entity_id);
CREATE INDEX idx_approvals_status       ON approvals_queue(status);
CREATE INDEX idx_resources_entity       ON resource_ids(entity_id);

-- RRHH
CREATE INDEX idx_hr_payment_member      ON hr_payment_records(member_id);
CREATE INDEX idx_hr_docs_member         ON hr_documents(member_id);
CREATE INDEX idx_hr_member_company      ON hr_members(company_id);
```

---

## MÓDULO RRHH / EMPRESAS (Tablas Nuevas — Zero-Impact)

### P. `hr_companies` — Empresas / Compañías (Estructura Jerárquica)
```sql
CREATE TABLE hr_companies (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    type        VARCHAR(30)  NOT NULL DEFAULT 'EMPRESA',
                -- 'HOLDING' | 'EMPRESA' | 'SUBSIDIARIA' | 'PROYECTO'
    parent_id   INTEGER REFERENCES hr_companies(id) ON DELETE SET NULL,
    nit         VARCHAR(30),
    industry    VARCHAR(100),
    status      VARCHAR(20) NOT NULL DEFAULT 'ACTIVA',  -- 'ACTIVA' | 'INACTIVA'
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Q. `hr_members` — Miembros / Empleados
```sql
CREATE TABLE hr_members (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER REFERENCES hr_companies(id) ON DELETE SET NULL,
    name            VARCHAR(100) NOT NULL,
    role            VARCHAR(100),
    email           VARCHAR(100),
    phone           VARCHAR(30),
    id_type         VARCHAR(10)  DEFAULT 'CC',   -- 'CC' | 'NIT' | 'CE' | 'PAS'
    id_number       VARCHAR(30),
    salary_base     DECIMAL(15,2) DEFAULT 0.00,
    hire_date       DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'ACTIVO',  -- 'ACTIVO' | 'INACTIVO'
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### R. `hr_payment_records` — Historial de Pagos / Nómina
```sql
CREATE TABLE hr_payment_records (
    id                  SERIAL PRIMARY KEY,
    member_id           INTEGER NOT NULL REFERENCES hr_members(id) ON DELETE CASCADE,
    payment_date        DATE    NOT NULL,
    period_start        DATE,
    period_end          DATE,
    payment_type        VARCHAR(50) NOT NULL DEFAULT 'NOMINA',
                        -- 'NOMINA' | 'BONO' | 'COMISION' | 'VACACIONES' | 'LIQUIDACION'
    gross_amount        DECIMAL(15,2) NOT NULL DEFAULT 0.00,  -- Salario bruto
    deductions          DECIMAL(15,2) NOT NULL DEFAULT 0.00,  -- Deducciones (salud, pensón, etc.)
    net_amount          DECIMAL(15,2) NOT NULL DEFAULT 0.00,  -- Monto neto pagado
    payment_method      VARCHAR(50),
    notes               TEXT,
    voucher_document_id INTEGER REFERENCES hr_documents(id) ON DELETE SET NULL,
                        -- NULL = sin comprobante; FK al doc generado
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### S. `hr_documents` — Documentos del Empleado (Drive-style)
```sql
CREATE TABLE hr_documents (
    id              SERIAL PRIMARY KEY,
    member_id       INTEGER NOT NULL REFERENCES hr_members(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    file_url        TEXT NOT NULL,
                    -- URL Storage bucket (PDFs/imágenes)
                    -- O data:text/html;base64,... para comprobantes HTML generados
    file_type       VARCHAR(50),     -- 'pdf' | 'image' | 'html' | 'other'
    category        VARCHAR(100) DEFAULT 'General',
                    -- 'Contrato' | 'Cédula' | 'EPS' | 'Pensón' | 'Comprobante Nómina' | ...
    is_voucher      BOOLEAN NOT NULL DEFAULT FALSE,
                    -- TRUE = comprobante de pago generado por el sistema
    description     TEXT,
    uploaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Relación clave**:
- `hr_payment_records.voucher_document_id` → `hr_documents.id`
  (vincula un registro de pago con su comprobante de nómina generado)
- `hr_documents.file_url` puede ser:
  - URL pública del bucket `hr-docs` para archivos subidos por el usuario
  - `data:text/html;base64,...` para comprobantes HTML generados por el sistema

---

## MÓDULO BOT IA — Etapa 09.F (Tablas y columnas nuevas — Zero-Impact)

> Spec: `docs/specs/09-bot-ia/09.F-sms-bancolombia.md` · Migración: `scripts/migrate_sms_bancolombia.py` (el server también auto-cura en `_startup()` vía `fin_sys_core/bot_sms.init_sms_tables`).

### T. `sms_ingest_tokens` — Tokens del webhook de SMS (uno por teléfono)
```sql
CREATE TABLE IF NOT EXISTS sms_ingest_tokens (
    id SERIAL PRIMARY KEY,
    hub_user_id UUID NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,                 -- sha256 hex; el token plano se muestra UNA vez
    label TEXT,
    sender_allowlist TEXT[] NOT NULL DEFAULT '{85540}',   -- remitentes permitidos (Bancolombia = 85540)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ                           -- NULL = vigente
);
```

### Columnas nuevas en `user_accounts` (cuentas POR ID, D-09F-03)
```sql
ALTER TABLE user_accounts ADD COLUMN IF NOT EXISTS last4_cuenta  VARCHAR(4);  -- últimos 4 del número de cuenta
ALTER TABLE user_accounts ADD COLUMN IF NOT EXISTS last4_tarjeta VARCHAR(4);  -- últimos 4 de la tarjeta asociada
```
El bot cruza el `*3037` del SMS con `last4_cuenta` y resuelve `account_id`; el nombre de la cuenta queda libre. Editables en 💳 Cuentas.

### Uso de tablas existentes (sin cambios de esquema)
- `bot_messages`: `channel='sms'`, `kind` ∈ `sms` (pendiente) · `sms_sin_chat` (sin link Telegram activo) · `sms_error` (falló al convertir) · `sms_info` (aviso sin dinero: no es un movimiento) · `retencion_aviso` (salida de la purga); `raw_chat_id` = `hub_user_id`; `external_message_id` = sha256(remitente|texto|sentStamp)[:32] (dedupe por el índice único existente); `content` = JSON `{from, text, sentStamp}`. Los tests de integración usan la cola aparte `sms_prueba` (`sms_prueba_sin_chat` / `_error` / `_info`): el poller de producción solo atiende `sms`.
- `transaction_drafts`: `channel='sms'`, `raw_text` = SMS completo, `payload.sms = {familia, remitente, origen_last4, destino, hora, contraparte, origen_campo, plantilla_nueva, medio, tercero_por_medio}`, `payload.account_id` / `payload.dest_account_id` resueltos por id. `medio = {tipo, valor}` es el identificador de la contraparte que el botón 💾 guarda en `third_party_accounts` (09.G).

---

## MÓDULO BOT IA — Etapa 09.G (Tabla nueva — Zero-Impact)

> Spec: `docs/specs/09-bot-ia/09.G-completar-borrador.md` §10 · Migración: `scripts/migrate_third_party_accounts.py` (aplicada 30-sep-2026; el server también auto-cura en `_startup()` vía `fin_sys_core/terceros_cuentas.init_table`).

### U. `third_party_accounts` — Medios de pago de un tercero
```sql
CREATE TABLE IF NOT EXISTS third_party_accounts (
    id SERIAL PRIMARY KEY,
    third_party_id BIGINT NOT NULL REFERENCES third_parties(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL CHECK (tipo IN ('celular', 'cuenta', 'llave', 'nombre_banco')),
    valor TEXT NOT NULL,              -- identificador COMPLETO, normalizado
    banco TEXT,                       -- opcional, informativo: Nequi, Bancolombia…
    etiqueta TEXT,                    -- opcional: "ahorros", "cuenta de la mamá"…
    origen TEXT NOT NULL DEFAULT 'web' CHECK (origen IN ('web', 'bot')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (tipo, valor)              -- un medio pertenece a UNA sola ficha
);
CREATE INDEX IF NOT EXISTS idx_third_party_accounts_tercero ON third_party_accounts(third_party_id);
```
- Un tercero (una ficha, la manda su documento) tiene **varios** medios: cuentas, celulares, llaves y el nombre con que el banco lo llama en sus SMS.
- `valor` normalizado (`fin_sys_core/terceros_cuentas.normalizar`): `celular` = 10 dígitos que empiezan por 3 (sin `+57`); `cuenta` = solo dígitos (4–20); `llave` = sin espacios, minúsculas; `nombre_banco` = MAYÚSCULAS sin tildes.
- Lo escribe una persona: botón 💾 del bot (`origen='bot'`) o la ficha del tercero en la web (`origen='web'`). El bot lo lee por **igualdad** para traer el tercero ya puesto en el borrador de un SMS (Regla 6b: nada se memoriza solo).
- Un número con forma de celular (`3` + 9 dígitos) es **un solo medio** aunque esté guardado como `celular`, `llave` o `cuenta` (`_equivalentes`): el `UNIQUE` no lo ve, así que `agregar` responde `de_otro` si otra ficha lo tiene en cualquiera de esas formas y `mover` se lleva todas sus filas.
- El tercero genérico (`999999999`) no puede tener medios. No altera `third_parties`.

## MÓDULO ANÁLISIS — Etapa 13.5 Organizador contable 📦 (Tablas nuevas — Zero-Impact)

> Spec: `docs/specs/13-analisis/13.5-submodulo-exportacion.md` §4.4 · DDL (fuente única): `fin_sys_core/accounting_files_driver.py` (`DDL`) · Migración: `scripts/migrate_exports.py` (idempotente; correr ANTES del deploy). El server no las crea al arrancar: sin migración los endpoints responden `503`.

### V. `accounting_doc_types` — Tipos documentales (las "categorías" de RRHH, versión contable)
```sql
CREATE TABLE IF NOT EXISTS accounting_doc_types (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(30) UNIQUE,          -- solo los default: libros, estados, impuestos, cartera, bancos, relaciones, soportes
    nombre VARCHAR(60) NOT NULL,       -- único sin mayúsculas/espacios (uq_accounting_doc_types_nombre)
    icono VARCHAR(16), color VARCHAR(9) NOT NULL DEFAULT '#64748b',
    orden SMALLINT NOT NULL DEFAULT 100,
    es_default BOOLEAN NOT NULL DEFAULT FALSE,   -- los default se renombran, no se borran
    creado_por VARCHAR(120), creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### W. `accounting_folders` — Carpetas propias ("Para el banco 2026", "Auditoría")
```sql
CREATE TABLE IF NOT EXISTS accounting_folders (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL, color VARCHAR(9) NOT NULL DEFAULT '#64748b',
    parent_id INTEGER REFERENCES accounting_folders(id) ON DELETE CASCADE,
    portfolio_id INTEGER REFERENCES portfolios(id) ON DELETE SET NULL,   -- NULL = general
    creado_por VARCHAR(120), creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
- Las carpetas **automáticas** (Empresa → Año → Mes) no son filas: salen de `accounting_files.portfolio_id` y `periodo_hasta`.

### X. `accounting_files` — Un archivo del organizador (generado o subido)
```sql
CREATE SEQUENCE IF NOT EXISTS accounting_files_folio_seq;
CREATE TABLE IF NOT EXISTS accounting_files (
    id SERIAL PRIMARY KEY,
    origen VARCHAR(10) NOT NULL CHECK (origen IN ('GENERADO', 'SUBIDO')),
    folio VARCHAR(20) UNIQUE,                    -- solo generados: EXP-AAAA-NNNN (secuencia global)
    nombre VARCHAR(160) NOT NULL,                -- visible
    nombre_archivo VARCHAR(200) NOT NULL,        -- el de la descarga
    tipo_documental_id INTEGER REFERENCES accounting_doc_types(id) ON DELETE SET NULL,
    paquete VARCHAR(40),                         -- cierre_mes, banco, impuestos, cartera, movimientos, completo, relacion, personalizado
    receta JSONB,                                -- receta normalizada del motor 13.4 (modo transacciones: tx_ids)
    portfolio_id INTEGER REFERENCES portfolios(id) ON DELETE SET NULL,   -- NULL = consolidado / varias / sin empresa
    periodo_desde DATE, periodo_hasta DATE,
    folder_id INTEGER REFERENCES accounting_folders(id) ON DELETE SET NULL,
    archivo BYTEA NOT NULL,                      -- el archivo exacto (D-135-01: nunca en el bucket público)
    mime_type VARCHAR(100) NOT NULL, tamano_bytes INTEGER NOT NULL,
    sha256 CHAR(64) NOT NULL,
    hojas TEXT[], sello JSONB,                   -- sello del motor: conteos, totales de control, advertencias
    huella_datos JSONB,                          -- §4.6: n_txs, suma_neto, max_tx, n_lineas, debitos, max_linea (+ tx_vivas)
    creado_por VARCHAR(120), creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fijado BOOLEAN NOT NULL DEFAULT FALSE, nota TEXT,
    descargas INTEGER NOT NULL DEFAULT 0, ultima_descarga TIMESTAMPTZ,
    reemplaza_a INTEGER REFERENCES accounting_files(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_accounting_files_empresa_periodo ON accounting_files (portfolio_id, periodo_hasta);
CREATE INDEX IF NOT EXISTS idx_accounting_files_folder ON accounting_files (folder_id);
CREATE INDEX IF NOT EXISTS idx_accounting_files_tipo ON accounting_files (tipo_documental_id);
CREATE INDEX IF NOT EXISTS idx_accounting_files_purga ON accounting_files (creado_en) WHERE origen = 'GENERADO' AND NOT fijado;
```
- **Inmutable:** el contenido de un generado jamás se reescribe; regenerar crea otra fila con folio nuevo y `reemplaza_a`.
- **Purga** (en cada INSERT, sin scheduler): borra lo `GENERADO` no `fijado` con más de `ANALYTICS_EXPORT_RETENCION_DIAS` (90). Fijados y subidos, nunca.
- Tope `ANALYTICS_EXPORT_MAX_MB` (10) por archivo. Subidas: PDF, PNG, JPG, XLSX, CSV, decididos por la firma del contenido.

### Y. `analytics_export_paquetes` — Recetas guardadas ("💾 Guardar como paquete")
```sql
CREATE TABLE IF NOT EXISTS analytics_export_paquetes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL,
    receta JSONB NOT NULL,                       -- puede llevar período relativo ("relativo": "mes_anterior")
    creado_por VARCHAR(120), creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
