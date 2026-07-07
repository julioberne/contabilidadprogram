-- ═══════════════════════════════════════════════════════════════════
-- FIN-SYS OS v2.0 — Schema Completo Exportado
-- Generado automáticamente desde Supabase PostgreSQL
-- Fecha: 2026-07-05T18:21:27.307626
-- Tablas: 37
-- ═══════════════════════════════════════════════════════════════════


-- ── APPROVALS_QUEUE ───────────────────────────────────
CREATE TABLE IF NOT EXISTS approvals_queue (
  id INTEGER DEFAULT nextval('approvals_queue_id_seq'::regclass) NOT NULL,
  entity_id INTEGER NOT NULL,
  transaction_id INTEGER,
  requested_by INTEGER,
  description VARCHAR(255),
  amount NUMERIC(15,2),
  status VARCHAR(20) DEFAULT 'PENDIENTE'::character varying NOT NULL,
  reviewed_by INTEGER,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE approvals_queue ADD CONSTRAINT approvals_queue_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE;
ALTER TABLE approvals_queue ADD CONSTRAINT approvals_queue_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES workspace_users(id) ON DELETE SET NULL;
ALTER TABLE approvals_queue ADD CONSTRAINT approvals_queue_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES workspace_users(id) ON DELETE SET NULL;
ALTER TABLE approvals_queue ADD CONSTRAINT approvals_queue_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL;
ALTER TABLE approvals_queue ADD CONSTRAINT approvals_queue_pkey PRIMARY KEY (id);
CREATE INDEX idx_approvals_entity_id ON public.approvals_queue USING btree (entity_id);
CREATE INDEX idx_approvals_tx_id ON public.approvals_queue USING btree (transaction_id);
CREATE INDEX idx_approvals_requested ON public.approvals_queue USING btree (requested_by);
CREATE INDEX idx_approvals_reviewed ON public.approvals_queue USING btree (reviewed_by);


-- ── ASSETS ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS assets (
  id INTEGER DEFAULT nextval('assets_id_seq'::regclass) NOT NULL,
  portfolio_id INTEGER NOT NULL,
  name VARCHAR(100) NOT NULL,
  purchase_value NUMERIC(15,2) NOT NULL,
  purchase_date DATE NOT NULL,
  custom_tag VARCHAR(50),
  is_passive_income_generator BOOLEAN DEFAULT false NOT NULL,
  recurrence_interval_days INTEGER,
  recurrence_amount NUMERIC(15,2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE assets ADD CONSTRAINT assets_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE;
ALTER TABLE assets ADD CONSTRAINT assets_pkey PRIMARY KEY (id);
CREATE INDEX idx_assets_portfolio ON public.assets USING btree (portfolio_id);


-- ── CARTERA_PAYMENTS ──────────────────────────────────
CREATE TABLE IF NOT EXISTS cartera_payments (
  id INTEGER DEFAULT nextval('cartera_payments_id_seq'::regclass) NOT NULL,
  ledger_id INTEGER NOT NULL,
  amount NUMERIC(15,2) NOT NULL,
  payment_date DATE DEFAULT CURRENT_DATE NOT NULL,
  note TEXT,
  balance_after NUMERIC(15,2),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE cartera_payments ADD CONSTRAINT cartera_payments_ledger_id_fkey FOREIGN KEY (ledger_id) REFERENCES cxp_cxc_ledger(id) ON DELETE CASCADE;
ALTER TABLE cartera_payments ADD CONSTRAINT cartera_payments_pkey PRIMARY KEY (id);
CREATE INDEX idx_cartera_payments_ledger ON public.cartera_payments USING btree (ledger_id);


-- ── CHART_OF_ACCOUNTS ─────────────────────────────────
CREATE TABLE IF NOT EXISTS chart_of_accounts (
  id INTEGER DEFAULT nextval('chart_of_accounts_id_seq'::regclass) NOT NULL,
  portfolio_id INTEGER NOT NULL,
  code VARCHAR(50) NOT NULL,
  name VARCHAR(150) NOT NULL,
  account_type VARCHAR(20) NOT NULL,
  parent_id INTEGER,
  is_group BOOLEAN DEFAULT false NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE chart_of_accounts ADD CONSTRAINT chart_of_accounts_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES chart_of_accounts(id) ON DELETE CASCADE;
ALTER TABLE chart_of_accounts ADD CONSTRAINT chart_of_accounts_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE;
ALTER TABLE chart_of_accounts ADD CONSTRAINT chart_of_accounts_pkey PRIMARY KEY (id);
ALTER TABLE chart_of_accounts ADD CONSTRAINT chart_of_accounts_portfolio_id_code_key UNIQUE (portfolio_id, code);
CREATE INDEX idx_coa_parent ON public.chart_of_accounts USING btree (parent_id);


-- ── CUSTOM_TAXES_TEMPLATES ────────────────────────────
CREATE TABLE IF NOT EXISTS custom_taxes_templates (
  id INTEGER DEFAULT nextval('custom_taxes_templates_id_seq'::regclass) NOT NULL,
  name VARCHAR(100) NOT NULL,
  rate NUMERIC(10,4) NOT NULL,
  type VARCHAR(20) DEFAULT 'ADDITIVE'::character varying,
  created_at TIMESTAMP DEFAULT now()
);
ALTER TABLE custom_taxes_templates ADD CONSTRAINT custom_taxes_templates_pkey PRIMARY KEY (id);


-- ── CXP_CXC_LEDGER ────────────────────────────────────
CREATE TABLE IF NOT EXISTS cxp_cxc_ledger (
  id INTEGER DEFAULT nextval('cxp_cxc_ledger_id_seq'::regclass) NOT NULL,
  transaction_id INTEGER,
  third_party_id INTEGER NOT NULL,
  type VARCHAR(10) NOT NULL,
  original_amount NUMERIC(15,2) NOT NULL,
  remaining_balance NUMERIC(15,2) NOT NULL,
  due_date DATE NOT NULL,
  term VARCHAR(20) NOT NULL,
  status VARCHAR(20) DEFAULT 'PENDIENTE'::character varying NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  start_date DATE DEFAULT CURRENT_DATE,
  payment_frequency INTEGER DEFAULT 30
);
ALTER TABLE cxp_cxc_ledger ADD CONSTRAINT chk_cxp_positive CHECK (((original_amount > (0)::numeric) AND (remaining_balance >= (0)::numeric)));
ALTER TABLE cxp_cxc_ledger ADD CONSTRAINT chk_ledger_status CHECK (((status)::text = ANY ((ARRAY['PENDIENTE'::character varying, 'PARCIAL'::character varying, 'PAGADO'::character varying, 'VENCIDO'::character varying])::text[])));
ALTER TABLE cxp_cxc_ledger ADD CONSTRAINT chk_ledger_type CHECK (((type)::text = ANY ((ARRAY['CXC'::character varying, 'CXP'::character varying])::text[])));
ALTER TABLE cxp_cxc_ledger ADD CONSTRAINT cxp_cxc_ledger_third_party_id_fkey FOREIGN KEY (third_party_id) REFERENCES third_parties(id) ON DELETE RESTRICT;
ALTER TABLE cxp_cxc_ledger ADD CONSTRAINT cxp_cxc_ledger_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL;
ALTER TABLE cxp_cxc_ledger ADD CONSTRAINT cxp_cxc_ledger_pkey PRIMARY KEY (id);
CREATE INDEX idx_cxp_due_date ON public.cxp_cxc_ledger USING btree (due_date);
CREATE INDEX idx_cxp_third_party ON public.cxp_cxc_ledger USING btree (third_party_id);
CREATE INDEX idx_cxp_transaction ON public.cxp_cxc_ledger USING btree (transaction_id);


-- ── ENTITIES ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS entities (
  id INTEGER DEFAULT nextval('entities_id_seq'::regclass) NOT NULL,
  name VARCHAR(150) NOT NULL,
  type VARCHAR(20) DEFAULT 'EMPRESA'::character varying NOT NULL,
  parent_id INTEGER,
  portfolio_id INTEGER,
  industry VARCHAR(100),
  sub_industry VARCHAR(100),
  status VARCHAR(20) DEFAULT 'AL DIA'::character varying NOT NULL,
  created_by INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE entities ADD CONSTRAINT chk_entity_status CHECK (((status)::text = ANY ((ARRAY['AL DIA'::character varying, 'ALERTA'::character varying, 'MOROSO'::character varying])::text[])));
ALTER TABLE entities ADD CONSTRAINT chk_entity_type CHECK (((type)::text = ANY ((ARRAY['HOLDING'::character varying, 'EMPRESA'::character varying, 'SUB_EMPRESA'::character varying, 'PROYECTO'::character varying, 'TAREA'::character varying])::text[])));
ALTER TABLE entities ADD CONSTRAINT entities_created_by_fkey FOREIGN KEY (created_by) REFERENCES workspace_users(id) ON DELETE SET NULL;
ALTER TABLE entities ADD CONSTRAINT entities_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES entities(id) ON DELETE CASCADE;
ALTER TABLE entities ADD CONSTRAINT entities_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE SET NULL;
ALTER TABLE entities ADD CONSTRAINT entities_pkey PRIMARY KEY (id);
CREATE INDEX idx_entities_created_by ON public.entities USING btree (created_by);
CREATE INDEX idx_entities_portfolio ON public.entities USING btree (portfolio_id);
CREATE INDEX idx_entities_parent ON public.entities USING btree (parent_id);


-- ── ENTITY_MEMBERS ────────────────────────────────────
CREATE TABLE IF NOT EXISTS entity_members (
  id INTEGER DEFAULT nextval('entity_members_id_seq'::regclass) NOT NULL,
  entity_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  role_label VARCHAR(100) DEFAULT 'Colaborador'::character varying NOT NULL,
  permissions JSONB DEFAULT '{"ledger": true, "reports": true}'::jsonb,
  invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expires_at TIMESTAMP
);
ALTER TABLE entity_members ADD CONSTRAINT entity_members_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE;
ALTER TABLE entity_members ADD CONSTRAINT entity_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES workspace_users(id) ON DELETE CASCADE;
ALTER TABLE entity_members ADD CONSTRAINT entity_members_pkey PRIMARY KEY (id);
ALTER TABLE entity_members ADD CONSTRAINT entity_members_entity_id_user_id_key UNIQUE (entity_id, user_id);
CREATE INDEX idx_members_entity ON public.entity_members USING btree (entity_id);
CREATE INDEX idx_members_user ON public.entity_members USING btree (user_id);


-- ── HR_DOC_CATEGORIES ─────────────────────────────────
CREATE TABLE IF NOT EXISTS hr_doc_categories (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  workspace_id UUID NOT NULL,
  name VARCHAR(100) NOT NULL,
  color VARCHAR(20) DEFAULT '#64748b'::character varying NOT NULL,
  sort_order INTEGER DEFAULT 99 NOT NULL,
  is_default BOOLEAN DEFAULT false NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hr_doc_categories ADD CONSTRAINT hr_doc_categories_pkey PRIMARY KEY (id);


-- ── HR_DOCUMENTS ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS hr_documents (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  user_id UUID NOT NULL,
  workspace_id UUID NOT NULL,
  folder_id UUID,
  file_name VARCHAR(255) NOT NULL,
  file_url TEXT NOT NULL,
  file_size BIGINT DEFAULT 0,
  mime_type VARCHAR(100),
  category VARCHAR(50) DEFAULT 'general'::character varying,
  description TEXT,
  uploaded_by UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hr_documents ADD CONSTRAINT hr_documents_folder_id_fkey FOREIGN KEY (folder_id) REFERENCES hr_folders(id) ON DELETE SET NULL;
ALTER TABLE hr_documents ADD CONSTRAINT hr_documents_pkey PRIMARY KEY (id);
CREATE INDEX idx_hr_docs_folder ON public.hr_documents USING btree (folder_id);


-- ── HR_EMPLOYEE_COMPANIES ─────────────────────────────
CREATE TABLE IF NOT EXISTS hr_employee_companies (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  user_id UUID NOT NULL,
  entity_id INTEGER NOT NULL,
  entity_name VARCHAR(100),
  role_in_company VARCHAR(100),
  start_date DATE,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hr_employee_companies ADD CONSTRAINT hr_employee_companies_pkey PRIMARY KEY (id);


-- ── HR_FOLDERS ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hr_folders (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  workspace_id UUID NOT NULL,
  name VARCHAR(100) NOT NULL,
  parent_id UUID,
  color VARCHAR(7) DEFAULT '#64748b'::character varying,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hr_folders ADD CONSTRAINT hr_folders_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES hr_folders(id) ON DELETE CASCADE;
ALTER TABLE hr_folders ADD CONSTRAINT hr_folders_pkey PRIMARY KEY (id);
CREATE INDEX idx_hr_folders_parent ON public.hr_folders USING btree (parent_id);


-- ── HR_PAYMENT_RECORDS ────────────────────────────────
CREATE TABLE IF NOT EXISTS hr_payment_records (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  user_id UUID NOT NULL,
  workspace_id UUID NOT NULL,
  period_label VARCHAR(30) NOT NULL,
  period_month INTEGER NOT NULL,
  period_year INTEGER NOT NULL,
  base_amount NUMERIC(14,2) DEFAULT 0,
  devengado_total NUMERIC(14,2) DEFAULT 0,
  deduccion_empleado NUMERIC(14,2) DEFAULT 0,
  neto_a_pagar NUMERIC(14,2) DEFAULT 0,
  costo_empleador NUMERIC(14,2) DEFAULT 0,
  payment_date DATE,
  voucher_document_id UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hr_payment_records ADD CONSTRAINT hr_payment_records_voucher_document_id_fkey FOREIGN KEY (voucher_document_id) REFERENCES hr_documents(id) ON DELETE SET NULL;
ALTER TABLE hr_payment_records ADD CONSTRAINT hr_payment_records_pkey PRIMARY KEY (id);
CREATE INDEX idx_hr_pay_voucher ON public.hr_payment_records USING btree (voucher_document_id);


-- ── HR_PROFILES ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS hr_profiles (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  user_id UUID NOT NULL,
  workspace_id UUID NOT NULL,
  cedula VARCHAR(20),
  phone VARCHAR(20),
  address TEXT,
  birth_date DATE,
  hire_date DATE,
  job_title VARCHAR(100),
  department VARCHAR(100),
  status VARCHAR(20) DEFAULT 'active'::character varying,
  emergency_contact TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  role_description TEXT,
  email VARCHAR(255),
  contract_type VARCHAR(50),
  bank_name VARCHAR(100),
  bank_account_type VARCHAR(30),
  bank_account_number VARCHAR(60),
  eps VARCHAR(100),
  pension_fund VARCHAR(100),
  social_security_no VARCHAR(50),
  country VARCHAR(80) DEFAULT 'Colombia'::character varying,
  city VARCHAR(80),
  marital_status VARCHAR(30),
  education_level VARCHAR(50),
  skills TEXT,
  avatar_url TEXT
);
ALTER TABLE hr_profiles ADD CONSTRAINT hr_profiles_pkey PRIMARY KEY (id);
ALTER TABLE hr_profiles ADD CONSTRAINT hr_profiles_user_id_workspace_id_key UNIQUE (user_id, workspace_id);


-- ── HR_SALARIES ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS hr_salaries (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  user_id UUID NOT NULL,
  workspace_id UUID NOT NULL,
  salary_type VARCHAR(20) DEFAULT 'base'::character varying,
  base_amount NUMERIC(15,2) DEFAULT 0,
  transport_allowance NUMERIC(15,2) DEFAULT 0,
  bonuses NUMERIC(15,2) DEFAULT 0,
  commissions NUMERIC(15,2) DEFAULT 0,
  vacation_provision NUMERIC(15,2) DEFAULT 0,
  severance_provision NUMERIC(15,2) DEFAULT 0,
  health_employee_pct NUMERIC(5,2) DEFAULT 4.0,
  pension_employee_pct NUMERIC(5,2) DEFAULT 4.0,
  tax_withholding NUMERIC(15,2) DEFAULT 0,
  voluntary_deductions NUMERIC(15,2) DEFAULT 0,
  health_employer_pct NUMERIC(5,2) DEFAULT 8.5,
  pension_employer_pct NUMERIC(5,2) DEFAULT 12.0,
  arl_pct NUMERIC(5,2) DEFAULT 0.522,
  family_comp_pct NUMERIC(5,2) DEFAULT 4.0,
  icbf_pct NUMERIC(5,2) DEFAULT 3.0,
  sena_pct NUMERIC(5,2) DEFAULT 2.0,
  ipc_adjustment_pct NUMERIC(5,2) DEFAULT 0,
  ipc_effective_date DATE,
  currency VARCHAR(3) DEFAULT 'COP'::character varying,
  updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hr_salaries ADD CONSTRAINT hr_salaries_pkey PRIMARY KEY (id);
ALTER TABLE hr_salaries ADD CONSTRAINT hr_salaries_user_id_workspace_id_key UNIQUE (user_id, workspace_id);


-- ── HUB_ENTITIES ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS hub_entities (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  workspace_id UUID NOT NULL,
  parent_id UUID,
  name TEXT NOT NULL,
  type TEXT DEFAULT 'CUSTOM'::text,
  description TEXT,
  color TEXT DEFAULT '#0EA5E9'::text,
  position INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hub_entities ADD CONSTRAINT hub_entities_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES hub_entities(id) ON DELETE SET NULL;
ALTER TABLE hub_entities ADD CONSTRAINT hub_entities_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES hub_workspaces(id) ON DELETE CASCADE;
ALTER TABLE hub_entities ADD CONSTRAINT hub_entities_pkey PRIMARY KEY (id);
CREATE INDEX idx_hub_entities_workspace ON public.hub_entities USING btree (workspace_id);
CREATE INDEX idx_hub_entities_parent ON public.hub_entities USING btree (parent_id);
CREATE INDEX idx_hub_entities_ws ON public.hub_entities USING btree (workspace_id);


-- ── HUB_EVENT_ATTENDEES ───────────────────────────────
CREATE TABLE IF NOT EXISTS hub_event_attendees (
  event_id UUID NOT NULL,
  user_id UUID NOT NULL
);
ALTER TABLE hub_event_attendees ADD CONSTRAINT hub_event_attendees_event_id_fkey FOREIGN KEY (event_id) REFERENCES hub_events(id) ON DELETE CASCADE;
ALTER TABLE hub_event_attendees ADD CONSTRAINT hub_event_attendees_user_id_fkey FOREIGN KEY (user_id) REFERENCES hub_users(id) ON DELETE CASCADE;
ALTER TABLE hub_event_attendees ADD CONSTRAINT hub_event_attendees_pkey PRIMARY KEY (event_id, user_id);
CREATE INDEX idx_hub_event_att_event ON public.hub_event_attendees USING btree (event_id);
CREATE INDEX idx_hub_event_att_user ON public.hub_event_attendees USING btree (user_id);


-- ── HUB_EVENTS ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hub_events (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  workspace_id UUID NOT NULL,
  project_id UUID,
  title TEXT NOT NULL,
  description TEXT,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ NOT NULL,
  all_day BOOLEAN DEFAULT false,
  color TEXT,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hub_events ADD CONSTRAINT hub_events_created_by_fkey FOREIGN KEY (created_by) REFERENCES hub_users(id);
ALTER TABLE hub_events ADD CONSTRAINT hub_events_project_id_fkey FOREIGN KEY (project_id) REFERENCES hub_projects(id) ON DELETE SET NULL;
ALTER TABLE hub_events ADD CONSTRAINT hub_events_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES hub_workspaces(id) ON DELETE CASCADE;
ALTER TABLE hub_events ADD CONSTRAINT hub_events_pkey PRIMARY KEY (id);
CREATE INDEX idx_hub_events_workspace ON public.hub_events USING btree (workspace_id);
CREATE INDEX idx_hub_events_time ON public.hub_events USING btree (start_time, end_time);
CREATE INDEX idx_hub_events_ws ON public.hub_events USING btree (workspace_id);
CREATE INDEX idx_hub_events_created ON public.hub_events USING btree (created_by);
CREATE INDEX idx_hub_events_project ON public.hub_events USING btree (project_id);


-- ── HUB_NOTES ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hub_notes (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  workspace_id UUID NOT NULL,
  project_id UUID,
  user_id UUID NOT NULL,
  title TEXT DEFAULT 'Sin titulo'::text,
  content JSONB DEFAULT '[]'::jsonb,
  is_private BOOLEAN DEFAULT true,
  updated_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hub_notes ADD CONSTRAINT hub_notes_project_id_fkey FOREIGN KEY (project_id) REFERENCES hub_projects(id) ON DELETE SET NULL;
ALTER TABLE hub_notes ADD CONSTRAINT hub_notes_user_id_fkey FOREIGN KEY (user_id) REFERENCES hub_users(id) ON DELETE CASCADE;
ALTER TABLE hub_notes ADD CONSTRAINT hub_notes_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES hub_workspaces(id) ON DELETE CASCADE;
ALTER TABLE hub_notes ADD CONSTRAINT hub_notes_pkey PRIMARY KEY (id);
CREATE INDEX idx_hub_notes_workspace ON public.hub_notes USING btree (workspace_id);
CREATE INDEX idx_hub_notes_user ON public.hub_notes USING btree (user_id);
CREATE INDEX idx_hub_notes_ws ON public.hub_notes USING btree (workspace_id);
CREATE INDEX idx_hub_notes_project ON public.hub_notes USING btree (project_id);


-- ── HUB_PROJECTS ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS hub_projects (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  workspace_id UUID NOT NULL,
  entity_id UUID,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'active'::text,
  color TEXT DEFAULT '#0EA5E9'::text,
  created_by UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hub_projects ADD CONSTRAINT hub_projects_created_by_fkey FOREIGN KEY (created_by) REFERENCES hub_users(id);
ALTER TABLE hub_projects ADD CONSTRAINT hub_projects_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES hub_entities(id) ON DELETE SET NULL;
ALTER TABLE hub_projects ADD CONSTRAINT hub_projects_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES hub_workspaces(id) ON DELETE CASCADE;
ALTER TABLE hub_projects ADD CONSTRAINT hub_projects_pkey PRIMARY KEY (id);
CREATE INDEX idx_hub_projects_workspace ON public.hub_projects USING btree (workspace_id);
CREATE INDEX idx_hub_projects_entity ON public.hub_projects USING btree (entity_id);
CREATE INDEX idx_hub_projects_ws ON public.hub_projects USING btree (workspace_id);
CREATE INDEX idx_hub_projects_created ON public.hub_projects USING btree (created_by);


-- ── HUB_TASK_ASSIGNEES ────────────────────────────────
CREATE TABLE IF NOT EXISTS hub_task_assignees (
  task_id UUID NOT NULL,
  user_id UUID NOT NULL
);
ALTER TABLE hub_task_assignees ADD CONSTRAINT hub_task_assignees_task_id_fkey FOREIGN KEY (task_id) REFERENCES hub_tasks(id) ON DELETE CASCADE;
ALTER TABLE hub_task_assignees ADD CONSTRAINT hub_task_assignees_user_id_fkey FOREIGN KEY (user_id) REFERENCES hub_users(id) ON DELETE CASCADE;
ALTER TABLE hub_task_assignees ADD CONSTRAINT hub_task_assignees_pkey PRIMARY KEY (task_id, user_id);
CREATE INDEX idx_hub_task_assign_task ON public.hub_task_assignees USING btree (task_id);
CREATE INDEX idx_hub_task_assign_user ON public.hub_task_assignees USING btree (user_id);


-- ── HUB_TASKS ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hub_tasks (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  workspace_id UUID NOT NULL,
  project_id UUID NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'todo'::text,
  priority TEXT DEFAULT 'medium'::text,
  due_date DATE,
  position INTEGER DEFAULT 0,
  created_by UUID,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hub_tasks ADD CONSTRAINT hub_tasks_created_by_fkey FOREIGN KEY (created_by) REFERENCES hub_users(id);
ALTER TABLE hub_tasks ADD CONSTRAINT hub_tasks_project_id_fkey FOREIGN KEY (project_id) REFERENCES hub_projects(id) ON DELETE CASCADE;
ALTER TABLE hub_tasks ADD CONSTRAINT hub_tasks_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES hub_workspaces(id) ON DELETE CASCADE;
ALTER TABLE hub_tasks ADD CONSTRAINT hub_tasks_pkey PRIMARY KEY (id);
CREATE INDEX idx_hub_tasks_workspace ON public.hub_tasks USING btree (workspace_id);
CREATE INDEX idx_hub_tasks_project ON public.hub_tasks USING btree (project_id);
CREATE INDEX idx_hub_tasks_status ON public.hub_tasks USING btree (status);
CREATE INDEX idx_hub_tasks_ws ON public.hub_tasks USING btree (workspace_id);
CREATE INDEX idx_hub_tasks_created ON public.hub_tasks USING btree (created_by);


-- ── HUB_USERS ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hub_users (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  email TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  cedula TEXT,
  avatar_url TEXT,
  color TEXT DEFAULT '#0EA5E9'::text,
  role TEXT DEFAULT 'member'::text,
  description TEXT,
  is_superuser BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hub_users ADD CONSTRAINT hub_users_pkey PRIMARY KEY (id);
ALTER TABLE hub_users ADD CONSTRAINT hub_users_email_key UNIQUE (email);


-- ── HUB_WORKSPACE_MEMBERS ─────────────────────────────
CREATE TABLE IF NOT EXISTS hub_workspace_members (
  workspace_id UUID NOT NULL,
  user_id UUID NOT NULL,
  role TEXT DEFAULT 'member'::text,
  joined_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hub_workspace_members ADD CONSTRAINT hub_workspace_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES hub_users(id) ON DELETE CASCADE;
ALTER TABLE hub_workspace_members ADD CONSTRAINT hub_workspace_members_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES hub_workspaces(id) ON DELETE CASCADE;
ALTER TABLE hub_workspace_members ADD CONSTRAINT hub_workspace_members_pkey PRIMARY KEY (workspace_id, user_id);
CREATE INDEX idx_hub_ws_members_ws ON public.hub_workspace_members USING btree (workspace_id);
CREATE INDEX idx_hub_ws_members_user ON public.hub_workspace_members USING btree (user_id);


-- ── HUB_WORKSPACES ────────────────────────────────────
CREATE TABLE IF NOT EXISTS hub_workspaces (
  id UUID DEFAULT gen_random_uuid() NOT NULL,
  slug TEXT NOT NULL,
  name TEXT NOT NULL,
  nit TEXT,
  logo_url TEXT,
  plan TEXT DEFAULT 'free'::text,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE hub_workspaces ADD CONSTRAINT hub_workspaces_pkey PRIMARY KEY (id);
ALTER TABLE hub_workspaces ADD CONSTRAINT hub_workspaces_slug_key UNIQUE (slug);


-- ── KERNEL_JOURNAL_ENTRIES ────────────────────────────
CREATE TABLE IF NOT EXISTS kernel_journal_entries (
  id INTEGER DEFAULT nextval('kernel_journal_entries_id_seq'::regclass) NOT NULL,
  entry_group_id VARCHAR(50) NOT NULL,
  fecha DATE NOT NULL,
  cuenta_codigo VARCHAR(50) NOT NULL,
  cuenta_nombre VARCHAR(150),
  cuenta_tipo VARCHAR(20),
  debito NUMERIC(18,2) DEFAULT 0 NOT NULL,
  credito NUMERIC(18,2) DEFAULT 0 NOT NULL,
  modulo_origen VARCHAR(30) NOT NULL,
  referencia VARCHAR(100),
  descripcion TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE kernel_journal_entries ADD CONSTRAINT kernel_journal_entries_pkey PRIMARY KEY (id);
CREATE INDEX idx_journal_entry_group ON public.kernel_journal_entries USING btree (entry_group_id);
CREATE INDEX idx_journal_fecha ON public.kernel_journal_entries USING btree (fecha);
CREATE INDEX idx_journal_cuenta ON public.kernel_journal_entries USING btree (cuenta_codigo);
CREATE INDEX idx_journal_modulo ON public.kernel_journal_entries USING btree (modulo_origen);


-- ── MODULE_FLAGS ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS module_flags (
  id INTEGER DEFAULT nextval('module_flags_id_seq'::regclass) NOT NULL,
  module_id TEXT NOT NULL,
  enabled BOOLEAN DEFAULT true,
  company_id INTEGER,
  role_filter TEXT,
  updated_at TIMESTAMPTZ DEFAULT now(),
  updated_by TEXT DEFAULT 'system'::text
);
ALTER TABLE module_flags ADD CONSTRAINT module_flags_pkey PRIMARY KEY (id);
ALTER TABLE module_flags ADD CONSTRAINT module_flags_module_id_company_id_role_filter_key UNIQUE (module_id, company_id, role_filter);
CREATE INDEX idx_module_flags_company ON public.module_flags USING btree (company_id);


-- ── POCKETS ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pockets (
  id INTEGER DEFAULT nextval('pockets_id_seq'::regclass) NOT NULL,
  portfolio_id INTEGER NOT NULL,
  name VARCHAR(50) NOT NULL,
  allocated_budget NUMERIC(15,2) DEFAULT 0.00 NOT NULL,
  current_balance NUMERIC(15,2) DEFAULT 0.00 NOT NULL
);
ALTER TABLE pockets ADD CONSTRAINT pockets_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE;
ALTER TABLE pockets ADD CONSTRAINT pockets_pkey PRIMARY KEY (id);
CREATE INDEX idx_pockets_portfolio ON public.pockets USING btree (portfolio_id);


-- ── PORTFOLIOS ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS portfolios (
  id INTEGER DEFAULT nextval('portfolios_id_seq'::regclass) NOT NULL,
  name VARCHAR(50) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  sub_industry_type VARCHAR(100) DEFAULT ''::character varying,
  industry_type VARCHAR(50) DEFAULT 'ESTANDAR'::character varying
);
ALTER TABLE portfolios ADD CONSTRAINT portfolios_pkey PRIMARY KEY (id);
ALTER TABLE portfolios ADD CONSTRAINT portfolios_name_key UNIQUE (name);


-- ── POSTING_RULES ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS posting_rules (
  id INTEGER DEFAULT nextval('posting_rules_id_seq'::regclass) NOT NULL,
  rule_name VARCHAR(100) NOT NULL,
  category VARCHAR(150) NOT NULL,
  transaction_type VARCHAR(15) NOT NULL,
  debit_account_code VARCHAR(50) NOT NULL,
  credit_account_code VARCHAR(50) NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT true,
  portfolio_id INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE posting_rules ADD CONSTRAINT posting_rules_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE;
ALTER TABLE posting_rules ADD CONSTRAINT posting_rules_pkey PRIMARY KEY (id);
CREATE UNIQUE INDEX uq_posting_rules_cat_type ON public.posting_rules USING btree (category, transaction_type, COALESCE(portfolio_id, 0));
CREATE INDEX idx_posting_rules_portfolio ON public.posting_rules USING btree (portfolio_id);


-- ── RESOURCE_IDS ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS resource_ids (
  id INTEGER DEFAULT nextval('resource_ids_id_seq'::regclass) NOT NULL,
  entity_id INTEGER NOT NULL,
  label VARCHAR(100) NOT NULL,
  value VARCHAR(255) NOT NULL,
  category VARCHAR(50) DEFAULT 'FISCAL'::character varying NOT NULL,
  expires_at DATE,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE resource_ids ADD CONSTRAINT resource_ids_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE;
ALTER TABLE resource_ids ADD CONSTRAINT resource_ids_pkey PRIMARY KEY (id);
CREATE INDEX idx_resources_entity ON public.resource_ids USING btree (entity_id);


-- ── TAG_DEFINITIONS ───────────────────────────────────
CREATE TABLE IF NOT EXISTS tag_definitions (
  id INTEGER DEFAULT nextval('tag_definitions_id_seq'::regclass) NOT NULL,
  name VARCHAR(100) NOT NULL,
  color VARCHAR(7) DEFAULT '#000000'::character varying,
  created_at TIMESTAMP DEFAULT now()
);
ALTER TABLE tag_definitions ADD CONSTRAINT tag_definitions_pkey PRIMARY KEY (id);
ALTER TABLE tag_definitions ADD CONSTRAINT tag_definitions_name_key UNIQUE (name);


-- ── THIRD_PARTIES ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS third_parties (
  id INTEGER DEFAULT nextval('third_parties_id_seq'::regclass) NOT NULL,
  identification_type VARCHAR(10) NOT NULL,
  identification_number VARCHAR(30) NOT NULL,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100),
  phone VARCHAR(30),
  website VARCHAR(150),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE third_parties ADD CONSTRAINT third_parties_pkey PRIMARY KEY (id);
ALTER TABLE third_parties ADD CONSTRAINT third_parties_identification_number_key UNIQUE (identification_number);
CREATE INDEX idx_third_parties_nit ON public.third_parties USING btree (identification_number);


-- ── TRANSACTIONS ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER DEFAULT nextval('transactions_id_seq'::regclass) NOT NULL,
  portfolio_id INTEGER NOT NULL,
  pocket_id INTEGER,
  third_party_id INTEGER NOT NULL,
  type VARCHAR(15) NOT NULL,
  amount NUMERIC(15,2) NOT NULL,
  concept VARCHAR(255) NOT NULL,
  transaction_date DATE NOT NULL,
  payment_method VARCHAR(50) NOT NULL,
  category VARCHAR(150) NOT NULL,
  tax_iva_percentage NUMERIC(5,2) DEFAULT 0.00,
  tax_iva_amount NUMERIC(15,2) DEFAULT 0.00,
  tax_gmf_percentage NUMERIC(5,2) DEFAULT 0.00,
  tax_gmf_amount NUMERIC(15,2) DEFAULT 0.00,
  custom_tax_amount NUMERIC(15,2) DEFAULT 0.00,
  net_value NUMERIC(15,2) NOT NULL,
  geo_latitude NUMERIC(10,8),
  geo_longitude NUMERIC(11,8),
  geo_maps_link TEXT,
  evidence_file_path TEXT,
  embedding USER-DEFINED,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  account_id INTEGER,
  dest_account_id INTEGER,
  trm NUMERIC(12,4) DEFAULT 1.0000,
  transaction_currency VARCHAR(10) DEFAULT 'COP'::character varying,
  is_recurring BOOLEAN DEFAULT false,
  recurrence_interval VARCHAR(50) DEFAULT 'MENSUAL'::character varying,
  recurrence_days INTEGER DEFAULT 30,
  recurrence_max_reps INTEGER,
  recurrence_start_date DATE,
  recurrence_end_date DATE
);
ALTER TABLE transactions ADD CONSTRAINT chk_tx_type CHECK (((type)::text = ANY ((ARRAY['INGRESO'::character varying, 'GASTO'::character varying, 'TRANSFERENCIA'::character varying])::text[])));
ALTER TABLE transactions ADD CONSTRAINT chk_tx_positive_amount CHECK ((amount > (0)::numeric));
ALTER TABLE transactions ADD CONSTRAINT transactions_dest_account_id_fkey FOREIGN KEY (dest_account_id) REFERENCES user_accounts(id);
ALTER TABLE transactions ADD CONSTRAINT transactions_pocket_id_fkey FOREIGN KEY (pocket_id) REFERENCES pockets(id) ON DELETE SET NULL;
ALTER TABLE transactions ADD CONSTRAINT transactions_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE RESTRICT;
ALTER TABLE transactions ADD CONSTRAINT transactions_third_party_id_fkey FOREIGN KEY (third_party_id) REFERENCES third_parties(id) ON DELETE RESTRICT;
ALTER TABLE transactions ADD CONSTRAINT transactions_account_id_fkey FOREIGN KEY (account_id) REFERENCES user_accounts(id);
ALTER TABLE transactions ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);
CREATE INDEX idx_transactions_portfolio ON public.transactions USING btree (portfolio_id);
CREATE INDEX idx_transactions_date ON public.transactions USING btree (transaction_date);
CREATE INDEX idx_tx_third_party ON public.transactions USING btree (third_party_id);
CREATE INDEX idx_tx_pocket ON public.transactions USING btree (pocket_id);
CREATE INDEX idx_tx_account ON public.transactions USING btree (account_id);
CREATE INDEX idx_tx_dest_account ON public.transactions USING btree (dest_account_id);


-- ── USER_ACCOUNTS ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_accounts (
  id INTEGER DEFAULT nextval('user_accounts_id_seq'::regclass) NOT NULL,
  name VARCHAR(100) NOT NULL,
  type VARCHAR(50) NOT NULL,
  currency VARCHAR(10) DEFAULT 'COP'::character varying NOT NULL,
  initial_balance NUMERIC(15,2) DEFAULT 0.00 NOT NULL,
  current_balance NUMERIC(15,2) DEFAULT 0.00 NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE user_accounts ADD CONSTRAINT chk_currency CHECK (((currency)::text = ANY ((ARRAY['COP'::character varying, 'USD'::character varying])::text[])));
ALTER TABLE user_accounts ADD CONSTRAINT user_accounts_pkey PRIMARY KEY (id);
ALTER TABLE user_accounts ADD CONSTRAINT user_accounts_name_key UNIQUE (name);


-- ── USER_PROFILES ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_profiles (
  id INTEGER DEFAULT nextval('user_profiles_id_seq'::regclass) NOT NULL,
  name VARCHAR(100) DEFAULT 'Andrés'::character varying NOT NULL,
  email VARCHAR(100) DEFAULT 'andres@finsys.os'::character varying NOT NULL,
  role VARCHAR(50) DEFAULT 'Administrador Contable'::character varying NOT NULL,
  avatar_style VARCHAR(50) DEFAULT 'pixel-grid'::character varying NOT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE user_profiles ADD CONSTRAINT user_profiles_pkey PRIMARY KEY (id);


-- ── WORKSPACE_USERS ───────────────────────────────────
CREATE TABLE IF NOT EXISTS workspace_users (
  id INTEGER DEFAULT nextval('workspace_users_id_seq'::regclass) NOT NULL,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role_label VARCHAR(100) DEFAULT 'Colaborador'::character varying NOT NULL,
  permissions JSONB DEFAULT '{"users": false, "ledger": true, "reports": true, "approvals": false}'::jsonb,
  parent_user_id INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE workspace_users ADD CONSTRAINT workspace_users_parent_user_id_fkey FOREIGN KEY (parent_user_id) REFERENCES workspace_users(id) ON DELETE SET NULL;
ALTER TABLE workspace_users ADD CONSTRAINT workspace_users_pkey PRIMARY KEY (id);
ALTER TABLE workspace_users ADD CONSTRAINT workspace_users_email_key UNIQUE (email);
CREATE INDEX idx_wu_parent ON public.workspace_users USING btree (parent_user_id);


-- ── ROW LEVEL SECURITY ─────────────────────────────────────────
ALTER TABLE workspace_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE pockets ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE resource_ids ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE hub_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE hub_event_attendees ENABLE ROW LEVEL SECURITY;
ALTER TABLE hr_salaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE hr_folders ENABLE ROW LEVEL SECURITY;
ALTER TABLE approvals_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE hr_employee_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE hub_workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE hub_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE hub_workspace_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE hub_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE chart_of_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE hub_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE hub_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE hub_task_assignees ENABLE ROW LEVEL SECURITY;
ALTER TABLE hub_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE third_parties ENABLE ROW LEVEL SECURITY;
ALTER TABLE hr_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE hr_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE hr_doc_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE hr_payment_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE kernel_journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE tag_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE custom_taxes_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE posting_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE cartera_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE module_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE cxp_cxc_ledger ENABLE ROW LEVEL SECURITY;
