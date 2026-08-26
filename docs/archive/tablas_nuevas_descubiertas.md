# Tablas Descubiertas en Auditoría (05 Jul 2026)

Estas tablas existen en Supabase pero no estaban documentadas.

## `hr_folders` (3 filas)

| Columna | Tipo | Nullable | Default |
|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() |
| `workspace_id` | uuid | NO | - |
| `name` | character varying | NO | - |
| `parent_id` | uuid | YES | - |
| `color` | character varying | YES | '#64748b'::character varying |
| `created_by` | uuid | YES | - |
| `created_at` | timestamp with time zone | YES | now() |

**Foreign Keys:**
- `parent_id` → `hr_folders`

---

## `hr_doc_categories` (4 filas)

| Columna | Tipo | Nullable | Default |
|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() |
| `workspace_id` | uuid | NO | - |
| `name` | character varying | NO | - |
| `color` | character varying | NO | '#64748b'::character varying |
| `sort_order` | integer | NO | 99 |
| `is_default` | boolean | NO | false |
| `created_at` | timestamp with time zone | YES | now() |

---

## `hr_profiles` (2 filas)

| Columna | Tipo | Nullable | Default |
|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() |
| `user_id` | uuid | NO | - |
| `workspace_id` | uuid | NO | - |
| `cedula` | character varying | YES | - |
| `phone` | character varying | YES | - |
| `address` | text | YES | - |
| `birth_date` | date | YES | - |
| `hire_date` | date | YES | - |
| `job_title` | character varying | YES | - |
| `department` | character varying | YES | - |
| `status` | character varying | YES | 'active'::character varying |
| `emergency_contact` | text | YES | - |
| `notes` | text | YES | - |
| `created_at` | timestamp with time zone | YES | now() |
| `updated_at` | timestamp with time zone | YES | now() |
| `role_description` | text | YES | - |
| `email` | character varying | YES | - |
| `contract_type` | character varying | YES | - |
| `bank_name` | character varying | YES | - |
| `bank_account_type` | character varying | YES | - |
| `bank_account_number` | character varying | YES | - |
| `eps` | character varying | YES | - |
| `pension_fund` | character varying | YES | - |
| `social_security_no` | character varying | YES | - |
| `country` | character varying | YES | 'Colombia'::character varying |
| `city` | character varying | YES | - |
| `marital_status` | character varying | YES | - |
| `education_level` | character varying | YES | - |
| `skills` | text | YES | - |
| `avatar_url` | text | YES | - |

---

## `hr_salaries` (2 filas)

| Columna | Tipo | Nullable | Default |
|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() |
| `user_id` | uuid | NO | - |
| `workspace_id` | uuid | NO | - |
| `salary_type` | character varying | YES | 'base'::character varying |
| `base_amount` | numeric | YES | 0 |
| `transport_allowance` | numeric | YES | 0 |
| `bonuses` | numeric | YES | 0 |
| `commissions` | numeric | YES | 0 |
| `vacation_provision` | numeric | YES | 0 |
| `severance_provision` | numeric | YES | 0 |
| `health_employee_pct` | numeric | YES | 4.0 |
| `pension_employee_pct` | numeric | YES | 4.0 |
| `tax_withholding` | numeric | YES | 0 |
| `voluntary_deductions` | numeric | YES | 0 |
| `health_employer_pct` | numeric | YES | 8.5 |
| `pension_employer_pct` | numeric | YES | 12.0 |
| `arl_pct` | numeric | YES | 0.522 |
| `family_comp_pct` | numeric | YES | 4.0 |
| `icbf_pct` | numeric | YES | 3.0 |
| `sena_pct` | numeric | YES | 2.0 |
| `ipc_adjustment_pct` | numeric | YES | 0 |
| `ipc_effective_date` | date | YES | - |
| `currency` | character varying | YES | 'COP'::character varying |
| `updated_at` | timestamp with time zone | YES | now() |

---

## `hr_employee_companies` (1 filas)

| Columna | Tipo | Nullable | Default |
|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() |
| `user_id` | uuid | NO | - |
| `entity_id` | integer | NO | - |
| `entity_name` | character varying | YES | - |
| `role_in_company` | character varying | YES | - |
| `start_date` | date | YES | - |
| `is_active` | boolean | YES | true |
| `created_at` | timestamp with time zone | YES | now() |

---

