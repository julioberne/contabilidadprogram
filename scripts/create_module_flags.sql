-- ============================================================
-- module_flags — Feature Flags por módulo, empresa y rol.
-- Permite activar/desactivar módulos del ERP desde la BD
-- sin necesidad de tocar código ni hacer deploy.
--
-- Resolución de prioridad (más específico gana):
--   1. company_id + role_filter  → match exacto
--   2. company_id + role=NULL    → toda la empresa
--   3. company_id=NULL + role    → todos con ese rol
--   4. company_id=NULL + role=NULL → flag GLOBAL
--   5. Si no hay flag → usa registry.active (default)
-- ============================================================

CREATE TABLE IF NOT EXISTS module_flags (
  id          SERIAL PRIMARY KEY,
  module_id   TEXT NOT NULL,                        -- 'contabilidad', 'control-tower', etc.
  enabled     BOOLEAN DEFAULT true,
  company_id  INTEGER DEFAULT NULL,                 -- NULL = todas las empresas
  role_filter TEXT DEFAULT NULL,                     -- NULL = todos los roles, o 'OWNER','ADMIN','MEMBER','VIEWER'
  updated_at  TIMESTAMPTZ DEFAULT now(),
  updated_by  TEXT DEFAULT 'system',
  UNIQUE(module_id, company_id, role_filter)
);

-- Índice para consultas rápidas por empresa
CREATE INDEX IF NOT EXISTS idx_module_flags_company ON module_flags(company_id);

-- Seed: Todos los módulos activos globalmente por defecto
INSERT INTO module_flags (module_id, enabled, company_id, role_filter, updated_by) VALUES
  ('contabilidad',    true,  NULL, NULL, 'system'),
  ('control-tower',   true,  NULL, NULL, 'system'),
  ('project-hub',     true,  NULL, NULL, 'system'),
  ('contabilidad-v2', true,  NULL, NULL, 'system'),
  ('bot',             false, NULL, NULL, 'system'),
  ('trading',         false, NULL, NULL, 'system')
ON CONFLICT (module_id, company_id, role_filter) DO NOTHING;

-- Verificar
SELECT module_id, enabled, company_id, role_filter FROM module_flags ORDER BY module_id;
