-- ═══════════════════════════════════════════════════════════════════
-- FIN-SYS OS v2.0 — MEJORAS PROGRESIVAS A LA BASE DE DATOS
-- ═══════════════════════════════════════════════════════════════════
-- Fecha: 05 Jul 2026
-- Ejecutar en: Supabase → SQL Editor → New query → Run
-- Pre-validado: scripts/db_pre_validate.py (9/9 reglas OK tras fix)
-- ═══════════════════════════════════════════════════════════════════

-- ┌─────────────────────────────────────────────────────────────────┐
-- │  PASO 0: CORRECCIÓN DE DATOS (prerequisito)                    │
-- │  2 entidades usan 'SUBSIDIARIA' en vez de 'SUB_EMPRESA'       │
-- └─────────────────────────────────────────────────────────────────┘

UPDATE entities SET type = 'SUB_EMPRESA' WHERE type = 'SUBSIDIARIA';
-- Afecta: ID=9, ID=13


-- ┌─────────────────────────────────────────────────────────────────┐
-- │  PASO 1: ÍNDICES EN FOREIGN KEYS (performance 10-100x)         │
-- │  34 FK sin índice → crear todos                                │
-- └─────────────────────────────────────────────────────────────────┘

-- ── Core (Contabilidad) ──────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_assets_portfolio ON assets(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_pockets_portfolio ON pockets(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_tx_third_party ON transactions(third_party_id);
CREATE INDEX IF NOT EXISTS idx_tx_pocket ON transactions(pocket_id);
CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_tx_dest_account ON transactions(dest_account_id);
CREATE INDEX IF NOT EXISTS idx_cxp_third_party ON cxp_cxc_ledger(third_party_id);
CREATE INDEX IF NOT EXISTS idx_cxp_transaction ON cxp_cxc_ledger(transaction_id);
CREATE INDEX IF NOT EXISTS idx_cartera_payments_ledger ON cartera_payments(ledger_id);
CREATE INDEX IF NOT EXISTS idx_coa_parent ON chart_of_accounts(parent_id);
CREATE INDEX IF NOT EXISTS idx_posting_rules_portfolio ON posting_rules(portfolio_id);

-- ── Control Tower ────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_approvals_entity_id ON approvals_queue(entity_id);
CREATE INDEX IF NOT EXISTS idx_approvals_tx_id ON approvals_queue(transaction_id);
CREATE INDEX IF NOT EXISTS idx_approvals_requested ON approvals_queue(requested_by);
CREATE INDEX IF NOT EXISTS idx_approvals_reviewed ON approvals_queue(reviewed_by);
CREATE INDEX IF NOT EXISTS idx_entities_created_by ON entities(created_by);
CREATE INDEX IF NOT EXISTS idx_entities_portfolio ON entities(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_members_entity ON entity_members(entity_id);
CREATE INDEX IF NOT EXISTS idx_members_user ON entity_members(user_id);
CREATE INDEX IF NOT EXISTS idx_resources_entity ON resource_ids(entity_id);
CREATE INDEX IF NOT EXISTS idx_wu_parent ON workspace_users(parent_user_id);

-- ── RRHH ─────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_hr_docs_folder ON hr_documents(folder_id);
CREATE INDEX IF NOT EXISTS idx_hr_folders_parent ON hr_folders(parent_id);
CREATE INDEX IF NOT EXISTS idx_hr_pay_voucher ON hr_payment_records(voucher_document_id);

-- ── Hub (Project Hub) ────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_hub_entities_ws ON hub_entities(workspace_id);
CREATE INDEX IF NOT EXISTS idx_hub_entities_parent ON hub_entities(parent_id);
CREATE INDEX IF NOT EXISTS idx_hub_events_ws ON hub_events(workspace_id);
CREATE INDEX IF NOT EXISTS idx_hub_events_created ON hub_events(created_by);
CREATE INDEX IF NOT EXISTS idx_hub_events_project ON hub_events(project_id);
CREATE INDEX IF NOT EXISTS idx_hub_notes_ws ON hub_notes(workspace_id);
CREATE INDEX IF NOT EXISTS idx_hub_notes_user ON hub_notes(user_id);
CREATE INDEX IF NOT EXISTS idx_hub_notes_project ON hub_notes(project_id);
CREATE INDEX IF NOT EXISTS idx_hub_projects_ws ON hub_projects(workspace_id);
CREATE INDEX IF NOT EXISTS idx_hub_projects_entity ON hub_projects(entity_id);
CREATE INDEX IF NOT EXISTS idx_hub_projects_created ON hub_projects(created_by);
CREATE INDEX IF NOT EXISTS idx_hub_tasks_ws ON hub_tasks(workspace_id);
CREATE INDEX IF NOT EXISTS idx_hub_tasks_project ON hub_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_hub_tasks_created ON hub_tasks(created_by);
CREATE INDEX IF NOT EXISTS idx_hub_task_assign_task ON hub_task_assignees(task_id);
CREATE INDEX IF NOT EXISTS idx_hub_task_assign_user ON hub_task_assignees(user_id);
CREATE INDEX IF NOT EXISTS idx_hub_event_att_event ON hub_event_attendees(event_id);
CREATE INDEX IF NOT EXISTS idx_hub_event_att_user ON hub_event_attendees(user_id);
CREATE INDEX IF NOT EXISTS idx_hub_ws_members_ws ON hub_workspace_members(workspace_id);
CREATE INDEX IF NOT EXISTS idx_hub_ws_members_user ON hub_workspace_members(user_id);


-- ┌─────────────────────────────────────────────────────────────────┐
-- │  PASO 2: CHECK CONSTRAINTS (integridad de datos)               │
-- │  La BD rechazará datos inválidos automáticamente                │
-- └─────────────────────────────────────────────────────────────────┘

-- Transacciones
ALTER TABLE transactions
  ADD CONSTRAINT chk_tx_type
  CHECK (type IN ('INGRESO', 'GASTO', 'TRANSFERENCIA'));

ALTER TABLE transactions
  ADD CONSTRAINT chk_tx_positive_amount
  CHECK (amount > 0);

-- Cartera CXC/CXP
ALTER TABLE cxp_cxc_ledger
  ADD CONSTRAINT chk_ledger_type
  CHECK (type IN ('CXC', 'CXP'));

ALTER TABLE cxp_cxc_ledger
  ADD CONSTRAINT chk_ledger_status
  CHECK (status IN ('PENDIENTE', 'PARCIAL', 'PAGADO', 'VENCIDO'));

ALTER TABLE cxp_cxc_ledger
  ADD CONSTRAINT chk_cxp_positive
  CHECK (original_amount > 0 AND remaining_balance >= 0);

-- Entidades (Control Tower)
ALTER TABLE entities
  ADD CONSTRAINT chk_entity_type
  CHECK (type IN ('HOLDING', 'EMPRESA', 'SUB_EMPRESA', 'PROYECTO', 'TAREA'));

ALTER TABLE entities
  ADD CONSTRAINT chk_entity_status
  CHECK (status IN ('AL DIA', 'ALERTA', 'MOROSO'));

-- Cuentas bancarias
ALTER TABLE user_accounts
  ADD CONSTRAINT chk_currency
  CHECK (currency IN ('COP', 'USD'));


-- ┌─────────────────────────────────────────────────────────────────┐
-- │  PASO 3: VERIFICACIÓN (confirmar que todo se aplicó)           │
-- └─────────────────────────────────────────────────────────────────┘

-- Contar índices nuevos
SELECT 'ÍNDICES CREADOS' AS tipo,
       count(*) AS total
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%';

-- Contar CHECK constraints
SELECT 'CHECK CONSTRAINTS' AS tipo,
       count(*) AS total
FROM pg_constraint
WHERE contype = 'c'
  AND connamespace = 'public'::regnamespace;

-- Verificar el fix de entities
SELECT 'ENTITIES FIX' AS tipo,
       count(*) AS total
FROM entities
WHERE type = 'SUBSIDIARIA';
-- Debe retornar 0
