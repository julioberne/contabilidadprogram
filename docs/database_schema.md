# 🗄️ FIN-SYS OS v2.0 — Esquema de Base de Datos

> **Motor**: PostgreSQL 17 en Supabase (proyecto `FIN-SYS OS v2.0`, us-east-2)
> **Última actualización**: 09 Junio 2026

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
```
